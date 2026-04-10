import requests
import time

BASE_URL = "http://localhost:8000"


def log(msg):
    print(f"\n{'─' * 55}")
    print(f"  {msg}")
    print('─' * 55)


def test_plan_quality_simple():
    log("Test 1: Planner — simple task plan quality")
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "What is the capital of Japan?",
        "session_id": "day9_test",
    })
    data = r.json()
    plan = data["plan"]
    print(f"  task_type:      {plan.get('task_type')}")
    print(f"  needs_research: {plan.get('needs_research')}")
    print(f"  needs_code:     {plan.get('needs_code')}")
    print(f"  confidence:     {plan.get('confidence')}")
    print(f"  subtasks:       {plan.get('subtasks')}")
    print(f"  response:       {data['response'][:200]}")
    assert plan["task_type"] == "simple"
    assert plan["needs_research"] == False
    assert plan["needs_code"] == False
    assert "confidence" in plan
    assert "estimated_steps" in plan
    print("  ✅ Simple plan quality good!")


def test_plan_quality_research():
    log("Test 2: Planner — research task plan quality")
    time.sleep(3)
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Search for the latest Python 3.13 features",
        "session_id": "day9_test",
    })
    data = r.json()
    plan = data["plan"]
    print(f"  task_type:      {plan.get('task_type')}")
    print(f"  search_queries: {plan.get('search_queries')}")
    print(f"  confidence:     {plan.get('confidence')}")
    print(f"  agents_used:    {data['agents_used']}")
    print(f"  response:       {data['response'][:200]}")
    assert plan["task_type"] == "research"
    assert plan["needs_research"] == True
    assert len(plan.get("search_queries", [])) > 0, "Planner should generate search queries"
    assert "researcher" in data["agents_used"]
    print("  ✅ Research plan quality good!")


def test_plan_quality_code():
    log("Test 3: Planner — code task plan quality")
    time.sleep(3)
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Write Python code to generate and plot the first 20 Fibonacci numbers",
        "session_id": "day9_test",
    })
    data = r.json()
    plan = data["plan"]
    print(f"  task_type:          {plan.get('task_type')}")
    print(f"  code_requirements:  {plan.get('code_requirements')}")
    print(f"  confidence:         {plan.get('confidence')}")
    print(f"  agents_used:        {data['agents_used']}")
    print(f"  response:           {data['response'][:200]}")
    assert plan["task_type"] == "code"
    assert plan["needs_code"] == True
    assert len(plan.get("code_requirements", [])) > 0, "Planner should generate code requirements"
    assert "coder" in data["agents_used"]
    print("  ✅ Code plan quality good!")


def test_plan_quality_both():
    log("Test 4: Planner — both task plan quality")
    time.sleep(3)
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Find the current ETH price and write Python to calculate profit if I bought 10 ETH at $2000",
        "session_id": "day9_test",
    })
    data = r.json()
    plan = data["plan"]
    print(f"  task_type:          {plan.get('task_type')}")
    print(f"  search_queries:     {plan.get('search_queries')}")
    print(f"  code_requirements:  {plan.get('code_requirements')}")
    print(f"  confidence:         {plan.get('confidence')}")
    print(f"  agents_used:        {data['agents_used']}")
    print(f"  response:           {data['response'][:300]}")
    assert plan["task_type"] == "both"
    assert plan["needs_research"] == True
    assert plan["needs_code"] == True
    assert "researcher" in data["agents_used"]
    assert "coder" in data["agents_used"]
    print("  ✅ Both task plan quality good!")


def test_fallback_plan():
    log("Test 5: Planner — fallback heuristics work")
    time.sleep(3)
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "search for news about AI and write code to analyze it",
        "session_id": "day9_test",
    })
    data = r.json()
    plan = data["plan"]
    print(f"  task_type:   {plan.get('task_type')}")
    print(f"  agents_used: {data['agents_used']}")
    print(f"  response:    {data['response'][:200]}")
    assert r.status_code == 200
    assert data["response"] != ""
    print("  ✅ Fallback plan handled gracefully!")


if __name__ == "__main__":
    print("\n🤖 Day 9 — Advanced Planner Tests")
    print("=" * 55)
    test_plan_quality_simple()
    test_plan_quality_research()
    test_plan_quality_code()
    test_plan_quality_both()
    test_fallback_plan()
    print("\n" + "=" * 55)
    print("🎉 All Day 9 tests passed!")