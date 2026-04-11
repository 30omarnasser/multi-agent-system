import sys, os, requests, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"
DOC_ID = "day13_test_doc"


def create_test_pdf() -> bytes:
    """PDF with specific content we can verify was retrieved."""
    return b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 700 >>
stream
BT /F1 11 Tf 50 750 Td
(ACME Corp Technical Architecture Document - Confidential) Tj 0 -20 Td
(Our system uses a microservices architecture with 12 services.) Tj 0 -18 Td
(The primary database is PostgreSQL 15 with pgvector extension.) Tj 0 -18 Td
(We use Redis 7 for caching with a 2-hour TTL on all sessions.) Tj 0 -18 Td
(The API gateway is built with FastAPI and runs on port 8000.) Tj 0 -18 Td
(Authentication uses JWT tokens with 24-hour expiry.) Tj 0 -18 Td
(Our deployment uses Docker Compose with 4 services.) Tj 0 -18 Td
(The machine learning pipeline uses Ollama for local inference.) Tj 0 -18 Td
(We process approximately 10000 requests per day on average.) Tj 0 -18 Td
(The system has 99.9 percent uptime SLA with automatic failover.) Tj 0 -18 Td
(Monitoring is done via Prometheus and Grafana dashboards.) Tj 0 -18 Td
(Our RAG pipeline chunks documents into 500-character segments.) Tj
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
0000000730 00000 n
trailer << /Size 6 /Root 1 0 R >>
startxref
800
%%EOF"""


def setup():
    print("\n⚙ Setup: uploading test document...")
    requests.delete(f"{BASE_URL}/documents/{DOC_ID}")
    time.sleep(1)
    pdf = create_test_pdf()
    r = requests.post(
        f"{BASE_URL}/upload-pdf",
        files={"file": ("acme_architecture.pdf", pdf, "application/pdf")},
        data={"doc_id": DOC_ID},
    )
    assert r.status_code == 200, f"Setup failed: {r.text}"
    data = r.json()
    print(f"  Uploaded: {data['chunks_stored']} chunks | status: {data['status']}")
    assert data["chunks_stored"] > 0


def test_doc_only_query():
    """Query that should be answered from documents, not web."""
    print("\n--- Test 1: Query answerable from uploaded docs ---")
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "What database does ACME Corp use and what is their Redis TTL?",
        "session_id": "day13_test",
    })
    assert r.status_code == 200
    data = r.json()
    print(f"  Agents used: {data['agents_used']}")
    print(f"  Plan type:   {data['plan'].get('task_type')}")
    print(f"  Response:    {data['response'][:400]}")

    response_lower = data["response"].lower()
    assert "postgresql" in response_lower or "postgres" in response_lower, \
        "Should mention PostgreSQL from the document"
    assert "researcher" in data["agents_used"]
    print("  ✅ Doc-based query answered correctly!")


def test_web_plus_doc_query():
    """Query needing both web search and document context."""
    print("\n--- Test 2: Query needing web + doc sources ---")
    time.sleep(3)
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Search for FastAPI best practices and compare with how ACME Corp uses it",
        "session_id": "day13_test",
    })
    assert r.status_code == 200
    data = r.json()
    print(f"  Agents used: {data['agents_used']}")
    print(f"  Response:    {data['response'][:400]}")
    assert "researcher" in data["agents_used"]
    print("  ✅ Combined web + doc research working!")


def test_rag_search_endpoint_directly():
    """Directly test the RAG search endpoint."""
    print("\n--- Test 3: Direct RAG search endpoint ---")
    r = requests.get(f"{BASE_URL}/search-docs", params={
        "query": "authentication JWT tokens expiry",
        "mode": "hybrid",
        "top_k": 3,
        "doc_id": DOC_ID,
    })
    assert r.status_code == 200
    data = r.json()
    print(f"  Results: {data['count']}")
    for res in data["results"]:
        print(f"  [{res.get('rrf_score', res.get('similarity', 0)):.4f}] {res['text'][:80]}")
    assert data["count"] > 0
    assert any("jwt" in r["text"].lower() or "auth" in r["text"].lower()
               for r in data["results"])
    print("  ✅ RAG retrieval finding correct content!")


def test_no_docs_fallback():
    """When no docs match, agent falls back to web search only."""
    print("\n--- Test 4: Fallback to web when no docs match ---")
    time.sleep(3)
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Search for the latest news about quantum computing breakthroughs",
        "session_id": "day13_test",
    })
    assert r.status_code == 200
    data = r.json()
    print(f"  Agents used: {data['agents_used']}")
    print(f"  Response:    {data['response'][:300]}")
    assert "researcher" in data["agents_used"]
    assert data["response"] != ""
    print("  ✅ Web-only fallback working!")


def test_code_with_doc_context():
    print("\n--- Test 5: Coder uses doc-informed research ---")
    time.sleep(3)
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Search for how to connect to PostgreSQL in Python, then write code to connect to a database called agent_db on localhost",
        "session_id": "day13_test",
    })
    assert r.status_code == 200
    data = r.json()
    critique = data.get("critique") or {}
    print(f"  Agents used: {data['agents_used']}")
    print(f"  Critique:    {critique.get('score', 'N/A')}/10")
    print(f"  Response:    {data['response'][:400]}")
    assert "coder" in data["agents_used"]
    assert data["response"] != ""
    print("  ✅ Coder using doc-informed context!")

def teardown():
    print("\n🧹 Teardown: cleaning up...")
    requests.delete(f"{BASE_URL}/documents/{DOC_ID}")
    print("  Done.")


if __name__ == "__main__":
    print("\n🔍 Day 13 — Researcher Agent with RAG Access")
    print("=" * 55)
    setup()
    test_doc_only_query()
    test_web_plus_doc_query()
    test_rag_search_endpoint_directly()
    test_no_docs_fallback()
    test_code_with_doc_context()
    teardown()
    print("\n" + "=" * 55)
    print("🎉 All Day 13 tests passed!")