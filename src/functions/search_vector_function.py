import os
import logging
from typing import Any
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryType,
    VectorizedQuery,
)

class SearchVectorFunction:
    def __init__(self, logger:logging, search_client:SearchClient, client:AzureOpenAI, model: str):
        self.__logger: Any = logger
        self.__search_client: SearchClient = search_client
        self.__client: AzureOpenAI = client
        self.__model = model
        self.search_function_spec: Any ={
            "type": "function",
            "function": {

                "name": "search",
                "description": "Semantic Search Engine to search for content",

                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_query": {
                            "type": "string",
                            "description": "Natural language query to search for content"
                        }


                    },
                    "required": ["search_query"],
                },
            }
        }

    def search(self, search_query):
        self.__logger.debug("search query: ", search_query)
        images_directory = ".\\processed_data"
        output = []
        vector_query = VectorizedQuery(vector=self.__get_text_embedding(text=search_query), k_nearest_neighbors=3, fields="contentVector")
        results = self.__search_client.search(
            query_type=QueryType.SEMANTIC, semantic_configuration_name='my-semantic-config', query_caption=QueryCaptionType.EXTRACTIVE, query_answer=QueryAnswerType.EXTRACTIVE,
            vector_queries=[vector_query],
            select=["topic", "file_name", "page_number", "related_content"],
            top=3
        )

        for result in results:
            self.__logger.debug(f"topic: {result['topic']}")
            self.__logger.debug("related_content: ", result['related_content'])

            page_image = os.path.join(
                images_directory, result['file_name'], "page_" + str(result['page_number']))+".png"
            output.append({'image_path': page_image,
                        'related_content': result['related_content']})
        return output

    def __get_text_embedding(self, text):
        text = text.replace("\n", " ")
        while True:
                embedding_response = self.__client.embeddings.create(
                    input=[text], model=self.__model).data[0].embedding
                return embedding_response