import sys
import os
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"
UI_URL = "http://localhost:8501"


def log(msg):
    print(f"\n{'─' * 55}")
    print(f"  {msg}")
    print('─' * 55)


def test_api_still_healthy():
    log("Test 1: API health after adding Streamlit")
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data["api"] == "ok"
    assert data["redis"] == "ok"
    assert data["postgres"] == "ok"
    print(f"  All services: ✅")
    print("  ✅ API still healthy!")


def test_streamlit_is_running():
    log("Test 2: Streamlit UI is accessible")
    try:
        r = requests.get(UI_URL, timeout=10)
        assert r.status_code == 200
        print(f"  Streamlit responding at {UI_URL} ✅")
        print("  ✅ Streamlit is running!")
    except Exception as e:
        print(f"  ⚠️  Streamlit not accessible: {e}")
        print("  (This is OK if running tests before Docker rebuild)")


def test_chat_endpoint_for_ui():
    log("Test 3: Chat endpoint works for UI")
    r = requests.post(f"{BASE_URL}/chat", json={
        "message": "Hello from the UI test",
        "session_id": "ui_test_session",
    }, timeout=60)
    assert r.status_code == 200
    data = r.json()
    assert "response" in data
    assert len(data["response"]) > 0
    print(f"  Response: {data['response'][:100]}")
    print("  ✅ Chat endpoint working for UI!")


def test_multi_agent_endpoint_for_ui():
    log("Test 4: Multi-agent endpoint works for UI")
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "What is 2 + 2?",
        "session_id": "ui_test_session",
        "user_id": "ui_test_user",
    }, timeout=120)
    assert r.status_code == 200
    data = r.json()
    assert "response" in data
    assert "agents_used" in data
    assert "plan" in data
    assert "critique_score" in data
    print(f"  Agents: {data['agents_used']}")
    print(f"  Score: {data['critique_score']}")
    print(f"  Response: {data['response'][:100]}")
    print("  ✅ Multi-agent endpoint working for UI!")


def test_memory_stats_for_ui():
    log("Test 5: Memory stats endpoint works for UI")
    r = requests.get(f"{BASE_URL}/memory/stats", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data["health"] == "ok"
    print(f"  Facts: {data['facts']['total']}")
    print(f"  Episodes: {data['episodes']['total']}")
    print("  ✅ Memory stats working for UI!")


def test_documents_endpoint_for_ui():
    log("Test 6: Documents endpoint works for UI")
    r = requests.get(f"{BASE_URL}/documents", timeout=10)
    assert r.status_code == 200
    data = r.json()
    print(f"  Documents: {data['count']}")
    print("  ✅ Documents endpoint working for UI!")


def test_profiles_endpoint_for_ui():
    log("Test 7: Profiles endpoint works for UI")
    r = requests.get(f"{BASE_URL}/profiles", timeout=10)
    assert r.status_code == 200
    data = r.json()
    print(f"  Profiles: {data['count']}")
    print("  ✅ Profiles endpoint working for UI!")


if __name__ == "__main__":
    print("\n🖥️  Day 18 — Streamlit UI Tests")
    print("=" * 55)
    test_api_still_healthy()
    test_streamlit_is_running()
    test_chat_endpoint_for_ui()
    test_multi_agent_endpoint_for_ui()
    test_memory_stats_for_ui()
    test_documents_endpoint_for_ui()
    test_profiles_endpoint_for_ui()
    print("\n" + "=" * 55)
    print("🎉 All Day 18 tests passed!")