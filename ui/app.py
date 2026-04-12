import streamlit as st
import requests
import os
from ui.components.traces import render_trace_viewer
from ui.components.evaluation import render_evaluation_dashboard
from ui.components.mlflow_panel import render_mlflow_panel

API_URL = os.getenv("API_URL", "http://localhost:8000")

# ─── Page Config ──────────────────────────────────────────────

st.set_page_config(
    page_title="Multi-Agent AI System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d1b69 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .status-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 2px;
    }
    .status-ok {
        background: #065f46;
        color: #6ee7b7;
        border: 1px solid #059669;
    }
    .status-error {
        background: #7f1d1d;
        color: #fca5a5;
        border: 1px solid #dc2626;
    }
    .stChatMessage {
        border-radius: 12px;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #374151;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ─── Imports ──────────────────────────────────────────────────

from ui.components.chat import render_chat_sidebar, render_chat_interface
from ui.components.memory import render_memory_explorer
from ui.components.documents import render_documents_panel

# ─── Header ───────────────────────────────────────────────────

def render_header():
    st.markdown("""
    <div class="main-header">
        <h1 style="margin:0; font-size:1.8rem;">🤖 Autonomous Multi-Agent AI System</h1>
        <p style="margin:0.3rem 0 0 0; opacity:0.8; font-size:0.9rem;">
            5 specialized agents • LangGraph orchestration • Full local stack
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_status_bar():
    """Show live service health in the header."""
    try:
        r = requests.get(f"{API_URL}/health", timeout=3)
        if r.status_code == 200:
            health = r.json()
            cols = st.columns(5)
            services = [
                ("API", health.get("api")),
                ("Redis", health.get("redis")),
                ("Postgres", health.get("postgres")),
                ("Ollama", health.get("ollama")),
            ]
            for i, (name, status) in enumerate(services):
                with cols[i]:
                    is_ok = status == "ok"
                    css_class = "status-ok" if is_ok else "status-error"
                    icon = "●" if is_ok else "●"
                    st.markdown(
                        f'<span class="status-badge {css_class}">{icon} {name}</span>',
                        unsafe_allow_html=True,
                    )
        else:
            st.error("⚠️ API not responding")
    except Exception:
        st.error("⚠️ Cannot connect to API at " + API_URL)


# ─── Navigation ───────────────────────────────────────────────

def render_navigation():
    return st.tabs([
        "💬 Chat",
        "🔍 Traces",
        "📊 Evaluation",
        "🧪 MLflow",          # ← NEW
        "🧠 Memory",
        "📄 Documents",
        "ℹ️ About",
    ])


# ─── About Tab ────────────────────────────────────────────────

def render_about():
    st.markdown("## About This System")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
### 🤖 Agent Pipeline
1. **Planner** — analyzes task, decides which agents to use
2. **Researcher** — searches web + knowledge base
3. **Coder** — writes and executes Python code
4. **Critic** — scores output (0-10), triggers revision if needed
5. **Responder** — synthesizes polished final answer

### 🧠 Memory System
- **Redis** — short-term session memory (1hr TTL)
- **PostgreSQL + pgvector** — long-term facts with semantic search
- **Episodic** — past session summaries with cross-session recall
- **User Profiles** — auto-learned preferences and expertise
        """)

    with col2:
        st.markdown("""
### 📚 RAG Pipeline
- Upload any PDF → auto-chunked with overlap
- Embedded with Ollama nomic-embed-text locally
- Hybrid search: vector similarity + keyword
- Researcher agent uses docs before web search

### ⚙️ Tech Stack
| Layer | Technology |
|-------|-----------|
| LLM | Ollama llama3.1:8b |
| Orchestration | LangGraph |
| API | FastAPI |
| Memory | Redis + PostgreSQL |
| Embeddings | Ollama nomic-embed-text |
| Search | Tavily API |
        """)

    st.markdown("---")
    st.markdown("### 🔗 Quick Links")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"[📖 API Docs]({API_URL}/docs)")
    with col2:
        st.markdown(f"[❤️ Health Check]({API_URL}/health)")
    with col3:
        st.markdown("[💻 GitHub](https://github.com/30omarnasser/multi-agent-system)")


# ─── Main ─────────────────────────────────────────────────────

def main():
    render_header()
    render_status_bar()
    st.markdown("---")

    render_chat_sidebar()
    tabs = render_navigation()

    with tabs[0]:
        render_chat_interface()
    with tabs[1]:
        render_trace_viewer()
    with tabs[2]:
        render_evaluation_dashboard()
    with tabs[3]:
        render_mlflow_panel()          # ← NEW
    with tabs[4]:
        render_memory_explorer()
    with tabs[5]:
        render_documents_panel()
    with tabs[6]:
        render_about()

if __name__ == "__main__":
    main()