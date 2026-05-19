from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class FlowState:
    case_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    raw_input: str = ""
    clean_text: str = ""
    
    route: str | None = None
    route_reason: str | None = None
    schema_name: str | None = None
    
    extraction_raw: str | None = None
    extraction_parsed: dict[str, Any] | None = None
    
    is_valid: bool = False
    validation_issues: list[str] = field(default_factory=list)
    
    fallback_triggered: bool = False
    fallback_method: str | None = None
    fallback_output: dict[str, Any] | None = None
    
    final_output: dict[str, Any] | None = None
    status: str = "initialized"
    
    steps: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_step(self, step_name: str, status: str, output: Any = None):
        self.steps.append({
            "step": step_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "output_keys": list(output.keys()) if isinstance(output, dict) else []
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "timestamp": self.timestamp,
            "raw_input": self.raw_input,
            "route": self.route,
            "status": self.status,
            "is_valid": self.is_valid,
            "fallback_triggered": self.fallback_triggered,
            "final_output": self.final_output,
            "steps": self.steps,
            "errors": self.errors,
            "warnings": self.warnings
        }
