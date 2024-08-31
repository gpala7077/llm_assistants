import json
import os

import yaml
from langchain.agents import Tool, initialize_agent
from langchain.llms import OpenAI
from langchain.memory import ChatMessageHistory
from langchain_community.vectorstores import FAISS
from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
    SystemMessagePromptTemplate,
)
import httpx
import asyncio


class FastAPIClient:
    def __init__(self, base_url):
        self.base_url = base_url

    async def send_request(self, endpoint, data):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.base_url}/{endpoint}", json=data)
                response.raise_for_status()
                return response.json()['command']
            except httpx.HTTPStatusError as e:
                print(f"HTTP error occurred: {e.response.status_code}")
                print(f"Response content: {e.response.text}")
                return ''
            except Exception as e:
                print(f"An error occurred: {e}")

    def send_request_sync(self, endpoint, data):
        return asyncio.run(self.send_request(endpoint, data))


class Assistant:
    def __init__(self, client, assistant_name, tools, tool_funcs, model, dynamic_instructions, logger):
        self.client = client
        self.assistant_name = assistant_name
        self.assistant = False
        self.log = logger
        self.model = model
        self.tool_funcs = tool_funcs
        self.assistant_folder = f'/conf/assistants/{self.assistant_name}'
        self.fast_api_client = FastAPIClient("http://localhost:8000")
        self.base_instructions = self.build_instructions()
        self.base_instructions += dynamic_instructions
        self.tools = self.build_tools(tools)
        self.user_files = {}
        self.files = {}
        self.initialize()

    def initialize(self):
        self.load_assistant()
        self.load_vector_stores()
        self.create_thread()

    def create_thread(self):
        self.threads = {
            'main': self.client.beta.threads.create()
        }

    def load_assistant(self):
        # Load the assistants
        assistants = self.client.beta.assistants.list()
        for assistant in assistants.data:
            if assistant.name == self.assistant_name:
                self.log(f"Updating assistant with latest instructions and tools: {assistant.name}")
                self.assistant = self.client.beta.assistants.update(
                    assistant_id=assistant.id,
                    instructions=self.base_instructions,
                    tools=self.tools
                )

        # If assistant is not found create a new assistant
        if not self.assistant:
            self.assistant = self.client.beta.assistants.create(
                name="home-assistant",
                instructions=self.base_instructions,
                tools=self.tools,
                model="gpt-4o",
            )

    def build_instructions(self):
        # Walk through the assistant folder and load any markdowns as one instruction
        self.base_instructions = ''
        instructions = self.get_files('instructions')
        for ins_name, ins_path in instructions.items():
            with open(ins_path, 'r') as ins:
                self.base_instructions += ins.read()
        return self.base_instructions

    def build_tools(self, tools):
        self.tools = [
            {"type": "code_interpreter"},
            {"type": "file_search"},
        ]

        self.tools += tools if isinstance(tools, list) else [tools]
        return self.tools

    def files_exist_in_vector_store(self, vector_store_id, file_name, get_attribute='id'):
        all_files = self.client.files.list()
        all_files = [file.id for file in all_files.data]
        existing_files = self.client.beta.vector_stores.files.list(vector_store_id=vector_store_id).data
        for file in existing_files:
            if file.id in all_files:
                if get_attribute:
                    return getattr(file, get_attribute)
        return False

    def get_file_info(self, file_id, get_attribute='id'):
        all_files = self.client.files.list()
        for file in all_files.data:
            if file.id == file_id:
                if get_attribute:
                    return getattr(file, get_attribute)
        return False

    def vector_exists(self, vector_name):
        vector_stores = self.client.beta.vector_stores.list().data
        for store in vector_stores:
            if store.name == vector_name:
                return store
        return False

    def get_files(self, folder):
        # Perform walkthrough assistant folder and look for file
        assistant_files = os.listdir(f"{self.assistant_folder}/{folder}")
        files_folders_found = {}

        # Get all folders and files in requested folder
        for file in assistant_files:

            # Check if it is a file or folder
            if os.path.isfile(f"{self.assistant_folder}/{folder}/{file}"):
                files_folders_found[file] = f"{self.assistant_folder}/{folder}/{file}"
            else:
                files_folders_found[file] = self.get_files(f"{folder}/{file}")

        return files_folders_found

    def load_vector_stores(self):
        self.batches = {}
        self.stores = {}
        self.streams = {}

        stores = self.get_files('vector_stores')

        for store in stores:
            file_paths = stores[store]
            # Check if the vector store already exists
            if not self.vector_exists(store):
                self.log(f"Creating Vector Store: {store}")
                self.stores[store] = self.client.beta.vector_stores.create(name=store)
            else:
                self.log(f"Vector Store already exists: {store}")
                self.stores[store] = self.vector_exists(store)

            self.streams[store] = {}
            for file_name, file_path in file_paths.items():
                file_name = file_name.split("/")[-1]
                # Check if the file already exists in the vector store
                # If the file has been changed, delete the file and re-upload
                file_id = self.files_exist_in_vector_store(self.stores[store].id, file_name)
                if file_id:
                    self.client.files.delete(file_id)
                self.streams[store][file_name] = open(file_path, 'rb')

            if self.streams[store]:  # If there are files to upload
                self.log(f"Uploading files to Vector Store: {self.stores[store]}")
                # Upload file to the vector store
                self.batches[store] = self.client.beta.vector_stores.file_batches.upload_and_poll(
                    vector_store_id=self.stores[store].id, files=list(self.streams[store].values())
                )

                # Check Status
                self.log(f"Batch Status: {self.batches[store].status}")
                self.log(f"Files Uploaded: {self.batches[store].file_counts}")

                # Update the assistant with the vector store id
                self.assistant = self.client.beta.assistants.update(
                    assistant_id=self.assistant.id,
                    tool_resources={"file_search": {"vector_store_ids": [self.stores[store].id]}}
                )

            loaded_files = self.client.beta.vector_stores.files.list(vector_store_id=self.stores[store].id).data
            all_files = self.client.files.list()
            # Build a dictionary of all associated files with the vector store and assistant
            self.files = {file.id: file for file in all_files.data if file.id in [f.id for f in loaded_files]}

    def send_message(self, system, message):
        messages = [SystemMessage(content=system)]
        message = [message] if isinstance(message, str) else message
        for m in message:
            messages.append(HumanMessage(content=m))
        return self.message_chain.invoke(response)

    def message(self, thread, content):
        def loop_through_function(tool, func):
            # Make sure \ are properly escaped in the pattern
            function_args = json.loads(tool.function.arguments.replace("\\", "\\\\"))
            self.log(f"Function Args: {function_args}")
            # Check if it is a list of commands or just a single command
            if isinstance(function_args, list):
                command_responses = []
                for args in function_args:
                    # Make sure we revert the pattern back to the original
                    if 'pattern' in function_args and isinstance(args['pattern'], list):
                        args['pattern'] = [
                            p.replace("\\\\", "\\") for p in args['pattern']
                        ]
                    elif 'pattern' in function_args:
                        args['pattern'] = args['pattern'].replace("\\\\", "\\")

                    command_response = func(**args)
                    self.log(f"Command Response: {command_response}")
                    command_responses.append(command_response)
                command_response = command_responses
            else:
                # Make sure we revert the pattern back to the original
                if 'pattern' in function_args and isinstance(function_args['pattern'], list):
                    function_args['pattern'] = [
                        p.replace("\\\\", "\\") for p in function_args['pattern']
                    ]
                elif 'pattern' in function_args:
                    function_args['pattern'] = function_args['pattern'].replace("\\\\", "\\")
                self.log(func)
                self.log(f"func(**{function_args})")
                command_response = func(**function_args)
                self.log(f"Command Response: {command_response}")

            tool_outputs.append({
                "tool_call_id": tool.id,
                "output": f'{command_response}'
            })

        self.log(f"Received message: {content}")
        thread = self.get_thread(thread)

        message = self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=content,
            attachments=[
                {'file_id': file_obj.id, "tools": [{"type": "file_search"}]}
                for file_obj in self.client.files.list().data
                # Make sure file is an accepted file type
                if file_obj.purpose == 'assistants'
            ]
        )

        run = None
        exit_loop_count = 0
        while True:
            self.log("Beginning run")
            if run is None:
                run = self.client.beta.threads.runs.create_and_poll(
                    thread_id=thread.id,
                    assistant_id=self.assistant.id,
                )

            if run.status == 'completed':
                messages = self.client.beta.threads.messages.list(
                    thread_id=thread.id
                )
                self.log(f"Run Status: {run.status}\n\nMessages: {messages.data[0]}")

                self.check_if_file_was_generated(messages)
                self.download_open_ai_files()
                if messages.data[0].content[0].type == 'image_file':
                    return messages.data[0].content[1].text.value
                else:
                    return messages.data[0].content[0].text.value

            elif run.status == 'requires_action':

                # Define the list to store tool outputs
                tool_outputs = []

                # IF there are tool calls in the required action section
                self.log(f"{run.required_action}")
                if run.required_action is not None:
                    # Loop through each tool in the required action section
                    for tool in run.required_action.submit_tool_outputs.tool_calls:
                        try:
                            loop_through_function(
                                tool=tool,
                                func=self.tool_funcs[tool.function.name]
                            )
                        except Exception as e:
                            self.log(f"Failed to run function: {tool.function.name} - {e}")
                            self.log(tool)
                    # Submit all tool outputs at once after collecting them in a list
                    if tool_outputs:
                        try:
                            run = self.client.beta.threads.runs.submit_tool_outputs_and_poll(
                                thread_id=thread.id,
                                run_id=run.id,
                                tool_outputs=tool_outputs
                            )
                            self.log(f"Tool outputs submitted successfully.\n{tool_outputs}")
                        except Exception as e:
                            self.log("Failed to submit tool outputs:", e)
                    else:
                        self.log("No tool outputs to submit.")

                    if run.status == 'completed':
                        messages = self.client.beta.threads.messages.list(
                            thread_id=thread.id
                        )
                        self.log(f"Run Status: {run.status}\n\nMessages: {messages.data[0]}")
                        self.check_if_file_was_generated(messages)
                        self.download_open_ai_files()

                        if messages.data[0].content[0].type == 'image_file':
                            return messages.data[0].content[1].text.value
                        else:
                            return messages.data[0].content[0].text.value
                    else:
                        self.log(run.status)
            else:
                self.log(f"Unexpected run status: {run.status}")
                self.log(run)
                break

            exit_loop_count += 1
            if exit_loop_count > 20:
                break

    def get_thread(self, thread):
        if thread in self.threads:
            return self.threads[thread]
        else:
            self.threads[thread] = self.client.beta.threads.create()
            return self.threads[thread]

    def check_if_file_was_generated(self, open_ai_response):
        files = {}
        # Find the message with the visualization file
        # Find the file type

        for message in open_ai_response.data:
            # Check attachments
            for attachment in message.attachments:
                # Check if the file exists in the vector store
                for store_name, store in self.stores.items():
                    files[attachment.file_id] = attachment

            if message.content[0].type == 'image_file':
                file_id = message.content[0].image_file.file_id
                # Check if the file exists in the vector store
                for store_name, store in self.stores.items():
                    files[file_id] = message.content[0].image_file

        self.files = files

    def download_open_ai_files(self, file_ids=None):
        files = self.files if file_ids is None else file_ids
        self.log(self.client.files.list())
        for i, file in enumerate(files):
            file_id = file
            file = self.files[file_id]
            # Check the purpose of the file
            if self.get_file_info(file_id, 'purpose') == 'assistants':
                continue
            file_name = self.get_file_info(file_id, 'filename')
            file_name = file_name.split("/")[-1].split(".")[0]
            self.log(f"Downloading file: {file_name}")
            image_data = self.client.files.content(file_id)
            image_data_bytes = image_data.read()
            self.log(image_data_bytes[:20])
            # Check data type
            if image_data_bytes[:4] == b'\x89PNG':
                filepath = f"/www/{file_name}.png"

            elif image_data_bytes[:4] == b'\xff\xd8\xff\xe0':
                filepath = f"/www/{file_name}.jpg"

            # if it's a html file
            elif (b'<html>' in image_data_bytes[:8] or
                  b'<HTML>' in image_data_bytes[:8] or
                  b'\n<html>' in image_data_bytes[:8] or
                  b'\n<!DOCTYPE html>\n<ht' in image_data_bytes[:20]
            ):
                filepath = f"/www/my-html-{i}.html"

            # if it's a csv file
            else:
                filepath = f"/www/{file_name}.csv"
            self.log(image_data_bytes[:4])

            with open(filepath, "wb") as file:
                file.write(image_data_bytes)

            self.log(f"File downloaded to {filepath}")

    def upload_file_to_open_ai(self, file_path):

        file = self.client.files.create(
            file=open(file_path, "rb"),
            purpose='assistants'
        )
        self.user_files[file_path] = file

        self.update_assistant_with_file(file.id)

    def update_assistant_with_file(self, file_id):
        response = self.client.beta.assistants.update(
            assistant_id=self.assistant.id,
            tool_resources={
                "code_interpreter": {
                    "file_ids": [file_id] if isinstance(file_id, str) else file_id
                }
            }
        )
        return response

    def generate_image(self, prompt):
        response = self.client.images.generate(
            model='dall-e-3',
            prompt=prompt,
            size='256x256',
            quality='better',
            n=1,
        )
        image_url = response.data[0].url
        # Download the image
        image_data = httpx.get(image_url)
        image_data_bytes = image_data.content
        # Get the file name
        file_name = image_url.split("/")[-1].split(".")[0]
        # Check data type
        if image_data_bytes[:4] == b'\x89PNG':
            filepath = f"/www/{file_name}.png"

        elif image_data_bytes[:4] == b'\xff\xd8\xff\xe0':
            filepath = f"/www/{file_name}.jpg"

        with open(filepath, "wb") as file:
            file.write(image_data_bytes)

        return image_url
