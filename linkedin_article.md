# I Built a Production-Grade Multi-Agent AI System in 5 Weeks — Here's Everything I Learned

Over the past 5 weeks I built an autonomous multi-agent AI system from scratch.
Not a tutorial. Not a wrapper around an existing product.
A real system — 5 specialized agents, layered memory, RAG pipeline, eval framework,
CI/CD, and a full UI.

Here's what I built, what I learned, and the decisions that mattered.

---

## What the system does

Send it a complex task. Five agents handle it automatically:

1. **Planner** — breaks the task down, decides which agents to involve
2. **Researcher** — searches the web + your document knowledge base
3. **Coder** — writes and executes Python in a sandboxed environment
4. **Critic** — scores the output 0-10, triggers revision if quality is low
5. **Responder** — synthesizes everything into one polished answer

The system doesn't just answer — it self-corrects. If the Critic scores
below 7, the pipeline automatically retries with the feedback. This loop
runs up to 2 times before the Responder synthesizes regardless.

---

## The memory architecture was the hardest part

I initially thought memory was simple. It's not.

The system has 5 distinct memory layers:

**Redis** — short-term session memory. Fast, TTL-based, ephemeral.
Every conversation message is stored here. When Redis expires the session,
it's gone — but that's fine because...

**PostgreSQL + pgvector** — long-term fact storage. After every conversation,
the LLM extracts important facts and stores them as 768-dimensional vectors.
When you ask something new, semantically similar facts are recalled and
injected into the system prompt automatically.

**Episodic memory** — past session summaries. The LLM summarizes entire
conversations into a summary + key_topics + outcome. These are embedded
and stored. Future sessions can recall "what did we talk about last time"
across any number of past sessions.

**User profiles** — auto-learned. After every conversation, the LLM extracts
your name, expertise level, communication style, and interests. These update
the profile automatically. The Responder adapts its tone and depth based on
what it knows about you.

**Document RAG** — the knowledge base. Upload any PDF and it gets chunked
(sentence-aware, 500 chars with 50-char overlap), embedded with
nomic-embed-text, and stored with a full-text index alongside the vector index.
Retrieval uses Reciprocal Rank Fusion — combining vector similarity scores
with keyword match scores for results that are both semantically relevant
and lexically precise.

The key insight: **different memory has different decay rates**. Redis for
what's happening now. PostgreSQL for what matters long-term. Episodic for
narrative continuity. Profiles for personalization that compounds over time.

---

## LangGraph was the right choice for orchestration

I considered building a simple chain. I'm glad I didn't.

LangGraph models agents as nodes in a directed graph with conditional edges.
This means:
- The Planner's output decides which agents run
- The Critic's score decides whether to loop back
- Human-in-the-loop is just another conditional node

Adding human approval was trivial once the graph was set up:

```python
def route_after_planner(state):
    if state["hitl_enabled"] and task_type != "simple":
        return "hitl_checkpoint"
    return task_type_to_agent[task_type]
```

The HITL checkpoint node creates a Redis-backed approval request, polls until
a decision arrives, and either continues or routes to an abort responder.
The pipeline pauses mid-execution. No WebSockets. No complex async. Just Redis
as a simple message broker with a polling loop.

---

## The 5 engineering decisions that made the biggest difference

**1. Ollama instead of cloud APIs**
Running completely locally means no rate limits, no API costs, no internet
dependency. The Ryzen 7 5800X runs llama3.1:8b comfortably. For production
you swap to Gemini with one env var change.

**2. Sentence-aware chunking with overlap**
Naive chunking cuts sentences mid-thought. Sentence-aware splitting respects
natural language boundaries. The 50-character overlap ensures that if a key
piece of information falls at a chunk boundary, it appears in both adjacent
chunks. This measurably improves retrieval quality.

**3. Hybrid search with RRF fusion**
Pure vector search misses exact matches. Pure keyword search misses synonyms.
Reciprocal Rank Fusion combines both rankings:
`rrf_score = 1/(k + vector_rank) + 1/(k + keyword_rank)`
This consistently outperforms either method alone.

**4. Fail-open on timeouts**
If the HITL checkpoint times out waiting for human approval, it auto-approves.
If fact extraction fails, the conversation continues without it. If episode
saving fails, the response still returns. Every non-critical operation is
wrapped in try/except with a safe default. Production systems should never
block on optional features.

**5. Save to Redis BEFORE running the pipeline**
This was a subtle bug that took hours to find. The pipeline's `save_episode_node`
reads from Redis at the end. But the user message isn't in Redis yet when the
pipeline starts — it's only there after the API saves it. Solution: save the
user message to Redis before calling `pipeline.invoke()`, then save the
assistant response after. Order matters.

---

## The tech stack

| Layer | Choice | Reason |
|-------|--------|--------|
| LLM | Ollama llama3.1:8b | Local, free, fast enough |
| Embeddings | nomic-embed-text | 768-dim, runs on CPU, good quality |
| Orchestration | LangGraph | Graph-based, conditional routing |
| API | FastAPI | Fast, auto-docs, pydantic validation |
| Short-term memory | Redis | TTL, O(1) reads, simple |
| Long-term memory | PostgreSQL + pgvector | One DB for everything |
| Web search | Tavily | Structured results, easy SDK |
| Code execution | Python subprocess | Sandboxed, 10s timeout |
| UI | Streamlit | Fast to build, good for demos |
| Tracking | MLflow | Standard in ML, free, local |
| CI | GitHub Actions | Standard, integrates with Docker |
| Containers | Docker + Docker Compose | Reproducible, easy to share |

---

## What I'd do differently

**Use async FastAPI from the start.** The agent pipeline takes 10-40 seconds.
Blocking sync endpoints meant I couldn't run concurrent requests without
multiple workers. Converting to async mid-project is painful.

**Add request IDs earlier.** Tracing a specific request through 5 agents,
3 memory layers, and multiple log sources is hard without a correlation ID
attached from the beginning.

**Start with evaluation.** I built the evaluation framework in Week 4.
If I'd built it in Week 1, every architectural decision would have been
data-driven from day one.

---

## What's next

The system is production-ready locally. The next step is deploying the API
to Render with a cloud Postgres (Supabase) and Redis (Redis Cloud), swapping
Ollama for Gemini API in production while keeping local development on Ollama.

The full source code is on GitHub.
Live demo video in the comments.

If you're building something similar or want to discuss the architecture,
reach out.

---

**Tags:** #AIEngineering #MultiAgent #LangGraph #Python #MachineLearning
#RAG #LLM #Ollama #FastAPI #OpenSource