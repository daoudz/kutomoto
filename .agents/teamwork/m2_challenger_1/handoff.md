# Milestone 2 Empirical Challenge Report — WorkflowRunner & Engine FSM

**Agent**: `m2_challenger_1`  
**Role**: Empirical Challenger (critic, specialist)  
**Target Milestone**: Milestone 2 — Win32 Automation Core & Workflow Execution Engine  
**Verdict**: **FAIL** (5 Confirmed Vulnerabilities / Flaws)  
**Copyright**: Copyrights reserved to 90Studio  
**Date**: 2026-11-04  

---

## 1. Observation

Direct empirical observations, verbatim code references, test execution outputs, and reproduction traces:

### 1.1 Vulnerability V1 (Critical): User Pause Does Not Pause Execution Loop and Crashes FSM
- **File**: `src/kutomoto/engine/runner.py`, lines 438–495 and 557–564.
- **Observed Code**:
  ```python
  # runner.py:557-564
  async def pause(self) -> None:
      """Pauses the runner if currently running."""
      if self._fsm.state == ExecutionState.RUNNING:
          await self._fsm.trigger(FSMEvent.USER_PAUSE)  # T09
          if self._ctx:
              self._ctx.pause_event.clear()
          await self._emit_telemetry("execution_paused", {})
  ```
  ```python
  # runner.py:438-495 (inside execute loop)
  for idx, step in enumerate(workflow.steps):
      ctx.current_step_index = idx + 1
      if not step.enabled:
          continue
      if ctx.abort_requested:
          ...
      if step.action_type != ActionType.FOCUS_WINDOW:
          await self._check_loss_of_focus(ctx)
      ...
      await self._dispatch_action(step, ctx)
      ...
      await self._fsm.trigger(FSMEvent.STEP_SUCCESS)
  ```
- **Observed Behavior**:
  `WorkflowRunner.execute` never evaluates `await ctx.pause_event.wait()` in its step iteration loop. The only call to `ctx.pause_event.wait()` is in `_check_loss_of_focus` (line 149), which is only reached if `current_fg != ctx.target_hwnd`. When a user or frontend invokes `await runner.pause()` while focus is retained, `self._fsm.state` becomes `PAUSED`, but the runner does NOT pause; it proceeds to execute the next step. Upon step completion (line 494), it executes `await self._fsm.trigger(FSMEvent.STEP_SUCCESS)`.
- **Verbatim Error**:
  ```
  kutomoto.engine.fsm.InvalidTransitionError: Invalid FSM transition: cannot transition from state 'PAUSED' via event 'STEP_SUCCESS'.
  ```
- **Reproduction**:
  Verified by `tests/test_engine_empirical_challenge.py::TestFSMTransitionsAdversarial::test_vulnerability_user_pause_does_not_pause_and_crashes_fsm`.

---

### 1.2 Vulnerability V2 (Critical): Abort While Paused Crashes with Invalid Transition `CLEANUP_DONE`
- **File**: `src/kutomoto/engine/runner.py`, line 446–450, and `src/kutomoto/engine/fsm.py`, line 75, 79.
- **Observed Code**:
  ```python
  # runner.py:446-450
  if ctx.abort_requested:
      await self._fsm.trigger(FSMEvent.ABORT_TRIGGERED)  # T11
      await self._cleanup_after_abort()
      await self._fsm.trigger(FSMEvent.CLEANUP_DONE)    # T18
      return self._finalize_audit(ctx, "ABORTED")
  ```
- **Observed Behavior**:
  From `ExecutionState.PAUSED`, event `ABORT_TRIGGERED` transitions directly to `STOPPED` via transition `T14: (PAUSED, ABORT_TRIGGERED) -> STOPPED`.
  Immediately after in line 449, the runner unconditionally calls `await self._fsm.trigger(FSMEvent.CLEANUP_DONE)`. But `CLEANUP_DONE` is only valid from `STOPPING` (transition `T18: (STOPPING, CLEANUP_DONE) -> STOPPED`). From `STOPPED`, `CLEANUP_DONE` is invalid.
- **Verbatim Error**:
  ```
  kutomoto.engine.fsm.InvalidTransitionError: Invalid FSM transition: cannot transition from state 'STOPPED' via event 'CLEANUP_DONE'.
  ```
- **Reproduction**:
  Verified by `tests/test_engine_empirical_challenge.py::TestFSMTransitionsAdversarial::test_vulnerability_abort_while_paused_crashes_with_cleanup_done`.

---

### 1.3 Vulnerability V3 (High): Resume Without Target HWND Never Clears Pause Lock
- **File**: `src/kutomoto/engine/runner.py`, lines 565–573.
- **Observed Code**:
  ```python
  # runner.py:565-573
  async def resume(self) -> None:
      """Resumes workflow execution from paused state."""
      if self._fsm.state == ExecutionState.PAUSED:
          if self._ctx and self._ctx.target_hwnd:
              self._driver.focus_window(self._ctx.target_hwnd)
              self._ctx.pause_event.set()
          await self._fsm.trigger(FSMEvent.USER_RESUME)  # T13
          await self._emit_telemetry("execution_resumed", {})
  ```
- **Observed Behavior**:
  `self._ctx.pause_event.set()` is indented inside `if self._ctx and self._ctx.target_hwnd:`. If execution paused before a window was focused or if the workflow operates without an attached HWND (e.g. desktop coordinate flows), `self._ctx.target_hwnd` is `None`. Consequently, `self._ctx.pause_event.set()` is bypassed, and the event remains cleared forever while FSM state transitions to `RUNNING`.
- **Reproduction**:
  Verified by `tests/test_engine_empirical_challenge.py::TestFSMTransitionsAdversarial::test_vulnerability_resume_without_target_hwnd_leaves_event_cleared`.

---

### 1.4 Vulnerability V4 (High): ErrorRecoveryPolicy `PROMPT_USER` Unhandled and Hard-Aborts
- **File**: `src/kutomoto/engine/runner.py`, lines 503–545.
- **Observed Code**:
  ```python
  # runner.py:510-534
  if policy_val == ErrorRecoveryPolicy.RETRY_STEP.value and retries_remaining > 0:
      ...
  elif policy_val == ErrorRecoveryPolicy.SKIP_STEP.value:
      ...
  else:  # ABORT
      if self._audit_logger:
          self._audit_logger.record_failure(...)
      await self._fsm.trigger(FSMEvent.POLICY_ABORT)  # T17
      await self._cleanup_after_abort()
      return self._finalize_audit(ctx, "FAILED")
  ```
- **Observed Behavior**:
  Specification Section 7.3 defines 4 recovery policies: `["abort", "retry_step", "prompt_user", "skip_step"]`.
  `WorkflowRunner` only handles `retry_step` and `skip_step`. If a workflow specifies `error_recovery_policy: "prompt_user"`, the step exception falls into `else: # ABORT`. No telemetry event is dispatched to request operator input, `self._prompt_resolver` is never called, and the workflow abruptly fails.
- **Reproduction**:
  Verified by `tests/test_engine_empirical_challenge.py::TestRecoveryPoliciesAdversarial::test_vulnerability_policy_prompt_user_unhandled_and_aborts`.

---

### 1.5 Vulnerability V5 (Medium): Required Variable Validation Rejects Valid Numeric Zero and Boolean False
- **File**: `src/kutomoto/engine/runner.py`, lines 406–409.
- **Observed Code**:
  ```python
  # runner.py:406-409
  missing_vars = [v.name for v in workflow.variables if v.required and not ctx.variables.get(v.name)]
  if missing_vars:
      await self._fsm.trigger(FSMEvent.VALIDATION_FAILED)  # T03
      raise ValueError(f"Workflow execution blocked: missing required variables: {missing_vars}")
  ```
- **Observed Behavior**:
  The expression `not ctx.variables.get(v.name)` relies on Python boolean truthiness. If a required variable of type `NUMBER` or `STRING` is assigned integer `0`, float `0.0`, or boolean `False`, `not 0` evaluates to `True`. The variable is incorrectly diagnosed as missing, blocking execution:
- **Verbatim Error**:
  ```
  ValueError: Workflow execution blocked: missing required variables: ['retry_count']
  ```
- **Reproduction**:
  Verified by `tests/test_engine_empirical_challenge.py::TestVariableAdversarial::test_vulnerability_zero_and_falsy_required_variables_rejected`.

---

### 1.6 Empirical Test Execution Results
Command executed:
```powershell
$env:PYTHONPATH="src"; python -m pytest tests/test_engine_empirical_challenge.py -v
```
Verbatim test output:
```
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.0.2, pluggy-1.6.0 -- C:\Python314\python.exe
rootdir: C:\Users\daoud\projects\kutomoto
plugins: anyio-4.12.1, langsmith-0.6.2, asyncio-1.3.0, cov-7.0.0
collected 13 items

tests/test_engine_empirical_challenge.py::TestDeepStepChains::test_deep_step_chain_1000_steps PASSED [  7%]
tests/test_engine_empirical_challenge.py::TestVariableAdversarial::test_vulnerability_zero_and_falsy_required_variables_rejected PASSED [ 15%]
tests/test_engine_empirical_challenge.py::TestVariableAdversarial::test_variable_interpolation_edge_cases PASSED [ 23%]
tests/test_engine_empirical_challenge.py::TestFSMTransitionsAdversarial::test_vulnerability_user_pause_does_not_pause_and_crashes_fsm PASSED [ 30%]
tests/test_engine_empirical_challenge.py::TestFSMTransitionsAdversarial::test_vulnerability_abort_while_paused_crashes_with_cleanup_done PASSED [ 38%]
tests/test_engine_empirical_challenge.py::TestFSMTransitionsAdversarial::test_vulnerability_resume_without_target_hwnd_leaves_event_cleared PASSED [ 46%]
tests/test_engine_empirical_challenge.py::TestRecoveryPoliciesAdversarial::test_policy_abort_terminates_immediately PASSED [ 53%]
tests/test_engine_empirical_challenge.py::TestRecoveryPoliciesAdversarial::test_policy_retry_exhaustion_terminates_in_error PASSED [ 61%]
tests/test_engine_empirical_challenge.py::TestRecoveryPoliciesAdversarial::test_policy_skip_continues_subsequent_steps PASSED [ 69%]
tests/test_engine_empirical_challenge.py::TestRecoveryPoliciesAdversarial::test_vulnerability_policy_prompt_user_unhandled_and_aborts PASSED [ 76%]
tests/test_engine_empirical_challenge.py::TestConcurrencyAndAuditThroughput::test_concurrent_listeners_stress PASSED [ 84%]
tests/test_engine_empirical_challenge.py::TestConcurrencyAndAuditThroughput::test_telemetry_resilience_to_listener_exceptions PASSED [ 92%]
tests/test_engine_empirical_challenge.py::TestConcurrencyAndAuditThroughput::test_audit_masking_high_throughput_10000_events PASSED [100%]

============================= 13 passed in 2.06s ==============================
```

---

## 2. Logic Chain

1. **Pause Failure (V1)**: From Observation 1.1, `WorkflowRunner.pause()` sets state to `PAUSED`, but `execute()` contains no check for `pause_event.wait()` in its step dispatch loop. The loop dispatches subsequent steps while `state == PAUSED`. Upon step completion, `trigger(FSMEvent.STEP_SUCCESS)` is invoked. Because `(ExecutionState.PAUSED, FSMEvent.STEP_SUCCESS)` does not exist in `ExecutionFSM.TRANSITIONS`, `InvalidTransitionError` is raised, breaking the workflow.
2. **Abort Crash (V2)**: From Observation 1.2, transition `T14` transitions `PAUSED -> STOPPED`. When an abort is requested during pause, line 449 unconditionally calls `trigger(FSMEvent.CLEANUP_DONE)`. Transition `T18` is strictly defined as `(STOPPING, CLEANUP_DONE) -> STOPPED`. Invoking `CLEANUP_DONE` when the FSM is already in `STOPPED` throws an uncaught `InvalidTransitionError`.
3. **Resume Lock (V3)**: From Observation 1.3, `pause_event.set()` is conditioned on `if self._ctx and self._ctx.target_hwnd:`. If `target_hwnd` is `None` (valid in headless or coordinate-only automation), `set()` is skipped. Any code awaiting `pause_event.wait()` will hang indefinitely despite FSM state being `RUNNING`.
4. **Policy Omission (V4)**: From Observation 1.4, Section 7.3 specifies `prompt_user` as a first-class recovery policy. In `runner.py`, lack of an explicit `elif policy_val == ErrorRecoveryPolicy.PROMPT_USER.value:` branch causes all failures under this policy to execute `else: # ABORT`, ignoring prompt capabilities.
5. **Falsy Variable Rejection (V5)**: From Observation 1.5, checking `not ctx.variables.get(v.name)` conflates missing values with valid falsy values (`0`, `0.0`, `False`). A required variable with value `0` causes an unwarranted `ValueError`.

---

## 3. Caveats

- Win32 native API calls (`ctypes.windll.user32`) were stress-tested in conjunction with `MockWin32Driver` for simulated CI/CD execution. Hardware-level physical keyboard/mouse simulation on real interactive desktops was verified separately by `test_win32_driver.py`.
- FSM transition throughput and listener concurrency were evaluated up to 50 concurrent listeners; memory overhead remained negligible.

---

## 4. Conclusion

**Verdict: FAIL**

While the core Win32 driver, audit logger, and baseline step execution operate correctly, the workflow execution runtime contains **critical control-flow bugs in state management**:
1. User-initiated pause fails to pause and crashes the runtime (`V1`).
2. Aborting while paused throws `InvalidTransitionError` (`V2`).
3. Resuming without target HWND leaves the pause event cleared (`V3`).
4. Recovery policy `PROMPT_USER` is completely unhandled and terminates workflows (`V4`).
5. Required variable validation blocks valid numeric `0` and boolean `False` (`V5`).

### Concrete Recommendations for Worker / Remediation:
1. In `WorkflowRunner.execute`:
   - At the beginning of the step loop (line 445), add:
     ```python
     if self._fsm.state == ExecutionState.PAUSED:
         await ctx.pause_event.wait()
     ```
   - In the abort handler (line 447):
     ```python
     if self._fsm.can_trigger(FSMEvent.ABORT_TRIGGERED):
         await self._fsm.trigger(FSMEvent.ABORT_TRIGGERED)
     await self._cleanup_after_abort()
     if self._fsm.can_trigger(FSMEvent.CLEANUP_DONE):
         await self._fsm.trigger(FSMEvent.CLEANUP_DONE)
     ```
2. In `WorkflowRunner.resume`:
   - Ensure `self._ctx.pause_event.set()` is called regardless of whether `self._ctx.target_hwnd` is set:
     ```python
     if self._ctx:
         if self._ctx.target_hwnd:
             self._driver.focus_window(self._ctx.target_hwnd)
         self._ctx.pause_event.set()
     ```
3. In `WorkflowRunner._check_loss_of_focus`:
   - Before resuming normal step execution after focus loss wait, check `if ctx.abort_requested: return`.
4. In `WorkflowRunner.execute` (line 406):
   - Check `ctx.variables.get(v.name) is None or ctx.variables.get(v.name) == ""` instead of `not ctx.variables.get(v.name)`.
5. In `WorkflowRunner.execute` error recovery (line 503):
   - Implement `elif policy_val == ErrorRecoveryPolicy.PROMPT_USER.value:` to dispatch a prompt request via `self._prompt_resolver` or telemetry before falling back to abort.

---

## 5. Verification Method

To independently verify all findings and reproduce the identified vulnerabilities:

1. **Execute Empirical Challenge Test Suite**:
   ```powershell
   $env:PYTHONPATH="src"; python -m pytest tests/test_engine_empirical_challenge.py -v
   ```
   **Expected Result**: All 13 stress tests pass, demonstrating empirical reproduction of the 5 defects.

2. **Run Full Test Suite**:
   ```powershell
   $env:PYTHONPATH="src"; python -m pytest tests/ -v
   ```
   **Expected Result**: 124 tests pass in < 5.0s.

3. **Code Inspection**:
   - Inspect `src/kutomoto/engine/runner.py` at lines 406–409, 446–450, 494, 532, and 568–570.
   - Inspect `src/kutomoto/engine/fsm.py` at line 75 and 79.

4. **Invalidation Conditions**:
   - `test_vulnerability_user_pause_does_not_pause_and_crashes_fsm` passes cleanly with the runner actually halting execution and resuming without raising `InvalidTransitionError`.
   - `test_vulnerability_zero_and_falsy_required_variables_rejected` permits numeric `0` without throwing `ValueError`.
   - `test_vulnerability_abort_while_paused_crashes_with_cleanup_done` transitions gracefully without `InvalidTransitionError`.
