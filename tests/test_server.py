import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, List, Optional
from langserve.client import RemoteRunnable
from api.api import app
import pytest
import uvicorn
from fastapi import FastAPI

port = 8000
host = "127.0.0.1"
baseUrl: str = f"http://{host}:{port}"

class UvicornTestServer(uvicorn.Server):
    """Uvicorn test server

    Usage:
        @pytest.fixture
        async def start_stop_server():
            server = UvicornTestServer()
            await server.up()
            yield
            await server.down()
    """

    def __init__(self, app: FastAPI, host: str = host, port: int = port) -> None:
        """Create a Uvicorn test server

        Args:
            app (FastAPI, optional): the FastAPI app. Defaults to main.app.
            host (str, optional): the host ip. Defaults to '127.0.0.1'.
            port (int, optional): the port. Defaults to PORT.
        """
        self._startup_done = asyncio.Event()
        super().__init__(config=uvicorn.Config(app=app, host=host, port=port))

    async def startup(self, sockets: Optional[List] = None) -> None:
        """Override uvicorn startup"""
        await super().startup(sockets=sockets)
        print("Server starting!!!!!")
        self.config.setup_event_loop()
        self._startup_done.set()
        print("Server started!!!!!!")

    async def up(self) -> None:
        """Start up server asynchronously"""
        print ("Starting up server")
        self._serve_task: asyncio.Task[None] = asyncio.create_task(coro=self.serve())
        await self._startup_done.wait()

    async def down(self) -> None:
        """Shut down server asynchronously"""
        self.should_exit = True
        await self._serve_task

@app.on_event(event_type="startup")
async def startup_event() -> None:
    print("Starting up server: startup event")

@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[FastAPI, Any]:
    server = UvicornTestServer(app=app)
    await server.up()
    yield app
    await server.down()

@pytest.fixture(scope="session")
async def server() -> AsyncGenerator[UvicornTestServer, Any]:
    server = UvicornTestServer(app=app)
    await server.up()
    yield server
    await server.down()

def test_server_response(server: AsyncGenerator[UvicornTestServer, Any]) -> None:
    print("Testing server response")
    client = RemoteRunnable(url=f"{baseUrl}/vectorRAG")
    response = client.invoke(input="What is a vector?")  # Replace with your API endpoint
    assert response is not None  # Replace with the expected status code
    print("Server response test passed")
