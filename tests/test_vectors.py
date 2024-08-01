from typing import List
from langchain_core.documents.base import Document
from langchain_core.embeddings import FakeEmbeddings
from langchain_core.vectorstores.in_memory import InMemoryVectorStore

def test_vector_rag() -> None:
    """Test the vector RAG."""
    
    # configure
    query = "What is a vector?"
    answer = "A vector is a mathematical object that has both a magnitude and a direction."
    vector_store = InMemoryVectorStore(embedding=FakeEmbeddings(size=1568))
    doc = Document(page_content=answer)
    vector_store.add_documents(documents=[doc])

    # invoke
    documents: List[Document] = vector_store.as_retriever().invoke(input=query)

    # assert
    assert len(documents) > 0
