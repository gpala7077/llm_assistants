import os


def load_assistant_instructions(assistant, file_name):
    # Perform walkthrough assistant folder and look for file
    assistant_files = os.listdir(f"/assistants/{assistant}")
    for file in assistant_files:
        if file_name in file:
            with open(f"/assistants/{assistant}/{file}", 'r') as f:
                return f.read()
