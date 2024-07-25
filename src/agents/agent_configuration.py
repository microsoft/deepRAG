from dataclasses import dataclass

@dataclass
class Parameter():
    type: str
    properties: dict

    @staticmethod
    def from_dict(data: dict) -> "Parameter":
        return Parameter(
            type=data["type"],
            properties=data["properties"]
        )
    
    def to_dict(self) -> dict:

        return {
            "type": self.type,
            "properties": {
                property_key: tool_property for property in self.properties for property_key, tool_property in property.items()
            }
        }
    
@dataclass
class Tool():
    name: str
    description: str
    type: str
    parameters: Parameter
    required: list[str]

    @staticmethod
    def from_dict(data: dict) -> "Tool":
        return Tool(
            name=data["name"],
            description=data["description"],
            type=data["type"],
            parameters=Parameter.from_dict(data=data["parameters"]),
            required=data["required"]
        )
    
    def to_openai_tool(self) -> dict:
        return {
            "type": self.type,
            "function": {
                "name": self.name,
                "description": self.description,
                "required": self.required,
                "parameters": self.parameters.to_dict()
            }
        }

@dataclass
class AgentConfiguration():
    persona: str
    model: str
    initial_message: str
    name: str
    tools: list[Tool]

    @staticmethod
    def from_dict(data: dict) -> "AgentConfiguration":
        return AgentConfiguration(
            persona=data["persona"],
            model=data["model"],
            initial_message=data["initial_message"],
            name=data["name"],
            tools=[Tool.from_dict(data=tool) for tool in data["tools"]]
        )
    
def agent_configuration_from_dict(data: dict) -> AgentConfiguration:
    return AgentConfiguration(
        persona=data["persona"],
        model=data["model"],
        initial_message=data["initial_message"],
        name=data["name"],
        tools=[Tool.from_dict(data=tool) for tool in data["tools"]]
    )

