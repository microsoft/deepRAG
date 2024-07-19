"""The main server file for the LangChain server."""
from fastapi import FastAPI
from langchain_core.runnables.base import Runnable
from langchain_openai import ChatOpenAI
from langserve import add_routes
from langchain_core.stores import InMemoryByteStore

from runnables.graph_retrieval.graph_retriever import Retriever as graph_retriever
from runnables.vector_retrieval.vector_retriever import Retriever as vector_retriever

app = FastAPI(
    title="LangChain Server",
    version="1.0",
    description="A simple api server using Langchain's Runnable interfaces",
)

azureSearch = vector_retriever.AzureSearch(
    azure_search_endpoint="https://langchain.search.windows.net/",
    azure_search_key="",
    index_name="azureblob-index",
)
vectorRAG: Runnable = ChatOpenAI(model="gpt-3.5-turbo-0125") \
    | vector_retriever.Retriever(
        vector_store=azureSearch,
        store=InMemoryByteStore(),
        id_key="",
    )
graphRAG: Runnable = ChatOpenAI(model="gtp-4o") \
    | graph_retriever.Retriever(
        index_creator=graph_retriever.GraphIndexCreator(),
        llm=ChatOpenAI("gpt-4o"),
        ontology="The quick brown fox jumps over the lazy dog",
    )

add_routes(
    app,
    runnable=vectorRAG,
    path="/vectorRAG",
)

add_routes(
    app,
    runnable=graphRAG,
    path="/graphRAG",
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
