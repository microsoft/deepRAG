"""The main server file for the LangChain server."""
import uuid
from logging import Logger
from typing import Any
from fastapi import FastAPI
from langserve import add_routes
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from models import Settings, AgentResponse
from utils import SmartAgentFactory
from agents import Smart_Agent
from functions import SearchVectorFunction
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

class Server(FastAPI):
    """The main server class for the LangChain server."""
    def __init__(
        self,
        vector_search: SearchVectorFunction | None = None,
        settings: Settings | None = None,
        session_id: str | None = None) -> None:
        super().__init__(
            title="LangChain Server",
            version="1.0",
            description="A simple api server using Langchain's Runnable interfaces",
        )
        self.__session_id: str = session_id or str(object=uuid.uuid4())
        self.__settings: Settings = settings or Settings(_env_file=".env") # type: ignore
        self.__vector_search: SearchVectorFunction = vector_search or SearchVectorFunction(
            logger=Logger(name="search_vector_function"),
            search_client=SearchClient(
                endpoint=self.__settings.azure_search_endpoint,
                index_name=self.__settings.azure_search_index_name,
                credential=AzureKeyCredential(key=self.__settings.azure_search_key)
            ),
            client=AzureOpenAI(
                azure_endpoint=self.__settings.openai_endpoint,
                api_key=self.__settings.openai_key,
                api_version=self.__settings.openai_api_version
            ),
            model=self.__settings.openai_embedding_deployment,
            image_directory=self.__settings.smart_agent_image_path
        )
        self.__init_routes__()

    def __init_routes__(self) -> None:
        add_routes(
            app=self,
            runnable=RunnableLambda(
                func=lambda question: self.vector_rag_search(question=str(object=question))),
            path="/vectorRAG",
        )
        add_routes(
            app=self,
            runnable=RunnablePassthrough() | RunnableLambda(
                func=lambda question: self.deep_rag_search(question=str(object=question))),
            path="/deepRAG",
        )

    def vector_rag_search(self, question: str) -> Any | str | None:
        return self.__vector_search.search(search_query=question)
    
    def deep_rag_search(self, question: str) -> Any | str | None:
        agent: Smart_Agent = SmartAgentFactory.create_smart_agent(
            settings=self.__settings, session_id=self.__session_id)
        agent_response: AgentResponse = agent.run(
            user_input=question, conversation=[], stream=False)
        return agent_response.response
