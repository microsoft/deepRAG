from typing import List
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable
from langchain_core.retrievers import BaseRetriever
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.llms.openai import OpenAI
from langchain_community.graphs import NetworkxEntityGraph
from langchain.indexes.graph import GraphIndexCreator
from langchain.retrievers.ensemble import EnsembleRetriever
from langchain.retrievers.multi_query import MultiQueryRetriever
from runnables.vector_retrieval.retriever import Retriever as VectorRetriever
from runnables.deep_retrieval.retriever import Retriever as DeepRetriever
from runnables.graph_retrieval.graph_retriever import Retriever as GraphRetriever

# test that the vector retriever pulls back expected documents from a given query.

# todo: setup in memory vector db
vectorDb = InMemoryVectorStore(
    embedding=OpenAIEmbeddings(),
)

# test that the graph retriever pulls back expected nodes from a given query.

# todo: setup in memory graph
llm = OpenAI()
prompt = "What is the capital of France?"
graph = NetworkxEntityGraph()
index_creator = GraphIndexCreator(llm=llm)


def make_chain(vector_retriever: BaseRetriever) -> Runnable:
    return DeepRetriever(
        graph_retriever=GraphRetriever(index_creator=index_creator),
        multi_query_retriever=MultiQueryRetriever(retriever=vector_retriever),
        vector_retriever=VectorRetriever(vector_store=None),
        ensemble_retriever=EnsembleRetriever(retrievers=[]),
    ) | StrOutputParser()
