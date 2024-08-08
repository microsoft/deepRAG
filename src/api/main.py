import uvicorn
from fastapi import FastAPI
from models import Settings
from functions import SearchVectorFunction
from logging import Logger
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
from api import Server

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
    image_directory=settings.smart_agent_image_path
)

server = Server(app=app, searchVectorFunction=search_vector_function)
uvicorn.run(app=server.app, host=settings.api_host, port=settings.api_port)
