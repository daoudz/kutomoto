"""
kutomoto.engine.runner
Asynchronous Workflow Execution Engine coordinating steps, safety, and telemetry.
Copyrights reserved to 90Studio
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
import os
import platform
import re
import time
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple
import uuid

from kutomoto.engine.audit import AuditLogger, CredentialMasker, KutomotoAuditLog
from kutomoto.engine.fsm import ExecutionFSM, ExecutionState, FSMEvent
from kutomoto.engine.safety import SafetyGuard, SafetyException
from kutomoto.engine.schema import (
    ActionType,
    ErrorRecoveryPolicy,
    KutomotoWorkflow,
    SubmitMethod,
    WorkflowStep,
)

logger = logging.getLogger("kutomoto.runner")


class IWin32Driver(Protocol):
    """Protocol / Interface contract for Win32 automation driver."""
    def set_dpi_awareness(self) -> bool: ...
    def get_screen_dimensions(self) -> Tuple[int, int]: ...
    def get_cursor_pos(self) -> Tuple[int, int]: ...
    def set_cursor_pos(self, x: int, y: int) -> None: ...
    def get_foreground_window(self) -> int: ...
    def find_window(self, title_pattern: str, match_mode: str = "contains", process_name: Optional[str] = None) -> Optional[int]: ...
    def focus_window(self, hwnd: int, timeout_ms: int = 1500) -> bool: ...
    def get_window_bounds(self, hwnd: int) -> Tuple[int, int, int, int]: ...
    def get_client_rect(self, hwnd: int) -> Tuple[int, int, int, int]: ...
    def client_to_screen(self, hwnd: int, client_x: int, client_y: int) -> Tuple[int, int]: ...
    def send_click(self, x: int, y: int, button: str = "left", click_count: int = 1) -> None: ...
    def send_mouse_move(self, x: int, y: int) -> None: ...
    def send_text(self, text: str, delay_between_keys_ms: int = 20, use_clipboard_threshold: int = 40) -> None: ...
    def send_key_press(self, key_name: str, repeat_count: int = 1) -> None: ...
    def send_hotkey(self, modifiers: List[str], key: str) -> None: ...
    def clear_field(self, strategy: str = "select_all_backspace") -> None: ...
    def send_scroll(self, delta_x: int, delta_y: int) -> None: ...
    def release_all_modifiers(self) -> None: ...


@dataclass
class ExecutionContext:
    workflow: KutomotoWorkflow
    execution_id: str
    target_hwnd: Optional[int] = None
    target_bounds: Optional[Tuple[int, int, int, int]] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    current_step_index: int = 0
    step_retry_count: int = 0
    is_paused: bool = False
    abort_requested: bool = False
    pause_event: asyncio.Event = field(default_factory=asyncio.Event)
    start_time: float = 0.0
    operator_username: str = ""
    host_machine: str = ""


class WorkflowRunner:
    """
    Asynchronous executor loop for kutomoto form-filling workflows.
    Enforces the 7-State FSM, loss-of-focus guardian, safety guardrails,
    variable interpolation, and 90Studio compliance audit logging.
    """

    def __init__(
        self,
        driver: Any,
        audit_logger: Optional[AuditLogger] = None,
        telemetry_callback: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
        safety_guard: Optional[SafetyGuard] = None,
        prompt_resolver: Optional[Any] = None,
    ):
        self._driver = driver
        self._initial_audit_logger = audit_logger
        self._audit_logger = audit_logger
        self._telemetry_cb = telemetry_callback
        self._safety_guard = safety_guard or SafetyGuard(driver=driver)
        self._prompt_resolver = prompt_resolver
        self._fsm = ExecutionFSM()
        self._ctx: Optional[ExecutionContext] = None
        self._has_run_once: bool = False

    @property
    def fsm(self) -> ExecutionFSM:
        return self._fsm

    @property
    def state(self) -> ExecutionState:
        return self._fsm.state

    @property
    def context(self) -> Optional[ExecutionContext]:
        return self._ctx

    async def _emit_telemetry(self, event_name: str, payload: Dict[str, Any]) -> None:
        if self._telemetry_cb:
            try:
                res = self._telemetry_cb(event_name, payload)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                logger.debug("Telemetry callback error for %s: %s", event_name, e)

    def _interpolate_variables(self, text: str, variables: Dict[str, Any]) -> str:
        """Replaces {{var_name}} occurrences with runtime variable values."""
        if not text or "{{" not in text:
            return text

        def repl(match):
            var_name = match.group(1).strip()
            if var_name in variables:
                val = variables[var_name]
                if val is not None:
                    return str(val)
            return match.group(0)

        return re.sub(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", repl, text)

    def _summarize_parameters(self, step: WorkflowStep) -> str:
        p = step.parameters
        is_sec = p.is_secret if hasattr(p, "is_secret") else False
        return CredentialMasker.mask_parameter_summary(step.action_type.value, p, is_sec)

    async def _check_loss_of_focus(self, ctx: ExecutionContext) -> None:
        """Edge Case E13: Active Browser Tab or Window Switching Guardian."""
        if not ctx.target_hwnd:
            return

        current_fg = self._driver.get_foreground_window()
        if current_fg != ctx.target_hwnd:
            # Trigger Loss-of-Focus FSM transition to PAUSED (T10)
            if self._fsm.can_trigger(FSMEvent.FOCUS_LOST):
                await self._fsm.trigger(FSMEvent.FOCUS_LOST)
            ctx.pause_event.clear()
            await self._emit_telemetry("focus_lost_warning", {
                "expected_hwnd": ctx.target_hwnd,
                "actual_hwnd": current_fg,
                "message": "Target application lost active focus. Execution automatically paused.",
            })
            # Wait until operator refocuses target window or clicks resume
            await ctx.pause_event.wait()

    async def _cleanup_after_abort(self) -> None:
        """Purges pressed keys and releases all modifiers."""
        try:
            self._safety_guard.emergency_cleanup()
        except Exception:
            pass
        try:
            self._driver.release_all_modifiers()
        except Exception:
            pass

    def _finalize_audit(self, ctx: ExecutionContext, final_status: str) -> KutomotoAuditLog:
        if self._audit_logger:
            return self._audit_logger.generate_log(final_status)  # type: ignore
        # Create minimal fallback audit log
        try:
            op_user = os.getlogin()
        except Exception:
            op_user = "enterprise_user"

        return KutomotoAuditLog(
            workflow_id=ctx.workflow.id,
            workflow_name=ctx.workflow.name,
            source_mode=ctx.workflow.source_mode.value,  # type: ignore
            operator_username=op_user,
            host_machine=platform.node(),
            os_version=f"{platform.system()} {platform.release()}",
            target_application={  # type: ignore
                "title": ctx.workflow.target_application.window_title_pattern,
                "hwnd": ctx.target_hwnd or 0,
                "process_name": ctx.workflow.target_application.process_name or "unknown",
                "pid": 0,
            },
            execution_summary={  # type: ignore
                "total_steps": len(ctx.workflow.steps),
                "successful_steps": 0,
                "failed_steps": 0,
                "retried_steps": 0,
                "duration_seconds": 0.0,
                "final_status": final_status,
            },
            step_events=[],
        )

    # --------------------------------------------------------------------------
    # Step Dispatchers for All 10 Atomic Actions
    # --------------------------------------------------------------------------

    async def _dispatch_action(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
        action = step.action_type
        if action == ActionType.FOCUS_WINDOW:
            await self._execute_focus_window(step, ctx)
        elif action == ActionType.CLICK:
            await self._execute_click(step, ctx)
        elif action == ActionType.TYPE_TEXT:
            await self._execute_type_text(step, ctx)
        elif action == ActionType.KEY_PRESS:
            await self._execute_key_press(step, ctx)
        elif action == ActionType.HOTKEY:
            await self._execute_hotkey(step, ctx)
        elif action == ActionType.CLEAR_FIELD:
            await self._execute_clear_field(step, ctx)
        elif action == ActionType.DELAY:
            await self._execute_delay(step, ctx)
        elif action == ActionType.SUBMIT:
            await self._execute_submit(step, ctx)
        elif action == ActionType.SCROLL:
            await self._execute_scroll(step, ctx)
        elif action == ActionType.PROMPT_USER_INPUT:
            await self._execute_prompt_user_input(step, ctx)
        else:
            raise ValueError(f"Unknown action type: {action}")

    async def _execute_focus_window(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
        pattern = step.parameters.window_title_pattern or ctx.workflow.target_application.window_title_pattern
        mode = step.parameters.match_mode or ctx.workflow.target_application.match_mode
        proc = step.parameters.process_name or ctx.workflow.target_application.process_name

        mode_str = mode.value if hasattr(mode, "value") else str(mode)
        hwnd = self._driver.find_window(pattern, match_mode=mode_str, process_name=proc)
        if not hwnd:
            raise RuntimeError(f"Target window matching '{pattern}' (process: {proc}) not found.")

        ctx.target_hwnd = hwnd
        self._safety_guard.set_target_hwnd(hwnd)
        success = self._driver.focus_window(hwnd)
        if not success:
            raise RuntimeError(f"Failed to bring target window 0x{hwnd:08X} to foreground.")

        if hasattr(self._driver, "get_client_rect"):
            ctx.target_bounds = self._driver.get_client_rect(hwnd)
        elif hasattr(self._driver, "get_client_bounds"):
            ctx.target_bounds = self._driver.get_client_bounds(hwnd)
        elif hasattr(self._driver, "get_window_bounds"):
            ctx.target_bounds = self._driver.get_window_bounds(hwnd)

        if self._audit_logger:
            self._audit_logger.set_target_app_details(
                hwnd=hwnd,
                title=pattern,
                process_name=proc or "unknown",
            )

    async def _execute_click(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
        p = step.parameters
        coord_mode = p.coordinate_mode.value if hasattr(p.coordinate_mode, "value") else str(p.coordinate_mode)
        btn = p.button.value if hasattr(p.button, "value") else str(p.button)
        click_count = p.click_count or 1

        if coord_mode == "normalized":
            if p.norm_x is None or p.norm_y is None:
                raise ValueError(f"Normalized click requires norm_x and norm_y in step {step.sequence_index}")
            if not ctx.target_hwnd:
                # Fallback to current foreground window
                ctx.target_hwnd = self._driver.get_foreground_window()
                if not ctx.target_hwnd:
                    raise RuntimeError("Cannot compute normalized coordinates: target_hwnd not resolved.")

            if hasattr(self._driver, "get_client_rect"):
                rect = self._driver.get_client_rect(ctx.target_hwnd)
            elif hasattr(self._driver, "get_client_bounds"):
                rect = self._driver.get_client_bounds(ctx.target_hwnd)
            else:
                rect = self._driver.get_window_bounds(ctx.target_hwnd)

            # Standardized geometry: rect is (screen_left, screen_top, width, height)
            client_w = rect[2]
            client_h = rect[3]
            client_x = int(round(p.norm_x * client_w))
            client_y = int(round(p.norm_y * client_h))

            if hasattr(self._driver, "client_to_screen"):
                screen_x, screen_y = self._driver.client_to_screen(ctx.target_hwnd, client_x, client_y)
            elif hasattr(self._driver, "client_to_screen_coords"):
                screen_x, screen_y = self._driver.client_to_screen_coords(ctx.target_hwnd, client_x, client_y)
            else:
                screen_x = rect[0] + client_x
                screen_y = rect[1] + client_y
        elif coord_mode == "window_client":
            if hasattr(self._driver, "client_to_screen") and ctx.target_hwnd:
                screen_x, screen_y = self._driver.client_to_screen(ctx.target_hwnd, int(p.x or 0), int(p.y or 0))
            elif hasattr(self._driver, "client_to_screen_coords") and ctx.target_hwnd:
                screen_x, screen_y = self._driver.client_to_screen_coords(ctx.target_hwnd, int(p.x or 0), int(p.y or 0))
            else:
                screen_x, screen_y = int(p.x or 0), int(p.y or 0)
        else:  # screen
            screen_x, screen_y = int(p.x or 0), int(p.y or 0)

        self._safety_guard.register_intentional_mouse_move(screen_x, screen_y)
        self._driver.send_click(screen_x, screen_y, button=btn, click_count=click_count)

    async def _execute_type_text(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
        raw_text = step.parameters.text or ""
        resolved_text = self._interpolate_variables(raw_text, ctx.variables)

        # Edge case E14: Blank or empty string payload bypasses typing loop
        if not resolved_text:
            return

        delay = step.parameters.keystroke_delay_ms or ctx.workflow.execution_settings.typing_speed_ms
        threshold = getattr(step.parameters, "use_clipboard_threshold", 40)
        self._driver.send_text(
            resolved_text,
            delay_between_keys_ms=delay,
            use_clipboard_threshold=threshold,
        )

    async def _execute_key_press(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
        key = step.parameters.key or "tab"
        repeat = step.parameters.repeat_count or 1
        self._driver.send_key_press(key, repeat_count=repeat)

    async def _execute_hotkey(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
        keys = step.parameters.keys or []
        if not keys:
            return
        modifiers = [k.lower() for k in keys[:-1]]
        key = keys[-1].lower()
        self._driver.send_hotkey(modifiers, key)

    async def _execute_clear_field(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
        strat = step.parameters.clear_strategy
        strat_val = strat.value if hasattr(strat, "value") else str(strat)
        self._driver.clear_field(strategy=strat_val)

    async def _execute_delay(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
        duration_ms = step.parameters.duration_ms or 0
        remaining = duration_ms / 1000.0
        while remaining > 0:
            if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                break
            if not ctx.pause_event.is_set():
                await ctx.pause_event.wait()
            chunk = min(0.05, remaining)
            await asyncio.sleep(chunk)
            remaining -= chunk

    async def _execute_submit(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
        method = step.parameters.submit_method
        method_val = method.value if hasattr(method, "value") else str(method)
        if method_val == SubmitMethod.ENTER_KEY.value:
            self._driver.send_key_press("enter", repeat_count=1)
        elif method_val == SubmitMethod.BUTTON_CLICK.value:
            await self._execute_click(step, ctx)

    async def _execute_scroll(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
        dx = step.parameters.delta_x
        dy = step.parameters.delta_y
        self._driver.send_scroll(delta_x=dx, delta_y=dy)

    async def _execute_prompt_user_input(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
        var_name = step.parameters.variable_name or "variable"
        msg = step.parameters.prompt_message or f"Enter value for {var_name}:"

        await self._emit_telemetry("user_prompt_requested", {
            "variable_name": var_name,
            "prompt_message": msg,
            "step_index": step.sequence_index,
        })

        if self._prompt_resolver and hasattr(self._prompt_resolver, "request_input"):
            is_sec = getattr(step.parameters, "is_password", False) or getattr(step.parameters, "is_secret", False)
            res = self._prompt_resolver.request_input(var_name, msg, is_sec)
            if asyncio.iscoroutine(res):
                value = await res
            else:
                value = res
            ctx.variables[var_name] = value
        elif var_name in ctx.variables:
            # Already bound
            pass
        else:
            ctx.variables[var_name] = ""

    # --------------------------------------------------------------------------
    # Main Execution Flow
    # --------------------------------------------------------------------------

    async def execute(
        self,
        workflow: KutomotoWorkflow,
        runtime_variables: Optional[Dict[str, Any]] = None,
    ) -> KutomotoAuditLog:
        # Support repeated execution: reset FSM if in terminal state
        if self._fsm.is_terminal:
            await self._fsm.trigger(FSMEvent.RESET)

        # Reset safety guard state to ensure clean run isolation
        if self._safety_guard and hasattr(self._safety_guard, "reset"):
            self._safety_guard.reset()

        # T01: IDLE -> VALIDATING
        await self._fsm.trigger(FSMEvent.EXECUTE_START)

        # Context Initialization
        try:
            op_user = os.getlogin()
        except Exception:
            op_user = "enterprise_user"

        if self._initial_audit_logger is not None and not self._has_run_once:
            exec_id = self._initial_audit_logger.execution_id
        else:
            exec_id = str(uuid.uuid4())
        self._has_run_once = True

        ctx = ExecutionContext(
            workflow=workflow,
            execution_id=exec_id,
            variables={v.name: v.default_value for v in workflow.variables},
            start_time=time.perf_counter(),
            operator_username=op_user,
            host_machine=platform.node(),
        )
        if runtime_variables:
            ctx.variables.update(runtime_variables)
        ctx.pause_event.set()  # Unpaused initially
        self._ctx = ctx

        # Clean Execution State Isolation for Audit Logger:
        if self._initial_audit_logger is not None:
            self._audit_logger = self._initial_audit_logger
            if hasattr(self._audit_logger, "reset"):
                self._audit_logger.reset(execution_id=ctx.execution_id, workflow=workflow)
            else:
                self._audit_logger.execution_id = ctx.execution_id
                self._audit_logger.workflow = workflow
                self._audit_logger.step_events.clear()
                self._audit_logger.start_perf = time.perf_counter()
        else:
            self._audit_logger = AuditLogger(execution_id=ctx.execution_id, workflow=workflow)

        # Validation Guard: Check required variables (permit valid numeric 0, 0.0, and False)
        missing_vars = [
            v.name for v in workflow.variables
            if v.required and (ctx.variables.get(v.name) is None or ctx.variables.get(v.name) == "")
        ]
        if missing_vars:
            await self._fsm.trigger(FSMEvent.VALIDATION_FAILED)  # T03
            raise ValueError(f"Workflow execution blocked: missing required variables: {missing_vars}")

        # T02: VALIDATING -> COUNTDOWN
        await self._fsm.trigger(FSMEvent.VALIDATION_OK)

        # Countdown Phase
        cd_secs = workflow.execution_settings.countdown_seconds
        for rem in range(cd_secs, 0, -1):
            if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                if self._fsm.can_trigger(FSMEvent.ABORT_TRIGGERED):
                    await self._fsm.trigger(FSMEvent.ABORT_TRIGGERED)  # T06
                await self._cleanup_after_abort()
                if self._fsm.can_trigger(FSMEvent.CLEANUP_DONE):
                    await self._fsm.trigger(FSMEvent.CLEANUP_DONE)
                return self._finalize_audit(ctx, "ABORTED")
            await self._emit_telemetry("countdown_tick", {"remaining": rem})
            await self._fsm.trigger(FSMEvent.COUNTDOWN_TICK)  # T04
            await asyncio.sleep(0.05 if cd_secs <= 0 else 0.1 if os.environ.get("KUTOMOTO_TEST_FAST") else 1.0)

        if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
            if self._fsm.can_trigger(FSMEvent.ABORT_TRIGGERED):
                await self._fsm.trigger(FSMEvent.ABORT_TRIGGERED)
            await self._cleanup_after_abort()
            if self._fsm.can_trigger(FSMEvent.CLEANUP_DONE):
                await self._fsm.trigger(FSMEvent.CLEANUP_DONE)
            return self._finalize_audit(ctx, "ABORTED")

        # T05: COUNTDOWN -> RUNNING
        await self._fsm.trigger(FSMEvent.COUNTDOWN_DONE)

        # Set DPI Awareness
        try:
            self._driver.set_dpi_awareness()
        except Exception as e:
            logger.debug("DPI awareness notice: %s", e)

        # Initialize audit logger if provided
        if not self._audit_logger:
            self._audit_logger = AuditLogger(execution_id=ctx.execution_id, workflow=workflow)

        # Step Execution Loop
        for idx, step in enumerate(workflow.steps):
            ctx.current_step_index = idx + 1
            if not step.enabled:
                if self._audit_logger:
                    self._audit_logger.record_skipped(idx + 1, step.action_type.value, step.label)
                continue

            # Check pause state before executing step
            if not ctx.pause_event.is_set():
                await ctx.pause_event.wait()

            # Check abort request
            if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                if self._fsm.can_trigger(FSMEvent.ABORT_TRIGGERED):
                    await self._fsm.trigger(FSMEvent.ABORT_TRIGGERED)  # T11 or T14
                await self._cleanup_after_abort()
                if self._fsm.can_trigger(FSMEvent.CLEANUP_DONE):
                    await self._fsm.trigger(FSMEvent.CLEANUP_DONE)    # T18 (only if from STOPPING)
                return self._finalize_audit(ctx, "ABORTED")

            # Pre-step Focus Guardian (E13)
            if step.action_type != ActionType.FOCUS_WINDOW:
                await self._check_loss_of_focus(ctx)
            if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                return self._finalize_audit(ctx, "ABORTED")

            # Pre-delay
            if step.pre_delay_ms > 0:
                pre_remaining = step.pre_delay_ms / 1000.0
                while pre_remaining > 0:
                    if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                        break
                    if not ctx.pause_event.is_set():
                        await ctx.pause_event.wait()
                    chunk = min(0.05, pre_remaining)
                    await asyncio.sleep(chunk)
                    pre_remaining -= chunk

            if not ctx.pause_event.is_set():
                await ctx.pause_event.wait()

            if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                return self._finalize_audit(ctx, "ABORTED")

            # Step dispatch with retry loop
            step_success = False
            retries_remaining = workflow.execution_settings.max_step_retries

            while not step_success:
                if not ctx.pause_event.is_set():
                    await ctx.pause_event.wait()
                if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                    return self._finalize_audit(ctx, "ABORTED")

                t0 = time.perf_counter()
                try:
                    await self._emit_telemetry("step_started", {
                        "step_index": idx + 1,
                        "action_type": step.action_type.value,
                        "label": step.label,
                    })

                    # Perform safety checks
                    if step.action_type != ActionType.FOCUS_WINDOW:
                        self._safety_guard.pre_step_check(ctx.target_hwnd)

                    await self._dispatch_action(step, ctx)

                    if not ctx.pause_event.is_set():
                        await ctx.pause_event.wait()

                    if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                        return self._finalize_audit(ctx, "ABORTED")

                    latency = (time.perf_counter() - t0) * 1000.0
                    if self._audit_logger:
                        self._audit_logger.record_success(
                            step_index=idx + 1,
                            action_type=step.action_type.value,
                            label=step.label,
                            parameters_summary=self._summarize_parameters(step),
                            latency_ms=latency,
                        )
                    await self._emit_telemetry("step_completed", {
                        "step_index": idx + 1,
                        "latency_ms": latency,
                    })

                    # Ensure runner waits if pause occurred during telemetry broadcast
                    if not ctx.pause_event.is_set():
                        await ctx.pause_event.wait()
                    if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                        return self._finalize_audit(ctx, "ABORTED")

                    step_success = True
                    # T07: RUNNING -> RUNNING (guarded against state PAUSED)
                    if self._fsm.can_trigger(FSMEvent.STEP_SUCCESS):
                        await self._fsm.trigger(FSMEvent.STEP_SUCCESS)

                except SafetyException as sex:
                    latency = (time.perf_counter() - t0) * 1000.0
                    logger.critical("Emergency safety guardrail triggered: %s", sex)
                    if self._audit_logger:
                        self._audit_logger.record_failure(
                            step_index=idx + 1,
                            action_type=step.action_type.value,
                            label=step.label,
                            parameters_summary=self._summarize_parameters(step),
                            latency_ms=latency,
                            error_details=f"Safety Guardrail: {sex}",
                        )
                    if self._fsm.can_trigger(FSMEvent.ABORT_TRIGGERED):
                        await self._fsm.trigger(FSMEvent.ABORT_TRIGGERED)
                    await self._cleanup_after_abort()
                    if self._fsm.can_trigger(FSMEvent.CLEANUP_DONE):
                        await self._fsm.trigger(FSMEvent.CLEANUP_DONE)
                    return self._finalize_audit(ctx, "ABORTED")

                except Exception as ex:
                    if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                        return self._finalize_audit(ctx, "ABORTED")

                    if not ctx.pause_event.is_set():
                        await ctx.pause_event.wait()
                    if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                        return self._finalize_audit(ctx, "ABORTED")

                    latency = (time.perf_counter() - t0) * 1000.0
                    try:
                        cur_pos = self._driver.get_cursor_pos()
                        self._safety_guard.register_intentional_mouse_move(cur_pos[0], cur_pos[1])
                    except Exception:
                        pass
                    policy = workflow.execution_settings.error_recovery_policy
                    policy_val = policy.value if hasattr(policy, "value") else str(policy)

                    # T12: RUNNING -> ERROR_RECOVERY
                    if self._fsm.can_trigger(FSMEvent.STEP_EXCEPTION):
                        await self._fsm.trigger(FSMEvent.STEP_EXCEPTION)

                    if policy_val == ErrorRecoveryPolicy.RETRY_STEP.value and retries_remaining > 0:
                        retries_remaining -= 1
                        ctx.step_retry_count += 1
                        if self._audit_logger:
                            self._audit_logger.record_retried(
                                step_index=idx + 1,
                                action_type=step.action_type.value,
                                label=step.label,
                                error_details=str(ex),
                            )
                        # Release modifiers before retry
                        try:
                            self._driver.release_all_modifiers()
                        except Exception:
                            pass
                        await asyncio.sleep(0.05 if os.environ.get("KUTOMOTO_TEST_FAST") else 0.5)
                        await self._fsm.trigger(FSMEvent.POLICY_RETRY)  # T15
                        continue
                    elif policy_val == ErrorRecoveryPolicy.SKIP_STEP.value:
                        if self._audit_logger:
                            self._audit_logger.record_skipped(
                                step_index=idx + 1,
                                action_type=step.action_type.value,
                                label=step.label,
                                error_details=str(ex),
                            )
                        # Release modifiers before skipping
                        try:
                            self._driver.release_all_modifiers()
                        except Exception:
                            pass
                        await self._fsm.trigger(FSMEvent.POLICY_SKIP)   # T16
                        step_success = True
                    elif policy_val == ErrorRecoveryPolicy.PROMPT_USER.value:
                        prompt_msg = f"Step {idx + 1} ({step.label or step.action_type.value}) failed: {ex}. Select recovery action:"
                        await self._emit_telemetry("user_prompt_requested", {
                            "step_index": idx + 1,
                            "action_type": step.action_type.value,
                            "error": str(ex),
                            "prompt_message": prompt_msg,
                            "options": ["retry", "skip", "abort"],
                        })
                        user_choice = None
                        if self._prompt_resolver and hasattr(self._prompt_resolver, "request_decision"):
                            res = self._prompt_resolver.request_decision(
                                step_index=idx + 1,
                                error=str(ex),
                                options=["retry", "skip", "abort"],
                            )
                            user_choice = await res if asyncio.iscoroutine(res) else res
                        elif self._prompt_resolver and hasattr(self._prompt_resolver, "request_input"):
                            res = self._prompt_resolver.request_input("recovery_action", prompt_msg, False)
                            user_choice = await res if asyncio.iscoroutine(res) else res

                        choice_str = str(user_choice).lower().strip() if user_choice else "abort"
                        if choice_str == "retry" and retries_remaining > 0:
                            retries_remaining -= 1
                            ctx.step_retry_count += 1
                            try:
                                self._driver.release_all_modifiers()
                            except Exception:
                                pass
                            await self._fsm.trigger(FSMEvent.POLICY_RETRY)
                            continue
                        elif choice_str == "skip":
                            if self._audit_logger:
                                self._audit_logger.record_skipped(
                                    step_index=idx + 1,
                                    action_type=step.action_type.value,
                                    label=step.label,
                                    error_details=str(ex),
                                )
                            try:
                                self._driver.release_all_modifiers()
                            except Exception:
                                pass
                            await self._fsm.trigger(FSMEvent.POLICY_SKIP)
                            step_success = True
                        else:  # abort
                            if self._audit_logger:
                                self._audit_logger.record_failure(
                                    step_index=idx + 1,
                                    action_type=step.action_type.value,
                                    label=step.label,
                                    parameters_summary=self._summarize_parameters(step),
                                    latency_ms=latency,
                                    error_details=str(ex),
                                )
                            await self._fsm.trigger(FSMEvent.POLICY_ABORT)
                            await self._cleanup_after_abort()
                            return self._finalize_audit(ctx, "FAILED")
                    else:  # ABORT
                        if self._audit_logger:
                            self._audit_logger.record_failure(
                                step_index=idx + 1,
                                action_type=step.action_type.value,
                                label=step.label,
                                parameters_summary=self._summarize_parameters(step),
                                latency_ms=latency,
                                error_details=str(ex),
                            )
                        await self._fsm.trigger(FSMEvent.POLICY_ABORT)  # T17
                        await self._cleanup_after_abort()
                        return self._finalize_audit(ctx, "FAILED")

            # Post-delay
            post_delay = step.post_delay_ms or (
                0 if os.environ.get("KUTOMOTO_TEST_FAST") else workflow.execution_settings.default_step_delay_ms
            )
            if post_delay > 0:
                post_remaining = post_delay / 1000.0
                while post_remaining > 0:
                    if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                        break
                    if not ctx.pause_event.is_set():
                        await ctx.pause_event.wait()
                    chunk = min(0.05, post_remaining)
                    await asyncio.sleep(chunk)
                    post_remaining -= chunk

            if not ctx.pause_event.is_set():
                await ctx.pause_event.wait()

            if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                return self._finalize_audit(ctx, "ABORTED")

        if not ctx.pause_event.is_set():
            await ctx.pause_event.wait()

        if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
            return self._finalize_audit(ctx, "ABORTED")

        # T08: RUNNING -> COMPLETED (guarded against state PAUSED)
        if self._fsm.can_trigger(FSMEvent.ALL_STEPS_DONE):
            await self._fsm.trigger(FSMEvent.ALL_STEPS_DONE)
        if self._safety_guard and hasattr(self._safety_guard, "reset"):
            self._safety_guard.reset()
        return self._finalize_audit(ctx, "SUCCESS")

    async def pause(self) -> None:
        """Pauses the runner if currently running."""
        if self._fsm.state == ExecutionState.RUNNING:
            await self._fsm.trigger(FSMEvent.USER_PAUSE)  # T09
            if self._ctx:
                self._ctx.pause_event.clear()
            await self._emit_telemetry("execution_paused", {})

    async def resume(self) -> None:
        """Resumes workflow execution from paused state."""
        if self._fsm.state == ExecutionState.PAUSED:
            if self._ctx and self._ctx.target_hwnd:
                try:
                    self._driver.focus_window(self._ctx.target_hwnd)
                except Exception as e:
                    logger.debug("Focus window on resume notice: %s", e)
            await self._fsm.trigger(FSMEvent.USER_RESUME)  # T13: PAUSED -> RUNNING
            if self._ctx:
                # Unblock pause event AFTER FSM has transitioned to RUNNING
                self._ctx.pause_event.set()
            await self._emit_telemetry("execution_resumed", {})

    async def abort(self) -> None:
        """Triggers emergency abort."""
        if self._ctx:
            self._ctx.abort_requested = True
            if self._ctx.pause_event:
                self._ctx.pause_event.set()
        await self._cleanup_after_abort()
        if self._fsm.can_trigger(FSMEvent.ABORT_TRIGGERED):
            await self._fsm.trigger(FSMEvent.ABORT_TRIGGERED)
        if self._fsm.can_trigger(FSMEvent.CLEANUP_DONE):
            await self._fsm.trigger(FSMEvent.CLEANUP_DONE)
