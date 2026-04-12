markdown# Deployment Guide

## Architecture
Local Development          Production (Cloud)
─────────────────          ──────────────────
Ollama (local GPU)    →    Gemini API / OpenAI API
Docker Compose        →    Render + Supabase + Redis Cloud
localhost:8000        →    https://your-app.onrender.com
localhost:8501        →    https://your-ui.onrender.com

## Option A — Full Local (Development)

Everything runs on your machine. Best for development.

```bash
# Prerequisites
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# Start
docker compose up -d

# Access
# API:       http://localhost:8000/docs
# UI:        http://localhost:8501
# MLflow:    http://localhost:5000
```

## Option B — Render Cloud (Production)

### Services needed:
- **Render** — API + Streamlit (free tier)
- **Supabase** — PostgreSQL with pgvector (free tier)
- **Redis Cloud** — Redis (free tier, 30MB)
- **Gemini API** — LLM (replaces Ollama, free tier)

### Step 1 — Set up Supabase
1. Go to supabase.com → New project
2. Get connection string from Settings → Database
3. Enable pgvector: SQL Editor → `CREATE EXTENSION vector;`

### Step 2 — Set up Redis Cloud
1. Go to redis.com/try-free
2. Create free database
3. Get host, port, password

### Step 3 — Deploy to Render
1. Go to render.com → New Web Service
2. Connect your GitHub repo
3. Set environment variables (see below)
4. Deploy

### Environment Variables for Render:
```env
POSTGRES_HOST=your-supabase-host
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
POSTGRES_DB=postgres
REDIS_HOST=your-redis-host
REDIS_PORT=your-redis-port
REDIS_PASSWORD=your-redis-password
TAVILY_API_KEY=your-key
OLLAMA_HOST=http://localhost:11434
AGENT_MODEL=gemini-2.0-flash
APP_ENV=production
```