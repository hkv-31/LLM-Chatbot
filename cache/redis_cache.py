"""Redis-backed response cache for the LLM chatbot demo."""
from __future__ import annotations
import hashlib, json, os
import redis

class RedisCache:
    def __init__(self, url=None, ttl=None, prefix="llm-cache:"):
        self.url = url or os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
        self.default_ttl = ttl if ttl is not None else int(os.getenv("CACHE_TTL", "60"))
        self.prefix = prefix
        self.client = redis.Redis.from_url(self.url, decode_responses=True)

    def ping(self):
        return bool(self.client.ping())

    def make_key(self, messages, model):
        payload = {"model": model, "messages": messages}
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"{self.prefix}{digest}"

    def get(self, key):
        return self.client.get(key)

    def set(self, key, value, ttl=None):
        expiry = self.default_ttl if ttl is None else ttl
        return bool(self.client.set(key, value, ex=expiry))

    def exists(self, key):
        return bool(self.client.exists(key))

    def ttl(self, key):
        return int(self.client.ttl(key))

    def delete(self, key):
        return bool(self.client.delete(key))

    def clear(self):
        keys = list(self.client.scan_iter(match=f"{self.prefix}*"))
        return int(self.client.delete(*keys)) if keys else 0
