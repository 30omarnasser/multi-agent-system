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
from memory.postgres_memory import PostgresMemory

load_dotenv()

app = FastAPI(title="Multi-Agent System", version="0.1.0")

# ─── Setup ────────────────────────────────────────────────────

registry = ToolRegistry()
registry.register(calculator_tool)
registry.register(web_search_tool)
registry.register(python_executor_tool)

short_term_memory = RedisMemory(ttl_seconds=3600)
long_term_memory = PostgresMemory()

SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Respond naturally and conversationally to the user. "
    "When relevant facts from long-term memory are provided, use them naturally in your response. "
    "NEVER output raw JSON, function call syntax, or tool definitions in your response. "
    "Only use tools when explicitly asked to search, calculate, or run code."
)

agent = BaseAgent(
    name="AssistantAgent",
    system_prompt=SYSTEM_PROMPT,
    model="llama3.1:8b",
    registry=registry,
    memory=short_term_memory,
    long_term_memory=long_term_memory,
)

# ─── Request/Response Models ──────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    clear_history: bool = False

class ChatResponse(BaseModel):
    response: str
    agent_name: str
    session_id: str
    history_length: int
    input_tokens: int
    output_tokens: int

class FactIn(BaseModel):
    fact: str
    category: str = "general"
    session_id: str = "default"

# ─── Endpoints ────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Multi-Agent System is running 🤖"}


@app.get("/health")
def health_check():
    status = {"api": "ok", "redis": "unknown", "postgres": "unknown", "ollama": "unknown"}
    try:
        r = redis_lib.Redis(host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")))
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
    try:
        import ollama as ollama_client
        client = ollama_client.Client(host=os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434"))
        client.list()
        status["ollama"] = "ok"
    except Exception as e:
        status["ollama"] = f"error: {str(e)}"
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
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")


@app.get("/history/{session_id}")
def get_history(session_id: str):
    return {"session_id": session_id, "history": short_term_memory.get_history(session_id)}


@app.delete("/history/{session_id}")
def clear_session(session_id: str):
    short_term_memory.clear_session(session_id)
    return {"message": f"Session '{session_id}' cleared"}


@app.get("/sessions")
def list_sessions():
    session_ids = short_term_memory.get_all_sessions()
    return [
        {
            "session_id": sid,
            "message_count": len(short_term_memory.get_history(sid)),
            "ttl_seconds": short_term_memory.get_session_ttl(sid),
        }
        for sid in session_ids
    ]


@app.get("/facts")
def get_all_facts(session_id: str = None):
    facts = long_term_memory.get_all_facts(session_id=session_id)
    return {"count": len(facts), "facts": facts}


@app.post("/facts")
def save_fact_manually(fact_in: FactIn):
    long_term_memory.save_fact(
        session_id=fact_in.session_id,
        fact=fact_in.fact,
        category=fact_in.category,
    )
    return {"message": "Fact saved successfully"}


@app.get("/facts/search")
def search_facts(query: str, session_id: str = None, top_k: int = 5):
    facts = long_term_memory.search_facts(
        query=query,
        session_id=session_id,
        top_k=top_k,
    )
    return {"query": query, "results": facts}


@app.delete("/facts/{session_id}")
def clear_facts(session_id: str):
    long_term_memory.clear_session_facts(session_id)
    return {"message": f"All facts cleared for session '{session_id}'"}