import json
import pickle
import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(ROOT / "distributed_cache"))
sys.path.insert(0, str(ROOT / "utils"))

from history_serializer import serialize_history, deserialize_history, history_cache_key  # noqa: E402
from session_tokens import issue_session_token, verify_session_token  # noqa: E402

SECRET = "s" * 32


class _FakeMessage:
    def model_dump(self, exclude_none: bool = False) -> dict:
        return {"role": "assistant", "content": "", "tool_calls": [{"id": "1"}]}


def test_session_token_round_trip():
    token = issue_session_token(SECRET)
    session_id = verify_session_token(token, SECRET)
    assert session_id is not None and token.startswith(session_id)
    assert history_cache_key(session_id) == f"deeprag:history:{session_id}"


def test_session_tokens_are_unique():
    assert issue_session_token(SECRET) != issue_session_token(SECRET)


def test_session_token_rejects_tampering_and_foreign_ids():
    token = issue_session_token(SECRET)
    session_id, signature = token.split(".")
    other_id = ("0" if session_id[0] != "0" else "1") + session_id[1:]
    assert verify_session_token(f"{other_id}.{signature}", SECRET) is None
    assert verify_session_token(token, "x" * 32) is None
    assert verify_session_token(session_id, SECRET) is None
    assert verify_session_token("session_id", SECRET) is None
    assert verify_session_token(None, SECRET) is None
    assert verify_session_token(token, "") is None


def test_history_json_round_trip():
    history = [{"role": "system", "content": "hi"}, _FakeMessage(), {"role": "tool", "content": [{"type": "text"}]}]
    raw = serialize_history(history)
    assert json.loads(raw)[1]["tool_calls"] == [{"id": "1"}]
    assert deserialize_history(raw) == json.loads(raw)
    assert deserialize_history(raw.encode("utf-8")) == json.loads(raw)


class _Exploit:
    def __reduce__(self):
        return (exec, ("raise SystemExit('pickle payload executed')",))


def test_history_rejects_pickle_and_malformed_payloads():
    pickled = base64.b64encode(pickle.dumps(_Exploit()))
    assert deserialize_history(pickled) == []
    assert deserialize_history(pickle.dumps(_Exploit())) == []
    assert deserialize_history(None) == []
    assert deserialize_history('{"role": "user"}') == []
    assert deserialize_history('[1, 2]') == []
    assert deserialize_history('[{"content": "no role"}]') == []
