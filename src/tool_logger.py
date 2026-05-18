import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

class ToolLogger:
    def __init__(self, log_path: str = "docs/tool_logs_lab12.jsonl"):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log_call(self, task_id: str, tool_name: str, tool_input: Any, tool_output: Any, success: bool = True, error: Optional[str] = None):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "tool_name": tool_name,
            "input": tool_input,
            "output": tool_output,
            "success": success,
            "error": error
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def get_logs(self):
        logs = []
        if os.path.exists(self.log_path):
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        logs.append(json.loads(line))
        return logs
