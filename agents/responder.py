import os
import ollama as ollama_client
from agents.state import AgentState

RESPONDER_PROMPT = """You are a Responder agent in a multi-agent AI system.
Your job is to synthesize all the work done by other agents into a clear,
helpful, and well-formatted final response for the user.
Be conversational, clear, and complete. Do not mention the internal agents."""


class ResponderAgent:

    def __init__(self, model: str = "llama3.1:8b"):
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

        print(f"\n[ResponderAgent] Composing final response")

        context = f"User request: {user_message}\n\n"
        if research:
            context += f"Research findings:\n{research}\n\n"
        if code_output:
            context += f"Code results:\n{code_output}\n\n"
        if critique.get("feedback"):
            context += f"Quality notes: {critique['feedback']}\n\n"

        # For simple tasks — just answer directly
        if plan.get("task_type") == "simple":
            context = f"User request: {user_message}\nAnswer this directly and conversationally."

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
            final_response = research or code_output or f"Error composing response: {e}"

        print(f"[ResponderAgent] Final response: {final_response[:200]}")

        return {
            **state,
            "final_response": final_response,
            "current_agent": "responder",
        }