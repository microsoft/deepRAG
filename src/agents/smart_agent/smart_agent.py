import base64
import inspect
import json
import logging
from types import MappingProxyType
from typing import Any, List
from openai import AzureOpenAI
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
from agents.agent import Agent
from agents.agent_configuration import AgentConfiguration

class Smart_Agent(Agent):
    """Smart agent that uses the pulls data from a vector database and uses the Azure OpenAI API to generate responses"""
    def __init__(
            self,
            logger: logging,
            agent_configuration: AgentConfiguration,
            client: AzureOpenAI,
            functions_spec: Any,
            functions_list: dict[str, Any],
            max_error_run:int = 3,
            max_run_per_question:int = 10
    ):
        super().__init__(logger=logger, agent_configuration=agent_configuration)
        
        self.__client = client
        self.__functions_spec = functions_spec
        self._functions_list = functions_list
        self.__max_error_run = max_error_run
        self.__max_run_per_question = max_run_per_question

    def run(self, user_input, conversation=None, stream=False, ):
        if user_input is None:  # if no input return init message
            return self._conversation, self._conversation[1]["content"]
        
        if conversation is not None:  # if no history return init message
            self._conversation = conversation

        execution_error_count = 0
        code = ""
        response_message = None
        data = {}
        run_count = 0
        self._conversation.append({"role": "user", "content": user_input})

        while True:
            if run_count >= self.__max_run_per_question:
                self._logger.debug(msg=f"Need to move on from this question due to max run count reached ({run_count} runs)")
                response_message = {
                    "role": "assistant", "content": "I am unable to answer this question at the moment, please ask another question."
                }
                break

            if execution_error_count >= self.__max_error_run:
                self._logger.debug(msg=f"resetting history due to too many errors ({execution_error_count} errors) in the code execution")
                execution_error_count = 0

            response: ChatCompletion = self.__client.chat.completions.create(
                model=self._agent_configuration.model,
                messages=self._conversation,
                tools=self.__functions_spec,
                tool_choice='auto',
                temperature=0.2,
            )
            
            run_count += 1
            response_message: ChatCompletionMessage = response.choices[0].message

            if response_message.content is None:
                response_message.content = ""

            tool_calls: List[ChatCompletionMessageToolCall] | None = response_message.tool_calls

            if tool_calls:
                self._conversation.append(response_message)
                self.__verify_openai_tools(tool_calls=tool_calls)
                continue
            else:
                break

        if not stream:
            self._conversation.append(response_message)
            if type(response_message) is dict:
                assistant_response = response_message.get('content')
            else:
                assistant_response = response_message.dict().get('content')

        else:
            assistant_response = response_message

        return stream, code, self._conversation, assistant_response, data

    def __check_args(self, function, args) -> bool:
        """Check if the function has the correct number of arguments"""
        sig: inspect.Signature = inspect.signature(function)
        params: MappingProxyType[str, inspect.Parameter] = sig.parameters

        for name in args:
            if name not in params:
                return False

        for name, param in params.items():
            if param.default is param.empty and name not in args:
                return False

        return True
    
    def __verify_openai_tools(self, tool_calls: List[ChatCompletionMessageToolCall]):
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            self._logger.debug(msg=f"Recommended Function call: {function_name}")

            # verify function exists
            if function_name not in self._functions_list:
                self._logger.debug(msg=f"Function {function_name} does not exist, retrying")
                self._conversation.pop()
                break

            function_to_call = self._functions_list[function_name]

            try:
                function_args = json.loads(s=tool_call.function.arguments)
            except json.JSONDecodeError as e:
                self._logger.error(e)
                self._conversation.pop()
                break

            if self.__check_args(function=function_to_call, args=function_args) is False:
                self._conversation.pop()
                break
            else:
                function_response = function_to_call(**function_args)

            if function_name == "search":
                function_response = self.__generate_search_function_response(function_response=function_response)

            self._conversation.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )

    def __generate_search_function_response(self, function_response):
        search_function_response = []

        for item in function_response:
            image_path = item['image_path']
            related_content = item['related_content']

            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(
                    image_file.read()).decode('utf-8')
            self._logger.debug("image_path: ", image_path)

            search_function_response.append(
                {"type": "text", "text": f"file_name: {image_path}"})
            search_function_response.append({"type": "image_url", "image_url": {
                                            "url":  f"data:image/jpeg;base64,{base64_image}"}})
            search_function_response.append(
                {"type": "text", "text": f"HINT: The following kind of content might be related to this topic\n: {related_content}"})
            
        return search_function_response
