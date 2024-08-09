from fastapi.testclient import TestClient
from api import Server
from httpx import Response
import pytest
from models import Settings

@pytest.fixture
def client() -> TestClient:
    settings: Settings = Settings(_env_file=".env")  # type: ignore
    settings.smart_agent_prompt_location = "/workspaces/deepRAG/" + settings.smart_agent_prompt_location
    server = Server(settings=settings)
    return TestClient(app=server)

def test_vector_rag(client: TestClient) -> None:
    # Test simple route
    response: Response = client.post(
        url="/vectorRAG/invoke", json={"input": "Nescaf brand guidelines for creating TikTok content for Gen Z with a focus on natural and authentic imagery"})
    assert response.status_code == 200
    print(response.json())

def test_deep_rag(client: TestClient) -> None:
    # Test simple route
    response: Response = client.post(
        url="/deepRAG/invoke", json={"input": "Nescaf brand guidelines for creating TikTok content for Gen Z with a focus on natural and authentic imagery"})
    assert response.status_code == 200
    print(response.json())
