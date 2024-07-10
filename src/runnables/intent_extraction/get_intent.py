from langchain_core import prompt, chain

@chain
def get_intent(text):
    # TODO: implement more sophisticated intent extraction
    return prompt(f"What is the intent of the text? Text: {text} \r\n Intent: ")
