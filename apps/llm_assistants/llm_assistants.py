import appdaemon.plugins.hass.hassapi as hass
import pytz
from openai import OpenAI
import json
import requests
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_community.tools import YouTubeSearchTool
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities.sql_database import SQLDatabase
# from serpapi import GoogleSearch
import traceback
import os
from llm_classes import Assistant, FastAPIClient
from llm_tools import get_tools
from datetime import datetime
import yaml
import pytz
from smarthome_global import *


class LLMAssistants(Base):
    def initialize(self):
        self.app_name = 'LLM Assistants Services'
        self.device_types = []
        self.sensor_types = []
        self.log_info("Starting LLM Assistants Services")
        super().initialize()  # Initialize the Base class

        # self.fast_api_client = FastAPIClient("http://localhost:8000")
        self.define_apps()
        self.define_tools()
        self.load_open_ai()
        # self.delete_all_files_and_stores() # Hail Mary to delete all files and stores

        self.load_agents()
        self.load_assistants()
        self.listen_for_user_input()

        self.manager.register_app(
            app_name=self.app_name_short,
            status='initialized',
            time_until_ready=self.get_time_until_ready()
        )
        self.log_info(
            message=f"""
            LLM Assistants Services have initialized
            Will be fully ready at {self.get_time_until_ready():%H:%M:%S %p}
            Or in approximately {(self.get_time_until_ready() - datetime.now(self.timezone)).total_seconds(): ,.0f} seconds from now
            """,
            level='INFO',
            log_room='all',
            function_name='setup'
        )

    def setup(self):
        """Set up the HACS app."""
        super().setup()
        self.create_room_automations = False
        self.create_home_automations = False
        self.user_room_auto = False
        self.connect_to_database()

    def create_room_based_automations(self):
        pass

    def create_automation_entities(self):
        super().create_automation_entities()

    def listen_for_user_input(self):
        # Listen for Assist Commands
        self.listen_event(self.send_command, event='appdaemon_tool_request')

    def define_tools(self):
        self.tool_funcs = {
            'command_matching_entities': self.controller.command_matching_entities,
            'play_buzzer': self.apps['apollo'].play_buzzer,
            'notify_desk': self.apps['workstation'].notify_desk,
            # 'toggle_desk_for_persons': self.apps['workstation'].toggle_desk_for_persons,
            'adjust_desk_height': self.apps['workstation'].adjust_desk_height,
            'get_matching_entities': self.controller.get_matching_entities,
            'get_room_info': self.manager.get_room_info,
            'get_home_info': self.manager.get_home_info,
            'get_user_info': self.manager.get_user_info,
            'get_home_settings': self.manager.get_home_settings,
            'control_master_overrides': self.control_master_overrides,
            'control_user_overrides': self.control_user_overrides,
            'get_master_overrides': self.get_master_overrides,
            'get_user_overrides': self.get_user_overrides,
            'search_internet': self.search_internet,
            'get_youtube_video': self.get_youtube_video,
            'db_agent': self.db_agent,
            'modify_home_database': self.modify_home_database,
            'log_user_preferences': self.log_user_preferences,
            'run_master_on_automation': self.run_master_on_automation,
            'run_master_off_automation': self.run_master_off_automation,
            'search_music': self.apps['music'].search_music,
            'play_music': self.apps['music'].play_music,
            'get_automation_status': self.get_automation_status,

        }

    def get_automation_status(self, app=None):
        status = {}
        if app:
            for entity in self.apps[app].room_automation_booleans:
                state = self.get_state(entity, attribute='all')
                self.log_info(f"{entity}: {state}")
                status[entity] = state
        else:
            for app in self.apps:
                for entity in self.apps[app].room_automation_booleans:
                    state = self.get_state(entity, attribute='all')
                    self.log_info(f"{entity}: {state}")
                    status[entity] = state

        return status

    def modify_home_database(self, sql):
        """Execute a SQL command on the Home Database"""
        try:
            result = self.home_database.execute_by_cursor(sql)
            return f"SQL Command executed successfully\n{result}"
        except Exception as e:
            self.log_info(f"Error: {e}")
            self.log_info(f"Traceback: {traceback.format_exc()}")
            return f"Error: {e}"

    def run_master_on_automation(self, app, room, override=True, delay_execution=0, **kwargs):
        try:
            if delay_execution > 0:
                self.run_in(self.apps[app].master_on, delay_execution, area=area, override=override)
            else:
                self.apps[app].master_on(
                    area=room,
                    override=override,
                    **kwargs
                )

            return f"Master on command sent to {app}" if delay_execution == 0 else f"Master on command scheduled for {app} in {delay_execution} seconds"
        except Exception as e:
            self.log_info(f"Error: {e}")
            self.log_info(f"Traceback: {traceback.format_exc()}")
            return f"Error: {e}"

    def run_master_off_automation(self, app, room, override=True, delay_execution=0, **kwargs):
        if delay_execution > 0:
            self.run_in(self.apps[app].master_off, delay_execution, area=area, override=override)
        else:
            self.apps[app].master_off(
                area=room,
                override=override,
                **kwargs
            )

        return f"Master off command sent to {app}" if delay_execution == 0 else f"Master off command scheduled for {app} in {delay_execution} seconds"

    def define_apps(self):
        self.apps = {
            'lights': self.get_app('lights'),
            'windows': self.get_app('windows'),
            'air_quality': self.get_app('air_quality'),
            'workstation': self.get_app('workstation'),
            'apollo': self.get_app('apollo'),
            'music': self.get_app('music'),
        }

    def delete_all_files_and_stores(self):
        # Delete all vector stores
        vector_stores = self.client.beta.vector_stores.list()
        for store in vector_stores.data:
            self.log_info(f"Deleting vector store: {store.name}")
            self.client.beta.vector_stores.delete(store.id)

        # Delete all files
        files = self.client.files.list()
        for file in files.data:
            self.log_info(f"Deleting file: {file}")
            self.client.files.delete(file.id)

    def load_open_ai(self):
        os.environ["OPENAI_API_KEY"] = self.args['openai_api_key']
        self.client = OpenAI()
        self.model = ChatOpenAI(model='gpt-4o-mini')
        self.parser = StrOutputParser()
        self.message_chain = self.model | self.parser
        self.youtube = YouTubeSearchTool()

    def load_sql_agents(self):
        try:
            # Load SQL Agents
            return {'home-db-agent': create_sql_agent(
                self.model,
                db=SQLDatabase.from_uri(self.args.get('home_db_url')),
                agent_type='openai-tools',
                verbose=True
            ), 'hass-db-agent': create_sql_agent(
                self.model,
                db=SQLDatabase.from_uri(self.args.get('hass_db_url')),
                agent_type='openai-tools',
                verbose=True
            )}
        except Exception as e:
            self.log_info(f"Error: {e}")
            self.log_info(f"Traceback: {traceback.format_exc()}")
            return {}

    def load_agents(self):
        self.agents = {}
        self.agents.update(self.load_sql_agents())

    def load_assistants(self):
        self.assistants = {}
        # Walk through folders in assistants directory and load assistants.
        assistants = os.listdir('/conf/assistants')
        for assistant in assistants:
            self.assistants[assistant] = Assistant(
                client=self.client,
                assistant_name=assistant,
                tools=get_tools('all'),
                tool_funcs=self.tool_funcs,
                logger=self.log,
                model=self.model,
                dynamic_instructions=self.dynamic_instructions()
            )

            # Every 15 minutes update the vector stores for each assistant
            # This will allow the AI to provide more accurate responses
            # Start 15 minutes after initialization
            # self.run_every(
            #     callback=self.assistants[assistant].load_vector_stores,
            #     start=datetime.now(pytz.timezone('America/Chicago')) + timedelta(seconds=60 * 15),
            #     interval=60 * 15,   # 15 minutes (60 seconds * 15)
            # )

    def dynamic_instructions(self):
        regex_patterns = {
            app: self.apps[app].get_all_patterns()
            for app in self.apps if hasattr(self.apps[app], 'get_all_patterns')
        }

        controllable = {
            app: self.apps[app].room_entities_data
            for app in self.apps if hasattr(self.apps[app], 'room_entities_data')
        }
        # Convert dictionary into a string for a dynamic instruction to feed into the AI Assistant
        regex_patterns_str = """The following Apps and their patterns are available for you to use when using
        command_matching_entities or get_matching_entities or any argument that requires a ReGeX pattern
        
        IT IS VERY IMPORTANT that you do not deviate from the patterns provided here.
        
        
        : \n\n"""

        for app, patterns in regex_patterns.items():
            regex_patterns_str += f"""
            ## {app.title()} Regex Patterns:
            """
            for device_type, pattern in patterns.items():
                regex_patterns_str += f"""
                {device_type.title()}:
                """
                for entity_type, pat in pattern.items():
                    regex_patterns_str += f"""
                    - {entity_type}: 
                        - INCLUDE: {pat[0]}
                        - EXCLUDE: {pat[1]}
                    """

        regex_patterns_str += f"""
        ## Controllable Entities:
        """
        for app, rooms in controllable.items():
            regex_patterns_str += f"""
            ## {app.title()} Controllable Entities:
            """
            for room, entities in rooms.items():
                regex_patterns_str += f"""
                {room.title()}:
                """
                for entity_type, entity in entities.items():
                    if entity:
                        regex_patterns_str += f"""
                        - {entity_type.title()}:
                            - {entity}
                        """

        # Add Available Tools in Instructions
        available_tools = f"""\n\n
        ## IMPORTANT NOTE:
        
        “You shall only invoke the following defined functions: 
        {list(self.tool_funcs.keys())}. 
        **You should NEVER invent or use functions NOT defined or NOT listed HERE, 
        especially the multi_tool_use.parallel function. 
        If you need to call multiple functions, you will call them one at a time **.
        ”
        """
        self.log_info(f"""
        Dynamic Instructions:
        {regex_patterns_str}
        """)
        return regex_patterns_str + available_tools

    def send_event_to_assistant(self, event, data, **kwargs):
        prompt = data.get('prompt')
        thread = data.get('thread_id', 'main')
        example = self.fast_api_client.send_request_sync(
            endpoint="generate_prompt",
            data={"query": content}
        )
        if example:
            command += f"""
         EXAMPLES:
        {example}
        """
        response = self.assistants['home-assistant'].message(thread, command)
        self.fire_event("appdaemon_tool_response", response=response)

    def send_command(self, *args, **kwargs):
        self.log_info(f"Received command: {args}")
        self.log_info(f"Received kwargs: {kwargs}")
        request_origin = 'appdaemon_tool_request'
        data = args[1]
        llm_context = data.get('llm_context')
        params = data.get('params')
        assistant_input = params.get('assistant_input')
        platform = llm_context.get('platform')
        context = llm_context.get('context')
        user_id = context.get('user_id')
        user = self.user_details.get(user_id, 'gerardo')
        thread = llm_context.get('thread_id', 'main')
        content = llm_context.get('user_prompt')
        device_id = llm_context.get('device_id')
        metadata = llm_context.get('metadata', {})
        self.log_info(
            f"""
            Received command from {user_id} on {platform} with the following metadata: {metadata}
            """
        )
        try:
            # # Enhance the user query with the best example set
            # example = self.fast_api_client.send_request_sync(
            #     endpoint="generate_prompt",
            #     data={"query": content}
            # )
            # self.log_info(f"Example content: {example}")

            # Enhance the user query by attaching a relevant vector store
            # This will allow the AI to provide more accurate responses
            vector_store = self.attach_vector_store(content)
            self.log_info(f"Vector Store: {vector_store}")
            #
            command = f"""
Receiving input from {user.title()}. Address them by their name and follow their instructions or 
perform the task accurately and provide feedback. 
It is {datetime.now(pytz.timezone('America/Chicago')).strftime('%A, %B %d, %Y')} at 
{datetime.now(pytz.timezone('America/Chicago')).strftime('%I:%M %p')}.
 
 USER INPUT: 
 
 {content}

 DESCRIPTION OF TASKS:
 {assistant_input}

"""
            #             if example:
            #                 command += f"""
            #  EXAMPLES:
            # {example}
            # """
            if vector_store:
                command += f"""
   USE VECTOR STORE: {vector_store}    
"""

            response = self.assistants['home-assistant'].message(thread, command, vector_store)

            if request_origin == 'appdaemon_tool_request':
                self.log_info(f"Sending response back to {platform} with the following response: {response}")
                self.fire_event("appdaemon_tool_response", response=response)

            elif request_origin == 'user_input':
                self.set_state(entity_id, state='responded', command=content, response=response)
            else:
                self.log_info(f"Unknown request origin: {request_origin}\n{response}")
            # self.manager.notify_tts(response, room_override='office', tts_override=True)
        except Exception as e:
            self.log_info(f"Error: {e}")
            self.log_info(f"Traceback: {traceback.format_exc()}")

            error_log = f"Error: {e}\n\nTraceback: {traceback.format_exc()}"

    def attach_vector_store(self, content):
        """Get the most relevant vector store for the user input if any."""

        query = f"""
        We have the following vector stores available for you to use:
        {list(self.assistants['home-assistant'].stores.keys())}
        
        Please select return the name of the most relevant vector store for the user input:
        
        IMPORTANT: ONLY RETURN THE NAME OF THE VECTOR STORE. DO NOT RETURN ANYTHING ELSE.
        
        user_preferences: Contain all the user preferences for the home assistant for each user.
        home_automation: Contains all the home automation rules, patterns, and usage rules
        Clarity: Contains all the PKM files and knowledge for the user Gerardo. 
        
        USER INPUT:
        {content}
        
        
        EXPECTED OUTPUT:
        
        <vector_store_name> # i.e 'user_preferences' or 'home_automation' or 'Clarity' 
        
        """

        response = self.message_chain.invoke(query)
        self.log(f"Response: {response}")
        for store in self.assistants['home-assistant'].stores:
            if store in response:
                return store

    def control_master_overrides(self, app, command='turn_on', delay_execution=0, **kwargs):
        try:
            return self.apps[app].control_master_overrides(command=command, delay_execution=delay_execution, **kwargs)
        except Exception as e:
            self.log_info(f"Error: {e}")
            self.log_info(f"Traceback: {traceback.format_exc()}")
            return f"No app {app} found."

    def control_user_overrides(self, app, area, command='turn_on', delay_execution=0, **kwargs):
        try:
            return self.apps[app].control_user_overrides(command=command, area=area, delay_execution=delay_execution,
                                                         **kwargs)
        except Exception as e:
            self.log_info(f"Error: {e}")
            self.log_info(f"Traceback: {traceback.format_exc()}")
            return f"No app {app} found."

    def get_master_overrides(self, app):
        try:
            return self.apps[app].get_master_overrides()
        except Exception as e:
            self.log_info(f"Error: {e}")
            self.log_info(f"Traceback: {traceback.format_exc()}")
            return f"No app {app} found."

    def get_user_overrides(self, app):
        try:
            return self.apps[app].get_user_overrides()
        except Exception as e:
            self.log_info(f"Error: {e}")
            self.log_info(f"Traceback: {traceback.format_exc()}")
            return f"No app {app} found."

    def get_youtube_video(self, search_term, max_results=1):
        try:
            response = self.youtube.run(f"{search_term},{max_results}")
            return response[0] if max_results == 1 else response
        except Exception as e:
            self.log_info(f"Error: {e}")
            self.log_info(f"Traceback: {traceback.format_exc()}")
            return f"Error: {e}"

    def search_internet(self, query):
        try:
            search = GoogleSearch(
                location="Chicago, Illinois, United States",
                q=query,
            )
            return search.get_dict()
        except Exception as e:
            self.log_info(f"Error: {e}")
            self.log_info(f"Traceback: {traceback.format_exc()}")
            return f"Error: {e}"

    def db_agent(self, db_agent, query):
        try:
            self.log_info(f"Received DB AGENT query: {query}", level='INFO')
            query_updated = self.fast_api_client.send_request_sync(
                endpoint="generate_prompt",
                data={"query": query}
            )
            self.log_info(f"""
            Updated Query for DB Agent {db_agent}:
            {query_updated}
            """, level='INFO')
            if not query_updated or query_updated == '':
                query_updated = query
            response = self.agents[db_agent].invoke(query_updated)
            self.log_info(f"Response: {response}")
            return response

        except Exception as e:
            self.log_info(f"Error: {e}")
            self.log_info(f"Traceback: {traceback.format_exc()}")
            return f"Error: {e}"

    #
    def log_user_preferences(self, user, app, category, preferences, when_to_use):
        user_preference = f"""
        ### User: {user}
        **Preference**: {preferences}  
        **Category**: {category}  
        **When to use**: {when_to_use}
        """

        # Define the path to the markdown file
        app_md_path = f"/conf/assistants/vector_stores/user_preferences/{app}.md"
        try:
            # Check if the markdown file exists, if not create it
            if not os.path.exists(app_md_path):
                with open(app_md_path, 'a') as f:
                    f.write(f"""
                    ## USER PREFERENCES
    
                    {user_preference}
                    \n
                    """)
            else:
                # If it exists, check if the user preference is already in the file
                with open(app_md_path, 'r') as f:
                    if user_preference in f.read():
                        return "User preference already logged"

                with open(app_md_path, 'a') as f:
                    f.write(user_preference)
                    f.write('\n')

            # Load the updated vector store for each assistant
            for name, assistant in self.assistants.items():
                assistant.load_vector_stores("vector_stores")
        except Exception as e:
            self.log_info(f"Error: {e}")
            self.log_info(f"Traceback: {traceback.format_exc()}")
            return f"Error: {e}"
