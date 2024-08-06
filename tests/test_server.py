from fastapi.testclient import TestClient
from api import app
from httpx import Response
import pytest
 
@pytest.fixture
def client() -> TestClient:
    return TestClient(app=app)

def test_vector_rag(client: TestClient) -> None:
    # Test simple route
    response: Response = client.post(url="/vectorRAG/invoke", json={"input": "NESCAF\u00c9's New Global Initiative"})
    assert response.status_code == 200

def test_deep_rag(client: TestClient) -> None:
    # Test simple route
    response: Response = client.post(url="/deepRAG/invoke", json={"input": "NESCAF\u00c9's New Global Initiative"})
    assert response.status_code == 200