import os
import ollama as ollama_client
from agents.state import AgentState
from tools.definitions import web_search_tool

RESEARCHER_PROMPT = """You are a Researcher agent in a multi-agent AI system.
Your job is to gather accurate, current information to answer the user's request.
Use all the search results provided to give a comprehensive, well-structured summary.
Be factual, cite sources where relevant, and organize findings clearly.
Today's date is April 2026."""


class ResearcherAgent:

    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model
        self.ollama = ollama_client.Client(
            host=os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        )
        print(f"[ResearcherAgent] Initialized | model: {self.model}")

    def run(self, state: AgentState) -> AgentState:
        user_message = state["user_message"]
        search_queries = state.get("search_queries", [])
        plan = state.get("plan", {})

        print(f"\n[ResearcherAgent] Researching: '{user_message[:100]}'")

        # Use planner's search queries if available, else fall back to message
        if not search_queries:
            subtasks = plan.get("subtasks", [])
            if subtasks:
                first = subtasks[0]
                search_queries = [first.get("description", user_message) if isinstance(first, dict) else first]
            else:
                search_queries = [user_message]

        print(f"[ResearcherAgent] Search queries: {search_queries}")

        # Run all search queries and collect results
        all_results = []
        for query in search_queries[:3]:  # cap at 3 searches
            try:
                result = web_search_tool.run(query=query)
                all_results.append(f"Query: {query}\n{result}")
                print(f"[ResearcherAgent] ✓ Searched: '{query}'")
            except Exception as e:
                print(f"[ResearcherAgent] ✗ Search failed for '{query}': {e}")

        combined_results = "\n\n---\n\n".join(all_results) if all_results else "No search results found."

        # Summarize with LLM
        try:
            response = self.ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": RESEARCHER_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"User request: {user_message}\n\n"
                            f"Search results:\n{combined_results}\n\n"
                            f"Provide a clear, well-structured research summary."
                        ),
                    },
                ],
            )
            research_summary = response["message"]["content"].strip()
        except Exception as e:
            print(f"[ResearcherAgent] Summarization failed: {e}")
            research_summary = combined_results

        print(f"[ResearcherAgent] Summary ({len(research_summary)} chars): {research_summary[:200]}")

        return {
            **state,
            "research": research_summary,
            "current_agent": "researcher",
        }