import sys, os, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from memory.redis_memory import RedisMemory
from agents.base_agent import BaseAgent
from tools.registry import ToolRegistry
from tools.definitions import calculator_tool

def test_redis_memory_basic():
    print("\n--- Test 1: Basic Redis save/load ---")
    mem = RedisMemory(ttl_seconds=300)

    mem.clear_session("test_session")
    mem.save_message("test_session", "user", "Hello!")
    mem.save_message("test_session", "assistant", "Hi! How can I help?")
    mem.save_message("test_session", "user", "What is 2+2?")

    history = mem.get_history("test_session")
    assert len(history) == 3, f"Expected 3 messages, got {len(history)}"
    assert history[0]["content"] == "Hello!"
    assert history[1]["role"] == "assistant"
    print(f"✅ Saved and loaded {len(history)} messages correctly")

def test_session_persistence():
    print("\n--- Test 2: Session persists across agent restarts ---")
    mem = RedisMemory(ttl_seconds=300)

    registry = ToolRegistry()
    registry.register(calculator_tool)

    # First agent instance
    agent1 = BaseAgent(
        name="Agent1",
        system_prompt="You are a helpful assistant.",
        model="gemini-2.0-flash",
        registry=registry,
        memory=mem,
    )
    agent1.run("My name is Omar and I am building a multi-agent system.", session_id="omar_session")
    print("Agent 1 done. Simulating restart...")
    time.sleep(3)

    # Second agent instance — simulates a server restart
    agent2 = BaseAgent(
        name="Agent2",
        system_prompt="You are a helpful assistant.",
        model="gemini-2.0-flash",
        registry=registry,
        memory=mem,
    )
    result = agent2.run("What is my name and what am I building?", session_id="omar_session")
    print(f"Agent 2 response: {result.content}")

    assert "Omar" in result.content or "multi-agent" in result.content.lower(), \
        "Agent should remember the name and project from previous session"
    print("✅ Session persistence working!")

def test_session_isolation():
    print("\n--- Test 3: Sessions are isolated ---")
    mem = RedisMemory(ttl_seconds=300)
    mem.clear_session("user_alice")
    mem.clear_session("user_bob")

    mem.save_message("user_alice", "user", "I love Python")
    mem.save_message("user_bob", "user", "I love JavaScript")

    alice_history = mem.get_history("user_alice")
    bob_history = mem.get_history("user_bob")

    assert alice_history[0]["content"] == "I love Python"
    assert bob_history[0]["content"] == "I love JavaScript"
    assert len(alice_history) == 1
    assert len(bob_history) == 1
    print("✅ Sessions are properly isolated!")

def test_clear_session():
    print("\n--- Test 4: Clear session ---")
    mem = RedisMemory(ttl_seconds=300)
    mem.save_message("temp_session", "user", "Delete me")
    assert mem.session_exists("temp_session")
    mem.clear_session("temp_session")
    assert not mem.session_exists("temp_session")
    print("✅ Session cleared successfully!")

if __name__ == "__main__":
    test_redis_memory_basic()
    test_session_isolation()
    test_clear_session()
    print("\n⏳ Waiting 5s before persistence test (uses Gemini API)...")
    time.sleep(5)
    test_session_persistence()
    print("\n🎉 All Day 5 tests passed!")