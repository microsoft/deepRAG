from langchain_core import prompt, chain

@chain
def generate_queries(text):
    #TODO: implement more sophisticated query generation
    return prompt(f"Generate queries for text: {text} \r\n Queries: ")
