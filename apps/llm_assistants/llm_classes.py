import json
import os
import time
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
import os
import csv
import mimetypes
import html
import urllib.parse

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
        self.log_info = logger
        self.model = model
        self.tool_funcs = tool_funcs
        self.tool_funcs['generate_image'] = self.generate_image
        self.assistant_folder = f'/conf/assistants/{self.assistant_name}'
        # self.fast_api_client = FastAPIClient("http://localhost:8000")
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
                self.log_info(f"Updating assistant with latest instructions and tools: {assistant.name}")
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
                model="gpt-3.5-turbo",
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

    def get_files(self, folder, base_folder=None):
        base_folder = base_folder if base_folder else self.assistant_folder

        # Perform walkthrough assistant folder and look for file
        assistant_files = os.listdir(f"{base_folder}/{folder}")
        files_folders_found = {}

        # Get all folders and files in requested folder
        for file in assistant_files:
            if file.startswith('.') or file.startswith('_') or file.startswith('copilot') or file.startswith('Tags'):
                continue  # Skip hidden files or working files/folders or copilot files
            if file.endswith('.png') or file.endswith('.jpg') or file.endswith('.jpeg') or file.endswith('.gif'):
                continue  # Skip image files

            # Check if it is a file or folder
            if os.path.isfile(f"{base_folder}/{folder}/{file}"):
                # Check if the file or folder is empty
                if os.path.getsize(f"{base_folder}/{folder}/{file}") == 0:
                    self.log_info(f"File is empty: {base_folder}/{folder}/{file}")
                    continue

                files_folders_found[file] = f"{base_folder}/{folder}/{file}"
            else:
                files_folders_found[file] = self.get_files(f"{folder}/{file}", base_folder=base_folder)

        return files_folders_found

    def load_vector_stores(self, **kwargs):
        def loop_through_dict(file_dict, store):
            for file_name, file_path in file_dict.items():
                if isinstance(file_path, dict):
                    loop_through_dict(file_path, store)
                else:
                    # Check if the file already exists in the vector store
                    # If the file has been changed, delete the file and re-upload
                    file_id = self.files_exist_in_vector_store(self.stores[store].id, file_name)
                    if file_id:
                        self.client.files.delete(file_id)
                    try:
                        self.streams[store][file_name] = open(file_path, 'rb')
                    except Exception as e:
                        self.log_info(f"Failed to open file: {file_path} - {e}")

        self.batches = {}
        self.stores = {}
        self.streams = {}

        stores = self.get_files('vector_stores')
        vaults = self.get_files('vaults', base_folder='/conf')

        # Combine and loop through all stores
        stores.update(vaults)

        for store in stores:
            file_paths = stores[store]
            # Check if the vector store already exists
            if not self.vector_exists(store):
                self.log_info(f"Creating Vector Store: {store}")
                self.stores[store] = self.client.beta.vector_stores.create(name=store)
            else:
                self.log_info(f"Vector Store already exists: {store}")
                self.stores[store] = self.vector_exists(store)

            self.streams[store] = {}
            for file_name, file_path in file_paths.items():
                file_name = file_name.split("/")[-1]
                if isinstance(file_path, dict):
                    loop_through_dict(file_path, store)

                elif isinstance(file_path, str):
                    # Check if the file already exists in the vector store
                    # If the file has been changed, delete the file and re-upload
                    file_id = self.files_exist_in_vector_store(self.stores[store].id, file_name)
                    if file_id:
                        self.client.files.delete(file_id)
                    try:
                        self.streams[store][file_name] = open(file_path, 'rb')
                    except Exception as e:
                        self.log_info(f"Failed to open file: {file_path} - {e}")

            if self.streams[store]:  # If there are files to upload
                self.log_info(f"Uploading files to Vector Store: {self.stores[store]}")

                # Upload file to the vector store
                self.batches[store] = self.client.beta.vector_stores.file_batches.upload_and_poll(
                    vector_store_id=self.stores[store].id, files=list(self.streams[store].values())
                )

                # Check Status
                self.log_info(f"Batch Status: {self.batches[store].status}")
                self.log_info(f"Files Uploaded: {self.batches[store].file_counts}")

        # all_files = self.client.files.list()
        # store_ids = []
        # for store in self.stores:
        #     loaded_files = self.client.beta.vector_stores.files.list(vector_store_id=self.stores[store].id).data
        #     # Build a dictionary of all associated files with the vector store and assistant
        #     self.files.update({file.id: file for file in all_files.data if file.id in [f.id for f in loaded_files]})
        #     store_ids.append(self.stores[store].id)  # Store the store ids

        # Update the assistant with the last vector store uploaded
        self.assistant = self.client.beta.assistants.update(
            assistant_id=self.assistant.id,
            tool_resources={"file_search": {"vector_store_ids": [self.stores[store].id]}}
        )

    def send_message(self, system, message):
        messages = [SystemMessage(content=system)]
        message = [message] if isinstance(message, str) else message
        for m in message:
            messages.append(HumanMessage(content=m))
        return self.message_chain.invoke(response)

    def message(self, thread, content, vector_store=None):
        self.log_info(f"Received message: {content}")

        def loop_through_function(tool, func):
            # Make sure \ are properly escaped in the pattern
            function_args = json.loads(tool.function.arguments.replace("\\", "\\\\"))
            self.log_info(f"Function Args: {function_args}")
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
                    self.log_info(f"Command Response: {command_response}")
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
                self.log_info(func)
                self.log_info(f"func(**{function_args})")
                command_response = func(**function_args)
                self.log_info(f"Command Response: {command_response}")

            tool_outputs.append({
                "tool_call_id": tool.id,
                "output": f'{command_response}'
            })

        thread = self.get_thread(thread, store_id=vector_store)

        # if vector_store:
        #     # Attach all the files from the vector store to the message
        #     files_in_store = self.client.beta.vector_stores.files.list(vector_store_id=self.stores[vector_store].id).data
        #     attachments = [
        #         {'file_id': file_obj.id, "tools": [{"type": "file_search"}]}
        #         for file_obj in files_in_store
        #     ]
        # else:
        #     attachments = None

        message = self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=content,
            # attachments=attachments,
            # attachments=[
            #     {'file_id': file_obj.id, "tools": [{"type": "file_search"}]}
            #     for file_obj in self.client.files.list().data
            #     # Make sure file is an accepted file type
            #     if file_obj.purpose == 'assistants'
            # ]
        )

        run = None
        exit_loop_count = 0
        while True:
            self.log_info("Beginning run")
            if run is None:
                run = self.client.beta.threads.runs.create_and_poll(
                    thread_id=thread.id,
                    assistant_id=self.assistant.id,
                )

            if run.status == 'completed':
                messages = self.client.beta.threads.messages.list(
                    thread_id=thread.id
                )
                self.log_info(f"Run Status 1: {run.status}\n\nMessages: {messages.data[0]}")

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
                self.log_info(f"{run.required_action}")
                if run.required_action is not None:
                    # Loop through each tool in the required action section
                    for tool in run.required_action.submit_tool_outputs.tool_calls:
                        try:
                            loop_through_function(
                                tool=tool,
                                func=self.tool_funcs[tool.function.name]
                            )
                        except Exception as e:
                            self.log_info(f"Failed to run function: {tool.function.name} - {e}")
                            self.log_info(tool)
                    # Submit all tool outputs at once after collecting them in a list
                    if tool_outputs:
                        try:
                            run = self.client.beta.threads.runs.submit_tool_outputs_and_poll(
                                thread_id=thread.id,
                                run_id=run.id,
                                tool_outputs=tool_outputs
                            )
                            self.log_info(f"Tool outputs submitted successfully.\n{tool_outputs}")
                        except Exception as e:
                            self.log_info("Failed to submit tool outputs:", e)
                    else:
                        self.log_info("No tool outputs to submit.")

                    if run.status == 'completed':
                        messages = self.client.beta.threads.messages.list(
                            thread_id=thread.id
                        )
                        self.log_info(f"Run Status 2: {run.status}\n\nMessages: {messages.data[0]}")
                        self.check_if_file_was_generated(messages)
                        self.download_open_ai_files()

                        if messages.data[0].content[0].type == 'image_file':
                            return messages.data[0].content[1].text.value
                        else:
                            return messages.data[0].content[0].text.value
                    else:
                        self.log_info(run.status)
            else:
                self.log_info(f"Unexpected run status: {run.status}")
                self.log_info(run)
                break

            exit_loop_count += 1
            if exit_loop_count > 20:
                break

    def get_thread(self, thread, store_id=None):
        store_id = self.stores[store_id] if store_id else None

        if thread in self.threads:
            if store_id:
                # # Update the assistant with the last vector store uploaded
                # self.assistant = self.client.beta.assistants.update(
                #     assistant_id=self.assistant.id,
                #     tool_resources={"file_search": {"vector_store_ids": [store_id.id]}}
                # )

                # Update the assistant with the vector store ids
                self.threads[thread] = self.client.beta.threads.update(
                    thread_id=self.threads[thread].id,
                    tool_resources={
                        "file_search": {
                            "vector_store_ids": [store_id.id]
                        }
                    }
                )

        else:
            if store_id:
                # Update the assistant with the last vector store uploaded
                # self.assistant = self.client.beta.assistants.update(
                #     assistant_id=self.assistant.id,
                #     tool_resources={"file_search": {"vector_store_ids": [store_id.id]}}
                # )
                # Update the assistant with the vector store ids
                self.threads[thread] = self.client.beta.threads.create(
                    tool_resources={
                        "file_search": {
                            "vector_store_ids": [store_id.id]
                        }
                    }
                )
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

            # Sometimes receive message like this :
            #  Message(
            #  id='msg_zL4El3GsyRTl7B5QGvLKTqHs',
            #  assistant_id='asst_25EUBkF394xaTNTtq6RBNyx1',
            #  attachments=[],
            #  completed_at=None,
            #  content=[
            #   TextContentBlock(
            #   text=Text(
            #   annotations=[
            #   FileCitationAnnotation(
            #   end_index=250,
            #   file_citation=FileCitation(
            #   file_id='file-RfYVAZsHVnrR1oT3YPFPxn'
            #   ),
            #   start_index=215,
            #   text="���42:12���Mariana's Surgery Update.md���", type='file_citation')
            #   ],
            #   value="Hello Appdaemon! There is a picture associated with Mariana's surgery update available.
            #   You can view it [here]
            #   (sandbox:/_FileOrganizer2000/Processed/Attachments/2024-12-03-20-46-41-Mariana's%20Surgery%20Update.jpeg)���42:12���Mariana's Surgery Update.md���. Let me know if there's anything else you'd like to see or do!"), type='text')], created_at=1733375734, incomplete_at=None, incomplete_details=None, metadata={}, object='thread.message', role='assistant', run_id='run_lxLRS6CoSp46aea9DhhkHyx4', status=None, thread_id='thread_YbPCNxCQ43IgmpYApXLDJtI4')

            # Check if the message itself contains a url to a file for download
            if message.content[0].type == 'text':
                for i, annotation in enumerate(message.content[0].text.annotations):
                    if annotation.type == 'file_citation':
                        file_id = annotation.file_citation.file_id
                        # Download the file
                        file_name = self.get_file_info(file_id, 'filename')
                        file_name = file_name.split("/")[-1].split(".")[0]

                        self.log_info(f"Downloading file: {file_name}")
                        try:
                            image_data = self.client.files.content(file_id)
                            image_data_bytes = image_data.read()
                            self.log_info(image_data_bytes[:20])
                            # Check data type
                            if image_data_bytes[:4] == b'\x89PNG':
                                filepath = f"/www/image-{i}.png"

                            elif image_data_bytes[:4] == b'\xff\xd8\xff\xe0':
                                filepath = f"/www/image-{i}.jpg"

                            # jpeg
                            elif image_data_bytes[:4] == b'\xff\xd8\xff\xe1':
                                filepath = f"/www/image-{i}.jpeg"

                            with open(filepath, "wb") as file:
                                file.write(image_data_bytes)

                        except Exception as e:
                            self.log_info(f"Failed to download file: {file_name} - {e}")
                        files[file_id] = file_name

        self.files = files



    def download_open_ai_files(self, file_ids=None):
        files = self.files if file_ids is None else file_ids
        self.log_info(self.client.files.list())
        downloaded_files = {}
        for i, file in enumerate(files):
            file_id = file
            file = self.files[file_id]
            # Check the purpose of the file
            if self.get_file_info(file_id, 'purpose') == 'assistants':
                continue
            file_name = self.get_file_info(file_id, 'filename')
            file_name = file_name.split("/")[-1].split(".")[0]
            self.log_info(f"Downloading file: {file_name}")
            image_data = self.client.files.content(file_id)
            image_data_bytes = image_data.read()
            self.log_info(image_data_bytes[:20])
            # Check data type
            if image_data_bytes[:4] == b'\x89PNG':
                filepath = f"/www/image-{i}.png"

            elif image_data_bytes[:4] == b'\xff\xd8\xff\xe0':
                filepath = f"/www/image-{i}.jpg"

            # if it's a html file
            elif (b'<html>' in image_data_bytes[:8] or
                  b'<HTML>' in image_data_bytes[:8] or
                  b'\n<html>' in image_data_bytes[:8] or
                  b'\n<!DOCTYPE html>\n<ht' in image_data_bytes[:20]
            ):
                filepath = f"/www/my-html-{i}.html"

            # if it's a csv file
            else:
                filepath = f"/www/csv-{i}.csv"
            self.log_info(image_data_bytes[:4])

            with open(filepath, "wb") as file:
                file.write(image_data_bytes)

            self.log_info(f"File downloaded to {filepath}")
            downloaded_files[file_name] = filepath

        self.display_downloads(files=downloaded_files)

    def display_downloads(self,files=None, directory='/www'):
        """
        Create an index.html file to display all the generated/downloaded files.
        If it's an image file, display the image.
        If it's a CSV file, display the head of the CSV file.
        If it's a PDF or text file, display the content.
        At the bottom of the page, allow the user to download the files.
        """
        html_content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Downloaded Files</title>
            <style>
                body { font-family: Arial, sans-serif; }
                .file-content { margin-bottom: 20px; }
                .download-links { margin-top: 50px; }
                pre { background-color: #f0f0f0; padding: 10px; }
                table { border-collapse: collapse; width: 100%; }
                table, th, td { border: 1px solid black; }
                th, td { padding: 8px; text-align: left; }
                img { max-width: 100%; height: auto; }
            </style>
        </head>
        <body>
        <h1>Downloaded Files</h1>
        '''

        download_files = []
        processed_files = set()  # To keep track of processed files and avoid duplicates

        for file in os.listdir(directory):
            if file == 'index.html' or file == 'delete.php':
                continue  # Skip index.html to prevent recursive inclusion

            filepath = os.path.join(directory, file)
            version_param = int(time.time())  # Convert to string

            if os.path.isfile(filepath):
                # Skip duplicate files
                if file in processed_files:
                    continue
                processed_files.add(file)

                mimetype, _ = mimetypes.guess_type(filepath)
                if mimetype:
                    self.log_info(f"Found file: {file} - {mimetype}")

                    # URL-encode the filename for URLs
                    url_encoded_file = urllib.parse.quote(file)

                    # Escape the filename for HTML content
                    escaped_file = html.escape(file)

                    if mimetype.startswith('image/'):
                        html_content += f'''
                        <div class="file-content">
                            <h2>{escaped_file}</h2>
                            <img src="{url_encoded_file}?v={version_param}" alt="{escaped_file}">
                        </div>
                        '''
                    elif mimetype == 'text/html':
                        # Be cautious with including HTML files directly
                        if file != 'index.html':
                            with open(filepath, 'r', encoding='utf-8') as f:
                                file_data = f.read()
                                html_content += f'''
                                <div class="file-content">
                                    <h2>{escaped_file}</h2>
                                    {file_data}
                                </div>
                                '''
                    elif mimetype == 'text/csv':
                        with open(filepath, 'r', encoding='utf-8') as f:
                            reader = csv.reader(f)
                            rows = [row for _, row in zip(range(5), reader)]  # Get first 5 rows
                            html_content += f'''
                            <div class="file-content">
                                <h2>{escaped_file}</h2>
                                <table>
                            '''
                            if rows:
                                # Add table headers
                                html_content += '<tr>' + ''.join(
                                    f'<th>{html.escape(cell)}</th>' for cell in rows[0]) + '</tr>'
                                # Add table rows
                                for row in rows[1:]:
                                    html_content += '<tr>' + ''.join(
                                        f'<td>{html.escape(cell)}</td>' for cell in row) + '</tr>'
                            html_content += '''
                                </table>
                            </div>
                            '''
                    elif mimetype == 'application/pdf':
                        html_content += f'''
                        <div class="file-content">
                            <h2>{escaped_file}</h2>
                            <embed src="{url_encoded_file}?v={version_param}" type="application/pdf" width="100%" height="600px" />
                        </div>
                        '''
                    elif mimetype.startswith('text/'):
                        with open(filepath, 'r', encoding='utf-8') as f:
                            file_data = f.read()
                            html_content += f'''
                            <div class="file-content">
                                <h2>{escaped_file}</h2>
                                <pre>{html.escape(file_data)}</pre>
                            </div>
                            '''
                    else:
                        # Handle other file types if necessary
                        pass
                else:
                    # Handle files with undetermined MIME types if necessary
                    pass

                download_files.append(file)

        # Add delete buttons at the bottom
        html_content += '''
        <div class="file-actions">
            <h2>Manage Files</h2>
            <ul>
        '''

        for file in download_files:
            url_encoded_file = urllib.parse.quote(file)
            escaped_file = html.escape(file)
            html_content += f'''
            {escaped_file}
            <a href="{escaped_file}" download>Download</a>
            <form method="POST" action="delete.php" style="display:inline;">
                <input type="hidden" name="filename" value="{escaped_file}">
                <button type="submit">Delete</button>
            </form>
            '''

        html_content += '''
            </ul>
        </div>
        </body>
        </html>
        '''

        # Write the HTML content to index.html
        with open(os.path.join(directory, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html_content)

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

    def generate_image(self, prompt, n=1):

        filepaths = {}
        for i in range(n):
            response = self.client.images.generate(
                model='dall-e-3',
                prompt=prompt,
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
                filepath = f"/www/image-{i}.png"

            elif image_data_bytes[:4] == b'\xff\xd8\xff\xe0':
                filepath = f"/www/image-{i}.jpg"

            with open(filepath, "wb") as file:
                file.write(image_data_bytes)

            filepaths[file_name] = filepath

        self.display_downloads(files=filepaths)
        return list(filepaths.values())


