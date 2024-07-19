from typing import Any, Dict
from langchain_community.graphs.networkx_graph import NetworkxEntityGraph
from runnables.cypher_generation.generate_cypher import generate_cypher
from langchain_core.runnables.base import chain
from langchain_community.graphs.index_creator import GraphIndexCreator
from langchain_community.chains.graph_qa.base import GraphQAChain
from langchain_core.language_models import BaseLanguageModel

class Retriever:
    def __init__(self, index_creator: GraphIndexCreator, llm: BaseLanguageModel | None, ontology) -> None:
        self.index_creator: GraphIndexCreator = index_creator
        self.llm: BaseLanguageModel | None = llm
        self.ontology: str = ontology

    @chain
    def invoke(self, input) -> Dict[str, Any]:
        graph: NetworkxEntityGraph = self.index_creator.from_text(text=self.ontology)
        chain: GraphQAChain = GraphQAChain.from_llm(llm=self.llm, graph=graph, verbose=True)
        return chain.invoke(input=input)
