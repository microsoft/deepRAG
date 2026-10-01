import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent / "src"
for package in ["api", "models", "utils", "agents", "functions", "distributed_cache", "services"]:
    sys.path.insert(0, str(ROOT / package))

API_KEY = "k" * 20
SESSION_SECRET = "s" * 40
_REQUIRED_ENV = [
    "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_EMB_DEPLOYMENT",
    "AZURE_OPENAI_CHAT_DEPLOYMENT", "AZURE_OPENAI_API_VERSION", "AZURE_SEARCH_ENDPOINT",
    "AZURE_SEARCH_KEY", "AZURE_SEARCH_INDEX_NAME", "AZURE_AI_VISION_API_KEY",
    "AZURE_AI_VISION_ENDPOINT", "SMART_AGENT_PROMPT_LOCATION", "IMAGE_PATH",
    "AZURE_REDIS_ENDPOINT", "AZURE_REDIS_KEY", "AZURE_STORAGE_ACCOUNT_KEY",
    "AZURE_STORAGE_ACCOUNT_NAME", "AZURE_CONTAINER_NAME",
]
for name in _REQUIRED_ENV:
    os.environ.setdefault(name, "test")
os.environ["API_KEY"] = API_KEY
os.environ["SESSION_SECRET"] = SESSION_SECRET


class FakeRedis:
    """In-memory stand-in for redis.Redis shared across instances."""
    store: dict = {}
    ttl: dict = {}

    def __init__(self, *args, **kwargs) -> None:
        pass

    def get(self, name):
        return self.store.get(name)

    def set(self, name, value, ex=None, **kwargs):
        if not isinstance(value, (str, bytes, int, float)):
            raise TypeError("redis only accepts str/bytes/numbers")
        self.store[name] = value
        self.ttl[name] = ex
        return True

    def delete(self, *names):
        for name in names:
            self.store.pop(name, None)


@pytest.fixture
def fake_redis():
    FakeRedis.store = {}
    FakeRedis.ttl = {}
    return FakeRedis
