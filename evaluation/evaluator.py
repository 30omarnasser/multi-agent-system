import os
import json
import ollama as ollama_client
from dotenv import load_dotenv

load_dotenv()

EVALUATION_PROMPT = """You are an AI quality evaluator. Score this AI response on 5 dimensions.

User request: {user_message}

AI response: {response}

Additional context:
- Agents used: {agents_used}
- Task type: {task_type}
- Had revision: {had_revision}
- Research was done: {had_research}
- Code was executed: {had_code}

Score each dimension from 0-10. Return ONLY valid JSON:
{{
  "relevance": <0-10>,
  "accuracy": <0-10>,
  "completeness": <0-10>,
  "efficiency": <0-10>,
  "coherence": <0-10>,
  "overall": <0-10>,
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["weakness 1", "weakness 2"],
  "reasoning": "brief explanation of scores"
}}

Scoring guide:
- relevance: does the response directly address what was asked?
- accuracy: is the information factually correct and trustworthy?
- completeness: does it fully answer all parts of the question?
- efficiency: was the right amount of effort used (not over/under)?
- coherence: is it well-structured and easy to understand?
- overall: holistic quality score

Return ONLY the JSON object."""


class EvaluationEngine:
    """
    Automatically evaluates pipeline responses using LLM-as-judge.
    Scores responses on multiple quality dimensions.
    """

    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model
        self.ollama = ollama_client.Client(
            host=os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        )
        print(f"[Evaluator] Initialized | model: {self.model}")

    def evaluate(
        self,
        user_message: str,
        response: str,
        agents_used: list[str],
        task_type: str = "simple",
        had_revision: bool = False,
        research: str = "",
        code_output: str = "",
        trace_id: str = "",
    ) -> dict:
        """
        Evaluate a pipeline response on multiple quality dimensions.
        Returns scores dict with reasoning.
        """
        print(f"[Evaluator] Evaluating response for: '{user_message[:60]}'")

        prompt = EVALUATION_PROMPT.format(
            user_message=user_message[:300],
            response=response[:1000],
            agents_used=", ".join(agents_used),
            task_type=task_type,
            had_revision=had_revision,
            had_research=bool(research),
            had_code=bool(code_output),
        )

        try:
            api_response = self.ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a strict AI quality evaluator. "
                            "Return ONLY valid JSON, nothing else."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            raw = api_response["message"]["content"].strip()

            # Clean markdown
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            if "{" in raw and "}" in raw:
                raw = raw[raw.index("{"):raw.rindex("}") + 1]

            scores = json.loads(raw)
            scores = self._validate_scores(scores)

        except Exception as e:
            print(f"[Evaluator] Evaluation failed: {e}")
            scores = self._fallback_scores(
                agents_used=agents_used,
                had_revision=had_revision,
                response=response,
            )

        # Add metadata
        scores["trace_id"] = trace_id
        scores["task_type"] = task_type
        scores["agents_used"] = agents_used
        scores["agent_count"] = len(agents_used)

        print(
            f"[Evaluator] ✓ Scores — "
            f"overall={scores.get('overall')}/10 | "
            f"relevance={scores.get('relevance')} | "
            f"completeness={scores.get('completeness')}"
        )
        return scores

    def _validate_scores(self, scores: dict) -> dict:
        """Ensure all required fields exist and are valid."""
        required = {
            "relevance": 7,
            "accuracy": 7,
            "completeness": 7,
            "efficiency": 7,
            "coherence": 7,
            "overall": 7,
            "strengths": [],
            "weaknesses": [],
            "reasoning": "",
        }
        for key, default in required.items():
            if key not in scores or scores[key] is None:
                scores[key] = default
            # Clamp numeric scores to 0-10
            if key not in ("strengths", "weaknesses", "reasoning"):
                try:
                    scores[key] = max(0, min(10, int(scores[key])))
                except (TypeError, ValueError):
                    scores[key] = default

        # Ensure lists
        if not isinstance(scores.get("strengths"), list):
            scores["strengths"] = []
        if not isinstance(scores.get("weaknesses"), list):
            scores["weaknesses"] = []

        return scores

    def _fallback_scores(
        self,
        agents_used: list[str],
        had_revision: bool,
        response: str,
    ) -> dict:
        """Generate heuristic scores when LLM evaluation fails."""
        base = 6
        # Longer responses are generally more complete
        if len(response) > 500:
            base += 1
        # Revision means it self-corrected — slight penalty for needing it
        if had_revision:
            base -= 1
        # More agents = more thorough
        if len(agents_used) >= 4:
            base += 1

        score = max(0, min(10, base))
        return {
            "relevance": score,
            "accuracy": score,
            "completeness": score,
            "efficiency": 7,
            "coherence": score,
            "overall": score,
            "strengths": ["Response was generated"],
            "weaknesses": ["Evaluation failed — scores are estimated"],
            "reasoning": "Fallback heuristic scoring — LLM evaluation unavailable",
        }