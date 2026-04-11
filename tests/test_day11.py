import sys
import os
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"

# ─── Create a test PDF in memory ──────────────────────────────

def create_test_pdf() -> bytes:
    """Create a minimal valid PDF for testing without any extra libraries."""
    content = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 200 >>
stream
BT
/F1 12 Tf
50 750 Td
(LangGraph is a framework for building multi-agent AI systems.) Tj
0 -20 Td
(It uses a graph-based approach where agents are nodes.) Tj
0 -20 Td
(Redis is used for short-term memory in our system.) Tj
0 -20 Td
(PostgreSQL stores long-term facts and document embeddings.) Tj
0 -20 Td
(Ollama runs large language models completely locally.) Tj
ET
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000274 00000 n
0000000528 00000 n
trailer << /Size 6 /Root 1 0 R >>
startxref
625
%%EOF"""
    return content


def test_pdf_upload():
    print("\n--- Test 1: PDF Upload and Ingestion ---")
    pdf_bytes = create_test_pdf()

    response = requests.post(
        f"{BASE_URL}/upload-pdf",
        files={"file": ("test_document.pdf", pdf_bytes, "application/pdf")},
        data={"doc_id": "test_doc_001"},
    )
    assert response.status_code == 200, f"Upload failed: {response.text}"
    data = response.json()
    print(f"  status:        {data['status']}")
    print(f"  doc_id:        {data['doc_id']}")
    print(f"  chunks_stored: {data['chunks_stored']}")
    assert data["doc_id"] == "test_doc_001"
    assert data["chunks_stored"] > 0
    print("  ✅ PDF upload working!")


def test_list_documents():
    print("\n--- Test 2: List Documents ---")
    response = requests.get(f"{BASE_URL}/documents")
    assert response.status_code == 200
    data = response.json()
    print(f"  total documents: {data['count']}")
    for doc in data["documents"]:
        print(f"  - {doc['filename']} | chunks: {doc['chunk_count']} | id: {doc['doc_id']}")
    assert data["count"] > 0
    print("  ✅ Document listing working!")


def test_semantic_search():
    print("\n--- Test 3: Semantic Search ---")
    response = requests.get(
        f"{BASE_URL}/search-docs",
        params={"query": "how does memory work in the system", "top_k": 3},
    )
    assert response.status_code == 200
    data = response.json()
    print(f"  query:   '{data['query']}'")
    print(f"  results: {data['count']}")
    for r in data["results"]:
        print(f"  [{r['similarity']:.2f}] {r['text'][:80]}...")
    assert data["count"] > 0
    print("  ✅ Semantic search working!")


def test_doc_context():
    print("\n--- Test 4: Formatted Context for LLM ---")
    response = requests.get(
        f"{BASE_URL}/search-docs/context",
        params={"query": "what is LangGraph", "top_k": 2},
    )
    assert response.status_code == 200
    data = response.json()
    print(f"  context length: {len(data['context'])} chars")
    print(f"  context preview: {data['context'][:200]}")
    assert len(data["context"]) > 50
    assert "Source" in data["context"]
    print("  ✅ Context formatting working!")


def test_duplicate_upload():
    print("\n--- Test 5: Duplicate Upload Handled Gracefully ---")
    pdf_bytes = create_test_pdf()
    response = requests.post(
        f"{BASE_URL}/upload-pdf",
        files={"file": ("test_document.pdf", pdf_bytes, "application/pdf")},
        data={"doc_id": "test_doc_001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "already_exists"
    print(f"  status: {data['status']} ✅ Duplicate handled correctly!")


def test_delete_document():
    print("\n--- Test 6: Delete Document ---")
    response = requests.delete(f"{BASE_URL}/documents/test_doc_001")
    assert response.status_code == 200
    data = response.json()
    print(f"  {data['message']}")
    # Verify it's gone
    response = requests.get(f"{BASE_URL}/documents")
    docs = response.json()["documents"]
    doc_ids = [d["doc_id"] for d in docs]
    assert "test_doc_001" not in doc_ids
    print("  ✅ Document deletion working!")


if __name__ == "__main__":
    print("\n📄 Day 11 — PDF Ingestion Pipeline Tests")
    print("=" * 55)
    test_pdf_upload()
    test_list_documents()
    test_semantic_search()
    test_doc_context()
    test_duplicate_upload()
    test_delete_document()
    print("\n" + "=" * 55)
    print("🎉 All Day 11 tests passed!")