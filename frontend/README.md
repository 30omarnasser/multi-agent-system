# NEXUS — Multi-Agent AI Frontend

A production-grade React frontend for the Autonomous Multi-Agent AI System.

## Design

- **Aesthetic**: Deep navy dark theme — professional, technical, refined
- **Typography**: Syne (display) + Instrument Sans (body) + JetBrains Mono (code)
- **Color palette**: Deep navy backgrounds, electric blue accents, cyan highlights

## Pages

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/` | System health, agent overview, memory stats |
| Chat | `/chat` | Multi-agent pipeline chat with pipeline trace |
| Memory | `/memory` | Browse facts, episodes, user profiles |
| Documents | `/documents` | Upload PDFs, search knowledge base |

## Features

- **Real-time pipeline visualization** — see which agents ran and their scores
- **HITL toggle** — enable human-in-the-loop approval from the chat UI
- **Semantic fact search** — search long-term memory with natural language
- **Hybrid document search** — vector + keyword + RRF fusion
- **Service health monitoring** — live status dots in the sidebar
- **Responsive markdown rendering** — code blocks, tables, lists

## Quick Start

```bash
# 1. Install
npm install

# 2. Make sure your API is running
# http://localhost:8000

# 3. Start
npm start

# 4. Open
# http://localhost:3000
```

## Environment

```env
REACT_APP_API_URL=http://localhost:8000
```

Change this to point to your deployed API.

## Build for production

```bash
npm run build
# Output in /build — serve with any static file server
```
