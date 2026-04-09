import os, time
from typing import Callable
from dotenv import load_dotenv
import google.generativeai as genai
import google.ai.generativelanguage as glm
from google.api_core.exceptions import ResourceExhausted

from agents.models import Message, Role, ToolCall, AgentResponse
from tools.registry import ToolRegistry

load_dotenv()

class BaseAgent:

    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str = "gemini-2.0-flash",
        max_tokens: int = 1024,
        registry: ToolRegistry = None,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.max_tokens = max_tokens
        self.history: list[Message] = []
        self.registry = registry or ToolRegistry()

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self._init_client()
        print(f"[{self.name}] Agent initialized with model: {self.model}")

    def _init_client(self):
        tools = self.registry.to_gemini_format() if self.registry._tools else None
        self.client = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=self.system_prompt,
            tools=tools,
        )
        self.chat_session = self.client.start_chat(history=[])

    def register_tool(self, name: str, func: Callable, description: str, parameters: dict):
        from tools.base import Tool
        tool = Tool(name=name, description=description, parameters=parameters, fn=func)
        self.registry.register(tool)
        self._init_client()
        print(f"[{self.name}] Tool registered: {name}")

    def _send_with_retry(self, message, max_retries: int = 4):
        for attempt in range(max_retries):
            try:
                return self.chat_session.send_message(message)
            except ResourceExhausted as e:
                wait = 2 ** attempt * 5  # 5s, 10s, 20s, 40s
                if attempt < max_retries - 1:
                    print(f"  [{self.name}] ⚠ Rate limited. Retrying in {wait}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait)
                else:
                    raise RuntimeError(
                        f"[{self.name}] Rate limit exceeded after {max_retries} retries. "
                        "Wait a few minutes and try again."
                    ) from e

    def run(self, user_message: str) -> AgentResponse:
        self.history.append(Message(role=Role.USER, content=user_message))

        tool_calls_made: list[ToolCall] = []
        response = self._send_with_retry(user_message)

        while True:
            part = response.candidates[0].content.parts[0]

            if hasattr(part, "function_call") and part.function_call.name:
                fn_call = part.function_call
                tool_name = fn_call.name
                tool_args = dict(fn_call.args)

                print(f"  [{self.name}] → Calling tool: {tool_name}({tool_args})")

                tool_call_record = ToolCall(tool_name=tool_name, arguments=tool_args)
                try:
                    tool = self.registry.get(tool_name)
                    result = tool.run(**tool_args)
                    tool_call_record.result = result
                    print(f"  [{self.name}] ✓ Tool result: {str(result)[:200]}")
                except Exception as e:
                    result = f"Tool error: {e}"
                    tool_call_record.error = str(e)
                    print(f"  [{self.name}] ✗ Tool error: {e}")

                tool_calls_made.append(tool_call_record)

                response = self._send_with_retry(
                    glm.Part(
                        function_response=glm.FunctionResponse(
                            name=tool_name,
                            response={"result": result},
                        )
                    )
                )

            else:
                final_text = part.text
                break

        self.history.append(Message(role=Role.ASSISTANT, content=final_text))

        return AgentResponse(
            content=final_text,
            tool_calls=tool_calls_made,
            input_tokens=0,
            output_tokens=0,
            model=self.model,
            agent_name=self.name,
        )

    def clear_history(self):
        self.history = []
        self._init_client()
        print(f"[{self.name}] History cleared.")

    def get_history(self) -> list[dict]:
        return [{"role": m.role.value, "content": m.content} for m in self.history]