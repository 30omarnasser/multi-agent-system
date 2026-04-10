import json
import os
import ollama as ollama_client
from agents.state import AgentState

PLANNER_PROMPT = """You are a Planner agent in a multi-agent AI system.
Your job is to analyze the user's request and produce a detailed execution plan.

You must respond ONLY with a valid JSON object — no explanation, no markdown, no backticks.

JSON schema:
{
  "task_type": "simple" | "research" | "code" | "both",
  "subtasks": [
    {"step": 1, "description": "what to do", "agent": "researcher" | "coder" | "responder"}
  ],
  "needs_research": true | false,
  "needs_code": true | false,
  "complexity": "low" | "medium" | "high",
  "estimated_steps": 1-5,
  "search_queries": ["exact search query 1", "exact search query 2"],
  "code_requirements": ["requirement 1", "requirement 2"],
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation of your decisions"
}

task_type guide:
- "simple": conversational question, no tools needed, answer directly
- "research": needs current/factual info from web search
- "code": needs Python code written and executed
- "both": needs web search first, then code using the results

search_queries: only fill if needs_research=true. Write the exact queries to search.
code_requirements: only fill if needs_code=true. List what the code must do.
confidence: how confident you are in this plan (0.0=uncertain, 1.0=certain)

Examples:
- "What is 2+2?" → simple, no research, no code
- "What is the Bitcoin price?" → research, search_queries=["Bitcoin current price USD"]
- "Write code to sort a list" → code, code_requirements=["sort a list", "print result"]
- "Get BTC price and calculate how many I can buy with $1000" → both

Return ONLY the JSON object. Nothing else."""

VALIDATION_PROMPT = """You are a JSON validator. 
The following plan may have issues. Fix it and return a valid plan JSON.
Ensure all required fields exist and have correct types.
Return ONLY valid JSON, nothing else.

Required fields: task_type, subtasks, needs_research, needs_code, 
complexity, estimated_steps, search_queries, code_requirements, confidence, reasoning

Plan to validate:
{plan}"""


class PlannerAgent:

    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model
        self.ollama = ollama_client.Client(
            host=os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        )
        print(f"[PlannerAgent] Initialized | model: {self.model}")

    # ─── Core Run ─────────────────────────────────────────────

    def run(self, state: AgentState) -> AgentState:
        user_message = state["user_message"]
        print(f"\n[PlannerAgent] Planning: '{user_message[:100]}'")

        plan = self._generate_plan(user_message)
        plan = self._validate_plan(plan)
        plan = self._apply_defaults(plan)

        self._log_plan(plan)

        return {
            **state,
            "plan": plan,
            "search_queries": plan.get("search_queries", []),
            "code_requirements": plan.get("code_requirements", []),
            "current_agent": "planner",
        }

    # ─── Plan Generation ──────────────────────────────────────

    def _generate_plan(self, user_message: str) -> dict:
        """Call LLM to generate initial plan."""
        try:
            response = self.ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": PLANNER_PROMPT},
                    {"role": "user", "content": f"User request: {user_message}"},
                ],
            )
            raw = response["message"]["content"].strip()
            return self._parse_json(raw)

        except Exception as e:
            print(f"[PlannerAgent] Generation failed: {e}")
            return self._fallback_plan(user_message, str(e))

    def _validate_plan(self, plan: dict) -> dict:
        """Ask LLM to validate and repair the plan if needed."""
        required_fields = {
            "task_type", "subtasks", "needs_research", "needs_code",
            "complexity", "estimated_steps", "search_queries",
            "code_requirements", "confidence", "reasoning",
        }

        missing = required_fields - set(plan.keys())
        if not missing:
            return plan  # plan is complete, skip validation call

        print(f"[PlannerAgent] Plan missing fields: {missing} — repairing...")
        try:
            response = self.ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a JSON repair assistant. Return ONLY valid JSON.",
                    },
                    {
                        "role": "user",
                        "content": VALIDATION_PROMPT.format(plan=json.dumps(plan)),
                    },
                ],
            )
            raw = response["message"]["content"].strip()
            repaired = self._parse_json(raw)
            print(f"[PlannerAgent] Plan repaired successfully.")
            return repaired
        except Exception as e:
            print(f"[PlannerAgent] Repair failed: {e} — using defaults")
            return plan

    def _apply_defaults(self, plan: dict) -> dict:
        """Fill any remaining missing fields with safe defaults."""
        defaults = {
            "task_type": "simple",
            "subtasks": [],
            "needs_research": False,
            "needs_code": False,
            "complexity": "low",
            "estimated_steps": 1,
            "search_queries": [],
            "code_requirements": [],
            "confidence": 0.7,
            "reasoning": "Default plan.",
        }
        for key, value in defaults.items():
            if key not in plan:
                plan[key] = value

        # Fix type mismatches
        if isinstance(plan["subtasks"], list):
            # Normalize subtasks — accept both strings and dicts
            normalized = []
            for i, s in enumerate(plan["subtasks"]):
                if isinstance(s, str):
                    normalized.append({"step": i + 1, "description": s, "agent": "responder"})
                elif isinstance(s, dict):
                    normalized.append(s)
            plan["subtasks"] = normalized

        # Ensure search_queries and code_requirements are lists
        if not isinstance(plan.get("search_queries"), list):
            plan["search_queries"] = []
        if not isinstance(plan.get("code_requirements"), list):
            plan["code_requirements"] = []

        # Auto-fix task_type consistency
        if plan["needs_research"] and plan["needs_code"]:
            plan["task_type"] = "both"
        elif plan["needs_research"] and plan["task_type"] == "simple":
            plan["task_type"] = "research"
        elif plan["needs_code"] and plan["task_type"] == "simple":
            plan["task_type"] = "code"

        return plan

    # ─── Helpers ──────────────────────────────────────────────

    def _parse_json(self, raw: str) -> dict:
        """Safely parse JSON from LLM output."""
        # Strip markdown fences
        if "```" in raw:
            parts = raw.split("```")
            for part in parts:
                if part.startswith("json"):
                    raw = part[4:].strip()
                    break
                elif "{" in part:
                    raw = part.strip()
                    break

        # Extract JSON object
        if "{" in raw and "}" in raw:
            raw = raw[raw.index("{"):raw.rindex("}") + 1]

        return json.loads(raw)

    def _fallback_plan(self, user_message: str, error: str) -> dict:
        """Return a safe default plan when everything fails."""
        # Simple heuristics to guess task type
        lowered = user_message.lower()
        needs_research = any(w in lowered for w in [
            "search", "find", "latest", "current", "news", "price", "today", "recent"
        ])
        needs_code = any(w in lowered for w in [
            "code", "write", "run", "execute", "calculate", "compute", "script", "program"
        ])

        if needs_research and needs_code:
            task_type = "both"
        elif needs_research:
            task_type = "research"
        elif needs_code:
            task_type = "code"
        else:
            task_type = "simple"

        return {
            "task_type": task_type,
            "subtasks": [{"step": 1, "description": "Handle user request", "agent": "responder"}],
            "needs_research": needs_research,
            "needs_code": needs_code,
            "complexity": "low",
            "estimated_steps": 1,
            "search_queries": [user_message] if needs_research else [],
            "code_requirements": [user_message] if needs_code else [],
            "confidence": 0.5,
            "reasoning": f"Fallback heuristic plan. LLM error: {error}",
        }

    def _log_plan(self, plan: dict):
        """Pretty print the plan for debugging."""
        print(f"[PlannerAgent] ─── Plan ───────────────────────")
        print(f"  task_type:      {plan.get('task_type')}")
        print(f"  complexity:     {plan.get('complexity')}")
        print(f"  needs_research: {plan.get('needs_research')}")
        print(f"  needs_code:     {plan.get('needs_code')}")
        print(f"  confidence:     {plan.get('confidence')}")
        print(f"  search_queries: {plan.get('search_queries')}")
        print(f"  code_reqs:      {plan.get('code_requirements')}")
        print(f"  reasoning:      {plan.get('reasoning', '')[:100]}")
        print(f"  subtasks:")
        for s in plan.get("subtasks", []):
            if isinstance(s, dict):
                print(f"    {s.get('step', '?')}. [{s.get('agent', '?')}] {s.get('description', '')}")
            else:
                print(f"    - {s}")
        print(f"[PlannerAgent] ────────────────────────────────")