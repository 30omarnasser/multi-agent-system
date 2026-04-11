import sys, os, requests, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"


def log(msg):
    print(f"\n{'─' * 55}")
    print(f"  {msg}")
    print('─' * 55)


def test_trace_created_on_pipeline_run():
    log("Test 1: Trace created when pipeline runs")
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "What is 2 + 2?",
        "session_id": "trace_test_001",
    }, timeout=120)
    assert r.status_code == 200, f"Pipeline failed: {r.text}"
    print(f"  Pipeline response: {r.json()['response'][:100]}")

    time.sleep(2)

    r2 = requests.get(f"{BASE_URL}/traces", params={"limit": 5})
    assert r2.status_code == 200
    data = r2.json()
    print(f"  Total traces: {data['count']}")
    assert data["count"] > 0, "No traces were created!"
    latest = data["traces"][0]
    print(f"  Latest trace: {latest['trace_id']}")
    print(f"  Status: {latest['status']}")
    print(f"  Duration: {latest['total_duration_ms']}ms")
    assert latest["status"] == "success"
    assert latest["total_duration_ms"] > 0
    print("  ✅ Trace created successfully!")
    return latest["trace_id"]


def test_trace_has_spans():
    log("Test 2: Trace has agent spans")
    # Get latest trace
    r = requests.get(f"{BASE_URL}/traces", params={"limit": 1})
    traces = r.json()["traces"]
    assert len(traces) > 0
    trace_id = traces[0]["trace_id"]

    # Get full trace with spans
    r2 = requests.get(f"{BASE_URL}/traces/{trace_id}")
    assert r2.status_code == 200
    trace = r2.json()
    spans = trace.get("spans", [])
    print(f"  Trace ID: {trace_id}")
    print(f"  Spans count: {len(spans)}")
    for span in spans:
        print(
            f"  [{span['agent_name']}] "
            f"{span['duration_ms']}ms | "
            f"{span['status']} | "
            f"IN: {span['input_summary'][:50]}"
        )
    assert len(spans) > 0, "Trace should have at least one span!"
    assert all(s["status"] == "success" for s in spans)
    print("  ✅ Trace spans populated correctly!")


def test_trace_session_filter():
    log("Test 3: Filter traces by session")
    r = requests.get(f"{BASE_URL}/traces", params={
        "session_id": "trace_test_001",
        "limit": 10,
    })
    assert r.status_code == 200
    data = r.json()
    print(f"  Traces for 'trace_test_001': {data['count']}")
    assert data["count"] > 0
    for t in data["traces"]:
        assert t["session_id"] == "trace_test_001"
    print("  ✅ Session filtering working!")


def test_trace_stats():
    log("Test 4: Trace performance stats")
    r = requests.get(f"{BASE_URL}/traces/stats")
    assert r.status_code == 200
    stats = r.json()
    print(f"  Total traces:    {stats.get('total_traces')}")
    print(f"  Avg duration:    {stats.get('avg_duration_ms', 0):.0f}ms")
    print(f"  Avg score:       {stats.get('avg_score', 0):.1f}/10")
    print(f"  Task types:      {stats.get('by_task_type', {})}")
    print(f"  Agent perf:")
    for ap in stats.get("agent_performance", []):
        print(f"    {ap['agent_name']}: {int(ap['avg_ms'] or 0)}ms avg, {ap['calls']} calls")
    assert stats["total_traces"] > 0
    assert "by_task_type" in stats
    assert "agent_performance" in stats
    print("  ✅ Trace stats working!")


def test_research_trace_has_researcher_span():
    log("Test 5: Research task trace has researcher span")
    time.sleep(2)
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Search for the latest Python programming trends",
        "session_id": "trace_test_002",
    }, timeout=120)
    assert r.status_code == 200
    agents = r.json().get("agents_used", [])
    print(f"  Agents used: {agents}")
    assert "researcher" in agents

    time.sleep(2)

    # Get latest trace
    r2 = requests.get(f"{BASE_URL}/traces", params={
        "session_id": "trace_test_002",
        "limit": 1,
    })
    trace_id = r2.json()["traces"][0]["trace_id"]
    r3 = requests.get(f"{BASE_URL}/traces/{trace_id}")
    spans = r3.json()["spans"]
    span_agents = [s["agent_name"] for s in spans]
    print(f"  Span agents: {span_agents}")
    assert "researcher" in span_agents
    assert "planner" in span_agents
    print("  ✅ Research trace spans correct!")


def test_trace_delete():
    log("Test 6: Delete a trace")
    r = requests.get(f"{BASE_URL}/traces", params={"limit": 1})
    traces = r.json()["traces"]
    if not traces:
        print("  No traces to delete — skipping")
        return

    trace_id = traces[0]["trace_id"]
    r2 = requests.delete(f"{BASE_URL}/traces/{trace_id}")
    assert r2.status_code == 200
    print(f"  Deleted trace: {trace_id}")

    r3 = requests.get(f"{BASE_URL}/traces/{trace_id}")
    assert r3.status_code == 404
    print("  ✅ Trace deletion working!")


if __name__ == "__main__":
    print("\n🔍 Day 19 — Agent Trace Viewer Tests")
    print("=" * 55)
    test_trace_created_on_pipeline_run()
    test_trace_has_spans()
    test_trace_session_filter()
    test_trace_stats()
    test_research_trace_has_researcher_span()
    test_trace_delete()
    print("\n" + "=" * 55)
    print("🎉 All Day 19 tests passed!")