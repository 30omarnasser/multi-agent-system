import streamlit as st


AGENT_COLORS = {
    "planner": "#3B82F6",
    "researcher": "#10B981",
    "coder": "#F59E0B",
    "critic": "#EF4444",
    "responder": "#8B5CF6",
}

AGENT_ICONS = {
    "planner": "🗺️",
    "researcher": "🔍",
    "coder": "💻",
    "critic": "⚖️",
    "responder": "✍️",
}

AGENT_DESCRIPTIONS = {
    "planner": "Analyzed task and created execution plan",
    "researcher": "Searched web and knowledge base",
    "coder": "Wrote and executed Python code",
    "critic": "Evaluated output quality",
    "responder": "Synthesized final response",
}


def render_pipeline_flow(agents_used: list[str], critique_score: int, had_revision: bool):
    """Render the agent pipeline as a visual flow."""
    st.markdown("### 🤖 Agent Pipeline")

    cols = st.columns(len(agents_used))
    for i, agent in enumerate(agents_used):
        with cols[i]:
            color = AGENT_COLORS.get(agent, "#6B7280")
            icon = AGENT_ICONS.get(agent, "🤖")
            desc = AGENT_DESCRIPTIONS.get(agent, "")
            st.markdown(
                f"""
                <div style="
                    background: {color}22;
                    border: 2px solid {color};
                    border-radius: 12px;
                    padding: 12px 8px;
                    text-align: center;
                    margin: 4px;
                ">
                    <div style="font-size: 1.5rem">{icon}</div>
                    <div style="font-weight: 700; color: {color}; font-size: 0.85rem; margin: 4px 0;">
                        {agent.upper()}
                    </div>
                    <div style="font-size: 0.7rem; color: #6B7280;">
                        {desc}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if i < len(agents_used) - 1:
                pass  # arrow handled by layout

    # Metadata row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Agents Used", len(agents_used))
    with col2:
        score_color = "🟢" if critique_score >= 8 else "🟡" if critique_score >= 6 else "🔴"
        st.metric("Critique Score", f"{score_color} {critique_score}/10")
    with col3:
        st.metric("Had Revision", "Yes ♻️" if had_revision else "No ✅")


def render_plan_details(plan: dict):
    """Render the planner's task breakdown."""
    if not plan:
        return

    with st.expander("📋 Task Plan Details", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Task Type:** `{plan.get('task_type', 'unknown')}`")
            st.markdown(f"**Complexity:** `{plan.get('complexity', 'unknown')}`")
            st.markdown(f"**Confidence:** `{plan.get('confidence', 0):.0%}`")
        with col2:
            st.markdown(f"**Needs Research:** {'✅' if plan.get('needs_research') else '❌'}")
            st.markdown(f"**Needs Code:** {'✅' if plan.get('needs_code') else '❌'}")
            st.markdown(f"**Estimated Steps:** `{plan.get('estimated_steps', 1)}`")

        if plan.get("search_queries"):
            st.markdown("**Search Queries:**")
            for q in plan["search_queries"]:
                st.markdown(f"  - `{q}`")

        if plan.get("code_requirements"):
            st.markdown("**Code Requirements:**")
            for r in plan["code_requirements"]:
                st.markdown(f"  - {r}")

        if plan.get("subtasks"):
            st.markdown("**Subtasks:**")
            for s in plan["subtasks"]:
                if isinstance(s, dict):
                    agent = s.get("agent", "?")
                    icon = AGENT_ICONS.get(agent, "🤖")
                    st.markdown(
                        f"  {s.get('step', '?')}. {icon} `[{agent}]` {s.get('description', '')}"
                    )