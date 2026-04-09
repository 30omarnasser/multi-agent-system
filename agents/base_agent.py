import os
from typing import Callable
from dotenv import load_dotenv
import google.generativeai as genai

from agents.models import Message, Role, ToolCall, AgentResponse

load_dotenv()


class BaseAgent:

    def __init__(self, name: str, system_prompt: str, model: str = "gemini-2.5-flash", max_tokens: int = 1024):
        # IMPORTANT: assign all attributes FIRST before anything else
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.max_tokens = max_tokens
        self.history: list[Message] = []
        self.tools: dict[str, Callable] = {}
        self.tool_schemas: list[dict] = []

        # Gemini client — AFTER attributes are set
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.client = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=self.system_prompt
        )
        self.chat_session = self.client.start_chat(history=[])

        print(f"[{self.name}] Agent initialized with model: {self.model}")

    def register_tool(self, name: str, func: Callable, description: str, parameters: dict):
        self.tools[name] = func
        self.tool_schemas.append({
            "name": name,
            "description": description,
            "input_schema": parameters,
        })
        print(f"[{self.name}] Tool registered: {name}")

    def run(self, user_message: str) -> AgentResponse:
        self.history.append(Message(role=Role.USER, content=user_message))

        response = self.chat_session.send_message(user_message)
        final_text = response.text

        self.history.append(Message(role=Role.ASSISTANT, content=final_text))

        return AgentResponse(
            content=final_text,
            tool_calls=[],
            input_tokens=0,
            output_tokens=0,
            model=self.model,
            agent_name=self.name,
        )

    def clear_history(self):
        self.history = []
        self.chat_session = self.client.start_chat(history=[])
        print(f"[{self.name}] History cleared.")

    def get_history(self) -> list[dict]:
        return [{"role": m.role.value, "content": m.content} for m in self.history]