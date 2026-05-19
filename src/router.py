from typing import Any
from src.agents import TriagerAgent, GroqLLMClient

class Router:
    def __init__(self, client: GroqLLMClient):
        self.agent = TriagerAgent(client)

    def route(self, text: str) -> dict[str, Any]:
        result = self.agent.run(text)
        if result.parsed_json:
            return result.parsed_json
        return {
            "task_type": "unknown",
            "route": "manual_review_route",
            "reason": "triager_invalid_json",
            "notes": result.raw_text
        }
