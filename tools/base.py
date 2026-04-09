from typing import Callable, Any
from dataclasses import dataclass

@dataclass
class Tool:
    name: str
    description: str
    parameters: dict          # JSON Schema format
    fn: Callable

    def run(self, **kwargs) -> Any:
        return self.fn(**kwargs)