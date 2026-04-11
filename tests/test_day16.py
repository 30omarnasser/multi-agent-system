import sys
import os
import requests
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"


def log(msg):
    print(f"\n{'─' * 55}")
    print(f"  {msg}")
    print('─' * 55)


def test_memory_stats_dashboard():
    log("Test 1: Memory stats dashboard")
    r = requests.get(f"{BASE_URL}/memory/stats")
    assert r.status_code == 200, f"Failed: {r.text}"
    data = r.json()

    print(f"  timestamp:    {data.get('timestamp')}")
    print(f"  health:       {data.get('health')}")
    print(f"  facts:")
    print(f"    total:      {data['facts'].get('total')}")
    print(f"    by_category:{data['facts'].get('by_category')}")
    print(f"  episodes:")
    print(f"    total:      {data['episodes'].get('total')}")
    print(f"    sessions:   {data['episodes'].get('sessions')}")
    print(f"  documents:")
    print(f"    chunks:     {data['documents'].get('total_chunks')}")
    print(f"    docs:       {data['documents'].get('total_docs')}")
    print(f"  profiles:")
    print(f"    total:      {data['profiles'].get('total')}")
    print(f"  recommendations:")
    for rec in data.get("recommendations", []):
        print(f"    - {rec}")

    assert data["health"] == "ok"
    assert "facts" in data
    assert "episodes" in data
    assert "documents" in data
    assert "profiles" in data
    assert "recommendations" in data
    print("  ✅ Memory stats dashboard working!")


def test_fact_deduplication():
    log("Test 2: Fact deduplication")

    # Manually save duplicate facts
    for _ in range(3):
        requests.post(f"{BASE_URL}/facts", json={
            "fact": "Omar is building a multi-agent system",
            "category": "project",
            "session_id": "dedup_test",
        })

    # Check facts before dedup
    r = requests.get(f"{BASE_URL}/facts", params={"session_id": "dedup_test"})
    before_count = r.json()["count"]
    print(f"  Facts before dedup: {before_count}")

    # Run deduplication
    r = requests.post(
        f"{BASE_URL}/memory/deduplicate-facts",
        params={"session_id": "dedup_test"}
    )
    assert r.status_code == 200
    removed = r.json()["duplicates_removed"]
    print(f"  Duplicates removed: {removed}")

    # Check after
    r = requests.get(f"{BASE_URL}/facts", params={"session_id": "dedup_test"})
    after_count = r.json()["count"]
    print(f"  Facts after dedup: {after_count}")

    assert after_count <= before_count
    print("  ✅ Fact deduplication working!")


def test_prune_facts():
    log("Test 3: Prune old facts endpoint")
    r = requests.post(
        f"{BASE_URL}/memory/prune-facts",
        params={"days_old": 365}
    )
    assert r.status_code == 200
    data = r.json()
    print(f"  Deleted: {data['deleted']} facts older than {data['days_old']} days")
    assert "deleted" in data
    print("  ✅ Fact pruning endpoint working!")


def test_prune_episodes():
    log("Test 4: Prune old episodes endpoint")
    r = requests.post(
        f"{BASE_URL}/memory/prune-episodes",
        params={"days_old": 365}
    )
    assert r.status_code == 200
    data = r.json()
    print(f"  Deleted: {data['deleted']} episodes older than {data['days_old']} days")
    assert "deleted" in data
    print("  ✅ Episode pruning endpoint working!")


def test_summarize_facts():
    log("Test 5: Summarize facts for a session")

    # First add some facts
    facts = [
        ("Omar is building a multi-agent AI system", "project"),
        ("Omar prefers Python for backend development", "preference"),
        ("Omar is studying embedded systems at university", "personal"),
    ]
    for fact, category in facts:
        requests.post(f"{BASE_URL}/facts", json={
            "fact": fact,
            "category": category,
            "session_id": "summary_test",
        })

    # Summarize
    r = requests.get(f"{BASE_URL}/memory/summarize-facts/summary_test")
    assert r.status_code == 200
    data = r.json()
    print(f"  Session: {data['session_id']}")
    print(f"  Summary: {data['summary'][:300]}")
    assert data["summary"]
    print("  ✅ Fact summarization working!")


def test_document_stats():
    log("Test 6: Document stats")
    r = requests.get(f"{BASE_URL}/memory/document-stats")
    assert r.status_code == 200
    data = r.json()
    print(f"  Total documents: {data['count']}")
    for doc in data["documents"]:
        print(f"  - {doc['filename']} | chunks: {doc['chunk_count']} | "
              f"chars: {doc.get('total_chars', 0)}")
    print("  ✅ Document stats working!")


def test_full_maintenance_run():
    log("Test 7: Full maintenance run")
    r = requests.post(
        f"{BASE_URL}/memory/maintenance",
        params={
            "prune_facts_days": 365,
            "prune_episodes_days": 365,
            "deduplicate": True,
        }
    )
    assert r.status_code == 200
    report = r.json()
    print(f"  Status:                 {report.get('status')}")
    print(f"  Facts pruned:           {report.get('facts_pruned')}")
    print(f"  Facts deduplicated:     {report.get('facts_deduplicated')}")
    print(f"  Episodes pruned:        {report.get('episodes_pruned')}")
    print(f"  Episodes deduplicated:  {report.get('episodes_deduplicated')}")
    print(f"  Errors:                 {report.get('errors')}")
    assert report["status"] in ("completed", "completed_with_errors")
    assert "facts_pruned" in report
    assert "episodes_pruned" in report
    print("  ✅ Full maintenance run working!")


def test_all_management_endpoints():
    log("Test 8: All memory management endpoints respond")
    endpoints = [
        ("GET", "/memory/stats", {}),
        ("GET", "/memory/document-stats", {}),
        ("GET", "/memory/summarize-facts/test_session", {}),
        ("POST", "/memory/prune-facts", {"days_old": 999}),
        ("POST", "/memory/prune-episodes", {"days_old": 999}),
        ("POST", "/memory/deduplicate-facts", {}),
        ("POST", "/memory/deduplicate-episodes", {}),
        ("POST", "/memory/maintenance", {}),
    ]
    for method, path, params in endpoints:
        if method == "GET":
            r = requests.get(f"{BASE_URL}{path}", params=params)
        else:
            r = requests.post(f"{BASE_URL}{path}", params=params)
        status = "✅" if r.status_code == 200 else f"❌ {r.status_code}"
        print(f"  {method} {path}: {status}")
        assert r.status_code == 200, f"Failed: {r.text[:200]}"
    print("  ✅ All memory management endpoints working!")


if __name__ == "__main__":
    print("\n🧹 Day 16 — Memory Management Tests")
    print("=" * 55)
    test_memory_stats_dashboard()
    test_fact_deduplication()
    test_prune_facts()
    test_prune_episodes()
    test_summarize_facts()
    test_document_stats()
    test_full_maintenance_run()
    test_all_management_endpoints()
    print("\n" + "=" * 55)
    print("🎉 All Day 16 tests passed!")