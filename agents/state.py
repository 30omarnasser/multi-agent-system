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
    critique: dict

    # Revision cycle count
    revision_count: int

    # Final response
    final_response: str

    # Active agent name
    current_agent: str

    # Session / user info
    session_id: str
    user_id: str

    # Planner hints
    search_queries: list
    code_requirements: list

    # RAG context
    doc_context: str

    # Memory contexts injected at start
    episode_context: str
    profile_context: str
    trace_id: str

    # ── Human-in-the-loop ─────────────────────────────────────
    hitl_enabled: bool       # Whether HITL is on for this run
    hitl_request_id: str     # Current pending request ID
    hitl_decision: str       # 'approved', 'rejected', 'timeout', ''
    hitl_feedback: str       # Human's feedback/reason
    hitl_checkpoint: str     # Which checkpoint triggered HITL