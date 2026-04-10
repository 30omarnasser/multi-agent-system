import os
import ollama as ollama_client
from agents.state import AgentState
from tools.definitions import python_executor_tool

CODER_PROMPT = """You are a Coder agent in a multi-agent AI system.
Your job is to write clean, correct, complete Python code that solves the user's request.
Rules:
- Write ONLY the Python code, nothing else
- No markdown fences, no explanation, just raw Python
- Always use print() to show all results
- If research context is provided, use the data from it directly in your code
- Handle edge cases and errors gracefully"""


class CoderAgent:

    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model
        self.ollama = ollama_client.Client(
            host=os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        )
        print(f"[CoderAgent] Initialized | model: {self.model}")

    def run(self, state: AgentState) -> AgentState:
        user_message = state["user_message"]
        research = state.get("research", "")
        code_requirements = state.get("code_requirements", [])
        critique = state.get("critique", {})

        print(f"\n[CoderAgent] Writing code for: '{user_message[:100]}'")

        # Build context for code generation
        context = f"User request: {user_message}\n"

        if code_requirements:
            context += f"\nCode must:\n"
            for i, req in enumerate(code_requirements, 1):
                context += f"  {i}. {req}\n"

        if research:
            context += f"\nResearch context (use this data in your code):\n{research}\n"

        if critique.get("feedback") and critique.get("approved") is False:
            context += f"\nPrevious attempt was rejected. Feedback:\n{critique['feedback']}\n"
            context += "Fix all issues mentioned above.\n"

        # Generate code
        code = self._generate_code(context)
        print(f"[CoderAgent] Generated code ({len(code)} chars):\n{code[:400]}")

        # Execute code
        execution_result = self._execute_code(code)
        print(f"[CoderAgent] Execution result: {execution_result[:300]}")

        code_output = (
            f"**Code:**\n```python\n{code}\n```\n\n"
            f"**Output:**\n{execution_result}"
        )

        return {
            **state,
            "code_output": code_output,
            "current_agent": "coder",
        }

    def _generate_code(self, context: str) -> str:
        try:
            response = self.ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": CODER_PROMPT},
                    {"role": "user", "content": context},
                ],
            )
            code = response["message"]["content"].strip()

            # Strip markdown fences if model ignored instructions
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()

            return code
        except Exception as e:
            return f'print("Code generation failed: {e}")'

    def _execute_code(self, code: str) -> str:
        try:
            result = python_executor_tool.run(code=code)
            return result
        except Exception as e:
            return f"Execution error: {e}"