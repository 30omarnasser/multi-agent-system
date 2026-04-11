import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import ollama as ollama_client

load_dotenv()


class UserProfileMemory:
    """
    Persistent user profile memory.
    Learns user preferences, expertise, and style from conversations.
    Updates automatically after every interaction.
    """

    def __init__(self):
        self.conn_params = {
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "user": os.getenv("POSTGRES_USER", "agent_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "agent_pass"),
            "dbname": os.getenv("POSTGRES_DB", "agent_db"),
        }
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        self.ollama = ollama_client.Client(host=self.ollama_host)
        self._init_db()
        print("[UserProfile] Ready.")

    def _get_conn(self):
        return psycopg2.connect(**self.conn_params)

    def _init_db(self):
        """Create user_profiles table."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        id SERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL UNIQUE,
                        name TEXT DEFAULT '',
                        expertise_level TEXT DEFAULT 'unknown',
                        communication_style TEXT DEFAULT 'neutral',
                        interests TEXT[] DEFAULT '{}',
                        preferences JSONB DEFAULT '{}',
                        interaction_count INTEGER DEFAULT 0,
                        last_updated TIMESTAMP DEFAULT NOW(),
                        created_at TIMESTAMP DEFAULT NOW(),
                        raw_notes TEXT DEFAULT ''
                    );
                """)
                conn.commit()
        print("[UserProfile] Database table ready.")

    # ─── Core Operations ──────────────────────────────────────

    def get_profile(self, user_id: str) -> dict:
        """Get user profile, create empty one if doesn't exist."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM user_profiles WHERE user_id = %s",
                    (user_id,)
                )
                row = cur.fetchone()
                if row:
                    return dict(row)
                else:
                    return self._create_empty_profile(user_id)

    def _create_empty_profile(self, user_id: str) -> dict:
        """Create a new empty profile for a user."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO user_profiles (user_id)
                    VALUES (%s)
                    RETURNING *
                    """,
                    (user_id,)
                )
                conn.commit()
                return dict(cur.fetchone())

    def update_profile(self, user_id: str, updates: dict) -> dict:
        """Manually update specific profile fields."""
        allowed = {
            "name", "expertise_level", "communication_style",
            "interests", "preferences", "raw_notes"
        }
        filtered = {k: v for k, v in updates.items() if k in allowed}
        if not filtered:
            return self.get_profile(user_id)

        set_clauses = []
        values = []
        for key, value in filtered.items():
            if key == "preferences":
                set_clauses.append(
                    f"{key} = {key} || %s::jsonb"
                )
                values.append(json.dumps(value))
            elif key == "interests":
                set_clauses.append(
                    f"{key} = ARRAY(SELECT DISTINCT unnest({key} || %s::text[]))"
                )
                values.append(value)
            else:
                set_clauses.append(f"{key} = %s")
                values.append(value)

        set_clauses.append("last_updated = NOW()")
        values.append(user_id)

        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    UPDATE user_profiles
                    SET {', '.join(set_clauses)}
                    WHERE user_id = %s
                    RETURNING *
                    """,
                    values,
                )
                conn.commit()
                row = cur.fetchone()
                return dict(row) if row else self.get_profile(user_id)

    def increment_interaction(self, user_id: str):
        """Increment interaction count after each conversation."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_profiles (user_id, interaction_count)
                    VALUES (%s, 1)
                    ON CONFLICT (user_id) DO UPDATE
                    SET interaction_count = user_profiles.interaction_count + 1,
                        last_updated = NOW()
                    """,
                    (user_id,)
                )
                conn.commit()

    def auto_update_from_conversation(
        self,
        user_id: str,
        user_message: str,
        assistant_response: str,
        model: str = "llama3.1:8b",
    ):
        """
        Automatically extract profile insights from a conversation
        and update the user profile.
        """
        current_profile = self.get_profile(user_id)

        prompt = f"""Analyze this conversation and extract user profile information.
Return ONLY a JSON object. No explanation, no markdown.

Current profile:
- expertise_level: {current_profile.get('expertise_level', 'unknown')}
- communication_style: {current_profile.get('communication_style', 'neutral')}
- interests: {current_profile.get('interests', [])}
- name: {current_profile.get('name', '')}

Conversation:
User: {user_message[:500]}
Assistant: {assistant_response[:300]}

Extract ONLY what's clearly evident. Return:
{{
  "name": "user's name if mentioned, else empty string",
  "expertise_level": "beginner/intermediate/advanced/expert or unknown",
  "communication_style": "formal/casual/technical/simple or neutral",
  "interests": ["topic1", "topic2"],
  "preferences": {{"key": "value"}},
  "notes": "one sentence observation about this user"
}}

If nothing is evident, return empty/unknown values. Return ONLY valid JSON:"""

        try:
            response = self.ollama.chat(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You extract user profile info from conversations. Return ONLY valid JSON."
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            raw = response["message"]["content"].strip()

            # Clean markdown
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:].strip()

            if "{" in raw and "}" in raw:
                raw = raw[raw.index("{"):raw.rindex("}") + 1]

            data = json.loads(raw)
            print(f"[UserProfile] Extracted: {data}")

            # Only update fields that have meaningful values
            updates = {}
            if data.get("name") and data["name"].strip():
                updates["name"] = data["name"].strip()
            if data.get("expertise_level") and data["expertise_level"] != "unknown":
                updates["expertise_level"] = data["expertise_level"]
            if data.get("communication_style") and data["communication_style"] != "neutral":
                updates["communication_style"] = data["communication_style"]
            if data.get("interests") and isinstance(data["interests"], list):
                updates["interests"] = [i for i in data["interests"] if i][:10]
            if data.get("preferences") and isinstance(data["preferences"], dict):
                updates["preferences"] = data["preferences"]
            if data.get("notes"):
                existing_notes = current_profile.get("raw_notes", "")
                new_note = data["notes"].strip()
                if new_note and new_note not in existing_notes:
                    updates["raw_notes"] = (existing_notes + f"\n- {new_note}").strip()

            if updates:
                self.update_profile(user_id, updates)
                print(f"[UserProfile] ✓ Updated profile for '{user_id}': {list(updates.keys())}")
            else:
                print(f"[UserProfile] No meaningful updates extracted for '{user_id}'")

        except Exception as e:
            print(f"[UserProfile] Auto-update failed (non-critical): {e}")

        # Always increment interaction count
        self.increment_interaction(user_id)

    # ─── Prompt Formatting ────────────────────────────────────

    def format_for_prompt(self, user_id: str) -> str:
        """Format profile as LLM-readable context string."""
        profile = self.get_profile(user_id)

        if profile.get("interaction_count", 0) == 0:
            return ""

        parts = []

        if profile.get("name"):
            parts.append(f"User's name: {profile['name']}")

        if profile.get("expertise_level") and profile["expertise_level"] != "unknown":
            parts.append(f"Expertise level: {profile['expertise_level']}")

        if profile.get("communication_style") and profile["communication_style"] != "neutral":
            parts.append(f"Preferred style: {profile['communication_style']}")

        interests = profile.get("interests") or []
        if interests:
            parts.append(f"Known interests: {', '.join(interests[:5])}")

        prefs = profile.get("preferences") or {}
        if prefs:
            pref_str = ", ".join([f"{k}: {v}" for k, v in list(prefs.items())[:3]])
            parts.append(f"Preferences: {pref_str}")

        if profile.get("raw_notes"):
            notes = profile["raw_notes"].strip()
            if notes:
                parts.append(f"Notes: {notes[:200]}")

        if not parts:
            return ""

        return "User profile:\n" + "\n".join(f"- {p}" for p in parts)

    def delete_profile(self, user_id: str):
        """Delete a user profile."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM user_profiles WHERE user_id = %s",
                    (user_id,)
                )
                conn.commit()
        print(f"[UserProfile] Deleted profile for '{user_id}'")

    def list_profiles(self) -> list[dict]:
        """List all user profiles."""
        with self._get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT user_id, name, expertise_level, communication_style,
                           interests, interaction_count, last_updated
                    FROM user_profiles
                    ORDER BY last_updated DESC
                """)
                return [dict(r) for r in cur.fetchall()]