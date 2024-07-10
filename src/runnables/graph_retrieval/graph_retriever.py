from cypher_generation.generate_cypher import generate_cypher
from langchain_core import prompt, chain

class Retriever:
    def __init__(self, graph):
        self.graph = graph

    @chain
    def _run(self, context):
        cypher_query = context['cypher_query']
        return self.graph.run(cypher_query)
    
    def retrieve(self, text):
        return generate_cypher(text) | self._run
