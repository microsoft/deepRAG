import os  
import uuid  
from pathlib import Path  
from dotenv import load_dotenv  
from openai import AzureOpenAI  
from fastapi import FastAPI, HTTPException, Request  
import sys
from src.agents.agent_manager import Agent_Runner  
from src.utils.session_state import SessionState  

load_dotenv()  
  
session_state = SessionState()  
agent_runner = Agent_Runner(session_state)  
  
client = AzureOpenAI(  
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),  
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT")  
)  
  
app = FastAPI()  
  
@app.post("/chat/")  
async def chat(request: Request):  
    data = await request.json()  
    message = data.get("message")  
    session_id = data.get("session_id", str(uuid.uuid4()))  

    response = agent_runner.run(message, session_id)  
    return {"response": response, "session_id": session_id}  
          
if __name__ == "__main__":  
    import uvicorn  
    uvicorn.run(app, host="0.0.0.0", port=8000)  