import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

SCORE_COLORS = {
    range(0, 5):  ("#EF4444", "🔴"),
    range(5, 7):  ("#F59E0B", "🟡"),
    range(7, 9):  ("#10B981", "🟢"),
    range(9, 11): ("#3B82F6", "🔵"),
}


def _score_color(score: int) -> tuple[str, str]:
    for r, (color, icon) in SCORE_COLORS.items():
        if score in r:
            return color, icon
    return "#6B7280", "⚪"


def render_score_bar(label: str, score: int, max_score: int = 10):
    color, icon = _score_color(score)
    pct = score / max_score
    st.markdown(
        f"""
        <div style="margin: 4px 0;">
            <div style="display:flex; justify-content:space-between; margin-bottom:2px;">
                <span style="font-size:0.8rem; color:#D1D5DB">{label}</span>
                <span style="font-size:0.8rem; font-weight:700; color:{color}">
                    {icon} {score}/{max_score}
                </span>
            </div>
            <div style="background:#374151; border-radius:4px; height:8px;">
                <div style="
                    background:{color};
                    width:{pct*100:.0f}%;
                    height:8px;
                    border-radius:4px;
                    transition:width 0.3s;
                "></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_evaluation_dashboard():
    """Full evaluation quality dashboard."""
    st.markdown("## 📊 Evaluation Dashboard")

    tab1, tab2, tab3 = st.tabs([
        "📈 Quality Stats",
        "📋 Recent Evaluations",
        "🔍 Filter & Browse",
    ])

    # ── Quality Stats ─────────────────────────────────────────
    with tab1:
        if st.button("🔄 Refresh", key="refresh_eval_stats"):
            st.cache_data.clear()

        try:
            r = requests.get(f"{API_URL}/evaluations/stats", timeout=10)
            if r.status_code != 200:
                st.error("Could not load evaluation stats")
                return
            stats = r.json()

            if not stats.get("total_evaluations"):
                st.info(
                    "No evaluations yet. Run some multi-agent pipeline requests first, "
                    "then come back here to see quality scores."
                )
                return

            # Top metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Evaluated", stats["total_evaluations"])
            with col2:
                avg = float(stats.get("avg_overall") or 0)
                color, icon = _score_color(int(avg))
                st.metric("Avg Overall Score", f"{icon} {avg:.1f}/10")
            with col3:
                high = stats.get("high_quality_count", 0)
                total = stats["total_evaluations"]
                st.metric("High Quality (≥8)", f"{high} ({high/total*100:.0f}%)")
            with col4:
                low = stats.get("low_quality_count", 0)
                st.metric("Low Quality (<6)", f"{low} ({low/total*100:.0f}%)")

            st.markdown("---")

            # Score breakdown
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 📊 Score Breakdown")
                dimensions = [
                    ("Relevance",    "avg_relevance"),
                    ("Accuracy",     "avg_accuracy"),
                    ("Completeness", "avg_completeness"),
                    ("Efficiency",   "avg_efficiency"),
                    ("Coherence",    "avg_coherence"),
                ]
                for label, key in dimensions:
                    score = int(float(stats.get(key) or 0))
                    render_score_bar(label, score)

            with col2:
                st.markdown("### 📋 By Task Type")
                for row in stats.get("by_task_type", []):
                    task = row["task_type"]
                    count = row["count"]
                    avg_s = float(row["avg_score"] or 0)
                    color, icon = _score_color(int(avg_s))
                    st.markdown(
                        f"""<div style="
                            background:#1F2937;
                            border-left: 4px solid {color};
                            padding: 8px 12px;
                            border-radius: 0 8px 8px 0;
                            margin: 6px 0;
                        ">
                            <strong style="color:{color}">{task.upper()}</strong>
                            &nbsp; {icon} {avg_s:.1f}/10 &nbsp;|&nbsp; {count} runs
                        </div>""",
                        unsafe_allow_html=True,
                    )

            st.markdown("---")

            # Top weaknesses
            weaknesses = stats.get("top_weaknesses", [])
            if weaknesses:
                st.markdown("### ⚠️ Most Common Weaknesses")
                for w in weaknesses:
                    st.markdown(f"- **{w['weakness']}** ({w['frequency']} occurrences)")

            # Recent trend
            recent = stats.get("recent_scores", [])
            if recent:
                st.markdown("---")
                st.markdown("### 📈 Recent Score Trend (last 10)")
                scores_list = [r["score_overall"] for r in reversed(recent)]
                st.line_chart(scores_list)

        except Exception as e:
            st.error(f"Error: {e}")

    # ── Recent Evaluations ────────────────────────────────────
    with tab2:
        if st.button("🔄 Refresh", key="refresh_eval_list"):
            st.cache_data.clear()

        try:
            r = requests.get(
                f"{API_URL}/evaluations",
                params={"limit": 15},
                timeout=10,
            )
            if r.status_code != 200:
                st.error("Could not load evaluations")
                return

            evals = r.json()["evaluations"]
            if not evals:
                st.info("No evaluations yet.")
                return

            st.markdown(f"**{len(evals)} recent evaluations**")
            for ev in evals:
                _render_eval_card(ev)

        except Exception as e:
            st.error(f"Error: {e}")

    # ── Filter & Browse ───────────────────────────────────────
    with tab3:
        st.markdown("### Filter Evaluations")
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_session = st.text_input("Session ID", key="eval_filter_session")
        with col2:
            filter_task = st.selectbox(
                "Task Type",
                ["", "simple", "research", "code", "both"],
                key="eval_filter_task",
            )
        with col3:
            min_score = st.slider("Min Score", 0, 10, 0, key="eval_min_score")

        if st.button("🔍 Search", key="eval_search"):
            try:
                params = {"limit": 20, "min_score": min_score}
                if filter_session:
                    params["session_id"] = filter_session
                if filter_task:
                    params["task_type"] = filter_task

                r = requests.get(
                    f"{API_URL}/evaluations",
                    params=params,
                    timeout=10,
                )
                evals = r.json()["evaluations"]
                st.markdown(f"**{len(evals)} results**")
                for ev in evals:
                    _render_eval_card(ev)
            except Exception as e:
                st.error(f"Error: {e}")

        st.markdown("---")
        st.markdown("### 🧹 Cleanup")
        if st.button("🗑️ Clear All Evaluations", use_container_width=False):
            r = requests.delete(f"{API_URL}/evaluations", timeout=10)
            if r.status_code == 200:
                st.success(f"Deleted {r.json()['deleted']} evaluations")
                st.rerun()


def _render_eval_card(ev: dict):
    """Render a single evaluation as an expandable card."""
    overall = ev.get("score_overall", 0)
    color, icon = _score_color(overall)
    task_type = ev.get("task_type", "simple")
    created = str(ev.get("created_at", ""))[:19]
    agents = ev.get("agents_used") or []
    revision = "♻️" if ev.get("had_revision") else ""

    header = (
        f"{icon} **{overall}/10** | "
        f"`{task_type}` | "
        f"Agents: {len(agents)} {revision} | "
        f"{created}"
    )

    with st.expander(header, expanded=False):
        # User message
        st.markdown(f"**Question:** {ev['user_message'][:200]}")

        # Score bars
        st.markdown("**Scores:**")
        col1, col2 = st.columns(2)
        with col1:
            render_score_bar("Relevance",    ev.get("score_relevance", 0))
            render_score_bar("Accuracy",     ev.get("score_accuracy", 0))
            render_score_bar("Completeness", ev.get("score_completeness", 0))
        with col2:
            render_score_bar("Efficiency", ev.get("score_efficiency", 0))
            render_score_bar("Coherence",  ev.get("score_coherence", 0))
            render_score_bar("Overall",    overall)

        # Strengths / weaknesses
        col1, col2 = st.columns(2)
        with col1:
            strengths = ev.get("strengths") or []
            if strengths:
                st.markdown("**✅ Strengths:**")
                for s in strengths:
                    st.markdown(f"- {s}")
        with col2:
            weaknesses = ev.get("weaknesses") or []
            if weaknesses:
                st.markdown("**⚠️ Weaknesses:**")
                for w in weaknesses:
                    st.markdown(f"- {w}")

        if ev.get("reasoning"):
            st.markdown(f"**Reasoning:** {ev['reasoning'][:300]}")

        if ev.get("response_preview"):
            with st.expander("📝 Response Preview", expanded=False):
                st.markdown(ev["response_preview"])