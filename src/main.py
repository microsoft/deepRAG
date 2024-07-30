import logging
import yaml
from pathlib import Path
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from models.agent_configuration import AgentConfiguration, agent_configuration_from_dict
from functions.search_vector_function import SearchVectorFunction
from agents.smart_agent.smart_agent import Smart_Agent
from models.settings import Settings

env_path = Path('..') / '.env'
settings: Settings = Settings(_env_file=env_path)

with open(file=settings.smart_agent_prompt_location, mode="r", encoding="utf-8") as file:
        agent_config_data = yaml.safe_load(stream=file)
        agent_config: AgentConfiguration = agent_configuration_from_dict(data=agent_config_data)

search_client = SearchClient(
    endpoint=settings.azure_search_endpoint,
    index_name=settings.azure_search_index_name,
    credential=AzureKeyCredential(key=settings.azure_search_key)
)

client = AzureOpenAI(
    api_key=settings.openai_key,
    api_version=settings.openai_api_version,
    azure_endpoint=settings.openai_endpoint,
)

search_vector_function = SearchVectorFunction(
        logger=logging,
        search_client=search_client,
        client=client,
        model=settings.openai_embedding_deployment,
        image_directory=settings.smart_agent_image_path
)

agent = Smart_Agent(
    logger=logging,
    client=client,
    agent_configuration=agent_config,
    search_vector_function = search_vector_function
)

agent_response = agent.run(user_input="What is the slogan of NESCAFE?", conversation=[], stream=False)
print(agent_response)