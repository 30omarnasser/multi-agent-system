import redis
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class RedisMemory:
    """
    Manages short-term conversation memory using Redis.
    Each session gets its own key. History survives server restarts.
    """

    def __init__(self, ttl_seconds: int = 3600):
        """
        ttl_seconds: how long a session lives in Redis (default 1 hour).
        """
        self.client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,  # returns strings, not bytes
        )
        self.ttl = ttl_seconds
        print(f"[RedisMemory] Connected. TTL={ttl_seconds}s")

    # ─── Core Operations ──────────────────────────────────────

    def save_message(self, session_id: str, role: str, content: str):
        """Append a single message to a session's history."""
        key = self._key(session_id)
        message = json.dumps({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        })
        # RPUSH appends to the end of a Redis list
        self.client.rpush(key, message)
        # Reset TTL on every new message — active sessions stay alive
        self.client.expire(key, self.ttl)

    def get_history(self, session_id: str) -> list[dict]:
        """Retrieve full conversation history for a session."""
        key = self._key(session_id)
        # LRANGE gets all items from the list
        raw_messages = self.client.lrange(key, 0, -1)
        return [json.loads(m) for m in raw_messages]

    def clear_session(self, session_id: str):
        """Delete all history for a session."""
        self.client.delete(self._key(session_id))
        print(f"[RedisMemory] Session cleared: {session_id}")

    def session_exists(self, session_id: str) -> bool:
        """Check if a session has any history."""
        return self.client.exists(self._key(session_id)) > 0

    def get_all_sessions(self) -> list[str]:
        """List all active session IDs."""
        keys = self.client.keys("session:*")
        # Strip the "session:" prefix to return just the IDs
        return [k.replace("session:", "") for k in keys]

    def get_session_ttl(self, session_id: str) -> int:
        """How many seconds until this session expires."""
        return self.client.ttl(self._key(session_id))

    # ─── Helper ───────────────────────────────────────────────

    def _key(self, session_id: str) -> str:
        """Namespace all keys under 'session:'"""
        return f"session:{session_id}"