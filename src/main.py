from pathlib import Path
from agents.smart_agent.smart_agent import Smart_Agent
from models.settings import Settings
from models.agent_response import AgentResponse
from utils.smart_agent_factory import SmartAgentFactory

env_path: Path = Path('..') / '.env'
settings: Settings = Settings(_env_file=env_path)
agent: Smart_Agent = SmartAgentFactory.create_smart_agent(settings=settings, session_id='session_id')
agent_response: AgentResponse = agent.run(user_input="What is the slogan of NESCAFE?", conversation=[], stream=False)

print(agent_response)