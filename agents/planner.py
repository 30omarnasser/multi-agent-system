import json
import os
import ollama as ollama_client
from agents.state import AgentState

PLANNER_PROMPT = """You are a Planner agent in a multi-agent AI system.
Your job is to analyze the user's request and break it down into a clear plan.

Respond ONLY with a JSON object like this:
{
  "task_type": "research" | "code" | "both" | "simple",
  "subtasks": ["subtask 1", "subtask 2"],
  "needs_research": true | false,
  "needs_code": true | false,
  "complexity": "low" | "medium" | "high",
  "reasoning": "why you made these decisions"
}

task_type guide:
- "simple": just answer directly, no tools needed
- "research": needs web search for current info
- "code": needs Python code written and executed
- "both": needs both research and code

Return ONLY valid JSON. No explanation, no markdown."""


class PlannerAgent:

    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model
        self.ollama = ollama_client.Client(
            host=os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        )
        print(f"[PlannerAgent] Initialized | model: {self.model}")

    def run(self, state: AgentState) -> AgentState:
        print(f"\n[PlannerAgent] Planning task: {state['user_message'][:100]}")

        try:
            response = self.ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": PLANNER_PROMPT},
                    {"role": "user", "content": f"User request: {state['user_message']}"},
                ],
            )
            raw = response["message"]["content"].strip()

            # Clean markdown if present
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            if "{" in raw and "}" in raw:
                raw = raw[raw.index("{"):raw.rindex("}") + 1]

            plan = json.loads(raw)
            print(f"[PlannerAgent] Plan: {plan}")

        except Exception as e:
            print(f"[PlannerAgent] Planning failed, using default: {e}")
            plan = {
                "task_type": "simple",
                "subtasks": ["Answer the user's question directly"],
                "needs_research": False,
                "needs_code": False,
                "complexity": "low",
                "reasoning": f"Fallback plan due to error: {e}",
            }

        return {
            **state,
            "plan": plan,
            "current_agent": "planner",
        }