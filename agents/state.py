from typing import TypedDict, Annotated, Any
from langgraph.graph.message import add_messages

from typing import TypedDict

class AgentState(TypedDict):
    """
    Shared state passed between all agents in the graph.
    Every agent reads from and writes to this state.
    """
    # Original user request
    user_message: str

    # Planner output — structured task breakdown
    plan: dict

    # Research results from Researcher agent
    research: str

    # Code written + executed by Coder agent
    code_output: str

    # Critic's evaluation and decision
    critique: dict  # {"score": int, "feedback": str, "approved": bool}

    # Number of revision cycles (prevents infinite loops)
    revision_count: int

    # Final response to the user
    final_response: str

    # Which agent is currently active
    current_agent: str

    # Session info
    session_id: str


class AgentState(TypedDict):
    # Original user request
    user_message: str

    # Planner output — structured task breakdown
    plan: dict

    # Research results from Researcher agent
    research: str

    # Code written + executed by Coder agent
    code_output: str

    # Critic's evaluation and decision
    critique: dict  # {"score": int, "feedback": str, "approved": bool, "issues": list}

    # Number of revision cycles (prevents infinite loops)
    revision_count: int

    # Final response to the user
    final_response: str

    # Which agent is currently active
    current_agent: str

    # Session info
    session_id: str

    # Planner metadata — used by downstream agents
    search_queries: list      # exact queries for Researcher
    code_requirements: list   # exact requirements for Coder
    
    doc_context: str 