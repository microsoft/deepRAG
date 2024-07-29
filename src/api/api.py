"""The main server file for the LangChain server."""
from fastapi import FastAPI
from langserve import add_routes
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_core.embeddings import FakeEmbeddings
from langchain_core.vectorstores.in_memory import InMemoryVectorStore

app = FastAPI(
    title="LangChain Server",
    version="1.0",
    description="A simple api server using Langchain's Runnable interfaces",
)

azureSearch = InMemoryVectorStore(
    embedding=FakeEmbeddings(size=1568),
)

add_routes(
    app,
    runnable=azureSearch.as_retriever(),
    path="/vectorRAG",
)

# add_routes(
#     app,
#     runnable=graphRAG,
#     path="/deepRAG",
# )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
