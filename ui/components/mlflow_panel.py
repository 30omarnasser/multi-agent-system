import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")
MLFLOW_UI_URL = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")


def render_mlflow_panel():
    """MLflow experiment tracking panel."""
    st.markdown("## 🧪 Experiment Tracking (MLflow)")

    tab1, tab2, tab3 = st.tabs([
        "📊 Overview",
        "🏆 Best Runs",
        "📋 All Runs",
    ])

    # ── Overview ──────────────────────────────────────────────
    with tab1:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(
                f"🔗 **MLflow UI:** [Open Dashboard]({MLFLOW_UI_URL}) "
                f"(full experiment browser)"
            )
        with col2:
            if st.button("🔄 Refresh", key="refresh_mlflow"):
                st.cache_data.clear()

        try:
            r = requests.get(f"{API_URL}/mlflow/summary", timeout=10)
            if r.status_code != 200:
                st.error("MLflow not available")
                return

            data = r.json()

            if not data.get("enabled"):
                st.warning(
                    "MLflow is not connected. "
                    "Make sure the MLflow service is running and rebuilt."
                )
                return

            if data.get("error"):
                st.error(f"MLflow error: {data['error']}")
                return

            if data.get("total", 0) == 0:
                st.info(
                    "No runs logged yet. "
                    "Send a few messages through the Chat tab to generate runs."
                )
                return

            # Top metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Runs", data["total"])
            with col2:
                avg_s = data.get("avg_score", 0)
                icon = "🟢" if avg_s >= 8 else "🟡" if avg_s >= 6 else "🔴"
                st.metric("Avg Score", f"{icon} {avg_s}/10")
            with col3:
                st.metric("Avg Duration", f"{data.get('avg_duration', 0):.1f}s")
            with col4:
                runs = data.get("runs", [])
                high = sum(1 for r in runs if r.get("quality_tag") == "high")
                st.metric("High Quality", f"{high}/{len(runs)}")

            st.markdown("---")

            # Score trend
            runs = data.get("runs", [])
            if runs:
                scores = [r.get("eval_overall", 0) for r in reversed(runs[:20])]
                st.markdown("### 📈 Score Trend (recent runs)")
                st.line_chart(scores)

                # Task type distribution
                st.markdown("### 🗂️ Task Type Distribution")
                task_counts = {}
                for r in runs:
                    t = r.get("task_type", "unknown")
                    task_counts[t] = task_counts.get(t, 0) + 1

                cols = st.columns(len(task_counts))
                task_colors = {
                    "simple": "🟢",
                    "research": "🔵",
                    "code": "🟡",
                    "both": "🟣",
                }
                for i, (task, count) in enumerate(task_counts.items()):
                    with cols[i]:
                        icon = task_colors.get(task, "⚪")
                        st.metric(f"{icon} {task}", count)

        except Exception as e:
            st.error(f"Error connecting to MLflow: {e}")

    # ── Best Runs ─────────────────────────────────────────────
    with tab2:
        metric_options = [
            "eval_overall",
            "eval_relevance",
            "eval_accuracy",
            "eval_completeness",
            "critique_score",
        ]
        col1, col2 = st.columns(2)
        with col1:
            selected_metric = st.selectbox(
                "Rank by metric",
                metric_options,
                key="mlflow_best_metric",
            )
        with col2:
            top_k = st.slider("Show top", 3, 10, 5, key="mlflow_top_k")

        if st.button("🏆 Get Best Runs", key="mlflow_get_best"):
            try:
                r = requests.get(
                    f"{API_URL}/mlflow/best",
                    params={"metric": selected_metric, "top_k": top_k},
                    timeout=10,
                )
                if r.status_code == 200:
                    best = r.json()["runs"]
                    if not best:
                        st.info("No runs found.")
                    else:
                        st.markdown(
                            f"**Top {len(best)} runs by `{selected_metric}`:**"
                        )
                        for i, run in enumerate(best, 1):
                            quality = run.get("quality", "")
                            icon = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
                            st.markdown(
                                f"""<div style="
                                    background:#1F2937;
                                    border-radius:8px;
                                    padding:12px 16px;
                                    margin:8px 0;
                                    border-left: 4px solid {'#10B981' if quality=='high' else '#F59E0B'};
                                ">
                                    <strong>{icon} Run: <code>{run['run_id'][:16]}</code></strong><br>
                                    📊 Score: <strong>{run['eval_overall']:.1f}/10</strong>
                                    &nbsp;|&nbsp; ⏱️ {run['duration_s']:.1f}s
                                    &nbsp;|&nbsp; 🗂️ {run['task_type']}
                                    &nbsp;|&nbsp; 🤖 {run['agents']}
                                </div>""",
                                unsafe_allow_html=True,
                            )
            except Exception as e:
                st.error(f"Error: {e}")

    # ── All Runs ──────────────────────────────────────────────
    with tab3:
        try:
            r = requests.get(f"{API_URL}/mlflow/summary", timeout=10)
            if r.status_code != 200:
                st.error("Could not load runs")
                return

            data = r.json()
            runs = data.get("runs", [])

            if not runs:
                st.info("No runs logged yet.")
                return

            st.markdown(f"**{len(runs)} logged runs** (most recent first)")

            for run in runs:
                score = run.get("eval_overall", 0)
                quality = run.get("quality_tag", "")
                icon = "🟢" if quality == "high" else "🟡" if quality == "medium" else "🔴"
                task = run.get("task_type", "")
                duration = run.get("duration_s", 0)
                agents = run.get("agents_used", "")
                start = run.get("start_time", "")[:16]

                with st.expander(
                    f"{icon} {score:.0f}/10 | `{task}` | {duration:.1f}s | {start}",
                    expanded=False,
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Run ID:** `{run['run_id'][:20]}`")
                        st.markdown(f"**Task Type:** `{task}`")
                        st.markdown(f"**Agents:** {agents}")
                        st.markdown(f"**Had Revision:** {run.get('had_revision', 'N/A')}")
                    with col2:
                        st.markdown(f"**Overall Score:** {score:.1f}/10")
                        st.markdown(f"**Duration:** {duration:.1f}s")
                        st.markdown(f"**Quality:** {quality}")
                        st.markdown(f"**Model:** {run.get('model', 'N/A')}")

                    st.markdown(
                        f"[🔗 View in MLflow UI]({MLFLOW_UI_URL}/#/experiments/1/runs/{run['run_id']})"
                    )

        except Exception as e:
            st.error(f"Error: {e}")