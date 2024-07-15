from typing import List
from langchain_core import chain
from langchain_core.stores import BaseStore
from langchain_core.documents import Document
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain.retrievers.multi_vector import MultiVectorRetriever

class Retriever:
    def __init__(self, vector_store: AzureSearch, store: BaseStore[str, Document], id_key) -> None:
        self.retriever = MultiVectorRetriever(
            vectorstore=vector_store,
            docstore=store,
            id_key=id_key,
        )

    @chain    
    def retrieve(self, context) -> List[Document]:
        return self.retriever.invoke(input=context)
