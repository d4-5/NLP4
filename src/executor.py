from typing import Any
from src.agents import ExtractorAgent, GroqLLMClient

class Executor:
    def __init__(self, client: GroqLLMClient):
        self.agent = ExtractorAgent(client)

    def execute(self, text: str, triage: dict[str, Any]) -> dict[str, Any]:
        result = self.agent.run(text, triage)
        return {
            "raw": result.raw_text,
            "parsed": result.parsed_json,
            "usage": result.usage
        }
