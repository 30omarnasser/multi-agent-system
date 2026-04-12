import sys
import os
import requests
import time
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"
TIMEOUT_SHORT = 10
TIMEOUT_LONG = 180


def log(msg):
    print(f"\n{'─' * 55}")
    print(f"  {msg}")
    print('─' * 55)


def post_with_retry(url, json, timeout=TIMEOUT_LONG, retries=3, delay=3):
    """POST with retry on connection errors (handles hot-reload race)."""
    for i in range(retries):
        try:
            return requests.post(url, json=json, timeout=timeout)
        except requests.exceptions.ConnectionError as e:
            if i < retries - 1:
                print(f"  [retry {i+1}/{retries}] Connection error, waiting {delay}s... ({e})")
                time.sleep(delay)
            else:
                raise


def get_with_retry(url, timeout=TIMEOUT_SHORT, retries=3, delay=3, params=None):
    """GET with retry on connection errors."""
    for i in range(retries):
        try:
            return requests.get(url, timeout=timeout, params=params)
        except requests.exceptions.ConnectionError as e:
            if i < retries - 1:
                print(f"  [retry {i+1}/{retries}] Connection error, waiting {delay}s... ({e})")
                time.sleep(delay)
            else:
                raise


# ─── Tests ────────────────────────────────────────────────────

def test_hitl_disabled_runs_normally():
    log("Test 1: HITL disabled — pipeline runs normally")
    r = post_with_retry(f"{BASE_URL}/multi-agent", json={
        "message": "What is Python?",
        "session_id": "hitl_test_001",
        "user_id": "hitl_user",
        "hitl_enabled": False,
    })
    assert r.status_code == 200, f"Failed: {r.text[:300]}"
    data = r.json()
    assert len(data["response"]) > 0, "Response should not be empty"
    assert data["hitl_enabled"] == False
    assert data["hitl_decision"] == "", f"Expected empty decision, got: {data['hitl_decision']}"
    assert data["hitl_request_id"] == "", f"Expected empty request_id, got: {data['hitl_request_id']}"
    print(f"  Response: {data['response'][:100]}")
    print(f"  HITL decision: '{data['hitl_decision']}'")
    print("  ✅ Normal run without HITL works!")


def test_hitl_pending_endpoint():
    log("Test 2: Pending approvals endpoint works")
    r = get_with_retry(f"{BASE_URL}/hitl/pending")
    assert r.status_code == 200, f"Failed: {r.text[:300]}"
    data = r.json()
    assert "count" in data, "Response missing 'count'"
    assert "requests" in data, "Response missing 'requests'"
    assert isinstance(data["requests"], list), "'requests' should be a list"
    print(f"  Pending requests: {data['count']}")
    print("  ✅ Pending endpoint working!")


def test_hitl_approve_flow():
    log("Test 3: HITL approve flow — auto-approve after creation")

    approved = {"done": False, "request_id": None}

    def auto_approve():
        """Poll for pending requests and approve the one for our session."""
        for _ in range(60):
            time.sleep(2)
            try:
                r = get_with_retry(f"{BASE_URL}/hitl/pending", timeout=5)
                if r.status_code == 200:
                    pending = r.json().get("requests", [])
                    for req in pending:
                        if req.get("session_id") == "hitl_test_approve":
                            rid = req["request_id"]
                            resp = requests.post(
                                f"{BASE_URL}/hitl/{rid}/approve",
                                params={"feedback": "Looks good, proceed!"},
                                timeout=5,
                            )
                            if resp.status_code == 200:
                                print(f"  [Auto-approver] ✅ Approved: {rid}")
                                approved["done"] = True
                                approved["request_id"] = rid
                                return
                            else:
                                print(f"  [Auto-approver] Approve failed: {resp.text[:100]}")
            except Exception as e:
                print(f"  [Auto-approver] Poll error: {e}")

    t = threading.Thread(target=auto_approve, daemon=True)
    t.start()

    r = post_with_retry(f"{BASE_URL}/multi-agent", json={
        "message": "Write Python code to calculate the sum of numbers 1 to 10",
        "session_id": "hitl_test_approve",
        "user_id": "hitl_user",
        "hitl_enabled": True,
    })

    assert r.status_code == 200, f"Failed: {r.text[:300]}"
    data = r.json()
    print(f"  HITL enabled:     {data['hitl_enabled']}")
    print(f"  HITL decision:    {data['hitl_decision']}")
    print(f"  HITL request_id:  {data['hitl_request_id']}")
    print(f"  Response:         {data['response'][:150]}")

    assert data["hitl_enabled"] == True
    assert data["hitl_decision"] in ("approved", "timeout"), \
        f"Expected 'approved' or 'timeout', got: '{data['hitl_decision']}'"
    assert len(data["response"]) > 0, "Response should not be empty"
    assert data["hitl_request_id"] != "", "Should have a request_id for code tasks"
    print("  ✅ HITL approve flow working!")


def test_hitl_reject_flow():
    log("Test 4: HITL reject flow — auto-reject")

    rejected = {"done": False}

    def auto_reject():
        """Poll for pending requests and reject the one for our session."""
        for _ in range(60):
            time.sleep(2)
            try:
                r = get_with_retry(f"{BASE_URL}/hitl/pending", timeout=5)
                if r.status_code == 200:
                    pending = r.json().get("requests", [])
                    for req in pending:
                        if req.get("session_id") == "hitl_test_reject":
                            rid = req["request_id"]
                            resp = requests.post(
                                f"{BASE_URL}/hitl/{rid}/reject",
                                params={"feedback": "Too risky, don't run this code"},
                                timeout=5,
                            )
                            if resp.status_code == 200:
                                print(f"  [Auto-rejecter] ✅ Rejected: {rid}")
                                rejected["done"] = True
                                return
                            else:
                                print(f"  [Auto-rejecter] Reject failed: {resp.text[:100]}")
            except Exception as e:
                print(f"  [Auto-rejecter] Poll error: {e}")

    t = threading.Thread(target=auto_reject, daemon=True)
    t.start()

    r = post_with_retry(f"{BASE_URL}/multi-agent", json={
        "message": "Write Python code to delete all files in a directory",
        "session_id": "hitl_test_reject",
        "user_id": "hitl_user",
        "hitl_enabled": True,
    })

    assert r.status_code == 200, f"Failed: {r.text[:300]}"
    data = r.json()
    print(f"  HITL decision:  {data['hitl_decision']}")
    print(f"  Response:       {data['response'][:200]}")

    assert data["hitl_enabled"] == True
    assert data["hitl_decision"] == "rejected", \
        f"Expected 'rejected', got: '{data['hitl_decision']}'"
    assert len(data["response"]) > 0, "Response should not be empty"

    # Responder should acknowledge the rejection in some way
    response_lower = data["response"].lower()
    assert any(word in response_lower for word in ("reject", "stop", "not", "request", "cannot", "unable", "declined")), \
        f"Response should mention rejection but got: {data['response'][:200]}"
    print("  ✅ HITL reject flow working!")


def test_hitl_session_requests():
    log("Test 5: Session requests endpoint")
    r = get_with_retry(f"{BASE_URL}/hitl/session/hitl_test_approve")
    assert r.status_code == 200, f"Failed: {r.text[:300]}"
    data = r.json()
    assert "count" in data
    assert "requests" in data
    assert isinstance(data["requests"], list)
    print(f"  Requests for session: {data['count']}")
    for req in data["requests"]:
        print(f"  - {req.get('request_id')} | status={req.get('status')} | agent={req.get('agent')}")
    # We ran an approve test earlier, so there should be at least 1
    assert data["count"] >= 1, "Expected at least 1 request from the approve test"
    print("  ✅ Session requests endpoint working!")


def test_hitl_simple_task_skips_checkpoint():
    log("Test 6: Simple task skips HITL checkpoint")
    r = post_with_retry(f"{BASE_URL}/multi-agent", json={
        "message": "What is the capital of Egypt?",
        "session_id": "hitl_test_simple",
        "user_id": "hitl_user",
        "hitl_enabled": True,
    })
    assert r.status_code == 200, f"Failed: {r.text[:300]}"
    data = r.json()
    task_type = data["plan"].get("task_type", "")
    print(f"  Task type:      {task_type}")
    print(f"  HITL decision:  '{data['hitl_decision']}'")
    print(f"  Response:       {data['response'][:100]}")

    # Simple tasks should not trigger HITL — decision stays empty or skipped
    assert data["hitl_decision"] in ("", "skipped", "approved"), \
        f"Simple task should not be rejected, got: '{data['hitl_decision']}'"
    assert len(data["response"]) > 0, "Response should not be empty"
    # Simple tasks should not create a HITL request
    assert data["hitl_request_id"] == "", \
        f"Simple task should not create a HITL request, got: '{data['hitl_request_id']}'"
    print("  ✅ Simple task skips HITL correctly!")


def test_hitl_get_request_by_id():
    log("Test 7: Get HITL request by ID")
    # First get a known request from session
    r = get_with_retry(f"{BASE_URL}/hitl/session/hitl_test_approve")
    assert r.status_code == 200
    data = r.json()

    if data["count"] == 0:
        print("  ⚠️  No requests found for session — skipping ID lookup")
        print("  ✅ Skipped (no prior requests)")
        return

    request_id = data["requests"][0]["request_id"]
    r2 = get_with_retry(f"{BASE_URL}/hitl/{request_id}")
    assert r2.status_code == 200, f"Failed: {r2.text[:300]}"
    req = r2.json()
    assert req["request_id"] == request_id
    assert "status" in req
    assert "agent" in req
    assert "created_at" in req
    print(f"  request_id: {req['request_id']}")
    print(f"  status:     {req['status']}")
    print(f"  agent:      {req['agent']}")
    print("  ✅ Get request by ID working!")


def test_hitl_all_endpoints():
    log("Test 8: All HITL endpoints respond correctly")
    endpoints = [
        ("GET", "/hitl/pending"),
        ("GET", "/hitl/session/hitl_test_approve"),
        ("GET", "/hitl/session/hitl_test_reject"),
        ("GET", "/hitl/session/nonexistent_session"),
    ]
    all_ok = True
    for method, path in endpoints:
        r = get_with_retry(f"{BASE_URL}{path}", timeout=5)
        ok = r.status_code == 200
        status = "✅" if ok else f"❌ {r.status_code}"
        print(f"  {method} {path}: {status}")
        if not ok:
            all_ok = False
    assert all_ok, "One or more HITL endpoints failed"
    print("  ✅ All HITL endpoints working!")


# ─── Entry Point ──────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🛡️  Day 22 — Human-in-the-Loop Tests")
    print("=" * 55)

    tests = [
        test_hitl_disabled_runs_normally,
        test_hitl_pending_endpoint,
        test_hitl_approve_flow,
        test_hitl_reject_flow,
        test_hitl_session_requests,
        test_hitl_simple_task_skips_checkpoint,
        test_hitl_get_request_by_id,
        test_hitl_all_endpoints,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n  ❌ FAILED: {test_fn.__name__}")
            print(f"     {e}")

    print("\n" + "=" * 55)
    print(f"  Results: {passed} passed, {failed} failed")
    if failed == 0:
        print("🎉 All Day 22 tests passed!")
    else:
        print("⚠️  Some tests failed — check output above.")
        sys.exit(1)