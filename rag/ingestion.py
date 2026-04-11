import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from pypdf import PdfReader
import io

from rag.chunker import TextChunker, Chunk
from rag.embedder import OllamaEmbedder

load_dotenv()

EMBEDDING_DIM = 768  # nomic-embed-text


class DocumentIngestion:
    """
    Full RAG ingestion pipeline.
    PDF → text extraction → chunking → embedding → Postgres storage.
    """

    def __init__(self):
        self.chunker = TextChunker(chunk_size=500, overlap=50)
        self.embedder = OllamaEmbedder()
        self.conn_params = {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "user": os.getenv("POSTGRES_USER", "agent_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "agent_pass"),
            "dbname": os.getenv("POSTGRES_DB", "agent_db"),
        }
        self._init_db()
        print("[Ingestion] Ready.")

    def _get_conn(self):
        return psycopg2.connect(**self.conn_params)

    def _init_db(self):
        """Create the document_chunks table if it doesn't exist."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS document_chunks (
                        id SERIAL PRIMARY KEY,
                        doc_id TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        text TEXT NOT NULL,
                        embedding vector({EMBEDDING_DIM}),
                        metadata JSONB DEFAULT '{{}}',
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """)
                # Index for fast similarity search
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS chunks_embedding_idx
                    ON document_chunks
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 10);
                """)
                # Index for filtering by doc_id
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS chunks_doc_id_idx
                    ON document_chunks (doc_id);
                """)
                conn.commit()
        print("[Ingestion] Database tables ready.")

    # ─── PDF Processing ───────────────────────────────────────

    def extract_text_from_pdf(self, pdf_bytes: bytes, filename: str) -> str:
        """Extract all text from a PDF file."""
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            pages_text = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    pages_text.append(f"[Page {i+1}]\n{text}")

            full_text = "\n\n".join(pages_text)
            print(f"[Ingestion] Extracted {len(full_text)} chars "
                  f"from {len(reader.pages)} pages of '{filename}'")
            return full_text
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {e}")

    # ─── Full Ingestion Pipeline ──────────────────────────────

    def ingest_pdf(self, pdf_bytes: bytes, filename: str, doc_id: str = None) -> dict:
        """
        Full pipeline: PDF bytes → chunks → embeddings → stored in Postgres.
        Returns summary of what was ingested.
        """
        if doc_id is None:
            import hashlib
            doc_id = hashlib.md5(pdf_bytes).hexdigest()[:12]

        print(f"\n[Ingestion] Starting ingestion: '{filename}' (doc_id: {doc_id})")

        # Check if already ingested
        if self.document_exists(doc_id):
            print(f"[Ingestion] Document '{doc_id}' already exists — skipping.")
            return {
                "doc_id": doc_id,
                "filename": filename,
                "status": "already_exists",
                "chunks_stored": self.chunk_count(doc_id),
            }

        # Step 1: Extract text
        text = self.extract_text_from_pdf(pdf_bytes, filename)
        if not text.strip():
            raise ValueError("PDF appears to be empty or image-only (no extractable text).")

        # Step 2: Chunk the text
        metadata = {"filename": filename, "doc_id": doc_id}
        chunks = self.chunker.chunk_text(text, metadata=metadata)
        if not chunks:
            raise ValueError("No chunks were generated from the document.")

        # Step 3: Embed all chunks
        chunk_texts = [c.text for c in chunks]
        embeddings = self.embedder.embed_batch(chunk_texts)

        # Step 4: Store in Postgres
        stored = self._store_chunks(doc_id, filename, chunks, embeddings)

        result = {
            "doc_id": doc_id,
            "filename": filename,
            "status": "success",
            "pages": text.count("[Page "),
            "chunks_stored": stored,
            "total_chars": len(text),
        }
        print(f"[Ingestion] ✓ Complete: {result}")
        return result

    def _store_chunks(
        self,
        doc_id: str,
        filename: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> int:
        """Store all chunks and their embeddings in Postgres."""
        stored = 0
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                for chunk, embedding in zip(chunks, embeddings):
                    cur.execute(
                        """
                        INSERT INTO document_chunks
                            (doc_id, filename, chunk_index, text, embedding, metadata)
                        VALUES (%s, %s, %s, %s, %s::vector, %s)
                        """,
                        (
                            doc_id,
                            filename,
                            chunk.chunk_index,
                            chunk.text,
                            str(embedding),
                            json.dumps(chunk.metadata),
                        ),
                    )
                    stored += 1
                conn.commit()
        print(f"[Ingestion] Stored {stored} chunks for doc_id='{doc_id}'")
        return stored

    # ─── Management ───────────────────────────────────────────

    def document_exists(self, doc_id: str) -> bool:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM document_chunks WHERE doc_id = %s",
                    (doc_id,)
                )
                return cur.fetchone()[0] > 0

    def chunk_count(self, doc_id: str = None) -> int:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                if doc_id:
                    cur.execute(
                        "SELECT COUNT(*) FROM document_chunks WHERE doc_id = %s",
                        (doc_id,)
                    )
                else:
                    cur.execute("SELECT COUNT(*) FROM document_chunks")
                return cur.fetchone()[0]

    def list_documents(self) -> list[dict]:
        """List all ingested documents."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT doc_id, filename,
                           COUNT(*) as chunk_count,
                           MIN(created_at) as ingested_at
                    FROM document_chunks
                    GROUP BY doc_id, filename
                    ORDER BY ingested_at DESC
                """)
                return [dict(r) for r in cur.fetchall()]

    def delete_document(self, doc_id: str) -> int:
        """Delete all chunks for a document."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM document_chunks WHERE doc_id = %s",
                    (doc_id,)
                )
                deleted = cur.rowcount
                conn.commit()
        print(f"[Ingestion] Deleted {deleted} chunks for doc_id='{doc_id}'")
        return deleted