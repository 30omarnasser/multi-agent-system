import os
import ollama as ollama_client
from agents.state import AgentState

RESPONDER_PROMPT = """You are a Responder agent — the final step in a multi-agent AI pipeline.
Your job is to synthesize all the work done by other agents into one clear, polished,
helpful response for the user.

Your response must:
- Directly answer the user's original question
- Integrate research findings naturally (don't just dump raw search results)
- Present code output clearly (explain what the code did and what the results mean)
- Be conversational and helpful, not robotic
- Be well-structured with clear sections if the response is long
- Never mention the internal agent names (Planner, Researcher, Coder, Critic)
- Sound like one coherent expert answer, not a collection of parts

If only research was done: summarize findings in a clear, readable way.
If only code was done: explain what was built and show the results.
If both were done: integrate them — use research data to contextualize code results.
If neither was done: answer directly from your knowledge."""


class ResponderAgent:

    def __init__(self, model: str = "llama3.2"):
        self.model = model
        self.ollama = ollama_client.Client(
            host=os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        )
        print(f"[ResponderAgent] Initialized | model: {self.model}")

    def run(self, state: AgentState) -> AgentState:
        user_message = state["user_message"]
        research = state.get("research", "")
        code_output = state.get("code_output", "")
        critique = state.get("critique", {})
        plan = state.get("plan", {})

        print(f"\n[ResponderAgent] Synthesizing final response...")

        # Build context
        context = self._build_context(user_message, research, code_output, plan, critique)

        try:
            response = self.ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": RESPONDER_PROMPT},
                    {"role": "user", "content": context},
                ],
            )
            final_response = response["message"]["content"].strip()
        except Exception as e:
            print(f"[ResponderAgent] Generation failed: {e}")
            final_response = self._fallback_response(research, code_output, user_message)

        print(f"[ResponderAgent] ✓ Response ({len(final_response)} chars): {final_response[:200]}")

        return {
            **state,
            "final_response": final_response,
            "current_agent": "responder",
        }

    def _build_context(
        self,
        user_message: str,
        research: str,
        code_output: str,
        plan: dict,
        critique: dict,
    ) -> str:
        # Simple tasks — answer directly, no need to synthesize
        if plan.get("task_type") == "simple":
            return f"User request: {user_message}\nAnswer this directly and conversationally."

        context = f"User's original request: {user_message}\n\n"

        if research:
            context += f"Research findings:\n{research}\n\n"

        if code_output:
            context += f"Code execution results:\n{code_output}\n\n"

        if critique.get("feedback") and critique.get("approved") is False:
            context += f"Quality notes to incorporate: {critique['feedback']}\n\n"

        if not research and not code_output:
            context += "No research or code was needed. Answer directly from your knowledge.\n"

        context += "Now write the final response to the user."
        return context

    def _fallback_response(self, research: str, code_output: str, user_message: str) -> str:
        """Simple fallback if LLM call fails."""
        parts = [f"Here's what I found for: {user_message}\n"]
        if research:
            parts.append(f"**Research:**\n{research[:500]}")
        if code_output:
            parts.append(f"**Code Output:**\n{code_output[:500]}")
        if not research and not code_output:
            parts.append("I wasn't able to generate a response. Please try again.")
        return "\n\n".join(parts)