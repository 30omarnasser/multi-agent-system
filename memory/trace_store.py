import os
import json
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class TraceStore:
    """
    Stores full agent pipeline execution traces.
    Each run gets a trace_id. Each agent step gets a span.
    """

    def __init__(self):
        self.conn_params = {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "user": os.getenv("POSTGRES_USER", "agent_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "agent_pass"),
            "dbname": os.getenv("POSTGRES_DB", "agent_db"),
        }
        self._init_db()
        print("[TraceStore] Ready.")

    def _get_conn(self):
        return psycopg2.connect(**self.conn_params)

    def _init_db(self):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                # Main trace table — one row per pipeline run
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS traces (
                        id SERIAL PRIMARY KEY,
                        trace_id TEXT UNIQUE NOT NULL,
                        session_id TEXT NOT NULL,
                        user_message TEXT NOT NULL,
                        final_response TEXT DEFAULT '',
                        agents_used TEXT[] DEFAULT '{}',
                        total_duration_ms INTEGER DEFAULT 0,
                        critique_score INTEGER DEFAULT 0,
                        had_revision BOOLEAN DEFAULT FALSE,
                        task_type TEXT DEFAULT 'simple',
                        status TEXT DEFAULT 'running',
                        created_at TIMESTAMP DEFAULT NOW(),
                        completed_at TIMESTAMP,
                        metadata JSONB DEFAULT '{}'
                    );
                """)
                # Spans table — one row per agent step
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS trace_spans (
                        id SERIAL PRIMARY KEY,
                        trace_id TEXT NOT NULL REFERENCES traces(trace_id),
                        agent_name TEXT NOT NULL,
                        step_index INTEGER NOT NULL,
                        status TEXT DEFAULT 'success',
                        duration_ms INTEGER DEFAULT 0,
                        input_summary TEXT DEFAULT '',
                        output_summary TEXT DEFAULT '',
                        details JSONB DEFAULT '{}',
                        started_at TIMESTAMP DEFAULT NOW(),
                        completed_at TIMESTAMP
                    );
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS traces_session_idx
                    ON traces (session_id);
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS traces_created_idx
                    ON traces (created_at DESC);
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS spans_trace_idx
                    ON trace_spans (trace_id);
                """)
                conn.commit()
        print("[TraceStore] Tables ready.")

    # ─── Trace Lifecycle ──────────────────────────────────────

    def create_trace(self, session_id: str, user_message: str) -> str:
        """Create a new trace and return its trace_id."""
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO traces (trace_id, session_id, user_message)
                    VALUES (%s, %s, %s)
                    """,
                    (trace_id, session_id, user_message),
                )
                conn.commit()
        print(f"[TraceStore] Created trace: {trace_id}")
        return trace_id

    def complete_trace(
        self,
        trace_id: str,
        final_response: str,
        agents_used: list[str],
        total_duration_ms: int,
        critique_score: int,
        had_revision: bool,
        task_type: str,
        status: str = "success",
    ):
        """Mark a trace as complete with final results."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE traces SET
                        final_response = %s,
                        agents_used = %s,
                        total_duration_ms = %s,
                        critique_score = %s,
                        had_revision = %s,
                        task_type = %s,
                        status = %s,
                        completed_at = NOW()
                    WHERE trace_id = %s
                    """,
                    (
                        final_response[:2000],
                        agents_used,
                        total_duration_ms,
                        critique_score,
                        had_revision,
                        task_type,
                        status,
                        trace_id,
                    ),
                )
                conn.commit()

    def add_span(
        self,
        trace_id: str,
        agent_name: str,
        step_index: int,
        duration_ms: int,
        input_summary: str,
        output_summary: str,
        status: str = "success",
        details: dict = None,
    ):
        """Add an agent execution span to a trace."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO trace_spans
                        (trace_id, agent_name, step_index, status,
                         duration_ms, input_summary, output_summary,
                         details, completed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        trace_id,
                        agent_name,
                        step_index,
                        status,
                        duration_ms,
                        input_summary[:500],
                        output_summary[:500],
                        json.dumps(details or {}),
                    ),
                )
                conn.commit()

    # ─── Retrieval ────────────────────────────────────────────

    def get_trace(self, trace_id: str) -> dict:
        """Get full trace with all spans."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM traces WHERE trace_id = %s",
                    (trace_id,),
                )
                trace = cur.fetchone()
                if not trace:
                    return {}
                trace = dict(trace)

                cur.execute(
                    """
                    SELECT * FROM trace_spans
                    WHERE trace_id = %s
                    ORDER BY step_index ASC
                    """,
                    (trace_id,),
                )
                trace["spans"] = [dict(r) for r in cur.fetchall()]
                return trace

    def list_traces(
        self,
        session_id: str = None,
        limit: int = 20,
    ) -> list[dict]:
        """List recent traces, optionally filtered by session."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if session_id:
                    cur.execute(
                        """
                        SELECT trace_id, session_id, user_message,
                               agents_used, total_duration_ms,
                               critique_score, had_revision, task_type,
                               status, created_at, completed_at
                        FROM traces
                        WHERE session_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (session_id, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT trace_id, session_id, user_message,
                               agents_used, total_duration_ms,
                               critique_score, had_revision, task_type,
                               status, created_at, completed_at
                        FROM traces
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                return [dict(r) for r in cur.fetchall()]

    def get_stats(self) -> dict:
        """Aggregate stats across all traces."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) as total_traces,
                        AVG(total_duration_ms) as avg_duration_ms,
                        AVG(critique_score) as avg_score,
                        SUM(CASE WHEN had_revision THEN 1 ELSE 0 END) as revision_count,
                        SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
                    FROM traces
                    WHERE status != 'running'
                """)
                row = dict(cur.fetchone())

                cur.execute("""
                    SELECT task_type, COUNT(*) as count
                    FROM traces
                    WHERE status != 'running'
                    GROUP BY task_type
                    ORDER BY count DESC
                """)
                row["by_task_type"] = {r["task_type"]: r["count"] for r in cur.fetchall()}

                cur.execute("""
                    SELECT agent_name, AVG(duration_ms) as avg_ms, COUNT(*) as calls
                    FROM trace_spans
                    GROUP BY agent_name
                    ORDER BY avg_ms DESC
                """)
                row["agent_performance"] = [dict(r) for r in cur.fetchall()]

                return row

    def delete_trace(self, trace_id: str):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM trace_spans WHERE trace_id = %s",
                    (trace_id,),
                )
                cur.execute(
                    "DELETE FROM traces WHERE trace_id = %s",
                    (trace_id,),
                )
                conn.commit()

    def clear_old_traces(self, days_old: int = 7) -> int:
        """Delete traces older than N days."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM trace_spans
                    WHERE trace_id IN (
                        SELECT trace_id FROM traces
                        WHERE created_at < NOW() - INTERVAL '%s days'
                    )
                    """,
                    (days_old,),
                )
                cur.execute(
                    """
                    DELETE FROM traces
                    WHERE created_at < NOW() - INTERVAL '%s days'
                    """,
                    (days_old,),
                )
                deleted = cur.rowcount
                conn.commit()
                return deleted