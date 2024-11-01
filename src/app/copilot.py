import uuid  
import streamlit as st  
import requests  
import os  
from dotenv import load_dotenv  
from streamlit_extras.add_vertical_space import add_vertical_space  
  
# Load environment variables  
load_dotenv()  
  
# Set up Streamlit page  
st.set_page_config(layout="wide", page_title="Chat Client", page_icon="💬")  
def initialize_chat_session():
    # Initialize session state  

    # Make initial call to get the assistant's first message  
    response = requests.post(  
        f"http://{os.getenv('API_HOST')}:{os.getenv('API_PORT')}/chat/",  
        json={"session_id": st.session_state['session_id']}  
    )  
    response_data = response.json()  
    initial_message = response_data.get("response", "No response received.")  
        
    # Append initial assistant's response to history  
    st.session_state['history'].append({"role": "assistant", "content": initial_message})  

if 'history' not in st.session_state:  
    st.session_state['history'] = []  

if 'session_id' not in st.session_state:  
    st.session_state['session_id'] = str(uuid.uuid4()) 
    initialize_chat_session()

    
    
# Sidebar setup  
with st.sidebar:  
    st.title("Chat Client")  
    add_vertical_space(5)  
    if st.button('Clear Chat'):  
        st.session_state['history'] = [] 
        del st.session_state['session_id']
        st.session_state['session_id'] = str(uuid.uuid4()) 
        initialize_chat_session()
    st.markdown("### Sample Questions:")  
    st.markdown("1. Can you help me with my flight booking?")  
    st.markdown("2. Can you check my hotel reservation?")  
  
# Chat input  
user_input = st.chat_input("You:")  
  
# Conditional display of chat messages  
history = st.session_state['history']  
  
if len(history) > 0:  
    for message in history:  
        with st.chat_message(message['role']):  
            st.markdown(message['content'])  
  
# Handle user input  
if user_input:  
    with st.chat_message("user"):
        st.markdown(user_input)
    # Append user's message to history  
    st.session_state['history'].append({"role": "user", "content": user_input})  
  
    # Send user input to backend and get response  
    response = requests.post(  
        f"http://{os.getenv('API_HOST')}:{os.getenv('API_PORT')}/chat/",  
        json={"message": user_input, "session_id": st.session_state['session_id']}  
    )  
    response_data = response.json()  
    assistant_response = response_data.get("response", "No response received.")  
    with st.chat_message("assistant"):
        st.markdown(assistant_response)
        
    # Append assistant's response to history  
    st.session_state['history'].append({"role": "assistant", "content": assistant_response})  

