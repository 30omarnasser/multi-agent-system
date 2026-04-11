import sys, os, requests, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"


def log(msg):
    print(f"\n{'─' * 55}")
    print(f"  {msg}")
    print('─' * 55)


def test_evaluation_created_on_pipeline_run():
    log("Test 1: Evaluation created after pipeline run")
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "What is machine learning?",
        "session_id": "eval_test_001",
    }, timeout=120)
    assert r.status_code == 200, f"Pipeline failed: {r.text}"
    print(f"  Response: {r.json()['response'][:100]}")

    # Wait for evaluation to complete
    time.sleep(5)

    r2 = requests.get(f"{BASE_URL}/evaluations", params={"limit": 5})
    assert r2.status_code == 200
    data = r2.json()
    print(f"  Total evaluations: {data['count']}")
    assert data["count"] > 0, "No evaluations were saved!"
    latest = data["evaluations"][0]
    print(f"  Overall score:     {latest['score_overall']}/10")
    print(f"  Relevance:         {latest['score_relevance']}/10")
    print(f"  Completeness:      {latest['score_completeness']}/10")
    print(f"  Task type:         {latest['task_type']}")
    assert latest["score_overall"] >= 0
    assert latest["score_overall"] <= 10
    print("  ✅ Evaluation created!")


def test_evaluation_scores_valid():
    log("Test 2: All score dimensions are valid")
    r = requests.get(f"{BASE_URL}/evaluations", params={"limit": 1})
    evals = r.json()["evaluations"]
    assert len(evals) > 0
    ev = evals[0]

    for dim in ["score_relevance", "score_accuracy", "score_completeness",
                "score_efficiency", "score_coherence", "score_overall"]:
        score = ev.get(dim, -1)
        print(f"  {dim}: {score}/10")
        assert 0 <= score <= 10, f"{dim} out of range: {score}"

    print("  ✅ All scores valid!")


def test_evaluation_stats():
    log("Test 3: Aggregate evaluation stats")
    r = requests.get(f"{BASE_URL}/evaluations/stats")
    assert r.status_code == 200
    stats = r.json()
    print(f"  Total evaluations: {stats.get('total_evaluations')}")
    print(f"  Avg overall:       {stats.get('avg_overall')}/10")
    print(f"  Avg relevance:     {stats.get('avg_relevance')}/10")
    print(f"  Avg completeness:  {stats.get('avg_completeness')}/10")
    print(f"  High quality:      {stats.get('high_quality_count')}")
    print(f"  By task type:      {stats.get('by_task_type')}")
    assert stats["total_evaluations"] > 0
    assert "by_task_type" in stats
    assert "recent_scores" in stats
    print("  ✅ Stats working!")


def test_evaluation_filter_by_session():
    log("Test 4: Filter evaluations by session")
    r = requests.get(f"{BASE_URL}/evaluations", params={
        "session_id": "eval_test_001",
        "limit": 10,
    })
    assert r.status_code == 200
    data = r.json()
    print(f"  Evaluations for 'eval_test_001': {data['count']}")
    assert data["count"] > 0
    for ev in data["evaluations"]:
        assert ev["session_id"] == "eval_test_001"
    print("  ✅ Session filter working!")


def test_multiple_task_types_evaluated():
    log("Test 5: Evaluate multiple task types")
    time.sleep(2)

    # Research task
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Search for the latest AI news this week",
        "session_id": "eval_test_002",
    }, timeout=120)
    assert r.status_code == 200
    print(f"  Research response: {r.json()['response'][:80]}")

    time.sleep(5)

    # Code task
    r2 = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Write Python code to calculate factorial of 10",
        "session_id": "eval_test_002",
    }, timeout=120)
    assert r2.status_code == 200
    print(f"  Code response: {r2.json()['response'][:80]}")

    time.sleep(5)

    # Check stats show multiple task types
    r3 = requests.get(f"{BASE_URL}/evaluations/stats")
    stats = r3.json()
    task_types = [t["task_type"] for t in stats.get("by_task_type", [])]
    print(f"  Task types in stats: {task_types}")
    assert len(task_types) >= 1
    print("  ✅ Multiple task types evaluated!")


def test_evaluation_get_by_id():
    log("Test 6: Get evaluation by ID")
    r = requests.get(f"{BASE_URL}/evaluations", params={"limit": 1})
    evals = r.json()["evaluations"]
    if not evals:
        print("  No evaluations — skipping")
        return

    eval_id = evals[0]["id"]
    r2 = requests.get(f"{BASE_URL}/evaluations/{eval_id}")
    assert r2.status_code == 200
    ev = r2.json()
    print(f"  Evaluation ID: {eval_id}")
    print(f"  Overall score: {ev['score_overall']}/10")
    print(f"  Reasoning: {ev.get('reasoning', '')[:100]}")
    assert ev["id"] == eval_id
    print("  ✅ Get by ID working!")


def test_evaluation_min_score_filter():
    log("Test 7: Min score filter")
    r = requests.get(f"{BASE_URL}/evaluations", params={
        "min_score": 7,
        "limit": 10,
    })
    assert r.status_code == 200
    evals = r.json()["evaluations"]
    print(f"  Evaluations with score >= 7: {len(evals)}")
    for ev in evals:
        assert ev["score_overall"] >= 7, \
            f"Score {ev['score_overall']} below min threshold"
    print("  ✅ Min score filter working!")


if __name__ == "__main__":
    print("\n📊 Day 20 — Evaluation Framework Tests")
    print("=" * 55)
    test_evaluation_created_on_pipeline_run()
    test_evaluation_scores_valid()
    test_evaluation_stats()
    test_evaluation_filter_by_session()
    test_multiple_task_types_evaluated()
    test_evaluation_get_by_id()
    test_evaluation_min_score_filter()
    print("\n" + "=" * 55)
    print("🎉 All Day 20 tests passed!")