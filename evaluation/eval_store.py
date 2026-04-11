import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


class EvalStore:
    """
    Stores and retrieves evaluation results in Postgres.
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
        print("[EvalStore] Ready.")

    def _get_conn(self):
        return psycopg2.connect(**self.conn_params)

    def _init_db(self):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS evaluations (
                        id SERIAL PRIMARY KEY,
                        trace_id TEXT,
                        session_id TEXT NOT NULL,
                        user_message TEXT NOT NULL,
                        response_preview TEXT DEFAULT '',
                        task_type TEXT DEFAULT 'simple',
                        agents_used TEXT[] DEFAULT '{}',
                        agent_count INTEGER DEFAULT 0,
                        had_revision BOOLEAN DEFAULT FALSE,
                        score_relevance INTEGER DEFAULT 0,
                        score_accuracy INTEGER DEFAULT 0,
                        score_completeness INTEGER DEFAULT 0,
                        score_efficiency INTEGER DEFAULT 0,
                        score_coherence INTEGER DEFAULT 0,
                        score_overall INTEGER DEFAULT 0,
                        strengths TEXT[] DEFAULT '{}',
                        weaknesses TEXT[] DEFAULT '{}',
                        reasoning TEXT DEFAULT '',
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS evals_session_idx
                    ON evaluations (session_id);
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS evals_created_idx
                    ON evaluations (created_at DESC);
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS evals_overall_idx
                    ON evaluations (score_overall DESC);
                """)
                conn.commit()
        print("[EvalStore] Tables ready.")

    def _get_conn(self):
        return psycopg2.connect(**self.conn_params)

    # ─── Core Operations ──────────────────────────────────────

    def save_evaluation(
        self,
        session_id: str,
        user_message: str,
        response: str,
        scores: dict,
        had_revision: bool = False,
    ) -> int:
        """Save an evaluation result. Returns the evaluation ID."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO evaluations (
                        trace_id, session_id, user_message, response_preview,
                        task_type, agents_used, agent_count, had_revision,
                        score_relevance, score_accuracy, score_completeness,
                        score_efficiency, score_coherence, score_overall,
                        strengths, weaknesses, reasoning
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s
                    ) RETURNING id
                    """,
                    (
                        scores.get("trace_id", ""),
                        session_id,
                        user_message[:500],
                        response[:300],
                        scores.get("task_type", "simple"),
                        scores.get("agents_used", []),
                        scores.get("agent_count", 0),
                        had_revision,
                        scores.get("relevance", 0),
                        scores.get("accuracy", 0),
                        scores.get("completeness", 0),
                        scores.get("efficiency", 0),
                        scores.get("coherence", 0),
                        scores.get("overall", 0),
                        scores.get("strengths", []),
                        scores.get("weaknesses", []),
                        scores.get("reasoning", ""),
                    ),
                )
                eval_id = cur.fetchone()[0]
                conn.commit()
        print(f"[EvalStore] ✓ Saved evaluation {eval_id} | overall={scores.get('overall')}/10")
        return eval_id

    def get_evaluation(self, eval_id: int) -> dict:
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM evaluations WHERE id = %s",
                    (eval_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else {}

    def list_evaluations(
        self,
        session_id: str = None,
        task_type: str = None,
        min_score: int = 0,
        limit: int = 20,
    ) -> list[dict]:
        conditions = ["score_overall >= %s"]
        params = [min_score]

        if session_id:
            conditions.append("session_id = %s")
            params.append(session_id)
        if task_type:
            conditions.append("task_type = %s")
            params.append(task_type)

        where = " AND ".join(conditions)
        params.append(limit)

        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT id, trace_id, session_id, user_message,
                           task_type, agents_used, agent_count, had_revision,
                           score_overall, score_relevance, score_accuracy,
                           score_completeness, score_efficiency, score_coherence,
                           strengths, weaknesses, reasoning, created_at
                    FROM evaluations
                    WHERE {where}
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    params,
                )
                return [dict(r) for r in cur.fetchall()]

    def get_aggregate_stats(self) -> dict:
        """Aggregate evaluation stats across all runs."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) as total_evaluations,
                        ROUND(AVG(score_overall), 2) as avg_overall,
                        ROUND(AVG(score_relevance), 2) as avg_relevance,
                        ROUND(AVG(score_accuracy), 2) as avg_accuracy,
                        ROUND(AVG(score_completeness), 2) as avg_completeness,
                        ROUND(AVG(score_efficiency), 2) as avg_efficiency,
                        ROUND(AVG(score_coherence), 2) as avg_coherence,
                        MAX(score_overall) as best_score,
                        MIN(score_overall) as worst_score,
                        SUM(CASE WHEN had_revision THEN 1 ELSE 0 END) as revision_count,
                        SUM(CASE WHEN score_overall >= 8 THEN 1 ELSE 0 END) as high_quality_count,
                        SUM(CASE WHEN score_overall < 6 THEN 1 ELSE 0 END) as low_quality_count
                    FROM evaluations
                """)
                stats = dict(cur.fetchone())

                # By task type
                cur.execute("""
                    SELECT task_type,
                           COUNT(*) as count,
                           ROUND(AVG(score_overall), 2) as avg_score
                    FROM evaluations
                    GROUP BY task_type
                    ORDER BY count DESC
                """)
                stats["by_task_type"] = [dict(r) for r in cur.fetchall()]

                # Score trends (last 10)
                cur.execute("""
                    SELECT score_overall, score_relevance, score_accuracy,
                           score_completeness, task_type, created_at
                    FROM evaluations
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
                stats["recent_scores"] = [dict(r) for r in cur.fetchall()]

                # Weakness frequency
                cur.execute("""
                    SELECT unnest(weaknesses) as weakness, COUNT(*) as frequency
                    FROM evaluations
                    WHERE weaknesses != '{}'
                    GROUP BY weakness
                    ORDER BY frequency DESC
                    LIMIT 5
                """)
                stats["top_weaknesses"] = [dict(r) for r in cur.fetchall()]

                return stats

    def delete_evaluation(self, eval_id: int):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM evaluations WHERE id = %s",
                    (eval_id,),
                )
                conn.commit()

    def clear_evaluations(self, session_id: str = None) -> int:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                if session_id:
                    cur.execute(
                        "DELETE FROM evaluations WHERE session_id = %s",
                        (session_id,),
                    )
                else:
                    cur.execute("DELETE FROM evaluations")
                deleted = cur.rowcount
                conn.commit()
                return deleted