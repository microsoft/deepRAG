"""The main server file for the LangChain server."""
from typing import Any
import uuid
import fsspec
from fsspec.utils import get_protocol
from fastapi import FastAPI
from langserve import add_routes
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_core.embeddings import FakeEmbeddings
from langchain_core.vectorstores.in_memory import InMemoryVectorStore
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


app = FastAPI(
    title="LangChain Server",
    version="1.0",
    description="A simple api server using Langchain's Runnable interfaces",
)

settings: Settings = Settings(_env_file=".env")  # type: ignore
azureSearch = InMemoryVectorStore(
    embedding=FakeEmbeddings(size=1568),
)

add_routes(
    app=app,
    runnable=azureSearch.as_retriever(),
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

    uvicorn.run(app=app, host="localhost", port=8000)
