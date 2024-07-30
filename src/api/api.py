"""The main server file for the LangChain server."""
import uuid
from fastapi import FastAPI
from langserve import add_routes
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_community.vectorstores.azuresearch import AzureSearch
from models.settings import Settings
from models.agent_response import AgentResponse
from utils.smart_agent_factory import SmartAgentFactory
from agents.smart_agent.smart_agent import Smart_Agent

def deep_rag_search(question:str):
    session_id = str(object=uuid.uuid4())
    agent: Smart_Agent = SmartAgentFactory.create_smart_agent(settings=settings, session_id=session_id)
    agent_response: AgentResponse = agent.run(user_input=question, conversation=[], stream=False)

    return agent_response.response

app = FastAPI(
    title="LangChain Server",
    version="1.0",
    description="A simple api server using Langchain's Runnable interfaces",
)

settings: Settings = Settings()

azureSearch = AzureSearch(
    azure_search_endpoint="https://langchain.search.windows.net/",
    azure_search_key="",
    index_name="azureblob-index",
    embedding_function="use",
)

add_routes(
    app=app,
    runnable=azureSearch.as_retriever(),
    path="/vectorRAG",
)

add_routes(
    app=app,
    runnable= RunnablePassthrough() | RunnableLambda(lambda question: deep_rag_search(question=question)),
    path="/deepRAG",
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
