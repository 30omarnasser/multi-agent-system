import os
import time
from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.planner import PlannerAgent
from agents.researcher import ResearcherAgent
from agents.coder import CoderAgent
from agents.critic import CriticAgent
from agents.responder import ResponderAgent
from memory.trace_store import TraceStore

MAX_REVISIONS = 2
DEFAULT_MODEL = os.getenv("AGENT_MODEL", "llama3.1:8b")

# Keywords used to fix planner mislabelling
_CODE_KEYWORDS = [
    "write", "code", "script", "program", "function", "implement",
    "calculate", "compute", "execute", "run", "sort", "sum", "loop",
]
_RESEARCH_KEYWORDS = [
    "search", "find", "latest", "current", "news", "price",
    "today", "recent", "what is", "who is", "how does",
]


def build_traced_graph(model: str = DEFAULT_MODEL):
    """Build graph with full execution tracing AND HITL checkpoints.
    This is the graph used by main.py via traced_pipeline.
    """

    planner = PlannerAgent(model=model)
    researcher = ResearcherAgent(model=model)
    coder = CoderAgent(model=model)
    critic = CriticAgent(model=model)
    responder = ResponderAgent(model=model)
    trace_store = TraceStore()

    # ─── Traced Agent Wrappers ─────────────────────────────────

    def make_traced(agent_name: str, agent_fn, step_index: int):
        """Wrap an agent's run() with timing and span logging."""
        def traced_run(state: AgentState) -> AgentState:
            trace_id = state.get("trace_id", "")
            start = time.time()
            input_summary = _summarize_input(agent_name, state)
            print(f"\n[Trace] ▶ {agent_name} starting (trace: {trace_id[:16]})")

            status = "success"
            new_state = state
            try:
                new_state = agent_fn(state)
                duration_ms = int((time.time() - start) * 1000)
                output_summary = _summarize_output(agent_name, new_state)
            except Exception as e:
                duration_ms = int((time.time() - start) * 1000)
                output_summary = f"ERROR: {str(e)[:200]}"
                status = "error"
                raise
            finally:
                if trace_id:
                    try:
                        trace_store.add_span(
                            trace_id=trace_id,
                            agent_name=agent_name,
                            step_index=step_index,
                            duration_ms=duration_ms,
                            input_summary=input_summary,
                            output_summary=output_summary,
                            status=status,
                            details=_get_details(agent_name, state, new_state),
                        )
                    except Exception as te:
                        print(f"[Trace] Span save failed: {te}")

            print(f"[Trace] ✓ {agent_name} done in {duration_ms}ms")
            return new_state

        return traced_run

    # ─── HITL Checkpoint Node ──────────────────────────────────

    def hitl_check_node(state: AgentState) -> AgentState:
        """
        Pause pipeline and wait for human approval.
        Only runs if hitl_enabled=True.
        Node is named 'hitl_check' (not 'hitl_checkpoint') to avoid
        clashing with the 'hitl_checkpoint' key in AgentState.
        """
        if not state.get("hitl_enabled", False):
            return state

        plan = state.get("plan", {})
        task_type = plan.get("task_type", "simple")
        complexity = plan.get("complexity", "low")

        should_pause = (
            task_type in ("code", "both")
            or complexity == "high"
            or plan.get("needs_code", False)
        )

        if not should_pause:
            print("[HITL] Low-risk task — skipping checkpoint")
            return {**state, "hitl_decision": "approved", "hitl_checkpoint": "skipped"}

        try:
            from memory.hitl_store import HITLStore
            hitl_store = HITLStore()

            session_id = state.get("session_id", "default")
            risk_level = "high" if task_type == "code" else "medium"

            request_id = hitl_store.create_request(
                session_id=session_id,
                agent="pipeline",
                action=f"Execute {task_type} pipeline",
                details={
                    "task_type": task_type,
                    "complexity": complexity,
                    "needs_research": plan.get("needs_research", False),
                    "needs_code": plan.get("needs_code", False),
                    "search_queries": plan.get("search_queries", []),
                    "code_requirements": plan.get("code_requirements", []),
                    "user_message": state.get("user_message", "")[:200],
                },
                risk_level=risk_level,
            )

            print(f"[HITL] ⏸️  Waiting for approval: {request_id}")
            decision = hitl_store.wait_for_decision(
                request_id=request_id,
                timeout_seconds=120,
            )
            print(f"[HITL] Decision: {decision}")

            request = hitl_store.get_request(request_id)
            feedback = request.get("feedback", "") if request else ""

            return {
                **state,
                "hitl_request_id": request_id,
                "hitl_decision": decision,
                "hitl_feedback": feedback,
                "hitl_checkpoint": "pre_execution",
            }

        except Exception as e:
            import traceback as tb
            print(f"[HITL] Checkpoint failed: {e}\n{tb.format_exc()}")
            # Fail open — approve on error
            return {**state, "hitl_decision": "approved", "hitl_checkpoint": "error"}

    # ─── Abort Responder Node ──────────────────────────────────

    def abort_responder_node(state: AgentState) -> AgentState:
        """Called when human rejects the plan."""
        feedback = state.get("hitl_feedback", "")
        message = (
            "I've stopped this task as requested. "
            + (f"Reason: {feedback} " if feedback else "")
            + "Please let me know how you'd like to proceed differently."
        )
        return {**state, "final_response": message, "current_agent": "abort"}

    # ─── Episode Save Node ─────────────────────────────────────

    def save_episode_node(state: AgentState) -> AgentState:
        try:
            from memory.episodic_memory import EpisodicMemory
            from memory.redis_memory import RedisMemory

            session_id = state.get("session_id", "default")
            if not session_id or session_id == "default":
                return state

            redis_memory = RedisMemory()
            messages = redis_memory.get_history(session_id)

            if len(messages) >= 2:
                episodic = EpisodicMemory()
                episodic.save_episode(
                    session_id=session_id,
                    messages=messages,
                    model=model,
                )
                print(f"[Graph] ✓ Episode saved for '{session_id}'")
        except Exception as e:
            print(f"[Graph] Episode save failed (non-critical): {e}")
        return state

    # ─── Router Functions ──────────────────────────────────────

    def _resolve_task_type(state: AgentState) -> str:
        """
        Get task_type from plan, with keyword fallback if planner
        mislabels a code/research request as 'simple'.
        Also mutates plan in-state so downstream agents see the fix.
        """
        plan = state.get("plan", {})
        task_type = plan.get("task_type", "simple")

        if task_type == "simple":
            msg = state.get("user_message", "").lower()
            if any(w in msg for w in _CODE_KEYWORDS):
                task_type = "code"
                plan["task_type"] = "code"
                plan["needs_code"] = True
                print(f"[Router] Planner said 'simple' but message has code keywords → overriding to 'code'")
            elif any(w in msg for w in _RESEARCH_KEYWORDS):
                task_type = "research"
                plan["task_type"] = "research"
                plan["needs_research"] = True
                print(f"[Router] Planner said 'simple' but message has research keywords → overriding to 'research'")

        return task_type

    def route_after_planner(state: AgentState) -> str:
        task_type = _resolve_task_type(state)

        # Gate non-trivial tasks through HITL if enabled
        if state.get("hitl_enabled", False) and task_type != "simple":
            return "hitl_check"

        if task_type == "simple":
            return "responder"
        elif task_type == "research":
            return "researcher"
        elif task_type == "code":
            return "coder"
        elif task_type == "both":
            return "researcher"
        return "responder"

    def route_after_hitl(state: AgentState) -> str:
        """After HITL checkpoint — proceed or abort."""
        decision = state.get("hitl_decision", "approved")
        plan = state.get("plan", {})
        task_type = plan.get("task_type", "simple")

        if decision == "rejected":
            print("[HITL] ❌ Rejected — routing to abort_responder")
            return "abort_responder"

        # Approved or timeout — proceed normally
        if task_type == "research":
            return "researcher"
        elif task_type == "code":
            return "coder"
        elif task_type == "both":
            return "researcher"
        return "responder"

    def route_after_researcher(state: AgentState) -> str:
        plan = state.get("plan", {})
        return "coder" if plan.get("needs_code", False) else "critic"

    def route_after_critic(state: AgentState) -> str:
        critique = state.get("critique", {})
        revision_count = state.get("revision_count", 0)
        if critique.get("approved", True) or revision_count >= MAX_REVISIONS:
            return "responder"
        plan = state.get("plan", {})
        return "coder" if plan.get("needs_code") else "researcher"

    # ─── Build Graph ───────────────────────────────────────────

    graph = StateGraph(AgentState)

    graph.add_node("planner",         make_traced("planner",    planner.run,    0))
    graph.add_node("hitl_check",      hitl_check_node)
    graph.add_node("researcher",      make_traced("researcher", researcher.run, 1))
    graph.add_node("coder",           make_traced("coder",      coder.run,      2))
    graph.add_node("critic",          make_traced("critic",     critic.run,     3))
    graph.add_node("responder",       make_traced("responder",  responder.run,  4))
    graph.add_node("abort_responder", abort_responder_node)
    graph.add_node("save_episode",    save_episode_node)

    graph.set_entry_point("planner")

    graph.add_conditional_edges(
        "planner", route_after_planner,
        {
            "hitl_check": "hitl_check",
            "researcher": "researcher",
            "coder":      "coder",
            "responder":  "responder",
        },
    )
    graph.add_conditional_edges(
        "hitl_check", route_after_hitl,
        {
            "researcher":      "researcher",
            "coder":           "coder",
            "responder":       "responder",
            "abort_responder": "abort_responder",
        },
    )
    graph.add_conditional_edges(
        "researcher", route_after_researcher,
        {"coder": "coder", "critic": "critic"},
    )
    graph.add_edge("coder", "critic")
    graph.add_conditional_edges(
        "critic", route_after_critic,
        {"responder": "responder", "researcher": "researcher", "coder": "coder"},
    )
    graph.add_edge("responder",       "save_episode")
    graph.add_edge("abort_responder", "save_episode")
    graph.add_edge("save_episode",    END)

    return graph.compile()


# ─── Input/Output Summarizers ─────────────────────────────────

def _summarize_input(agent_name: str, state: AgentState) -> str:
    msg = state.get("user_message", "")[:100]
    if agent_name == "planner":
        return f"User: {msg}"
    elif agent_name == "researcher":
        queries = state.get("search_queries", [])
        return f"Queries: {queries[:2]} | User: {msg[:60]}"
    elif agent_name == "coder":
        reqs = state.get("code_requirements", [])
        return f"Requirements: {reqs[:2]} | Research: {state.get('research', '')[:80]}"
    elif agent_name == "critic":
        research_len = len(state.get("research", ""))
        code_len = len(state.get("code_output", ""))
        return f"Research: {research_len} chars | Code: {code_len} chars"
    elif agent_name == "responder":
        return f"Research: {len(state.get('research',''))}c | Code: {len(state.get('code_output',''))}c"
    return f"User: {msg}"


def _summarize_output(agent_name: str, state: AgentState) -> str:
    if agent_name == "planner":
        plan = state.get("plan", {})
        return (
            f"task_type={plan.get('task_type')} | "
            f"complexity={plan.get('complexity')} | "
            f"confidence={plan.get('confidence', 0):.0%}"
        )
    elif agent_name == "researcher":
        return f"Summary: {state.get('research', '')[:150]}"
    elif agent_name == "coder":
        return f"Output: {state.get('code_output', '')[:150]}"
    elif agent_name == "critic":
        critique = state.get("critique", {})
        return (
            f"Score: {critique.get('score')}/10 | "
            f"Approved: {critique.get('approved')} | "
            f"Feedback: {critique.get('feedback', '')[:80]}"
        )
    elif agent_name == "responder":
        response = state.get("final_response", "")
        return f"Response ({len(response)} chars): {response[:150]}"
    return ""


def _get_details(agent_name: str, input_state: AgentState, output_state: AgentState) -> dict:
    details = {"agent": agent_name}
    if agent_name == "planner":
        details["plan"] = output_state.get("plan", {})
    elif agent_name == "researcher":
        details["search_queries"] = input_state.get("search_queries", [])
        details["research_length"] = len(output_state.get("research", ""))
    elif agent_name == "coder":
        details["code_requirements"] = input_state.get("code_requirements", [])
    elif agent_name == "critic":
        details["critique"] = output_state.get("critique", {})
        details["revision_count"] = output_state.get("revision_count", 0)
    elif agent_name == "responder":
        details["response_length"] = len(output_state.get("final_response", ""))
    return details


# ─── Singleton ────────────────────────────────────────────────

_traced_graph = None


def get_traced_graph(model: str = DEFAULT_MODEL):
    global _traced_graph
    if _traced_graph is None:
        _traced_graph = build_traced_graph(model=model)
        print("[TracedGraph] Compiled ✅")
    return _traced_graph


traced_pipeline = get_traced_graph()