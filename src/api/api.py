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
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from typing import List
from azure.search.documents.models import QueryAnswerResult

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
    def __init__(self, search_client: SearchClient, app: FastAPI):
        self.search_client = search_client
        self.app = app
        add_routes(
            app=app,
            runnable= RunnableLambda(
                func=lambda question: self.vector_rag_search(question=str(object=question))),
            path="/vectorRAG",
        )
        add_routes(
            app=app,
            runnable=RunnablePassthrough() | RunnableLambda(
                func=lambda question: deep_rag_search(question=str(object=question))),
            path="/deepRAG",
        )

    def vector_rag_search(self, question: str) -> Any | str | None:
        answers: List[QueryAnswerResult] | None = self.search_client.search(search_text=str(object=question), query_type="simple", search_fields=["topic"], query_answer_threshold=2.0).get_answers()
        return answers if answers is not None and len(answers) > 0 else ["No results"]

if __name__ == "__main__":
    import uvicorn

    app = FastAPI(
        title="LangChain Server",
        version="1.0",
        description="A simple api server using Langchain's Runnable interfaces",
    )
    settings: Settings = Settings(_env_file=".env")  # type: ignore

    service_endpoint = settings.azure_search_endpoint
    index_name = settings.azure_search_index_name
    key = settings.azure_search_key
    search_client = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=AzureKeyCredential(key=key))

    server = Server(search_client=search_client, app=app)
    uvicorn.run(app=server.app, host="localhost", port=8000)