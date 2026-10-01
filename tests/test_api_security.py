import base64
import json
import pickle

import fsspec
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function
from pydantic import ValidationError

from security_fixtures import API_KEY, SESSION_SECRET, FakeRedis, fake_redis  # noqa: F401

import api
import smart_agent_factory
from history import History
from models import Settings
from session_tokens import issue_session_token

HEADERS = {"X-API-Key": API_KEY}


class _FakeAgent:
    def __init__(self, init_history=None, **kwargs) -> None:
        self._conversation = list(init_history or [])

    def run(self, user_input, **kwargs):
        self._conversation.append({"role": "user", "content": user_input})

        class _Response:
            response = f"echo:{user_input}"
        return _Response()


@pytest.fixture
def client(monkeypatch, fake_redis):
    monkeypatch.setattr(smart_agent_factory.redis, "Redis", fake_redis)
    monkeypatch.setattr(api.SmartAgentFactory, "create_smart_agent", staticmethod(
        lambda fs, settings, session_id: _FakeAgent(
            init_history=smart_agent_factory.deserialize_history(
                fake_redis.store.get(smart_agent_factory.history_cache_key(session_id))))))
    app = FastAPI()
    api.Server(app=app, searchVectorFunction=None)
    return TestClient(app, raise_server_exceptions=False)


def _invoke(client, session_id, question="hi", headers=HEADERS):
    return client.post("/deepRAG/invoke", headers=headers,
                       json={"input": {"question": question, "session_id": session_id}})


# --- API authentication / session ownership -------------------------------------------------

@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}, {"X-API-Key": ""}])
def test_endpoints_require_api_key(client, headers):
    assert client.post("/session", headers=headers).status_code == 401
    assert _invoke(client, issue_session_token(SESSION_SECRET), headers=headers).status_code == 401
    assert client.post("/vectorRAG/invoke", headers=headers, json={"input": "q"}).status_code == 401


def test_session_endpoint_issues_unique_tokens(client):
    first = client.post("/session", headers=HEADERS)
    second = client.post("/session", headers=HEADERS)
    assert first.status_code == 200
    assert first.json()["session_id"] != second.json()["session_id"]


@pytest.mark.parametrize("session_id", ["victim", "session_id", "", None, "a" * 32,
                                        "0" * 32 + "." + "0" * 64])
def test_forged_session_ids_are_forbidden(client, fake_redis, session_id):
    response = _invoke(client, session_id)
    assert response.status_code == 403
    assert fake_redis.store == {}


def test_cannot_read_or_overwrite_raw_redis_keys(client, fake_redis):
    fake_redis.store["victim"] = json.dumps([{"role": "user", "content": "secret"}])
    assert _invoke(client, "victim").status_code == 403
    assert fake_redis.store["victim"] == json.dumps([{"role": "user", "content": "secret"}])


def test_sessions_are_isolated(client, fake_redis):
    alice = client.post("/session", headers=HEADERS).json()["session_id"]
    bob = client.post("/session", headers=HEADERS).json()["session_id"]

    assert _invoke(client, alice, "alice-secret").json()["output"] == "echo:alice-secret"
    assert _invoke(client, bob, "bob-question").status_code == 200

    alice_key = smart_agent_factory.history_cache_key(alice.split(".")[0])
    bob_key = smart_agent_factory.history_cache_key(bob.split(".")[0])
    assert "alice-secret" in fake_redis.store[alice_key]
    assert "alice-secret" not in fake_redis.store[bob_key]
    assert all(key.startswith("deeprag:history:") for key in fake_redis.store)


def test_tampered_token_cannot_access_other_session(client, fake_redis):
    alice = client.post("/session", headers=HEADERS).json()["session_id"]
    _invoke(client, alice, "alice-secret")
    mallory = client.post("/session", headers=HEADERS).json()["session_id"]
    forged = alice.split(".")[0] + "." + mallory.split(".")[1]
    assert _invoke(client, forged).status_code == 403


# --- Redis persistence via SmartAgentFactory ------------------------------------------------

@pytest.fixture
def factory_env(monkeypatch, fake_redis):
    monkeypatch.setattr(smart_agent_factory.redis, "Redis", fake_redis)
    for name in ["SearchClient", "AzureOpenAI", "SearchVectorFunction"]:
        monkeypatch.setattr(smart_agent_factory, name, lambda *a, **k: object())
    monkeypatch.setattr(smart_agent_factory, "agent_configuration_from_dict", lambda data: data)
    monkeypatch.setattr(smart_agent_factory, "Smart_Agent", _FakeAgent)
    fs = fsspec.filesystem("memory")
    fs.pipe("/prompt.yaml", b"name: test\n")
    settings = Settings()  # type: ignore
    settings.smart_agent_prompt_location = "/prompt.yaml"
    return fs, settings


def test_history_persisted_as_json_with_ttl(factory_env, fake_redis):
    fs, settings = factory_env
    agent = _FakeAgent(init_history=[{"role": "system", "content": "sys"}])
    agent._conversation.append(ChatCompletionMessage(
        role="assistant", content="",
        tool_calls=[ChatCompletionMessageToolCall(
            id="call_1", type="function", function=Function(name="search", arguments="{}"))]))
    smart_agent_factory.SmartAgentFactory.persist_history(smart_agent=agent, session_id="abc", settings=settings)

    raw = fake_redis.store["deeprag:history:abc"]
    stored = json.loads(raw)
    assert stored[1]["tool_calls"][0]["function"]["name"] == "search"
    assert fake_redis.ttl["deeprag:history:abc"] == 3600

    reloaded = smart_agent_factory.SmartAgentFactory.create_smart_agent(fs=fs, settings=settings, session_id="abc")
    assert reloaded._conversation == stored


class _Exploit:
    def __reduce__(self):
        return (exec, ("raise SystemExit('pickle payload executed')",))


def test_legacy_or_malicious_pickle_entry_is_ignored(factory_env, fake_redis):
    fs, settings = factory_env
    fake_redis.store["deeprag:history:abc"] = base64.b64encode(pickle.dumps(_Exploit())).decode()
    agent = smart_agent_factory.SmartAgentFactory.create_smart_agent(fs=fs, settings=settings, session_id="abc")
    assert agent._conversation == []


def test_no_session_does_not_touch_redis(factory_env, fake_redis):
    fs, settings = factory_env
    fake_redis.store[smart_agent_factory.history_cache_key("None")] = "[]"
    agent = smart_agent_factory.SmartAgentFactory.create_smart_agent(fs=fs, settings=settings, session_id=None)
    assert agent._conversation == []


# --- services.History -----------------------------------------------------------------------

def _seed(cache, history):
    History(session_id="s1", cache=cache).set_history(history)
    return History(session_id="s1", cache=cache)


def test_history_service_round_trip_and_namespacing(fake_redis):
    cache = fake_redis()
    history = _seed(cache, [{"role": "user", "content": "q"}])
    assert history.history == [{"role": "user", "content": "q"}]
    assert list(cache.store) == ["deeprag:history:s1"]
    json.loads(cache.store["deeprag:history:s1"])


def test_history_service_clean_up(fake_redis):
    cache = fake_redis()
    history = _seed(cache, [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "q2"},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "q3"},
    ])
    history.clean_up_history(max_q_with_detail_hist=1, max_q_to_keep=2)
    remaining = [m["content"] for m in json.loads(cache.store["deeprag:history:s1"])]
    assert remaining == ["sys", "a2", "q3"]


def test_history_service_reset_to_last_question(fake_redis):
    cache = fake_redis()
    history = _seed(cache, [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
        {"role": "tool", "content": "t"},
    ])
    history.reset_history_to_last_question()
    assert json.loads(cache.store["deeprag:history:s1"]) == [{"role": "user", "content": "q1"}]


def test_history_service_ignores_pickle(fake_redis):
    cache = fake_redis()
    cache.store["deeprag:history:s1"] = base64.b64encode(pickle.dumps(_Exploit()))
    history = History(session_id="s1", cache=cache)
    assert history.history == []
    history.reset_history_to_last_question()
    history.clean_up_history()


# --- Settings fail closed -------------------------------------------------------------------

@pytest.mark.parametrize("name,value", [
    ("API_KEY", None), ("API_KEY", "short"), ("SESSION_SECRET", None), ("SESSION_SECRET", "s" * 31)])
def test_settings_require_strong_secrets(monkeypatch, name, value):
    if value is None:
        monkeypatch.delenv(name)
    else:
        monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        Settings()  # type: ignore
