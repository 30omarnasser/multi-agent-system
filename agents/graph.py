import os
from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.planner import PlannerAgent
from agents.researcher import ResearcherAgent
from agents.coder import CoderAgent
from agents.critic import CriticAgent
from agents.responder import ResponderAgent

MAX_REVISIONS = 2  # prevent infinite critique loops


def build_graph(model: str = "llama3.1:8b"):
    """Build and compile the multi-agent LangGraph."""

    # Initialize all agents
    planner = PlannerAgent(model=model)
    researcher = ResearcherAgent(model=model)
    coder = CoderAgent(model=model)
    critic = CriticAgent(model=model)
    responder = ResponderAgent(model=model)

    # ─── Router Functions ──────────────────────────────────────

    def route_after_planner(state: AgentState) -> str:
        """Decide which agent runs after planner based on task type."""
        plan = state.get("plan", {})
        task_type = plan.get("task_type", "simple")

        if task_type == "simple":
            return "responder"
        elif task_type == "research":
            return "researcher"
        elif task_type == "code":
            return "coder"
        elif task_type == "both":
            return "researcher"  # researcher runs first, then coder
        else:
            return "responder"

    def route_after_researcher(state: AgentState) -> str:
        """After research, go to coder if needed, else critic."""
        plan = state.get("plan", {})
        if plan.get("needs_code", False):
            return "coder"
        return "critic"

    def route_after_critic(state: AgentState) -> str:
        """Approve → responder. Reject → retry (up to MAX_REVISIONS)."""
        critique = state.get("critique", {})
        revision_count = state.get("revision_count", 0)

        if critique.get("approved", True) or revision_count >= MAX_REVISIONS:
            return "responder"
        else:
            # Send back for revision
            plan = state.get("plan", {})
            if plan.get("needs_code"):
                return "coder"
            return "researcher"

    # ─── Build Graph ───────────────────────────────────────────

    graph = StateGraph(AgentState)

    # Add all agent nodes
    graph.add_node("planner", planner.run)
    graph.add_node("researcher", researcher.run)
    graph.add_node("coder", coder.run)
    graph.add_node("critic", critic.run)
    graph.add_node("responder", responder.run)

    # Entry point
    graph.set_entry_point("planner")

    # Conditional routing after planner
    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "researcher": "researcher",
            "coder": "coder",
            "responder": "responder",
        },
    )

    # After researcher — go to coder or critic
    graph.add_conditional_edges(
        "researcher",
        route_after_researcher,
        {
            "coder": "coder",
            "critic": "critic",
        },
    )

    # Coder always goes to critic
    graph.add_edge("coder", "critic")

    # Critic routes to responder or back for revision
    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "responder": "responder",
            "researcher": "researcher",
            "coder": "coder",
        },
    )

    # Responder is always the end
    graph.add_edge("responder", END)

    return graph.compile()


# Singleton — built once at startup
_graph = None

def get_graph(model: str = "llama3.1:8b"):
    global _graph
    if _graph is None:
        _graph = build_graph(model=model)
        print("[Graph] Multi-agent graph compiled.")
    return _graph