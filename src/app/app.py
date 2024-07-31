import uuid
import streamlit as st
import os
import json
import pandas as pd
import yaml
import fsspec
from typing import LiteralString
from streamlit_extras.add_vertical_space import add_vertical_space
from plotly.graph_objects import Figure as PlotlyFigure
from matplotlib.figure import Figure as MatplotFigure
from models.agent_configuration import AgentConfiguration, agent_configuration_from_dict
from models.agent_response import AgentResponse
from models.settings import Settings
from utils.smart_agent_factory import SmartAgentFactory

# Initialize smart agent with CODER1 persona
settings: Settings = Settings(_env_file=".env") # type: ignore
fs: fsspec.AbstractFileSystem = fsspec.filesystem(protocol="file")
with fs.open(path=settings.smart_agent_prompt_location, mode="r", encoding="utf-8") as file:
    agent_config_data = yaml.safe_load(stream=file)
    agent_config: AgentConfiguration = agent_configuration_from_dict(
        data=agent_config_data)

session_id = str(uuid.uuid4())
agent = SmartAgentFactory.create_smart_agent(fs=fs, settings=settings, session_id=session_id)

st.set_page_config(
    layout="wide", page_title="Smart Research Copilot Demo Application using LLM")
style: LiteralString = f"""
<style>
    .stTextInput {{
      position: fixed;
      bottom: 3rem;
    }}
</style>
"""
st.markdown(body=style, unsafe_allow_html=True)

MAX_HIST = 3
# Sidebar contents
with st.sidebar:

    st.title('Deep RAG AI Copilot')
    st.markdown('''
    ''')
    st.checkbox("Show AI Assistant's internal thought process",
                key='show_internal_thoughts', value=False)

    add_vertical_space(5)
    if st.button('Clear Chat'):

        if 'history' in st.session_state:
            st.session_state['history'] = []
        if 'display_data' in st.session_state:
            st.session_state['display_data'] = {}

    st.markdown("""
### Sample Questions:  
1. Suggest alternative headlines inspired from 'hack it the way you like it' for a new coffee concentrate product launch in Australia targeting young people
2. What is the slogan of NESCAFE?
3. Three separate steps of preparing an iced latte using NESCAFE coffee concentrate
4. Nescaf brand guidelines for creating TikTok content for Gen Z with a focus on natural and authentic imagery
5. Nescaf brand guidelines for creating a storyboard for an iced latte coffee recipe focusing on innovation
          """)
    st.write('')
    st.write('')
    st.write('')

    st.markdown(body='#### Created by James N., 2024')
    if 'history' not in st.session_state:
        st.session_state['history'] = []
    if 'input' not in st.session_state:
        st.session_state['input'] = ""
    if 'display_data' not in st.session_state:
        st.session_state['display_data'] = {}
    if 'question_count' not in st.session_state:
        st.session_state['question_count'] = 0
    if 'solution_provided' not in st.session_state:
        st.session_state['solution_provided'] = False


user_input = st.chat_input(placeholder="You:")
# Conditional display of AI generated responses as a function of user provided prompts
history = st.session_state['history']
display_data = st.session_state['display_data']
question_count = st.session_state['question_count']

if len(history) > 0:
    # purging history
    removal_indices = []
    idx = 0
    running_question_count = 0
    # flag to start including history items in the removal_indices list
    start_counting = False
    for message in history:
        idx += 1
        message = dict(message)
        print("role: ", message.get("role"), "name: ", message.get("name"))
        if message.get("role") == "user":
            running_question_count += 1
            start_counting = True
        if start_counting and (question_count - running_question_count >= MAX_HIST):
            removal_indices.append(idx-1)
        elif question_count - running_question_count < MAX_HIST:
            break

    # remove items with indices in removal_indices
    for index in removal_indices:
        del history[index]
    question_count = 0
    for message in history:
        message = dict(message)

        if message.get("role") == "user":
            question_count += 1
        if message.get("role") != "system" \
            and message.get("role") != "tool" \
                and message.get("name") is None \
        and len(message.get("content") or []) > 0:
            with st.chat_message(name=message["role"]):
                st.markdown(body=message["content"])
        elif message.get("role") == "tool":
            data_item = display_data.get(message.get("tool_call_id"), None)
            if data_item is not None:
                data_item_type = type(data_item)
                if data_item_type is PlotlyFigure:
                    st.plotly_chart(figure_or_data=data_item)
                elif data_item_type is MatplotFigure:
                    st.pyplot(fig=data_item)
                elif data_item_type is pd.DataFrame:
                    st.dataframe(data=data_item)
else:
    response: AgentResponse = agent.run(user_input=None)
    history = response.conversation
    agent_response: str | None = response.response
    with st.chat_message(name="assistant"):
        st.markdown(body=agent_response)
    user_history = []
if user_input:
    st.session_state['solution_provided'] = False
    st.session_state['feedback'] = False
    data: dict = {}
    with st.chat_message(name="user"):
        st.markdown(body=user_input)
        try:
            response = agent.run(user_input=user_input,
                                 conversation=history, stream=False)
            history = response.conversation
            agent_response = response.response
            stream_out: bool = response.streaming
        except Exception as e:
            agent_response = None
            print("error in running agent, error is ", e)
            if 'history' in st.session_state:
                st.session_state['history'] = []
            if 'display_data' in st.session_state:
                st.session_state['display_data'] = {}

    with st.chat_message(name="assistant"):
        json_response = None
        if agent_response:
            if "overall_explanation" in agent_response:
                try:
                    agent_response = agent_response.strip("```json")
                    json_response = json.loads(s=agent_response)
                    st.markdown(body=json_response.get("overall_explanation"))
                except Exception as e:
                    print("exception json load ", e)
                    print(agent_response)
                    st.markdown(body=agent_response)
            if json_response:
                for item in json_response:
                    if item != "overall_explanation":
                        image_path: str = os.path.join(
                            ".\\processed_data", item)
                        st.markdown(body=json_response[item])
                        st.image(image=image_path)

st.session_state['history'] = history
st.session_state['question_count'] = question_count
