from dataclasses import dataclass

@dataclass
class AgentResponse:
    """Class to represent a response from an agent"""
    conversation: list
    response: str | None
    streaming: bool = False