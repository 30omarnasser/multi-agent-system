import os
from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.planner import PlannerAgent
from agents.researcher import ResearcherAgent
from agents.coder import CoderAgent
from agents.critic import CriticAgent
from agents.responder import ResponderAgent

MAX_REVISIONS = 2
DEFAULT_MODEL = os.getenv("AGENT_MODEL", "llama3.2")


def build_graph(model: str = DEFAULT_MODEL):
    """Build and compile the multi-agent LangGraph."""

    planner = PlannerAgent(model=model)
    researcher = ResearcherAgent(model=model)
    coder = CoderAgent(model=model)
    critic = CriticAgent(model=model)
    responder = ResponderAgent(model=model)

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

    graph.add_edge("responder", END)

    return graph.compile()


# ─── Singleton ────────────────────────────────────────────────

_graph = None


def get_graph(model: str = DEFAULT_MODEL):
    global _graph
    if _graph is None:
        _graph = build_graph(model=model)
        print("[Graph] Multi-agent pipeline compiled ✅")
    return _graph


# Direct import alias — used by api/main.py
pipeline = get_graph()