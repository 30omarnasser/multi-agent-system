"""
Demo runner — run this while screen recording for your demo video.
Shows all 3 scenarios with clean formatted output.
"""
import sys
import os
import requests
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"

def divider(char="═", n=60):
    print(char * n)

def header(title):
    divider()
    print(f"  {title}")
    divider()

def section(title):
    print(f"\n  {'─' * 50}")
    print(f"  {title}")
    print(f"  {'─' * 50}")

def run(message: str, session: str, label: str = "") -> dict:
    if label:
        print(f"\n  📤 {label}")
    print(f"  Message: {message[:80]}...")
    print(f"  ⏳ Running pipeline...")

    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": message,
        "session_id": session,
        "user_id": "demo_user",
        "hitl_enabled": False,
    }, timeout=180)

    assert r.status_code == 200, f"Failed: {r.text[:200]}"
    data = r.json()

    print(f"  ✅ Agents: {' → '.join(data['agents_used'])}")
    print(f"  📊 Score:  {data['critique_score']}/10")
    print(f"  📝 Response preview:")
    print(f"     {data['response'][:300]}")
    return data


def main():
    print("\n")
    divider("🤖", 30)
    print("  AUTONOMOUS MULTI-AGENT AI SYSTEM")
    print("  Live Demo — 3 Scenarios")
    divider("🤖", 30)

    # ── Health Check ──────────────────────────────────────────
    header("SYSTEM STATUS")
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    health = r.json()
    for service, status in health.items():
        icon = "✅" if status == "ok" else "❌"
        print(f"  {icon} {service.upper()}: {status}")

    time.sleep(2)

    # ── Scenario 1 ────────────────────────────────────────────
    header("SCENARIO 1 — Research Report")
    print("  The system searches the web and synthesizes a research report")

    run(
        "Search for the current state of multi-agent AI systems in 2026. "
        "What are the main frameworks and use cases?",
        session="demo_s1",
        label="Research query",
    )
    time.sleep(3)

    run(
        "Based on your research, what are the top 3 most important trends?",
        session="demo_s1",
        label="Follow-up (memory continuity test)",
    )

    section("Memory check — facts saved automatically")
    r = requests.get(f"{BASE_URL}/facts/search", params={
        "query": "multi-agent AI frameworks",
        "top_k": 3,
    })
    facts = r.json()["results"]
    print(f"  📚 {len(facts)} relevant facts saved to long-term memory")
    for f in facts[:2]:
        print(f"     [{f['category']}] {f['fact'][:70]}")

    time.sleep(3)

    # ── Scenario 2 ────────────────────────────────────────────
    header("SCENARIO 2 — Code Debugging & Testing")
    print("  The system writes, executes, and tests Python code")

    run(
        "Write Python code to implement a binary search algorithm, "
        "then run it to verify it works with a test list.",
        session="demo_s2",
        label="Code generation request",
    )
    time.sleep(3)

    run(
        "Now add unit tests for the binary search function and run them.",
        session="demo_s2",
        label="Test generation (memory continuity)",
    )

    time.sleep(3)

    # ── Scenario 3 ────────────────────────────────────────────
    header("SCENARIO 3 — Document Q&A with RAG")
    print("  Upload a document and answer questions from it")

    # Upload test PDF
    pdf_bytes = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 600 >>
stream
BT /F1 10 Tf 50 750 Td
(TechCorp AI Platform - Internal Specification) Tj 0 -20 Td
(Version: 3.0 | Confidential) Tj 0 -25 Td
(Architecture: Microservices with 12 specialized AI agents.) Tj 0 -15 Td
(Database: PostgreSQL 16 with vector search capabilities.) Tj 0 -15 Td
(Cache: Redis 7 cluster with 500GB capacity.) Tj 0 -15 Td
(Throughput: 2 million requests per day at peak.) Tj 0 -15 Td
(Security: Zero-trust architecture with mTLS.) Tj 0 -15 Td
(Deployment: Kubernetes on AWS EKS, 3 regions.) Tj 0 -15 Td
(SLA: 99.99 percent uptime with automatic failover.) Tj 0 -15 Td
(Team: 8 ML engineers and 4 DevOps engineers.) Tj
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
0000000928 00000 n
trailer << /Size 6 /Root 1 0 R >>
startxref
995
%%EOF"""

    requests.delete(f"{BASE_URL}/documents/demo_doc")
    time.sleep(1)
    r_up = requests.post(
        f"{BASE_URL}/upload-pdf",
        files={"file": ("techcorp_spec.pdf", pdf_bytes, "application/pdf")},
        data={"doc_id": "demo_doc"},
        timeout=60,
    )
    if r_up.status_code == 200:
        print(f"\n  📄 Uploaded: techcorp_spec.pdf | "
              f"chunks: {r_up.json()['chunks_stored']}")
    time.sleep(2)

    run(
        "What is the SLA and daily throughput of the TechCorp AI Platform?",
        session="demo_s3",
        label="Document Q&A",
    )
    time.sleep(3)

    run(
        "How many engineers work on this platform and what is the "
        "deployment infrastructure?",
        session="demo_s3",
        label="Follow-up document query",
    )

    requests.delete(f"{BASE_URL}/documents/demo_doc")

    # ── Final Stats ───────────────────────────────────────────
    header("SYSTEM STATS AFTER DEMO")
    mem = requests.get(f"{BASE_URL}/memory/stats", timeout=10).json()
    evals = requests.get(f"{BASE_URL}/evaluate/summary", timeout=10).json()

    print(f"""
  Memory:
    Facts stored:     {mem['facts']['total']}
    Episodes saved:   {mem['episodes']['total']}
    Documents:        {mem['documents']['total_docs']}
    User profiles:    {mem['profiles']['total']}

  Evaluation:
    Total runs:       {evals.get('total_runs', 0)}
    Avg score:        {evals.get('avg_score', 0)}/10
    """)

    divider("✅", 30)
    print("  DEMO COMPLETE")
    print("  GitHub: https://github.com/30omarnasser/multi-agent-system")
    divider("✅", 30)


if __name__ == "__main__":
    main()