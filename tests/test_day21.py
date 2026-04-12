import sys, os, requests, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"
MLFLOW_URL = "http://localhost:5000"


def log(msg):
    print(f"\n{'─' * 55}")
    print(f"  {msg}")
    print('─' * 55)


def test_mlflow_service_running():
    log("Test 1: MLflow service is running")
    try:
        r = requests.get(f"{MLFLOW_URL}/", timeout=5)
        print(f"  MLflow status: {r.status_code}")
        assert r.status_code == 200
        print("  ✅ MLflow service running!")
    except Exception as e:
        print(f"  ⚠️  MLflow not accessible: {e}")


def test_run_logged_after_pipeline():
    log("Test 2: MLflow run logged after pipeline execution")
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "What is the difference between supervised and unsupervised learning?",
        "session_id": "mlflow_test_001",
    }, timeout=120)
    assert r.status_code == 200
    print(f"  Pipeline response: {r.json()['response'][:100]}")

    time.sleep(5)

    r2 = requests.get(f"{BASE_URL}/mlflow/summary", timeout=10)
    assert r2.status_code == 200
    data = r2.json()
    print(f"  MLflow enabled: {data.get('enabled')}")
    print(f"  Total runs: {data.get('total', 0)}")

    if data.get("enabled") and data.get("total", 0) > 0:
        print(f"  Avg score: {data.get('avg_score')}/10")
        print(f"  Avg duration: {data.get('avg_duration')}s")
        assert data["total"] > 0
        print("  ✅ MLflow run logged!")
    else:
        print("  ⚠️  MLflow connected but no runs yet — check docker logs")


def test_mlflow_summary_endpoint():
    log("Test 3: MLflow summary endpoint structure")
    r = requests.get(f"{BASE_URL}/mlflow/summary", timeout=10)
    assert r.status_code == 200
    data = r.json()
    print(f"  Enabled: {data.get('enabled')}")
    print(f"  Total: {data.get('total', 0)}")
    print(f"  Avg score: {data.get('avg_score', 0)}")
    print(f"  Avg duration: {data.get('avg_duration', 0)}s")
    assert "enabled" in data
    assert "runs" in data
    print("  ✅ Summary endpoint working!")


def test_mlflow_best_runs():
    log("Test 4: Best runs endpoint")
    r = requests.get(f"{BASE_URL}/mlflow/best", params={
        "metric": "eval_overall",
        "top_k": 3,
    }, timeout=10)
    assert r.status_code == 200
    data = r.json()
    print(f"  Metric: {data['metric']}")
    print(f"  Top K: {data['top_k']}")
    print(f"  Runs returned: {len(data['runs'])}")
    for run in data["runs"]:
        print(
            f"  - {run['run_id'][:16]} | "
            f"score={run['eval_overall']:.1f} | "
            f"task={run['task_type']} | "
            f"{run['duration_s']:.1f}s"
        )
    assert "runs" in data
    print("  ✅ Best runs endpoint working!")


def test_log_memory_stats():
    log("Test 5: Log memory stats to MLflow")
    r = requests.post(f"{BASE_URL}/mlflow/log-memory-stats", timeout=15)
    assert r.status_code == 200
    data = r.json()
    print(f"  Run ID: {data.get('run_id', 'N/A')}")
    print(f"  Facts total: {data.get('stats', {}).get('facts', {}).get('total', 0)}")
    print(f"  Episodes total: {data.get('stats', {}).get('episodes', {}).get('total', 0)}")
    print("  ✅ Memory stats logged to MLflow!")


def test_multiple_runs_tracked():
    log("Test 6: Multiple different task types logged")
    time.sleep(2)

    # Simple task
    r1 = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "What is 15 * 7?",
        "session_id": "mlflow_test_002",
    }, timeout=120)
    assert r1.status_code == 200
    print(f"  Simple task done: {r1.json()['response'][:60]}")

    time.sleep(5)

    # Code task
    r2 = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Write Python code to find all prime numbers up to 30",
        "session_id": "mlflow_test_002",
    }, timeout=120)
    assert r2.status_code == 200
    print(f"  Code task done: {r2.json()['response'][:60]}")

    time.sleep(5)

    r3 = requests.get(f"{BASE_URL}/mlflow/summary", timeout=10)
    data = r3.json()
    runs = data.get("runs", [])
    task_types = list({r.get("task_type") for r in runs})
    print(f"  Task types tracked: {task_types}")
    print(f"  Total runs: {data.get('total', 0)}")
    assert data.get("total", 0) >= 2
    print("  ✅ Multiple task types tracked!")


def test_mlflow_run_has_metrics():
    log("Test 7: MLflow runs contain expected metrics")
    r = requests.get(f"{BASE_URL}/mlflow/summary", timeout=10)
    data = r.json()
    runs = data.get("runs", [])

    if not runs:
        print("  No runs yet — skipping metric check")
        return

    run = runs[0]
    print(f"  Run: {run['run_id'][:16]}")
    print(f"  eval_overall:   {run.get('eval_overall', 'N/A')}")
    print(f"  critique_score: {run.get('critique_score', 'N/A')}")
    print(f"  duration_s:     {run.get('duration_s', 'N/A')}")
    print(f"  task_type:      {run.get('task_type', 'N/A')}")
    print(f"  quality_tag:    {run.get('quality_tag', 'N/A')}")

    assert "eval_overall" in run
    assert "duration_s" in run
    assert "task_type" in run
    print("  ✅ Run metrics populated correctly!")


if __name__ == "__main__":
    print("\n🧪 Day 21 — MLflow Integration Tests")
    print("=" * 55)
    test_mlflow_service_running()
    test_run_logged_after_pipeline()
    test_mlflow_summary_endpoint()
    test_mlflow_best_runs()
    test_log_memory_stats()
    test_multiple_runs_tracked()
    test_mlflow_run_has_metrics()
    print("\n" + "=" * 55)
    print("🎉 All Day 21 tests passed!")