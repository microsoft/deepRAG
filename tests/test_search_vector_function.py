from unittest.mock import Mock, MagicMock
import pytest_mock
from typing import Any, List, Union
from openai import AzureOpenAI
from openai.types.create_embedding_response import CreateEmbeddingResponse, Usage
from openai.types.embedding import Embedding
from azure.search.documents import (SearchItemPaged, SearchClient)
from functions import SearchVectorFunction

def setup(mocker: pytest_mock.MockerFixture,
          input: Union[str, List[str], List[int], List[List[int]]],
          image_directory: str,
          documents: list[dict[str, Any]]) -> SearchVectorFunction:
    mockAzureOpenAI: Mock | Mock = mocker.Mock(target=AzureOpenAI, embeddings=mocker.Mock(create=mocker.Mock()))
    mockSearchClient: Mock | Mock = mocker.Mock(target=SearchClient, search=mocker.Mock(search=mocker.Mock()))
    mock_search_item_paged = MagicMock(spec=SearchItemPaged)

# Define the behavior of the mock instance
    mock_search_item_paged.__iter__.return_value = iter(documents)

    mockAzureOpenAI.embeddings.create.return_value = CreateEmbeddingResponse(
        data=[
            Embedding(
                embedding=[0.23333 for _ in range(233)],
                index=i,
                object='embedding'
            ) for i in range(len(input))
        ],
        model="gpt-4",
        object='list',
        usage=Usage(
            prompt_tokens=2,
            total_tokens=2
        )
    )

    mockSearchClient.search.return_value = mock_search_item_paged

    return SearchVectorFunction(
        logger=mocker.Mock(),
        search_client=mockSearchClient,
        client=mockAzureOpenAI,
        model="gpt-4",
        image_directory=image_directory
    )

def test_valid_search_return(mocker: pytest_mock.MockerFixture,):
    """Test for a valid search return"""
    image_directory: str = "images"
    file_name: str = "page_1.png"
    related_content: str = "Hello World"
    page_number: int = 1
    documents:list[dict[str, Any]] = [
        {
            'id': '1',
            'name': 'Item 1',
            'topic': 'test',
            'related_content': related_content,
            'page_number': page_number,
            'file_name': file_name
        }
    ]

    search_vector_function: SearchVectorFunction = setup(
        mocker=mocker,
        input="search query",
        image_directory=image_directory,
        documents=documents
    )

    search_vector_response: list[Any] = search_vector_function.search(search_query="search query")

    for t in search_vector_response:
        assert t['image_path'] == f"{image_directory}/{file_name}/page_{page_number}.png"
        assert t['related_content'] == related_content

def test_muliple_document_return(mocker: pytest_mock.MockerFixture):
    """Test for multiple document return"""
    image_directory: str = "images"
    documents:list[dict[str, Any]] = [
        {
            'id': '1',
            'name': 'Item 1',
            'topic': 'test',
            'related_content': "Hello World",
            'page_number': 1,
            'file_name': "page_1.png"
        }, {
            'id': '2',
            'name': 'Item 2',
            'topic': 'test',
            'related_content': None,
            'page_number': 2,
            'file_name': "page_2.png"
        }
    ]

    search_vector_function: SearchVectorFunction = setup(
        mocker=mocker,
        input="search query",
        image_directory=image_directory,
        documents= documents
    )

    search_vector_response: list[Any] = search_vector_function.search(search_query="search query")

    for search_document in search_vector_response:
        document: dict[str, Any] = next((document for document in documents if document.get("id") == search_document["id"]), None)
        file_name= document["file_name"]
        page_number= document["page_number"]

        assert search_document['image_path'] == f"{image_directory}/{file_name}/page_{page_number}.png"
        assert search_document['related_content'] == document["related_content"]