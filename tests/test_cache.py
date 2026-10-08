import os
import pytest
from cache.redis_cache import RedisCache

@pytest.fixture
def cache():
    client = RedisCache(url=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"), ttl=2, prefix="test-llm-cache:")
    try:
        client.ping()
    except Exception as exc:
        pytest.skip(f"Redis is not running: {exc}")
    client.clear()
    yield client
    client.clear()

def test_key_is_deterministic(cache):
    messages = [{"role": "user", "content": "What is RAG?"}]
    assert cache.make_key(messages, "test-model") == cache.make_key(messages, "test-model")

def test_different_history_produces_different_key(cache):
    first = [{"role": "user", "content": "What is RAG?"}]
    second = [{"role": "user", "content": "Explain embeddings first."}, {"role": "assistant", "content": "Embeddings are vectors."}, {"role": "user", "content": "What is RAG?"}]
    assert cache.make_key(first, "test-model") != cache.make_key(second, "test-model")

def test_set_get_and_ttl(cache):
    key = cache.make_key([{"role": "user", "content": "hello"}], "test-model")
    assert cache.get(key) is None
    assert cache.set(key, "cached response", ttl=2)
    assert cache.get(key) == "cached response"
    assert cache.exists(key)
    assert 0 < cache.ttl(key) <= 2

def test_delete(cache):
    key = cache.make_key([{"role": "user", "content": "delete me"}], "test-model")
    cache.set(key, "value", ttl=60)
    assert cache.delete(key)
    assert cache.get(key) is None
