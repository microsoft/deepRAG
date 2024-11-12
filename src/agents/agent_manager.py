import os  
import random  
from openai import AzureOpenAI  
from .smart_agent import Smart_Agent  
  
class Agent_Runner:  
    def __init__(self, session_state): 
        base_path = "src/agents/agent_profiles"  
        self.agent_names = [f[:-13] for f in os.listdir(base_path) if f.endswith("_profile.yaml") and "common" not in f]  
        print("agents:", self.agent_names)  
        self.agents = [Smart_Agent(name, base_path) for name in self.agent_names]  
        self.default_agent = next(agent for agent in self.agents if agent.default_agent)
        self.session_state = session_state  
        self.evaluator_engine = os.environ.get("AZURE_OPENAI_EVALUATOR_DEPLOYMENT")  
        self.client = AzureOpenAI(  
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),  
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT")  
        )  
        self.active_agent = None  
        self.agent_descriptions = "\n".join([f"{agent.name}: {agent.domain_description}" for agent in self.agents])  
        for agent in self.agents:
            if 'agent_domains' in agent.init_history[0]['content']:
                agent.init_history[0]['content']=agent.init_history[0]['content'].replace('agent_domains', self.agent_descriptions)
                print("agent persona updated for", agent.name, agent.init_history[0]['content'])
    def classify_intent(self, user_input):  
        prompt = f"Given the request [{user_input}], pick a name from [{', '.join(self.agent_names)}]. Just output the name of the agent, no need to add any other text."  
        messages = [{"role": "system", "content": "You are a helpful AI assistant to match requests with agents. Here are agents with the description of their responsibilities:\n\n" + self.agent_descriptions}, {"role": "user", "content": prompt}]  
          
        response = self.client.chat.completions.create(  
            model=self.evaluator_engine,  
            messages=messages,  
            max_tokens=20  
        )  
          
        response_message = response.choices[0].message.content.strip()  
        print("classified as:", response_message)  
        return response_message  
  
    def revaluate_agent_assignment(self, function_description):  
        count = 0  
        while True:  
            count += 1  
            if count > 2:  
                next_agent = self.default_agent
                print("main agent keep refusing,assigned to designated default agent", next_agent.name)  
                break  
            next_agent = self.classify_intent(function_description)  
            if next_agent == self.active_agent.name:  
                continue  
            if next_agent in self.agent_names:  
                break  
        for agent in self.agents:  
            if next_agent == agent.name:  
                self.active_agent = agent  
                print("agent changed to", agent.name)  
                break  
  
    def run(self, user_input, session_id):  
        session = self.session_state.get(session_id)  
        if session:  
            active_agent_name = session.get("active_agent")  
            self.active_agent = next(agent for agent in self.agents if agent.name == active_agent_name)  
            conversation = session.get("conversation")  
            print("session found, active agent:", active_agent_name)
            print("conversation:", conversation)
        else:  
            
            self.active_agent = next(agent for agent in self.agents if agent.name == 'generic_agent') 
            conversation = self.active_agent.init_history  
  
        get_help, conversation, assistant_response = self.active_agent.run(user_input=user_input, conversation=conversation)  
          
        if get_help:  
            self.revaluate_agent_assignment(assistant_response)  
            conversation += self.active_agent.init_history  
            get_help, conversation, assistant_response = self.active_agent.run(user_input=user_input, conversation=conversation)
            if get_help: # if the agent still needs help even after re-assignment, then it's time to assign to the default agent
                self.active_agent = self.default_agent
                conversation += self.active_agent.init_history
                get_help, conversation, assistant_response = self.active_agent.run(user_input=user_input, conversation=conversation) 

        session_state = {"active_agent": self.active_agent.name, "conversation": conversation}  
        self.session_state.set(session_id, session_state)  
        return assistant_response  