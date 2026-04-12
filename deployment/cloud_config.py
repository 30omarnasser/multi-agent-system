import os


def get_llm_config() -> dict:
    """
    Auto-detect LLM configuration based on environment.
    Local: use Ollama
    Cloud: use Gemini API (if GEMINI_API_KEY is set)
    """
    env = os.getenv("APP_ENV", "development")
    gemini_key = os.getenv("GEMINI_API_KEY", "")

    if env == "production" and gemini_key:
        return {
            "provider": "gemini",
            "model": "gemini-2.0-flash",
            "api_key": gemini_key,
        }
    else:
        return {
            "provider": "ollama",
            "model": os.getenv("AGENT_MODEL", "llama3.1:8b"),
            "host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        }


def get_db_config() -> dict:
    return {
        "host":     os.getenv("POSTGRES_HOST", "postgres"),
        "port":     os.getenv("POSTGRES_PORT", "5432"),
        "user":     os.getenv("POSTGRES_USER", "agent_user"),
        "password": os.getenv("POSTGRES_PASSWORD", "agent_pass"),
        "dbname":   os.getenv("POSTGRES_DB", "agent_db"),
    }


def get_redis_config() -> dict:
    return {
        "host":     os.getenv("REDIS_HOST", "redis"),
        "port":     int(os.getenv("REDIS_PORT", 6379)),
        "password": os.getenv("REDIS_PASSWORD", None),
    }


def is_production() -> bool:
    return os.getenv("APP_ENV", "development") == "production"


def is_local() -> bool:
    return not is_production()