# Milestone 2 Synthesis & Remediation Plan

**Author**: `m2_fix_explorer_1`  
**Working Directory**: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_fix_explorer_1`  
**Milestone**: Milestone 2 — Win32 Automation Core & Workflow Execution Engine (Fix Iteration)  
**Date**: 2026-11-04  
**Target Recipient**: `m2_fix_worker_1` / Orchestrator  
**Copyright**: Copyrights reserved to 90Studio  

---

## 1. Executive Summary

Milestone 2 implementation was evaluated by two independent reviewers (`m2_reviewer_1`, `m2_reviewer_2`) and two empirical challengers (`m2_challenger_1`, `m2_challenger_2`). While the 64-bit ABI memory alignment (`sizeof(INPUT) == 40`), ctypes C-API signatures, UTF-16 surrogate pair decomposition, and Pydantic V2 schemas were found to be of high technical rigor, the milestone received unanimous rejection (`REQUEST_CHANGES` / `FAIL`) due to:

1. **Integrity Violations in Unit Tests**: Five tests in `tests/test_win32_driver.py` and `tests/test_engine.py` were self-certifying tautologies (testing local variables, lists, and dicts against themselves rather than invoking target library functions), while 0% coverage existed for multiple atomic actions and lifecycle methods.
2. **Safety Guardrail Trapping & Bypassing**: Emergency failsafes (`EscapeAbortTriggered`, `CornerFailsafeTriggered`, `MouseDisturbanceDetected`) were caught inside the general step exception handler, causing emergency stops to be retried (delaying shutdown) or skipped (allowing the workflow to finish with `SUCCESS`).
3. **Geometry Interface Contract Mismatch**: `win32_window.py` returns `(screen_left, screen_top, width, height)` for client bounds, while `runner.py` calculated `client_w = rect[2] - rect[0]`, resulting in click targeting errors of 150px+ and inverted coordinates when `screen_left > width`.
4. **FSM Control-Flow & Lifecycle Defects**: `pause()` failed to pause the step loop and crashed the FSM upon step completion; aborting while paused called `CLEANUP_DONE` from terminal `STOPPED`, crashing with `InvalidTransitionError`; `resume()` without a target HWND never cleared the pause lock; and re-executing a completed runner threw an invalid transition error instead of auto-resetting.
5. **Modifier Key Leaks**: Modifier keys were not purged on step failures under `SKIP_STEP` or `RETRY_STEP` policies.
6. **Data & Policy Gaps**: Variable validation rejected valid numeric `0` and boolean `False`; recovery policy `PROMPT_USER` was unhandled and fell into hard abort.

This document synthesizes all findings into an exact, comprehensive remediation plan containing drop-in code modifications for `m2_fix_worker_1`.

---

## 2. Synthesis Matrix of Findings

| ID | Issue Description | Origin | Severity | Affected Files | Resolution |
|---|---|---|---|---|---|
| **D1** | Coordinate geometry contract mismatch (`rect[2] - rect[0]` assumes `right`, got `width`) | Reviewer 1, Reviewer 2, Challenger 2 | Critical | `runner.py`, `safety.py`, `win32_window.py` | Use `rect[2]` and `rect[3]` directly; align `MockWin32Driver.get_client_rect` to return `(x, y, w, h)`; alias `get_client_rect` and `client_to_screen` in `win32_window.py`. |
| **D2** | Emergency safety failsafes swallowed/retried under `SKIP_STEP` / `RETRY_STEP` | Reviewer 1, Reviewer 2, Challenger 1, Challenger 2 | Critical | `runner.py` | Prioritize `SafetyException` catching before general `except Exception`; trigger immediate `ABORT_TRIGGERED`, purge modifiers, and finalize audit as `ABORTED`. |
| **D3** | `pause()` does not pause step execution loop, crashes FSM with `InvalidTransitionError` on `STEP_SUCCESS` | Reviewer 2, Challenger 1 | Critical | `runner.py` | Await `ctx.pause_event.wait()` at loop start and inside delay steps. |
| **D4** | Aborting from `PAUSED` state calls `CLEANUP_DONE` when already `STOPPED`, crashing FSM | Reviewer 2, Challenger 1 | High | `runner.py` | Guard `CLEANUP_DONE` transition with `self._fsm.can_trigger(FSMEvent.CLEANUP_DONE)`. |
| **D5** | `resume()` without target HWND bypasses `pause_event.set()`, deadlocking workflow | Challenger 1 | High | `runner.py` | Move `ctx.pause_event.set()` outside the `if ctx.target_hwnd:` conditional block. |
| **D6** | Inability to re-execute runner instance from terminal state (`COMPLETED`/`STOPPED`/`ERROR`) | Reviewer 2 | Medium | `runner.py` | If `self._fsm.is_terminal`, trigger `FSMEvent.RESET` at start of `execute()`. |
| **D7** | Modifier keys leaked on step failures under `SKIP_STEP` and `RETRY_STEP` | Reviewer 1, Challenger 2 | High | `runner.py` | Call `self._driver.release_all_modifiers()` in both retry and skip exception branches. |
| **D8** | Required variable validation rejects valid numeric `0` and boolean `False` | Challenger 1 | Medium | `runner.py` | Check `ctx.variables.get(v.name) is None or ctx.variables.get(v.name) == ""` instead of `not ctx.variables.get(v.name)`. |
| **D9** | ErrorRecoveryPolicy `PROMPT_USER` unhandled, defaults to hard abort without telemetry | Challenger 1 | Medium | `runner.py` | Implement `elif policy_val == ErrorRecoveryPolicy.PROMPT_USER.value:` branch emitting telemetry and consulting `prompt_resolver`. |
| **D10** | Tautological/self-certifying unit tests in `test_win32_driver.py` and `test_engine.py` | Reviewer 1 | Critical (Integrity) | `test_win32_driver.py`, `test_engine.py` | Replace local-var tests with genuine tests calling `clear_field()`, `normalized_to_screen_coords()`, `send_text()`, `_execute_delay()`, `_execute_prompt_user_input()`. |
| **D11** | Zero test coverage for actions `HOTKEY`, `DELAY`, `SCROLL`, `PROMPT_USER_INPUT`, `pause()`, `resume()`, `abort()` | Reviewer 1 | High | `test_engine.py` | Add comprehensive unit tests covering all 10 actions and full lifecycle controls. |

---

## 3. Drop-In Code Modifications

### 3.1 `src/kutomoto/engine/runner.py`

#### Modification 1: Support Re-Execution by Resetting Terminal FSM
**Location**: `src/kutomoto/engine/runner.py`, at start of `execute()` (around line 383)

```python
<<<<
        # T01: IDLE -> VALIDATING
        await self._fsm.trigger(FSMEvent.EXECUTE_START)
====
        # Support repeated execution: reset FSM if in terminal state
        if self._fsm.is_terminal:
            await self._fsm.trigger(FSMEvent.RESET)

        # T01: IDLE -> VALIDATING
        await self._fsm.trigger(FSMEvent.EXECUTE_START)
>>>>
```

#### Modification 2: Correct Required Variable Validation for 0 and False
**Location**: `src/kutomoto/engine/runner.py`, lines 406–409

```python
<<<<
        # Validation Guard: Check required variables
        missing_vars = [v.name for v in workflow.variables if v.required and not ctx.variables.get(v.name)]
        if missing_vars:
            await self._fsm.trigger(FSMEvent.VALIDATION_FAILED)  # T03
            raise ValueError(f"Workflow execution blocked: missing required variables: {missing_vars}")
====
        # Validation Guard: Check required variables (permit valid numeric 0, 0.0, and False)
        missing_vars = [
            v.name for v in workflow.variables
            if v.required and (ctx.variables.get(v.name) is None or ctx.variables.get(v.name) == "")
        ]
        if missing_vars:
            await self._fsm.trigger(FSMEvent.VALIDATION_FAILED)  # T03
            raise ValueError(f"Workflow execution blocked: missing required variables: {missing_vars}")
>>>>
```

#### Modification 3: Coordinate Arithmetic & Geometry Harmonization
**Location**: `src/kutomoto/engine/runner.py`, lines 267–286

```python
<<<<
            if hasattr(self._driver, "get_client_rect"):
                rect = self._driver.get_client_rect(ctx.target_hwnd)
            else:
                rect = self._driver.get_window_bounds(ctx.target_hwnd)

            client_w = rect[2] - rect[0]
            client_h = rect[3] - rect[1]
            client_x = int(round(p.norm_x * client_w))
            client_y = int(round(p.norm_y * client_h))

            if hasattr(self._driver, "client_to_screen"):
                screen_x, screen_y = self._driver.client_to_screen(ctx.target_hwnd, client_x, client_y)
            else:
                screen_x = rect[0] + client_x
                screen_y = rect[1] + client_y
        elif coord_mode == "window_client":
            if hasattr(self._driver, "client_to_screen") and ctx.target_hwnd:
                screen_x, screen_y = self._driver.client_to_screen(ctx.target_hwnd, int(p.x or 0), int(p.y or 0))
            else:
                screen_x, screen_y = int(p.x or 0), int(p.y or 0)
====
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
>>>>
```

Also in `_execute_focus_window` (lines 240–244):
```python
<<<<
        if hasattr(self._driver, "get_client_rect"):
            ctx.target_bounds = self._driver.get_client_rect(hwnd)
        elif hasattr(self._driver, "get_window_bounds"):
            ctx.target_bounds = self._driver.get_window_bounds(hwnd)
====
        if hasattr(self._driver, "get_client_rect"):
            ctx.target_bounds = self._driver.get_client_rect(hwnd)
        elif hasattr(self._driver, "get_client_bounds"):
            ctx.target_bounds = self._driver.get_client_bounds(hwnd)
        elif hasattr(self._driver, "get_window_bounds"):
            ctx.target_bounds = self._driver.get_window_bounds(hwnd)
>>>>
```

#### Modification 4: Delay Step Supports Pausing
**Location**: `src/kutomoto/engine/runner.py`, lines 327–336

```python
<<<<
    async def _execute_delay(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
        duration_ms = step.parameters.duration_ms or 0
        remaining = duration_ms / 1000.0
        while remaining > 0:
            if ctx.abort_requested:
                break
            chunk = min(0.05, remaining)
            await asyncio.sleep(chunk)
            remaining -= chunk
====
    async def _execute_delay(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
        duration_ms = step.parameters.duration_ms or 0
        remaining = duration_ms / 1000.0
        while remaining > 0:
            if ctx.abort_requested:
                break
            if not ctx.pause_event.is_set():
                await ctx.pause_event.wait()
            chunk = min(0.05, remaining)
            await asyncio.sleep(chunk)
            remaining -= chunk
>>>>
```

#### Modification 5: Step Loop Pause Waiting and Safe Abort
**Location**: `src/kutomoto/engine/runner.py`, lines 438–451

```python
<<<<
        # Step Execution Loop
        for idx, step in enumerate(workflow.steps):
            ctx.current_step_index = idx + 1
            if not step.enabled:
                if self._audit_logger:
                    self._audit_logger.record_skipped(idx + 1, step.action_type.value, step.label)
                continue

            # Check abort request
            if ctx.abort_requested:
                await self._fsm.trigger(FSMEvent.ABORT_TRIGGERED)  # T11
                await self._cleanup_after_abort()
                await self._fsm.trigger(FSMEvent.CLEANUP_DONE)    # T18
                return self._finalize_audit(ctx, "ABORTED")
====
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
            if ctx.abort_requested:
                if self._fsm.can_trigger(FSMEvent.ABORT_TRIGGERED):
                    await self._fsm.trigger(FSMEvent.ABORT_TRIGGERED)  # T11 or T14
                await self._cleanup_after_abort()
                if self._fsm.can_trigger(FSMEvent.CLEANUP_DONE):
                    await self._fsm.trigger(FSMEvent.CLEANUP_DONE)    # T18 (only if from STOPPING)
                return self._finalize_audit(ctx, "ABORTED")
>>>>
```

#### Modification 6: Safety Exception Prioritization, Modifier Release, and Prompt User Recovery
**Location**: `src/kutomoto/engine/runner.py`, lines 496–545
Import `SafetyException` at top of `runner.py`:
```python
from kutomoto.engine.safety import SafetyGuard, SafetyException
```
Then replace lines 496–545:
```python
<<<<
                except Exception as ex:
                    latency = (time.perf_counter() - t0) * 1000.0
                    try:
                        cur_pos = self._driver.get_cursor_pos()
                        self._safety_guard.register_intentional_mouse_move(cur_pos[0], cur_pos[1])
                    except Exception:
                        pass
                    policy = workflow.execution_settings.error_recovery_policy
                    policy_val = policy.value if hasattr(policy, "value") else str(policy)

                    # T12: RUNNING -> ERROR_RECOVERY
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
                        await self._fsm.trigger(FSMEvent.POLICY_SKIP)   # T16
                        step_success = True
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
====
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
                    latency = (time.perf_counter() - t0) * 1000.0
                    try:
                        cur_pos = self._driver.get_cursor_pos()
                        self._safety_guard.register_intentional_mouse_move(cur_pos[0], cur_pos[1])
                    except Exception:
                        pass
                    policy = workflow.execution_settings.error_recovery_policy
                    policy_val = policy.value if hasattr(policy, "value") else str(policy)

                    # T12: RUNNING -> ERROR_RECOVERY
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
>>>>
```

#### Modification 7: Reliable Resume and Abort
**Location**: `src/kutomoto/engine/runner.py`, lines 565–581

```python
<<<<
    async def resume(self) -> None:
        """Resumes workflow execution from paused state."""
        if self._fsm.state == ExecutionState.PAUSED:
            if self._ctx and self._ctx.target_hwnd:
                self._driver.focus_window(self._ctx.target_hwnd)
                self._ctx.pause_event.set()
            await self._fsm.trigger(FSMEvent.USER_RESUME)  # T13
            await self._emit_telemetry("execution_resumed", {})

    async def abort(self) -> None:
        """Triggers emergency abort."""
        if self._ctx:
            self._ctx.abort_requested = True
            if self._ctx.pause_event:
                self._ctx.pause_event.set()
        await self._cleanup_after_abort()
====
    async def resume(self) -> None:
        """Resumes workflow execution from paused state."""
        if self._fsm.state == ExecutionState.PAUSED:
            if self._ctx:
                if self._ctx.target_hwnd:
                    try:
                        self._driver.focus_window(self._ctx.target_hwnd)
                    except Exception as e:
                        logger.debug("Focus window on resume notice: %s", e)
                # Unblock pause event regardless of whether target_hwnd is set
                self._ctx.pause_event.set()
            await self._fsm.trigger(FSMEvent.USER_RESUME)  # T13
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
>>>>
```

---

### 3.2 `src/kutomoto/engine/safety.py`

#### Modification 1: Align `MockWin32Driver.get_client_rect` and Aliases
**Location**: `src/kutomoto/engine/safety.py`, lines 452–461

```python
<<<<
    def get_client_rect(self, hwnd: int) -> Tuple[int, int, int, int]:
        bounds = self.get_window_bounds(hwnd)
        # Returns (left, top, right, bottom)
        return (bounds[0], bounds[1], bounds[0] + bounds[2], bounds[1] + bounds[3])

    def client_to_screen(self, hwnd: int, client_x: int, client_y: int) -> Tuple[int, int]:
        self.calls.append({"method": "client_to_screen", "hwnd": hwnd, "x": client_x, "y": client_y})
        win_x, win_y, _, _ = self.get_window_bounds(hwnd)
        return (win_x + int(client_x), win_y + int(client_y))
====
    def get_client_rect(self, hwnd: int) -> Tuple[int, int, int, int]:
        bounds = self.get_window_bounds(hwnd)
        # Standardized return: (screen_left, screen_top, width, height)
        return (bounds[0], bounds[1], bounds[2], bounds[3])

    def get_client_bounds(self, hwnd: int) -> Tuple[int, int, int, int]:
        return self.get_client_rect(hwnd)

    def client_to_screen(self, hwnd: int, client_x: int, client_y: int) -> Tuple[int, int]:
        self.calls.append({"method": "client_to_screen", "hwnd": hwnd, "x": client_x, "y": client_y})
        win_x, win_y, _, _ = self.get_window_bounds(hwnd)
        return (win_x + int(client_x), win_y + int(client_y))

    def client_to_screen_coords(self, hwnd: int, client_x: int, client_y: int) -> Tuple[int, int]:
        return self.client_to_screen(hwnd, client_x, client_y)
>>>>
```

---

### 3.3 `src/kutomoto/automation/win32_window.py`

#### Modification 1: Provide Contract Aliases
**Location**: `src/kutomoto/automation/win32_window.py`, at bottom (around line 407)

```python
# Provide aliases for engine interface harmonization
get_client_rect = get_client_bounds
client_to_screen = client_to_screen_coords

__all__ = [
    ...
    "get_client_bounds",
    "get_client_rect",
    "client_to_screen_coords",
    "client_to_screen",
    ...
]
```
Also expose `get_client_rect` and `client_to_screen` in `src/kutomoto/automation/__init__.py`.

---

### 3.4 `tests/test_win32_driver.py`

#### Modification 1: Replace Tautological Tests with Authentic Tests
Replace lines 78–114 and 136–144 with:

```python
def test_normalized_coordinate_translation(monkeypatch):
    """
    Tests translating normalized [0.0, 1.0] coordinates to physical screen pixels
    by executing kutomoto.automation.win32_window.normalized_to_screen_coords.
    """
    from kutomoto.automation import win32_window

    def fake_get_client_rect(hwnd, rect_ptr):
        rect = rect_ptr.contents
        rect.left = 0
        rect.top = 0
        rect.right = 1000
        rect.bottom = 600
        return 1

    monkeypatch.setattr(win32_window.user32, "GetClientRect", fake_get_client_rect)
    monkeypatch.setattr(win32_window, "client_to_screen_coords", lambda hwnd, cx, cy: (200 + cx, 150 + cy))

    screen_x, screen_y = win32_window.normalized_to_screen_coords(101, 0.35, 0.50)
    assert screen_x == 550
    assert screen_y == 450


def test_unicode_utf16_surrogate_splitting(monkeypatch):
    """
    Tests that send_text decomposes non-BMP Unicode characters (e.g. emojis)
    into UTF-16 surrogate pairs and dispatches them via SendInput KEYEVENTF_UNICODE.
    """
    from kutomoto.automation import win32_input
    from kutomoto.automation.win32_core import INPUT_KEYBOARD, KEYEVENTF_KEYUP, KEYEVENTF_UNICODE

    captured_inputs = []

    def mock_send_raw_input(inputs):
        captured_inputs.extend(inputs)
        return len(inputs)

    monkeypatch.setattr(win32_input, "send_raw_input", mock_send_raw_input)

    text = "Kutomoto 🚀 Banking"
    win32_input.send_text(text, delay_between_keys_ms=0)

    # Extract scanned 16-bit code units for keydown unicode inputs
    scans = [
        inp.union.ki.wScan for inp in captured_inputs
        if inp.type == INPUT_KEYBOARD and (inp.union.ki.dwFlags & KEYEVENTF_UNICODE) and not (inp.union.ki.dwFlags & KEYEVENTF_KEYUP)
    ]

    # Rocket emoji '🚀' is U+1F680, which decomposes into 0xD83D and 0xDE80
    assert 0xD83D in scans
    assert 0xDE80 in scans
    assert len(scans) == len(text) + 1  # 1 extra unit for surrogate pair


def test_clear_field_strategy_sequences(monkeypatch):
    """Verifies that clear_field executes correct keyboard/mouse sequences for all strategies."""
    from kutomoto.automation import win32_input

    calls = []
    monkeypatch.setattr(win32_input, "send_hotkey", lambda mods, key: calls.append(("hotkey", mods, key)))
    monkeypatch.setattr(win32_input, "send_key_press", lambda key, count=1: calls.append(("key_press", key, count)))
    monkeypatch.setattr(win32_input, "send_click", lambda x, y, button="left", click_count=1: calls.append(("click", button, click_count)))
    monkeypatch.setattr(win32_input, "get_cursor_pos", lambda: (100, 200))

    # Strategy 1: select_all_backspace
    calls.clear()
    win32_input.clear_field("select_all_backspace")
    assert calls == [("hotkey", ["ctrl"], "a"), ("key_press", "backspace", 1)]

    # Strategy 2: triple_click_delete
    calls.clear()
    win32_input.clear_field("triple_click_delete")
    assert calls == [("click", "left", 3), ("key_press", "delete", 1)]

    # Strategy 3: home_shift_end_delete
    calls.clear()
    win32_input.clear_field("home_shift_end_delete")
    assert calls == [("key_press", "home", 1), ("hotkey", ["shift"], "end"), ("key_press", "delete", 1)]
```

---

### 3.5 `tests/test_engine.py`

#### Modification 1: Replace Tautological Action Tests with Genuine Tests
Replace lines 130–137 (`test_07_action_delay`) and lines 152–159 (`test_10_action_prompt_user_input`) with:

```python
    @pytest.mark.asyncio
    async def test_07_action_delay(self, mock_driver, monkeypatch):
        """Action 7: delay executes non-blocking sleep via WorkflowRunner."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = KutomotoWorkflow(
            name="Delay Test",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.DELAY,
                    parameters=StepParameters(duration_ms=60),
                ),
            ],
        )
        runner = WorkflowRunner(driver=mock_driver)
        start = asyncio.get_event_loop().time()
        audit = await runner.execute(workflow)
        duration = asyncio.get_event_loop().time() - start
        assert audit.execution_summary.final_status == "SUCCESS"
        assert audit.execution_summary.successful_steps == 1
        assert runner.state == ExecutionState.COMPLETED
        assert duration >= 0.05

    @pytest.mark.asyncio
    async def test_10_action_prompt_user_input(self, mock_driver, monkeypatch):
        """Action 10: prompt_user_input invokes prompt resolver and binds variable."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = KutomotoWorkflow(
            name="Prompt Test",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.PROMPT_USER_INPUT,
                    parameters=StepParameters(variable_name="loan_amount", prompt_message="Enter amount:"),
                ),
            ],
        )

        class MockPromptResolver:
            def request_input(self, var_name, prompt_msg, is_secret):
                return "250000.00"

        telemetry_events = []
        runner = WorkflowRunner(
            driver=mock_driver,
            prompt_resolver=MockPromptResolver(),
            telemetry_callback=lambda evt, payload: telemetry_events.append((evt, payload)),
        )
        audit = await runner.execute(workflow)
        assert audit.execution_summary.final_status == "SUCCESS"
        assert runner.context.variables["loan_amount"] == "250000.00"
        assert any(evt[0] == "user_prompt_requested" and evt[1]["variable_name"] == "loan_amount" for evt in telemetry_events)
```

#### Modification 2: Add Full Coverage Suite in `TestWorkflowRunner`
Add the following new test methods to `TestWorkflowRunner`:

```python
    @pytest.mark.asyncio
    async def test_runner_executes_all_10_atomic_actions(self, mock_driver, monkeypatch):
        """Exercises all 10 atomic actions in a single end-to-end workflow."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        class MockResolver:
            def request_input(self, name, msg, sec):
                return "100000"

        workflow = KutomotoWorkflow(
            name="All 10 Actions Flow",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            variables=[
                WorkflowVariable(name="applicant_name", default_value="Jane Doe"),
            ],
            steps=[
                WorkflowStep(sequence_index=1, action_type=ActionType.FOCUS_WINDOW, parameters=StepParameters(window_title_pattern=".*Banking KYC.*")),
                WorkflowStep(sequence_index=2, action_type=ActionType.CLICK, parameters=StepParameters(norm_x=0.5, norm_y=0.5, coordinate_mode=CoordinateMode.NORMALIZED)),
                WorkflowStep(sequence_index=3, action_type=ActionType.CLEAR_FIELD, parameters=StepParameters(clear_strategy="select_all_backspace")),
                WorkflowStep(sequence_index=4, action_type=ActionType.TYPE_TEXT, parameters=StepParameters(text="{{applicant_name}}")),
                WorkflowStep(sequence_index=5, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key="tab", repeat_count=1)),
                WorkflowStep(sequence_index=6, action_type=ActionType.HOTKEY, parameters=StepParameters(keys=["ctrl", "s"])),
                WorkflowStep(sequence_index=7, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=10)),
                WorkflowStep(sequence_index=8, action_type=ActionType.SCROLL, parameters=StepParameters(delta_x=0, delta_y=-120)),
                WorkflowStep(sequence_index=9, action_type=ActionType.PROMPT_USER_INPUT, parameters=StepParameters(variable_name="loan_amt")),
                WorkflowStep(sequence_index=10, action_type=ActionType.SUBMIT, parameters=StepParameters(submit_method=SubmitMethod.BUTTON_CLICK, norm_x=0.8, norm_y=0.9, coordinate_mode=CoordinateMode.NORMALIZED)),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver, prompt_resolver=MockResolver())
        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert audit.execution_summary.successful_steps == 10
        assert runner.state == ExecutionState.COMPLETED
        assert len(mock_driver.hotkeys) == 1
        assert len(mock_driver.scrolls) == 1
        assert "Jane Doe" in mock_driver.typed_text
        assert runner.context.variables["loan_amt"] == "100000"

    @pytest.mark.asyncio
    async def test_runner_pause_and_resume_lifecycle(self, mock_driver, monkeypatch):
        """Verifies pause suspends step execution without crashing and resume completes workflow."""
        monkeypatch.delenv("KUTOMOTO_TEST_FAST", raising=False)

        workflow = KutomotoWorkflow(
            name="Pause Resume Lifecycle Flow",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0, default_step_delay_ms=20),
            steps=[
                WorkflowStep(sequence_index=1, action_type=ActionType.FOCUS_WINDOW, parameters=StepParameters(window_title_pattern=".*Banking KYC.*")),
                WorkflowStep(sequence_index=2, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=80)),
                WorkflowStep(sequence_index=3, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key="tab")),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver)
        task = asyncio.create_task(runner.execute(workflow))

        await asyncio.sleep(0.02)
        assert runner.state == ExecutionState.RUNNING

        # Pause execution
        await runner.pause()
        assert runner.state == ExecutionState.PAUSED

        # Allow execution tick; verify step 3 does NOT execute
        await asyncio.sleep(0.06)
        assert runner.state == ExecutionState.PAUSED
        assert len(mock_driver.key_presses) == 0

        # Resume execution
        await runner.resume()
        assert runner.state == ExecutionState.RUNNING

        audit = await task
        assert audit.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED
        assert len(mock_driver.key_presses) == 1

    @pytest.mark.asyncio
    async def test_runner_abort_from_paused(self, mock_driver, monkeypatch):
        """Verifies aborting while paused transitions gracefully to STOPPED without InvalidTransitionError."""
        monkeypatch.delenv("KUTOMOTO_TEST_FAST", raising=False)

        workflow = KutomotoWorkflow(
            name="Abort While Paused Flow",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0, default_step_delay_ms=30),
            steps=[
                WorkflowStep(sequence_index=1, action_type=ActionType.FOCUS_WINDOW, parameters=StepParameters(window_title_pattern=".*Banking KYC.*")),
                WorkflowStep(sequence_index=2, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=100)),
                WorkflowStep(sequence_index=3, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key="tab")),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver)
        task = asyncio.create_task(runner.execute(workflow))

        await asyncio.sleep(0.02)
        await runner.pause()
        assert runner.state == ExecutionState.PAUSED

        # Abort while paused
        await runner.abort()
        audit = await task

        assert audit.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED
        assert len(mock_driver.key_presses) == 0

    @pytest.mark.asyncio
    async def test_runner_reexecution_with_auto_reset(self, mock_driver, monkeypatch):
        """Verifies a completed WorkflowRunner automatically resets and executes a second workflow."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        workflow = KutomotoWorkflow(
            name="Run 1",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=[
                WorkflowStep(sequence_index=1, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key="tab")),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver)
        audit1 = await runner.execute(workflow)
        assert audit1.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED

        # Re-execute using the same runner instance
        audit2 = await runner.execute(workflow)
        assert audit2.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED
        assert len(mock_driver.key_presses) == 2

    @pytest.mark.asyncio
    async def test_runner_emergency_failsafe_aborts_immediately_under_skip_and_retry(self, mock_driver, monkeypatch):
        """Verifies CornerFailsafeTriggered aborts immediately under both SKIP_STEP and RETRY_STEP."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        for policy in (ErrorRecoveryPolicy.SKIP_STEP, ErrorRecoveryPolicy.RETRY_STEP):
            mock_driver.reset()
            workflow = KutomotoWorkflow(
                name=f"Failsafe Test {policy.value}",
                target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
                execution_settings=ExecutionSettings(countdown_seconds=0, error_recovery_policy=policy, max_step_retries=3),
                steps=[
                    WorkflowStep(sequence_index=1, action_type=ActionType.FOCUS_WINDOW, parameters=StepParameters(window_title_pattern=".*Banking KYC.*")),
                    WorkflowStep(sequence_index=2, action_type=ActionType.CLICK, parameters=StepParameters(norm_x=0.5, norm_y=0.5, coordinate_mode=CoordinateMode.NORMALIZED)),
                ],
            )

            mock_driver.simulate_corner_failsafe(0, 0)
            runner = WorkflowRunner(driver=mock_driver)
            audit = await runner.execute(workflow)

            assert audit.execution_summary.final_status == "ABORTED", f"Policy {policy.value} failed to abort immediately on corner failsafe!"
            assert runner.state == ExecutionState.STOPPED
            assert runner.context.step_retry_count == 0
```

---

### 3.6 Updating Empirical Challenge Suites to Assert Fixed Behavior

#### A. `tests/test_m2_empirical_challenge.py`
In `TestAdversarialChallenges`:
1. `test_adversarial_client_rect_contract_mismatch`:
   Update assertion from `assert (targeting_error_x, targeting_error_y) == (150, 100)` to:
   ```python
   assert (targeting_error_x, targeting_error_y) == (0, 0)
   assert actual_click["x"] == 700
   assert actual_click["y"] == 500
   ```
2. `test_adversarial_corner_failsafe_bypassed_under_skip_policy`:
   Update assertion from `assert log.execution_summary.final_status == "SUCCESS"` to:
   ```python
   assert log.execution_summary.final_status == "ABORTED"
   assert runner.state == ExecutionState.STOPPED
   assert len(executed_steps) == 0
   ```
3. `test_adversarial_escape_abort_retried_under_retry_policy`:
   Update assertion from `assert runner.context.step_retry_count == 2` to:
   ```python
   assert runner.context.step_retry_count == 0
   assert log.execution_summary.final_status == "ABORTED"
   assert runner.state == ExecutionState.STOPPED
   ```
4. `test_adversarial_modifier_leak_on_skip_policy`:
   Update assertion from `assert "ctrl" in driver.active_modifiers` to:
   ```python
   assert "ctrl" not in driver.active_modifiers
   ```

#### B. `tests/test_engine_empirical_challenge.py`
1. `test_vulnerability_zero_and_falsy_required_variables_rejected`:
   Update to assert successful execution with numeric `0`:
   ```python
   audit = await runner.execute(workflow, runtime_variables={"retry_count": 0})
   assert audit.execution_summary.final_status == "SUCCESS"
   assert runner.state == ExecutionState.COMPLETED
   assert "Count: 0" in mock_driver.typed_text
   ```
2. `test_vulnerability_user_pause_does_not_pause_and_crashes_fsm`:
   Update to assert pause halts execution and resume cleanly completes:
   ```python
   await runner.pause()
   assert runner.state == ExecutionState.PAUSED
   await asyncio.sleep(0.05)
   assert runner.state == ExecutionState.PAUSED
   assert len(mock_driver.key_presses) == 0

   await runner.resume()
   assert runner.state == ExecutionState.RUNNING
   audit = await task
   assert audit.execution_summary.final_status == "SUCCESS"
   assert runner.state == ExecutionState.COMPLETED
   assert len(mock_driver.key_presses) == 1
   ```
3. `test_vulnerability_abort_while_paused_crashes_with_cleanup_done`:
   Update to test runner abort from paused state without `InvalidTransitionError`:
   ```python
   runner = WorkflowRunner(driver=mock_driver)
   from kutomoto.engine.runner import ExecutionContext
   ctx = ExecutionContext(workflow=None, execution_id="test")  # type: ignore
   ctx.pause_event.clear()
   runner._ctx = ctx
   await runner._fsm.trigger(FSMEvent.EXECUTE_START)
   await runner._fsm.trigger(FSMEvent.VALIDATION_OK)
   await runner._fsm.trigger(FSMEvent.COUNTDOWN_DONE)
   await runner._fsm.trigger(FSMEvent.USER_PAUSE)
   assert runner.state == ExecutionState.PAUSED

   await runner.abort()
   assert runner.state == ExecutionState.STOPPED
   ```
4. `test_vulnerability_resume_without_target_hwnd_leaves_event_cleared`:
   Update assertion to:
   ```python
   await runner.resume()
   assert runner.state == ExecutionState.RUNNING
   assert ctx.pause_event.is_set()
   ```
5. `test_vulnerability_policy_prompt_user_unhandled_and_aborts`:
   Update assertion:
   ```python
   audit = await runner.execute(workflow)
   assert audit.execution_summary.final_status == "FAILED"
   assert runner.state == ExecutionState.ERROR
   assert "user_prompt_requested" in telemetry_events
   ```

---

## 4. Verification Protocol & Quality Gates for `m2_fix_worker_1`

After applying the changes above, `m2_fix_worker_1` must execute and satisfy the following gates:

### Gate 1: Full Test Suite Execution
```powershell
python -m pytest tests/ -v
```
**Pass Condition**: 100% of collected tests pass (124+ tests, 0 failures, 0 errors).

### Gate 2: Code Coverage Verification
```powershell
python -m pytest --cov=kutomoto.automation --cov=kutomoto.engine --cov-report=term-missing tests/test_win32_driver.py tests/test_engine.py
```
**Pass Conditions**:
- `kutomoto.engine.runner`: Missing lines drops from 121 to < 20 statements (> 90% coverage).
- `kutomoto.engine.safety`: > 90% coverage.
- `kutomoto.engine.fsm`: > 95% coverage.
- `kutomoto.automation.win32_window`: Coverage increases significantly due to real `normalized_to_screen_coords` test.
- `kutomoto.automation.win32_input`: Coverage increases due to real `clear_field` and `send_text` tests.

### Gate 3: Ruff Linter Verification
```powershell
python -m ruff check src/ tests/
```
**Pass Condition**: All checks passed with 0 warnings or errors.

### Gate 4: Zero Tautological Tests Attestation
Inspect `test_clear_field_strategy_sequences`, `test_normalized_coordinate_translation`, `test_unicode_utf16_surrogate_splitting`, `test_07_action_delay`, and `test_10_action_prompt_user_input` to ensure zero self-certifying local variable tests remain.
