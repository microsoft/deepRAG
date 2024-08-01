import os
from logging import Logger
from typing import (Any, List, Dict)
from openai import AzureOpenAI
from azure.search.documents import (SearchItemPaged, SearchClient)
from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryType,
    VectorizedQuery,
)

class SearchVectorFunction:
    """Search function that uses a vector database to search for related content"""
    def __init__(
            self,
            logger: Logger,
            search_client:SearchClient,
            client:AzureOpenAI,
            model: str,
            image_directory: str
        ) -> None:
        self.__logger: Logger = logger
        self.__search_client: SearchClient = search_client
        self.__client: AzureOpenAI = client
        self.__model: str = model
        self.__image_directory: str = image_directory

    def search(self, search_query) -> list:
        """Search for related content based on a search query"""
        self.__logger.debug("search query: ", search_query)
        output = []
        vector_query = VectorizedQuery(
            vector=self.__get_text_embedding(text=search_query),
            k_nearest_neighbors=3,
            fields="contentVector"
        )

        results:SearchItemPaged[Dict]= self.__search_client.search(
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name='my-semantic-config',
            query_caption=QueryCaptionType.EXTRACTIVE,
            query_answer=QueryAnswerType.EXTRACTIVE,
            vector_queries=[vector_query],
            select=["topic", "file_name", "page_number", "related_content"],
            top=3
        )

        for result in results:
            self.__logger.debug(f"topic: {result['topic']}")
            self.__logger.debug("related_content: ", result['related_content'])
            page_image = os.path.join(
                self.__image_directory,
                result['file_name'],
                "page_" + str(result['page_number'])
            )+".png"

            output.append({
                'image_path': page_image,
                'related_content': result['related_content']}
            )

        return output

    def __get_text_embedding(self, text) -> List[float]:
        text = text.replace("\n", " ")

        while True:
            embedding_response: List[float] = self.__client.embeddings.create(
                    input=[text],
                    model=self.__model
                ).data[0].embedding

            return embedding_response
