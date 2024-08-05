import pytest
import pytest_mock
from typing import Any, List
from langserve.client import RemoteRunnable
from langchain_core.embeddings import FakeEmbeddings
from langchain_core.vectorstores.in_memory import InMemoryVectorStore
# from langchain.embeddings import OpenAIEmbeddings
# from langchain.vectorstores import FAISS
# from langchain.text_splitter import CharacterTextSplitter
# from langchain_core.documents.base import Document

from api import Server

def test_vectorRAG_api_happy_path(mocker):
    # Arrange
    # mock_client = Mock()
    # mock_remote_runnable.return_value = mock_client
    # mock_client.invoke.return_value = []

    # Act
    client = RemoteRunnable(url="http://localhost:8000/vectorRAG")
    response = client.invoke(input="What is the slogan for NESCAFE?")

    # Assert
    # assert response is not None
    # print(response)
    # assert response_data is not None

    # Assuming the response contains a field 'document' with the retrieved document text
    # retrieved_document = response_data.get("document")
    # assert retrieved_document is not None

#     # Initialize embeddings
#     embeddings = OpenAIEmbeddings()

#     # Split document into chunks (if needed)
#     text_splitter = CharacterTextSplitter(chunk_size=100, chunk_overlap=0)
#     docs = text_splitter.split_documents(retrieved_document)

#     # Calculate similarity score
#     vector_store = FAISS.from_documents(docs, embeddings)
#     query = "This is a sample document."
#     query_embedding = embeddings.embed_query(query)
#     similarity_scores = vector_store.similarity_search(query_embedding)

#     # Ensure the similarity score is above a certain threshold
#     # assert similarity_score > 0.7  # Adjust threshold as needed

#     assert response == []
#     mock_client.invoke.assert_called_once_with(input="What is a vector?")
