# Milestone 2 Review & Adversarial Critic Report

**Agent**: `m2_reviewer_2`  
**Target Milestone**: Milestone 2 — Win32 Automation Core & Workflow Execution Engine  
**Target Files Reviewed**: `src/kutomoto/engine/runner.py`, `src/kutomoto/engine/safety.py`, `src/kutomoto/engine/audit.py`  
**Copyright**: Copyrights reserved to 90Studio  
**Date**: 2026-11-04  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

### 1.1 Integrity Violation Assessment
An exhaustive inspection of `src/kutomoto/engine/runner.py`, `src/kutomoto/engine/safety.py`, `src/kutomoto/engine/audit.py`, and `src/kutomoto/automation/` was performed:
- **Hardcoded test results**: None. No static test outputs or artificial pass bypasses are embedded in the source.
- **Dummy or facade implementations**: None. The 10 atomic action handlers, 7-State FSM, Win32 `SendInput` structures, DPI ladder, and safety detectors contain genuine logic.
- **Task shortcuts / external tool delegation**: None. Real Win32 ctypes and Pydantic V2 schemas are implemented from scratch.
- **Fabricated verification outputs**: None. The 75 test suite runs and passes cleanly in ~0.42s.
- **Attestation**: Integrity checks PASSED. No cheating detected.

---

### 1.2 Baseline Verification Execution
Running the project test suite:
```powershell
python -m pytest tests/ -v
```
Output:
```
collected 75 items
tests/test_engine.py::TestAtomicActionHandlers::test_01_action_focus_window PASSED
...
============================= 75 passed in 0.42s ==============================
```

---

### 1.3 Adversarial Stress-Test Findings & Verbatim Exceptions

While baseline unit tests pass, adversarial challenge testing surfaced **2 Critical** and **2 Major** architectural defects in `runner.py`:

#### Observation O1: Emergency Failsafe & Abort Bypass under Error Policies
- **File**: `src/kutomoto/engine/runner.py`, lines 474–545
- **Behavior**:
  In `runner.py`, line 475 calls `self._safety_guard.pre_step_check(ctx.target_hwnd)`. If the operator hits the screen corner `(0, 0)` or presses `Escape`, `CornerFailsafeTriggered` or `EscapeAbortTriggered` is raised. However, line 496 catches this exception inside a generic `except Exception as ex:` block. If `workflow.execution_settings.error_recovery_policy == ErrorRecoveryPolicy.SKIP_STEP`, the runner logs `record_skipped`, marks `step_success = True`, and continues executing subsequent steps until the workflow completes and returns `final_status: "SUCCESS"`!
- **Reproduction**:
  ```python
  driver.simulate_corner_failsafe(0, 0)
  audit = await runner.execute(workflow_with_skip_step)
  assert audit.execution_summary.final_status == "SUCCESS" # Emergency stop was ignored!
  assert runner.state == ExecutionState.COMPLETED
  ```
  If `error_recovery_policy == ErrorRecoveryPolicy.RETRY_STEP`, the runner repeatedly retries the step `max_step_retries` times instead of halting immediately within 50ms as mandated by Feature F11 and Section 9.3.

#### Observation O2: Invalid FSM Transition Crash on `runner.pause()`
- **File**: `src/kutomoto/engine/runner.py`, lines 438–495 and 557–564
- **Behavior**:
  `runner.pause()` transitions the FSM to `ExecutionState.PAUSED` via `FSMEvent.USER_PAUSE` (T09) and clears `ctx.pause_event`. However, the main step loop in `execute()` **does not check or wait on `ctx.pause_event`** unless an external window focus shift is detected in `_check_loss_of_focus`. When a running workflow continues to its next step while in `PAUSED` state, the step executes, and line 494 attempts:
  `await self._fsm.trigger(FSMEvent.STEP_SUCCESS)`.
  Because the FSM is in `PAUSED` state, `(ExecutionState.PAUSED, FSMEvent.STEP_SUCCESS)` is invalid and raises:
  ```
  kutomoto.engine.fsm.InvalidTransitionError: Invalid FSM transition: cannot transition from state 'PAUSED' via event 'STEP_SUCCESS'.
  ```
  Then the exception handler at line 507 attempts:
  `await self._fsm.trigger(FSMEvent.STEP_EXCEPTION)`.
  Because the FSM is STILL in `PAUSED` state, it immediately crashes again:
  ```
  kutomoto.engine.fsm.InvalidTransitionError: Invalid FSM transition: cannot transition from state 'PAUSED' via event 'STEP_EXCEPTION'.
  ```

#### Observation O3: Crash on Aborting from `PAUSED` State
- **File**: `src/kutomoto/engine/runner.py`, lines 446–450
- **Behavior**:
  When `ctx.abort_requested` is true:
  ```python
  await self._fsm.trigger(FSMEvent.ABORT_TRIGGERED) # Line 447
  await self._cleanup_after_abort()
  await self._fsm.trigger(FSMEvent.CLEANUP_DONE)    # Line 449
  ```
  If the runner was paused, transition T14 moves `PAUSED` directly to `STOPPED`.
  Line 449 then triggers `CLEANUP_DONE` when the FSM is ALREADY `STOPPED`.
  `(ExecutionState.STOPPED, FSMEvent.CLEANUP_DONE)` does not exist in `TRANSITIONS` and crashes:
  ```
  kutomoto.engine.fsm.InvalidTransitionError: Invalid FSM transition: cannot transition from state 'STOPPED' via event 'CLEANUP_DONE'.
  ```
  Transition T18 (`STOPPING + CLEANUP_DONE -> STOPPED`) only applies when transitioning from `RUNNING` via T11 (`RUNNING + ABORT_TRIGGERED -> STOPPING`).

#### Observation O4: Inability to Re-execute Runner Instance
- **File**: `src/kutomoto/engine/runner.py`, line 384
- **Behavior**:
  `WorkflowRunner.execute()` begins with:
  `await self._fsm.trigger(FSMEvent.EXECUTE_START)`.
  After a workflow run concludes in `COMPLETED`, `STOPPED`, or `ERROR`, re-running the same `WorkflowRunner` instance throws:
  ```
  kutomoto.engine.fsm.InvalidTransitionError: Invalid FSM transition: cannot transition from state 'COMPLETED' via event 'EXECUTE_START'.
  ```
  The FSM supports `RESET` transitions (T19–T21) from terminal states back to `IDLE`, but `WorkflowRunner.execute()` never triggers `RESET`.

#### Observation O5: Interface Contract Discrepancy for Window Rect
- **File**: `src/kutomoto/engine/runner.py`, lines 267–281 vs `src/kutomoto/automation/win32_window.py`
- **Behavior**:
  In `_execute_click`, the runner probes `hasattr(self._driver, "get_client_rect")`. `MockWin32Driver` defines `get_client_rect(hwnd)` returning `(left, top, right, bottom)`. However, `automation.win32_window` does NOT define `get_client_rect`; it defines `get_client_bounds(hwnd)` returning `(screen_left, screen_top, width, height)`.
  Because `hasattr(real_driver, "get_client_rect")` evaluates to `False`, the runner falls back to `get_window_bounds(hwnd)`. This measures the outer window rect (including non-client title bar and window border offsets), causing normalized click coordinates $(norm\_x, norm\_y)$ to skew when targeting physical Windows desktop forms.

---

## 2. Logic Chain

1. **Safety Primacy**: Specifications (F11, Section 9.3) mandate that emergency failsafe mechanisms (Escape key press and (0,0) corner hit) must immediately halt execution within 50ms and purge input queues. From Observation O1, because `runner.py` catches all exceptions into the generic recovery handler, non-abort policies (`SKIP_STEP` and `RETRY_STEP`) swallow the emergency abort, continuing execution or completing with `"SUCCESS"`. This breaks the fundamental safety contract.
2. **FSM State Discipline**: In `runner.py`, `pause()` transitions the FSM into `PAUSED`, but the loop does not pause. From Observation O2, executing steps while in `PAUSED` state triggers `STEP_SUCCESS` or `STEP_EXCEPTION`, neither of which is valid in `PAUSED`, causing runtime crash rather than clean suspension.
3. **Transition Determinism**: From Observation O3, transition T14 moves `PAUSED` directly to `STOPPED`. Triggering `CLEANUP_DONE` when already `STOPPED` violates the FSM transition graph.
4. **Lifecycle Usability**: From Observation O4, enterprise UI runners require repeatable execution. Failing to trigger `RESET` prevents workflow re-runs.
5. **Coordinate Accuracy**: From Observation O5, falling back to outer window bounds skews normalized coordinates by 30+ pixels due to title bar height.

Therefore, changes are required before Milestone 2 can be approved.

---

## 3. Caveats

- All 75 baseline unit tests passed because they tested `ExecutionFSM` transitions and `SafetyGuard` methods in isolation, rather than under cross-policy stress combinations in `WorkflowRunner.execute()`.
- The Win32 driver implementation (`win32_core.py`, `win32_input.py`, `win32_window.py`) is high quality with 40-byte 64-bit ABI alignment and genuine Win32 ctypes calls.
- The 90Studio audit logging and credential masking are compliant with Section 10.1.

---

## 4. Conclusion

Milestone 2 implementation is well-architected and contains no integrity violations. However, because of the 2 Critical findings and 2 Major findings identified above, Milestone 2 cannot be approved in its current state.

### Actionable Fix Recommendations for `m2_worker`:

1. **Fix Safety Abort Handling in `runner.py`**:
   In `WorkflowRunner.execute()`, catch `EscapeAbortTriggered` and `CornerFailsafeTriggered` (or any `SafetyException` when not focus loss) separately from general step exceptions:
   ```python
   except (EscapeAbortTriggered, CornerFailsafeTriggered):
       if self._fsm.can_trigger(FSMEvent.ABORT_TRIGGERED):
           await self._fsm.trigger(FSMEvent.ABORT_TRIGGERED)
       await self._cleanup_after_abort()
       if self._fsm.can_trigger(FSMEvent.CLEANUP_DONE):
           await self._fsm.trigger(FSMEvent.CLEANUP_DONE)
       return self._finalize_audit(ctx, "ABORTED")
   ```

2. **Fix Loop Pause Behavior in `runner.py`**:
   In `WorkflowRunner.execute()`, at the start of each step (and inside long delays), await `ctx.pause_event`:
   ```python
   # Check pause state before executing step
   if not ctx.pause_event.is_set():
       await ctx.pause_event.wait()
   ```

3. **Guard `CLEANUP_DONE` Transition**:
   In lines 447–450 of `runner.py`:
   ```python
   if ctx.abort_requested:
       if self._fsm.can_trigger(FSMEvent.ABORT_TRIGGERED):
           await self._fsm.trigger(FSMEvent.ABORT_TRIGGERED)
       await self._cleanup_after_abort()
       if self._fsm.can_trigger(FSMEvent.CLEANUP_DONE):
           await self._fsm.trigger(FSMEvent.CLEANUP_DONE)
       return self._finalize_audit(ctx, "ABORTED")
   ```

4. **Support Automatic Runner Reset**:
   In `WorkflowRunner.execute()`:
   ```python
   if self._fsm.is_terminal:
       await self._fsm.trigger(FSMEvent.RESET)
   ```

5. **Harmonize Window Client Rect Contract**:
   In `runner._execute_click`, use `get_client_bounds` or `normalized_to_screen_coords` if present on driver:
   ```python
   if hasattr(self._driver, "normalized_to_screen_coords"):
       screen_x, screen_y = self._driver.normalized_to_screen_coords(ctx.target_hwnd, p.norm_x, p.norm_y)
   ```

---

## 5. Verification Method

To independently verify the required fixes:

1. **Baseline Suite**:
   ```powershell
   python -m pytest tests/test_win32_driver.py tests/test_engine.py -v
   ```
   **Expected**: 47 passed.

2. **Empirical Challenge Repro Scripts**:
   - Run pause-and-abort test:
     ```powershell
     python -c "import sys; sys.path.insert(0, 'src'); import asyncio; from kutomoto.engine import *; ..."
     ```
     **Expected**: Clean pause, clean abort, no `InvalidTransitionError`.
   - Run corner failsafe with `SKIP_STEP`:
     ```powershell
     python -c "..."
     ```
     **Expected**: Immediate abort, `final_status == 'ABORTED'`, state == `STOPPED`.

3. **Invalidation Conditions**:
   - Any `InvalidTransitionError` thrown during pause, resume, or abort.
   - Any scenario where `CornerFailsafeTriggered` or `EscapeAbortTriggered` yields `final_status == "SUCCESS"`.
