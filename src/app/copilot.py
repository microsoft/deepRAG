import uuid  
import streamlit as st  
import requests  
import os  
from dotenv import load_dotenv  
from streamlit_extras.add_vertical_space import add_vertical_space  
import time
# Load environment variables  
load_dotenv()  
  
# Set up Streamlit page  
st.set_page_config(layout="wide", page_title="Chat Client", page_icon="💬")  
def initialize_chat_session():  
    # Initialize session state  
    max_retries = 3  # Maximum number of retry attempts  
    retry_delay = 2  # Delay between retries in seconds  
    attempt = 0  
  
    while attempt < max_retries:  
        try:  
            # Make initial call to get the assistant's first message  
            response = requests.post(  
                f"{os.getenv('AGENT_SERVICE_URL')}/chat/",  
                json={"session_id": st.session_state['session_id']}  
            )  
            response.raise_for_status()  # Raise an error for bad HTTP status codes  
            response_data = response.json()  
            initial_message = response_data.get("response", "No response received.")  
              
            # Append initial assistant's response to history  
            st.session_state['history'].append({"role": "assistant", "content": initial_message})  
            break  # Exit the loop if successful  
  
        except requests.exceptions.RequestException as e:  
            attempt += 1  
            if attempt < max_retries:  
                time.sleep(retry_delay)  
            else:  
                print(f"Attempt {attempt} failed: {e}. No more retries left.") 
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
    
    st.markdown("1. How does the consent management process work in the Visibility Control Center?")  
    st.markdown("2. What are the detailed descriptions of each onboarding status for carriers?")  
    st.markdown("3. How can I effectively expand my carrier network using the Visibility Hub?")  
    st.markdown("4. What factors affect the visibility index and allocation rating, and how can I improve them?")  
    st.markdown("5. What additional insights can be gained from the Onboarding Status Report, and how can it be utilized effectively?")
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
        f"{os.getenv('AGENT_SERVICE_URL')}/chat/",  
        json={"message": user_input, "session_id": st.session_state['session_id']}  
    )  
    response_data = response.json()  
    assistant_response = response_data.get("response", "No response received.")  
    with st.chat_message("assistant"):
        st.markdown(assistant_response)
        
    # Append assistant's response to history  
    st.session_state['history'].append({"role": "assistant", "content": assistant_response})  

