import os
import ollama as ollama_client
from agents.state import AgentState
from tools.definitions import web_search_tool

RESEARCHER_PROMPT = """You are a Researcher agent in a multi-agent AI system.
Your job is to gather accurate, current information to answer the user's request.
Use the search results provided to give a comprehensive research summary.
Be factual, concise, and cite what you found.
Today's date is April 2026."""


class ResearcherAgent:

    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model
        self.ollama = ollama_client.Client(
            host=os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        )
        print(f"[ResearcherAgent] Initialized | model: {self.model}")

    def run(self, state: AgentState) -> AgentState:
        plan = state.get("plan", {})
        user_message = state["user_message"]

        print(f"\n[ResearcherAgent] Researching: {user_message[:100]}")

        # Build search query from plan subtasks
        subtasks = plan.get("subtasks", [user_message])
        search_query = subtasks[0] if subtasks else user_message

        # Run web search
        try:
            raw_results = web_search_tool.run(query=search_query)
            print(f"[ResearcherAgent] Search results: {raw_results[:200]}")
        except Exception as e:
            raw_results = f"Search failed: {e}"
            print(f"[ResearcherAgent] Search error: {e}")

        # Summarize findings with LLM
        try:
            response = self.ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": RESEARCHER_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"User request: {user_message}\n\n"
                            f"Search results:\n{raw_results}\n\n"
                            f"Provide a clear research summary."
                        ),
                    },
                ],
            )
            research_summary = response["message"]["content"].strip()
        except Exception as e:
            research_summary = raw_results  # fallback to raw results

        print(f"[ResearcherAgent] Summary: {research_summary[:200]}")

        return {
            **state,
            "research": research_summary,
            "current_agent": "researcher",
        }