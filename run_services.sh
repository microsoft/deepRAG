#!/bin/bash  

# Run the first Python module  
python -m src.api.agent_service &  

# Run the Streamlit application  
streamlit run src/app/copilot.py
