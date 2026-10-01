"""Safe (JSON based) serialization of conversation history stored in the distributed cache.

History must never be serialized with pickle: data read back from the cache is untrusted,
and unpickling attacker-controlled bytes leads to arbitrary code execution.
"""
import json
from typing import Any, List

HISTORY_KEY_PREFIX = "deeprag:history:"


def history_cache_key(session_id: str) -> str:
    """Build the cache key for a (server-validated) session id."""
    return f"{HISTORY_KEY_PREFIX}{session_id}"


def _to_jsonable(message: Any) -> dict:
    if isinstance(message, dict):
        return message
    model_dump = getattr(message, "model_dump", None)
    if callable(model_dump):
        return model_dump(exclude_none=True)
    raise TypeError(f"Unsupported history message type: {type(message).__name__}")


def serialize_history(history: List[Any]) -> str:
    """Serialize a conversation history to a JSON string."""
    return json.dumps([_to_jsonable(message) for message in history])


def deserialize_history(raw: str | bytes | None) -> List[dict]:
    """Deserialize a conversation history; returns an empty list for missing or malformed data."""
    if raw is None:
        return []
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        history = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return []
    if not isinstance(history, list) or not all(
            isinstance(message, dict) and isinstance(message.get("role"), str) for message in history):
        return []
    return history
