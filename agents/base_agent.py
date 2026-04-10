import os
import json
import time
from typing import Callable
from dotenv import load_dotenv
import ollama as ollama_client

from agents.models import Message, Role, ToolCall, AgentResponse
from tools.registry import ToolRegistry
from memory.redis_memory import RedisMemory
from memory.postgres_memory import PostgresMemory

load_dotenv()

# Words that indicate the user actually needs a tool
TOOL_TRIGGER_WORDS = {
    "search", "look up", "lookup", "find", "google",
    "calculate", "compute", "math", "equation",
    "run", "execute", "code", "script", "program",
    "what is the price", "how much", "cost",
    "latest", "current", "news", "today", "weather",
    "who is", "when did", "what happened",
}


class BaseAgent:

    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str = "llama3.1:8b",
        max_tokens: int = 1024,
        registry: ToolRegistry = None,
        memory: RedisMemory = None,
        long_term_memory: PostgresMemory = None,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.max_tokens = max_tokens
        self.history: list[Message] = []
        self.registry = registry or ToolRegistry()
        self.memory = memory
        self.long_term_memory = long_term_memory
        self.session_id = None

        self.ollama_host = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        self.ollama = ollama_client.Client(host=self.ollama_host)

        print(f"[{self.name}] Agent initialized | model: {self.model}")

    # ─── Session / Memory ─────────────────────────────────────

    def load_session(self, session_id: str):
        self.session_id = session_id
        if self.memory and self.memory.session_exists(session_id):
            stored = self.memory.get_history(session_id)
            self.history = [
                Message(role=Role(m["role"]), content=m["content"])
                for m in stored
                if m["role"] in ("user", "assistant")
            ]
            print(f"[{self.name}] Loaded session '{session_id}' — {len(self.history)} messages")
        else:
            self.history = []
            print(f"[{self.name}] New session: '{session_id}'")

    def _recall_relevant_facts(self, query: str) -> str:
        """Search long-term memory for facts relevant to the current query."""
        if not self.long_term_memory:
            return ""
        facts = self.long_term_memory.search_facts(
            query=query,
            session_id=self.session_id,
            top_k=5,
            threshold=0.3,
        )
        if not facts:
            return ""
        facts_text = "\n".join([f"- [{f['category']}] {f['fact']}" for f in facts])
        return f"\n\nRelevant facts from long-term memory:\n{facts_text}\n"

    def _extract_and_save_facts(self, user_message: str, assistant_response: str):
        """Ask the LLM to extract important facts and save to long-term memory."""
        if not self.long_term_memory or not self.session_id:
            return

        extraction_prompt = f"""Extract important facts from this conversation.
Return ONLY a JSON array. No explanation, no markdown, no backticks.
Use categories: personal, project, preference, technical, general.
Only extract facts worth remembering long-term.
If no important facts, return: []

User: {user_message}
Assistant: {assistant_response}

JSON array only:"""

        try:
            response = self.ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a JSON extraction assistant. "
                            "You output ONLY valid JSON arrays, nothing else. "
                            "No markdown, no explanation."
                        ),
                    },
                    {"role": "user", "content": extraction_prompt},
                ],
            )
            raw = response["message"]["content"].strip()
            print(f"[{self.name}] Raw fact extraction: {raw[:200]}")

            # Strip markdown code blocks if present
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            # Extract just the JSON array
            if "[" in raw and "]" in raw:
                raw = raw[raw.index("[") : raw.rindex("]") + 1]

            facts = json.loads(raw)
            saved = 0
            for item in facts:
                if isinstance(item, dict) and "fact" in item:
                    self.long_term_memory.save_fact(
                        session_id=self.session_id,
                        fact=item["fact"],
                        category=item.get("category", "general"),
                    )
                    saved += 1
            print(f"[{self.name}] ✓ Saved {saved} facts to long-term memory.")

        except Exception as e:
            print(f"[{self.name}] Fact extraction failed (non-critical): {e}")

    # ─── Tool Helpers ─────────────────────────────────────────

    def register_tool(self, name: str, func: Callable, description: str, parameters: dict):
        from tools.base import Tool
        tool = Tool(name=name, description=description, parameters=parameters, fn=func)
        self.registry.register(tool)
        print(f"[{self.name}] Tool registered: {name}")

    def _needs_tools(self, message: str) -> bool:
        """Only attach tools if the message actually needs them."""
        lowered = message.lower()
        return any(word in lowered for word in TOOL_TRIGGER_WORDS)

    def _get_tools_for_ollama(self) -> list:
        if not self.registry._tools:
            return []
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
            }
            for t in self.registry._tools.values()
        ]

    # ─── Message Builder ──────────────────────────────────────

    def _build_messages(self, extra_context: str = "") -> list[dict]:
        system = self.system_prompt
        if extra_context:
            system += extra_context
        messages = [{"role": "system", "content": system}]
        for msg in self.history:
            if msg.role in (Role.USER, Role.ASSISTANT):
                messages.append({"role": msg.role.value, "content": msg.content})
        return messages

    # ─── Core Run ─────────────────────────────────────────────

    def run(self, user_message: str, session_id: str = None) -> AgentResponse:
        # Load Redis session if session_id provided
        if session_id and self.memory:
            self.load_session(session_id)

        # Recall relevant long-term facts before responding
        extra_context = self._recall_relevant_facts(user_message)
        if extra_context:
            print(f"[{self.name}] 🧠 Recalled facts: {extra_context.strip()[:200]}")

        # Add user message to history + Redis
        self.history.append(Message(role=Role.USER, content=user_message))
        if self.memory and self.session_id:
            self.memory.save_message(self.session_id, "user", user_message)

        messages = self._build_messages(extra_context=extra_context)
        tool_calls_made: list[ToolCall] = []

        # Decide once whether this message needs tools
        use_tools = self._needs_tools(user_message)
        print(f"[{self.name}] Tools enabled for this message: {use_tools}")

        # ─── ReAct Loop ───────────────────────────────────────
        while True:
            kwargs = {"model": self.model, "messages": messages}

            # Only attach tools when message actually needs them
            if use_tools:
                tools = self._get_tools_for_ollama()
                if tools:
                    kwargs["tools"] = tools

            response = self.ollama.chat(**kwargs)
            msg = response["message"]

            if use_tools and msg.get("tool_calls"):
                # Append assistant tool-call turn
                messages.append({
                    "role": "assistant",
                    "content": msg.get("content", ""),
                    "tool_calls": msg["tool_calls"],
                })

                for tc in msg["tool_calls"]:
                    tool_name = tc["function"]["name"]
                    tool_args = tc["function"]["arguments"]

                    if isinstance(tool_args, str):
                        try:
                            tool_args = json.loads(tool_args)
                        except json.JSONDecodeError:
                            tool_args = {}

                    print(f"  [{self.name}] → Calling tool: {tool_name}({tool_args})")
                    tool_call_record = ToolCall(tool_name=tool_name, arguments=tool_args)

                    try:
                        tool = self.registry.get(tool_name)
                        result = tool.run(**tool_args)
                        tool_call_record.result = result
                        print(f"  [{self.name}] ✓ Result: {str(result)[:200]}")
                    except Exception as e:
                        result = f"Tool error: {e}"
                        tool_call_record.error = str(e)
                        print(f"  [{self.name}] ✗ Tool error: {e}")

                    tool_calls_made.append(tool_call_record)
                    messages.append({"role": "tool", "content": str(result)})

            else:
                # Final text response — exit loop
                final_text = msg.get("content", "")
                break

        # ─── Save to history + Redis ──────────────────────────
        self.history.append(Message(role=Role.ASSISTANT, content=final_text))
        if self.memory and self.session_id:
            self.memory.save_message(self.session_id, "assistant", final_text)

        # ─── Extract facts to long-term memory ───────────────
        self._extract_and_save_facts(user_message, final_text)

        return AgentResponse(
            content=final_text,
            tool_calls=tool_calls_made,
            input_tokens=0,
            output_tokens=0,
            model=self.model,
            agent_name=self.name,
        )

    # ─── Utilities ────────────────────────────────────────────

    def clear_history(self):
        self.history = []
        if self.memory and self.session_id:
            self.memory.clear_session(self.session_id)
        print(f"[{self.name}] History cleared.")

    def get_history(self) -> list[dict]:
        return [{"role": m.role.value, "content": m.content} for m in self.history]