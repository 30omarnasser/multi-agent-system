import streamlit as st
import requests
import os
import uuid

API_URL = os.getenv("API_URL", "http://localhost:8000")


def get_or_create_session() -> tuple[str, str]:
    """Get or create session_id and user_id."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"session_{uuid.uuid4().hex[:8]}"
    if "user_id" not in st.session_state:
        st.session_state.user_id = f"user_{uuid.uuid4().hex[:8]}"
    return st.session_state.session_id, st.session_state.user_id


def render_chat_sidebar():
    """Render session controls in sidebar."""
    with st.sidebar:
        st.markdown("### 💬 Session")
        session_id, user_id = get_or_create_session()
        st.code(f"Session: {session_id}", language=None)
        st.code(f"User: {user_id}", language=None)

        if st.button("🔄 New Session", use_container_width=True):
            st.session_state.session_id = f"session_{uuid.uuid4().hex[:8]}"
            st.session_state.messages = []
            st.rerun()

        st.markdown("---")
        st.markdown("### ⚙️ Mode")
        mode = st.radio(
            "Agent mode",
            ["Multi-Agent Pipeline", "Single Agent"],
            index=0,
        )
        st.session_state.agent_mode = mode
        st.markdown("---")
    st.markdown("### 🛡️ Human-in-the-Loop")
    hitl_enabled = st.toggle(
        "Enable approval checkpoint",
        value=False,
        help="Agent will pause and ask for approval before executing high-risk tasks",
    )
    st.session_state.hitl_enabled = hitl_enabled
    if hitl_enabled:
        st.info("⏸️ Agent will pause before executing code or complex tasks")
        st.markdown("---")
        st.markdown("### 👤 Your Profile")
        try:
            r = requests.get(
                f"{API_URL}/profile/{user_id}",
                timeout=5
            )
            if r.status_code == 200:
                profile = r.json()
                if profile.get("name"):
                    st.markdown(f"**Name:** {profile['name']}")
                if profile.get("expertise_level") != "unknown":
                    st.markdown(f"**Expertise:** {profile['expertise_level']}")
                if profile.get("interests"):
                    st.markdown(f"**Interests:** {', '.join(profile['interests'][:3])}")
                st.markdown(f"**Interactions:** {profile.get('interaction_count', 0)}")
        except Exception:
            st.markdown("*Profile loading...*")


def render_message(role: str, content: str, metadata: dict = None):
    """Render a single chat message."""
    with st.chat_message(role):
        st.markdown(content)
        if metadata and role == "assistant":
            agents = metadata.get("agents_used", [])
            score = metadata.get("critique_score", 0)
            if agents:
                from ui.components.pipeline import (
                    render_pipeline_flow,
                    render_plan_details,
                )
                render_pipeline_flow(
                    agents_used=agents,
                    critique_score=score,
                    had_revision=metadata.get("had_revision", False),
                )
                render_plan_details(metadata.get("plan", {}))


def send_message(message: str, session_id: str, user_id: str) -> dict:
    mode = st.session_state.get("agent_mode", "Multi-Agent Pipeline")
    hitl_enabled = st.session_state.get("hitl_enabled", False)

    if mode == "Multi-Agent Pipeline":
        r = requests.post(
            f"{API_URL}/multi-agent",
            json={
                "message": message,
                "session_id": session_id,
                "user_id": user_id,
                "hitl_enabled": hitl_enabled,
            },
            timeout=180,  # longer timeout for HITL
        )
    else:
        r = requests.post(
            f"{API_URL}/chat",
            json={"message": message, "session_id": session_id},
            timeout=60,
        )

    if r.status_code == 200:
        return r.json()
    else:
        raise Exception(f"API error {r.status_code}: {r.text[:200]}")


def render_chat_interface():
    """Main chat interface."""
    session_id, user_id = get_or_create_session()

    # Initialize message history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display existing messages
    for msg in st.session_state.messages:
        render_message(
            role=msg["role"],
            content=msg["content"],
            metadata=msg.get("metadata"),
        )
def render_hitl_approval_panel():
    """Show pending HITL requests and approval buttons."""
    try:
        r = requests.get(f"{API_URL}/hitl/pending", timeout=5)
        if r.status_code != 200:
            return
        data = r.json()
        if data["count"] == 0:
            return

        st.markdown("---")
        st.markdown("### ⏸️ Awaiting Your Approval")

        for req in data["requests"]:
            with st.container():
                risk_color = {
                    "high": "🔴",
                    "medium": "🟡",
                    "low": "🟢",
                }.get(req.get("risk_level", "medium"), "🟡")

                st.markdown(
                    f"{risk_color} **{req['action']}** "
                    f"(Session: `{req['session_id']}`)"
                )

                details = req.get("details", {})
                if details.get("user_message"):
                    st.caption(f"Task: {details['user_message'][:100]}")
                if details.get("search_queries"):
                    st.caption(f"Will search: {details['search_queries']}")
                if details.get("code_requirements"):
                    st.caption(f"Will code: {details['code_requirements']}")

                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    feedback = st.text_input(
                        "Feedback (optional)",
                        key=f"feedback_{req['request_id']}",
                        placeholder="Add guidance or reason...",
                    )
                with col2:
                    if st.button(
                        "✅ Approve",
                        key=f"approve_{req['request_id']}",
                        use_container_width=True,
                        type="primary",
                    ):
                        requests.post(
                            f"{API_URL}/hitl/{req['request_id']}/approve",
                            params={"feedback": feedback},
                            timeout=5,
                        )
                        st.success("Approved!")
                        st.rerun()
                with col3:
                    if st.button(
                        "❌ Reject",
                        key=f"reject_{req['request_id']}",
                        use_container_width=True,
                    ):
                        requests.post(
                            f"{API_URL}/hitl/{req['request_id']}/reject",
                            params={"feedback": feedback},
                            timeout=5,
                        )
                        st.error("Rejected!")
                        st.rerun()

    except Exception:
        pass       

    # Chat input
    if prompt := st.chat_input("Ask anything..."):
        # Show user message immediately
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
        })
        render_message("user", prompt)

        # Show thinking indicator
        with st.chat_message("assistant"):
            mode = st.session_state.get("agent_mode", "Multi-Agent Pipeline")
            if mode == "Multi-Agent Pipeline":
                with st.status("🤖 Running multi-agent pipeline...", expanded=True) as status:
                    st.write("🗺️ Planner analyzing task...")
                    try:
                        response_data = send_message(prompt, session_id, user_id)
                        agents = response_data.get("agents_used", [])
                        for agent in agents[1:]:
                            from ui.components.pipeline import AGENT_ICONS
                            icon = AGENT_ICONS.get(agent, "🤖")
                            st.write(f"{icon} {agent.capitalize()} running...")
                        status.update(label="✅ Pipeline complete!", state="complete")
                    except Exception as e:
                        status.update(label=f"❌ Error: {e}", state="error")
                        response_data = {"response": f"Error: {e}", "agents_used": []}

                st.markdown(response_data.get("response", ""))

                if response_data.get("agents_used"):
                    from ui.components.pipeline import (
                        render_pipeline_flow,
                        render_plan_details,
                    )
                    render_pipeline_flow(
                        agents_used=response_data.get("agents_used", []),
                        critique_score=response_data.get("critique_score", 0),
                        had_revision=response_data.get("had_revision", False),
                    )
                    render_plan_details(response_data.get("plan", {}))
            else:
                with st.spinner("Thinking..."):
                    try:
                        response_data = send_message(prompt, session_id, user_id)
                    except Exception as e:
                        response_data = {"response": f"Error: {e}"}
                st.markdown(response_data.get("response", ""))

        # Save to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_data.get("response", ""),
            "metadata": response_data,
        })
# Show HITL approval panel if there are pending requests
render_hitl_approval_panel()        