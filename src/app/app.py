import sys
import streamlit as st
import os
import json
import logging
import pandas as pd
import yaml
from typing import Any
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from streamlit_extras.add_vertical_space import add_vertical_space
from plotly.graph_objects import Figure as PlotlyFigure
from matplotlib.figure import Figure as MatplotFigure
from functions.search_vector_function import SearchVectorFunction
from agents.smart_agent.smart_agent import Smart_Agent
from agents.agent_configuration import AgentConfiguration

sys.path.append("..")

# Initialize smart agent with CODER1 persona
with open(file=os.environ.get("SMART_AGENT_PROMPT_LOCATION"), mode="r", encoding="utf-8") as file:
        agent_config_data = yaml.safe_load(stream=file)
        agent_config = AgentConfiguration(
            persona=agent_config_data["persona"],
            model=agent_config_data["model"],
            initial_message=agent_config_data["initial_message"],
            name=agent_config_data["name"]
        )

search_client = SearchClient(
    endpoint=os.environ.get("AZURE_SEARCH_ENDPOINT"),
    index_name=os.environ.get("AZURE_SEARCH_INDEX_NAME"),
    credential=AzureKeyCredential(key=os.environ.get("AZURE_SEARCH_KEY"))
)

client = AzureOpenAI(
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
)

search_vector_function = SearchVectorFunction(
        logger=logging,
        search_client=search_client,
        client=client,
        model=os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
)

AVAILABLE_FUNCTIONS: dict[str, Any] = {
    "search": search_vector_function.search
}

FUNCTIONS_SPEC: Any = [
    search_vector_function.search_function_spec
]

agent = Smart_Agent(
    logger=logging,
    client=client,
    agent_configuration=agent_config,
    functions_list=AVAILABLE_FUNCTIONS,
    functions_spec=FUNCTIONS_SPEC
)

st.set_page_config(layout="wide",page_title="Smart Research Copilot Demo Application using LLM")
styl = f"""
<style>
    .stTextInput {{
      position: fixed;
      bottom: 3rem;
    }}
</style>
"""
st.markdown(styl, unsafe_allow_html=True)


MAX_HIST= 3
# Sidebar contents
with st.sidebar:

    st.title('Deep RAG AI Copilot')
    st.markdown('''
    ''')
    st.checkbox("Show AI Assistant's internal thought process", key='show_internal_thoughts', value=False)

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

    st.markdown('#### Created by James N., 2024')
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

        
user_input= st.chat_input("You:")
## Conditional display of AI generated responses as a function of user provided prompts
history = st.session_state['history']
display_data = st.session_state['display_data']
question_count=st.session_state['question_count']
# print("new round-----------------------------------")
# print("question_count: ", question_count)

if len(history) > 0:
    #purging history
    removal_indices =[]
    idx=0
    running_question_count=0
    start_counting=False # flag to start including history items in the removal_indices list
    for message in history:
        idx += 1
        message = dict(message)
        print("role: ", message.get("role"), "name: ", message.get("name"))
        if message.get("role") == "user":
            running_question_count +=1
            start_counting=True
        if start_counting and (question_count- running_question_count>= MAX_HIST):
            removal_indices.append(idx-1)
        elif question_count- running_question_count< MAX_HIST:
            break
            
    # remove items with indices in removal_indices
    # print("removal_indices", removal_indices)
    for index in removal_indices:
        del history[index]
    question_count=0
    # print("done purging history, len history now", len(history ))
    for message in history:
        message = dict(message)
        # if message.get("role") != "system":
        #     print("message: ", message)
        # else:
        #     print("system message here, omitted")

        if message.get("role") == "user":
            question_count +=1
            # print("question_count added, it becomes: ", question_count)   
        if message.get("role") != "system" and message.get("role") != "tool" and message.get("name") is None and len(message.get("content")) > 0:
            with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        elif message.get("role") == "tool":
            data_item = display_data.get(message.get("tool_call_id"), None)
            if  data_item is not None:
                if type(data_item) is PlotlyFigure:
                    st.plotly_chart(data_item)
                elif type(data_item) is MatplotFigure:
                    st.pyplot(data_item)
                elif type(data_item) is pd.DataFrame:
                    st.dataframe(data_item)




else:
    history, agent_response = agent.run(user_input=None)
    with st.chat_message("assistant"):
        st.markdown(agent_response)
    user_history=[]
if user_input:
    st.session_state['solution_provided'] = False
    st.session_state['feedback'] = False
    data: dict = None
    with st.chat_message("user"):
        st.markdown(user_input)
        try:
            # stream_out= False
            stream_out, code, history, agent_response,data = agent.run(user_input=user_input, conversation=history, stream=False)
        except Exception as e:
            agent_response= None
            print("error in running agent, error is ", e)
            if 'history' in st.session_state:
                st.session_state['history'] = []
            if 'display_data' in st.session_state:
                st.session_state['display_data'] = {}

    with st.chat_message("assistant"):
        json_response=None
        if agent_response:
            if "overall_explanation"  in agent_response:
                try:
                    agent_response= agent_response.strip("```json")
                    json_response = json.loads(agent_response)
                    st.markdown(json_response.get("overall_explanation")) 
                except Exception as e:
                    print("exception json load ", e)
                    print(agent_response)
                    st.markdown(agent_response)
            if json_response:
                for item in json_response:
                    if item !="overall_explanation":
                        image_path = os.path.join(".\\processed_data", item)
                        st.markdown(json_response[item])
                        st.image(image_path)


    if data is not None:
        # print("adding data to session state, data is ", data)
        st.session_state['display_data'] = data

st.session_state['history'] = history
# print("question_count at the end of interaction ", question_count)
st.session_state['question_count'] = question_count