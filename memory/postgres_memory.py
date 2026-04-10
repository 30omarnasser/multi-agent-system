import os
import json
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import ollama as ollama_client

load_dotenv()


class PostgresMemory:
    """
    Long-term memory using PostgreSQL + pgvector.
    Uses Ollama (nomic-embed-text) for local embeddings — no external APIs needed.
    Facts persist forever — survive restarts, Redis TTL expiry, everything.
    """

    EMBEDDING_DIM = 768  # nomic-embed-text produces 768-dim vectors

    def __init__(self):
        self.conn_params = {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "user": os.getenv("POSTGRES_USER", "agent_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "agent_pass"),
            "dbname": os.getenv("POSTGRES_DB", "agent_db"),
        }
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama = ollama_client.Client(host=self.ollama_host)
        self._pull_embedding_model()
        self._init_db_with_retry()
        print("[PostgresMemory] Ready.")

    def _init_db_with_retry(self, max_retries: int = 10, wait: int = 3):
        """Wait for Postgres to be ready before initializing."""
        import time
        for attempt in range(max_retries):
            try:
                self._init_db()
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[PostgresMemory] Postgres not ready, retrying in {wait}s... ({attempt + 1}/{max_retries})")
                    time.sleep(wait)
                else:
                    raise RuntimeError(f"Could not connect to Postgres after {max_retries} attempts: {e}")

    def _pull_embedding_model(self):
        """Pull the embedding model if not already downloaded."""
        try:
            self.ollama.embeddings(model="nomic-embed-text", prompt="test")
            print("[PostgresMemory] nomic-embed-text ready.")
        except Exception:
            print("[PostgresMemory] Pulling nomic-embed-text model...")
            self.ollama.pull("nomic-embed-text")
            print("[PostgresMemory] nomic-embed-text downloaded.")

    def _get_conn(self):
        return psycopg2.connect(**self.conn_params)

    def _init_db(self):
        """Create tables and enable pgvector extension."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS facts (
                        id SERIAL PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        fact TEXT NOT NULL,
                        category TEXT DEFAULT 'general',
                        embedding vector({self.EMBEDDING_DIM}),
                        created_at TIMESTAMP DEFAULT NOW(),
                        metadata JSONB DEFAULT '{{}}'
                    );
                """)
                conn.commit()
        print("[PostgresMemory] Database initialized.")

    def _embed(self, text: str) -> list[float]:
        """Generate embedding vector using Ollama locally."""
        response = self.ollama.embeddings(
            model="nomic-embed-text",
            prompt=text,
        )
        return response["embedding"]

    # ─── Core Operations ──────────────────────────────────────

    def save_fact(self, session_id: str, fact: str, category: str = "general", metadata: dict = None):
        """Store an important fact with its embedding vector."""
        embedding = self._embed(fact)
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO facts (session_id, fact, category, embedding, metadata)
                    VALUES (%s, %s, %s, %s::vector, %s)
                    """,
                    (session_id, fact, category, str(embedding), json.dumps(metadata or {})),
                )
                conn.commit()
        print(f"[PostgresMemory] Saved: '{fact[:80]}'")

    def search_facts(self, query: str, session_id: str = None, top_k: int = 5, threshold: float = 0.3) -> list[dict]:
        """Search for relevant facts using semantic similarity."""
        query_embedding = self._embed(query)
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if session_id:
                    cur.execute(
                        """
                        SELECT id, session_id, fact, category, created_at,
                               1 - (embedding <=> %s::vector) AS similarity
                        FROM facts
                        WHERE session_id = %s
                          AND 1 - (embedding <=> %s::vector) > %s
                        ORDER BY similarity DESC
                        LIMIT %s
                        """,
                        (str(query_embedding), session_id, str(query_embedding), threshold, top_k),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, session_id, fact, category, created_at,
                               1 - (embedding <=> %s::vector) AS similarity
                        FROM facts
                        WHERE 1 - (embedding <=> %s::vector) > %s
                        ORDER BY similarity DESC
                        LIMIT %s
                        """,
                        (str(query_embedding), str(query_embedding), threshold, top_k),
                    )
                return [dict(r) for r in cur.fetchall()]

    def get_all_facts(self, session_id: str = None) -> list[dict]:
        """Get all stored facts, optionally filtered by session."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if session_id:
                    cur.execute(
                        "SELECT id, session_id, fact, category, created_at FROM facts WHERE session_id = %s ORDER BY created_at DESC",
                        (session_id,),
                    )
                else:
                    cur.execute(
                        "SELECT id, session_id, fact, category, created_at FROM facts ORDER BY created_at DESC"
                    )
                return [dict(r) for r in cur.fetchall()]

    def delete_fact(self, fact_id: int):
        """Delete a specific fact by ID."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM facts WHERE id = %s", (fact_id,))
                conn.commit()

    def clear_session_facts(self, session_id: str):
        """Delete all facts for a session."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM facts WHERE session_id = %s", (session_id,))
                conn.commit()
        print(f"[PostgresMemory] Cleared facts for: {session_id}")

    def fact_count(self, session_id: str = None) -> int:
        """Count stored facts."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                if session_id:
                    cur.execute("SELECT COUNT(*) FROM facts WHERE session_id = %s", (session_id,))
                else:
                    cur.execute("SELECT COUNT(*) FROM facts")
                return cur.fetchone()[0]