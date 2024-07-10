from langchain_core import chain
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain.retrievers.multi_vector import MultiVectorRetriever

class Retriever:
    def __init__(self, vector_store: AzureSearch, store, id_key):
        self.retriever = MultiVectorRetriever(
            vectorstore=vector_store,
            docstore=store,
            id_key=id_key,
        )

    @chain    
    def retrieve(self, context):
        return self.retriever.invoke(context)
