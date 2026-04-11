import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import ollama as ollama_client
from datetime import datetime, timedelta

load_dotenv()


class MemoryManager:
    """
    Central memory health system.
    Handles:
    - Summarizing long Redis conversations before they expire
    - Pruning low-relevance facts from Postgres
    - Deduplicating similar episodes
    - Memory usage stats and dashboard
    - Scheduled cleanup operations
    """

    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model
        self.conn_params = {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "user": os.getenv("POSTGRES_USER", "agent_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "agent_pass"),
            "dbname": os.getenv("POSTGRES_DB", "agent_db"),
        }
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        self.ollama = ollama_client.Client(host=self.ollama_host)
        print(f"[MemoryManager] Ready | model: {self.model}")

    def _get_conn(self):
        return psycopg2.connect(**self.conn_params)

    # ─── Stats & Dashboard ────────────────────────────────────

    def get_memory_stats(self) -> dict:
        """
        Get a full snapshot of memory usage across all systems.
        This is what powers the memory dashboard.
        """
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "facts": {},
            "episodes": {},
            "documents": {},
            "profiles": {},
            "health": "ok",
            "recommendations": [],
        }

        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:

                    # Facts stats
                    cur.execute("SELECT COUNT(*) FROM facts")
                    stats["facts"]["total"] = cur.fetchone()[0]

                    cur.execute("""
                        SELECT category, COUNT(*) as count
                        FROM facts
                        GROUP BY category
                        ORDER BY count DESC
                    """)
                    stats["facts"]["by_category"] = {
                        row[0]: row[1] for row in cur.fetchall()
                    }

                    cur.execute("""
                        SELECT COUNT(DISTINCT session_id) FROM facts
                    """)
                    stats["facts"]["sessions"] = cur.fetchone()[0]

                    # Episodes stats
                    cur.execute("SELECT COUNT(*) FROM episodes")
                    stats["episodes"]["total"] = cur.fetchone()[0]

                    cur.execute("""
                        SELECT COUNT(DISTINCT session_id) FROM episodes
                    """)
                    stats["episodes"]["sessions"] = cur.fetchone()[0]

                    cur.execute("""
                        SELECT AVG(message_count) FROM episodes
                    """)
                    avg = cur.fetchone()[0]
                    stats["episodes"]["avg_messages"] = round(float(avg), 1) if avg else 0

                    # Document chunks stats
                    cur.execute("SELECT COUNT(*) FROM document_chunks")
                    stats["documents"]["total_chunks"] = cur.fetchone()[0]

                    cur.execute("""
                        SELECT COUNT(DISTINCT doc_id) FROM document_chunks
                    """)
                    stats["documents"]["total_docs"] = cur.fetchone()[0]

                    # Profile stats
                    cur.execute("SELECT COUNT(*) FROM user_profiles")
                    stats["profiles"]["total"] = cur.fetchone()[0]

                    cur.execute("""
                        SELECT AVG(interaction_count) FROM user_profiles
                    """)
                    avg_int = cur.fetchone()[0]
                    stats["profiles"]["avg_interactions"] = round(float(avg_int), 1) if avg_int else 0

        except Exception as e:
            stats["health"] = f"error: {str(e)}"

        # Generate recommendations
        stats["recommendations"] = self._generate_recommendations(stats)
        return stats

    def _generate_recommendations(self, stats: dict) -> list[str]:
        """Suggest maintenance actions based on current stats."""
        recs = []
        facts_total = stats.get("facts", {}).get("total", 0)
        episodes_total = stats.get("episodes", {}).get("total", 0)
        docs_total = stats.get("documents", {}).get("total_chunks", 0)

        if facts_total > 500:
            recs.append(f"Facts table has {facts_total} entries — consider pruning old facts")
        if facts_total > 1000:
            recs.append("Facts table is large — run deduplicate_facts() to remove duplicates")
        if episodes_total > 200:
            recs.append(f"Episodes table has {episodes_total} entries — consider archiving old ones")
        if docs_total > 10000:
            recs.append(f"Document chunks ({docs_total}) is large — consider removing unused documents")
        if not recs:
            recs.append("Memory looks healthy — no action needed")

        return recs

    # ─── Facts Management ─────────────────────────────────────

    def prune_old_facts(
        self,
        days_old: int = 30,
        session_id: str = None,
    ) -> int:
        """Delete facts older than N days."""
        cutoff = datetime.utcnow() - timedelta(days=days_old)
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                if session_id:
                    cur.execute(
                        """
                        DELETE FROM facts
                        WHERE created_at < %s AND session_id = %s
                        """,
                        (cutoff, session_id),
                    )
                else:
                    cur.execute(
                        "DELETE FROM facts WHERE created_at < %s",
                        (cutoff,),
                    )
                deleted = cur.rowcount
                conn.commit()
        print(f"[MemoryManager] Pruned {deleted} facts older than {days_old} days")
        return deleted

    def deduplicate_facts(self, session_id: str = None) -> int:
        """
        Remove duplicate facts — keep the most recent version
        when the same fact text appears more than once.
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                if session_id:
                    cur.execute(
                        """
                        DELETE FROM facts
                        WHERE id NOT IN (
                            SELECT MAX(id)
                            FROM facts
                            WHERE session_id = %s
                            GROUP BY fact, session_id
                        )
                        AND session_id = %s
                        """,
                        (session_id, session_id),
                    )
                else:
                    cur.execute(
                        """
                        DELETE FROM facts
                        WHERE id NOT IN (
                            SELECT MAX(id)
                            FROM facts
                            GROUP BY fact, session_id
                        )
                        """
                    )
                deleted = cur.rowcount
                conn.commit()
        print(f"[MemoryManager] Deduplicated facts — removed {deleted} duplicates")
        return deleted

    def summarize_facts(self, session_id: str) -> str:
        """
        Use LLM to summarize all facts for a session into
        a condensed list — useful before pruning old individual facts.
        """
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT fact, category FROM facts WHERE session_id = %s ORDER BY created_at",
                    (session_id,)
                )
                facts = cur.fetchall()

        if not facts:
            return ""

        facts_text = "\n".join([f"[{f['category']}] {f['fact']}" for f in facts])

        prompt = f"""Summarize these facts about a user into a concise profile summary.
Keep only the most important and unique information.
Return a clean, readable paragraph.

Facts:
{facts_text[:3000]}

Summary:"""

        try:
            response = self.ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response["message"]["content"].strip()
        except Exception as e:
            print(f"[MemoryManager] Fact summarization failed: {e}")
            return facts_text[:500]

    # ─── Episodes Management ──────────────────────────────────

    def prune_old_episodes(self, days_old: int = 60) -> int:
        """Delete episodes older than N days."""
        cutoff = datetime.utcnow() - timedelta(days=days_old)
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM episodes WHERE created_at < %s",
                    (cutoff,)
                )
                deleted = cur.rowcount
                conn.commit()
        print(f"[MemoryManager] Pruned {deleted} episodes older than {days_old} days")
        return deleted

    def deduplicate_episodes(self, similarity_threshold: float = 0.95) -> int:
        """
        Remove near-duplicate episodes using vector similarity.
        Keeps the most recent episode when two are very similar.
        """
        removed = 0
        try:
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Find pairs of very similar episodes
                    cur.execute(
                        """
                        SELECT a.id as id_a, b.id as id_b,
                               1 - (a.embedding <=> b.embedding) as similarity
                        FROM episodes a
                        JOIN episodes b ON a.id < b.id
                        WHERE 1 - (a.embedding <=> b.embedding) > %s
                        ORDER BY similarity DESC
                        """,
                        (similarity_threshold,)
                    )
                    pairs = cur.fetchall()

                ids_to_delete = set()
                for pair in pairs:
                    # Keep the higher ID (more recent), delete the older one
                    ids_to_delete.add(pair["id_a"])

                if ids_to_delete:
                    with conn.cursor() as cur:
                        cur.execute(
                            "DELETE FROM episodes WHERE id = ANY(%s)",
                            (list(ids_to_delete),)
                        )
                        removed = cur.rowcount
                        conn.commit()

        except Exception as e:
            print(f"[MemoryManager] Episode deduplication failed: {e}")

        print(f"[MemoryManager] Deduplicated episodes — removed {removed} near-duplicates")
        return removed

    def archive_old_episodes(
        self,
        days_old: int = 30,
        keep_per_session: int = 5,
    ) -> int:
        """
        Keep only the N most recent episodes per session,
        delete the rest that are older than days_old.
        """
        cutoff = datetime.utcnow() - timedelta(days=days_old)
        deleted = 0

        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get all sessions
                cur.execute("SELECT DISTINCT session_id FROM episodes")
                sessions = [r["session_id"] for r in cur.fetchall()]

            for session_id in sessions:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM episodes
                        WHERE session_id = %s
                          AND created_at < %s
                          AND id NOT IN (
                              SELECT id FROM episodes
                              WHERE session_id = %s
                              ORDER BY created_at DESC
                              LIMIT %s
                          )
                        """,
                        (session_id, cutoff, session_id, keep_per_session),
                    )
                    deleted += cur.rowcount
                    conn.commit()

        print(f"[MemoryManager] Archived {deleted} old episodes "
              f"(kept {keep_per_session} per session)")
        return deleted

    # ─── Document Management ──────────────────────────────────

    def get_document_stats(self) -> list[dict]:
        """Get per-document chunk counts and sizes."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        doc_id,
                        filename,
                        COUNT(*) as chunk_count,
                        SUM(LENGTH(text)) as total_chars,
                        MIN(created_at) as ingested_at
                    FROM document_chunks
                    GROUP BY doc_id, filename
                    ORDER BY ingested_at DESC
                """)
                return [dict(r) for r in cur.fetchall()]

    # ─── Full Maintenance Run ─────────────────────────────────

    def run_maintenance(
        self,
        prune_facts_days: int = 30,
        prune_episodes_days: int = 60,
        deduplicate: bool = True,
    ) -> dict:
        """
        Run all maintenance operations in one call.
        Returns a report of what was cleaned up.
        """
        print(f"\n[MemoryManager] ─── Starting maintenance run ───")
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "facts_pruned": 0,
            "facts_deduplicated": 0,
            "episodes_pruned": 0,
            "episodes_deduplicated": 0,
            "errors": [],
        }

        try:
            report["facts_pruned"] = self.prune_old_facts(days_old=prune_facts_days)
        except Exception as e:
            report["errors"].append(f"facts_prune: {e}")

        try:
            report["episodes_pruned"] = self.prune_old_episodes(days_old=prune_episodes_days)
        except Exception as e:
            report["errors"].append(f"episodes_prune: {e}")

        if deduplicate:
            try:
                report["facts_deduplicated"] = self.deduplicate_facts()
            except Exception as e:
                report["errors"].append(f"facts_dedup: {e}")

            try:
                report["episodes_deduplicated"] = self.deduplicate_episodes()
            except Exception as e:
                report["errors"].append(f"episodes_dedup: {e}")

        report["status"] = "completed" if not report["errors"] else "completed_with_errors"
        print(f"[MemoryManager] ─── Maintenance complete: {report} ───\n")
        return report