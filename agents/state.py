from typing import TypedDict


class AgentState(TypedDict):
    # Original user request
    user_message: str

    # Planner output
    plan: dict

    # Research results
    research: str

    # Code written + executed
    code_output: str

    # Critic evaluation
    critique: dict  # {score, feedback, approved, issues}

    # Revision cycle count
    revision_count: int

    # Final response
    final_response: str

    # Active agent name
    current_agent: str

    # Session info
    session_id: str

    # Planner hints for downstream agents
    search_queries: list
    code_requirements: list

    # RAG context from documents
    doc_context: str

    # Episodic memory context injected at start
    episode_context: str