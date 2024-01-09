import json
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal

import pandas as pd
import requests
import streamlit as st
from databot.PyDatabot import databot_sensors
from dotenv import load_dotenv
from openai.types.beta.threads import Run

from openai_assistant import OpenAIAssistant, FunctionDefinition, FunctionParameter, AssistantThreadMessage


class DatabotOpenAIAssistant(OpenAIAssistant):

    def _get_databot_friendly_names(self) -> List:
        df = pd.DataFrame(data=databot_sensors.values()).sort_values(by="friendly_name")
        f_names = df['friendly_name'].to_list()
        return f_names

    def _get_function_definition(self) -> FunctionDefinition:
        function_definition = FunctionDefinition(
            name="get_databot_values",
            description="""Get sensor values from the databot.  If there are multiple sensor values, a list of sensor names can be provided.
                            This function can only provide information on the current values from the databot.  
                            This function CANNOT describe what the sensor is measuring.
                            """,
            parameters=[
                FunctionParameter(
                    name="sensor_names",
                    description="""List of the friendly human readable sensor value names.""",
                    type="string",
                    required=True,
                    enum_values=get_databot_friendly_names()
                )
            ]
        )
        return function_definition

    def create_assistant(self, name: str, instructions: str | None = None,
                         tools: List[Literal["retrieval", "code_interpreter", "function"]] = ["retrieval"],
                         model: Literal[
                             "gpt-3.5-turbo-1106", "gpt-4-1106-preview"] = "gpt-3.5-turbo-1106",
                         include_files: bool = True):
        assistant_instructions = self.get_assistant_instructions()
        if instructions is None:
            instructions = assistant_instructions

        self.add_function(self._get_function_definition())

        super().create_assistant(name, instructions, tools, model, include_files)

    def __init__(self, api_key: str = None, log_level: int = logging.WARNING):
        super().__init__(api_key=api_key, log_level=log_level)

    def get_assistant_instructions(self) -> str:
        values = databot_sensors.values()
        system_content = f"""
        you are an expert on the databot sensor device.  
        Use the following dictionary to understand how 'data columns' are associated with a sensor name.

        Databot Sensor Dictionary: 
        {json.dumps(list(values), indent=2)} 

        The 'friendly_name' is what humans will call the sensor value. 
        
        The 'data_columns' will be the list of values associated with the sensor name.  
        
        All 'data_columns' associated with a sensor will need to be returned in the response.  

        The 'sensor_name' is the name of the sensor known by the databot.  

        DO NOT call the function `get_databot_values` unless the user needs the current sensor value.

        Any temperature values will be in celsius, so convert the temperature to fahrenheit and show both values with their units.
        """
        return system_content

    def handle_requires_action(self, tool_call, function_name: str, function_args: str) -> str:
        rtn_value = None
        try:
            print(tool_call)
            print(function_name)
            print(function_args)
            args = json.loads(function_args)
            st.sidebar.write(f"Call function: {function_name}")
            st.sidebar.write(f"Arguments: {function_args}")

            output = get_databot_values(args['sensor_names'])
            st.sidebar.write("Document returned to OpenAI")
            st.sidebar.json(output)
            print(output)
            rtn_value = output

        except Exception as exc:
            logging.error(exc)
            st.sidebar.error(str(exc))
            rtn_value = "Unknown"

        return rtn_value

    def run_response_callback(self, the_run: Run):
        super().run_response_callback(the_run)
        st.sidebar.write(the_run.status)


def get_assistant() -> DatabotOpenAIAssistant:
    if "openai_assistant" not in st.session_state:
        assistant = DatabotOpenAIAssistant(log_level=logging.INFO)
        assistant.create_assistant(name="Databot Assistant",
                                   tools=['function', 'retrieval', 'code_interpreter'],
                                   instructions="You help answer questions about the databot sensor device and can call function to retrieve values from the databot."
                                   )
        st.session_state["openai_assistant"] = assistant

    return st.session_state["openai_assistant"]


@dataclass
class ChatMessage:
    role: str
    content: str


def show_chat_history():
    for chat in st.session_state.chat_history:
        with st.chat_message(chat.get_role()):
            st.markdown(chat)


def get_databot_values(sensor_names: List) -> str:
    try:
        print(f"Get values for: {sensor_names}")
        url = "http://localhost:8321/"
        response = requests.get(url)
        return json.dumps(response.json())
    except:
        return "There was an error trying to access the databot device.  Make sure it is turned on and running the webserver."


def get_databot_friendly_names() -> List:
    df = pd.DataFrame(data=databot_sensors.values()).sort_values(by="friendly_name")
    f_names = df['friendly_name'].to_list()
    return f_names


def get_function_definition() -> FunctionDefinition:
    function_definition = FunctionDefinition(
        name="get_databot_values",
        description="""Get sensor values from the databot.  If there are multiple sensor values, a list of sensor names can be provided.
                        This function can only provide information on the current values from the databot.  
                        This function CANNOT describe what the sensor is measuring.
                        """,
        parameters=[
            FunctionParameter(
                name="sensor_names",
                description="""List of the friendly human readable sensor value names.""",
                type="string",
                required=True,
                enum_values=get_databot_friendly_names()
            )
        ]
    )
    return function_definition


@contextmanager
def files_in_directory(directory_path):
    path = Path(directory_path)
    if path.is_dir():
        try:
            files = [str(file) for file in path.glob('*') if file.is_file()]
            yield files
        except Exception as e:
            print("An exception occurred: ", str(e))
            yield None
        finally:
            pass  # Add any cleanup code here, if necessary
    else:
        print("Provided path is not a directory.")
        yield None


def setup_sidebar():
    with st.sidebar:
        c1, c2, c3 = st.columns(3)
        with c1:
            upload_files_btn = st.button(label="Upload Files")
        with c2:
            delete_files_btn = st.button(label="Delete Files")
        # with c3:
        #     show_assistant_files = st.button(label="Show Assistant Files")
        # with c4:
        #     debug_btn = st.button(label="Debug")

        with c3:
            delete_assistant_btn = st.button(label="Delete Assistant")

        if upload_files_btn:
            st.write("Uploading")
            # since we are uploading the entire directory - to keep things in sync
            # first delete all files that are currently in openai
            get_assistant().delete_files()

            with files_in_directory('./databot_docs') as files:
                for file_path in files:
                    st.write(file_path)
                    get_assistant().add_file_to_assistant(file_path=file_path)

        if delete_files_btn:
            st.write("Deleting files...")
            get_assistant().delete_files()

            files = get_assistant().get_assistant_files(refresh_from_openai=False)
            if len(files) > 0:
                st.warning("Some files were not deleted")
            st.write("Deleting files...Done")


        if delete_assistant_btn:
            st.write("Deleting Assistant...")
            get_assistant().delete_assistant()
            st.write("Deleting Assistant...Done")


def handle_userinput(user_content: str):
    """
    :param user_content: The content provided by the user as input.
    :return: None

    This method takes in user content as input and processes it to generate a response. It uses the `run_conversation` function from the `databot_chat` module to perform the conversation. If the conversation is successful, it retrieves the assistant's response and adds it to the chat history. If there is an error, it adds an error message to the chat history.

    Note: This method requires the `streamlit`, `dotenv`, `databot_chat`, `openai`, and `dataclasses` modules to be imported.

    Example usage:

    ```python
    handle_userinput("Hello, how are you?")
    ```
    """
    # user_chat_message = ChatMessage(role="user", content=user_content)
    # st.session_state.chat_history.append(user_chat_message)
    # show_chat_history()

    try:
        get_assistant().submit_user_prompt(user_content, wait_for_completion=True)
        messages: List[AssistantThreadMessage] = get_assistant().get_assistant_conversation()
        for message in messages:
            if message.get_id() not in st.session_state.chat_history_ids:
                st.session_state.chat_history.append(message)
                st.session_state.chat_history_ids.add(message.get_id())

        show_chat_history()


    except Exception as e:
        with st.chat_message("assistant"):
            st.write(f"Oops something went wrong: {e}")


def main():
    st.set_page_config(page_title="Chat with a databot",
                       page_icon=":speech_balloon:",
                       layout="centered",
                       initial_sidebar_state="expanded")

    setup_sidebar()

    with st.container():
        st.title(":speech_balloon: Chat Databot")
        st.caption("Chat with your databot. Powered by OpenAI and DroneBlocks")
        st.divider()

    if not 'chat_history' in st.session_state:
        st.session_state.chat_history = []
        st.session_state.chat_history_ids = set()

    user_question = st.chat_input("Ask databot:")
    if user_question:
        # with st.spinner("Running conversation..."):
        #     handle_userinput(user_question)
        handle_userinput(user_question)


if __name__ == '__main__':
    load_dotenv()

    main()
