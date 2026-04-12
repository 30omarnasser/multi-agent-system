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