from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from dotenv import load_dotenv
import redis as redis_lib
import psycopg2
import os
import traceback
import math
import time

from evaluation.evaluator import EvaluationEngine
from evaluation.eval_store import EvalStore
from evaluation.mlflow_logger import MLflowLogger
from agents.base_agent import BaseAgent
from agents.traced_graph import traced_pipeline
from agents.state import AgentState
from tools.registry import ToolRegistry
from tools.definitions import calculator_tool, web_search_tool, python_executor_tool
from memory.redis_memory import RedisMemory
from memory.postgres_memory import PostgresMemory
from memory.episodic_memory import EpisodicMemory
from memory.user_profile import UserProfileMemory
from memory.memory_manager import MemoryManager
from memory.trace_store import TraceStore
from memory.hitl_store import HITLStore
from rag.ingestion import DocumentIngestion
from rag.retriever import DocumentRetriever

load_dotenv()

app = FastAPI(title="Multi-Agent System", version="0.3.0")

# ─── Services Setup ───────────────────────────────────────────

registry = ToolRegistry()
registry.register(calculator_tool)
registry.register(web_search_tool)
registry.register(python_executor_tool)

short_term_memory = RedisMemory(ttl_seconds=3600)
long_term_memory = PostgresMemory()
doc_ingestion = DocumentIngestion()
doc_retriever = DocumentRetriever()
episodic_memory = EpisodicMemory()
user_profile_memory = UserProfileMemory()
memory_manager = MemoryManager()
trace_store = TraceStore()
evaluator = EvaluationEngine(model="llama3.1:8b")
eval_store = EvalStore()
mlflow_logger = MLflowLogger()
hitl_store = HITLStore()

SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Respond naturally and conversationally to the user. "
    "When relevant facts from long-term memory are provided, use them naturally. "
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

# ─── Request / Response Models ────────────────────────────────

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

class MultiAgentRequest(BaseModel):
    message: str
    session_id: str = "default"
    user_id: str = ""
    hitl_enabled: bool = False

class MultiAgentResponse(BaseModel):
    response: str
    session_id: str
    plan: dict
    critique: dict
    agents_used: list[str]
    had_revision: bool
    critique_score: int
    hitl_enabled: bool
    hitl_decision: str
    hitl_request_id: str

class FactIn(BaseModel):
    fact: str
    category: str = "general"
    session_id: str = "default"

# ─── Utility ──────────────────────────────────────────────────

def clean_json(obj):
    """Recursively clean NaN/Inf floats from JSON-serializable objects."""
    if isinstance(obj, dict):
        return {k: clean_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_json(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return 0
    return obj

# ─── Core Endpoints ───────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Multi-Agent System is running 🤖", "version": "0.3.0"}


@app.get("/health")
def health_check():
    status = {"api": "ok", "redis": "unknown", "postgres": "unknown", "ollama": "unknown"}
    try:
        r = redis_lib.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
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
    try:
        import requests as req
        ollama_url = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        resp = req.get(ollama_url, timeout=3)
        status["ollama"] = "ok"
    except Exception as e:
        status["ollama"] = f"error: {str(e)[:50]}"
    return status


# ─── Single Agent — Week 1 ────────────────────────────────────

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
            detail=f"{str(e)}\n{traceback.format_exc()}",
        )


# ─── Multi-Agent Pipeline — Week 2+ ──────────────────────────

@app.post("/multi-agent", response_model=MultiAgentResponse)
def multi_agent(request: MultiAgentRequest):
    pipeline_start = time.time()
    try:
        # Save user message to Redis
        try:
            short_term_memory.save_message(
                request.session_id, "user", request.message
            )
        except Exception as e:
            print(f"[API] Redis pre-save failed: {e}")

        # Recall user profile
        profile_context = ""
        try:
            uid = request.user_id or request.session_id
            profile_context = user_profile_memory.format_for_prompt(uid)
        except Exception as e:
            print(f"[API] Profile recall failed: {e}")

        # Recall past episodes
        episode_context = ""
        try:
            past_episodes = episodic_memory.search_episodes(
                query=request.message,
                top_k=3,
                threshold=0.3,
                exclude_session=request.session_id,
            )
            if past_episodes:
                episode_context = episodic_memory.format_episodes_for_prompt(past_episodes)
        except Exception as e:
            print(f"[API] Episode recall failed: {e}")

        # Create trace
        trace_id = trace_store.create_trace(
            session_id=request.session_id,
            user_message=request.message,
        )

        initial_state: AgentState = {
            "user_message": request.message,
            "plan": {},
            "research": "",
            "code_output": "",
            "critique": {},
            "revision_count": 0,
            "final_response": "",
            "current_agent": "",
            "session_id": request.session_id,
            "user_id": request.user_id or request.session_id,
            "search_queries": [],
            "code_requirements": [],
            "doc_context": "",
            "episode_context": episode_context,
            "profile_context": profile_context,
            "trace_id": trace_id,
            "hitl_enabled": request.hitl_enabled,
            "hitl_request_id": "",
            "hitl_decision": "",
            "hitl_feedback": "",
            "hitl_checkpoint": "",
        }

        print(f"\n{'=' * 55}")
        print(f"[Pipeline] Starting: '{request.message[:80]}'")
        print(f"[Pipeline] Trace ID: {trace_id}")
        print(f"{'=' * 55}")

        final_state = traced_pipeline.invoke(initial_state)

        # Save assistant response
        try:
            short_term_memory.save_message(
                request.session_id, "assistant",
                final_state.get("final_response", "")
            )
        except Exception as e:
            print(f"[API] Redis post-save failed: {e}")

        # Build agents_used list
        agents_used = []
        if final_state.get("plan"):
            agents_used.append("planner")
        if final_state.get("research"):
            agents_used.append("researcher")
        if final_state.get("code_output"):
            agents_used.append("coder")
        if final_state.get("critique"):
            agents_used.append("critic")
        if final_state.get("final_response"):
            agents_used.append("responder")

        critique = final_state.get("critique") or {}
        critique_score = int(critique.get("score", 0)) if critique.get("score") else 0
        had_revision = (final_state.get("revision_count", 0) > 1)
        total_duration_ms = int((time.time() - pipeline_start) * 1000)

        # Complete the trace
        try:
            trace_store.complete_trace(
                trace_id=trace_id,
                final_response=final_state.get("final_response", ""),
                agents_used=agents_used,
                total_duration_ms=total_duration_ms,
                critique_score=critique_score,
                had_revision=had_revision,
                task_type=final_state.get("plan", {}).get("task_type", "simple"),
            )
        except Exception as e:
            print(f"[API] Trace completion failed: {e}")

        print(f"[Pipeline] ✓ Complete | agents: {agents_used} | {total_duration_ms}ms")

        # Evaluate the response
        scores = {}
        try:
            scores = evaluator.evaluate(
                user_message=request.message,
                response=final_state.get("final_response", ""),
                agents_used=agents_used,
                task_type=final_state.get("plan", {}).get("task_type", "simple"),
                had_revision=had_revision,
                research=final_state.get("research", ""),
                code_output=final_state.get("code_output", ""),
                trace_id=trace_id,
            )
            eval_store.save_evaluation(
                session_id=request.session_id,
                user_message=request.message,
                response=final_state.get("final_response", ""),
                scores=scores,
                had_revision=had_revision,
            )
        except Exception as e:
            print(f"[API] Evaluation failed (non-critical): {e}")

        # Log to MLflow
        try:
            mlflow_logger.log_pipeline_run(
                session_id=request.session_id,
                user_message=request.message,
                final_response=final_state.get("final_response", ""),
                agents_used=agents_used,
                plan=final_state.get("plan") or {},
                critique=critique,
                eval_scores=scores,
                trace_id=trace_id,
                total_duration_ms=total_duration_ms,
                had_revision=had_revision,
            )
        except Exception as e:
            print(f"[API] MLflow logging failed (non-critical): {e}")

        return MultiAgentResponse(
            response=final_state.get("final_response", ""),
            session_id=request.session_id,
            plan=final_state.get("plan") or {},
            critique=critique,
            agents_used=agents_used,
            had_revision=had_revision,
            critique_score=critique_score,
            hitl_enabled=request.hitl_enabled,
            hitl_decision=final_state.get("hitl_decision", ""),
            hitl_request_id=final_state.get("hitl_request_id", ""),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{str(e)}\n{traceback.format_exc()}",
        )


# ─── Session / History ────────────────────────────────────────

@app.get("/history/{session_id}")
def get_history(session_id: str):
    return {
        "session_id": session_id,
        "history": short_term_memory.get_history(session_id),
    }


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


# ─── Long-term Memory / Facts ─────────────────────────────────

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


# ─── RAG / Document Endpoints ─────────────────────────────────

@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    doc_id: str = Form(None),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    try:
        pdf_bytes = await file.read()
        result = doc_ingestion.ingest_pdf(
            pdf_bytes=pdf_bytes,
            filename=file.filename,
            doc_id=doc_id,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
def list_documents():
    docs = doc_ingestion.list_documents()
    return {"count": len(docs), "documents": docs}


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: str):
    deleted = doc_ingestion.delete_document(doc_id)
    return {"message": f"Deleted {deleted} chunks for doc_id='{doc_id}'"}


@app.get("/search-docs")
def search_documents(
    query: str,
    top_k: int = 5,
    threshold: float = 0.2,
    doc_id: str = None,
    mode: str = "hybrid",
):
    results = doc_retriever.search(
        query=query,
        top_k=top_k,
        threshold=threshold,
        doc_id=doc_id,
        mode=mode,
    )
    return {"query": query, "mode": mode, "count": len(results), "results": results}


@app.get("/search-docs/context")
def get_doc_context(
    query: str,
    top_k: int = 5,
    doc_id: str = None,
    mode: str = "hybrid",
):
    context = doc_retriever.search_and_format(
        query=query, top_k=top_k, doc_id=doc_id, mode=mode,
    )
    return {"query": query, "mode": mode, "context": context}


@app.get("/search-docs/compare")
def compare_search_modes(query: str, top_k: int = 5, doc_id: str = None):
    vector_results = doc_retriever.search(query=query, top_k=top_k, doc_id=doc_id, mode="vector")
    keyword_results = doc_retriever.search(query=query, top_k=top_k, doc_id=doc_id, mode="keyword")
    hybrid_results = doc_retriever.search(query=query, top_k=top_k, doc_id=doc_id, mode="hybrid")
    return {
        "query": query,
        "vector":  {"count": len(vector_results),  "results": [{"text": r["text"][:100], "score": r.get("similarity")} for r in vector_results]},
        "keyword": {"count": len(keyword_results), "results": [{"text": r["text"][:100], "score": r.get("keyword_score")} for r in keyword_results]},
        "hybrid":  {"count": len(hybrid_results),  "results": [{"text": r["text"][:100], "score": r.get("rrf_score")} for r in hybrid_results]},
    }


# ─── Episodic Memory ──────────────────────────────────────────

@app.get("/episodes")
def get_all_episodes(session_id: str = None):
    episodes = episodic_memory.get_all_episodes(session_id=session_id)
    return {"count": len(episodes), "episodes": episodes}


@app.get("/episodes/search")
def search_episodes(query: str, top_k: int = 3, threshold: float = 0.3):
    episodes = episodic_memory.search_episodes(query=query, top_k=top_k, threshold=threshold)
    return {"query": query, "count": len(episodes), "episodes": episodes}


@app.get("/episodes/recent")
def get_recent_episodes(limit: int = 5):
    episodes = episodic_memory.get_recent_episodes(limit=limit)
    return {"count": len(episodes), "episodes": episodes}


@app.delete("/episodes/{episode_id}")
def delete_episode(episode_id: int):
    episodic_memory.delete_episode(episode_id)
    return {"message": f"Episode {episode_id} deleted"}


# ─── User Profiles ────────────────────────────────────────────

@app.get("/profile/{user_id}")
def get_profile(user_id: str):
    return user_profile_memory.get_profile(user_id)


@app.put("/profile/{user_id}")
def update_profile(user_id: str, updates: dict):
    return user_profile_memory.update_profile(user_id, updates)


@app.get("/profiles")
def list_profiles():
    profiles = user_profile_memory.list_profiles()
    return {"count": len(profiles), "profiles": profiles}


@app.delete("/profile/{user_id}")
def delete_profile(user_id: str):
    user_profile_memory.delete_profile(user_id)
    return {"message": f"Profile deleted for '{user_id}'"}


# ─── Memory Management ────────────────────────────────────────

@app.get("/memory/stats")
def get_memory_stats():
    return memory_manager.get_memory_stats()


@app.post("/memory/maintenance")
def run_maintenance(prune_facts_days: int = 30, prune_episodes_days: int = 60, deduplicate: bool = True):
    return memory_manager.run_maintenance(
        prune_facts_days=prune_facts_days,
        prune_episodes_days=prune_episodes_days,
        deduplicate=deduplicate,
    )


@app.post("/memory/prune-facts")
def prune_facts(days_old: int = 30, session_id: str = None):
    deleted = memory_manager.prune_old_facts(days_old=days_old, session_id=session_id)
    return {"deleted": deleted, "days_old": days_old}


@app.post("/memory/prune-episodes")
def prune_episodes(days_old: int = 60):
    deleted = memory_manager.prune_old_episodes(days_old=days_old)
    return {"deleted": deleted, "days_old": days_old}


@app.post("/memory/deduplicate-facts")
def deduplicate_facts(session_id: str = None):
    deleted = memory_manager.deduplicate_facts(session_id=session_id)
    return {"duplicates_removed": deleted}


@app.post("/memory/deduplicate-episodes")
def deduplicate_episodes(similarity_threshold: float = 0.95):
    deleted = memory_manager.deduplicate_episodes(similarity_threshold=similarity_threshold)
    return {"duplicates_removed": deleted}


@app.get("/memory/summarize-facts/{session_id}")
def summarize_facts(session_id: str):
    summary = memory_manager.summarize_facts(session_id=session_id)
    return {"session_id": session_id, "summary": summary}


@app.get("/memory/document-stats")
def get_document_stats():
    stats = memory_manager.get_document_stats()
    return {"count": len(stats), "documents": stats}


# ─── Traces ───────────────────────────────────────────────────

@app.get("/traces")
def list_traces(session_id: str = None, limit: int = 20):
    traces = trace_store.list_traces(session_id=session_id, limit=limit)
    return {"count": len(traces), "traces": traces}


@app.get("/traces/stats")
def get_trace_stats():
    return trace_store.get_stats()


@app.get("/traces/{trace_id}")
def get_trace(trace_id: str):
    trace = trace_store.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
    return trace


@app.delete("/traces/{trace_id}")
def delete_trace(trace_id: str):
    trace_store.delete_trace(trace_id)
    return {"message": f"Trace '{trace_id}' deleted"}


@app.delete("/traces")
def clear_old_traces(days_old: int = 7):
    deleted = trace_store.clear_old_traces(days_old=days_old)
    return {"deleted": deleted, "days_old": days_old}


# ─── Evaluations ──────────────────────────────────────────────

@app.get("/evaluations")
def list_evaluations(session_id: str = None, task_type: str = None, min_score: int = 0, limit: int = 20):
    evals = eval_store.list_evaluations(
        session_id=session_id, task_type=task_type, min_score=min_score, limit=limit,
    )
    return {"count": len(evals), "evaluations": evals}


@app.get("/evaluations/stats")
def get_evaluation_stats():
    return eval_store.get_aggregate_stats()


@app.get("/evaluations/{eval_id}")
def get_evaluation(eval_id: int):
    ev = eval_store.get_evaluation(eval_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evaluation {eval_id} not found")
    return ev


@app.delete("/evaluations/{eval_id}")
def delete_evaluation(eval_id: int):
    eval_store.delete_evaluation(eval_id)
    return {"message": f"Evaluation {eval_id} deleted"}


@app.delete("/evaluations")
def clear_evaluations(session_id: str = None):
    deleted = eval_store.clear_evaluations(session_id=session_id)
    return {"deleted": deleted}


# ─── MLflow ───────────────────────────────────────────────────

@app.get("/mlflow/summary")
def get_mlflow_summary():
    return clean_json(mlflow_logger.get_experiment_summary())


@app.get("/mlflow/best")
def get_best_runs(metric: str = "eval_overall", top_k: int = 5):
    runs = mlflow_logger.get_best_runs(metric=metric, top_k=top_k)
    return {"metric": metric, "top_k": top_k, "runs": runs}


@app.post("/mlflow/log-memory-stats")
def log_memory_stats_to_mlflow():
    stats = memory_manager.get_memory_stats()
    run_id = mlflow_logger.log_memory_stats(stats)
    return {"run_id": run_id, "stats": stats}


# ─── Human-in-the-Loop ────────────────────────────────────────

@app.get("/hitl/pending")
def get_pending_approvals():
    requests_list = hitl_store.get_pending_requests()
    return {"count": len(requests_list), "requests": requests_list}


@app.get("/hitl/session/{session_id}")
def get_session_requests(session_id: str):
    requests_list = hitl_store.get_session_requests(session_id)
    return {"count": len(requests_list), "requests": requests_list}


@app.get("/hitl/{request_id}")
def get_hitl_request(request_id: str):
    req = hitl_store.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


@app.post("/hitl/{request_id}/approve")
def approve_request(request_id: str, feedback: str = ""):
    success = hitl_store.approve(request_id, feedback=feedback)
    if not success:
        raise HTTPException(status_code=404, detail="Request not found or already decided")
    return {"message": f"Request {request_id} approved", "feedback": feedback}


@app.post("/hitl/{request_id}/reject")
def reject_request(request_id: str, feedback: str = ""):
    success = hitl_store.reject(request_id, feedback=feedback)
    if not success:
        raise HTTPException(status_code=404, detail="Request not found or already decided")
    return {"message": f"Request {request_id} rejected", "feedback": feedback}


@app.delete("/hitl/session/{session_id}")
def clear_hitl_session(session_id: str):
    hitl_store.clear_session(session_id)
    return {"message": f"HITL requests cleared for session '{session_id}'"}