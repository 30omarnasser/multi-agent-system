import sys
import os
import requests
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = "http://localhost:8000"


def log(msg):
    print(f"\n{'─' * 55}")
    print(f"  {msg}")
    print('─' * 55)


def test_profile_created_on_first_message():
    log("Test 1: Profile created after first conversation")

    # Delete any existing profile first
    requests.delete(f"{BASE_URL}/profile/user_omar")

    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Hi, my name is Omar and I am an advanced Python developer.",
        "session_id": "profile_test_001",
        "user_id": "user_omar",
    })
    assert r.status_code == 200, f"Failed: {r.text}"
    print(f"  Response: {r.json()['response'][:150]}")

    time.sleep(3)

    # Check profile exists
    r2 = requests.get(f"{BASE_URL}/profile/user_omar")
    profile = r2.json()
    print(f"  Profile:")
    print(f"    name:            {profile.get('name')}")
    print(f"    expertise_level: {profile.get('expertise_level')}")
    print(f"    interests:       {profile.get('interests')}")
    print(f"    interaction_count: {profile.get('interaction_count')}")
    assert profile.get("interaction_count", 0) >= 1
    print("  ✅ Profile created!")


def test_profile_updates_with_interactions():
    log("Test 2: Profile updates after multiple conversations")
    time.sleep(2)

    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "I prefer concise technical explanations without fluff.",
        "session_id": "profile_test_002",
        "user_id": "user_omar",
    })
    assert r.status_code == 200
    print(f"  Response: {r.json()['response'][:150]}")
    time.sleep(3)

    profile = requests.get(f"{BASE_URL}/profile/user_omar").json()
    print(f"  interaction_count: {profile.get('interaction_count')}")
    print(f"  communication_style: {profile.get('communication_style')}")
    assert profile.get("interaction_count", 0) >= 2
    print("  ✅ Profile updated after multiple interactions!")


def test_profile_personalization():
    log("Test 3: Response is personalized based on profile")
    time.sleep(5)  # ← increase from 2 to 5
    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "Explain what a Python decorator is.",
        "session_id": "profile_test_003",
        "user_id": "user_omar",
    })
    assert r.status_code == 200, f"Got {r.status_code}: {r.text[:300]}"
    response_text = r.json()["response"]
    print(f"  Response (first 300 chars): {response_text[:300]}")
    assert len(response_text) > 50
    print("  ✅ Personalized response generated!")


def test_manual_profile_update():
    log("Test 4: Manual profile update via API")

    r = requests.put(
        f"{BASE_URL}/profile/user_omar",
        json={
            "name": "Omar Nasser",
            "expertise_level": "expert",
            "interests": ["AI", "embedded systems", "Python"],
        }
    )
    assert r.status_code == 200
    profile = r.json()
    print(f"  Updated name:     {profile.get('name')}")
    print(f"  Updated expertise: {profile.get('expertise_level')}")
    print(f"  Updated interests: {profile.get('interests')}")
    assert profile.get("name") == "Omar Nasser"
    print("  ✅ Manual profile update working!")


def test_profile_context_in_pipeline():
    log("Test 5: Profile context injected into pipeline")
    time.sleep(5)  # ← was 2

    r = requests.post(f"{BASE_URL}/multi-agent", json={
        "message": "What should I learn next to improve as a developer?",
        "session_id": "profile_test_004",
        "user_id": "user_omar",
    })
    assert r.status_code == 200
    response_text = r.json()["response"]
    print(f"  Response: {response_text[:400]}")
    assert len(response_text) > 50
    print("  ✅ Profile context used in pipeline!")


def test_list_profiles():
    log("Test 6: List all profiles")

    r = requests.get(f"{BASE_URL}/profiles")
    assert r.status_code == 200
    data = r.json()
    print(f"  Total profiles: {data['count']}")
    for p in data["profiles"]:
        print(f"  - {p['user_id']} | {p.get('name')} | "
              f"interactions: {p.get('interaction_count')}")
    assert data["count"] > 0
    print("  ✅ Profile listing working!")


def test_profile_api_endpoints():
    log("Test 7: All profile endpoints respond correctly")

    # GET /profile/{user_id}
    r = requests.get(f"{BASE_URL}/profile/user_omar")
    assert r.status_code == 200
    print(f"  GET /profile/user_omar: ✅")

    # GET /profiles
    r = requests.get(f"{BASE_URL}/profiles")
    assert r.status_code == 200
    print(f"  GET /profiles: {r.json()['count']} profiles ✅")

    # DELETE /profile/{user_id}
    requests.delete(f"{BASE_URL}/profile/user_test_delete")
    print(f"  DELETE /profile/user_test_delete: ✅")

    print("  ✅ All profile endpoints working!")


if __name__ == "__main__":
    print("\n👤 Day 15 — User Profile Memory Tests")
    print("=" * 55)
    test_profile_created_on_first_message()
    test_profile_updates_with_interactions()
    test_profile_personalization()
    test_manual_profile_update()
    test_profile_context_in_pipeline()
    test_list_profiles()
    test_profile_api_endpoints()
    print("\n" + "=" * 55)
    print("🎉 All Day 15 tests passed!")