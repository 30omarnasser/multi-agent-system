from fastapi import FastAPI
from dotenv import load_dotenv
import redis
import psycopg2
import os

load_dotenv()

app = FastAPI(title="Multi-Agent System", version="0.1.0")


@app.get("/health")
def health_check():
    """Check that the API, Redis, and Postgres are all reachable."""
    status = {"api": "ok", "redis": "unknown", "postgres": "unknown"}

    # Test Redis
    try:
        r = redis.Redis(host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")))
        r.ping()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = f"error: {str(e)}"

    # Test Postgres
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            dbname=os.getenv("POSTGRES_DB"),
        )
        conn.close()
        status["postgres"] = "ok"
    except Exception as e:
        status["postgres"] = f"error: {str(e)}"

    return status


@app.get("/")
def root():
    return {"message": "Multi-Agent System is running 🤖"}