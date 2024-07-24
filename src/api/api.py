"""The main server file for the LangChain server."""
from fastapi import FastAPI
from langserve import add_routes
from langchain_community.vectorstores.azuresearch import AzureSearch

app = FastAPI(
    title="LangChain Server",
    version="1.0",
    description="A simple api server using Langchain's Runnable interfaces",
)

azureSearch = AzureSearch(
    azure_search_endpoint="https://langchain.search.windows.net/",
    azure_search_key="",
    index_name="azureblob-index",
    embedding_function="use",
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
