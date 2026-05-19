import json
from typing import Any
from src.flow_state import FlowState

class Exporter:
    def export(self, state: FlowState) -> dict[str, Any]:
        return {
            "case_id": state.case_id,
            "timestamp": state.timestamp,
            "input": state.raw_input,
            "route": state.route,
            "output": state.extraction_parsed or state.fallback_output,
            "status": state.status,
            "is_valid": state.is_valid,
            "fallback_triggered": state.fallback_triggered,
            "fallback_method": state.fallback_method,
            "warnings": state.warnings,
            "errors": state.errors,
            "needs_manual_review": state.status in ["failed", "manual_review", "exported_with_warning", "failed_manual_review"]
        }

    def to_json(self, export_data: dict[str, Any]) -> str:
        return json.dumps(export_data, ensure_ascii=False, indent=2)
