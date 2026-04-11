import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

AGENT_COLORS = {
    "planner":    "#3B82F6",
    "researcher": "#10B981",
    "coder":      "#F59E0B",
    "critic":     "#EF4444",
    "responder":  "#8B5CF6",
}

AGENT_ICONS = {
    "planner":    "🗺️",
    "researcher": "🔍",
    "coder":      "💻",
    "critic":     "⚖️",
    "responder":  "✍️",
}


def render_trace_viewer():
    """Full agent trace viewer panel."""
    st.markdown("## 🔍 Agent Trace Viewer")

    tab1, tab2 = st.tabs(["📋 Recent Traces", "📊 Performance Stats"])

    # ── Recent Traces ─────────────────────────────────────────
    with tab1:
        col1, col2 = st.columns([3, 1])
        with col1:
            session_filter = st.text_input(
                "Filter by session ID",
                placeholder="Leave empty to show all",
                key="trace_session_filter",
            )
        with col2:
            limit = st.slider("Max traces", 5, 50, 20, key="trace_limit")

        if st.button("🔄 Refresh Traces", key="refresh_traces"):
            st.cache_data.clear()

        try:
            params = {"limit": limit}
            if session_filter:
                params["session_id"] = session_filter

            r = requests.get(f"{API_URL}/traces", params=params, timeout=10)
            if r.status_code != 200:
                st.error(f"Failed to load traces: {r.text}")
                return

            data = r.json()
            traces = data["traces"]

            if not traces:
                st.info("No traces yet. Run a multi-agent pipeline request to see traces here.")
                return

            st.markdown(f"**{len(traces)} traces**")

            for trace in traces:
                _render_trace_card(trace)

        except Exception as e:
            st.error(f"Error loading traces: {e}")

    # ── Performance Stats ─────────────────────────────────────
    with tab2:
        st.markdown("### Pipeline Performance Stats")

        if st.button("🔄 Refresh Stats", key="refresh_trace_stats"):
            st.cache_data.clear()

        try:
            r = requests.get(f"{API_URL}/traces/stats", timeout=10)
            if r.status_code != 200:
                st.error("Could not load stats")
                return

            stats = r.json()

            # Top metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Runs", stats.get("total_traces", 0))
            with col2:
                avg_ms = stats.get("avg_duration_ms") or 0
                st.metric("Avg Duration", f"{int(avg_ms / 1000)}s")
            with col3:
                avg_score = stats.get("avg_score") or 0
                st.metric("Avg Critique Score", f"{avg_score:.1f}/10")
            with col4:
                errors = stats.get("error_count", 0)
                st.metric("Errors", errors)

            st.markdown("---")

            col1, col2 = st.columns(2)

            # Task type breakdown
            with col1:
                st.markdown("### Task Type Distribution")
                task_types = stats.get("by_task_type", {})
                if task_types:
                    for task_type, count in task_types.items():
                        total = stats.get("total_traces", 1)
                        pct = count / total * 100
                        color = {
                            "simple": "🟢",
                            "research": "🔵",
                            "code": "🟡",
                            "both": "🟣",
                        }.get(task_type, "⚪")
                        st.markdown(f"{color} **{task_type}**: {count} ({pct:.0f}%)")
                        st.progress(pct / 100)

            # Agent performance
            with col2:
                st.markdown("### Agent Performance")
                agent_perf = stats.get("agent_performance", [])
                if agent_perf:
                    for ap in agent_perf:
                        name = ap["agent_name"]
                        avg_ms = int(ap["avg_ms"] or 0)
                        calls = ap["calls"]
                        color = AGENT_COLORS.get(name, "#6B7280")
                        icon = AGENT_ICONS.get(name, "🤖")
                        st.markdown(
                            f"""<div style="
                                background: {color}22;
                                border-left: 4px solid {color};
                                padding: 8px 12px;
                                border-radius: 6px;
                                margin: 6px 0;
                            ">
                                {icon} <strong>{name}</strong>
                                &nbsp;|&nbsp; avg: <strong>{avg_ms}ms</strong>
                                &nbsp;|&nbsp; calls: <strong>{calls}</strong>
                            </div>""",
                            unsafe_allow_html=True,
                        )

            st.markdown("---")
            st.markdown("### 🧹 Cleanup")
            col1, col2 = st.columns(2)
            with col1:
                days = st.slider("Delete traces older than (days)", 1, 30, 7)
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ Clear Old Traces", use_container_width=True):
                    r2 = requests.delete(
                        f"{API_URL}/traces",
                        params={"days_old": days},
                        timeout=10,
                    )
                    if r2.status_code == 200:
                        st.success(f"Deleted {r2.json()['deleted']} traces")
                        st.rerun()

        except Exception as e:
            st.error(f"Error loading stats: {e}")


def _render_trace_card(trace: dict):
    """Render a single trace as an expandable card."""
    trace_id = trace["trace_id"]
    agents = trace.get("agents_used") or []
    score = trace.get("critique_score", 0)
    duration_s = (trace.get("total_duration_ms") or 0) / 1000
    status = trace.get("status", "unknown")
    task_type = trace.get("task_type", "simple")
    created = str(trace.get("created_at", ""))[:19]

    # Status icon
    status_icon = "✅" if status == "success" else "❌" if status == "error" else "⏳"

    # Score color
    score_icon = "🟢" if score >= 8 else "🟡" if score >= 6 else "🔴" if score > 0 else "⚪"

    header = (
        f"{status_icon} `{trace_id[:20]}` | "
        f"**{task_type}** | "
        f"{score_icon} {score}/10 | "
        f"⏱️ {duration_s:.1f}s | "
        f"📅 {created}"
    )

    with st.expander(header, expanded=False):
        # User message
        st.markdown(f"**User:** {trace['user_message'][:200]}")

        # Agent flow visualization
        if agents:
            st.markdown("**Agent Flow:**")
            flow_cols = st.columns(len(agents))
            for i, agent in enumerate(agents):
                with flow_cols[i]:
                    color = AGENT_COLORS.get(agent, "#6B7280")
                    icon = AGENT_ICONS.get(agent, "🤖")
                    st.markdown(
                        f"""<div style="
                            background: {color}22;
                            border: 2px solid {color};
                            border-radius: 8px;
                            padding: 6px;
                            text-align: center;
                            font-size: 0.75rem;
                        ">
                            {icon}<br>
                            <strong style="color:{color}">{agent}</strong>
                        </div>""",
                        unsafe_allow_html=True,
                    )

        st.markdown("---")

        # Load full spans
        if st.button(f"📊 Load Spans", key=f"spans_{trace_id}"):
            try:
                r = requests.get(
                    f"{API_URL}/traces/{trace_id}",
                    timeout=10,
                )
                if r.status_code == 200:
                    full_trace = r.json()
                    spans = full_trace.get("spans", [])
                    if spans:
                        st.markdown("**Execution Spans:**")
                        for span in spans:
                            _render_span(span)
                    else:
                        st.info("No spans recorded for this trace.")
            except Exception as e:
                st.error(f"Could not load spans: {e}")

        # Final response preview
        if trace.get("final_response"):
            with st.expander("📝 Final Response", expanded=False):
                st.markdown(trace["final_response"][:500])


def _render_span(span: dict):
    """Render a single agent span."""
    agent = span["agent_name"]
    color = AGENT_COLORS.get(agent, "#6B7280")
    icon = AGENT_ICONS.get(agent, "🤖")
    duration = span.get("duration_ms", 0)
    status = span.get("status", "success")
    status_icon = "✅" if status == "success" else "❌"

    st.markdown(
        f"""<div style="
            border-left: 4px solid {color};
            padding: 10px 16px;
            margin: 8px 0;
            background: {color}11;
            border-radius: 0 8px 8px 0;
        ">
            <strong>{status_icon} {icon} {agent.upper()}</strong>
            &nbsp;&nbsp; ⏱️ <code>{duration}ms</code>
            <br>
            <small style="color:#9CA3AF">
                <strong>IN:</strong> {span.get('input_summary', '')[:120]}
            </small>
            <br>
            <small style="color:#D1D5DB">
                <strong>OUT:</strong> {span.get('output_summary', '')[:120]}
            </small>
        </div>""",
        unsafe_allow_html=True,
    )