import yaml  
from typing import Any  
import os  
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker, relationship  
from datetime import datetime  
import random  
from dotenv import load_dotenv  
from openai import AsyncAzureOpenAI  
from pathlib import Path  
import json  
from scipy import spatial  # for calculating vector similarities for search  
# Load YAML file  
import yaml
# Load YAML file  
import asyncio
import time
import aiohttp
import urllib.request  
import json  
import os  
import ssl  

def load_entity(file_path, entity_name):  
    with open(file_path, 'r') as file:  
        data = yaml.safe_load(file)  
    for entity in data['agents']:  
        if entity.get('name') == entity_name:  
            return entity  
    return None  
  
# Load environment variables  
env_path = Path('./') / '.env'  
load_dotenv(dotenv_path=env_path)  
async_client = AsyncAzureOpenAI(  
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),  
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),  
) 
INTENT_SHIFT_API_KEY = os.environ.get("INTENT_SHIFT_API_KEY")
INTENT_SHIFT_API_URL = os.environ.get("INTENT_SHIFT_API_URL") 
INTENT_SHIFT_API_DEPLOYMENT=os.environ.get("INTENT_SHIFT_API_DEPLOYMENT")
chat_deployment=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT")
prompt_template = load_entity('prompt.yaml', "classifier_agent")["persona"]

async def detect_intent_change(job_description, conversation):
        start_time = time.time()
        conversation= [{"role":"user", "content":prompt_template.format(job_description=job_description, conversation=conversation)}]

        response = await async_client.chat.completions.create(  
            model=chat_deployment,  
            messages=conversation,  
        )  
        end_time = time.time()  
        print(f"Job succeeded in {end_time - start_time:.2f} seconds.") 
        return response.choices[0].message.content.lower()
  
def allowSelfSignedHttps(allowed):  
    if allowed and not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None):  
        ssl._create_default_https_context = ssl._create_unverified_context  
  
allowSelfSignedHttps(True)  
  
async def detect_intent_change_2(current_domain, conversation): 
    start_time = time.time() 
    # Prepare the request data  
# Format the data according to the ServiceInput schema  
    value = f"##current_domain:{current_domain}\n##conversation:\n{conversation}"  
    data = {  
        "input_data": {  
            "columns": ["input_string"],  
            "index": [0],  
            "data": [[value]]  # Wrap value in a list to match the expected structure  
        },  
        "params": {}  
    }  
    
    # Encode the data as JSON  
    body = json.dumps(data).encode('utf-8')  
    
    # Check if the API key is provided  
    if not INTENT_SHIFT_API_KEY:  
        raise Exception("A key should be provided to invoke the endpoint")  
    
    # Set the headers  
    headers = {  
        'Content-Type': 'application/json',  
        'Authorization': f'Bearer {INTENT_SHIFT_API_KEY}',  
        'azureml-model-deployment': INTENT_SHIFT_API_DEPLOYMENT  
    }  
    
    # Make the request  
    req = urllib.request.Request(INTENT_SHIFT_API_URL, body, headers=headers)  
  
  
    try:  
        response = urllib.request.urlopen(req)  
        result = response.read()
        result = json.loads(result)[0]['0'].strip()
        print("current domain ", current_domain)
        print("conversation ", value)
        print(result)
        end_time = time.time()
        print(f"Job succeeded in {end_time - start_time:.2f} seconds.")
        if result != "no_change" and result!=current_domain:
            return "yes"
        else:
            return result
        
    except urllib.error.HTTPError as error:  
        print("The request failed with status code: " + str(error.code))  
        print(error.info())  
        print(error.read().decode("utf8", 'ignore'))  
        return None  
