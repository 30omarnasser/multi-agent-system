```markdown
# 🏗️ System Architecture

## Overview

A production-grade autonomous multi-agent AI system where 5 specialized agents collaborate to solve complex tasks. The system runs fully locally via Ollama — no external API keys required except Tavily for web search. Built with LangGraph for orchestration, FastAPI for the API layer, and a 5-layer memory architecture backed by Redis and PostgreSQL with pgvector.

---

## Agent Pipeline

```
                        ┌─────────────────────────────────────────┐
                        │           User Request                  │
                        └─────────────────┬───────────────────────┘
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │        Planner        │
                              │  Analyzes task type   │
                              │  Generates sub-tasks  │
                              │  Routes to agents     │
                              └───────────┬───────────┘
                                          │
              ┌───────────────────────────┼────────────────────────┐
              │                           │                        │
           simple                     research                   code
              │                           │                        │
              ▼                           ▼                        ▼
         Responder              ┌──────────────────┐         ┌──────────┐
                                │   Researcher     │         │  Coder   │
                                │  Web search      │         │  Writes  │
                                │  RAG retrieval   │         │  Python  │
                                │  Summarizes      │         │  Runs in │
                                └────────┬─────────┘         │  sandbox │
                                         │                   └────┬─────┘
                                   needs_code?                    │
                                         │ yes                    │
                                         ▼                        │
                                    ┌──────────┐                  │
                                    │  Coder   │◄─────────────────┘
                                    └────┬─────┘
                                         │
                                         ▼
                              ┌───────────────────────┐
                              │        Critic         │
                              │  Scores 0-10          │
                              │  Approves or rejects  │
                              │  Max 2 revisions      │
                              └───────────┬───────────┘
                                          │
                              approved or max revisions
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │       Responder       │
                              │  Synthesizes all      │
                              │  Personalizes output  │
                              │  Uses profile context │
                              │  Uses episode context │
                              └───────────┬───────────┘
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │    save_episode_node  │
                              │  Saves to episodes    │
                              │  table in Postgres    │
                              └───────────┬───────────┘
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │  update_profile_node  │
                              │  Extracts user info   │
                              │  Updates profile DB   │
                              └───────────┬───────────┘
                                          │
                                          ▼
                                        END
```

---

## Memory Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Memory Layers                               │
│                                                                     │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────────────┐   │
│  │    Redis     │  │  PostgreSQL   │  │     PostgreSQL        │   │
│  │              │  │  + pgvector   │  │     + pgvector        │   │
│  │  Short-term  │  │  Long-term    │  │     Episodic          │   │
│  │  Session     │  │  Facts        │  │     Episodes          │   │
│  │  Memory      │  │               │  │                       │   │
│  │  TTL: 1hr    │  │  Semantic     │  │  Cross-session        │   │
│  │  Per session │  │  search       │  │  recall               │   │
│  │  Key: list   │  │  768-dim vecs │  │  Summarized by LLM    │   │
│  └──────────────┘  └───────────────┘  └───────────────────────┘   │
│                                                                     │
│  ┌──────────────────────┐  ┌──────────────────────────────────┐   │
│  │     PostgreSQL       │  │          PostgreSQL              │   │
│  │     + pgvector       │  │                                  │   │
│  │     Documents        │  │          User Profiles           │   │
│  │     (RAG)            │  │                                  │   │
│  │                      │  │  Auto-learned from convos        │   │
│  │  PDF → chunks        │  │  name, expertise, interests      │   │
│  │  Hybrid search       │  │  communication style             │   │
│  │  Vector + keyword    │  │  interaction count               │   │
│  └──────────────────────┘  └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## RAG Pipeline

```
PDF File
    │
    ▼
┌─────────────────┐
│  Text Extractor │  pypdf — extracts text page by page
│  (pypdf)        │  labels each page [Page N]
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Text Chunker   │  chunk_size=500 chars, overlap=50
│                 │  sentence-aware — never cuts mid-sentence
│                 │  returns Chunk objects with metadata
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Embedder       │  Ollama nomic-embed-text (local)
│  (Ollama)       │  768-dimensional vectors
│                 │  batch embedding for efficiency
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PostgreSQL     │  document_chunks table
│  + pgvector     │  ivfflat index for fast ANN search
│                 │  full-text index for keyword search
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│              Hybrid Retriever               │
│                                             │
│  Vector search (cosine similarity)          │
│       +                                     │
│  Keyword search (PostgreSQL full-text)      │
│       +                                     │
│  RRF Fusion (Reciprocal Rank Fusion)        │
│                                             │
│  Returns top-k most relevant chunks         │
└─────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| LLM | Ollama llama3.1:8b | All agent reasoning (local) |
| Embeddings | Ollama nomic-embed-text | Vector embeddings (local) |
| Orchestration | LangGraph 0.1.5 | Agent graph + state machine |
| API Framework | FastAPI + Uvicorn | REST API + auto docs |
| Short-term memory | Redis 7 | Session conversation history |
| Long-term memory | PostgreSQL 15 + pgvector | Facts, episodes, docs, profiles |
| Web Search | Tavily API | Real-time web search for Researcher |
| Code Execution | Python subprocess | Sandboxed code runner (10s timeout) |
| Containerization | Docker + Docker Compose | Full local stack |

---

## Database Schema

```sql
-- Long-term facts (semantic search)
CREATE TABLE facts (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    fact TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    embedding vector(768),
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Episodic memory (past sessions)
CREATE TABLE episodes (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    key_topics TEXT[] DEFAULT '{}',
    outcome TEXT DEFAULT '',
    embedding vector(768),
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Document chunks (RAG knowledge base)
CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding vector(768),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- User profiles (personalization)
CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    name TEXT DEFAULT '',
    expertise_level TEXT DEFAULT 'unknown',
    communication_style TEXT DEFAULT 'neutral',
    interests TEXT[] DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    interaction_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    raw_notes TEXT DEFAULT ''
);
```

---

## API Endpoints

### Core
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | System status + version |
| GET | `/health` | Redis + Postgres + Ollama health |
| POST | `/chat` | Single agent chat (Week 1) |
| POST | `/multi-agent` | Full 5-agent pipeline |

### Memory — Short-term
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/history/{session_id}` | Conversation history |
| DELETE | `/history/{session_id}` | Clear session |
| GET | `/sessions` | List active sessions |

### Memory — Long-term Facts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/facts` | All facts (filterable by session) |
| POST | `/facts` | Manually save a fact |
| GET | `/facts/search` | Semantic fact search |
| DELETE | `/facts/{session_id}` | Clear facts for session |

### Memory — Episodic
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/episodes` | All episodes |
| GET | `/episodes/search` | Semantic episode search |
| GET | `/episodes/recent` | Most recent episodes |
| DELETE | `/episodes/{episode_id}` | Delete episode |

### Memory — User Profiles
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/profile/{user_id}` | Get user profile |
| PUT | `/profile/{user_id}` | Update profile |
| GET | `/profiles` | List all profiles |
| DELETE | `/profile/{user_id}` | Delete profile |

### RAG — Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload-pdf` | Ingest PDF into knowledge base |
| GET | `/documents` | List ingested documents |
| DELETE | `/documents/{doc_id}` | Delete document + chunks |
| GET | `/search-docs` | Semantic/hybrid doc search |
| GET | `/search-docs/context` | LLM-ready context string |
| GET | `/search-docs/compare` | Compare vector vs keyword vs hybrid |

### Memory Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/memory/stats` | Full memory dashboard |
| POST | `/memory/maintenance` | Run full cleanup |
| POST | `/memory/prune-facts` | Delete old facts |
| POST | `/memory/prune-episodes` | Delete old episodes |
| POST | `/memory/deduplicate-facts` | Remove duplicate facts |
| POST | `/memory/deduplicate-episodes` | Remove near-duplicate episodes |
| GET | `/memory/summarize-facts/{session_id}` | LLM summary of facts |
| GET | `/memory/document-stats` | Per-doc chunk counts |

---

## Project Structure

```
multi-agent-system/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py        ← Single agent (Week 1)
│   ├── models.py            ← Pydantic models
│   ├── state.py             ← AgentState TypedDict
│   ├── planner.py           ← Task decomposition + routing
│   ├── researcher.py        ← Web search + RAG retrieval
│   ├── coder.py             ← Code generation + execution
│   ├── critic.py            ← Quality evaluation
│   ├── responder.py         ← Response synthesis
│   └── graph.py             ← LangGraph pipeline
├── memory/
│   ├── redis_memory.py      ← Short-term session memory
│   ├── postgres_memory.py   ← Long-term fact storage
│   ├── episodic_memory.py   ← Past session episodes
│   ├── user_profile.py      ← User profile learning
│   └── memory_manager.py   ← Pruning + maintenance
├── rag/
│   ├── chunker.py           ← Sentence-aware chunking
│   ├── embedder.py          ← Ollama embeddings
│   ├── ingestion.py         ← PDF ingestion pipeline
│   └── retriever.py         ← Hybrid search
├── tools/
│   ├── base.py              ← Tool dataclass
│   ├── definitions.py       ← calculator, web_search, python_executor
│   └── registry.py          ← Tool registry
├── api/
│   └── main.py              ← FastAPI — 30+ endpoints
├── tests/
│   ├── test_day11.py        ← PDF ingestion tests
│   ├── test_day14.py        ← Episodic memory tests
│   ├── test_day15.py        ← User profile tests
│   ├── test_day16.py        ← Memory management tests
│   └── test_week3.py        ← Full regression suite
├── docs/
│   └── architecture.md      ← This file
├── .env                     ← Secrets (never commit)
├── .env.example             ← Template for new developers
├── docker-compose.yml       ← Full local stack
├── Dockerfile               ← API container
├── requirements.txt         ← Python dependencies
└── README.md                ← Project documentation
```

---

## LangGraph State

```python
class AgentState(TypedDict):
    user_message: str        # Original user request
    plan: dict               # Planner output
    research: str            # Researcher findings
    code_output: str         # Coder results
    critique: dict           # Critic evaluation
    revision_count: int      # Revision loop counter
    final_response: str      # Final answer
    current_agent: str       # Currently active agent
    session_id: str          # Conversation session
    user_id: str             # User for profile lookup
    search_queries: list     # Planner-generated search queries
    code_requirements: list  # Planner-generated code requirements
    doc_context: str         # RAG context from documents
    episode_context: str     # Past session context
    profile_context: str     # User profile context
```

---

## Key Design Decisions

| Decision | Reason |
|----------|--------|
| Ollama for LLM | No API costs, no rate limits, runs offline |
| Ollama for embeddings | Consistent with LLM stack, no extra services |
| pgvector in Postgres | One DB for everything — facts, episodes, docs, profiles |
| LangGraph StateGraph | Clean state machine, easy to extend with new agents |
| Redis for short-term | Fast O(1) reads, TTL auto-cleanup, no manual expiry |
| Hybrid search (RRF) | Better than pure vector — handles exact matches too |
| Sentence-aware chunking | Never cuts mid-sentence, preserves meaning |
| Critic revision loop | Self-improving — max 2 retries prevents infinite loops |
| Overlap in chunks | 50-char overlap ensures context at boundaries |
| `save_episode_node` in graph | Episode saved inside pipeline — guaranteed execution |

---

## Running Locally

```bash
# Pull models
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# Start stack
docker compose up --build

# Run all tests
python tests/test_week3.py

# API docs
open http://localhost:8000/docs
```
```