import logging
from abc import abstractmethod
from agents.agent_configuration import AgentConfiguration

class Agent():
    """Base class for agents"""
    def __init__(self, 
                 logger: logging, 
                 agent_configuration: AgentConfiguration
    ):
        self._logger: logging = logger
        self._agent_configuration: AgentConfiguration = agent_configuration
        self._conversation:list = []

        if self._agent_configuration.initial_message is not None:
            self._conversation = [{"role": "system", "content": self._agent_configuration.persona},
                         {"role": "assistant", "content": self._agent_configuration.initial_message}]
        else:
            self._conversation = [{"role": "system", "content": self._agent_configuration.persona}]

    @abstractmethod
    def run(self) -> None:
        """Abstract method to run the agent"""
        pass