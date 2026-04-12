import sys, os, requests, time, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"


def log(title: str):
    print(f"\n{'═' * 60}")
    print(f"  🎬 {title}")
    print('═' * 60)


def section(msg: str):
    print(f"\n  {'─' * 50}")
    print(f"  {msg}")
    print(f"  {'─' * 50}")


def run_pipeline(message: str, session_id: str, hitl: bool = False) -> dict:
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": message,
        "session_id": session_id,
        "user_id": "demo_user",
        "hitl_enabled": hitl,
    }, timeout=180)
    assert r.status_code == 200, f"Pipeline failed: {r.text[:200]}"
    return r.json()


# ─── Scenario 1: Research Report ──────────────────────────────

def demo_research_report():
    log("SCENARIO 1 — Automated Research Report")
    print("  Topic: The state of multi-agent AI systems in 2026")
    print("  This demo shows: Planner → Researcher → Critic → Responder")
    print("  Expected: A structured research report with real web sources")

    session = "demo_research_001"
    time.sleep(2)

    section("Step 1: Initial research query")
    r1 = run_pipeline(
        "Search for and summarize the current state of multi-agent AI systems "
        "in 2026. What are the main frameworks, use cases, and challenges?",
        session_id=session,
    )
    print(f"  Agents used:     {r1['agents_used']}")
    print(f"  Critique score:  {r1['critique_score']}/10")
    print(f"  Response length: {len(r1['response'])} chars")
    print(f"\n  📄 Report preview:\n")
    print(f"  {r1['response'][:600]}")
    assert "researcher" in r1["agents_used"]
    assert len(r1["response"]) > 100

    time.sleep(3)

    section("Step 2: Follow-up — memory continuity test")
    r2 = run_pipeline(
        "Based on what you just found, what are the top 3 most important "
        "developments in this space?",
        session_id=session,
    )
    print(f"  Response: {r2['response'][:400]}")
    assert len(r2["response"]) > 50

    time.sleep(3)

    section("Step 3: Check facts were saved to long-term memory")
    r3 = requests.get(f"{BASE_URL}/facts/search", params={
        "query": "multi-agent AI systems",
        "top_k": 3,
    })
    facts = r3.json()["results"]
    print(f"  Facts saved: {len(facts)}")
    for f in facts[:3]:
        print(f"  - [{f['category']}] {f['fact'][:80]}")

    section("Step 4: Check episode was created")
    r4 = requests.get(f"{BASE_URL}/episodes/recent", params={"limit": 3})
    episodes = r4.json()["episodes"]
    print(f"  Episodes stored: {len(episodes)}")
    if episodes:
        print(f"  Latest: {episodes[0]['summary'][:100]}")

    print("\n  ✅ Scenario 1 — Research Report: COMPLETE")
    return r1


# ─── Scenario 2: Code Debugging ───────────────────────────────

def demo_code_debugging():
    log("SCENARIO 2 — Intelligent Code Debugging")
    print("  Task: Debug a broken Python function + write tests")
    print("  This demo shows: Planner → Coder → Critic → Responder")
    print("  Expected: Working fixed code with execution output")

    session = "demo_code_001"
    time.sleep(2)

    section("Step 1: Submit buggy code for debugging")
    buggy_code = """
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)  # Bug: crashes on empty list

def find_max(lst):
    max_val = lst[0]  # Bug: crashes on empty list
    for item in lst:
        if item > max_val:
            max_val = item
    return max_val

# Test calls that will crash:
print(calculate_average([]))
print(find_max([]))
"""

    r1 = run_pipeline(
        f"Debug this Python code, fix all bugs, and run it to verify it works:\n{buggy_code}",
        session_id=session,
    )
    print(f"  Agents used:    {r1['agents_used']}")
    print(f"  Critique score: {r1['critique_score']}/10")
    print(f"\n  🔧 Fixed code response:\n")
    print(f"  {r1['response'][:800]}")
    assert "coder" in r1["agents_used"]

    time.sleep(3)

    section("Step 2: Ask it to add unit tests")
    r2 = run_pipeline(
        "Now write and run Python unit tests for the fixed functions "
        "using the unittest module. Test edge cases.",
        session_id=session,
    )
    print(f"  Agents: {r2['agents_used']}")
    print(f"  Response: {r2['response'][:400]}")
    assert "coder" in r2["agents_used"]

    time.sleep(3)

    section("Step 3: Performance analysis")
    r3 = run_pipeline(
        "Write Python code to benchmark the calculate_average function "
        "with lists of 1000, 10000, and 100000 numbers. Show execution times.",
        session_id=session,
    )
    print(f"  Response: {r3['response'][:400]}")

    print("\n  ✅ Scenario 2 — Code Debugging: COMPLETE")
    return r1


# ─── Scenario 3: Document Q&A ─────────────────────────────────

def demo_document_qa():
    log("SCENARIO 3 — Document Q&A with RAG")
    print("  Task: Upload a technical doc and answer questions from it")
    print("  This demo shows: PDF ingestion → Hybrid RAG → Researcher → Responder")
    print("  Expected: Accurate answers grounded in the uploaded document")

    session = "demo_rag_001"

    section("Step 1: Upload a technical document")

    # Create a realistic technical PDF
    pdf_content = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 1200 >>
stream
BT /F1 10 Tf 50 750 Td
(ACME AI Platform - Technical Specification v2.0) Tj 0 -20 Td
(================================================) Tj 0 -25 Td
(1. SYSTEM OVERVIEW) Tj 0 -18 Td
(The ACME AI Platform processes 50000 requests per day using a) Tj 0 -15 Td
(multi-agent architecture with 5 specialized AI agents.) Tj 0 -25 Td
(2. INFRASTRUCTURE) Tj 0 -18 Td
(Primary Database: PostgreSQL 15 with pgvector extension.) Tj 0 -15 Td
(Cache Layer: Redis 7 with 2-hour session TTL.) Tj 0 -15 Td
(API Framework: FastAPI running on port 8000.) Tj 0 -15 Td
(LLM Engine: Ollama with llama3.1:8b model.) Tj 0 -15 Td
(Embedding Model: nomic-embed-text producing 768-dim vectors.) Tj 0 -25 Td
(3. PERFORMANCE METRICS) Tj 0 -18 Td
(Average response time: 6.5 seconds per request.) Tj 0 -15 Td
(Uptime SLA: 99.9 percent guaranteed.) Tj 0 -15 Td
(Peak load: 500 concurrent requests.) Tj 0 -15 Td
(Memory usage: 4GB RAM under normal load.) Tj 0 -25 Td
(4. SECURITY) Tj 0 -18 Td
(Authentication: JWT tokens with 24-hour expiry.) Tj 0 -15 Td
(Encryption: TLS 1.3 for all API traffic.) Tj 0 -15 Td
(Data isolation: Each session uses separate Redis namespace.) Tj 0 -25 Td
(5. AGENT PIPELINE) Tj 0 -18 Td
(Planner Agent: Decomposes tasks using confidence scoring.) Tj 0 -15 Td
(Researcher Agent: Hybrid search over web and knowledge base.) Tj 0 -15 Td
(Coder Agent: Sandboxed Python execution with 10s timeout.) Tj 0 -15 Td
(Critic Agent: Scores outputs 0-10, triggers revision if below 7.) Tj 0 -15 Td
(Responder Agent: Synthesizes final answer with episode context.) Tj
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
0000001530 00000 n
trailer << /Size 6 /Root 1 0 R >>
startxref
1600
%%EOF"""

    # Delete if exists, then upload
    requests.delete(f"{BASE_URL}/documents/demo_tech_spec")
    time.sleep(1)

    r_upload = requests.post(
        f"{BASE_URL}/upload-pdf",
        files={"file": ("acme_tech_spec.pdf", pdf_content, "application/pdf")},
        data={"doc_id": "demo_tech_spec"},
        timeout=60,
    )
    assert r_upload.status_code == 200
    upload_data = r_upload.json()
    print(f"  Uploaded: {upload_data['filename']}")
    print(f"  Chunks:   {upload_data['chunks_stored']}")
    assert upload_data["chunks_stored"] > 0

    time.sleep(2)

    section("Step 2: Query the document — specific facts")
    r1 = run_pipeline(
        "What is the average response time and uptime SLA of the ACME AI Platform?",
        session_id=session,
    )
    print(f"  Agents: {r1['agents_used']}")
    print(f"  Response: {r1['response'][:400]}")
    response_lower = r1["response"].lower()
    assert "6.5" in r1["response"] or "99.9" in r1["response"] or \
           "response time" in response_lower or "uptime" in response_lower, \
        "Response should contain document facts"

    time.sleep(3)

    section("Step 3: Query about security details")
    r2 = run_pipeline(
        "What authentication method does the ACME platform use and "
        "how long do tokens last?",
        session_id=session,
    )
    print(f"  Response: {r2['response'][:400]}")
    assert "jwt" in r2["response"].lower() or "token" in r2["response"].lower()

    time.sleep(3)

    section("Step 4: Cross-source query — doc + web")
    r3 = run_pipeline(
        "Search the web for best practices for JWT authentication, "
        "then compare with how the ACME platform implements it.",
        session_id=session,
    )
    print(f"  Agents: {r3['agents_used']}")
    print(f"  Response: {r3['response'][:400]}")

    section("Step 5: Verify semantic search")
    r4 = requests.get(f"{BASE_URL}/search-docs", params={
        "query": "agent pipeline performance timeout",
        "mode": "hybrid",
        "top_k": 3,
        "doc_id": "demo_tech_spec",
    })
    results = r4.json()["results"]
    print(f"  RAG search results: {len(results)}")
    for res in results:
        print(f"  [{res.get('rrf_score', 0):.3f}] {res['text'][:80]}")
    assert len(results) > 0

    # Cleanup
    requests.delete(f"{BASE_URL}/documents/demo_tech_spec")

    print("\n  ✅ Scenario 3 — Document Q&A: COMPLETE")
    return r1


# ─── Full Demo Summary ─────────────────────────────────────────

def print_demo_summary(results: list[dict]):
    log("DEMO SUMMARY")

    r = requests.get(f"{BASE_URL}/evaluations/stats")
    stats = r.json()

    r2 = requests.get(f"{BASE_URL}/traces/stats")
    trace_stats = r2.json()

    r3 = requests.get(f"{BASE_URL}/memory/stats")
    mem_stats = r3.json()

    print(f"""
  📊 System Performance During Demo:
  ───────────────────────────────────
  Total pipeline runs:    {trace_stats.get('total_traces', 0)}
  Avg response time:      {trace_stats.get('avg_duration_ms', 0)/1000:.1f}s
  Avg quality score:      {stats.get('avg_overall', 0)}/10
  Facts learned:          {mem_stats.get('facts', {}).get('total', 0)}
  Episodes stored:        {mem_stats.get('episodes', {}).get('total', 0)}

  🤖 Agent Pipeline:
  ───────────────────────────────────
  Planner → routes every request
  Researcher → web + RAG hybrid search
  Coder → sandboxed Python execution
  Critic → self-correction loop (0-10)
  Responder → synthesizes final answer

  🧠 Memory Systems:
  ───────────────────────────────────
  Redis → short-term session memory
  PostgreSQL + pgvector → long-term facts
  Episodic → cross-session recall
  User profiles → preference learning

  📚 RAG Pipeline:
  ───────────────────────────────────
  PDF → chunks → embeddings → hybrid search
  Vector + keyword + RRF fusion
  Integrated into Researcher agent

  🔗 Links:
  ───────────────────────────────────
  API Docs:  http://localhost:8000/docs
  UI:        http://localhost:8501
  GitHub:    https://github.com/30omarnasser/multi-agent-system
    """)


if __name__ == "__main__":
    print("\n" + "🎬" * 30)
    print("  MULTI-AGENT AI SYSTEM — LIVE DEMO")
    print("  3 Scenarios showcasing the full system")
    print("🎬" * 30)

    results = []

    print("\n⏳ Running Scenario 1...")
    r1 = demo_research_report()
    results.append(r1)

    print("\n⏳ Running Scenario 2...")
    r2 = demo_code_debugging()
    results.append(r2)

    print("\n⏳ Running Scenario 3...")
    r3 = demo_document_qa()
    results.append(r3)

    print_demo_summary(results)

    print("\n" + "✅" * 30)
    print("  ALL 3 DEMO SCENARIOS COMPLETE!")
    print("✅" * 30)