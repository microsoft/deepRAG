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
from langserve.client import RemoteRunnable
from utils import SmartAgentFactory
from agents import Smart_Agent
from models import (
    AgentConfiguration,
    agent_configuration_from_dict,
    AgentResponse,
    Settings)
import fsspec
from fsspec.utils import get_protocol

# Initialize smart agent with CODER1 persona
settings: Settings = Settings(_env_file="../../.env")  # type: ignore
protocol: str = get_protocol(url=settings.smart_agent_prompt_location)
fs: fsspec.AbstractFileSystem = fsspec.filesystem(protocol=protocol)
with fs.open(path=settings.smart_agent_prompt_location, mode="r", encoding="utf-8") as file:
    agent_config_data = yaml.safe_load(stream=file)
    agent_config: AgentConfiguration = agent_configuration_from_dict(
        data=agent_config_data)

if 'session_id' in st.session_state:
    session_id= st.session_state['session_id']
else:
    session_id = str(object=uuid.uuid4())
    st.session_state['session_id'] = session_id
# agent: Smart_Agent = SmartAgentFactory.create_smart_agent(fs=fs, settings=settings, session_id=session_id)
remoteAgent = RemoteRunnable(f"http://{settings.api_host}:{settings.api_port}/deepRAG")
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

    st.title(body='Deep RAG AI Copilot')
    st.markdown(body='''
    ''')
    st.checkbox(label="Show AI Assistant's internal thought process",
                key='show_internal_thoughts', value=False)

    add_vertical_space(num_lines=5)
    if st.button(label='Clear Chat'):

        if 'history' in st.session_state:
            st.session_state['history'] = []
        if 'session_id' in st.session_state:
            del st.session_state['session_id'] 

    st.markdown(body="""
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
    if 'input' not in st.session_state:
        st.session_state['input'] = ""
    if 'question_count' not in st.session_state:
        st.session_state['question_count'] = 0


user_input: str | None = st.chat_input(placeholder="You:")
# Conditional display of AI generated responses as a function of user provided prompts
conversation=None
if user_input:
    try:
        output = remoteAgent.invoke(input={"question":user_input, "session_id":session_id})
        agent_response = output.get("agent_response")
        conversation = output.get("conversation")
                
    except Exception as e:
        agent_response = None
        print("error in running agent, error is ", e)
    if conversation:
        for message in conversation:
            with st.chat_message(name=message.get("role")):
                st.markdown(body=message.get("content"))

    with st.chat_message(name="user"):
        st.markdown(body=user_input)
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
                        print("item is ", item)
                        
                        image_path: str = os.path.join(
                            settings.smart_agent_image_path, item)
                        st.markdown(body=json_response[item])
                        st.image(image=image_path)
