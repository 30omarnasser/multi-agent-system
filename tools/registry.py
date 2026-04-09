from tools.base import Tool
from typing import Dict

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found in registry")
        return self._tools[name]

    def to_openai_format(self) -> list:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
            }
            for t in self._tools.values()
        ]

    def to_gemini_format(self) -> list:
        """Format tools for Gemini's genai.Tool format"""
        from google.generativeai.types import FunctionDeclaration, Tool as GeminiTool

        declarations = []
        for t in self._tools.values():
            declarations.append(
                FunctionDeclaration(
                    name=t.name,
                    description=t.description,
                    parameters=t.parameters,
                )
            )
        return [GeminiTool(function_declarations=declarations)]