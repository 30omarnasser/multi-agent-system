import os
from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.planner import PlannerAgent
from agents.researcher import ResearcherAgent
from agents.coder import CoderAgent
from agents.critic import CriticAgent
from agents.responder import ResponderAgent

MAX_REVISIONS = 2
DEFAULT_MODEL = os.getenv("AGENT_MODEL", "llama3.1:8b")


def build_graph(model: str = DEFAULT_MODEL):

    planner = PlannerAgent(model=model)
    researcher = ResearcherAgent(model=model)
    coder = CoderAgent(model=model)
    critic = CriticAgent(model=model)
    responder = ResponderAgent(model=model)

    # ─── HITL Checkpoint Node ──────────────────────────────────
    # NOTE: node is named "hitl_check" (not "hitl_checkpoint") because
    # "hitl_checkpoint" is already a key in AgentState — LangGraph
    # forbids node names that clash with state keys.

    def hitl_check_node(state: AgentState) -> AgentState:
        """
        Pause the pipeline and wait for human approval.
        Only activates if hitl_enabled=True in state.
        """
        if not state.get("hitl_enabled", False):
            return state

        plan = state.get("plan", {})
        task_type = plan.get("task_type", "simple")
        complexity = plan.get("complexity", "low")

        # Only pause for high-risk operations
        should_pause = (
            task_type in ("code", "both")
            or complexity == "high"
            or plan.get("needs_code", False)
        )

        if not should_pause:
            print(f"[HITL] Low-risk task — skipping checkpoint")
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
            print(f"[HITL] Checkpoint failed: {e}")
            print(tb.format_exc())
            # Fail open — approve on error
            return {**state, "hitl_decision": "approved", "hitl_checkpoint": "error"}

    # ─── Episode Save Node ─────────────────────────────────────

    def save_episode_node(state: AgentState) -> AgentState:
        print(f"[Graph] save_episode_node | session: {state.get('session_id')}")
        try:
            from memory.episodic_memory import EpisodicMemory
            session_id = state.get("session_id", "default")
            if not session_id or session_id == "default":
                return state
            user_message = state.get("user_message", "")
            final_response = state.get("final_response", "")
            if not user_message or not final_response:
                return state
            messages = [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": final_response},
            ]
            episodic = EpisodicMemory()
            result = episodic.save_episode(
                session_id=session_id,
                messages=messages,
                model=model,
            )
            print(f"[Graph] ✓ Episode saved: id={result.get('id')}")
        except Exception as e:
            import traceback as tb
            print(f"[Graph] Episode save FAILED: {e}")
            print(tb.format_exc())
        return state

    # ─── Profile Update Node ───────────────────────────────────

    def update_profile_node(state: AgentState) -> AgentState:
        print(f"[Graph] update_profile_node | user: {state.get('user_id')}")
        try:
            from memory.user_profile import UserProfileMemory
            user_id = state.get("user_id") or state.get("session_id", "default")
            if not user_id or user_id == "default":
                return state
            user_message = state.get("user_message", "")
            final_response = state.get("final_response", "")
            if not user_message or not final_response:
                return state
            profile_memory = UserProfileMemory()
            profile_memory.auto_update_from_conversation(
                user_id=user_id,
                user_message=user_message,
                assistant_response=final_response,
                model=model,
            )
            print(f"[Graph] ✓ Profile updated for '{user_id}'")
        except Exception as e:
            import traceback as tb
            print(f"[Graph] Profile update FAILED: {e}")
            print(tb.format_exc())
        return state

    # ─── Router Functions ──────────────────────────────────────

    def route_after_planner(state: AgentState) -> str:
        plan = state.get("plan", {})
        task_type = plan.get("task_type", "simple")

        # Safety net: if planner mislabels a code/research request as "simple",
        # catch it via keywords so HITL and routing still work correctly.
        if task_type == "simple":
            msg = state.get("user_message", "").lower()
            code_keywords = [
                "write", "code", "script", "program", "function", "implement",
                "calculate", "compute", "execute", "run", "sort", "sum", "loop",
            ]
            research_keywords = [
                "search", "find", "latest", "current", "news", "price",
                "today", "recent", "what is", "who is", "how does",
            ]
            if any(w in msg for w in code_keywords):
                task_type = "code"
                plan["task_type"] = "code"
                plan["needs_code"] = True
            elif any(w in msg for w in research_keywords):
                task_type = "research"
                plan["task_type"] = "research"
                plan["needs_research"] = True

        # If HITL is enabled and task is non-trivial, gate through checkpoint
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
        else:
            return "responder"

    def route_after_hitl(state: AgentState) -> str:
        """After HITL checkpoint — proceed or abort."""
        decision = state.get("hitl_decision", "approved")
        plan = state.get("plan", {})
        task_type = plan.get("task_type", "simple")

        if decision == "rejected":
            print(f"[HITL] ❌ Rejected — routing to abort_responder")
            return "abort_responder"

        # Approved or timeout — proceed normally
        if task_type == "research":
            return "researcher"
        elif task_type == "code":
            return "coder"
        elif task_type == "both":
            return "researcher"
        else:
            return "responder"

    def route_after_researcher(state: AgentState) -> str:
        plan = state.get("plan", {})
        if plan.get("needs_code", False):
            return "coder"
        return "critic"

    def route_after_critic(state: AgentState) -> str:
        critique = state.get("critique", {})
        revision_count = state.get("revision_count", 0)
        if critique.get("approved", True) or revision_count >= MAX_REVISIONS:
            return "responder"
        else:
            plan = state.get("plan", {})
            if plan.get("needs_code"):
                return "coder"
            return "researcher"

    # ─── Abort Responder ──────────────────────────────────────

    def abort_responder_node(state: AgentState) -> AgentState:
        """Called when human rejects the plan."""
        feedback = state.get("hitl_feedback", "")
        message = (
            f"I've stopped this task as requested. "
            f"{('Reason: ' + feedback) if feedback else ''} "
            f"Please let me know how you'd like to proceed differently."
        )
        return {
            **state,
            "final_response": message,
            "current_agent": "abort",
        }

    # ─── Build Graph ───────────────────────────────────────────

    graph = StateGraph(AgentState)

    graph.add_node("planner",         planner.run)
    graph.add_node("hitl_check",      hitl_check_node)   # renamed from hitl_checkpoint
    graph.add_node("researcher",      researcher.run)
    graph.add_node("coder",           coder.run)
    graph.add_node("critic",          critic.run)
    graph.add_node("responder",       responder.run)
    graph.add_node("abort_responder", abort_responder_node)
    graph.add_node("save_episode",    save_episode_node)
    graph.add_node("update_profile",  update_profile_node)

    graph.set_entry_point("planner")

    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "hitl_check": "hitl_check",
            "researcher":  "researcher",
            "coder":       "coder",
            "responder":   "responder",
        },
    )

    graph.add_conditional_edges(
        "hitl_check",
        route_after_hitl,
        {
            "researcher":     "researcher",
            "coder":          "coder",
            "responder":      "responder",
            "abort_responder": "abort_responder",
        },
    )

    graph.add_conditional_edges(
        "researcher",
        route_after_researcher,
        {
            "coder":  "coder",
            "critic": "critic",
        },
    )

    graph.add_edge("coder", "critic")

    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "responder":  "responder",
            "researcher": "researcher",
            "coder":      "coder",
        },
    )

    graph.add_edge("responder",       "save_episode")
    graph.add_edge("abort_responder", "save_episode")
    graph.add_edge("save_episode",    "update_profile")
    graph.add_edge("update_profile",  END)

    return graph.compile()


# ─── Singleton ────────────────────────────────────────────────

_graph = None


def get_graph(model: str = DEFAULT_MODEL):
    global _graph
    if _graph is None:
        _graph = build_graph(model=model)
        print("[Graph] Multi-agent pipeline compiled ✅")
    return _graph


pipeline = get_graph()