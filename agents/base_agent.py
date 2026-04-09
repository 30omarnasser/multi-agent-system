import os
import json
from typing import Callable
from dotenv import load_dotenv
import ollama as ollama_client

from agents.models import Message, Role, ToolCall, AgentResponse
from tools.registry import ToolRegistry
from memory.redis_memory import RedisMemory

load_dotenv()


class BaseAgent:

    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str = "llama3.2",
        max_tokens: int = 1024,
        registry: ToolRegistry = None,
        memory: RedisMemory = None,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.max_tokens = max_tokens
        self.history: list[Message] = []
        self.registry = registry or ToolRegistry()
        self.memory = memory
        self.session_id = None

        # Ollama host — inside Docker we reach it via host.docker.internal
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama = ollama_client.Client(host=self.ollama_host)

        print(f"[{self.name}] Agent initialized | model: {self.model} | ollama: {self.ollama_host}")

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

    # ─── Tool Registration ────────────────────────────────────

    def register_tool(self, name: str, func: Callable, description: str, parameters: dict):
        from tools.base import Tool
        tool = Tool(name=name, description=description, parameters=parameters, fn=func)
        self.registry.register(tool)
        print(f"[{self.name}] Tool registered: {name}")

    def _get_tools_for_ollama(self) -> list:
        """Convert registry tools to Ollama tool format."""
        if not self.registry._tools:
            return []
        tools = []
        for t in self.registry._tools.values():
            tools.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
            })
        return tools

    # ─── Message Builder ──────────────────────────────────────

    def _build_messages(self) -> list[dict]:
        """Build full message list including system prompt."""
        messages = [{"role": "system", "content": self.system_prompt}]
        for msg in self.history:
            if msg.role in (Role.USER, Role.ASSISTANT):
                messages.append({
                    "role": msg.role.value,
                    "content": msg.content,
                })
        return messages

    # ─── Core Run ─────────────────────────────────────────────

    def run(self, user_message: str, session_id: str = None) -> AgentResponse:
        """Send a message and get a response. Handles tool calls automatically."""

        # Load Redis session if provided
        if session_id and self.memory:
            self.load_session(session_id)

        # Add user message to history and Redis
        self.history.append(Message(role=Role.USER, content=user_message))
        if self.memory and self.session_id:
            self.memory.save_message(self.session_id, "user", user_message)

        # Build messages and tools
        messages = self._build_messages()
        tools = self._get_tools_for_ollama()
        tool_calls_made = []

        # ReAct loop — keep going while model wants to call tools
        while True:
            kwargs = {
                "model": self.model,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools

            response = self.ollama.chat(**kwargs)
            msg = response["message"]

            # ── Tool call branch ──
            if msg.get("tool_calls"):
                # Add assistant's tool-call message to context
                messages.append({
                    "role": "assistant",
                    "content": msg.get("content", ""),
                    "tool_calls": msg["tool_calls"],
                })

                for tc in msg["tool_calls"]:
                    tool_name = tc["function"]["name"]
                    tool_args = tc["function"]["arguments"]
                    if isinstance(tool_args, str):
                        tool_args = json.loads(tool_args)

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
                        print(f"  [{self.name}] ✗ Error: {e}")

                    tool_calls_made.append(tool_call_record)

                    # Add tool result back to context
                    messages.append({
                        "role": "tool",
                        "content": str(result),
                    })

            # ── Final text branch ──
            else:
                final_text = msg.get("content", "")
                break

        # Save to history and Redis
        self.history.append(Message(role=Role.ASSISTANT, content=final_text))
        if self.memory and self.session_id:
            self.memory.save_message(self.session_id, "assistant", final_text)

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