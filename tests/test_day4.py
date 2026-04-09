import sys, os, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.registry import ToolRegistry
from tools.definitions import calculator_tool, web_search_tool, python_executor_tool
from agents.base_agent import BaseAgent

MODEL = "gemini-2.0-flash"

CURRENT_DATE_CONTEXT = (
    "Today's date is April 2026. "
    "ALWAYS use your tools when asked — never refuse to search or run code. "
    "Never say you cannot access the internet or that a date is in the future."
)


def test_real_web_search():
    registry = ToolRegistry()
    registry.register(web_search_tool)
    agent = BaseAgent(
        name="SearchAgent",
        system_prompt=(
            f"You are a research assistant. {CURRENT_DATE_CONTEXT} "
            "When the user asks you to search for anything, ALWAYS call the web_search tool immediately."
        ),
        model=MODEL,
        registry=registry,
    )
    print("\n--- Test 1: Real web search ---")
    r = agent.run("Search the web for: LangGraph latest features and updates")
    print(f"Response: {r.content[:500]}")
    print(f"Tools used: {[t.tool_name for t in r.tool_calls]}")
    assert "web_search" in [t.tool_name for t in r.tool_calls], \
        f"Expected web_search to be called. Tools used: {[t.tool_name for t in r.tool_calls]}"
    assert r.tool_calls[0].result and "[STUB]" not in r.tool_calls[0].result, \
        "web_search returned a stub result — check TAVILY_API_KEY in .env"
    print("✅ Real web search working!")


def test_python_executor():
    registry = ToolRegistry()
    registry.register(python_executor_tool)
    agent = BaseAgent(
        name="CoderAgent",
        system_prompt=(
            f"You are a coding assistant. {CURRENT_DATE_CONTEXT} "
            "When asked to write or run code, ALWAYS use the python_executor tool. "
            "Never just show code without running it."
        ),
        model=MODEL,
        registry=registry,
    )

    print("\n--- Test 2: Python executor - fibonacci ---")
    r = agent.run("Use python_executor to run code that computes and prints the first 10 Fibonacci numbers.")
    print(f"Response: {r.content}")
    print(f"Tools used: {[t.tool_name for t in r.tool_calls]}")
    assert "python_executor" in [t.tool_name for t in r.tool_calls], \
        "Expected python_executor to be called for fibonacci"

    time.sleep(5)

    print("\n--- Test 3: Python executor - data processing ---")
    r = agent.run(
        "Use python_executor to run code that calculates the mean and standard deviation "
        "of this list: [12, 45, 7, 23, 89, 34, 56, 11]. Print both results."
    )
    print(f"Response: {r.content}")
    print(f"Tools used: {[t.tool_name for t in r.tool_calls]}")
    assert "python_executor" in [t.tool_name for t in r.tool_calls], \
        "Expected python_executor to be called for stats"
    print("✅ Python executor working!")


def test_combined_tools():
    registry = ToolRegistry()
    registry.register(web_search_tool)
    registry.register(python_executor_tool)
    registry.register(calculator_tool)
    agent = BaseAgent(
        name="FullAgent",
        system_prompt=(
            f"You are a powerful assistant with web search and code execution abilities. {CURRENT_DATE_CONTEXT} "
            "For tasks involving current data, use web_search first, then use python_executor to process the results. "
            "Always use tools — never guess at current prices or live data."
        ),
        model=MODEL,
        registry=registry,
    )

    print("\n--- Test 4: Combined tools ---")
    r = agent.run(
        "Use web_search to find the current price of Bitcoin, "
        "then use python_executor to calculate how many BTC you could buy with $10,000."
    )
    print(f"Response: {r.content}")
    tools_used = [t.tool_name for t in r.tool_calls]
    print(f"Tools used: {tools_used}")
    assert "web_search" in tools_used, "Expected web_search to be called"
    assert "python_executor" in tools_used, "Expected python_executor to be called"
    print("✅ Combined tools test done!")


if __name__ == "__main__":
    test_real_web_search()
    print("\n⏳ Waiting 10s between tests to avoid rate limits...")
    time.sleep(10)

    test_python_executor()
    print("\n⏳ Waiting 10s between tests to avoid rate limits...")
    time.sleep(10)

    test_combined_tools()
    print("\n🎉 All Day 4 tests passed!")