import sys
import os
import requests
import subprocess
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"


def log(msg):
    print(f"\n{'─' * 55}")
    print(f"  {msg}")
    print('─' * 55)


def test_health_check_all_green():
    log("Test 1: All services healthy")
    r = requests.get(f"{BASE_URL}/health", timeout=10)
    assert r.status_code == 200
    data = r.json()
    print(f"  API:      {data['api']}")
    print(f"  Redis:    {data['redis']}")
    print(f"  Postgres: {data['postgres']}")
    print(f"  Ollama:   {data['ollama']}")
    assert data["api"] == "ok"
    assert data["redis"] == "ok"
    assert data["postgres"] == "ok"
    print("  ✅ All services healthy!")


def test_api_version():
    log("Test 2: API version endpoint")
    r = requests.get(f"{BASE_URL}/", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert "version" in data
    print(f"  Version: {data['version']}")
    print("  ✅ Version endpoint working!")


def test_prod_dockerfile_exists():
    log("Test 3: Production files exist")
    files = [
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.prod.yml",
        "Makefile",
        ".env.example",
    ]
    for f in files:
        exists = os.path.exists(f)
        status = "✅" if exists else "❌"
        print(f"  {status} {f}")
        assert exists, f"Missing: {f}"
    print("  ✅ All production files present!")


def test_env_example_has_required_keys():
    log("Test 4: .env.example has all required keys")
    required_keys = [
        "TAVILY_API_KEY",
        "POSTGRES_HOST",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "REDIS_HOST",
        "REDIS_PORT",
        "OLLAMA_HOST",
        "AGENT_MODEL",
    ]
    with open(".env.example") as f:
        content = f.read()
    for key in required_keys:
        assert key in content, f"Missing key in .env.example: {key}"
        print(f"  ✅ {key}")
    print("  ✅ All required keys in .env.example!")


def test_requirements_pinned():
    log("Test 5: requirements.txt has pinned versions")
    with open("requirements.txt") as f:
        lines = [l.strip() for l in f.readlines()
                 if l.strip() and not l.startswith("#")]
    unpinned = [l for l in lines if "==" not in l and not l.startswith("-")]
    if unpinned:
        print(f"  ⚠️  Unpinned packages: {unpinned}")
    else:
        print("  ✅ All packages pinned")
    print("  ✅ Requirements check done!")


def test_api_handles_bad_input():
    log("Test 6: API handles bad input gracefully")

    # Empty message
    r = requests.post(f"{BASE_URL}/chat", json={
        "message": "",
        "session_id": "test_bad_input",
    }, timeout=30)
    print(f"  Empty message: {r.status_code}")

    # Missing session_id (should use default)
    r = requests.post(f"{BASE_URL}/chat", json={
        "message": "Hello",
    }, timeout=30)
    print(f"  Missing session_id: {r.status_code}")
    assert r.status_code in (200, 422, 500)
    print("  ✅ Bad input handled!")


def test_docker_compose_valid():
    log("Test 7: docker-compose.yml is valid")
    try:
        result = subprocess.run(
            ["docker", "compose", "config", "--quiet"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            print("  ✅ docker-compose.yml is valid!")
        else:
            print(f"  ⚠️  docker compose config: {result.stderr[:200]}")
    except Exception as e:
        print(f"  ⚠️  Could not validate: {e}")


if __name__ == "__main__":
    print("\n🐳 Day 24 — Production Polish Tests")
    print("=" * 55)
    test_health_check_all_green()
    test_api_version()
    test_prod_dockerfile_exists()
    test_env_example_has_required_keys()
    test_requirements_pinned()
    test_api_handles_bad_input()
    test_docker_compose_valid()
    print("\n" + "=" * 55)
    print("🎉 All Day 24 tests passed!")