from typing_extensions import Literal
from datetime import datetime
from unittest.mock import Mock
from openai import AzureOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessage, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message_tool_call import Function
from agents import Smart_Agent, AgentResponse
import pytest_mock

def setup_mock_azure_openai_with_side_effects(
        mocker: pytest_mock.MockerFixture,
        chat_completion_response: str,
        chat_completion_finish_reason: Literal["stop", "tool_calls"] = 'stop',
        chat_completion_tool_calls: list[ChatCompletionMessageToolCall] = [],
        chat_completion_side_effect: list[ChatCompletion] = []
) -> Mock:
    mockAzureOpenAI: Mock | Mock = mocker.Mock(target=AzureOpenAI, chat=mocker.Mock(
        completions=mocker.Mock(create=mocker.Mock())))
    mockAzureOpenAI.chat.completions.create.side_effect = [ChatCompletion(
        id="foo",
        model="gpt-4",
        object="chat.completion",
        choices=[
            Choice(
                finish_reason=chat_completion_finish_reason,
                index=0,
                message=ChatCompletionMessage(
                    content=chat_completion_response,
                    role="assistant",
                    tool_calls=chat_completion_tool_calls,
                ),
            )
        ],
        created=int(datetime.now().timestamp())
    ),
        *chat_completion_side_effect
    ]

    return mockAzureOpenAI


def setup_mock_azure_openai(
    mocker: pytest_mock.MockerFixture,
    chat_completion_response: str,
    chat_completion_finish_reason: Literal["stop", "tool_calls"] = 'stop',
    chat_completion_tool_calls: list[ChatCompletionMessageToolCall] = []
) -> Mock:
    mockAzureOpenAI: Mock | Mock = mocker.Mock(target=AzureOpenAI, chat=mocker.Mock(
        completions=mocker.Mock(create=mocker.Mock())))
    mockAzureOpenAI.chat.completions.create.return_value = ChatCompletion(
        id="foo",
        model="gpt-4",
        object="chat.completion",
        choices=[
            Choice(
                finish_reason=chat_completion_finish_reason,
                index=0,
                message=ChatCompletionMessage(
                    content=chat_completion_response,
                    role="assistant",
                    tool_calls=chat_completion_tool_calls,
                ),
            )
        ],
        created=int(datetime.now().timestamp())
    )

    return mockAzureOpenAI


def setup(
        mocker: pytest_mock.MockerFixture,
        mockAzureOpenAI: Mock) -> Smart_Agent:

    return Smart_Agent(
        logger=mocker.Mock(),
        client=mockAzureOpenAI,
        agent_configuration=mocker.Mock(tools=[]),
        search_vector_function=mocker.Mock(
            search=mocker.Mock(return_value=[])),
        history=mocker.Mock(),
    )


def test_for_valid_response(mocker: pytest_mock.MockerFixture) -> None:
    """Test for a valid response from the smart agent"""
    chat_completion_response: str = "Assistant Response"
    smart_agent_prompt: str = "Hello World"
    mockAzureOpenAI = setup_mock_azure_openai(
        mocker=mocker, chat_completion_response=chat_completion_response)
    smart_agent: Smart_Agent = setup(
        mocker=mocker, mockAzureOpenAI=mockAzureOpenAI)
    smart_agent_response: AgentResponse = smart_agent.run(user_input=smart_agent_prompt)

    assert smart_agent_response.response == chat_completion_response


def test_for_no_user_input(mocker: pytest_mock.MockerFixture) -> None:
    """Test for no user input"""
    smart_agent_prompt = None
    mockAzureOpenAI = setup_mock_azure_openai(
        mocker=mocker, chat_completion_response="Assistant Response")
    smart_agent: Smart_Agent = setup(
        mocker=mocker, mockAzureOpenAI=mockAzureOpenAI)
    smart_agent_response: AgentResponse = smart_agent.run(
        user_input=smart_agent_prompt)

    assert smart_agent_response.response == smart_agent._conversation[1]["content"]


def test_if_conversation_is_not_none(mocker: pytest_mock.MockerFixture) -> None:
    """Test if conversation is not None"""
    conversation_item = {"role": "user",
                         "content": "Initial Conversation Item"}
    mockAzureOpenAI = setup_mock_azure_openai(
        mocker=mocker, chat_completion_response="Assistant Response")
    smart_agent: Smart_Agent = setup(
        mocker=mocker, mockAzureOpenAI=mockAzureOpenAI)
    smart_agent_response: AgentResponse = smart_agent.run(
        user_input="Hello World", conversation=[conversation_item])

    assert conversation_item in smart_agent_response.conversation


def test_for_max_run_count(mocker: pytest_mock.MockerFixture) -> None:
    """Test for max run count"""
    chat_completion_tools: list[ChatCompletionMessageToolCall] = [
        ChatCompletionMessageToolCall(
            id="foo", type="function", function=Function(name="test", arguments="{}"))
    ]

    mockAzureOpenAI = setup_mock_azure_openai(
        mocker=mocker,
        chat_completion_response="Assistant Response",
        chat_completion_finish_reason="tool_calls",
        chat_completion_tool_calls=chat_completion_tools
    )

    smart_agent: Smart_Agent = setup(
        mocker=mocker,
        mockAzureOpenAI=mockAzureOpenAI
    )

    smart_agent_response: AgentResponse = smart_agent.run(
        user_input="Hello World")

    assert smart_agent_response.response == "I am unable to answer this question at the moment, please ask another question."


def test_for_tool_calls(mocker: pytest_mock.MockerFixture) -> None:
    """Test for tool calls"""
    chat_completion_response: str = "Assistant Response"
    tool_id: str = "foo"
    tool_name: str = "search"
    tool_message = {'tool_call_id': tool_id,
                    'role': 'tool', 'name': tool_name, 'content': []}
    chat_completion_side_effects: list[ChatCompletion] = [
        ChatCompletion(
            id=tool_id,
            model="gpt-4",
            object="chat.completion",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(
                        content=chat_completion_response,
                        role="assistant",
                    ),
                )
            ],
            created=int(datetime.now().timestamp())
        )
    ]

    chat_completion_tools: list[ChatCompletionMessageToolCall] = [
        ChatCompletionMessageToolCall(
            id="foo",
            type="function",
            function=Function(
                name=tool_name,
                arguments="{\"args\": \"Hello World\", \"kwargs\": \"Hello World\"}"
            )
        )
    ]

    mockAzureOpenAI: Mock = setup_mock_azure_openai_with_side_effects(
        mocker=mocker,
        chat_completion_response="Assistant Response",
        chat_completion_finish_reason="tool_calls",
        chat_completion_tool_calls=chat_completion_tools,
        chat_completion_side_effect=chat_completion_side_effects
    )

    smart_agent: Smart_Agent = setup(
        mocker=mocker,
        mockAzureOpenAI=mockAzureOpenAI
    )

    smart_agent_response: AgentResponse = smart_agent.run(
        user_input="Hello World")

    assert smart_agent_response.response == chat_completion_response
    assert tool_message in smart_agent_response.conversation
