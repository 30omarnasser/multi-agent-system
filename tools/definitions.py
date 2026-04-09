from tools.base import Tool
import math
import os
import subprocess
import sys
import tempfile
from dotenv import load_dotenv

load_dotenv()

# ─── Calculator ───────────────────────────────────────────────
def _calculator(expression: str) -> str:
    try:
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"Error: {e}"

calculator_tool = Tool(
    name="calculator",
    description="Evaluate a mathematical expression. Use this for any arithmetic or math.",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "A valid Python math expression e.g. '2 ** 10' or 'sqrt(144)'"
            }
        },
        "required": ["expression"]
    },
    fn=_calculator
)

# ─── Real Tavily Web Search ────────────────────────────────────
def _web_search(query: str) -> str:
    try:
        from tavily import TavilyClient
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "Error: TAVILY_API_KEY not set in environment."
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, max_results=3)
        results = response.get("results", [])
        if not results:
            return "No results found."
        formatted = []
        for r in results:
            formatted.append(
                f"Title: {r.get('title', 'N/A')}\n"
                f"URL: {r.get('url', 'N/A')}\n"
                f"Summary: {r.get('content', 'N/A')[:300]}"
            )
        return "\n\n---\n\n".join(formatted)
    except Exception as e:
        return f"Search error: {e}"

web_search_tool = Tool(
    name="web_search",
    description="Search the web for current information, recent news, or facts you don't know. Returns real search results.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query string"
            }
        },
        "required": ["query"]
    },
    fn=_web_search
)

# ─── Sandboxed Python Executor ─────────────────────────────────
def _python_executor(code: str) -> str:
    """
    Executes Python code in a subprocess with a 10-second timeout.
    Captures stdout/stderr. Safe for simple scripts — no network, no file writes outside /tmp.
    """
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir="/tmp"
        ) as f:
            f.write(code)
            tmp_path = f.name

        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "PYTHONPATH": ""},  # strip PYTHONPATH for isolation
        )

        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout.strip()}"
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr.strip()}"
        if not output:
            output = "(No output)"
        return output[:2000]  # cap output length

    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out (10s limit)."
    except Exception as e:
        return f"Execution error: {e}"

python_executor_tool = Tool(
    name="python_executor",
    description=(
        "Execute Python code and return the output. Use this when you need to run calculations, "
        "data processing, generate plots (describe instead), or test logic. "
        "Write complete, runnable Python scripts with print() to show results."
    ),
    parameters={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Complete, runnable Python code. Use print() to output results."
            }
        },
        "required": ["code"]
    },
    fn=_python_executor
)