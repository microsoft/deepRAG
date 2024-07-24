from langchain_core.runnables.base import Runnable
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables.base import chain

@chain
def generate_cypher(ontology) -> Runnable:
    """Generate cypher code for a given ontology."""
    #TODO: implement more sophisticated cypher generation
    return PromptTemplate(f"Generate cypher code for ontology: {ontology} \r\n Cypher: ")
