# 🤖 Multi-Agent AI System

A production-grade autonomous multi-agent AI system built from scratch.
Specialized agents collaborate to solve complex tasks with full memory,
tool use, and a real API — engineered properly, not hacked together.

> **CV Project** | Target: AI Engineer roles | Stack: Python · Ollama · FastAPI · Redis · PostgreSQL · Docker

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        FastAPI                          │
│         /chat  /facts  /history  /sessions  /health     │
└──────────────────────┬──────────────────────────────────┘
                       │
              ┌────────▼────────┐
              │   BaseAgent     │
              │  ReAct Loop     │
              │  Tool Routing   │
              └──┬──────────┬───┘
                 │          │
        ┌────────▼───┐  ┌───▼──────────┐
        │  Tools     │  │   Memory     │
        │ calculator │  │ Redis (STM)  │
        │ web_search │  │ Postgres+    │
        │ python_exec│  │ pgvector(LTM)│
        └────────────┘  └──────────────┘
                 │
        ┌────────▼───────┐
        │  Ollama (local)│
        │  llama3.1:8b   │
        │  nomic-embed   │
        └────────────────┘
```

---

## Features

- **Local LLM** — Runs entirely on your machine via Ollama. No OpenAI API costs.
- **Tool Use** — Calculator, real web search (Tavily), sandboxed Python executor
- **Short-term Memory** — Redis-backed conversation history per session with TTL
- **Long-term Memory** — PostgreSQL + pgvector semantic fact storage with embeddings
- **Fact Extraction** — Agent automatically extracts and stores important facts from conversations
- **Semantic Search** — Search stored facts by meaning, not just keywords
- **Session Management** — Multiple isolated sessions with full history API
- **Production Ready** — Docker Compose, health checks, retry logic, error handling

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Ollama — `llama3.1:8b` |
| Embeddings | Ollama — `nomic-embed-text` |
| API | FastAPI + Uvicorn |
| Short-term Memory | Redis 7 |
| Long-term Memory | PostgreSQL 15 + pgvector |
| Web Search | Tavily API |
| Containerization | Docker + Docker Compose |
| Testing | Python `requests` + assertions |
| OS | Windows 11 |

---

## Project Structure

```
multi-agent-system/
├── agents/
│   ├── base_agent.py      ← ReAct loop, tool routing, memory integration
│   └── models.py          ← Pydantic models: Message, AgentResponse, ToolCall
├── api/
│   └── main.py            ← FastAPI endpoints
├── memory/
│   ├── redis_memory.py    ← Short-term session memory
│   └── postgres_memory.py ← Long-term semantic fact memory
├── tools/
│   ├── base.py            ← Tool dataclass
│   ├── registry.py        ← ToolRegistry
│   └── definitions.py     ← calculator, web_search, python_executor
├── tests/
│   ├── test_day3.py
│   ├── test_day4.py
│   └── test_day7.py       ← Full end-to-end test suite
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env
```

---

## Quick Start

### Prerequisites
- Docker Desktop
- Ollama installed on Windows ([ollama.com](https://ollama.com))
- Tavily API key ([tavily.com](https://tavily.com))

### 1 — Pull models
```powershell
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

### 2 — Configure environment
```env
# .env
GEMINI_API_KEY=your_key
TAVILY_API_KEY=your_key
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=agent_user
POSTGRES_PASSWORD=agent_pass
POSTGRES_DB=agent_db
REDIS_HOST=redis
REDIS_PORT=6379
OLLAMA_HOST=http://host.docker.internal:11434
APP_ENV=development
```

### 3 — Start the system
```powershell
docker compose up -d
```

### 4 — Test it
```powershell
python tests/test_day7.py
```

### 5 — Explore the API
Open **http://localhost:8000/docs** in your browser.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Send a message to the agent |
| `GET` | `/health` | Check all service statuses |
| `GET` | `/history/{session_id}` | Get conversation history |
| `DELETE` | `/history/{session_id}` | Clear a session |
| `GET` | `/sessions` | List all active sessions |
| `GET` | `/facts` | Get all stored facts |
| `POST` | `/facts` | Manually save a fact |
| `GET` | `/facts/search?query=...` | Semantic search over facts |
| `DELETE` | `/facts/{session_id}` | Clear facts for a session |

### Example — Chat
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "My name is Omar", "session_id": "my_session"}'
```

### Example — Search Facts
```bash
curl "http://localhost:8000/facts/search?query=programming+language&session_id=my_session"
```

---

## Memory Architecture

```
Every conversation turn:

User message
    │
    ├──► Redis (short-term)
    │    └── Full conversation history
    │        TTL: 1 hour per session
    │
    ├──► pgvector (long-term)
    │    └── Important facts extracted by LLM
    │        Embedded with nomic-embed-text
    │        Persist forever
    │
    └──► Recalled on next turn
         Short-term: full history injected
         Long-term: top-5 relevant facts injected
```
## Week 4 — UI, Evaluation & Control

### Streamlit UI (`http://localhost:8501`)
A full-featured web interface with:
- **Chat tab** — real-time chat with agent pipeline visualization
- **Memory tab** — explore facts, episodes, profiles, run maintenance
- **Documents tab** — upload PDFs, search knowledge base
- **About tab** — system architecture and API links

### Agent Trace Viewer
Every pipeline response includes:
- Which agents ran and in what order
- Critique score (0-10)
- Whether a revision loop was triggered
- Full task plan with subtasks, search queries, code requirements

### Evaluation Framework
Automatic scoring of every pipeline run:
- Tracks accuracy, relevance, completeness, efficiency
- Rolling averages across all runs
- Filter by task type, score threshold
- Accessible at `GET /evaluate/summary`

### MLflow Integration
Every pipeline run logged to MLflow:
- Metrics: critique score, duration, agent count
- Parameters: task type, model, HITL enabled
- View at `http://localhost:5000`

### Human-in-the-Loop
Add a pause button to any pipeline run:
```json
POST /multi-agent
{"message": "...", "hitl_enabled": true}
```
- Pipeline pauses before executing high-risk operations
- Approve or reject via API or Streamlit UI
- Rejected tasks get a graceful abort response
- Simple tasks automatically skip the checkpoint
---

## What's Coming (Weeks 2–5)

- **Week 2** — Multi-agent graph: Planner, Researcher, Coder, Critic with LangGraph
- **Week 3** — Full RAG pipeline: PDF ingestion, chunking, hybrid search
- **Week 4** — Streamlit UI, agent trace viewer, evaluation framework
- **Week 5** — CI/CD, cloud deployment, demo video, LinkedIn article

---

## Author

**Omar Nasser** — Embedded Systems student & AI Engineer in training  
GitHub: [github.com/30omarnasser/multi-agent-system](https://github.com/30omarnasser/multi-agent-system)