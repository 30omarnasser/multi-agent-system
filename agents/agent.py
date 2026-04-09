import json
from openai import OpenAI
from tools.registry import ToolRegistry

class Agent:
    def __init__(self, registry: ToolRegistry):
        self.client = OpenAI()
        self.registry = registry
        self.messages = []

    def run(self, user_input: str) -> str:
        # Add user message to history
        self.messages.append({"role": "user", "content": user_input})

        # Loop until the LLM gives a final answer (not a tool call)
        while True:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self.messages,
                tools=self.registry.to_openai_format(),
                tool_choice="auto"   # let the LLM decide
            )

            message = response.choices[0].message

            # Case 1: LLM wants to call a tool
            if message.tool_calls:
                self.messages.append(message)  # add assistant's decision

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    print(f"  → Calling tool: {tool_name}({tool_args})")

                    # Execute the tool
                    tool = self.registry.get(tool_name)
                    result = tool.run(**tool_args)

                    # Feed result back into the conversation
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result)
                    })

                # Loop again — LLM will now use the tool results

            # Case 2: LLM gave a final text answer
            else:
                final = message.content
                self.messages.append({"role": "assistant", "content": final})
                return final