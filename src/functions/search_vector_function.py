import os  
from logging import Logger  
from typing import Any, List, Dict  
from openai import AzureOpenAI  
from azure.search.documents import SearchItemPaged, SearchClient  
from azure.search.documents.models import (  
    QueryAnswerType,  
    QueryCaptionType,  
    QueryType,  
    VectorizedQuery,  
)  
from azure.storage.blob import BlobServiceClient, ContainerClient  
  
class SearchVectorFunction:  
    """Search function that uses a vector database to search for related content"""  
  
    def __init__(  
            self,  
            logger: Logger,  
            search_client: SearchClient,  
            client: AzureOpenAI,  
            model: str,  
            image_directory: str,  
            storage_account_key: str,  
            storage_account_name: str,  
            container_name: str  
        ) -> None:  
        self.__logger: Logger = logger  
        self.__search_client: SearchClient = search_client  
        self.__client: AzureOpenAI = client  
        self.__model: str = model  
        self.__image_directory: str = image_directory  
        self.__blob_service_client = BlobServiceClient(  
            account_url=f"https://{storage_account_name}.blob.core.windows.net",  
            credential=storage_account_key  
        )  
        self.__container_client: ContainerClient = self.__blob_service_client.get_container_client(container_name)  
  
    def search(self, search_query) -> list:  
        """Search for related content based on a search query"""  
        self.__logger.debug("search query: ", search_query)  
        output = []  
        vector_query = VectorizedQuery(  
            vector=self.__get_text_embedding(text=search_query),  
            k_nearest_neighbors=3,  
            fields="contentVector"  
        )  
        results: SearchItemPaged[Dict] = self.__search_client.search(  
            query_type=QueryType.SEMANTIC,  
            semantic_configuration_name='my-semantic-config',  
            query_caption=QueryCaptionType.EXTRACTIVE,  
            query_answer=QueryAnswerType.EXTRACTIVE,  
            vector_queries=[vector_query],  
            select=["topic", "file_name", "page_number", "related_content"],  
            top=3  
        )  
        for result in results:  
            self.__logger.debug(msg=f"topic: {result['topic']}")  
            self.__logger.debug("related_content: ", result['related_content'])  
            page_image_name = f"{result['file_name']}/page_{result['page_number']}.png"  
            page_image_local_path = os.path.join(self.__image_directory, page_image_name)  
            print("page_image_name ", page_image_name)
            # Ensure the local directory exists  
            os.makedirs(os.path.dirname(page_image_local_path), exist_ok=True)  
  
            # Download the image from Azure Blob Storage to local directory  
            self.__download_image_from_blob(page_image_name, page_image_local_path)  
            output.append({  
                'id': result['id'] if 'id' in result.keys() else None,  
                'image_path': page_image_name,  
                'related_content': result['related_content']  
            })  
        return output  
  
    def __get_text_embedding(self, text: str) -> List[float]:  
        text = text.replace("\n", " ")  
        return self.__client.embeddings.create(  
            input=[text],  
            model=self.__model  
        ).data[0].embedding  
  
    def __download_image_from_blob(self, blob_name: str, download_file_path: str) -> None:  
        """  
        Download an image from Azure Blob Storage to a local file  
        """  
        with open(download_file_path, "wb") as download_file:  
            blob_client = self.__container_client.get_blob_client(blob_name)  
            download_stream = blob_client.download_blob()  
            download_file.write(download_stream.readall())  
