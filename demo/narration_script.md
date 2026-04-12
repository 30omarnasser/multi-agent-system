# Demo Video Script — Multi-Agent AI System
## Duration: 5-7 minutes

---

### INTRO (30 seconds)

"Hi, I'm Omar. I built a production-grade autonomous multi-agent AI system
from scratch over 5 weeks. Five specialized AI agents collaborate to solve
complex tasks — planning, researching, coding, critiquing, and responding.

Everything runs completely locally with no API keys required except for
web search. Let me show you what it can do."

---

### SCENE 1 — System Overview (45 seconds)

Open browser to http://localhost:8000/docs

"First, the API. Built with FastAPI, it has over 30 endpoints covering
the full agent pipeline, memory management, document search, and more.

Let me check the health of all services."

Click GET /health → Execute

"PostgreSQL, Redis, and Ollama all green. The system is running 5 Docker
containers on my local machine."

Open http://localhost:8501

"And here's the Streamlit UI — a full chat interface showing real-time
agent activity, memory explorer, and document manager."

---

### SCENE 2 — Research Pipeline (90 seconds)

Go to Streamlit UI → Chat tab

"Let me ask something that requires real web search."

Type: "Search for the latest developments in LangGraph and multi-agent
AI frameworks in 2026"

"Watch the pipeline status — the Planner is analyzing the task,
routing to the Researcher agent which is searching the web right now..."

[Wait for response]

"The Researcher searched the web, the Critic scored it 8 out of 10,
and the Responder synthesized everything into this structured answer.

Notice the pipeline visualization — 4 agents ran in sequence automatically."

---

### SCENE 3 — Code Pipeline (90 seconds)

Type: "Write Python code to find all prime numbers up to 1000 and
calculate their sum"

"This time the Planner routes to the Coder agent..."

[Wait for response]

"The Coder wrote the Python, executed it in a sandboxed environment,
got the output, the Critic reviewed it and gave it a 9 out of 10.

The code ran live — you can see the actual output right there in the response."

---

### SCENE 4 — Document Q&A (60 seconds)

Click Documents tab

"Now let me show the RAG pipeline. I'll upload a PDF..."

Upload any PDF

"The system chunks it, embeds it with Ollama's embedding model, and
stores it in PostgreSQL with pgvector for semantic search."

Go back to Chat

Type: "What are the main topics covered in the document I just uploaded?"

"The Researcher agent now searches my document knowledge base first
before going to the web. It found relevant chunks using hybrid
vector and keyword search."

---

### SCENE 5 — Memory System (45 seconds)

Click Memory tab

"The system has 5 memory layers. Here you can see facts automatically
extracted from our conversation, past session episodes summarized by
the LLM, and my user profile that the system learned automatically —
it already knows I'm technical and interested in AI."

Click Dashboard

"Over 30 facts stored, multiple episodes, one profile. The memory
manager can prune and deduplicate automatically."

---

### SCENE 6 — Human-in-the-Loop (30 seconds)

Go back to Chat, toggle on HITL

Type: "Write Python code to process files in a directory"

"With human-in-the-loop enabled, the system pauses before executing
high-risk operations and asks for approval."

[Show approval panel appearing]

"I can approve with feedback, or reject with a reason. This is critical
for production AI systems."

Click Approve

---

### OUTRO (30 seconds)

"In 5 weeks I built a system with:
- 5 specialized agents with self-correction loops
- 5-layer memory architecture
- Full RAG pipeline with hybrid search
- Human-in-the-loop control
- MLflow evaluation tracking
- GitHub Actions CI/CD
- Production Docker setup

Everything in the GitHub repo — link in the description.
The full technical article is on LinkedIn."

---

## Recording Checklist

Before recording:
- [ ] All Docker containers running
- [ ] Ollama running with llama3.1:8b and nomic-embed-text
- [ ] Browser open at localhost:8501 and localhost:8000/docs
- [ ] Screen recording software ready (OBS, Loom, or Windows Game Bar Win+G)
- [ ] Microphone tested
- [ ] Close Slack, notifications off
- [ ] Run docker compose logs api to confirm no errors

Recording order:
1. Record full demo in one take if possible
2. If you make a mistake — keep going, edit later
3. Aim for 5-6 minutes total

After recording:
- [ ] Trim beginning and end
- [ ] Add simple title card: "Autonomous Multi-Agent AI System"
- [ ] Upload to YouTube (unlisted or public)
- [ ] Copy URL for LinkedIn article