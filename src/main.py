import fsspec
from fsspec.utils import get_protocol
from pathlib import Path
from agents.smart_agent.smart_agent import Smart_Agent
from models.settings import Settings
from models.agent_response import AgentResponse
from utils.smart_agent_factory import SmartAgentFactory

env_path: Path = Path('..') / '.env'
settings: Settings = Settings(_env_file=env_path) # type: ignore
agent_path: str = settings.smart_agent_prompt_location
protocol: str = get_protocol(url=agent_path)
fs: fsspec.AbstractFileSystem = fsspec.filesystem(protocol=protocol)
agent: Smart_Agent = SmartAgentFactory.create_smart_agent(fs=fs, settings=settings, session_id='session_id')
agent_response: AgentResponse = agent.run(user_input="What is the slogan of NESCAFE?", conversation=[], stream=False)

print(agent_response)
