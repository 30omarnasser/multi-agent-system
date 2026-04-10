import requests
import time

BASE_URL = "http://localhost:8000"

def log(msg):
    print(f"\n{'='*55}")
    print(f"  {msg}")
    print('='*55)

def test_simple_pipeline():
    log("Test 1: Simple question — direct response")
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "What is machine learning?",
        "session_id": "day10_test",
    })
    assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
    data = r.json()
    print(f"  agents_used:    {data['agents_used']}")
    print(f"  critique_score: {data['critique_score']}")
    print(f"  response:       {data['response'][:300]}")
    assert "planner" in data["agents_used"]
    assert "responder" in data["agents_used"]
    assert len(data["response"]) > 50
    print("  ✅ Simple pipeline working!")


def test_research_pipeline():
    log("Test 2: Research question — full research flow")
    time.sleep(3)
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Search for the latest news about LangGraph framework",
        "session_id": "day10_test",
    })
    assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
    data = r.json()
    print(f"  agents_used:    {data['agents_used']}")
    print(f"  search_queries: {data['plan'].get('search_queries')}")
    print(f"  critique_score: {data['critique_score']}")
    print(f"  response:       {data['response'][:300]}")
    assert "researcher" in data["agents_used"]
    assert "responder" in data["agents_used"]
    assert len(data["response"]) > 100
    print("  ✅ Research pipeline working!")


def test_code_pipeline():
    log("Test 3: Code question — full code flow")
    time.sleep(3)
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Write Python code to calculate and print prime numbers up to 50",
        "session_id": "day10_test",
    })
    assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
    data = r.json()
    print(f"  agents_used:    {data['agents_used']}")
    print(f"  critique_score: {data['critique_score']}")
    print(f"  had_revision:   {data['had_revision']}")
    print(f"  response:       {data['response'][:300]}")
    assert "coder" in data["agents_used"]
    assert "critic" in data["agents_used"]
    assert "responder" in data["agents_used"]
    assert len(data["response"]) > 50
    print("  ✅ Code pipeline working!")


def test_full_pipeline():
    log("Test 4: Both research + code — full pipeline")
    time.sleep(3)
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Find the current price of Bitcoin and write Python to calculate how many I can buy with $5000",
        "session_id": "day10_test",
    })
    assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
    data = r.json()
    print(f"  agents_used:    {data['agents_used']}")
    print(f"  critique_score: {data['critique_score']}")
    print(f"  had_revision:   {data['had_revision']}")
    print(f"  response:       {data['response'][:400]}")
    assert "researcher" in data["agents_used"]
    assert "coder" in data["agents_used"]
    assert "critic" in data["agents_used"]
    assert "responder" in data["agents_used"]
    print("  ✅ Full pipeline working!")


def test_pipeline_metadata():
    log("Test 5: Pipeline metadata is complete")
    time.sleep(3)
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Explain what Redis is used for",
        "session_id": "day10_test",
    })
    data = r.json()
    print(f"  Full response data:")
    print(f"  - response length:  {len(data['response'])}")
    print(f"  - agents_used:      {data['agents_used']}")
    print(f"  - had_revision:     {data['had_revision']}")
    print(f"  - critique_score:   {data['critique_score']}")
    print(f"  - plan.task_type:   {data['plan'].get('task_type')}")
    print(f"  - plan.confidence:  {data['plan'].get('confidence')}")
    assert "response" in data
    assert "plan" in data
    assert "agents_used" in data
    assert "critique_score" in data
    assert "had_revision" in data
    print("  ✅ All metadata fields present!")


if __name__ == "__main__":
    print("\n🤖 Day 10 — Responder + Full Pipeline Tests")
    print("=" * 55)
    test_simple_pipeline()
    test_research_pipeline()
    test_code_pipeline()
    test_full_pipeline()
    test_pipeline_metadata()
    print("\n" + "=" * 55)
    print("🎉 All Day 10 tests passed!")