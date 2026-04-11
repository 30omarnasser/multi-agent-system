import sys, os, requests, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"
DOC_ID = "day12_test_doc"


def create_test_pdf() -> bytes:
    """Multi-topic PDF so we can test vector vs keyword differences."""
    return b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 600 >>
stream
BT /F1 11 Tf 50 750 Td
(Redis is an in-memory data structure store used as a database and cache.) Tj 0 -18 Td
(It supports strings, hashes, lists, sets and sorted sets with range queries.) Tj 0 -18 Td
(PostgreSQL is a powerful open-source relational database system.) Tj 0 -18 Td
(It supports JSON, full-text search, and vector similarity via pgvector.) Tj 0 -18 Td
(LangGraph is a library for building stateful multi-agent applications.) Tj 0 -18 Td
(Agents in LangGraph are represented as nodes in a directed graph.) Tj 0 -18 Td
(Ollama allows running large language models locally on your machine.) Tj 0 -18 Td
(The nomic-embed-text model generates 768-dimensional embedding vectors.) Tj 0 -18 Td
(Retrieval Augmented Generation combines search with language model generation.) Tj 0 -18 Td
(Hybrid search uses both vector similarity and keyword matching for better results.) Tj
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
0000000628 00000 n
trailer << /Size 6 /Root 1 0 R >>
startxref
700
%%EOF"""


def setup():
    """Upload test document before running tests."""
    print("\n⚙ Setup: uploading test document...")
    # Delete if exists
    requests.delete(f"{BASE_URL}/documents/{DOC_ID}")
    time.sleep(1)
    pdf = create_test_pdf()
    r = requests.post(
        f"{BASE_URL}/upload-pdf",
        files={"file": ("hybrid_test.pdf", pdf, "application/pdf")},
        data={"doc_id": DOC_ID},
    )
    assert r.status_code == 200, f"Setup failed: {r.text}"
    data = r.json()
    print(f"  Uploaded: {data['chunks_stored']} chunks stored")
    assert data["chunks_stored"] > 0


def test_vector_search():
    print("\n--- Test 1: Pure Vector Search ---")
    r = requests.get(f"{BASE_URL}/search-docs", params={
        "query": "in-memory storage system for caching",
        "mode": "vector",
        "top_k": 3,
        "doc_id": DOC_ID,
    })
    data = r.json()
    print(f"  mode:    {data['mode']}")
    print(f"  results: {data['count']}")
    for res in data["results"]:
        print(f"  [{res.get('similarity', 0):.4f}] {res['text'][:80]}")
    assert r.status_code == 200
    assert data["mode"] == "vector"
    print("  ✅ Vector search working!")


def test_keyword_search():
    print("\n--- Test 2: Pure Keyword Search ---")
    r = requests.get(f"{BASE_URL}/search-docs", params={
        "query": "pgvector PostgreSQL",
        "mode": "keyword",
        "top_k": 3,
        "doc_id": DOC_ID,
    })
    data = r.json()
    print(f"  mode:    {data['mode']}")
    print(f"  results: {data['count']}")
    for res in data["results"]:
        print(f"  [{res.get('keyword_score', 0):.4f}] {res['text'][:80]}")
    assert r.status_code == 200
    assert data["mode"] == "keyword"
    print("  ✅ Keyword search working!")


def test_hybrid_search():
    print("\n--- Test 3: Hybrid Search (RRF) ---")
    r = requests.get(f"{BASE_URL}/search-docs", params={
        "query": "vector embeddings and database storage",
        "mode": "hybrid",
        "top_k": 3,
        "doc_id": DOC_ID,
    })
    data = r.json()
    print(f"  mode:    {data['mode']}")
    print(f"  results: {data['count']}")
    for res in data["results"]:
        print(
            f"  [rrf={res.get('rrf_score', 0):.4f}] "
            f"[v_rank={res.get('vector_rank')}] "
            f"[k_rank={res.get('keyword_rank')}] "
            f"{res['text'][:70]}"
        )
    assert r.status_code == 200
    assert data["mode"] == "hybrid"
    assert data["count"] > 0
    # Verify RRF fields are present
    if data["results"]:
        assert "rrf_score" in data["results"][0]
        assert "vector_rank" in data["results"][0]
    print("  ✅ Hybrid search working!")


def test_compare_modes():
    print("\n--- Test 4: Compare All Search Modes ---")
    r = requests.get(f"{BASE_URL}/search-docs/compare", params={
        "query": "LangGraph agents local language models",
        "top_k": 3,
        "doc_id": DOC_ID,
    })
    data = r.json()
    print(f"  query: '{data['query']}'")
    print(f"  vector results:  {data['vector']['count']}")
    print(f"  keyword results: {data['keyword']['count']}")
    print(f"  hybrid results:  {data['hybrid']['count']}")
    print(f"\n  Vector top result:  {data['vector']['results'][0]['text'][:70] if data['vector']['results'] else 'none'}")
    print(f"  Keyword top result: {data['keyword']['results'][0]['text'][:70] if data['keyword']['results'] else 'none'}")
    print(f"  Hybrid top result:  {data['hybrid']['results'][0]['text'][:70] if data['hybrid']['results'] else 'none'}")
    assert r.status_code == 200
    assert "vector" in data and "keyword" in data and "hybrid" in data
    print("  ✅ Mode comparison working!")


def test_hybrid_context_format():
    print("\n--- Test 5: Hybrid Context Formatting ---")
    r = requests.get(f"{BASE_URL}/search-docs/context", params={
        "query": "how does retrieval augmented generation work",
        "mode": "hybrid",
        "top_k": 3,
        "doc_id": DOC_ID,
    })
    data = r.json()
    print(f"  mode:           {data['mode']}")
    print(f"  context length: {len(data['context'])} chars")
    print(f"  preview:        {data['context'][:200]}")
    assert r.status_code == 200
    assert len(data["context"]) > 50
    assert "Source" in data["context"]
    assert "score" in data["context"]
    print("  ✅ Hybrid context formatting working!")


def test_global_hybrid_search():
    print("\n--- Test 6: Global Hybrid Search (no doc_id filter) ---")
    r = requests.get(f"{BASE_URL}/search-docs", params={
        "query": "Ollama embedding model dimensions",
        "mode": "hybrid",
        "top_k": 5,
    })
    data = r.json()
    print(f"  results: {data['count']}")
    for res in data["results"]:
        print(f"  [{res.get('rrf_score', 0):.4f}] [{res['filename']}] {res['text'][:70]}")
    assert r.status_code == 200
    print("  ✅ Global hybrid search working!")


def teardown():
    print("\n🧹 Teardown: cleaning up test document...")
    requests.delete(f"{BASE_URL}/documents/{DOC_ID}")
    print("  Done.")


if __name__ == "__main__":
    print("\n🔍 Day 12 — Hybrid Search Tests")
    print("=" * 55)
    setup()
    test_vector_search()
    test_keyword_search()
    test_hybrid_search()
    test_compare_modes()
    test_hybrid_context_format()
    test_global_hybrid_search()
    teardown()
    print("\n" + "=" * 55)
    print("🎉 All Day 12 tests passed!")