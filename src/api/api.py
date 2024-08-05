"""The main server file for the LangChain server."""
from typing import Any
import uuid
import fsspec
from fsspec.utils import get_protocol
from fastapi import FastAPI
from langserve import add_routes
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_community.vectorstores import VectorStore
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_core.vectorstores.in_memory import InMemoryVectorStore
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import AzureOpenAIEmbeddings
from models import Settings, AgentResponse
from utils import SmartAgentFactory
from agents import Smart_Agent

def deep_rag_search(question: str) -> Any | str | None:
    protocol: str = get_protocol(url=settings.smart_agent_prompt_location)
    fs: fsspec.AbstractFileSystem = fsspec.filesystem(protocol=protocol)
    session_id = str(object=uuid.uuid4())
    agent: Smart_Agent = SmartAgentFactory.create_smart_agent(
        fs=fs, settings=settings, session_id=session_id)
    agent_response: AgentResponse = agent.run(
        user_input=question, conversation=[], stream=False)
    return agent_response.response

class Server:
    def __init__(self, vector_store: VectorStore, app: FastAPI):
        self.vector_store = vector_store
        self.app = app
        add_routes(
            app=app,
            runnable= RunnableLambda(
                func=lambda question: vector_store.search(query=str(object=question), search_type="similarity")),
            path="/vectorRAG",
        )

        add_routes(
            app=app,
            runnable=RunnablePassthrough() | RunnableLambda(
                func=lambda question: deep_rag_search(question=str(object=question))),
            path="/deepRAG",
        )

if __name__ == "__main__":
    import uvicorn

    app = FastAPI(
        title="LangChain Server",
        version="1.0",
        description="A simple api server using Langchain's Runnable interfaces",
    )
    settings: Settings = Settings(_env_file=".env")  # type: ignore
    embeddings = AzureOpenAIEmbeddings(
        api_key=settings.openai_key,
        api_version=settings.openai_api_version,
        azure_endpoint=settings.openai_endpoint,
        model=settings.openai_embedding_deployment,
    )
    azureSearch = AzureSearch(azure_search_endpoint=settings.azure_search_endpoint,
                          azure_search_key=settings.azure_search_key,
                          index_name=settings.azure_search_index_name,
                          embedding_function=embeddings)
    # azureSearch = InMemoryVectorStore(
    #     embedding=FakeEmbeddings(size=1568),
    # )

    server = Server(vector_store=azureSearch, app=app)

    uvicorn.run(app=server.app, host="localhost", port=8000)