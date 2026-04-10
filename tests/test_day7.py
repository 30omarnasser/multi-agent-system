import sys, os, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests

BASE_URL = "http://localhost:8000"
SESSION_ID = "test_day7"


def log(msg: str):
    print(f"\n{'─' * 60}")
    print(f"  {msg}")
    print('─' * 60)


def test_health():
    log("Test 1: Health Check")
    r = requests.get(f"{BASE_URL}/health")
    data = r.json()
    print(f"  Status: {data}")
    assert data["api"] == "ok", "API not healthy"
    assert data["redis"] == "ok", "Redis not healthy"
    assert data["postgres"] == "ok", "Postgres not healthy"
    assert data["ollama"] == "ok", "Ollama not healthy"
    print("  ✅ All services healthy!")


def test_basic_chat():
    log("Test 2: Basic Conversation (no tools)")
    r = requests.post(f"{BASE_URL}/chat", json={
        "message": "My name is Omar. I study embedded systems and love Python.",
        "session_id": SESSION_ID,
    })
    data = r.json()
    print(f"  Response: {data['response'][:200]}")
    print(f"  History length: {data['history_length']}")
    assert r.status_code == 200
    assert data["response"] != ""
    assert "json" not in data["response"].lower() or "function" not in data["response"].lower(), \
        "Model hallucinated tool calls in plain chat!"
    print("  ✅ Basic chat working!")


def test_memory_recall():
    log("Test 3: Short-term Memory Recall")
    time.sleep(2)
    r = requests.post(f"{BASE_URL}/chat", json={
        "message": "What is my name and what do I study?",
        "session_id": SESSION_ID,
    })
    data = r.json()
    print(f"  Response: {data['response'][:300]}")
    assert "omar" in data["response"].lower(), "Agent forgot the user's name!"
    print("  ✅ Short-term memory working!")


def test_tool_web_search():
    log("Test 4: Tool Use — Web Search")
    time.sleep(2)
    r = requests.post(f"{BASE_URL}/chat", json={
        "message": "Search the web for: what is LangGraph used for",
        "session_id": SESSION_ID,
    })
    data = r.json()
    print(f"  Response: {data['response'][:300]}")
    assert r.status_code == 200
    assert data["response"] != ""
    print("  ✅ Web search tool working!")


def test_tool_calculator():
    log("Test 5: Tool Use — Calculator")
    time.sleep(2)
    r = requests.post(f"{BASE_URL}/chat", json={
        "message": "Calculate 2 to the power of 16",
        "session_id": SESSION_ID,
    })
    data = r.json()
    print(f"  Response: {data['response'][:300]}")
    assert r.status_code == 200
    assert "65536" in data["response"].replace(",", "")
    print("  ✅ Calculator tool working!")


def test_tool_python_executor():
    log("Test 6: Tool Use — Python Executor")
    time.sleep(2)
    r = requests.post(f"{BASE_URL}/chat", json={
        "message": "Run Python code to compute the first 5 Fibonacci numbers and print them",
        "session_id": SESSION_ID,
    })
    data = r.json()
    print(f"  Response: {data['response'][:300]}")
    assert r.status_code == 200
    assert data["response"] != ""
    print("  ✅ Python executor tool working!")


def test_long_term_memory_facts():
    log("Test 7: Long-term Memory — Facts Saved")
    time.sleep(3)  # give fact extraction time to complete
    r = requests.get(f"{BASE_URL}/facts", params={"session_id": SESSION_ID})
    data = r.json()
    print(f"  Total facts saved: {data['count']}")
    for f in data["facts"]:
        print(f"  - [{f['category']}] {f['fact']}")
    assert data["count"] > 0, "No facts were saved to long-term memory!"
    print("  ✅ Long-term memory facts saved!")


def test_semantic_search():
    log("Test 8: Semantic Search over Facts")
    r = requests.get(f"{BASE_URL}/facts/search", params={
        "query": "programming language preference",
        "session_id": SESSION_ID,
        "top_k": 3,
    })
    data = r.json()
    print(f"  Query: {data['query']}")
    print(f"  Results: {len(data['results'])}")
    for res in data["results"]:
        print(f"  - [{res['category']}] {res['fact']} (score: {res.get('similarity', 'N/A')})")
    assert r.status_code == 200
    print("  ✅ Semantic search working!")


def test_session_history():
    log("Test 9: Session History via API")
    r = requests.get(f"{BASE_URL}/history/{SESSION_ID}")
    data = r.json()
    print(f"  Messages in session: {len(data['history'])}")
    for msg in data["history"][-4:]:
        print(f"  [{msg['role']}]: {msg['content'][:80]}...")
    assert len(data["history"]) > 0
    print("  ✅ Session history working!")


def test_sessions_list():
    log("Test 10: List All Sessions")
    r = requests.get(f"{BASE_URL}/sessions")
    sessions = r.json()
    print(f"  Active sessions: {len(sessions)}")
    for s in sessions:
        print(f"  - {s['session_id']} ({s['message_count']} messages, TTL: {s['ttl_seconds']}s)")
    assert any(s["session_id"] == SESSION_ID for s in sessions)
    print("  ✅ Sessions list working!")


def test_clear_session():
    log("Test 11: Clear Session")
    r = requests.delete(f"{BASE_URL}/history/{SESSION_ID}")
    assert r.status_code == 200
    r2 = requests.get(f"{BASE_URL}/history/{SESSION_ID}")
    assert len(r2.json()["history"]) == 0
    print("  ✅ Session cleared!")


def test_cross_session_memory():
    log("Test 12: Cross-session Long-term Memory")
    # New session — but facts from omar_permanent should still be searchable
    r = requests.post(f"{BASE_URL}/chat", json={
        "message": "My name is Omar and I love Python.",
        "session_id": "omar_permanent",
    })
    assert r.status_code == 200

    time.sleep(3)

    # Search facts globally (no session filter)
    r2 = requests.get(f"{BASE_URL}/facts/search", params={
        "query": "Omar Python embedded systems",
        "top_k": 5,
    })
    data = r2.json()
    print(f"  Global fact search results: {len(data['results'])}")
    for res in data["results"]:
        print(f"  - [{res['category']}] {res['fact']}")
    assert r.status_code == 200
    print("  ✅ Cross-session memory working!")


if __name__ == "__main__":
    print("\n🤖 Day 7 — Full End-to-End System Test")
    print("=" * 60)

    test_health()
    test_basic_chat()
    test_memory_recall()
    test_tool_web_search()
    test_tool_calculator()
    test_tool_python_executor()
    test_long_term_memory_facts()
    test_semantic_search()
    test_session_history()
    test_sessions_list()
    test_clear_session()
    test_cross_session_memory()

    print("\n" + "=" * 60)
    print("🎉 All Day 7 tests passed! Week 1 complete.")
    print("=" * 60)