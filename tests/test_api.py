import pytest
from typing import Any, List
from langserve.client import RemoteRunnable
from api import Server

def test_vectorRAG_api_happy_path():

    client = RemoteRunnable(url="http://localhost:8000/vectorRAG")
    response: List[Any] = client.invoke(input="What is a vector?")
    assert response is not None

    document = response.pop()
    print(document)
    assert document is not None
    assert document.get("image_path", None) is not None
    assert document.get("related_content", None) is not None
