def define_command_matching_entities():
    tool = [{
        "type": "function",
        "function": {
            "name": "command_matching_entities",
            "description": """
                        Command Matching Entities using ReGex Patterns.
                        This function will match entities based on the given ReGex pattern and execute
                        the given command on the matching entities. This function returns 
                        the output of the command executed and all the entities that were affected.
                        This returns a dictionary with the response. If there was no command executed, it returns 
                        an empty dictionary.
                    """,
            "parameters": {
                "type": "object",
                "properties": {
                    "hacs_commands": {
                        "type": "string",
                        "description": "Command to execute on matching entities"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "ReGex pattern to match entities"
                    },
                    "area": {
                        "type": "string",
                        "description": "Area to match entities"
                    },
                    "domain": {
                        "type": "string",
                        "description": "Domain to match entities"
                    },
                    "pattern_overwrite": {
                        "type": "string",
                        "description": "Overwrite pattern if necessary"
                    },
                    "device_state": {
                        "type": "string",
                        "description": "State of the device to filter entities"
                    },
                    "delay_execution": {
                        "type": "number",
                        "description": "Delay execution of the command"
                    },
                },
                "required": ["hacs_commands"]
            }
        }
    }]
    return tool


def define_get_matching_entities():
    tool = [{
        "type": "function",
        "function": {
            "name": "get_matching_entities",
            "description": """
                        Get Matching Entities using ReGex Patterns.
                        This function will match entities based on the given ReGex pattern and return
                        the given state or attributes on the matching entities. This function returns 
                        the all sensors and requested information.
                    """,
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "ReGex pattern to match entities"
                    },
                    "area": {
                        "type": "string",
                        "description": "Area to match entities"
                    },
                    "domain": {
                        "type": "string",
                        "description": "Domain to match entities"
                    },
                    "pattern_overwrite": {
                        "type": "string",
                        "description": "Overwrite pattern if necessary"
                    },
                    "device_state": {
                        "type": "string",
                        "description": "State of the device to filter entities"
                    },
                    "get_attribute": {
                        "type": "string",
                        "description": "Attribute to get from the entities"
                    },

                    "filter_by": {
                        "type": "string",
                        "description": "Filter by the attribute value"
                    },
                    "filter_by_and_or": {
                        "type": "string",
                        "description": "Filter by the attribute value"
                    },
                    "agg_func": {
                        "type": "string",
                        "description": "Aggregate function to apply to the entities"
                    },
                    "index": {
                        "type": "string",
                        "description": "Index to aggregate the entities"
                    },

                },
                "required": ['domain']
            }
        }
    }]

    return tool


def define_shortcut_functions():
    tool = [
        {
            "type": "function",
            "function": {
                "name": "get_room_info",
                "description": """
                            Get information about a specific room.
                            This function returns various environmental and occupancy data about the specified room.
                        """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "room": {
                            "type": "string",
                            "description": "The room to get information about"
                        },
                    },
                    "required": ["room"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_home_info",
                "description": """
                            Get information about the entire home.
                            This function returns various environmental and occupancy data about the entire home.
                        """,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_user_info",
                "description": """
                            Get information about specific users.
                            This function returns location, focus mode, and device information for specified users.
                        """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "users": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "List of users to get information about"
                        },
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_home_settings",
                "description": """
                            Get the current home settings.
                            This function returns the current settings for input selects and booleans in the home.
                        """,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
        },
        {
            "type": "function",
            'function': {
                'name': 'search_music',
                'description': """
                    Search the user's Apple Music library for a song/album/artist or playlist.
                    This function requires 'media_type' to be specified AND one of optional parameters 
                    'name', 'artist', 'album' to be specified.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the song to search for "
                        },
                        "media_type": {
                            "type": "string",
                            "description": "Type of media searching for (artist, album, track, radio, playlist)"
                        },
                        "artist": {
                            "type": "string",
                            "description": "The Artist name to search for"
                        },
                        "album": {
                            "type": "string",
                            "description": "The album name to search for"
                        },
                        "limit": {
                            "type": "number",
                            "description": "The number of results to return"
                        },
                    },
                    "required": ["media_type"]
                }
            },
        },

        {
            "type": "function",
            'function': {
                'name': 'play_music',
                'description': """
                Play a song/album/artist or playlist from the user's Apple Music library.
            """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "speakers": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "List of speakers to play music on"
                        },
                        "media_type": {
                            "type": "string",
                            "description": "Type of media searching for (artist, album, track, radio, playlist)"
                        },
                        "media_id": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "A list of URIs of the media to play"
                        },

                    },
                    "required": ["speakers", "media_type", "media_id"]
                }
            },
        },
    ]

    return tool


def define_buzzer_desk_functions():
    tool = [
        {
            "type": "function",
            "function": {
                "name": "play_buzzer",
                "description": """
                Play a buzzer song on a specific entity.
                This function will play the specified song on the buzzer entity provided.
            """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "The ID of the buzzer entity to play the song on"
                        },
                        "song_str": {
                            "type": "string",
                            "description": "The song to play on the buzzer. Can be a predefined song or a custom RTTL string."
                        },
                    },
                    "required": ["entity_id", "song_str"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "notify_desk",
                "description": """
                Notify a desk with an RGB light based on the person and room.
                This function will turn on the notification light on the specified desk
                for the given person in the specified room.
            """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "room": {
                            "type": "string",
                            "description": "The room where the desk is located"
                        },
                        "person": {
                            "type": "string",
                            "description": "The person whose desk will be notified"
                        },
                    },
                    "required": ["room", "person"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "adjust_desk_height",
                "description": """
            Adjust a user's desk height with either a preset or custom height in inches.
            This function will adjust the height of the specified desk for the given user.
            IMPORTANT: Either a preset or custom height can be specified, but not both.
        """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "room": {
                            "type": "string",
                            "description": "The room where the desk is located"
                        },
                        "person": {
                            "type": "string",
                            "description": "The person whose desk will be activated"
                        },
                        "preset": {
                            "type": "string",
                            "description": "The Preset name to adjust the desk to i.e.'sitting', 'standing'. The default is 'sitting'"
                        },
                        "desk_height": {
                            "type": "number",
                            "description": "The custom height in inches to adjust the desk to. Default is None."
                        },
                    },
                    "required": ["room", "person"]
                }
            }
        },
    ]

    return tool


def define_master_room_functions():
    tool = [
        {
            "type": "function",
            "function": {
                "name": "control_user_overrides",
                "description": """
                    Control user-specific overrides for devices.
                    This function will execute the given command on user-specific device overrides in a specified area.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app": {
                            "type": "string",
                            "description": "App to control the overrides for"
                        },
                        "command": {
                            "type": "string",
                            "description": "turn_on or turn_off"
                        },
                        "area": {
                            "type": "string",
                            "description": "The area where the overrides are applied"
                        },
                        "delay_execution": {
                            "type": "number",
                            "description": "The number of seconds to delay the execution of the command"
                        },
                    },
                    "required": ["app", "command", "area"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "control_master_overrides",
                "description": """
                    Control master overrides for devices.
                    This function will execute the given command on master device overrides.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app": {
                            "type": "string",
                            "description": "App to control the overrides for"
                        },
                        "command": {
                            "type": "string",
                            "description": "turn_on or turn_off"
                        },
                        "delay_execution": {
                            "type": "number",
                            "description": "The number of seconds to delay the execution of the command"
                        },
                    },
                    "required": ["app", "command"]
                }
            }
        },
    ]

    return tool


def define_get_master_room_functions():
    tool = [
        {
            "type": "function",
            "function": {
                "name": "get_user_overrides",
                "description": """
                    Control user-specific overrides for devices.
                    This function will execute the given command on user-specific device overrides in a specified area.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app": {
                            "type": "string",
                            "description": "App to control the overrides for"
                        },
                    },
                    "required": ["app"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_master_overrides",
                "description": """
                    Control master overrides for devices.
                    This function will execute the given command on master device overrides.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app": {
                            "type": "string",
                            "description": "App to control the overrides for"
                        },
                    },
                    "required": ["app"]
                }
            }
        },
    ]

    return tool


def define_base_tools():
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_internet",
                "description": """
                    Search the internet for the given query.
                    This function performs a search using a specified search engine API and returns the results.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to look up on the internet"
                        },
                        "api_key": {
                            "type": "string",
                            "description": "API key for the search engine"
                        }
                    },
                    "required": ["query", "api_key"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_youtube_video",
                "description": """
                    Retrieve a YouTube video based on a search term.
                    This function performs a search on YouTube and returns the URL of the video.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_term": {
                            "type": "string",
                            "description": "The term to search for on YouTube"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "The maximum number of results to return"
                        }
                    },
                    "required": ["search_term"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "db_agent",
                "description": """
                Query a specified database.
                This function employs an AI Agent to search and answer questions in a Database. Only two db_agent 
                choices are available, 'home-db-agent' and 'hass-db-agent'.
            """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "db_agent": {
                            "type": "string",
                            "description": "The database to query (only two choices, 'home-db-agent', 'hass-db-agent')"
                        },
                        "query": {
                            "type": "string",
                            "description": "The actual SQL query to execute"
                        }
                    },
                    "required": ["db_agent", "query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "log_user_preferences",
                "description": """
            Adds an entry to the assistant vector store that logs a user's preference and when to use it and why. Be
            as descriptive as possible for the user's preference and when to use it. This will help the assistant
            understand the user's preferences and when to use them.
        """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user": {
                            "type": "string",
                            "description": "The name of the user whose preference is being logged"
                        },
                        "app": {
                            "type": "string",
                            "description": """The name of the app for which the preference is being logged. 
                            (e.g. 'lights', 'workstation')"""
                        },
                        "category": {
                            "type": "string",
                            "description": "The category of the preference (e.g. 'Hue-Color', "
                                           "'Brightness', 'Volume Level', 'Music')"
                        },
                        "preferences": {
                            "type": "string",
                            "description": "The user's preference for the category"
                        },
                        "when_to_use": {
                            "type": "string",
                            "description": "When the user prefers to use the preference"
                        }
                    },
                    "required": ["user", "app", "category", "preferences", "when_to_use"]
                }
            }
        },

        {
            "type": "function",
            "function": {
                "name": "run_master_on_automation",
                "description": """
            Run the main automation for each app. i.e. perform the main automation for lights, workstation, etc.
        """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app": {
                            "type": "string",
                            "description": "The app to control (e.g. 'lights', 'workstation')"
                        },
                        "delay_execution": {
                            "type": "number",
                            "description": "The number of seconds to delay the execution of the command"
                        },
                        "room": {
                            "type": "string",
                            "description": "The room to control the automation in"
                        },
                        'override': {
                            "type": "boolean",
                            "description": "Override the automation if there are any constraints"
                        },
                        "kwargs": {
                            "type": "object",
                            "description": "Additional keyword arguments for the command"
                        }
                    },
                    "required": ["app", "room", "override"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "run_master_off_automation",
                "description": """
        Run the main 'OFF' automation for each app. i.e. perform the 'turn off' function for the main automation for 
        lights, workstation, etc.
    """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app": {
                            "type": "string",
                            "description": "The app to control (e.g. 'lights', 'workstation')"
                        },
                        "delay_execution": {
                            "type": "number",
                            "description": "The number of seconds to delay the execution of the command"
                        },
                        "room": {
                            "type": "string",
                            "description": "The room to control the automation in"
                        },
                        'override': {
                            "type": "boolean",
                            "description": "Override the automation if there are any constraints"
                        },
                        "kwargs": {
                            "type": "object",
                            "description": "Additional keyword arguments for the command"
                        }
                    },
                    "required": ["app", "room", "override"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generate_image",
                "description": """
        Creates an image based on the given text using the highly advanced DALL-E-3 model.
    """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "A description of the image to generate"
                        },
                    },
                    "required": ["prompt"]
                }
            }
        },

    ]

    return tools


def get_tools(tool_names):
    tools = []

    tool_dict = {
        "command_matching_entities": define_command_matching_entities,
        "get_matching_entities": define_get_matching_entities,
        "shortcut_functions": define_shortcut_functions,
        "buzzer_desk_functions": define_buzzer_desk_functions,
        "master_room_functions": define_master_room_functions,
        "get_master_room_functions": define_get_master_room_functions,
        "base_tools": define_base_tools
    }
    if tool_names == 'all':
        tool_names = list(tool_dict.keys())

    for tool_name in tool_names:
        tool_function = tool_dict.get(tool_name)
        if tool_function is not None:
            tools.extend(tool_function())
    return tools
