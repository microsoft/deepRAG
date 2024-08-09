from typing import Awaitable
import redis
import yaml
import fsspec
from logging import Logger
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from distributedcache import CacheProtocol
from functions import SearchVectorFunction
from models import AgentConfiguration, agent_configuration_from_dict
from models import Settings
import base64
import pickle
from agents import Smart_Agent
from redis.commands.core import BasicKeyCommands
from redis.typing import KeyT, ResponseT, AbsExpiryT, ExpiryT, EncodableT

class SmartAgentFactory:
    @staticmethod
    def create_smart_agent(fs: fsspec.AbstractFileSystem, settings: Settings, session_id: str) -> Smart_Agent:
        with fs.open(path=settings.smart_agent_prompt_location, mode="r", encoding="utf-8") as file:
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
            image_directory=settings.smart_agent_image_path,  
            storage_account_key=settings.azure_storage_account_key,  
            storage_account_name=settings.azure_storage_account_name,  
            container_name=settings.azure_container_name  
        )  

        redis_client: CacheProtocol[KeyT, ResponseT, EncodableT, ExpiryT, AbsExpiryT] = redis.Redis(
            host=settings.azure_redis_endpoint,
            port=6380,
            ssl=True,
            db=0,
            password=settings.azure_redis_key,
            decode_responses=True
        )
        init_history=[]
        if session_id:

            raw_hist = redis_client.get(session_id)
            init_history = pickle.loads(base64.b64decode(s=raw_hist)) if raw_hist else []
        return Smart_Agent(
            logger=Logger(name="smart_agent"),
            client=client,
            agent_configuration=agent_config,
            search_vector_function = search_vector_function,
            init_history=init_history,
            fs=fs,
            image_directory=settings.smart_agent_image_path,
        )
    @staticmethod
    def persist_history(smart_agent:Smart_Agent, session_id: str, settings: Settings) -> None:
        redis_client: CacheProtocol[KeyT, ResponseT, EncodableT, ExpiryT, AbsExpiryT] = redis.Redis(
            host=settings.azure_redis_endpoint,
            port=6380,
            ssl=True,
            db=0,
            password=settings.azure_redis_key,
            decode_responses=True
        )
        history = smart_agent._conversation   
        redis_client.set(name=session_id, value=base64.b64encode(pickle.dumps(history)))
        redis_client.expire(name=session_id, time=3600)