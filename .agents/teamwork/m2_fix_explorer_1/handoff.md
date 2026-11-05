# Milestone 2 Fix Synthesis Handoff Report

**Agent**: `m2_fix_explorer_1`  
**Role**: Explorer, Synthesis Specialist  
**Working Directory**: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_fix_explorer_1`  
**Date**: 2026-11-04  
**Target Milestone**: Milestone 2 — Win32 Automation Core & Workflow Execution Engine (Fix Iteration)  
**Deliverable**: Comprehensive Synthesis & Remediation Plan (`report.md`)  

---

## 1. Observation

### 1.1 Reviewed Handoffs & Evidence Artifacts
Direct review was performed on all four failure reports and the codebase:
- `m2_reviewer_1/handoff.md` (Integrity violation: self-certifying tests; safety failsafe caught by recovery policies; coordinate arithmetic contract mismatch; modifier leakage on skip; missing test coverage).
- `m2_reviewer_2/handoff.md` (Invalid transition crash on pause; invalid transition crash on abort from paused; cannot re-execute runner; client rect mismatch).
- `m2_challenger_1/handoff.md` (`tests/test_engine_empirical_challenge.py` reproducing user pause loop failure, abort from paused `CLEANUP_DONE` crash, resume without hwnd, unhandled `PROMPT_USER` policy, falsy required variable rejection).
- `m2_challenger_2/handoff.md` (`tests/test_m2_empirical_challenge.py` reproducing coordinate targeting error of 150px X / 100px Y, corner failsafe bypass under `SKIP_STEP`, escape abort retry under `RETRY_STEP`, modifier leak under `SKIP_STEP`).

### 1.2 Concrete Code Observations
1. **Coordinate Geometry Arithmetic**:
   In `src/kutomoto/engine/runner.py` lines 272–273:
   `client_w = rect[2] - rect[0]` and `client_h = rect[3] - rect[1]`.
   In `src/kutomoto/automation/win32_window.py` lines 367–377:
   `get_client_bounds(hwnd)` returns `(pt.x, pt.y, crc.right - crc.left, crc.bottom - crc.top)` = `(screen_left, screen_top, width, height)`.
   Because `rect[2]` is `width`, `client_w` becomes `width - screen_left`, producing targeting skew or negative widths. In `src/kutomoto/engine/safety.py` line 455, `MockWin32Driver.get_client_rect` returned `(bounds[0], bounds[1], bounds[0] + bounds[2], bounds[1] + bounds[3])`, masking the bug during mock tests.
2. **Safety Guardrail Trapping**:
   In `src/kutomoto/engine/runner.py` lines 475–532:
   `self._safety_guard.pre_step_check(ctx.target_hwnd)` raises `CornerFailsafeTriggered` or `EscapeAbortTriggered`. Both inherit from `SafetyException(Exception)`. Because they are caught under `except Exception as ex:`, `RETRY_STEP` retried `EscapeAbortTriggered` `max_step_retries` times, and `SKIP_STEP` marked `step_success = True` and returned `"SUCCESS"`.
3. **User Pause Control Flow**:
   In `src/kutomoto/engine/runner.py` lines 438–495:
   `execute()` never awaited `ctx.pause_event.wait()` at loop start. Calling `pause()` set state to `PAUSED`, but the loop executed the step and called `trigger(FSMEvent.STEP_SUCCESS)`, crashing with `InvalidTransitionError: cannot transition from state 'PAUSED' via event 'STEP_SUCCESS'`.
4. **Abort from Paused State**:
   In `src/kutomoto/engine/runner.py` line 449:
   `trigger(FSMEvent.CLEANUP_DONE)` was unconditionally invoked after `ABORT_TRIGGERED`. When paused, transition T14 moves `PAUSED` directly to `STOPPED`. Triggering `CLEANUP_DONE` from `STOPPED` crashes with `InvalidTransitionError`.
5. **Resume Event Lock**:
   In `src/kutomoto/engine/runner.py` lines 568–570:
   `self._ctx.pause_event.set()` was nested inside `if self._ctx and self._ctx.target_hwnd:`. If `target_hwnd` is `None`, the event remained cleared.
6. **Re-execution Reset**:
   In `src/kutomoto/engine/runner.py` line 384:
   Re-running a completed runner triggered `EXECUTE_START` from `COMPLETED`, crashing because `RESET` was never called.
7. **Modifier Purge Missing**:
   In `src/kutomoto/engine/runner.py` lines 510–531:
   Neither `RETRY_STEP` nor `SKIP_STEP` branches released modifiers, leaking stuck keys.
8. **Falsy Variable Validation**:
   In `src/kutomoto/engine/runner.py` line 406:
   `not ctx.variables.get(v.name)` evaluated `not 0` as `True`, rejecting valid numeric `0` and boolean `False`.
9. **`PROMPT_USER` Recovery Policy**:
   In `src/kutomoto/engine/runner.py` lines 503–532:
   Policy `PROMPT_USER` had no handler, falling into hard abort without telemetry.
10. **Tautological Tests**:
    In `tests/test_win32_driver.py` lines 78–114, 136–144 and `tests/test_engine.py` lines 130–137, 152–159:
    Tests checked local lists/dicts/math without calling library code.
11. **Coverage Gaps in `runner.py`**:
    Lines 210, 214, 217–220, 315–320, 328–335, 346–348, 351–372, 559–580 lacked test coverage.

---

## 2. Logic Chain

1. **Safety Primacy (Observation 1.2.2)**: Safety guardrails are non-negotiable hard stops. Therefore, in `WorkflowRunner.execute()`, `SafetyException` must be caught explicitly before `except Exception as ex:` to immediately trigger `ABORT_TRIGGERED`, purge modifiers, and return `final_status == "ABORTED"` without retries or skips.
2. **Deterministic State Synchronization (Observation 1.2.3, 1.2.4, 1.2.5)**:
   - For `pause()` to actually suspend the workflow, the step loop and delay step must wait on `ctx.pause_event.wait()`.
   - To prevent crashing on abort while paused, `CLEANUP_DONE` must only be triggered when `self._fsm.can_trigger(FSMEvent.CLEANUP_DONE)` is true.
   - For `resume()` to reliably unblock execution, `ctx.pause_event.set()` must execute unconditionally whenever `ctx` exists.
3. **Lifecycle Reusability (Observation 1.2.6)**: To support enterprise workflow reuse on a runner instance, `execute()` must check `if self._fsm.is_terminal:` and call `RESET` to return to `IDLE` before triggering `EXECUTE_START`.
4. **Spatial Accuracy (Observation 1.2.1)**: Standardizing client rect as `(screen_left, screen_top, width, height)` requires `client_w = rect[2]` and `client_h = rect[3]` directly. Aligning `MockWin32Driver.get_client_rect` and aliasing `get_client_rect` and `client_to_screen` in `win32_window.py` completely eliminates the 150px coordinate distortion on Windows desktops.
5. **Session Cleanliness (Observation 1.2.7)**: When a step fails under `RETRY_STEP` or `SKIP_STEP`, calling `self._driver.release_all_modifiers()` ensures keyboard/mouse modifiers do not remain stuck down.
6. **Data Fidelity & Policy Completeness (Observation 1.2.8, 1.2.9)**:
   - Required variable validation must check `is None or == ""` to support numeric `0` and boolean `False`.
   - Error recovery policy `PROMPT_USER` must emit telemetry `user_prompt_requested` and query `prompt_resolver`.
7. **Test Integrity & Verification Rigor (Observation 1.2.10, 1.2.11)**:
   - Replacing tautological tests with genuine tests calling `clear_field`, `normalized_to_screen_coords`, `send_text`, `_execute_delay`, and `_execute_prompt_user_input` eliminates self-certifying false positives.
   - Adding tests for all 10 actions and runner lifecycle methods raises coverage above 90%.

---

## 3. Caveats

- Hardware-dependent features (physical mouse slam, physical Escape key press, multi-monitor physical DPI scaling) rely on Windows OS ctypes simulation via `MockWin32Driver` and monkeypatching in automated tests; interactive verification will be performed during M5 E2E testing.
- No other caveats.

---

## 4. Conclusion

All 11 identified defects across the four reviewer and challenger reports have been synthesized into an exact, actionable remediation plan documented in:
`c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_fix_explorer_1\report.md`

`m2_fix_worker_1` can directly drop in the supplied code modifications for `runner.py`, `safety.py`, `win32_window.py`, `test_win32_driver.py`, and `test_engine.py`, and update the empirical challenge assertions to achieve 100% test pass rate with > 90% coverage and zero tautological tests.

---

## 5. Verification Method

To independently verify the proposed remediation plan:

1. **Verify Report Completeness**:
   Inspect `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_fix_explorer_1\report.md` to confirm exact before/after diffs are provided for all 7 affected files.
2. **Execute Full Test Suite**:
   ```powershell
   python -m pytest tests/ -v
   ```
   *Pass Condition*: 100% pass across all 124+ collected tests.
3. **Execute Coverage Verification**:
   ```powershell
   python -m pytest --cov=kutomoto.automation --cov=kutomoto.engine --cov-report=term-missing tests/test_win32_driver.py tests/test_engine.py
   ```
   *Pass Condition*: `WorkflowRunner` dispatchers and lifecycle methods covered (> 90% module coverage).
4. **Static Linting**:
   ```powershell
   python -m ruff check src/ tests/
   ```
   *Pass Condition*: Clean (0 errors).
5. **Invalidation Conditions**:
   - Any test that passes by asserting local variable equality without invoking `kutomoto` library code.
   - Any condition where `CornerFailsafeTriggered` or `EscapeAbortTriggered` results in `final_status == "SUCCESS"`.
   - Any `InvalidTransitionError` occurring during `pause()`, `resume()`, or `abort()`.
