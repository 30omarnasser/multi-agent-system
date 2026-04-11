import sys
import os
import requests
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"


def log(msg, level="info"):
    icons = {"info": "─", "pass": "✅", "fail": "❌", "section": "═"}
    icon = icons.get(level, "─")
    print(f"\n{icon * 55}")
    print(f"  {msg}")
    print(f"{icon * 55}")


def check(label: str, condition: bool, detail: str = ""):
    if condition:
        print(f"  ✅ {label}")
    else:
        print(f"  ❌ {label} {detail}")
        raise AssertionError(f"FAILED: {label} {detail}")


# ─── Week 1 Regression ────────────────────────────────────────

def test_week1_single_agent():
    log("Week 1 — Single agent chat")
    r = requests.post(f"{BASE_URL}/chat", json={
        "message": "What is 2 + 2?",
        "session_id": "week3_regression",
    })
    check("Single agent responds", r.status_code == 200)
    check("Response not empty", len(r.json()["response"]) > 0)
    print(f"  Response: {r.json()['response'][:100]}")


def test_week1_health():
    log("Week 1 — Health check")
    r = requests.get(f"{BASE_URL}/health")
    data = r.json()
    check("API ok", data["api"] == "ok")
    check("Redis ok", data["redis"] == "ok")
    check("Postgres ok", data["postgres"] == "ok")
    check("Ollama ok", data["ollama"] == "ok")
    print(f"  All services healthy ✅")


# ─── Week 2 Regression ────────────────────────────────────────

def test_week2_multi_agent_simple():
    log("Week 2 — Multi-agent pipeline (simple)")
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "What is machine learning?",
        "session_id": "week3_regression_w2",
        "user_id": "regression_user",
    })
    check("Pipeline responds", r.status_code == 200)
    data = r.json()
    check("Has response", len(data["response"]) > 0)
    check("Has plan", "plan" in data)
    check("Has agents_used", "agents_used" in data)
    check("Planner ran", "planner" in data["agents_used"])
    check("Responder ran", "responder" in data["agents_used"])
    print(f"  Agents: {data['agents_used']}")
    print(f"  Response: {data['response'][:150]}")


def test_week2_multi_agent_research():
    log("Week 2 — Multi-agent pipeline (research)")
    time.sleep(3)
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Search for latest news about Python programming language",
        "session_id": "week3_regression_w2",
        "user_id": "regression_user",
    })
    check("Pipeline responds", r.status_code == 200)
    data = r.json()
    check("Researcher ran", "researcher" in data["agents_used"])
    check("Has critique score", "critique_score" in data)
    print(f"  Agents: {data['agents_used']}")
    print(f"  Score: {data['critique_score']}")


# ─── Week 3 Regression ────────────────────────────────────────

def test_week3_pdf_upload():
    log("Week 3 — PDF ingestion")

    pdf_bytes = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 150 >>
stream
BT /F1 12 Tf 50 750 Td
(This document covers multi-agent AI systems and RAG pipelines.) Tj
0 -20 Td (Vector embeddings enable semantic search over documents.) Tj
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
0000000478 00000 n
trailer << /Size 6 /Root 1 0 R >>
startxref
545
%%EOF"""

    r = requests.post(
        f"{BASE_URL}/upload-pdf",
        files={"file": ("regression_test.pdf", pdf_bytes, "application/pdf")},
        data={"doc_id": "regression_doc"},
    )
    check("PDF upload responds", r.status_code == 200)
    data = r.json()
    check("Has doc_id", "doc_id" in data)
    check("Status ok", data["status"] in ("success", "already_exists"))
    print(f"  Status: {data['status']} | chunks: {data.get('chunks_stored', '?')}")


def test_week3_semantic_search():
    log("Week 3 — Semantic document search")
    r = requests.get(f"{BASE_URL}/search-docs", params={
        "query": "what are vector embeddings",
        "top_k": 3,
    })
    check("Search responds", r.status_code == 200)
    data = r.json()
    check("Has results field", "results" in data)
    print(f"  Results: {data['count']}")


def test_week3_episodic_memory():
    log("Week 3 — Episodic memory")
    r = requests.get(f"{BASE_URL}/episodes")
    check("Episodes endpoint ok", r.status_code == 200)
    data = r.json()
    check("Has count", "count" in data)
    print(f"  Total episodes: {data['count']}")

    r2 = requests.get(f"{BASE_URL}/episodes/recent", params={"limit": 3})
    check("Recent episodes ok", r2.status_code == 200)


def test_week3_user_profiles():
    log("Week 3 — User profile memory")
    r = requests.get(f"{BASE_URL}/profile/regression_user")
    check("Profile endpoint ok", r.status_code == 200)
    profile = r.json()
    check("Has user_id", "user_id" in profile)
    print(f"  Profile: interactions={profile.get('interaction_count')}, "
          f"expertise={profile.get('expertise_level')}")

    r2 = requests.get(f"{BASE_URL}/profiles")
    check("Profiles list ok", r2.status_code == 200)


def test_week3_memory_management():
    log("Week 3 — Memory management")
    r = requests.get(f"{BASE_URL}/memory/stats")
    check("Stats endpoint ok", r.status_code == 200)
    data = r.json()
    check("Health ok", data["health"] == "ok")
    check("Has facts stats", "facts" in data)
    check("Has episodes stats", "episodes" in data)
    check("Has recommendations", "recommendations" in data)
    print(f"  Facts: {data['facts']['total']} | "
          f"Episodes: {data['episodes']['total']} | "
          f"Docs: {data['documents']['total_chunks']} chunks")


def test_week3_all_endpoints_healthy():
    log("Week 3 — All endpoints respond 200")
    endpoints = [
        ("GET", "/"),
        ("GET", "/health"),
        ("GET", "/sessions"),
        ("GET", "/facts"),
        ("GET", "/documents"),
        ("GET", "/episodes"),
        ("GET", "/episodes/recent"),
        ("GET", "/profiles"),
        ("GET", "/memory/stats"),
        ("GET", "/memory/document-stats"),
    ]
    for method, path in endpoints:
        r = requests.get(f"{BASE_URL}{path}")
        status = "✅" if r.status_code == 200 else f"❌ {r.status_code}"
        print(f"  {method} {path}: {status}")
        check(f"{path} ok", r.status_code == 200)


if __name__ == "__main__":
    print("\n🤖 Week 3 Regression Test Suite")
    print("=" * 55)
    print("Testing all systems end-to-end...\n")

    tests = [
        ("Week 1: Health check", test_week1_health),
        ("Week 1: Single agent", test_week1_single_agent),
        ("Week 2: Multi-agent simple", test_week2_multi_agent_simple),
        ("Week 2: Multi-agent research", test_week2_multi_agent_research),
        ("Week 3: PDF upload", test_week3_pdf_upload),
        ("Week 3: Semantic search", test_week3_semantic_search),
        ("Week 3: Episodic memory", test_week3_episodic_memory),
        ("Week 3: User profiles", test_week3_user_profiles),
        ("Week 3: Memory management", test_week3_memory_management),
        ("Week 3: All endpoints", test_week3_all_endpoints_healthy),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  ❌ FAILED: {name}")
            print(f"     {e}")
            failed += 1
        time.sleep(1)

    print(f"\n{'=' * 55}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'=' * 55}")

    if failed == 0:
        print("  🎉 All Week 3 regression tests passed!")
    else:
        print(f"  ⚠️  {failed} test(s) failed — fix before Week 4")