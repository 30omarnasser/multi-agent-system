import requests, time

BASE_URL = "http://localhost:8000"

def test_simple_task():
    print("\n--- Test 1: Simple task (no tools) ---")
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "What is the capital of France?",
        "session_id": "day8_test",
    })
    data = r.json()
    print(f"Plan: {data['plan']}")
    print(f"Agents used: {data['agents_used']}")
    print(f"Response: {data['response'][:300]}")
    assert r.status_code == 200
    assert "paris" in data["response"].lower()
    print("✅ Simple task passed!")

def test_research_task():
    print("\n--- Test 2: Research task ---")
    time.sleep(3)
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Search for and summarize the latest developments in LangGraph",
        "session_id": "day8_test",
    })
    data = r.json()
    print(f"Plan: {data['plan']}")
    print(f"Agents used: {data['agents_used']}")
    print(f"Critique score: {data['critique'].get('score')}/10")
    print(f"Response: {data['response'][:300]}")
    assert r.status_code == 200
    assert "researcher" in data["agents_used"]
    print("✅ Research task passed!")

def test_code_task():
    print("\n--- Test 3: Code task ---")
    time.sleep(3)
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Write and run Python code to generate the first 10 prime numbers",
        "session_id": "day8_test",
    })
    data = r.json()
    print(f"Plan: {data['plan']}")
    print(f"Agents used: {data['agents_used']}")
    print(f"Critique score: {data['critique'].get('score')}/10")
    print(f"Response: {data['response'][:300]}")
    assert r.status_code == 200
    assert "coder" in data["agents_used"]
    print("✅ Code task passed!")

def test_combined_task():
    print("\n--- Test 4: Combined research + code task ---")
    time.sleep(3)
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Search for the current Bitcoin price and write Python code to calculate how many BTC I can buy with $5000",
        "session_id": "day8_test",
    })
    data = r.json()
    print(f"Plan: {data['plan']}")
    print(f"Agents used: {data['agents_used']}")
    print(f"Critique score: {data['critique'].get('score')}/10")
    print(f"Response: {data['response'][:400]}")
    assert r.status_code == 200
    assert "researcher" in data["agents_used"]
    assert "coder" in data["agents_used"]
    print("✅ Combined task passed!")

if __name__ == "__main__":
    print("🤖 Day 8 — Multi-Agent Graph Tests")
    print("=" * 50)
    test_simple_task()
    test_research_task()
    test_code_task()
    test_combined_task()
    print("\n🎉 All Day 8 tests passed!")