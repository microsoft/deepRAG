from typing import Any, List
from langchain_core.documents.base import Document
from langchain_core.embeddings import FakeEmbeddings, DeterministicFakeEmbedding
from langchain_core.vectorstores.base import VectorStoreRetriever
from langchain_core.vectorstores.in_memory import InMemoryVectorStore
import pytest_mock
import pytest

@pytest.fixture(scope="module")
def vector_document() -> Document:
    return Document(page_content="A vector is a mathematical object that has both a magnitude and a direction.")

@pytest.fixture(scope="module")
def scalar_document() -> Document:
    return Document(page_content="A scalar is a mathematical object that has only a magnitude. It is not a vector.")

@pytest.fixture(scope="module")
def unrelated_document() -> Document:
    return Document(page_content="The sky is blue.")

@pytest.fixture(scope="module")
def vector_store(
    vector_document: Document,
    scalar_document: Document,
    unrelated_document: Document) -> InMemoryVectorStore:
    store = InMemoryVectorStore(embedding=DeterministicFakeEmbedding(size=1568))
    store.add_documents(documents=[vector_document, scalar_document, unrelated_document])
    return store

def test_vector_rag(
    vector_store: InMemoryVectorStore,
    vector_document: Document) -> None:
    """
    Test the vector RAG pipeline to ensure it pulls the documents we expect, and not the ones we don't.
    """
    
    # arrange
    query: str = vector_document.page_content
    retriever: VectorStoreRetriever = vector_store.as_retriever(
        search_kwargs={"k": 1},
    )

    # act
    documents: List[Document] = retriever.invoke(input=query)

    # assert
    assert len(documents) == 1
    assert documents[0].page_content == query
