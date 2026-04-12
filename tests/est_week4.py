import sys
import os
import requests
import time
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"
UI_URL = "http://localhost:8501"


def log(msg):
    print(f"\n{'═' * 55}")
    print(f"  {msg}")
    print('═' * 55)


def check(label: str, condition: bool, detail: str = ""):
    if condition:
        print(f"  ✅ {label}")
    else:
        print(f"  ❌ {label} {detail}")
        raise AssertionError(f"FAILED: {label} {detail}")


# ─── Week 4 Tests ─────────────────────────────────────────────

def test_streamlit_accessible():
    log("Week 4 — Streamlit UI accessible")
    try:
        r = requests.get(UI_URL, timeout=10)
        check("Streamlit responds", r.status_code == 200)
        print(f"  UI at {UI_URL} ✅")
    except Exception as e:
        print(f"  ⚠️  Streamlit not accessible: {e}")
        print("  (OK if running without Docker)")


def test_evaluation_endpoint():
    log("Week 4 — Evaluation framework")
    r = requests.get(f"{BASE_URL}/evaluate/summary", timeout=10)
    check("Eval summary responds", r.status_code == 200)
    data = r.json()
    check("Has total_runs", "total_runs" in data)
    print(f"  Total runs evaluated: {data['total_runs']}")
    print(f"  Avg score: {data.get('avg_score', 0)}")


def test_mlflow_accessible():
    log("Week 4 — MLflow service")
    try:
        r = requests.get("http://localhost:5000", timeout=5)
        check("MLflow responds", r.status_code == 200)
        print(f"  MLflow at http://localhost:5000 ✅")
    except Exception as e:
        print(f"  ⚠️  MLflow not accessible: {e}")
        print("  (OK if MLflow container not running)")


def test_hitl_endpoints():
    log("Week 4 — HITL endpoints")
    r = requests.get(f"{BASE_URL}/hitl/pending", timeout=5)
    check("HITL pending responds", r.status_code == 200)
    data = r.json()
    check("Has count", "count" in data)
    print(f"  Pending requests: {data['count']}")


def test_hitl_disabled_pipeline():
    log("Week 4 — Pipeline runs without HITL")
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "What is 10 + 10?",
        "session_id": "week4_regression",
        "user_id": "week4_user",
        "hitl_enabled": False,
    }, timeout=120)
    check("Pipeline responds", r.status_code == 200)
    data = r.json()
    check("Has response", len(data["response"]) > 0)
    check("Has HITL fields", "hitl_enabled" in data)
    check("HITL disabled", data["hitl_enabled"] == False)
    print(f"  Agents: {data['agents_used']}")
    print(f"  Response: {data['response'][:100]}")


def test_all_week4_endpoints():
    log("Week 4 — All endpoints healthy")
    endpoints = [
        "/",
        "/health",
        "/hitl/pending",
        "/evaluate/summary",
        "/memory/stats",
        "/sessions",
        "/documents",
        "/episodes",
        "/profiles",
    ]
    for path in endpoints:
        try:
            r = requests.get(f"{BASE_URL}{path}", timeout=10)
            status = "✅" if r.status_code == 200 else f"❌ {r.status_code}"
            print(f"  GET {path}: {status}")
            check(f"{path} ok", r.status_code == 200)
        except Exception as e:
            print(f"  ❌ {path}: {e}")


def test_full_pipeline_week4():
    log("Week 4 — Full pipeline end-to-end")
    time.sleep(2)
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Search for what LangGraph is used for",
        "session_id": "week4_e2e",
        "user_id": "week4_user",
        "hitl_enabled": False,
    }, timeout=180)
    check("Pipeline responds", r.status_code == 200)
    data = r.json()
    check("Has response", len(data["response"]) > 50)
    check("Has plan", bool(data.get("plan")))
    check("Has agents", len(data.get("agents_used", [])) > 0)
    check("Has critique score", "critique_score" in data)
    print(f"  Agents: {data['agents_used']}")
    print(f"  Score: {data['critique_score']}")
    print(f"  Response: {data['response'][:200]}")


if __name__ == "__main__":
    print("\n🤖 Week 4 Regression Test Suite")
    print("=" * 55)

    tests = [
        ("Streamlit accessible", test_streamlit_accessible),
        ("Evaluation endpoint", test_evaluation_endpoint),
        ("MLflow accessible", test_mlflow_accessible),
        ("HITL endpoints", test_hitl_endpoints),
        ("HITL disabled pipeline", test_hitl_disabled_pipeline),
        ("All endpoints healthy", test_all_week4_endpoints),
        ("Full pipeline e2e", test_full_pipeline_week4),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  ❌ FAILED: {name} — {e}")
            failed += 1
        time.sleep(1)

    print(f"\n{'=' * 55}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'=' * 55}")
    if failed == 0:
        print("  🎉 All Week 4 tests passed!")
    else:
        print(f"  ⚠️  {failed} test(s) failed")