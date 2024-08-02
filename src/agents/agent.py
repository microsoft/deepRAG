from dataclasses import dataclass
from logging import Logger
from dataclasses import dataclass
from logging import Logger
from abc import abstractmethod
from models.agent_configuration import AgentConfiguration
from models.agent_response import AgentResponse

class Agent():
    """Base class for agents"""
    def __init__(self, 
        logger: Logger, 
        agent_configuration: AgentConfiguration
    ) -> None:
        self._logger: Logger = logger
        self._agent_configuration: AgentConfiguration = agent_configuration
        self._conversation: list = [
                { "role": "system", "content": self._agent_configuration.persona },
                { "role": "assistant", "content": self._agent_configuration.initial_message }
            ] if self._agent_configuration.initial_message is not None else [
                { "role": "system", "content": self._agent_configuration.persona }
            ]

    @abstractmethod
    def run(self, user_input: str | None, conversation=None, stream=False) -> AgentResponse:
        """Abstract method to run the agent"""
        pass