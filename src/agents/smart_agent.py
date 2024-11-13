#General module to load tool specifications and make it available for the agent to use.
from pathlib import Path  
import json  
import os  
from openai import AzureOpenAI  
import yaml  
from tenacity import retry, wait_random_exponential, stop_after_attempt  
import pandas as pd  
from dotenv import load_dotenv  
import inspect  
import yaml
import importlib  
import numpy as np

MAX_ERROR_RUN = 3  
MAX_RUN_PER_QUESTION = 10  
MAX_QUESTION_TO_KEEP = 3  
MAX_QUESTION_WITH_DETAIL_HIST = 1  
  
  
max_conversation_len = 5  # Set the desired value of k  
  
def clean_up_history(history, max_q_with_detail_hist=1, max_q_to_keep=2):  
    question_count = 0  
    removal_indices = []  
    for idx in range(len(history) - 1, 0, -1):  
        message = dict(history[idx])  
        if message.get("role") == "user":  
            question_count += 1  
            if question_count >= max_q_with_detail_hist and question_count < max_q_to_keep:  
                if message.get("role") != "user" and message.get("role") != "assistant" and len(message.get("content")) == 0:  
                    removal_indices.append(idx)  
        if question_count >= max_q_to_keep:  
            removal_indices.append(idx)  
    for index in removal_indices:  
        del history[index]  
  
def reset_history_to_last_question(history):  
    for i in range(len(history) - 1, -1, -1):  
        message = dict(history[i])  
        if message.get("role") == "user":  
            break  
        history.pop()  
  
class Smart_Agent():
    """
    Agent that can use other agents and tools to answer questions.

    Args:
        persona (str): The persona of the agent.
        tools (list): A list of {"tool_name":tool} that the agent can use to answer questions. Tool must have a run method that takes a question and returns an answer.
        stop (list): A list of strings that the agent will use to stop the conversation.
        init_message (str): The initial message of the agent. Defaults to None.
        engine (str): The name of the GPT engine to use. Defaults to "gpt-35-turbo".

    Methods:
        llm(new_input, stop, history=None, stream=False): Generates a response to the input using the LLM model.
        _run(new_input, stop, history=None, stream=False): Runs the agent and generates a response to the input.
        run(new_input, history=None, stream=False): Runs the agent and generates a response to the input.

    Attributes:
        persona (str): The persona of the agent.
        tools (list): A list of {"tool_name":tool} that the agent can use to answer questions. Tool must have a run method that takes a question and returns an answer.
        stop (list): A list of strings that the agent will use to stop the conversation.
        init_message (str): The initial message of the agent.
        engine (str): The name of the GPT engine to use.
    """
        
    def check_args(self, function, args):
        sig = inspect.signature(function)
        params = sig.parameters

        # Check if there are extra arguments
        for name in args:
            if name not in params:
                return False
        # Check if the required arguments are provided 
        for name, param in params.items():
            if param.default is param.empty and name not in args:
                return False


    def _create_functions_dict(self, agent_name):  
        functions_dict = {}  
        tools_path = Path(__file__).parent / 'tools'  

        for file in os.listdir(tools_path):  
            if (file.endswith('.py') and agent_name in file) or file=="tools.py":  
                module_name = file[:-3]  
                module = importlib.import_module(f'src.agents.tools.{module_name}')  
                  
                # Iterate over all classes in the module  
                for name, obj in inspect.getmembers(module, inspect.isclass):  
                    if name.endswith("Tool"):
                        # Create an instance of the tool class  
                        tool_instance = obj()  
                        # Get all methods from the tool instance  
                        methods = inspect.getmembers(tool_instance, predicate=inspect.ismethod)  
                        # Add methods to the dictionary  
                        for method_name, method in methods:  
                            if not method_name.startswith("_"):
                                functions_dict[method_name] = method  
          
        return functions_dict  


    def __init__(self,agent_name, base_path):
        self.name = agent_name

        self.client = AzureOpenAI(  
        api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),  
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT")   
        ) 
        with open(os.environ.get("USER_PROFILE_FILE")) as f:
            user_profile = json.load(f)
      
        self.engine = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT")
        profile_file = f'{base_path}/{agent_name}_profile.yaml'
        with open(profile_file, 'r') as file:  
            profile = yaml.safe_load(file)  
        self.domain_description = profile["domain_description"]
        common_profile_file = f'{base_path}/common_agent_profile.yaml'
        with open(common_profile_file, 'r') as file:
            common_profile = yaml.safe_load(file)
        if profile.get('default_agent') ==True:
            self.default_agent = True
            print("Default agent is set to ", self.name)
        else:
            self.default_agent = False
        self.follow_up_instruction1 = profile.get("follow_up_instruction1")
        self.follow_up_instruction2 = profile.get("follow_up_instruction2")
        self.follow_up_instruction3 = profile.get("follow_up_instruction3")
        self.base_instruction =profile["persona"].format(customer_name =user_profile['name'], customer_id=user_profile['customer_id'])
        if self.follow_up_instruction1:
            self.default_persona = self.base_instruction+"\n" + self.follow_up_instruction1
        else:
            self.default_persona = self.base_instruction
        self.init_history =[{"role":"system", "content":self.default_persona}, {"role":"assistant", "content":profile["initial_message"]}]
        self.function_spec = []
        for tool in profile.get('tools', []):
            self.function_spec.append({        
                "type": tool['type'], 
                "function":{ 
                "name": tool['name'],  
                "description": tool['description'],  
                "parameters": tool['parameters']  
                }}
            )
        for tool in common_profile.get('tools', []):  
            self.function_spec.append({        
                "type": tool['type'],
                "function":{  
                "name": tool['name'],  
                "description": tool['description'],  
                "parameters": tool['parameters']  
            }})  


        self.functions_list = self._create_functions_dict(profile["name"])  
        
    def run(self, user_input, conversation=None):
        if user_input is None: #if no input return init message
            return False, self.init_history, self.init_history[1]["content"]
        if conversation is None: #if no history return init message
            conversation = self.init_history.copy()
        conversation.append({"role": "user", "content": user_input})
        request_help = False
        if len(self.function_spec)>0:
            print("conversation : ", conversation)
            while True:
                response = self.client.chat.completions.create(
                    model=self.engine, 
                    messages=conversation,
                tools=self.function_spec,
                tool_choice='auto',
                logprobs=True,

                )
                
                response_message = response.choices[0].message
                if response_message.content is None:
                    response_message.content = ""

                tool_calls = response_message.tool_calls
                

                print("assistant response: ", response_message.content)
                # Step 2: check if GPT wanted to call a function
                if  tool_calls:
                    conversation.append(response_message)  # extend conversation with assistant's reply
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        print("Recommended Function call:")
                        print(function_name)
                        print()                                    
                        # verify function exists
                        if function_name not in self.functions_list:
                            raise Exception("Function " + function_name + " does not exist")
                        function_to_call = self.functions_list[function_name]
                        
                        # verify function has correct number of arguments
                        function_args = json.loads(tool_call.function.arguments)


                        
                        # print("beginning function call")
                        function_response = str(function_to_call(**function_args))

                        if function_name=="get_help": #scenario where the agent asks for help
                            summary_conversation = []
                            for message in conversation:
                                message = dict(message)
                                if message.get("role") != "system" and message.get("role") != "tool" and len(message.get("content"))>0:
                                    summary_conversation.append({"role":message.get("role"), "content":message.get("content")})
                            summary_conversation.pop() #remove the last message which is the agent asking for help
                            return True, summary_conversation, function_response

                        print("Output of function call:")
                        print(function_response)
                        print()
                    
                        conversation.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": function_response,
                            }
                        )  # extend conversation with function response
                        

                    continue
                else:
                    
                    if response_message.content == "True" or response_message.content == "False":
                        logprob = response.choices[0].logprobs.content[0]
                        logprob =np.round(np.exp(logprob.logprob)*100,2)
                        hallucination_flag = logprob < float(os.getenv("SUFFICIENT_CONTEXT_SCORE_THRESHOLD"))
                        if response_message.content == "True" and not hallucination_flag:
                            #update system message to remove the analyze instruction so that LLM can generate the answer without analyzing again
                            conversation[0]['content'] = self.base_instruction 
                            advisor_message = {"role": "user", "content": self.follow_up_instruction2}
                            print("good context, proceed to generation answer")
                        else:
                            print("not sufficient context, proceed to provide alternative answer")

                            advisor_message = {"role": "user", "content": self.follow_up_instruction3}
                        conversation.append(advisor_message)
                        continue


                    break #if no function call break out of loop as this indicates that the agent finished the research and is ready to respond to the user
        else:
            response = self.client.chat.completions.create(
                model=self.engine, 
                messages=conversation,
                )
            response_message = response.choices[0].message

        conversation.append(response_message)
        conversation[0]['content'] = self.default_persona #after answering the question, reset the system message to the default persona so that the self-review can be activated 
        # remove conversation where the content is either self.follow_up_instruction2 or self.follow_up_instruction3
        for idx, message in enumerate(conversation):
            message = dict(message)
            if message["content"] == self.follow_up_instruction2 or message["content"] == self.follow_up_instruction3:
                conversation.pop(idx)
        assistant_response = response_message.content

        return request_help, conversation, assistant_response
  
