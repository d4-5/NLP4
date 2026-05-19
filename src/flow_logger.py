import json
from pathlib import Path
from typing import Any
from src.flow_state import FlowState

class FlowLogger:
    def __init__(self, log_path: str = "docs/flow_logs_lab14.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_case(self, state: FlowState):
        log_entry = state.to_dict()
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def log_event(self, case_id: str, event: str, details: Any):
        pass
