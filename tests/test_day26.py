import sys, os, requests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"


def log(msg):
    print(f"\n{'─' * 55}")
    print(f"  {msg}")
    print('─' * 55)


def test_deployment_files_exist():
    log("Test 1: Deployment files exist")
    files = [
        "deployment/README.md",
        "deployment/render.yaml",
        "deployment/cloud_config.py",
        ".env.example",
    ]
    for f in files:
        exists = os.path.exists(f)
        print(f"  {'✅' if exists else '❌'} {f}")
        assert exists, f"Missing: {f}"
    print("  ✅ All deployment files present!")


def test_env_example_complete():
    log("Test 2: .env.example has all required keys")
    required = [
        "TAVILY_API_KEY",
        "OLLAMA_HOST",
        "AGENT_MODEL",
        "POSTGRES_HOST",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "REDIS_HOST",
        "REDIS_PORT",
        "APP_ENV",
    ]
    with open(".env.example") as f:
        content = f.read()
    for key in required:
        assert key in content, f"Missing: {key}"
        print(f"  ✅ {key}")
    print("  ✅ .env.example complete!")


def test_cloud_config_works():
    log("Test 3: Cloud config module works")
    sys.path.insert(0, ".")
    from deployment.cloud_config import get_llm_config, get_db_config, is_local
    config = get_llm_config()
    print(f"  LLM provider: {config['provider']}")
    print(f"  LLM model:    {config['model']}")
    assert "provider" in config
    assert "model" in config
    assert is_local() == True  # we're in dev
    print("  ✅ Cloud config working!")


def test_api_health_all_green():
    log("Test 4: All services healthy")
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


def test_render_yaml_valid():
    log("Test 5: render.yaml is valid YAML")
    import yaml
    with open("deployment/render.yaml") as f:
        config = yaml.safe_load(f)
    assert "services" in config
    service = config["services"][0]
    print(f"  Service name: {service['name']}")
    print(f"  Build cmd:    {service['buildCommand']}")
    print(f"  Start cmd:    {service['startCommand']}")
    assert service["healthCheckPath"] == "/health"
    print("  ✅ render.yaml valid!")


def test_dockerfile_production_ready():
    log("Test 6: Dockerfile is production-ready")
    with open("Dockerfile") as f:
        content = f.read()
    checks = [
        ("WORKDIR /app", "Has WORKDIR"),
        ("PYTHONPATH", "Sets PYTHONPATH"),
        ("COPY requirements.txt", "Copies requirements first"),
        ("pip install", "Installs dependencies"),
    ]
    for check, label in checks:
        assert check in content, f"Missing: {check}"
        print(f"  ✅ {label}")
    print("  ✅ Dockerfile production-ready!")


if __name__ == "__main__":
    print("\n☁️  Day 26 — Cloud Deployment Tests")
    print("=" * 55)
    test_deployment_files_exist()
    test_env_example_complete()
    test_cloud_config_works()
    test_api_health_all_green()
    test_render_yaml_valid()
    test_dockerfile_production_ready()
    print("\n" + "=" * 55)
    print("🎉 All Day 26 tests passed!")