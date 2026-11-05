# Milestone 4 Empirical Challenge & Stress Testing Report

**Challenger**: `m4_challenger_1` (Empirical Challenger & Adversarial Verifier)  
**Date**: 2026-11-05T07:29:00Z  
**Parent Agent**: `59700fc9-320d-4ed3-b1db-2fc709fed831`  
**Verdict**: **FAIL** (Critical FSM Race Condition & Ghost Running Lockout Vulnerabilities)

---

## Challenge Summary

- **Overall Risk Assessment**: **CRITICAL**
- **Target Components**:
  - `src/kutomoto/server/app.py` (FastAPI REST endpoints & WebSocket Hub)
  - `src/kutomoto/engine/runner.py` (Workflow execution loop interaction with server)
  - `src/kutomoto/engine/fsm.py` (Finite State Machine transition integrity)
  - `tests/test_api.py` (Worker unit test baseline)
  - `tests/test_m4_empirical_challenge.py` (Adversarial stress testing suite)

---

## 1. Observation

### Baseline Verification
The baseline API test suite created by `m4_worker_1` (`tests/test_api.py`) passes 100%:
```powershell
python -m pytest tests/test_api.py -v
# Output: 17 passed in 0.57s
```

### Empirical Adversarial Stress Suite (`tests/test_m4_empirical_challenge.py`)
To test the four dimensions mandated by the mission, an empirical challenge harness of 14 adversarial stress tests was implemented:
```powershell
python -m pytest tests/test_m4_empirical_challenge.py -v
```
**Output**:
```
tests/test_m4_empirical_challenge.py::TestConcurrencyAttacks::test_20_concurrent_start_requests_single_flight_lock PASSED [  7%]
tests/test_m4_empirical_challenge.py::TestConcurrencyAttacks::test_concurrent_start_after_abort_clean_recovery PASSED [ 14%]
tests/test_m4_empirical_challenge.py::TestConcurrencyAttacks::test_concurrent_start_and_abort_race_no_deadlock PASSED [ 21%]
tests/test_m4_empirical_challenge.py::TestWebSocketResilience::test_websocket_multi_client_concurrent_broadcast PASSED [ 28%]
tests/test_m4_empirical_challenge.py::TestWebSocketResilience::test_websocket_mid_execution_abrupt_disconnect PASSED [ 35%]
tests/test_m4_empirical_challenge.py::TestWebSocketResilience::test_websocket_frame_fuzzing_and_ping_pong PASSED [ 42%]
tests/test_m4_empirical_challenge.py::TestWebSocketResilience::test_websocket_rapid_connect_disconnect_churn PASSED [ 50%]
tests/test_m4_empirical_challenge.py::TestEdgeCaseAndPayloadFuzzing::test_workflows_crud_fuzzing_invalid_payloads PASSED [ 57%]
tests/test_m4_empirical_challenge.py::TestEdgeCaseAndPayloadFuzzing::test_designer_compile_fuzzing_invalid_payloads PASSED [ 64%]
tests/test_m4_empirical_challenge.py::TestEdgeCaseAndPayloadFuzzing::test_workflow_id_path_traversal_sanitization PASSED [ 71%]
tests/test_m4_empirical_challenge.py::TestEdgeCaseAndPayloadFuzzing::test_lifecycle_invalid_state_transitions_rejected PASSED [ 78%]
tests/test_m4_empirical_challenge.py::TestFSMRapidStateThrashingAndVulnerabilities::test_rapid_thrash_zero_delay_cycles PASSED [ 85%]
tests/test_m4_empirical_challenge.py::TestFSMRapidStateThrashingAndVulnerabilities::test_vulnerability_post_delay_pause_causes_invalid_fsm_transition XFAIL [ 92%]
tests/test_m4_empirical_challenge.py::TestFSMRapidStateThrashingAndVulnerabilities::test_vulnerability_pre_delay_pause_causes_invalid_fsm_transition XFAIL [100%]

======================== 12 passed, 2 xfailed in 1.30s ========================
```

### Direct Empirical Findings & Verbatim Exceptions

#### Finding F-M4-01 [CRITICAL]: Post-delay pause crashes FSM with `InvalidTransitionError` and locks server into Ghost Running state
- **File**: `src/kutomoto/engine/runner.py:690-710` & `src/kutomoto/server/app.py:296-302, 427-436`
- **Verbatim Error**:
  ```
  ERROR kutomoto.server:app.py:376 Workflow execution error: Invalid FSM transition: cannot transition from state 'PAUSED' via event 'ALL_STEPS_DONE'.
  Traceback (most recent call last):
    File "src/kutomoto/server/app.py", line 358, in _run_wrapper
      audit = await runner.execute(workflow, runtime_variables=variables)
    File "src/kutomoto/engine/runner.py", line 710, in execute
      await self._fsm.trigger(FSMEvent.ALL_STEPS_DONE)
    File "src/kutomoto/engine/fsm.py", line 99, in trigger
      raise InvalidTransitionError(self._state, event)
  kutomoto.engine.fsm.InvalidTransitionError: Invalid FSM transition: cannot transition from state 'PAUSED' via event 'ALL_STEPS_DONE'.
  ```
- **Consequence Observed**:
  1. The background task `_active_task` is dead.
  2. `_runner.fsm.state` remains `PAUSED`.
  3. When client calls `POST /api/execute/resume`, `ServerExecutionManager.resume()` triggers `USER_RESUME` -> FSM state becomes `RUNNING`.
  4. But no background task is executing.
  5. `ServerExecutionManager.is_active()` returns `True` because `self._runner.fsm.is_active` is True.
  6. Any subsequent `POST /api/execute/start` request is rejected with `409 Conflict: A workflow execution is already active. Concurrency not permitted.`
  7. The server is permanently locked in a Ghost Running state.

#### Finding F-M4-02 [HIGH]: Pre-delay pause crashes step execution with `InvalidTransitionError`
- **File**: `src/kutomoto/engine/runner.py:498-507, 547-548`
- **Verbatim Error**:
  ```
  ERROR kutomoto.server:app.py:376 Workflow execution error: Invalid FSM transition: cannot transition from state 'PAUSED' via event 'STEP_EXCEPTION'.
  Traceback (most recent call last):
    File "src/kutomoto/engine/runner.py", line 548, in execute
      await self._fsm.trigger(FSMEvent.STEP_SUCCESS)
    File "src/kutomoto/engine/fsm.py", line 99, in trigger
      raise InvalidTransitionError(self._state, event)
  kutomoto.engine.fsm.InvalidTransitionError: Invalid FSM transition: cannot transition from state 'PAUSED' via event 'STEP_SUCCESS'.

  During handling of the above exception, another exception occurred:

  Traceback (most recent call last):
    File "src/kutomoto/server/app.py", line 358, in _run_wrapper
      audit = await runner.execute(workflow, runtime_variables=variables)
    File "src/kutomoto/engine/runner.py", line 583, in execute
      await self._fsm.trigger(FSMEvent.STEP_EXCEPTION)
    File "src/kutomoto/engine/fsm.py", line 99, in trigger
      raise InvalidTransitionError(self._state, event)
  kutomoto.engine.fsm.InvalidTransitionError: Invalid FSM transition: cannot transition from state 'PAUSED' via event 'STEP_EXCEPTION'.
  ```
- **Consequence Observed**:
  When paused during `pre_delay`, the pre-delay loop does not wait on `pause_event`. It completes, runs the step action, and attempts `STEP_SUCCESS` while FSM is in `PAUSED`. FSM rejects the transition, and the exception handler fails to transition to `STEP_EXCEPTION` from `PAUSED`, crashing the workflow.

---

## 2. Logic Chain

1. **Mission Requirement 1 (Concurrency Attacks)**:
   - Evaluated 20 simultaneous async requests to `POST /api/execute/start` via `httpx.AsyncClient` under `asyncio.gather`.
   - Verified that `asyncio.Lock` in `ServerExecutionManager.start` enforces single-flight execution.
   - Result: Exactly 1 request returned 200 OK ('started') and 19 requests returned 409 Conflict with RFC 7807 problem details and 90Studio attribution.
   - Zero 500 errors; zero deadlocks. Lock cleanly releases on completion and abort.

2. **Mission Requirement 4 (WebSocket Resilience)**:
   - Connected 10 concurrent WebSocket clients simultaneously. All 10 received `connection_established` with `system: kutomoto` and 90Studio copyright watermark. All 10 received streamed events simultaneously.
   - Disconnected 3 out of 5 clients mid-execution while events were actively broadcasting. `WebSocketHub.broadcast()` caught socket send errors and purged dead connections without server crash. Remaining 2 clients continued receiving telemetry.
   - Fuzzed WebSocket incoming messages with raw non-JSON text, non-dict JSON lists (`[1, 2, 3]`), unknown actions, and rapid ping/pong requests. The hub handled all gracefully without dropping connections.

3. **Mission Requirement 3 (Edge Case and Payload Fuzzing)**:
   - Malformed JSON bodies on `/api/workflows`, `/api/designer/compile`, and `/api/execute/start` return HTTP 422 with JSON decode problem details.
   - Missing/forged copyright headers are rejected with 422.
   - Empty boxes list, negative box dimensions, and duplicate box IDs in `/api/designer/compile` are rejected with 422.
   - Path traversal attempts (`../../windows/system32/cmd.exe`, `..%2F..%2Fwindows%2Fwin.ini`, and Windows reserved device names `CON`, `PRN`, `NUL`) are sanitized by `re.sub(r"[^a-zA-Z0-9_\-]", "_", workflow_id)` and return 404 / 405 without leaking filesystem data.

4. **Mission Requirement 2 (FSM Rapid State Thrashing & Failure Analysis)**:
   - Rapid thrashing with zero-delay steps succeeds.
   - However, in production or enterprise workflows where steps have `pre_delay_ms` or `post_delay_ms`:
     - `runner.py:499-506`:
       ```python
       if step.pre_delay_ms > 0:
           pre_remaining = step.pre_delay_ms / 1000.0
           while pre_remaining > 0:
               if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                   break
               chunk = min(0.05, pre_remaining)
               await asyncio.sleep(chunk)
               pre_remaining -= chunk
       ```
     - Notice that unlike `_execute_delay` (lines 346-347), `pre_delay` does NOT check:
       `if not ctx.pause_event.is_set(): await ctx.pause_event.wait()`
     - Similarly, `post_delay` (lines 694-702) does NOT check `pause_event`.
     - When `POST /api/execute/pause` is invoked while a delay is ticking:
       - `runner.pause()` sets `FSMEvent.USER_PAUSE`, changing state to `PAUSED`.
       - But `pre_delay` or `post_delay` continues sleeping without pausing!
       - After `pre_delay`, the step runs and line 548 executes `await self._fsm.trigger(FSMEvent.STEP_SUCCESS)`.
       - Because state is `PAUSED`, `(ExecutionState.PAUSED, FSMEvent.STEP_SUCCESS)` does not exist.
       - It crashes with `InvalidTransitionError`.
       - In `post_delay` of the final step, line 710 executes `await self._fsm.trigger(FSMEvent.ALL_STEPS_DONE)`.
       - Because state is `PAUSED`, `(ExecutionState.PAUSED, FSMEvent.ALL_STEPS_DONE)` does not exist.
       - It crashes with `InvalidTransitionError`.
     - In `src/kutomoto/server/app.py`:
       - `_run_wrapper` catches `Exception`, broadcasts `step_failed` and `execution_error`, and exits.
       - The task is dead. But `_runner.fsm.state` was never transitioned to `ERROR` or `STOPPED`. It remains `PAUSED`.
       - Calling `POST /api/execute/resume` transitions `_runner.fsm.state` to `RUNNING` without restarting the background task.
       - `is_active()` returns `True` because `_runner.fsm.is_active` is True.
       - Any subsequent `POST /api/execute/start` fails permanently with 409 Conflict.
     - Therefore, FSM state transition integrity fails under realistic multi-step timing thrashing.

---

## 3. Caveats

- Win32 native SendInput actions were tested using `MockWin32Driver` to permit headless CI/CD execution. Physical keyboard/mouse hardware interactions in interactive Windows desktop sessions were not evaluated by this harness (assigned to Milestone 5).
- Microsoft Edge App Mode browser process lifecycle was not tested directly inside this unit harness.

---

## 4. Conclusion & Recommended Worker Remediation

### Explicit Verdict: **FAIL**

While Concurrency Control, WebSocket Hub streaming, and Payload Fuzzing are robust and enterprise-grade, **FSM Rapid State Thrashing fails** due to Findings F-M4-01 and F-M4-02.

### Actionable Remediation for `m4_worker_1`:

1. **Fix `pre_delay` and `post_delay` pause handling in `src/kutomoto/engine/runner.py`**:
   Inside both the `pre_delay` loop (line 499) and the `post_delay` loop (line 694), add pause-awareness:
   ```python
   if not ctx.pause_event.is_set():
       await ctx.pause_event.wait()
   ```

2. **Fix `ALL_STEPS_DONE` pause-awareness in `src/kutomoto/engine/runner.py`**:
   Before triggering `ALL_STEPS_DONE` at line 710:
   ```python
   if not ctx.pause_event.is_set():
       await ctx.pause_event.wait()
   ```

3. **Defend `ServerExecutionManager` against dead task resumption in `src/kutomoto/server/app.py`**:
   - In `ServerExecutionManager._run_wrapper`:
     If an unhandled exception occurs, ensure the runner transitions to `STOPPED` or `ERROR` so it does not linger in `PAUSED`.
   - In `ServerExecutionManager.resume()`:
     Verify that `self._active_task is not None and not self._active_task.done()` before attempting to resume. If the background task is dead, raise 409 or cleanly reset state.

---

## 5. Verification Method

To independently verify all findings and stress tests:

1. **Execute Empirical Challenge Test Suite**:
   ```powershell
   python -m pytest tests/test_m4_empirical_challenge.py -v
   ```
   *Expected Result*: 12 PASSED, 2 XFAILED (confirming F-M4-01 and F-M4-02).

2. **Execute Worker Baseline Test Suite**:
   ```powershell
   python -m pytest tests/test_api.py -v
   ```
   *Expected Result*: 17 PASSED in < 1.0s.

3. **Verify Linter Cleanliness**:
   ```powershell
   python -m ruff check src/ tests/
   ```
   *Expected Result*: All checks passed!
