from dataclasses import dataclass
from typing import Any, Literal
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.shared_params import FunctionDefinition

@dataclass
class Parameter():
    """Parameter class to represent the parameters of a tool"""
    type: str
    properties: dict

    @staticmethod
    def from_dict(data: dict) -> "Parameter":
        """Converts a dictionary to a Parameter object"""
        return Parameter(
            type=data["type"],
            properties=data["properties"]
        )

    def to_dict(self) -> dict:
        """Converts a Parameter object to a dictionary"""
        return {
            "type": self.type,
            "properties": {
                property_key: tool_property for property in self.properties for property_key, tool_property in property.items()
            }
        }

@dataclass
class Tool():
    """Tool class to represent the tools that the agent can use"""
    name: str
    description: str
    type: Literal["function"]
    parameters: Parameter
    required: list[str]

    @staticmethod
    def from_dict(data: dict) -> "Tool":
        """Converts a dictionary to a Tool object"""
        return Tool(
            name=data["name"],
            description=data["description"],
            type=data["type"],
            parameters=Parameter.from_dict(data=data["parameters"]),
            required=data["required"]
        )

    def to_openai_tool(self) -> ChatCompletionToolParam:
        """Converts a Tool object to a dictionary that matches the openai format"""
        return ChatCompletionToolParam(
            type=self.type,
            function=FunctionDefinition(
                name=self.name,
                description=self.description,
                #required=self.required,
                parameters=self.parameters.to_dict(),
            )
        )

@dataclass
class AgentConfiguration():
    """AgentConfiguration class to represent the configuration of the agent"""
    persona: str
    model: str
    initial_message: str
    name: str
    tools: list[Tool]

    @staticmethod
    def from_dict(data: dict) -> "AgentConfiguration":
        """Converts a dictionary to an AgentConfiguration object"""
        return AgentConfiguration(
            persona=data["persona"],
            model=data["model"],
            initial_message=data["initial_message"],
            name=data["name"],
            tools=[Tool.from_dict(data=tool) for tool in data["tools"]]
        )

def agent_configuration_from_dict(data: dict) -> AgentConfiguration:
    """Converts a dictionary to an AgentConfiguration object"""
    return AgentConfiguration(
        persona=data["persona"],
        model=data["model"],
        initial_message=data["initial_message"],
        name=data["name"],
        tools=[Tool.from_dict(data=tool) for tool in data["tools"]]
    )
