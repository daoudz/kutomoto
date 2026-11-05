# Review & Adversarial Challenge Handoff Report: Milestone 2 Re-Review

**Reviewer**: `m2_fix_reviewer_2`  
**Roles**: Reviewer, Adversarial Critic  
**Working Directory**: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_fix_reviewer_2`  
**Target Recipient**: Orchestrator / Parent (`ce2dd708-d288-4e8f-9834-dfdb673a5856`)  
**Date**: 2026-11-04  
**Verdict**: **REQUEST_CHANGES**  

---

## Review Summary

**Verdict**: **REQUEST_CHANGES**

While `m2_fix_worker_1` successfully resolved 10 of the original Milestone 2 defects (including coordinate geometry alignment, safety exception prioritization, modifier cleanup on retry/skip, required variable handling, and removal of test tautologies), deep adversarial stress-testing identified a **CRITICAL race condition & FSM crash** in `WorkflowRunner`:
Calling `await runner.abort()` while a workflow is executing an asynchronous delay (`_execute_delay`), sleeping during `pre_delay_ms`, or paused in `_check_loss_of_focus` crashes the runner loop with `InvalidTransitionError: cannot transition from state 'STOPPED' via event 'STEP_SUCCESS'`.

---

## 1. Observation

### 1.1 Verbatim Failure Reproduction 1: Abort During `ActionType.DELAY`
Command executed:
```powershell
python -c "import sys, asyncio; sys.path.insert(0, 'src'); from kutomoto.engine import WorkflowRunner, KutomotoWorkflow, WorkflowStep, ActionType, StepParameters, TargetApplication, ExecutionSettings, MockWin32Driver
async def test():
    d = MockWin32Driver()
    wf = KutomotoWorkflow(
        name='Delay Abort Crash Test',
        target_application=TargetApplication(type='windows_desktop', window_title_pattern='.*Banking KYC.*'),
        execution_settings=ExecutionSettings(countdown_seconds=0),
        steps=[WorkflowStep(sequence_index=1, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=1000))]
    )
    r = WorkflowRunner(driver=d)
    t = asyncio.create_task(r.execute(wf))
    await asyncio.sleep(0.05)
    await r.abort()
    await t
asyncio.run(test())"
```
Verbatim Exception Output:
```
Traceback (most recent call last):
  File "C:\Users\daoud\projects\kutomoto\src\kutomoto\engine\runner.py", line 522, in execute
    await self._fsm.trigger(FSMEvent.STEP_SUCCESS)
  File "C:\Users\daoud\projects\kutomoto\src\kutomoto\engine\fsm.py", line 99, in trigger
    raise InvalidTransitionError(self._state, event)
kutomoto.engine.fsm.InvalidTransitionError: Invalid FSM transition: cannot transition from state 'STOPPED' via event 'STEP_SUCCESS'.

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\Users\daoud\projects\kutomoto\src\kutomoto\engine\runner.py", line 554, in execute
    await self._fsm.trigger(FSMEvent.STEP_EXCEPTION)
  File "C:\Users\daoud\projects\kutomoto\src\kutomoto\engine\fsm.py", line 99, in trigger
    raise InvalidTransitionError(self._state, event)
kutomoto.engine.fsm.InvalidTransitionError: Invalid FSM transition: cannot transition from state 'STOPPED' via event 'STEP_EXCEPTION'.
```

### 1.2 Verbatim Failure Reproduction 2: Abort While Paused in `_check_loss_of_focus`
Command executed:
```powershell
python -c "import sys, asyncio; sys.path.insert(0, 'src'); from kutomoto.engine import WorkflowRunner, KutomotoWorkflow, WorkflowStep, ActionType, StepParameters, TargetApplication, ExecutionSettings, MockWin32Driver
async def test():
    d = MockWin32Driver()
    wf = KutomotoWorkflow(
        name='Focus Loss Abort Crash Test',
        target_application=TargetApplication(type='windows_desktop', window_title_pattern='.*Banking KYC.*'),
        execution_settings=ExecutionSettings(countdown_seconds=0),
        steps=[
            WorkflowStep(sequence_index=1, action_type=ActionType.FOCUS_WINDOW, parameters=StepParameters(window_title_pattern='.*Banking KYC.*')),
            WorkflowStep(sequence_index=2, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key='tab'))
        ]
    )
    r = WorkflowRunner(driver=d)
    t = asyncio.create_task(r.execute(wf))
    await asyncio.sleep(0.01)
    d.simulate_focus_loss(9999)
    await asyncio.sleep(0.25)
    d.foreground_hwnd = 1001
    await r.abort()
    await t
asyncio.run(test())"
```
Verbatim Exception Output:
```
kutomoto.engine.fsm.InvalidTransitionError: Invalid FSM transition: cannot transition from state 'STOPPED' via event 'STEP_SUCCESS'.
...
kutomoto.engine.fsm.InvalidTransitionError: Invalid FSM transition: cannot transition from state 'STOPPED' via event 'STEP_EXCEPTION'.
```

### 1.3 Verbatim Failure Reproduction 3: Abort During `step.pre_delay_ms`
Command executed:
```powershell
python -c "import sys, asyncio; sys.path.insert(0, 'src'); from kutomoto.engine import WorkflowRunner, KutomotoWorkflow, WorkflowStep, ActionType, StepParameters, TargetApplication, ExecutionSettings, MockWin32Driver
async def test():
    d = MockWin32Driver()
    wf = KutomotoWorkflow(
        name='Pre-Delay Abort Crash Test',
        target_application=TargetApplication(type='windows_desktop', window_title_pattern='.*Banking KYC.*'),
        execution_settings=ExecutionSettings(countdown_seconds=0),
        steps=[
            WorkflowStep(sequence_index=1, action_type=ActionType.KEY_PRESS, pre_delay_ms=500, parameters=StepParameters(key='tab'))
        ]
    )
    r = WorkflowRunner(driver=d)
    t = asyncio.create_task(r.execute(wf))
    await asyncio.sleep(0.05)
    await r.abort()
    await t
asyncio.run(test())"
```
Verbatim Exception Output:
```
kutomoto.engine.fsm.InvalidTransitionError: Invalid FSM transition: cannot transition from state 'STOPPED' via event 'STEP_SUCCESS'.
```

### 1.4 Code Inspection Observations
In `src/kutomoto/engine/runner.py`:
- Lines 472–478 check `if ctx.abort_requested:` at the top of the step loop.
- Lines 480–483 invoke `await self._check_loss_of_focus(ctx)`. Line 153 suspends with `await ctx.pause_event.wait()`.
- Line 486 suspends with `await asyncio.sleep(step.pre_delay_ms / 1000.0)`.
- Lines 343–351 in `_execute_delay` breaks on `if ctx.abort_requested: break`.
- Lines 520–522: After any action returns (including broken delays), line 520 sets `step_success = True` and line 522 unconditionally calls `await self._fsm.trigger(FSMEvent.STEP_SUCCESS)`.
- When `abort()` is invoked externally, lines 701–704 transition the FSM: `RUNNING -> STOPPING -> STOPPED` (or `PAUSED -> STOPPED`).
- Because `self._fsm.state` is now `STOPPED`, line 522 attempts `(STOPPED, STEP_SUCCESS)`, which is invalid in FSM transitions and raises `InvalidTransitionError`.
- The exception handler at line 543 catches this error and calls `await self._fsm.trigger(FSMEvent.STEP_EXCEPTION)` at line 554, which raises a second `InvalidTransitionError` because `(STOPPED, STEP_EXCEPTION)` is also invalid.

---

## 2. Logic Chain

1. In `src/kutomoto/engine/runner.py`, `abort()` can be called asynchronously at any moment during execution by an operator or UI handler.
2. When `runner.abort()` runs (line 694):
   - It sets `ctx.abort_requested = True`
   - It signals `ctx.pause_event.set()`
   - It immediately fires `ABORT_TRIGGERED` and `CLEANUP_DONE`, moving the FSM into terminal state `STOPPED`.
3. However, inside `runner.execute()`:
   - If the runner was suspended at line 153 in `_check_loss_of_focus` (`await ctx.pause_event.wait()`), `pause_event.set()` unblocks it. It returns to line 482 without checking `ctx.abort_requested`, executes `pre_delay_ms`, and executes `_dispatch_action(step, ctx)`.
   - If the runner was executing `ActionType.DELAY` (`_execute_delay`), the loop at line 344 detects `ctx.abort_requested` and breaks. But `_execute_delay` finishes normally, returning execution to line 506.
   - If the runner was sleeping in `pre_delay_ms` (line 486), the sleep finishes, and it enters the step dispatch.
4. In all three cases, line 522 unconditionally executes:
   ```python
   step_success = True
   # T07: RUNNING -> RUNNING
   await self._fsm.trigger(FSMEvent.STEP_SUCCESS)
   ```
5. Since `self._fsm.state` was already moved to `STOPPED` by `abort()`, `trigger(STEP_SUCCESS)` throws `InvalidTransitionError`.
6. Line 554 then attempts `trigger(STEP_EXCEPTION)` from `STOPPED`, throwing another `InvalidTransitionError`.
7. This causes the task to crash completely with an unhandled exception rather than returning an `ABORTED` audit log.

---

## 3. Findings

### [Critical] Finding 1: Unhandled `abort_requested` in Step Loop Causes Fatal FSM Crash

- **What**: Invoking `await runner.abort()` while the workflow is in `_execute_delay`, `_check_loss_of_focus`, or `pre_delay_ms` crashes the runner task with `InvalidTransitionError`.
- **Where**: `src/kutomoto/engine/runner.py`, lines 153, 344, 482, 486, 505–523, and 543–555.
- **Why**: `abort()` transitions the FSM into terminal state `STOPPED`. Resuming from asynchronous pauses or delays without verifying `if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.STOPPING):` leads directly to invoking `trigger(STEP_SUCCESS)` from `STOPPED`.
- **Suggestion**:
  1. Add an abort guard check in `execute()`:
     - Immediately after `await self._check_loss_of_focus(ctx)`
     - Immediately after `if step.pre_delay_ms > 0: await asyncio.sleep(...)`
     - Immediately after `await self._dispatch_action(step, ctx)` (before `step_success = True` and before `trigger(STEP_SUCCESS)`)
  2. In `except Exception as ex:` at line 543, guard against terminal state:
     ```python
     if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.STOPPING):
         return self._finalize_audit(ctx, "ABORTED")
     ```
  3. In `_execute_delay`, when `ctx.abort_requested` is detected, do not allow subsequent code to treat the step as successful.
  4. Add automated test cases in `tests/test_engine.py` covering:
     - Abort during `ActionType.DELAY`
     - Abort while waiting in `_check_loss_of_focus`
     - Abort during `pre_delay_ms`

---

## 4. Verified Claims from Dispatch

The following items were verified and confirmed working as specified:

| Item | Verification Method | Result |
|------|---------------------|--------|
| **Safety Exception Priority** | `runner.py:524` has `except SafetyException as sex:` before general `except Exception as ex:`. Tested via `test_runner_emergency_failsafe_aborts_immediately_under_skip_and_retry`. | **PASS** |
| **Step Loop Pause Event** | `runner.py:468` has `if not ctx.pause_event.is_set(): await ctx.pause_event.wait()`. Tested via `test_runner_pause_and_resume_lifecycle`. | **PASS** |
| **Resume Sets Event** | `runner.py:690` sets `self._ctx.pause_event.set()` outside the `target_hwnd` block. Tested via `test_vulnerability_resume_without_target_hwnd_leaves_event_cleared`. | **PASS** |
| **Re-execution Reset** | `runner.py:399` has `if self._fsm.is_terminal: await self._fsm.trigger(FSMEvent.RESET)`. Tested via `test_runner_reexecution_with_auto_reset`. | **PASS** |
| **Coordinate Geometry** | `runner.py:281` uses `client_w = rect[2]` and `client_h = rect[3]`. `MockWin32Driver.get_client_rect` and `win32_window.get_client_bounds` standardized to `(screen_left, screen_top, width, height)`. | **PASS** |
| **Modifier Release** | `self._driver.release_all_modifiers()` called on `RETRY_STEP` (line 568) and `SKIP_STEP` (line 584). Tested via `test_adversarial_modifier_leak_on_skip_policy`. | **PASS** |
| **Test Suite Assertions** | `tests/test_win32_driver.py` and `tests/test_engine.py` tautologies were removed and replaced with authentic calls to `normalized_to_screen_coords`, `send_text`, `clear_field`, `DELAY`, and `PROMPT_USER_INPUT`. | **PASS** |
| **Pytest & Lint** | `pytest tests/test_engine.py` (39 passed); `pytest tests/` (129 passed); `ruff check src/ tests/` (all checks passed). | **PASS** |

---

## 5. Caveats

- No integrity violations (hardcoded facades or fake implementations) were found in the worker's changes. The implementation of 10 actions, FSM transitions, and driver contracts is genuine.
- The failure found is an asynchronous concurrency / race condition defect between `runner.abort()` and the step execution loop.

---

## 6. Conclusion

Because emergency abort is a non-negotiable safety guardrail for enterprise automation (especially in banking and telecom where runaway automated actions can submit unauthorized transactions), the runner crashing with `InvalidTransitionError` upon abort is a critical blocker.

**Verdict**: **REQUEST_CHANGES**

---

## 7. Verification Method

To reproduce and verify the critical finding:

1. **Reproduce Abort During Delay Crash**:
   ```powershell
   python -c "import sys, asyncio; sys.path.insert(0, 'src'); from kutomoto.engine import WorkflowRunner, KutomotoWorkflow, WorkflowStep, ActionType, StepParameters, TargetApplication, ExecutionSettings, MockWin32Driver; async def test(): d = MockWin32Driver(); wf = KutomotoWorkflow(name='T', target_application=TargetApplication(type='windows_desktop', window_title_pattern='.*Banking KYC.*'), execution_settings=ExecutionSettings(countdown_seconds=0), steps=[WorkflowStep(sequence_index=1, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=1000))]); r = WorkflowRunner(driver=d); t = asyncio.create_task(r.execute(wf)); await asyncio.sleep(0.05); await r.abort(); await t; asyncio.run(test())"
   ```
   *Current Result*: Crashes with `InvalidTransitionError: cannot transition from state 'STOPPED' via event 'STEP_SUCCESS'`.  
   *Expected Result*: Returns clean `KutomotoAuditLog` with `final_status="ABORTED"` and state `STOPPED`.

2. **Reproduce Abort During Focus Loss Pause Crash**:
   ```powershell
   python -c "import sys, asyncio; sys.path.insert(0, 'src'); from kutomoto.engine import WorkflowRunner, KutomotoWorkflow, WorkflowStep, ActionType, StepParameters, TargetApplication, ExecutionSettings, MockWin32Driver; async def test(): d = MockWin32Driver(); wf = KutomotoWorkflow(name='T', target_application=TargetApplication(type='windows_desktop', window_title_pattern='.*Banking KYC.*'), execution_settings=ExecutionSettings(countdown_seconds=0), steps=[WorkflowStep(sequence_index=1, action_type=ActionType.FOCUS_WINDOW, parameters=StepParameters(window_title_pattern='.*Banking KYC.*')), WorkflowStep(sequence_index=2, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key='tab'))]); r = WorkflowRunner(driver=d); t = asyncio.create_task(r.execute(wf)); await asyncio.sleep(0.01); d.simulate_focus_loss(9999); await asyncio.sleep(0.25); d.foreground_hwnd = 1001; await r.abort(); await t; asyncio.run(test())"
   ```
   *Current Result*: Crashes with `InvalidTransitionError: cannot transition from state 'STOPPED' via event 'STEP_SUCCESS'`.  
   *Expected Result*: Returns clean `KutomotoAuditLog` with `final_status="ABORTED"` and state `STOPPED`.

3. **Verify Full Test Suite**:
   ```powershell
   python -m pytest tests/test_engine.py -v
   python -m pytest tests/ -v
   python -m ruff check src/ tests/
   ```
