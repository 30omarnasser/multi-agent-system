# Changelog

## [1.0.0] — 2026-04-12

### Week 1 — Core Agent Foundation
- BaseAgent class with Ollama LLM integration
- Tool registry with calculator, web search, Python executor
- Redis short-term memory with session persistence
- PostgreSQL long-term memory with pgvector embeddings
- FastAPI backend with /chat endpoint

### Week 2 — Multi-Agent Architecture
- Planner Agent — task decomposition with confidence scoring
- Researcher Agent — web search + RAG retrieval
- Coder Agent — sandboxed Python execution
- Critic Agent — quality scoring with revision loops
- Responder Agent — context-aware response synthesis
- LangGraph orchestration — conditional routing graph

### Week 3 — Memory & RAG
- PDF ingestion pipeline — chunking, embedding, storage
- Hybrid search — vector + keyword + RRF fusion
- Researcher RAG integration — docs before web
- Episodic memory — cross-session recall
- User profile memory — auto-learned preferences
- Memory management — pruning, deduplication, dashboard

### Week 4 — UI & Evaluation
- Streamlit UI — chat, memory explorer, document manager
- Agent trace viewer — full pipeline visualization
- Evaluation framework — automatic quality scoring
- MLflow integration — metric tracking and experiment logging
- Human-in-the-loop — approval checkpoints with Redis

### Week 5 — Production & Showcase
- Production Docker — health checks, restart policies
- GitHub Actions CI — lint, test, build, security scan
- Cloud deployment guide — Render + Supabase + Redis Cloud
- Demo scenarios — research, code, document Q&A
- v1.0 release