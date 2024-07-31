import base64
import inspect
import json
from logging import Logger
from types import MappingProxyType
from typing import List
from openai import AzureOpenAI
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from agents.agent import Agent
from models.agent_configuration import AgentConfiguration
from models.agent_response import AgentResponse
from functions.search_vector_function import SearchVectorFunction
from services.history import History
import fsspec


class Smart_Agent(Agent):
    """Smart agent that uses the pulls data from a vector database and uses the Azure OpenAI API to generate responses"""
    def __init__(
            self,
            logger: Logger,
            agent_configuration: AgentConfiguration,
            client: AzureOpenAI,
            search_vector_function: SearchVectorFunction,
            history: History,
            fs: fsspec.AbstractFileSystem,
            max_error_run:int = 3,
            max_run_per_question:int = 10,
            max_question_to_keep:int = 3,
            max_question_with_detail_hist:int = 1
    ):
        super().__init__(logger=logger, agent_configuration=agent_configuration)
        
        self.__client: AzureOpenAI = client
        self.__max_error_run: int = max_error_run
        self.__max_run_per_question: int = max_run_per_question
        self.__max_question_to_keep: int = max_question_to_keep
        self.__max_question_with_detail_hist: int = max_question_with_detail_hist
        self.__functions_spec: List[ChatCompletionToolParam] = [tool.to_openai_tool() for tool in self._agent_configuration.tools]
        self.__history: History = history
        self._functions_list = {
            "search": search_vector_function.search
        }
        self.__fs: fsspec.AbstractFileSystem = fs

    def run(self, user_input: str | None, conversation=None, stream=False) -> AgentResponse:
        if user_input is None:  # if no input return init message
            return AgentResponse(conversation=self._conversation, response=self._conversation[1]["content"])
        
        if conversation is not None:
            self._conversation = conversation

        execution_error_count = 0
        run_count = 0

        self._conversation.append({"role": "user", "content": user_input})
        self.__history.clean_up_history(max_q_with_detail_hist=self.__max_question_with_detail_hist, max_q_to_keep=self.__max_question_to_keep)

        while True:
            response_message: ChatCompletionMessage

            if execution_error_count >= self.__max_error_run:
                self.__history.reset_history_to_last_question()
                self._logger.debug(msg=f"resetting history due to too many errors ({execution_error_count} errors) in the code execution")
                execution_error_count=0
            
            if run_count >= self.__max_run_per_question:
                self._logger.debug(msg=f"Need to move on from this question due to max run count reached ({run_count} runs)")
                response_message = ChatCompletionMessage(
                    role="assistant",
                    content="I am unable to answer this question at the moment, please ask another question."
                )
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
            response_message = response.choices[0].message

            if response_message.content is None:
                response_message.content = ""

            tool_calls: List[ChatCompletionMessageToolCall] | None = response_message.tool_calls

            if tool_calls:
                self._conversation.append(response_message)
                self.__verify_openai_tools(tool_calls=tool_calls)
                continue
            else:
                break

        return AgentResponse(streaming=stream, conversation=self._conversation, response=response_message.content)

    def __check_args(self, function, args) -> bool:
        """Check if the function has the correct number of arguments"""
        sig: inspect.Signature = inspect.signature(obj=function)
        params: MappingProxyType[str, inspect.Parameter] = sig.parameters

        for name in args:
            if name not in params:
                return False

        for name, param in params.items():
            if param.default is param.empty and name not in args:
                return False

        return True
    
    def __verify_openai_tools(self, tool_calls: List[ChatCompletionMessageToolCall]) -> None:
        for tool_call in tool_calls:
            function_name: str = tool_call.function.name
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
                self._logger.error(msg=e)
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

            image_file: str | bytes = self.__fs.read_bytes(path=image_path)
            image_bytes: bytes | None = image_file if isinstance(image_file, bytes) else None
            image_bytes = image_file.encode(encoding='utf-8') if isinstance(image_file, str) else image_file
            base64_image: str = base64.b64encode(s=image_bytes).decode(encoding='utf-8')
            self._logger.debug("image_path: ", image_path)

            search_function_response.append(
                {"type": "text", "text": f"file_name: {image_path}"})
            search_function_response.append({"type": "image_url", "image_url": {
                                            "url":  f"data:image/jpeg;base64,{base64_image}"}})
            search_function_response.append(
                {"type": "text", "text": f"HINT: The following kind of content might be related to this topic\n: {related_content}"})
            
        return search_function_response
