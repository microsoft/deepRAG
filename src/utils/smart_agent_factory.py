import redis
import yaml
import fsspec
from logging import Logger
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from distributed_cache.cache import Cache
from functions.search_vector_function import SearchVectorFunction
from models.agent_configuration import AgentConfiguration, agent_configuration_from_dict
from models.settings import Settings
from services.history import History
from agents.smart_agent.smart_agent import Smart_Agent
from fsspec.implementations.local import LocalFileSystem

class SmartAgentFactory:
    @staticmethod
    def create_smart_agent(settings: Settings, session_id: str) -> Smart_Agent:
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
                logger=Logger(name="search_vector_function"),
                search_client=search_client,
                client=client,
                model=settings.openai_embedding_deployment,
                image_directory=settings.smart_agent_image_path
        )

        redis_client: Cache = redis.Redis(
                host=settings.azure_redis_endpoint,
                port=6380,
                ssl=True,
                db=0,
                password=settings.azure_redis_key,
                decode_responses=True
        )

        fs: fsspec.AbstractFileSystem = fsspec.filesystem(protocol="file")
        history: History = History(session_id=session_id, cache=redis_client)
        return Smart_Agent(
            logger=Logger(name="smart_agent"),
            client=client,
            agent_configuration=agent_config,
            search_vector_function = search_vector_function,
            history = history,
            fs=LocalFileSystem(),
        )