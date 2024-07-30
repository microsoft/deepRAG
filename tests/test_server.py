from langserve.client import RemoteRunnable
from api import app

def test_server_response() -> None:
    import uvicorn
    uvicorn.run(app=app, host="localhost", port=8000)
    client = RemoteRunnable(url="http://localhost:8000/vectorRAG")
    response = client.invoke(input="What is a vector?")  # Replace with your API endpoint
    assert response is not None  # Replace with the expected status code
