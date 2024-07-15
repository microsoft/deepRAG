from langchain_core import prompt, chain
from langchain.retrievers import MultiQueryRetriever

class Retreiver:
    def __init__(self, vectordb, llm_chain, parser_key):
        self.retriever = MultiQueryRetriever(
            retriever=vectordb.as_retriever(),
            llm_chain=llm_chain,
            parser_key=parser_key
        )

    @chain
    def generate_queries(self, text):
        #TODO: implement more sophisticated query generation
        return prompt(text) | self.retriever
