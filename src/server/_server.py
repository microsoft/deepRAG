"""The main server file for the LangChain server."""
from fastapi import FastAPI
from langchain_openai import ChatOpenAI
from langserve import add_routes

app = FastAPI(
    title="LangChain Server",
    version="1.0",
    description="A simple api server using Langchain's Runnable interfaces",
)

add_routes(
    app,
    ChatOpenAI(model="gpt-3.5-turbo-0125"),
    path="/vectorRAG",
)

add_routes(
    app,
    ChatOpenAI(model="gtp-4o"),
    path="/graphRAG",
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
