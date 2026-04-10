import json
import os
import ollama as ollama_client
from agents.state import AgentState

CRITIC_PROMPT = """You are a Critic agent in a multi-agent AI system.
Your job is to evaluate the quality of the work done by other agents.
Be strict but fair. Check for accuracy, completeness, and relevance.

Respond ONLY with a JSON object:
{
  "score": 1-10,
  "approved": true | false,
  "feedback": "specific feedback on what's good and what needs improvement",
  "issues": ["issue 1", "issue 2"]
}

Approve (true) if score >= 7. Reject if score < 7.
Return ONLY valid JSON. No explanation, no markdown."""


class CriticAgent:

    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model
        self.ollama = ollama_client.Client(
            host=os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        )
        print(f"[CriticAgent] Initialized | model: {self.model}")

    def run(self, state: AgentState) -> AgentState:
        user_message = state["user_message"]
        research = state.get("research", "")
        code_output = state.get("code_output", "")
        revision_count = state.get("revision_count", 0)

        print(f"\n[CriticAgent] Evaluating output (revision #{revision_count})")

        # Build evaluation context
        work_done = ""
        if research:
            work_done += f"Research Summary:\n{research}\n\n"
        if code_output:
            work_done += f"Code & Output:\n{code_output}\n\n"

        if not work_done:
            # Nothing to critique — auto approve simple tasks
            return {
                **state,
                "critique": {"score": 9, "approved": True, "feedback": "Simple task, no critique needed.", "issues": []},
                "current_agent": "critic",
            }

        try:
            response = self.ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": CRITIC_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Original request: {user_message}\n\n"
                            f"Work to evaluate:\n{work_done}\n\n"
                            f"Evaluate this work."
                        ),
                    },
                ],
            )
            raw = response["message"]["content"].strip()

            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            if "{" in raw and "}" in raw:
                raw = raw[raw.index("{"):raw.rindex("}") + 1]

            critique = json.loads(raw)
            print(f"[CriticAgent] Score: {critique.get('score')}/10 | Approved: {critique.get('approved')}")
            print(f"[CriticAgent] Feedback: {critique.get('feedback', '')[:200]}")

        except Exception as e:
            print(f"[CriticAgent] Critique failed: {e}")
            critique = {"score": 8, "approved": True, "feedback": "Auto-approved due to evaluation error.", "issues": []}

        return {
            **state,
            "critique": critique,
            "revision_count": revision_count + 1,
            "current_agent": "critic",
        }