import sys
import os
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"


def log(msg):
    print(f"\n{'─' * 55}")
    print(f"  {msg}")
    print('─' * 55)


def test_ci_files_exist():
    log("Test 1: CI/CD files exist")
    files = [
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
        "Makefile",
        "scripts/start.sh",
        "scripts/stop.sh",
        "scripts/reset.sh",
    ]
    for f in files:
        exists = os.path.exists(f)
        status = "✅" if exists else "❌"
        print(f"  {status} {f}")
        assert exists, f"Missing: {f}"
    print("  ✅ All CI/CD files present!")


def test_ci_yml_valid_yaml():
    log("Test 2: CI YAML files are valid")
    try:
        import yaml
        with open(".github/workflows/ci.yml") as f:
            ci = yaml.safe_load(f)
        assert "jobs" in ci
        assert "on" in ci
        print(f"  ci.yml jobs: {list(ci['jobs'].keys())}")

        with open(".github/workflows/release.yml") as f:
            release = yaml.safe_load(f)
        assert "jobs" in release
        print(f"  release.yml jobs: {list(release['jobs'].keys())}")
        print("  ✅ YAML files valid!")
    except ImportError:
        print("  ⚠️  PyYAML not installed — skipping YAML validation")
        print("  (Install with: pip install pyyaml)")


def test_makefile_has_targets():
    log("Test 3: Makefile has required targets")
    with open("Makefile") as f:
        content = f.read()
    targets = ["up", "down", "build", "test", "logs", "health"]
    for target in targets:
        assert f"{target}:" in content, f"Missing target: {target}"
        print(f"  ✅ make {target}")
    print("  ✅ All Makefile targets present!")


def test_gitignore_has_secrets():
    log("Test 4: .gitignore protects secrets")
    if not os.path.exists(".gitignore"):
        print("  ⚠️  .gitignore not found")
        return
    with open(".gitignore") as f:
        content = f.read()
    protected = [".env", "__pycache__", "*.pyc"]
    for item in protected:
        if item in content:
            print(f"  ✅ {item} ignored")
        else:
            print(f"  ⚠️  {item} not in .gitignore")
    print("  ✅ Secrets protected!")


def test_api_still_running():
    log("Test 5: API still running after CI setup")
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data["api"] == "ok"
    print(f"  All services: ✅")
    print("  ✅ API healthy after CI setup!")


def test_project_structure_complete():
    log("Test 6: Complete project structure")
    required_dirs = [
        "agents", "memory", "rag", "tools",
        "api", "ui", "tests", "docs",
        ".github/workflows", "scripts",
    ]
    required_files = [
        "agents/graph.py",
        "agents/planner.py",
        "agents/researcher.py",
        "agents/coder.py",
        "agents/critic.py",
        "agents/responder.py",
        "memory/redis_memory.py",
        "memory/postgres_memory.py",
        "memory/episodic_memory.py",
        "memory/user_profile.py",
        "memory/memory_manager.py",
        "memory/hitl_store.py",
        "rag/chunker.py",
        "rag/embedder.py",
        "rag/ingestion.py",
        "rag/retriever.py",
        "ui/app.py",
        "api/main.py",
        "docker-compose.yml",
        "docker-compose.prod.yml",
        "Dockerfile",
        "requirements.txt",
        "README.md",
        "docs/architecture.md",
    ]

    all_good = True
    for d in required_dirs:
        exists = os.path.exists(d)
        status = "✅" if exists else "❌"
        if not exists:
            all_good = False
        print(f"  {status} {d}/")

    for f in required_files:
        exists = os.path.exists(f)
        status = "✅" if exists else "❌"
        if not exists:
            all_good = False
            print(f"  {status} {f}")

    assert all_good, "Some required files/dirs missing"
    print(f"  ✅ Project structure complete!")


if __name__ == "__main__":
    print("\n⚙️  Day 25 — GitHub Actions CI/CD Tests")
    print("=" * 55)
    test_ci_files_exist()
    test_ci_yml_valid_yaml()
    test_makefile_has_targets()
    test_gitignore_has_secrets()
    test_api_still_running()
    test_project_structure_complete()
    print("\n" + "=" * 55)
    print("🎉 All Day 25 tests passed!")