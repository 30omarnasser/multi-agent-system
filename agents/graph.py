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
        """Auto-update user profile after each conversation."""
        print(f"[Graph] update_profile_node | user: {state.get('user_id')}")
        try:
            from memory.user_profile import UserProfileMemory

            user_id = state.get("user_id") or state.get("session_id", "default")
            if not user_id or user_id == "default":
                print("[Graph] Skipping profile update — no user_id")
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

    # ─── Build Graph ───────────────────────────────────────────

    graph = StateGraph(AgentState)

    graph.add_node("planner", planner.run)
    graph.add_node("researcher", researcher.run)
    graph.add_node("coder", coder.run)
    graph.add_node("critic", critic.run)
    graph.add_node("responder", responder.run)
    graph.add_node("save_episode", save_episode_node)
    graph.add_node("update_profile", update_profile_node)  # ← NEW

    graph.set_entry_point("planner")

    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "researcher": "researcher",
            "coder": "coder",
            "responder": "responder",
        },
    )

    graph.add_conditional_edges(
        "researcher",
        route_after_researcher,
        {
            "coder": "coder",
            "critic": "critic",
        },
    )

    graph.add_edge("coder", "critic")

    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "responder": "responder",
            "researcher": "researcher",
            "coder": "coder",
        },
    )

    # Responder → save episode → update profile → END
    graph.add_edge("responder", "save_episode")
    graph.add_edge("save_episode", "update_profile")  # ← NEW
    graph.add_edge("update_profile", END)              # ← NEW

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