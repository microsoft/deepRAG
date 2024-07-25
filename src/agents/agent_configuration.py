class AgentConfiguration:
    def __init__(self, persona: str, model: str, initial_message: str, name: str):
        self.persona: str = persona
        self.model: str = model
        self.initial_message: str = initial_message
        self.name: str = name