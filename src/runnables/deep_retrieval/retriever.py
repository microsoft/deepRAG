from typing import Any, List

from langchain_core.documents.base import Document
from runnables.multi_query.generate_queries import Retreiver as MultiQueryRetriever
from runnables.vector_retrieval.retriever import Retriever as VectorRetriever
from runnables.graph_retrieval.graph_retriever import Retriever as GraphRetriever
from langchain.retrievers import EnsembleRetriever
from langchain_core.runnables.base import Runnable

class Retriever:
    def __init__(self,
            graph_retriever: GraphRetriever,
            multi_query_retriever: MultiQueryRetriever,
            vector_retriever: VectorRetriever,
            ensemble_retriever: EnsembleRetriever) -> None:
        self.vector_retriever: VectorRetriever = vector_retriever
        self.multi_query_retriever: MultiQueryRetriever = multi_query_retriever
        self.graph_retriever: GraphRetriever = graph_retriever

    def retrieve(self, input) -> Runnable:
        multi_queries: List[Document] = self.multi_query_retriever.retriever.invoke(input=input)
        vector_retrievers: List[Document] = [self.vector_retriever.retrieve(query) for query in multi_queries]
        graph_retrievers: List = [self.graph_retriever.retrieve(query) for query in vector_retrievers]