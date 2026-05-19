from __future__ import annotations

import logging
from typing import Any

from src.agents import GroqLLMClient, RepairAgent, ReviewerAgent
from src.executor import Executor
from src.exporter import Exporter
from src.fallback import run_fallback
from src.flow_logger import FlowLogger
from src.flow_state import FlowState
from src.router import Router
from src.validator import validate_output

class NLPFlow:
    def __init__(self, client: GroqLLMClient):
        self.client = client
        self.router = Router(client)
        self.executor = Executor(client)
        self.reviewer = ReviewerAgent(client)
        self.repair = RepairAgent(client)
        self.exporter = Exporter()
        self.logger = FlowLogger()

    def run(self, text: str) -> dict[str, Any]:
        state = FlowState(raw_input=text)
        
        try:
            self._step_ingest(state)
            
            self._step_route(state)
            
            self._step_execute(state)
            
            self._step_validate(state)
            
            export_data = self._step_export(state)
            
            self.logger.log_case(state)
            return export_data
            
        except Exception as e:
            state.status = "failed"
            state.errors.append(f"Unexpected error: {str(e)}")
            self.logger.log_case(state)
            return self.exporter.export(state)

    def _step_ingest(self, state: FlowState):
        state.status = "ingesting"
        state.clean_text = state.raw_input.strip()
        if not state.clean_text:
            state.errors.append("Empty input")
            state.status = "failed"
            raise ValueError("Empty input")
        
        state.status = "ingested"
        state.add_step("ingest", "ok")

    def _step_route(self, state: FlowState):
        state.status = "routing"
        triage = self.router.route(state.clean_text)
        state.route = triage.get("route")
        state.route_reason = triage.get("reason")
        state.schema_name = triage.get("schema")
        
        state.status = "routed"
        state.add_step("route", "ok", triage)

    def _step_execute(self, state: FlowState):
        if state.status == "failed": return
        state.status = "executing"
        
        triage = {
            "route": state.route,
            "reason": state.route_reason,
            "schema": state.schema_name
        }
        execution_result = self.executor.execute(state.clean_text, triage)
        state.extraction_raw = execution_result["raw"]
        state.extraction_parsed = execution_result["parsed"]
        
        state.status = "executed"
        state.add_step("execute", "ok", execution_result)

    def _step_validate(self, state: FlowState):
        if state.status == "failed": return
        state.status = "validating"
        
        validation = validate_output(state.extraction_raw or "")
        state.is_valid = validation.is_valid
        state.validation_issues = validation.error_messages()
        
        triage = {"route": state.route}
        review_result = self.reviewer.run(
            text=state.clean_text,
            triage=triage,
            extraction=state.extraction_parsed,
            validation_errors=state.validation_issues
        )
        review = review_result.parsed_json or {}
        
        if state.is_valid and review.get("verdict") == "accept":
            state.status = "validated"
            state.add_step("validate", "ok", review)
        else:
            state.fallback_triggered = True
            state.add_step("validate", "warning", review)
            self._handle_fallback(state, review)

    def _handle_fallback(self, state: FlowState, review: dict[str, Any]):
        state.status = "falling_back"
        triage = {"route": state.route}
        
        fallback_res = run_fallback(
            text=state.clean_text,
            triage=triage,
            extraction=state.extraction_parsed,
            review=review,
            repair_agent=self.repair
        )
        
        state.fallback_method = fallback_res.get("action")
        state.fallback_output = fallback_res.get("output")
        
        if fallback_res.get("success"):
            state.status = "validated_after_fallback"
            if fallback_res.get("needs_manual_review"):
                state.warnings.append("Fallback success but needs manual review")
        else:
            state.status = "failed_manual_review"
            state.errors.append("Fallback failed to produce valid output")
        
        state.add_step("fallback", "ok" if fallback_res.get("success") else "failed", fallback_res)

    def _step_export(self, state: FlowState) -> dict[str, Any]:
        state.status = "exported" if not state.errors else "exported_with_errors"
        export_data = self.exporter.export(state)
        state.add_step("export", "ok")
        return export_data
