import os
import json
import tempfile
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
EXPERIMENT_NAME = "multi-agent-system"


class MLflowLogger:
    """
    Logs pipeline runs, evaluation scores, and agent traces to MLflow.
    Provides experiment tracking, metric comparison, and artifact storage.
    """

    def __init__(self):
        self.enabled = False
        self._setup()

    def _setup(self):
        """Initialize MLflow — fail gracefully if unavailable."""
        try:
            import mlflow
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            mlflow.set_experiment(EXPERIMENT_NAME)
            self.mlflow = mlflow
            self.enabled = True
            print(f"[MLflow] Connected to {MLFLOW_TRACKING_URI}")
        except Exception as e:
            print(f"[MLflow] Unavailable (non-critical): {e}")
            self.enabled = False

    def log_pipeline_run(
        self,
        session_id: str,
        user_message: str,
        final_response: str,
        agents_used: list[str],
        plan: dict,
        critique: dict,
        eval_scores: dict,
        trace_id: str,
        total_duration_ms: int,
        had_revision: bool,
        model: str = "llama3.1:8b",
    ) -> str:
        """
        Log a complete pipeline run to MLflow.
        Returns the MLflow run_id or empty string if disabled.
        """
        if not self.enabled:
            return ""

        try:
            with self.mlflow.start_run(
                run_name=f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            ) as run:
                # ── Parameters (config/inputs) ─────────────────
                self.mlflow.log_params({
                    "model":        model,
                    "session_id":   session_id[:50],
                    "task_type":    plan.get("task_type", "simple"),
                    "complexity":   plan.get("complexity", "low"),
                    "agent_count":  len(agents_used),
                    "agents_used":  ",".join(agents_used),
                    "had_revision": had_revision,
                    "needs_research": plan.get("needs_research", False),
                    "needs_code":   plan.get("needs_code", False),
                    "trace_id":     trace_id[:50],
                })

                # ── Metrics (numeric scores) ───────────────────
                metrics = {
                    "duration_seconds":   total_duration_ms / 1000,
                    "critique_score":     float(critique.get("score", 0) or 0),
                    "eval_overall":       float(eval_scores.get("overall", 0) or 0),
                    "eval_relevance":     float(eval_scores.get("relevance", 0) or 0),
                    "eval_accuracy":      float(eval_scores.get("accuracy", 0) or 0),
                    "eval_completeness":  float(eval_scores.get("completeness", 0) or 0),
                    "eval_efficiency":    float(eval_scores.get("efficiency", 0) or 0),
                    "eval_coherence":     float(eval_scores.get("coherence", 0) or 0),
                    "response_length":    float(len(final_response)),
                    "revision_count":     float(1 if had_revision else 0),
                    "plan_confidence":    float(plan.get("confidence", 0.5) or 0.5),
                }
                self.mlflow.log_metrics(metrics)

                # ── Tags ──────────────────────────────────────
                self.mlflow.set_tags({
                    "session_id": session_id,
                    "task_type":  plan.get("task_type", "simple"),
                    "model":      model,
                    "quality":    (
                        "high" if metrics["eval_overall"] >= 8
                        else "medium" if metrics["eval_overall"] >= 6
                        else "low"
                    ),
                })

                # ── Artifacts (text files) ─────────────────────
                with tempfile.TemporaryDirectory() as tmp:
                    # 1. Conversation artifact
                    conv_path = os.path.join(tmp, "conversation.txt")
                    with open(conv_path, "w") as f:
                        f.write(f"USER: {user_message}\n\n")
                        f.write(f"ASSISTANT: {final_response}\n")
                    self.mlflow.log_artifact(conv_path, "conversation")

                    # 2. Plan artifact
                    plan_path = os.path.join(tmp, "plan.json")
                    with open(plan_path, "w") as f:
                        json.dump(plan, f, indent=2, default=str)
                    self.mlflow.log_artifact(plan_path, "plan")

                    # 3. Evaluation artifact
                    eval_path = os.path.join(tmp, "evaluation.json")
                    with open(eval_path, "w") as f:
                        json.dump({
                            "scores": eval_scores,
                            "critique": critique,
                        }, f, indent=2, default=str)
                    self.mlflow.log_artifact(eval_path, "evaluation")

                run_id = run.info.run_id
                print(f"[MLflow] ✓ Logged run: {run_id}")
                return run_id

        except Exception as e:
            print(f"[MLflow] Logging failed (non-critical): {e}")
            return ""

    def log_memory_stats(self, stats: dict) -> str:
        """Log memory health stats as a separate MLflow run."""
        if not self.enabled:
            return ""

        try:
            with self.mlflow.start_run(
                run_name=f"memory_stats_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            ) as run:
                self.mlflow.set_tag("run_type", "memory_stats")

                metrics = {
                    "facts_total":      float(stats.get("facts", {}).get("total", 0)),
                    "episodes_total":   float(stats.get("episodes", {}).get("total", 0)),
                    "doc_chunks_total": float(stats.get("documents", {}).get("total_chunks", 0)),
                    "profiles_total":   float(stats.get("profiles", {}).get("total", 0)),
                }
                self.mlflow.log_metrics(metrics)

                return run.info.run_id
        except Exception as e:
            print(f"[MLflow] Memory stats logging failed: {e}")
            return ""

    def get_experiment_summary(self) -> dict:
        """Get summary of all logged runs from MLflow."""
        if not self.enabled:
            return {"enabled": False, "runs": []}

        try:
            experiment = self.mlflow.get_experiment_by_name(EXPERIMENT_NAME)
            if not experiment:
                return {"enabled": True, "runs": [], "total": 0}

            runs = self.mlflow.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=["start_time DESC"],
                max_results=50,
            )

            if runs.empty:
                return {"enabled": True, "runs": [], "total": 0}

            run_list = []
            for _, row in runs.iterrows():
                run_list.append({
                    "run_id":         row.get("run_id", ""),
                    "run_name":       row.get("tags.mlflow.runName", ""),
                    "task_type":      row.get("params.task_type", ""),
                    "model":          row.get("params.model", ""),
                    "agents_used":    row.get("params.agents_used", ""),
                    "had_revision":   row.get("params.had_revision", ""),
                    "eval_overall":   row.get("metrics.eval_overall", 0),
                    "critique_score": row.get("metrics.critique_score", 0),
                    "duration_s":     row.get("metrics.duration_seconds", 0),
                    "quality_tag":    row.get("tags.quality", ""),
                    "start_time":     str(row.get("start_time", ""))[:19],
                    "status":         row.get("status", ""),
                })

            # Aggregate metrics
            avg_overall = runs["metrics.eval_overall"].mean() if "metrics.eval_overall" in runs else 0
            avg_duration = runs["metrics.duration_seconds"].mean() if "metrics.duration_seconds" in runs else 0

            return {
                "enabled":      True,
                "experiment":   EXPERIMENT_NAME,
                "total":        len(run_list),
                "avg_score":    round(float(avg_overall), 2),
                "avg_duration": round(float(avg_duration), 2),
                "runs":         run_list,
                "ui_url":       MLFLOW_TRACKING_URI,
            }

        except Exception as e:
            print(f"[MLflow] Summary failed: {e}")
            return {"enabled": True, "error": str(e), "runs": []}

    def get_best_runs(self, metric: str = "eval_overall", top_k: int = 5) -> list[dict]:
        """Get top K runs by a specific metric."""
        if not self.enabled:
            return []

        try:
            experiment = self.mlflow.get_experiment_by_name(EXPERIMENT_NAME)
            if not experiment:
                return []

            runs = self.mlflow.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=[f"metrics.{metric} DESC"],
                max_results=top_k,
            )

            if runs.empty:
                return []

            result = []
            for _, row in runs.iterrows():
                result.append({
                    "run_id":       row.get("run_id", ""),
                    "task_type":    row.get("params.task_type", ""),
                    "eval_overall": row.get("metrics.eval_overall", 0),
                    "duration_s":   row.get("metrics.duration_seconds", 0),
                    "agents":       row.get("params.agents_used", ""),
                    "quality":      row.get("tags.quality", ""),
                })
            return result

        except Exception as e:
            print(f"[MLflow] Best runs failed: {e}")
            return []