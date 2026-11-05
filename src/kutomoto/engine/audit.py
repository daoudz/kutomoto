"""
kutomoto.engine.audit
90Studio Compliance Audit Trail Models, Credential Masking, and Structured Logger.
Copyrights reserved to 90Studio
"""

from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import platform
import time
from typing import Any, List, Literal, Optional
import uuid

from pydantic import BaseModel, Field

logger = logging.getLogger("kutomoto.audit")


# ==============================================================================
# 1. AUDIT DATA MODELS (COMPLIANT WITH SPECIFICATION.MD SECTION 10.1)
# ==============================================================================

class AuditTargetApplication(BaseModel):
    title: str = Field(..., description="Target window caption")
    hwnd: int = Field(..., description="Win32 Window Handle integer")
    process_name: str = Field(..., description="Target process executable name")
    pid: Optional[int] = Field(None, description="Process ID")


class AuditExecutionSummary(BaseModel):
    total_steps: int = Field(..., ge=0)
    successful_steps: int = Field(..., ge=0)
    failed_steps: int = Field(..., ge=0)
    retried_steps: int = Field(..., ge=0)
    duration_seconds: float = Field(..., ge=0.0)
    final_status: Literal["SUCCESS", "FAILED", "ABORTED"]


class AuditStepEvent(BaseModel):
    step_index: int = Field(..., ge=1)
    action_type: str = Field(...)
    label: Optional[str] = None
    timestamp_offset_ms: int = Field(..., ge=0)
    parameters_summary: str = Field(...)
    latency_ms: float = Field(..., ge=0.0)
    status: Literal["SUCCESS", "ERROR", "SKIPPED", "RETRIED"]
    error_details: Optional[str] = None


class KutomotoAuditLog(BaseModel):
    audit_version: Literal["1.0.0"] = "1.0.0"
    system: Literal["kutomoto"] = "kutomoto"
    copyright: Literal["Copyrights reserved to 90Studio"] = "Copyrights reserved to 90Studio"
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = Field(...)
    workflow_name: str = Field(...)
    source_mode: Optional[Literal["visual_designer_generated", "manual_step_flow", "hybrid"]] = "manual_step_flow"
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    operator_username: str = Field(...)
    host_machine: str = Field(...)
    os_version: str = Field(...)
    target_application: AuditTargetApplication
    execution_summary: AuditExecutionSummary
    step_events: List[AuditStepEvent]


# ==============================================================================
# 2. CREDENTIAL MASKING UTILITY
# ==============================================================================

class CredentialMasker:
    """Masks secret values in audit summaries and execution logs."""
    MASK_STRING = "********"

    @classmethod
    def mask_parameter_summary(cls, action_type: str, params: Any, is_secret: bool = False) -> str:
        if action_type == "type_text":
            secret_flag = is_secret or getattr(params, "is_secret", False)
            if secret_flag:
                char_count = len(getattr(params, "text", "") or "")
                return f"text='{cls.MASK_STRING}' ({char_count} chars, masked), pacing={getattr(params, 'keystroke_delay_ms', 20)}ms"
            return f"text='{getattr(params, 'text', '')}', pacing={getattr(params, 'keystroke_delay_ms', 20)}ms"

        elif action_type == "click":
            mode = getattr(params, "coordinate_mode", "normalized")
            mode_val = mode.value if hasattr(mode, "value") else str(mode)
            if mode_val == "normalized":
                nx = getattr(params, "norm_x", 0.0) or 0.0
                ny = getattr(params, "norm_y", 0.0) or 0.0
                btn = getattr(params, "button", "left")
                btn_val = btn.value if hasattr(btn, "value") else str(btn)
                return f"norm_coords=({nx:.4f}, {ny:.4f}), button={btn_val}"
            btn = getattr(params, "button", "left")
            btn_val = btn.value if hasattr(btn, "value") else str(btn)
            return f"screen_coords=({getattr(params, 'x', 0)}, {getattr(params, 'y', 0)}), button={btn_val}"

        elif action_type == "focus_window":
            return f"pattern='{getattr(params, 'window_title_pattern', '')}', process='{getattr(params, 'process_name', '')}'"

        elif action_type == "key_press":
            return f"key={getattr(params, 'key', 'tab')}, repeat={getattr(params, 'repeat_count', 1)}"

        elif action_type == "hotkey":
            return f"keys={getattr(params, 'keys', [])}"

        elif action_type == "clear_field":
            strat = getattr(params, "clear_strategy", "select_all_backspace")
            strat_val = strat.value if hasattr(strat, "value") else str(strat)
            return f"strategy={strat_val}"

        elif action_type == "delay":
            return f"duration_ms={getattr(params, 'duration_ms', 0)}"

        elif action_type == "submit":
            m = getattr(params, "submit_method", "enter_key")
            m_val = m.value if hasattr(m, "value") else str(m)
            return f"method={m_val}"

        elif action_type == "scroll":
            return f"delta_x={getattr(params, 'delta_x', 0)}, delta_y={getattr(params, 'delta_y', 0)}"

        elif action_type == "prompt_user_input":
            var = getattr(params, "variable_name", "")
            if is_secret or getattr(params, "is_password", False):
                return f"prompt for variable '{var}' (secret input)"
            return f"prompt for variable '{var}'"

        return str(params)


# ==============================================================================
# 3. STRUCTURED AUDIT LOGGER
# ==============================================================================

class AuditLogger:
    def __init__(self, execution_id: str, workflow: Any):
        self.execution_id = execution_id
        self.workflow = workflow
        self.start_perf = time.perf_counter()
        self.step_events: List[AuditStepEvent] = []
        self._target_app_info = AuditTargetApplication(
            title=getattr(workflow.target_application, "window_title_pattern", ""),
            hwnd=0,
            process_name=getattr(workflow.target_application, "process_name", "") or "unknown",
            pid=0,
        )

    def set_target_app_details(self, hwnd: int, title: str, process_name: str, pid: Optional[int] = None) -> None:
        self._target_app_info = AuditTargetApplication(
            title=title,
            hwnd=hwnd,
            process_name=process_name,
            pid=pid,
        )

    def reset(self, execution_id: Optional[str] = None, workflow: Optional[Any] = None) -> None:
        """
        Resets internal audit logger state for an isolated workflow execution run.
        Clears step events, resets start timer, and optionally updates execution_id/workflow.
        """
        if execution_id is not None:
            self.execution_id = execution_id
        if workflow is not None:
            self.workflow = workflow
            target_app = getattr(workflow, "target_application", None)
            self._target_app_info = AuditTargetApplication(
                title=getattr(target_app, "window_title_pattern", "") if target_app else "",
                hwnd=0,
                process_name=(getattr(target_app, "process_name", "") or "unknown") if target_app else "unknown",
                pid=0,
            )
        self.start_perf = time.perf_counter()
        self.step_events.clear()

    def _offset_ms(self) -> int:
        return int((time.perf_counter() - self.start_perf) * 1000)

    def record_success(
        self,
        step_index: int,
        action_type: str,
        label: Optional[str],
        parameters_summary: str,
        latency_ms: float,
    ) -> None:
        self.step_events.append(AuditStepEvent(
            step_index=step_index,
            action_type=action_type,
            label=label,
            timestamp_offset_ms=self._offset_ms(),
            parameters_summary=parameters_summary,
            latency_ms=round(latency_ms, 2),
            status="SUCCESS",
        ))

    def record_failure(
        self,
        step_index: int,
        action_type: str,
        label: Optional[str],
        parameters_summary: str,
        latency_ms: float,
        error_details: str,
    ) -> None:
        self.step_events.append(AuditStepEvent(
            step_index=step_index,
            action_type=action_type,
            label=label,
            timestamp_offset_ms=self._offset_ms(),
            parameters_summary=parameters_summary,
            latency_ms=round(latency_ms, 2),
            status="ERROR",
            error_details=error_details,
        ))

    def record_skipped(
        self,
        step_index: int,
        action_type: str,
        label: Optional[str],
        error_details: Optional[str] = None,
    ) -> None:
        self.step_events.append(AuditStepEvent(
            step_index=step_index,
            action_type=action_type,
            label=label,
            timestamp_offset_ms=self._offset_ms(),
            parameters_summary="Step skipped",
            latency_ms=0.0,
            status="SKIPPED",
            error_details=error_details,
        ))

    def record_retried(
        self,
        step_index: int,
        action_type: str,
        label: Optional[str],
        error_details: str,
    ) -> None:
        self.step_events.append(AuditStepEvent(
            step_index=step_index,
            action_type=action_type,
            label=label,
            timestamp_offset_ms=self._offset_ms(),
            parameters_summary="Step execution retried",
            latency_ms=0.0,
            status="RETRIED",
            error_details=error_details,
        ))

    def generate_log(self, final_status: Literal["SUCCESS", "FAILED", "ABORTED"]) -> KutomotoAuditLog:
        duration = round(time.perf_counter() - self.start_perf, 2)
        successful = sum(1 for e in self.step_events if e.status == "SUCCESS")
        failed = sum(1 for e in self.step_events if e.status == "ERROR")
        retried = sum(1 for e in self.step_events if e.status == "RETRIED")

        try:
            op_user = os.getlogin()
        except Exception:
            op_user = "enterprise_user"

        src_mode = getattr(self.workflow, "source_mode", "manual_step_flow")
        src_val = src_mode.value if hasattr(src_mode, "value") else str(src_mode)

        return KutomotoAuditLog(
            workflow_id=getattr(self.workflow, "id", str(uuid.uuid4())),
            workflow_name=getattr(self.workflow, "name", "Workflow"),
            source_mode=src_val,  # type: ignore
            operator_username=op_user,
            host_machine=platform.node(),
            os_version=f"{platform.system()} {platform.release()} ({platform.version()})",
            target_application=self._target_app_info,
            execution_summary=AuditExecutionSummary(
                total_steps=len(getattr(self.workflow, "steps", [])),
                successful_steps=successful,
                failed_steps=failed,
                retried_steps=retried,
                duration_seconds=duration,
                final_status=final_status,
            ),
            step_events=self.step_events,
        )

    def write_to_disk(self, log: KutomotoAuditLog, base_dir: Optional[Path] = None) -> Path:
        target_dir = base_dir or (Path.home() / ".kutomoto" / "audit")
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"audit_{log.workflow_id}_{log.execution_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        out_path = target_dir / filename
        out_path.write_text(log.model_dump_json(indent=2), encoding="utf-8")
        return out_path
