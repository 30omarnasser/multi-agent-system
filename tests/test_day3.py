import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.registry import ToolRegistry
from tools.definitions import calculator_tool, web_search_tool
from agents.base_agent import BaseAgent


def test_tool_use():
    registry = ToolRegistry()
    registry.register(calculator_tool)
    registry.register(web_search_tool)

    agent = BaseAgent(
        name="TestAgent",
        system_prompt="You are a helpful assistant. Use tools when needed.",
        model="gemini-2.5-flash",
        registry=registry,
    )

    print("\n--- Test 1: Should use calculator ---")
    r = agent.run("What is 2 to the power of 16?")
    print(f"Response: {r.content}")
    print(f"Tools used: {[t.tool_name for t in r.tool_calls]}")
    assert "65536" in r.content.replace(",", "")

    print("\n--- Test 2: Should use web search ---")
    r = agent.run("Search for latest news about LangGraph")
    print(f"Response: {r.content}")
    print(f"Tools used: {[t.tool_name for t in r.tool_calls]}")
    assert "web_search" in [t.tool_name for t in r.tool_calls]

    print("\n--- Test 3: Should answer directly, no tools ---")
    r = agent.run("What is the capital of France?")
    print(f"Response: {r.content}")
    print(f"Tools used: {[t.tool_name for t in r.tool_calls]}")
    assert r.tool_calls == []

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_tool_use()