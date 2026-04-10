import sys, os, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from memory.postgres_memory import PostgresMemory


def test_save_and_search():
    print("\n--- Test 1: Save and semantic search ---")
    mem = PostgresMemory()
    mem.clear_session_facts("test_day6")

    mem.save_fact("test_day6", "Omar is studying embedded systems at university", "personal")
    mem.save_fact("test_day6", "Omar is building a multi-agent AI system as a CV project", "project")
    mem.save_fact("test_day6", "Omar uses Python and Docker for development", "technical")
    mem.save_fact("test_day6", "Omar's favorite programming language is Python", "preference")

    # Search with a related query
    results = mem.search_facts("What programming does Omar do?", session_id="test_day6")
    print(f"Search results ({len(results)}):")
    for r in results:
        print(f"  [{r['similarity']:.2f}] {r['fact']}")

    assert len(results) > 0, "Should find relevant facts"
    print("✅ Save and search working!")


def test_semantic_similarity():
    print("\n--- Test 2: Semantic similarity (different words, same meaning) ---")
    mem = PostgresMemory()
    mem.clear_session_facts("test_semantic")

    mem.save_fact("test_semantic", "The user prefers dark mode in their IDE", "preference")
    mem.save_fact("test_semantic", "The user drinks coffee every morning", "personal")
    mem.save_fact("test_semantic", "The user works best at night", "personal")

    # Search with different wording
    results = mem.search_facts("What are this person's daily habits?", session_id="test_semantic")
    print(f"Results for 'daily habits':")
    for r in results:
        print(f"  [{r['similarity']:.2f}] {r['fact']}")

    assert len(results) > 0
    print("✅ Semantic similarity working!")


def test_session_isolation():
    print("\n--- Test 3: Facts are isolated by session ---")
    mem = PostgresMemory()
    mem.clear_session_facts("session_a")
    mem.clear_session_facts("session_b")

    mem.save_fact("session_a", "Alice is a data scientist", "personal")
    mem.save_fact("session_b", "Bob is a backend engineer", "personal")

    alice_facts = mem.get_all_facts(session_id="session_a")
    bob_facts = mem.get_all_facts(session_id="session_b")

    assert len(alice_facts) == 1
    assert len(bob_facts) == 1
    assert "Alice" in alice_facts[0]["fact"]
    assert "Bob" in bob_facts[0]["fact"]
    print("✅ Session isolation working!")


def test_fact_count():
    print("\n--- Test 4: Fact counting ---")
    mem = PostgresMemory()
    mem.clear_session_facts("count_test")

    for i in range(5):
        mem.save_fact("count_test", f"Test fact number {i}", "general")

    count = mem.fact_count("count_test")
    assert count == 5, f"Expected 5 facts, got {count}"
    print(f"✅ Fact count correct: {count}")


if __name__ == "__main__":
    test_save_and_search()
    test_semantic_similarity()
    test_session_isolation()
    test_fact_count()
    print("\n🎉 All Day 6 tests passed!")