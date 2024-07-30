from dataclasses import dataclass

@dataclass
class AgentResponse():
    stream: bool
    code: str
    history: list
    response:str
    data: dict