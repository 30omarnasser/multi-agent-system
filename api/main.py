from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import redis as redis_lib
import psycopg2
import os
import traceback

from agents.base_agent import BaseAgent
from tools.registry import ToolRegistry
from tools.definitions import calculator_tool, web_search_tool, python_executor_tool
from memory.redis_memory import RedisMemory

load_dotenv()

app = FastAPI(title="Multi-Agent System", version="0.1.0")

# ─── Setup ────────────────────────────────────────────────────

registry = ToolRegistry()
registry.register(calculator_tool)
registry.register(web_search_tool)
registry.register(python_executor_tool)

memory = RedisMemory(ttl_seconds=3600)  # sessions live 1 hour

SYSTEM_PROMPT = (
    "You are a helpful AI assistant that is part of a multi-agent system. "
    "Today's date is April 2026. "
    "ALWAYS use your tools when asked — never refuse to search or run code. "
    "You are clear, concise, and always explain your reasoning step by step."
)

agent = BaseAgent(
    name="AssistantAgent",
    system_prompt=SYSTEM_PROMPT,
    model="llama3.2",
    registry=registry,
    memory=memory,
)

# ─── Request/Response Models ──────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"   # each user/conversation gets a unique ID
    clear_history: bool = False

class ChatResponse(BaseModel):
    response: str
    agent_name: str
    session_id: str
    history_length: int
    input_tokens: int
    output_tokens: int

class SessionInfo(BaseModel):
    session_id: str
    message_count: int
    ttl_seconds: int

# ─── Endpoints ────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Multi-Agent System is running 🤖"}


@app.get("/health")
def health_check():
    status = {"api": "ok", "redis": "unknown", "postgres": "unknown"}
    try:
        r = redis_lib.Redis(
            host=os.getenv("REDIS_HOST"),
            port=int(os.getenv("REDIS_PORT"))
        )
        r.ping()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = f"error: {str(e)}"
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


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        if request.clear_history:
            agent.load_session(request.session_id)
            agent.clear_history()

        result = agent.run(
            user_message=request.message,
            session_id=request.session_id,
        )

        return ChatResponse(
            response=result.content,
            agent_name=result.agent_name,
            session_id=request.session_id,
            history_length=len(agent.history),
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{str(e)}\n{traceback.format_exc()}"
        )


@app.get("/history/{session_id}")
def get_history(session_id: str):
    """Get full conversation history for a session."""
    history = memory.get_history(session_id)
    return {"session_id": session_id, "history": history}


@app.delete("/history/{session_id}")
def clear_session(session_id: str):
    """Delete all history for a session."""
    memory.clear_session(session_id)
    return {"message": f"Session '{session_id}' cleared"}


@app.get("/sessions", response_model=list[SessionInfo])
def list_sessions():
    """List all active sessions with their message count and TTL."""
    session_ids = memory.get_all_sessions()
    result = []
    for sid in session_ids:
        history = memory.get_history(sid)
        result.append(SessionInfo(
            session_id=sid,
            message_count=len(history),
            ttl_seconds=memory.get_session_ttl(sid),
        ))
    return result