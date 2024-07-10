from langchain_core import prompt, chain

@chain
def generate_cypher(ontology):
    #TODO: implement more sophisticated cypher generation
    return prompt(f"Generate cypher code for ontology: {ontology} \r\n Cypher: ")