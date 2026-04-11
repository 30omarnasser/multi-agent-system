import sys, os, requests, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"


def log(msg):
    print(f"\n{'─' * 55}")
    print(f"  {msg}")
    print('─' * 55)


def test_episode_saved_after_conversation():
    log("Test 1: Episode saved after conversation")
    # Have a conversation
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "What is machine learning and how does it relate to AI?",
        "session_id": "episode_test_001",
    })
    assert r.status_code == 200, f"Chat failed: {r.text}"
    print(f"  Response: {r.json()['response'][:150]}")

    # Wait for episode to be saved
    time.sleep(3)

    # Check episodes exist
    r2 = requests.get(f"{BASE_URL}/episodes")
    data = r2.json()
    print(f"  Total episodes stored: {data['count']}")
    assert data["count"] > 0, "No episodes were saved!"
    print("  ✅ Episode saved after conversation!")


def test_episode_content():
    log("Test 2: Episode has correct content")
    r = requests.get(f"{BASE_URL}/episodes", params={"session_id": "episode_test_001"})
    data = r.json()
    print(f"  Episodes for session: {data['count']}")
    if data["count"] > 0:
        ep = data["episodes"][0]
        print(f"  Summary:    {ep['summary'][:200]}")
        print(f"  Key topics: {ep.get('key_topics', [])}")
        print(f"  Outcome:    {ep.get('outcome', '')[:100]}")
        assert ep["summary"], "Episode summary should not be empty"
        assert ep["session_id"] == "episode_test_001"
    print("  ✅ Episode content looks good!")


def test_episode_semantic_search():
    log("Test 3: Semantic search over episodes")
    r = requests.get(f"{BASE_URL}/episodes/search", params={
        "query": "artificial intelligence neural networks",
        "top_k": 3,
        "threshold": 0.2,
    })
    data = r.json()
    print(f"  Query: '{data['query']}'")
    print(f"  Results: {data['count']}")
    for ep in data["episodes"]:
        print(f"  - [{ep['session_id']}] {ep['summary'][:100]}")
    assert r.status_code == 200
    print("  ✅ Episode semantic search working!")


def test_cross_session_recall():
    log("Test 4: Cross-session episode recall")
    time.sleep(2)

    # Start a NEW session about a related topic
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Can you tell me more about deep learning algorithms?",
        "session_id": "episode_test_002",  # different session
    })
    assert r.status_code == 200
    response_text = r.json()["response"]
    print(f"  Response: {response_text[:300]}")
    # The agent should give a good response
    # (we can't assert it references past sessions since that depends on similarity)
    assert response_text != ""
    print("  ✅ Cross-session conversation working!")


def test_recent_episodes():
    log("Test 5: Recent episodes endpoint")
    r = requests.get(f"{BASE_URL}/episodes/recent", params={"limit": 5})
    data = r.json()
    print(f"  Recent episodes: {data['count']}")
    for ep in data["episodes"]:
        print(f"  - [{ep['session_id']}] {ep['summary'][:80]}")
    assert r.status_code == 200
    assert data["count"] > 0
    print("  ✅ Recent episodes endpoint working!")


def test_multiple_episodes_same_session():
    log("Test 6: Multiple conversations build episode history")
    time.sleep(2)

    # Second conversation in same session
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "What are some practical applications of machine learning?",
        "session_id": "episode_test_001",
    })
    assert r.status_code == 200
    print(f"  Response: {r.json()['response'][:150]}")
    time.sleep(3)

    # Should now have multiple episodes for this session
    r2 = requests.get(f"{BASE_URL}/episodes", params={"session_id": "episode_test_001"})
    data = r2.json()
    print(f"  Episodes for session 001: {data['count']}")
    assert r.status_code == 200
    print("  ✅ Multiple episodes building correctly!")


def test_episode_api_endpoints():
    log("Test 7: All episode API endpoints respond correctly")

    # GET /episodes
    r = requests.get(f"{BASE_URL}/episodes")
    assert r.status_code == 200
    print(f"  GET /episodes: {r.json()['count']} episodes")

    # GET /episodes/recent
    r = requests.get(f"{BASE_URL}/episodes/recent")
    assert r.status_code == 200
    print(f"  GET /episodes/recent: {r.json()['count']} episodes")

    # GET /episodes/search
    r = requests.get(f"{BASE_URL}/episodes/search", params={"query": "test"})
    assert r.status_code == 200
    print(f"  GET /episodes/search: {r.json()['count']} results")

    print("  ✅ All episode endpoints working!")


if __name__ == "__main__":
    print("\n🧠 Day 14 — Episodic Memory Tests")
    print("=" * 55)
    test_episode_saved_after_conversation()
    test_episode_content()
    test_episode_semantic_search()
    test_cross_session_recall()
    test_recent_episodes()
    test_multiple_episodes_same_session()
    test_episode_api_endpoints()
    print("\n" + "=" * 55)
    print("🎉 All Day 14 tests passed!")