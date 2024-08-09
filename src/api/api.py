"""The main server file for the LangChain server."""
from typing import Any
import uuid
import fsspec
from openai import AzureOpenAI
from fsspec.utils import get_protocol
from fastapi import FastAPI
from langserve import add_routes
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from models import Settings, AgentResponse
from utils import SmartAgentFactory
from agents import Smart_Agent
from functions import SearchVectorFunction
from logging import Logger
import ast
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
settings: Settings = Settings(_env_file=".env")  # type: ignore

def deep_rag_search(input) -> Any | str | None:
    question = input['question']
    session_id = input['session_id']
    protocol: str = get_protocol(url=settings.smart_agent_prompt_location)
    fs: fsspec.AbstractFileSystem = fsspec.filesystem(protocol=protocol)
    agent: Smart_Agent = SmartAgentFactory.create_smart_agent(
        fs=fs, settings=settings, session_id=session_id)
    agent_response: AgentResponse = agent.run(
        user_input=question, conversation=[], stream=False)
    SmartAgentFactory.persist_history(smart_agent=agent, session_id=session_id,settings=settings)
    
    return agent_response.response

class Server:
    def __init__(self, app: FastAPI, searchVectorFunction: SearchVectorFunction) -> None:
        self.app = app
        self.searchVectorFunction = searchVectorFunction
        add_routes(
            app=app,
            runnable= RunnableLambda(
                func=lambda input: self.vector_rag_search(input=input)),
            path="/vectorRAG",
        )
        add_routes(
            app=app,
            runnable=RunnablePassthrough() | RunnableLambda(
                func=lambda input: deep_rag_search(input=input)),
            path="/deepRAG",
        )

    def vector_rag_search(self, question: str) -> Any | str | None:
        return self.searchVectorFunction.search(search_query=question)

if __name__ == "__main__":
    import uvicorn

    app = FastAPI(
        title="LangChain Server",
        version="1.0",
        description="A simple api server using Langchain's Runnable interfaces",
    )

    settings: Settings = Settings(_env_file=".env")  # type: ignore

    openai_client = AzureOpenAI(
        azure_endpoint=settings.openai_endpoint,
        api_key=settings.openai_key,
        api_version=settings.openai_api_version
    )

    search_client = SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_index_name,
        credential=AzureKeyCredential(key=settings.azure_search_key)
    )

    search_vector_function = SearchVectorFunction(
        logger=Logger(name="search_vector_function"),
        search_client=search_client,
        client=openai_client,
        model=settings.openai_embedding_deployment,
        image_directory=settings.smart_agent_image_path,
        storage_account_key=settings.azure_storage_account_key,  
        storage_account_name=settings.azure_storage_account_name,  
        container_name=settings.azure_container_name  

    )

    server = Server(app=app, searchVectorFunction=search_vector_function)
    uvicorn.run(app=server.app, host=settings.api_host, port=settings.api_port)