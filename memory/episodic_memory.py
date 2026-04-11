import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import ollama as ollama_client

load_dotenv()

EMBEDDING_DIM = 768


class EpisodicMemory:
    """
    Stores and retrieves past conversation episodes.
    Each episode = one full conversation session summary.
    Enables agents to remember past interactions across sessions.
    """

    def __init__(self):
        self.conn_params = {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "user": os.getenv("POSTGRES_USER", "agent_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "agent_pass"),
            "dbname": os.getenv("POSTGRES_DB", "agent_db"),
        }
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        self.ollama = ollama_client.Client(host=self.ollama_host)
        self._init_db()
        print("[EpisodicMemory] Ready.")

    def _get_conn(self):
        return psycopg2.connect(**self.conn_params)

    def _init_db(self):
        """Create episodes table."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS episodes (
                        id SERIAL PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        key_topics TEXT[] DEFAULT '{{}}',
                        outcome TEXT DEFAULT '',
                        embedding vector({EMBEDDING_DIM}),
                        message_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT NOW(),
                        metadata JSONB DEFAULT '{{}}'
                    );
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS episodes_session_idx
                    ON episodes (session_id);
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS episodes_embedding_idx
                    ON episodes
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 10);
                """)
                conn.commit()
        print("[EpisodicMemory] Database tables ready.")

    def _embed(self, text: str) -> list[float]:
        response = self.ollama.embeddings(
            model="nomic-embed-text",
            prompt=text,
        )
        return response["embedding"]

    # ─── Core Operations ──────────────────────────────────────

    def save_episode(
        self,
        session_id: str,
        messages: list[dict],
        model: str = "llama3.1:8b",
    ) -> dict:
        """
        Summarize a conversation and save it as an episode.
        Called at the end of each session.
        """
        if not messages:
            return {}

        # Build conversation text
        conversation = "\n".join([
            f"{m['role'].upper()}: {m['content'][:200]}"
            for m in messages
            if m.get("role") in ("user", "assistant")
        ])

        if not conversation.strip():
            return {}

        # Generate summary with LLM
        summary, key_topics, outcome = self._summarize_conversation(
            conversation=conversation,
            model=model,
        )

        # Embed the summary for semantic search
        embedding = self._embed(summary)

        # Store in Postgres
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO episodes
                        (session_id, summary, key_topics, outcome,
                         embedding, message_count, metadata)
                    VALUES (%s, %s, %s, %s, %s::vector, %s, %s)
                    RETURNING id
                    """,
                    (
                        session_id,
                        summary,
                        key_topics,
                        outcome,
                        str(embedding),
                        len(messages),
                        json.dumps({"model": model}),
                    ),
                )
                episode_id = cur.fetchone()[0]
                conn.commit()

        result = {
            "id": episode_id,
            "session_id": session_id,
            "summary": summary,
            "key_topics": key_topics,
            "outcome": outcome,
            "message_count": len(messages),
        }
        print(f"[EpisodicMemory] ✓ Saved episode {episode_id} for session '{session_id}'")
        return result

    def search_episodes(
        self,
        query: str,
        session_id: str = None,
        top_k: int = 3,
        threshold: float = 0.3,
        exclude_session: str = None,
    ) -> list[dict]:
        query_embedding = self._embed(query)
        embedding_str = str(query_embedding)

        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if session_id:
                    cur.execute(
                        """
                        SELECT id, session_id, summary, key_topics, outcome,
                            message_count, created_at,
                            1 - (embedding <=> %s::vector) AS similarity
                        FROM episodes
                        WHERE session_id = %s
                        AND 1 - (embedding <=> %s::vector) > %s
                        ORDER BY similarity DESC
                        LIMIT %s
                        """,
                        (embedding_str, session_id, embedding_str, threshold, top_k),
                    )
                elif exclude_session:
                    cur.execute(
                        """
                        SELECT id, session_id, summary, key_topics, outcome,
                            message_count, created_at,
                            1 - (embedding <=> %s::vector) AS similarity
                        FROM episodes
                        WHERE session_id != %s
                        AND 1 - (embedding <=> %s::vector) > %s
                        ORDER BY similarity DESC
                        LIMIT %s
                        """,
                        (embedding_str, exclude_session, embedding_str, threshold, top_k),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, session_id, summary, key_topics, outcome,
                            message_count, created_at,
                            1 - (embedding <=> %s::vector) AS similarity
                        FROM episodes
                        WHERE 1 - (embedding <=> %s::vector) > %s
                        ORDER BY similarity DESC
                        LIMIT %s
                        """,
                        (embedding_str, embedding_str, threshold, top_k),
                    )
                return [dict(r) for r in cur.fetchall()]

    def get_recent_episodes(
        self,
        limit: int = 5,
        exclude_session: str = None,
    ) -> list[dict]:
        """Get most recent episodes regardless of content."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if exclude_session:
                    cur.execute(
                        """
                        SELECT id, session_id, summary, key_topics,
                               outcome, message_count, created_at
                        FROM episodes
                        WHERE session_id != %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (exclude_session, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, session_id, summary, key_topics,
                               outcome, message_count, created_at
                        FROM episodes
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                return [dict(r) for r in cur.fetchall()]

    def get_all_episodes(self, session_id: str = None) -> list[dict]:
        """List all stored episodes."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if session_id:
                    cur.execute(
                        """
                        SELECT id, session_id, summary, key_topics,
                               outcome, message_count, created_at
                        FROM episodes
                        WHERE session_id = %s
                        ORDER BY created_at DESC
                        """,
                        (session_id,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, session_id, summary, key_topics,
                               outcome, message_count, created_at
                        FROM episodes
                        ORDER BY created_at DESC
                        """
                    )
                return [dict(r) for r in cur.fetchall()]

    def episode_count(self) -> int:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM episodes")
                return cur.fetchone()[0]

    def delete_episode(self, episode_id: int):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM episodes WHERE id = %s", (episode_id,))
                conn.commit()

    def format_episodes_for_prompt(self, episodes: list[dict]) -> str:
        """Format episodes into LLM-readable context."""
        if not episodes:
            return ""
        parts = []
        for ep in episodes:
            topics = ", ".join(ep.get("key_topics") or [])
            parts.append(
                f"[Past Session: {ep['session_id']} | "
                f"Topics: {topics or 'general'}]\n"
                f"Summary: {ep['summary'][:300]}\n"
                f"Outcome: {ep.get('outcome', '')[:150]}"
            )
        return "\n\n---\n\n".join(parts)

    # ─── Private: LLM Summarization ───────────────────────────

    def _summarize_conversation(
        self,
        conversation: str,
        model: str,
    ) -> tuple[str, list[str], str]:
        """Use LLM to summarize a conversation into episode fields."""

        prompt = f"""Summarize this conversation into 3 parts.
Return ONLY a JSON object with these fields:
{{
  "summary": "2-3 sentence summary of what was discussed",
  "key_topics": ["topic1", "topic2", "topic3"],
  "outcome": "what was accomplished or concluded"
}}

Conversation:
{conversation[:3000]}

Return ONLY valid JSON:"""

        try:
            response = self.ollama.chat(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a summarization assistant. Return ONLY valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            raw = response["message"]["content"].strip()

            # Clean markdown
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            if "{" in raw and "}" in raw:
                raw = raw[raw.index("{"):raw.rindex("}") + 1]

            data = json.loads(raw)
            summary = data.get("summary", conversation[:200])
            key_topics = data.get("key_topics", [])
            outcome = data.get("outcome", "")

            if isinstance(key_topics, str):
                key_topics = [key_topics]

            return summary, key_topics[:5], outcome

        except Exception as e:
            print(f"[EpisodicMemory] Summarization failed: {e}")
            # Fallback — use first 300 chars of conversation
            return conversation[:300], [], ""