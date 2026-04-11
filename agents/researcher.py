import os
import ollama as ollama_client
from agents.state import AgentState
from tools.definitions import web_search_tool

RESEARCHER_PROMPT = """You are a Researcher agent in a multi-agent AI system.
Your job is to gather accurate, current information from multiple sources and synthesize it.
You have access to two information sources:
1. An internal knowledge base of uploaded documents (highly trusted)
2. Web search results (current but may vary in quality)

Rules:
- Prioritize document knowledge base results when available
- Use web search to fill gaps or get current information
- Clearly distinguish between document sources and web sources
- Be factual, organized, and cite which source supports each claim
- Today's date is April 2026."""

SYNTHESIS_PROMPT = """You are synthesizing research from multiple sources.
Given the document context and web search results, write a comprehensive research summary.
Structure your response clearly. Cite sources inline like [Doc] or [Web].
Be concise but complete. No repetition."""


class ResearcherAgent:

    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model
        self.ollama = ollama_client.Client(
            host=os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        )
        self.retriever = None
        self._init_retriever()
        print(f"[ResearcherAgent] Initialized | model: {self.model}")

    def _init_retriever(self):
        """Initialize RAG retriever — fail gracefully if DB not ready."""
        try:
            from rag.retriever import DocumentRetriever
            self.retriever = DocumentRetriever()
            print("[ResearcherAgent] RAG retriever connected.")
        except Exception as e:
            print(f"[ResearcherAgent] RAG retriever unavailable (non-critical): {e}")
            self.retriever = None

    # ─── Core Run ─────────────────────────────────────────────

    def run(self, state: AgentState) -> AgentState:
        user_message = state["user_message"]
        search_queries = state.get("search_queries", [])
        plan = state.get("plan", {})

        print(f"\n[ResearcherAgent] Researching: '{user_message[:100]}'")

        # Resolve search queries from planner or fallback
        if not search_queries:
            subtasks = plan.get("subtasks", [])
            if subtasks:
                first = subtasks[0]
                search_queries = [
                    first.get("description", user_message)
                    if isinstance(first, dict) else first
                ]
            else:
                search_queries = [user_message]

        print(f"[ResearcherAgent] Queries: {search_queries}")

        # ── Source 1: RAG document search ─────────────────────
        doc_context = self._search_documents(user_message, search_queries)

        # ── Source 2: Web search ───────────────────────────────
        web_context = self._search_web(search_queries)

        # ── Synthesize both sources ────────────────────────────
        research_summary = self._synthesize(
            user_message=user_message,
            doc_context=doc_context,
            web_context=web_context,
        )

        print(
            f"[ResearcherAgent] Summary ({len(research_summary)} chars): "
            f"{research_summary[:200]}"
        )

        return {
            **state,
            "research": research_summary,
            "current_agent": "researcher",
        }

    # ─── RAG Document Search ──────────────────────────────────

    def _search_documents(self, user_message: str, queries: list[str]) -> str:
        """Search ingested documents using hybrid RAG search."""
        if not self.retriever:
            return ""

        try:
            # Use the primary query for RAG search
            primary_query = queries[0] if queries else user_message

            results = self.retriever.search(
                query=primary_query,
                top_k=4,
                threshold=0.2,
                mode="hybrid",
            )

            # Also search with user message if different from primary query
            if user_message.lower() != primary_query.lower() and len(queries) > 1:
                extra = self.retriever.search(
                    query=user_message,
                    top_k=3,
                    threshold=0.2,
                    mode="hybrid",
                )
                # Merge — deduplicate by chunk id
                existing_ids = {r["id"] for r in results}
                for r in extra:
                    if r["id"] not in existing_ids:
                        results.append(r)
                        existing_ids.add(r["id"])

            if not results:
                print("[ResearcherAgent] No relevant docs found in knowledge base.")
                return ""

            doc_context = self.retriever.format_context(results)
            print(
                f"[ResearcherAgent] 📚 Found {len(results)} doc chunks: "
                f"{doc_context[:150]}"
            )
            return doc_context

        except Exception as e:
            print(f"[ResearcherAgent] Doc search failed (non-critical): {e}")
            return ""

    # ─── Web Search ───────────────────────────────────────────

    def _search_web(self, queries: list[str]) -> str:
        """Run Tavily web searches for all queries."""
        all_results = []

        for query in queries[:3]:  # cap at 3 web searches
            try:
                result = web_search_tool.run(query=query)
                all_results.append(f"[Web Query: {query}]\n{result}")
                print(f"[ResearcherAgent] 🌐 Web searched: '{query}'")
            except Exception as e:
                print(f"[ResearcherAgent] Web search failed for '{query}': {e}")

        return "\n\n---\n\n".join(all_results) if all_results else ""

    # ─── Synthesis ────────────────────────────────────────────

    def _synthesize(
        self,
        user_message: str,
        doc_context: str,
        web_context: str,
    ) -> str:
        """Combine doc + web results into a coherent research summary."""

        # Build the context block
        context_parts = []

        if doc_context:
            context_parts.append(
                f"=== KNOWLEDGE BASE (uploaded documents) ===\n{doc_context}"
            )
        if web_context:
            context_parts.append(
                f"=== WEB SEARCH RESULTS ===\n{web_context}"
            )

        if not context_parts:
            # Nothing found anywhere — tell the LLM to answer from training
            context_parts.append(
                "No external sources found. Answer from your training knowledge."
            )

        combined = "\n\n".join(context_parts)

        # Source summary for logging
        sources = []
        if doc_context:
            sources.append("knowledge base")
        if web_context:
            sources.append("web")
        print(f"[ResearcherAgent] Synthesizing from: {', '.join(sources) or 'training only'}")

        try:
            response = self.ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": RESEARCHER_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"User request: {user_message}\n\n"
                            f"{combined}\n\n"
                            f"Write a comprehensive, well-structured research summary."
                        ),
                    },
                ],
            )
            return response["message"]["content"].strip()

        except Exception as e:
            print(f"[ResearcherAgent] Synthesis failed: {e}")
            # Return raw context as fallback
            return combined[:2000]