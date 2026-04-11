import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

from rag.embedder import OllamaEmbedder

load_dotenv()


class DocumentRetriever:
    """
    Hybrid search over ingested document chunks.
    Combines vector similarity (semantic) + full-text (keyword) search,
    then re-ranks results using Reciprocal Rank Fusion (RRF).
    """

    def __init__(self):
        self.embedder = OllamaEmbedder()
        self.conn_params = {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "user": os.getenv("POSTGRES_USER", "agent_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "agent_pass"),
            "dbname": os.getenv("POSTGRES_DB", "agent_db"),
        }
        self._ensure_fulltext_index()
        print("[Retriever] Ready (hybrid search enabled).")

    def _get_conn(self):
        return psycopg2.connect(**self.conn_params)

    def _ensure_fulltext_index(self):
        """Add tsvector column and GIN index if not already present."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                # Add generated tsvector column if missing
                cur.execute("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name='document_chunks'
                            AND column_name='text_search'
                        ) THEN
                            ALTER TABLE document_chunks
                            ADD COLUMN text_search tsvector
                            GENERATED ALWAYS AS (to_tsvector('english', text)) STORED;
                        END IF;
                    END$$;
                """)
                # Add GIN index if missing
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS chunks_fulltext_idx
                    ON document_chunks USING gin(text_search);
                """)
                conn.commit()
        print("[Retriever] Full-text index ready.")

    # ─── Vector Search ────────────────────────────────────────

    def vector_search(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.2,
        doc_id: str = None,
    ) -> list[dict]:
        """Pure semantic vector search using cosine similarity."""
        query_embedding = self.embedder.embed(query)

        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if doc_id:
                    cur.execute(
                        """
                        SELECT id, doc_id, filename, chunk_index, text, metadata,
                               1 - (embedding <=> %s::vector) AS similarity
                        FROM document_chunks
                        WHERE doc_id = %s
                          AND 1 - (embedding <=> %s::vector) > %s
                        ORDER BY similarity DESC
                        LIMIT %s
                        """,
                        (str(query_embedding), doc_id,
                         str(query_embedding), threshold, top_k),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, doc_id, filename, chunk_index, text, metadata,
                               1 - (embedding <=> %s::vector) AS similarity
                        FROM document_chunks
                        WHERE 1 - (embedding <=> %s::vector) > %s
                        ORDER BY similarity DESC
                        LIMIT %s
                        """,
                        (str(query_embedding), str(query_embedding),
                         threshold, top_k),
                    )
                results = [dict(r) for r in cur.fetchall()]

        print(f"[Retriever] Vector search: '{query[:50]}' → {len(results)} results")
        return results

    # ─── Keyword Search ───────────────────────────────────────

    def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        doc_id: str = None,
    ) -> list[dict]:
        """Full-text keyword search using Postgres tsvector + tsquery."""
        # Convert query to tsquery — handle multi-word queries
        tsquery = " & ".join(
            word for word in query.split()
            if len(word) > 2  # skip very short words
        )
        if not tsquery:
            return []

        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                try:
                    if doc_id:
                        cur.execute(
                            """
                            SELECT id, doc_id, filename, chunk_index, text, metadata,
                                   ts_rank(text_search, to_tsquery('english', %s)) AS keyword_score
                            FROM document_chunks
                            WHERE doc_id = %s
                              AND text_search @@ to_tsquery('english', %s)
                            ORDER BY keyword_score DESC
                            LIMIT %s
                            """,
                            (tsquery, doc_id, tsquery, top_k),
                        )
                    else:
                        cur.execute(
                            """
                            SELECT id, doc_id, filename, chunk_index, text, metadata,
                                   ts_rank(text_search, to_tsquery('english', %s)) AS keyword_score
                            FROM document_chunks
                            WHERE text_search @@ to_tsquery('english', %s)
                            ORDER BY keyword_score DESC
                            LIMIT %s
                            """,
                            (tsquery, tsquery, top_k),
                        )
                    results = [dict(r) for r in cur.fetchall()]
                except Exception as e:
                    # tsquery syntax error — fall back to plainto_tsquery
                    print(f"[Retriever] tsquery error, using plainto: {e}")
                    if doc_id:
                        cur.execute(
                            """
                            SELECT id, doc_id, filename, chunk_index, text, metadata,
                                   ts_rank(text_search, plainto_tsquery('english', %s)) AS keyword_score
                            FROM document_chunks
                            WHERE doc_id = %s
                              AND text_search @@ plainto_tsquery('english', %s)
                            ORDER BY keyword_score DESC
                            LIMIT %s
                            """,
                            (query, doc_id, query, top_k),
                        )
                    else:
                        cur.execute(
                            """
                            SELECT id, doc_id, filename, chunk_index, text, metadata,
                                   ts_rank(text_search, plainto_tsquery('english', %s)) AS keyword_score
                            FROM document_chunks
                            WHERE text_search @@ plainto_tsquery('english', %s)
                            ORDER BY keyword_score DESC
                            LIMIT %s
                            """,
                            (query, query, top_k),
                        )
                    results = [dict(r) for r in cur.fetchall()]

        print(f"[Retriever] Keyword search: '{query[:50]}' → {len(results)} results")
        return results

    # ─── Hybrid Search with RRF ───────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.2,
        doc_id: str = None,
        mode: str = "hybrid",  # "hybrid" | "vector" | "keyword"
    ) -> list[dict]:
        """
        Main search method. Modes:
        - hybrid: RRF fusion of vector + keyword (default, best results)
        - vector: pure semantic search
        - keyword: pure full-text search
        """
        if mode == "vector":
            return self.vector_search(query, top_k=top_k,
                                      threshold=threshold, doc_id=doc_id)
        elif mode == "keyword":
            return self.keyword_search(query, top_k=top_k, doc_id=doc_id)
        else:
            return self.hybrid_search(query, top_k=top_k,
                                      threshold=threshold, doc_id=doc_id)

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.2,
        doc_id: str = None,
        rrf_k: int = 60,
    ) -> list[dict]:
        """
        Hybrid search using Reciprocal Rank Fusion (RRF).

        RRF score = 1/(k + rank_vector) + 1/(k + rank_keyword)

        Higher k = smoother fusion, less sensitive to top ranks.
        k=60 is the standard default from the original RRF paper.
        """
        # Run both searches with more candidates than needed
        vector_results = self.vector_search(
            query, top_k=top_k * 3, threshold=threshold, doc_id=doc_id
        )
        keyword_results = self.keyword_search(
            query, top_k=top_k * 3, doc_id=doc_id
        )

        # Build rank maps: chunk_id → rank (1-indexed)
        vector_ranks = {r["id"]: rank for rank, r in enumerate(vector_results, 1)}
        keyword_ranks = {r["id"]: rank for rank, r in enumerate(keyword_results, 1)}

        # Collect all unique chunk IDs from both result sets
        all_ids = set(vector_ranks.keys()) | set(keyword_ranks.keys())

        # Build a lookup of full chunk data
        all_chunks = {}
        for r in vector_results:
            all_chunks[r["id"]] = r
        for r in keyword_results:
            if r["id"] not in all_chunks:
                all_chunks[r["id"]] = r

        # Compute RRF score for each chunk
        rrf_scores = []
        for chunk_id in all_ids:
            v_rank = vector_ranks.get(chunk_id, len(vector_results) + rrf_k)
            k_rank = keyword_ranks.get(chunk_id, len(keyword_results) + rrf_k)
            rrf_score = 1 / (rrf_k + v_rank) + 1 / (rrf_k + k_rank)

            chunk = all_chunks[chunk_id].copy()
            chunk["rrf_score"] = round(rrf_score, 6)
            chunk["vector_rank"] = vector_ranks.get(chunk_id, None)
            chunk["keyword_rank"] = keyword_ranks.get(chunk_id, None)
            # Use rrf_score as the primary similarity field for consistency
            chunk["similarity"] = chunk["rrf_score"]
            rrf_scores.append(chunk)

        # Sort by RRF score descending, take top_k
        rrf_scores.sort(key=lambda x: x["rrf_score"], reverse=True)
        final = rrf_scores[:top_k]

        print(
            f"[Retriever] Hybrid search: '{query[:50]}' → "
            f"{len(vector_results)}v + {len(keyword_results)}k → "
            f"{len(final)} fused results"
        )
        return final

    # ─── Formatting ───────────────────────────────────────────

    def format_context(self, results: list[dict]) -> str:
        """Format retrieved chunks into LLM-ready context string."""
        if not results:
            return "No relevant document context found."

        parts = []
        for i, r in enumerate(results, 1):
            score = r.get("rrf_score") or r.get("similarity", 0)
            parts.append(
                f"[Source {i}: {r['filename']}, chunk {r['chunk_index']}, "
                f"score: {score:.4f}]\n{r['text']}"
            )
        return "\n\n---\n\n".join(parts)

    def search_and_format(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.2,
        doc_id: str = None,
        mode: str = "hybrid",
    ) -> str:
        """Search and return formatted context string."""
        results = self.search(query, top_k=top_k, threshold=threshold,
                              doc_id=doc_id, mode=mode)
        return self.format_context(results)