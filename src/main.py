import os
import logging
import yaml
from typing import Any
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from agents.agent_configuration import AgentConfiguration, agent_configuration_from_dict
from functions.search_vector_function import SearchVectorFunction
from agents.smart_agent.smart_agent import Smart_Agent

env_path = Path('..') / '.env'
load_dotenv(dotenv_path=env_path)

with open(file=os.environ.get("SMART_AGENT_PROMPT_LOCATION"), mode="r", encoding="utf-8") as file:
        agent_config_data = yaml.safe_load(stream=file)
        agent_config: AgentConfiguration = agent_configuration_from_dict(data=agent_config_data)

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

agent = Smart_Agent(
    logger=logging,
    client=client,
    agent_configuration=agent_config,
    search_vector_function = search_vector_function
)

agent_response = agent.run(user_input="What is the slogan of NESCAFE?", conversation=[], stream=False)
print(agent_response)