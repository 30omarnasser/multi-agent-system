from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import redis
import psycopg2
import os
import traceback

from agents.base_agent import BaseAgent

load_dotenv()

app = FastAPI(title="Multi-Agent System", version="0.1.0")

agent = BaseAgent(
    name="AssistantAgent",
    system_prompt="You are a helpful AI assistant that is part of a multi-agent system. You are clear, concise, and always explain your reasoning step by step.",
    model="gemini-2.5-flash"

)

class ChatRequest(BaseModel):
    message: str
    clear_history: bool = False

class ChatResponse(BaseModel):
    response: str
    agent_name: str
    input_tokens: int
    output_tokens: int
    history_length: int

@app.get("/health")
def health_check():
    status = {"api": "ok", "redis": "unknown", "postgres": "unknown"}
    try:
        r = redis.Redis(host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")))
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

@app.get("/")
def root():
    return {"message": "Multi-Agent System is running 🤖"}

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        if request.clear_history:
            agent.clear_history()
        result = agent.run(request.message)
        return ChatResponse(
            response=result.content,
            agent_name=result.agent_name,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            history_length=len(agent.history),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")

@app.get("/history")
def get_history():
    return {"history": agent.get_history()}

@app.delete("/history")
def clear_history():
    agent.clear_history()
    return {"message": "History cleared"}