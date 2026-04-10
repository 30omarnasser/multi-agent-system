import os
import ollama as ollama_client
from agents.state import AgentState
from tools.definitions import python_executor_tool

CODER_PROMPT = """You are a Coder agent in a multi-agent AI system.
Your job is to write clean, working Python code to solve the user's request.
Always write complete, runnable code with print() statements to show results.
If you have research context, use it to inform your code.
Return ONLY the Python code, no explanation, no markdown fences."""


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

        print(f"\n[CoderAgent] Writing code for: {user_message[:100]}")

        context = f"User request: {user_message}"
        if research:
            context += f"\n\nResearch context:\n{research}"

        # Generate code
        try:
            response = self.ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": CODER_PROMPT},
                    {"role": "user", "content": context},
                ],
            )
            code = response["message"]["content"].strip()

            # Strip markdown fences if model added them
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()

            print(f"[CoderAgent] Generated code:\n{code[:300]}")

        except Exception as e:
            code = f'print("Code generation failed: {e}")'

        # Execute the code
        try:
            execution_result = python_executor_tool.run(code=code)
            print(f"[CoderAgent] Execution result: {execution_result[:200]}")
        except Exception as e:
            execution_result = f"Execution error: {e}"

        code_output = f"Code:\n```python\n{code}\n```\n\nOutput:\n{execution_result}"

        return {
            **state,
            "code_output": code_output,
            "current_agent": "coder",
        }