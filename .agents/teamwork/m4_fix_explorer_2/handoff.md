# Milestone 4 Concurrency & FSM Fix Strategy Report

**Agent**: `m4_fix_explorer_2` (Concurrency & FSM Execution Mechanics Explorer)  
**Date**: 2026-11-05T04:40:00Z  
**Parent Agent**: `59700fc9-320d-4ed3-b1db-2fc709fed831`  
**Target Vulnerabilities**: Finding F-M4-01 (Critical) & Finding F-M4-02 (High)  
**Target Files**:
- `src/kutomoto/engine/runner.py`
- `src/kutomoto/server/app.py`
- `tests/test_m4_empirical_challenge.py`

---

## 1. Observation

### Empirical Test Execution and Baseline Status
Running baseline and empirical test suites reveals:
1. `tests/test_api.py`: 17 passed in 0.53s.
2. `tests/test_engine.py`: 42 passed in 0.78s.
3. `tests/test_m4_empirical_challenge.py`: 12 passed, 2 xfailed in 1.25s.
   The two xfailures are the exact probes written by `m4_challenger_1`:
   - `test_vulnerability_post_delay_pause_causes_invalid_fsm_transition` (F-M4-01)
   - `test_vulnerability_pre_delay_pause_causes_invalid_fsm_transition` (F-M4-02)

### Direct Inspection of `src/kutomoto/engine/runner.py`

#### Observation 1.1: `_execute_delay` vs. `pre_delay` and `post_delay`
In `src/kutomoto/engine/runner.py:340-351` (`_execute_delay`):
```python
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
```
Notice lines 346-347: `if not ctx.pause_event.is_set(): await ctx.pause_event.wait()`. If paused, `_execute_delay` suspends execution and waits.

However, in `src/kutomoto/engine/runner.py:499-506` (`pre_delay`):
```python
            # Pre-delay
            if step.pre_delay_ms > 0:
                pre_remaining = step.pre_delay_ms / 1000.0
                while pre_remaining > 0:
                    if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                        break
                    chunk = min(0.05, pre_remaining)
                    await asyncio.sleep(chunk)
                    pre_remaining -= chunk

            if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                return self._finalize_audit(ctx, "ABORTED")
```
And in `src/kutomoto/engine/runner.py:694-702` (`post_delay`):
```python
            if post_delay > 0:
                post_remaining = post_delay / 1000.0
                while post_remaining > 0:
                    if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                        break
                    chunk = min(0.05, post_remaining)
                    await asyncio.sleep(chunk)
                    post_remaining -= chunk
```
Both `pre_delay` and `post_delay` completely lack any pause check! Neither checks `if not ctx.pause_event.is_set(): await ctx.pause_event.wait()`.

#### Observation 1.2: State Transitions in State `PAUSED`
In `src/kutomoto/engine/fsm.py:61-83`, the transitions from `ExecutionState.PAUSED` are strictly:
```python
(ExecutionState.PAUSED, FSMEvent.USER_RESUME): ExecutionState.RUNNING,
(ExecutionState.PAUSED, FSMEvent.ABORT_TRIGGERED): ExecutionState.STOPPED,
```
There is NO valid transition from `PAUSED` via `STEP_SUCCESS`, `STEP_EXCEPTION`, or `ALL_STEPS_DONE`.
Yet in `runner.py`:
- Line 548: `await self._fsm.trigger(FSMEvent.STEP_SUCCESS)`
- Line 583: `await self._fsm.trigger(FSMEvent.STEP_EXCEPTION)`
- Line 710: `await self._fsm.trigger(FSMEvent.ALL_STEPS_DONE)`
None of these transitions verify that `self._fsm.state` is not `PAUSED` or await `ctx.pause_event.wait()` before triggering. When a pause arrives during `pre_delay` or `post_delay`, the runner attempts these transitions while in state `PAUSED`, crashing with `InvalidTransitionError`.

#### Observation 1.3: Event Signaling Race in `WorkflowRunner.resume()`
In `src/kutomoto/engine/runner.py:721-733`:
```python
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
```
Line 731 calls `self._ctx.pause_event.set()` *before* line 732 calls `await self._fsm.trigger(FSMEvent.USER_RESUME)`. While `trigger` updates `self._state` synchronously, setting the event before triggering the FSM introduces unnecessary risk of waiters resuming before the FSM transition completes.

---

### Direct Inspection of `src/kutomoto/server/app.py`

#### Observation 1.4: Unhandled Exceptions in `_run_wrapper` Trap Runner in `PAUSED`
In `src/kutomoto/server/app.py:351-385`:
```python
    async def _run_wrapper(
        self,
        runner: WorkflowRunner,
        workflow: Any,
        variables: Optional[Dict[str, Any]],
    ) -> None:
        try:
            audit = await runner.execute(workflow, runtime_variables=variables)
            ...
        except Exception as ex:
            logger.error("Workflow execution error: %s", ex, exc_info=True)
            err_data = {
                "execution_id": self._execution_id,
                "workflow_id": self._workflow_id,
                "error": str(ex),
                "status": "ERROR",
            }
            await self.hub.broadcast("step_failed", err_data)
            await self.hub.broadcast("execution_error", err_data)
```
When an unhandled exception occurs (e.g. `InvalidTransitionError` caused by F-M4-01 or F-M4-02):
1. `_run_wrapper` catches `Exception` and logs/broadcasts errors.
2. The background task (`self._active_task`) terminates (`done() == True`).
3. But `runner.fsm.state` was never transitioned to a terminal state (`ERROR` or `STOPPED`)!
4. `runner.fsm.state` remains `PAUSED`.

#### Observation 1.5: `is_active()` Reports True for Dead Tasks
In `src/kutomoto/server/app.py:296-301`:
```python
    def is_active(self) -> bool:
        if self._runner is not None and self._runner.fsm.is_active:
            return True
        if self._active_task is not None and not self._active_task.done():
            return True
        return False
```
Because `ExecutionFSM.is_active` includes `PAUSED` and `RUNNING`, when the background task dies while `runner.fsm.state` is `PAUSED`, `self._runner.fsm.is_active` is `True`. Consequently, `is_active()` returns `True` even though `self._active_task.done()` is `True`!
This blocks any future `POST /api/execute/start` call forever with HTTP 409 Conflict.

#### Observation 1.6: `resume()` Operates on Dead Background Tasks
In `src/kutomoto/server/app.py:427-436`:
```python
    async def resume(self) -> Dict[str, Any]:
        if not self._runner or self._runner.state != ExecutionState.PAUSED:
            current = self._runner.state.value if self._runner else "IDLE"
            raise HTTPException(
                status_code=409,
                detail=f"Cannot resume runner in state '{current}'. Only PAUSED may be resumed.",
            )
        await self._runner.resume()
        return {"status": "resumed", "runner_state": "RUNNING"}
```
`resume()` only checks `self._runner.state != ExecutionState.PAUSED`. It never verifies `self._active_task is not None and not self._active_task.done()`.
If the background task died, calling `resume()` triggers `USER_RESUME`, transitioning `runner.fsm.state` to `RUNNING` while no task is executing, creating a permanent Ghost Running zombie.

---

## 2. Logic Chain

1. **Root Cause of F-M4-01 (`post_delay` pause failure)**:
   - User pauses during `post_delay` of final step.
   - `post_delay` loop does not check `pause_event`, sleeps through its chunks, and exits.
   - Step execution loop terminates.
   - Line 710 executes `await self._fsm.trigger(FSMEvent.ALL_STEPS_DONE)`.
   - `(PAUSED, ALL_STEPS_DONE)` is undefined in FSM -> raises `InvalidTransitionError`.
   - `_run_wrapper` catches error and finishes task without updating FSM state -> server locked into Ghost Running state.

2. **Root Cause of F-M4-02 (`pre_delay` pause failure)**:
   - User pauses during `pre_delay`.
   - `pre_delay` loop does not check `pause_event`, sleeps through its chunks, and exits.
   - Runner proceeds to step execution while FSM is `PAUSED`.
   - Step executes and attempts `await self._fsm.trigger(FSMEvent.STEP_SUCCESS)`.
   - `(PAUSED, STEP_SUCCESS)` is undefined -> raises `InvalidTransitionError`.
   - Runner exception handler catches error and attempts `await self._fsm.trigger(FSMEvent.STEP_EXCEPTION)`.
   - `(PAUSED, STEP_EXCEPTION)` is undefined -> raises secondary `InvalidTransitionError` out of runner.

3. **Required Fix Mechanics in `runner.py`**:
   - **Pause-Aware Delays**: Inside both `pre_delay` and `post_delay` loops, insert `if not ctx.pause_event.is_set(): await ctx.pause_event.wait()`.
   - **Post-Loop Pause Check**: After both delay loops, check `if not ctx.pause_event.is_set(): await ctx.pause_event.wait()`.
   - **Pre-Transition Pause Guards**: Immediately before triggering `STEP_SUCCESS`, `STEP_EXCEPTION`, and `ALL_STEPS_DONE`, ensure runner waits on `pause_event.wait()`.
   - **Transition Safety**: Guard transitions with `if self._fsm.can_trigger(...)` to guarantee that an invalid transition can never crash the runner.
   - **Inversion of Resume Signaling**: In `WorkflowRunner.resume()`, call `await self._fsm.trigger(FSMEvent.USER_RESUME)` *first*, and only then call `self._ctx.pause_event.set()`. This ensures that when any paused coroutine awakens, the FSM is already in `RUNNING`.

4. **Required Fix Mechanics in `app.py`**:
   - **Dead Task Guard in `is_active()`**: If `self._active_task is not None and self._active_task.done()`, return `False` immediately. A dead task cannot be active.
   - **Terminal Transition on Exception in `_run_wrapper`**: In `except Exception as ex:`, if `runner` is not in a terminal state, transition it cleanly via `ABORT_TRIGGERED` / `POLICY_ABORT` or set `_state = ExecutionState.ERROR`.
   - **Dead Task Guard in `resume()`**: Before resuming, check `if self._active_task is None or self._active_task.done()`. If the background task has terminated, clean up runner state and reject with HTTP 409 Conflict.

---

## 3. Caveats

- **No Caveats**: The mechanics of `asyncio.Event`, `asyncio.Task`, and `ExecutionFSM` transitions are deterministic and self-contained within Python's async runtime.
- **Strict Read-Only Enforcement**: As `m4_fix_explorer_2`, this report only specifies the exact code proposals. The implementation is reserved for `m4_worker_1`.

---

## 4. Conclusion & Exact Proposed Code Changes

The fixes are precise, targeted, and preserve 100% backward compatibility with existing tests.

### Proposed File 1: `src/kutomoto/engine/runner.py`

#### Patch 1.1: `pre_delay` pause check and step dispatch guard
**Location**: Lines 498-549  
**Original**:
```python
            # Pre-delay
            if step.pre_delay_ms > 0:
                pre_remaining = step.pre_delay_ms / 1000.0
                while pre_remaining > 0:
                    if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                        break
                    chunk = min(0.05, pre_remaining)
                    await asyncio.sleep(chunk)
                    pre_remaining -= chunk

            if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                return self._finalize_audit(ctx, "ABORTED")

            # Step dispatch with retry loop
            step_success = False
            retries_remaining = workflow.execution_settings.max_step_retries

            while not step_success:
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
                    step_success = True
                    # T07: RUNNING -> RUNNING
                    await self._fsm.trigger(FSMEvent.STEP_SUCCESS)
```

**Replacement**:
```python
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
```

#### Patch 1.2: Step Exception handler pause check
**Location**: Lines 569-584  
**Original**:
```python
                except Exception as ex:
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
                    await self._fsm.trigger(FSMEvent.STEP_EXCEPTION)
```

**Replacement**:
```python
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
```

#### Patch 1.3: `post_delay` and `ALL_STEPS_DONE` pause check
**Location**: Lines 690-711  
**Original**:
```python
            # Post-delay
            post_delay = step.post_delay_ms or (
                0 if os.environ.get("KUTOMOTO_TEST_FAST") else workflow.execution_settings.default_step_delay_ms
            )
            if post_delay > 0:
                post_remaining = post_delay / 1000.0
                while post_remaining > 0:
                    if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                        break
                    chunk = min(0.05, post_remaining)
                    await asyncio.sleep(chunk)
                    post_remaining -= chunk

            if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
                return self._finalize_audit(ctx, "ABORTED")

        if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
            return self._finalize_audit(ctx, "ABORTED")

        # T08: RUNNING -> COMPLETED
        await self._fsm.trigger(FSMEvent.ALL_STEPS_DONE)
        return self._finalize_audit(ctx, "SUCCESS")
```

**Replacement**:
```python
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
        return self._finalize_audit(ctx, "SUCCESS")
```

#### Patch 1.4: Invert resume event trigger and pause_event signaling order
**Location**: Lines 721-734  
**Original**:
```python
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
```

**Replacement**:
```python
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
```

---

### Proposed File 2: `src/kutomoto/server/app.py`

#### Patch 2.1: Defend `is_active()` against dead background tasks
**Location**: Lines 296-302  
**Original**:
```python
    def is_active(self) -> bool:
        if self._runner is not None and self._runner.fsm.is_active:
            return True
        if self._active_task is not None and not self._active_task.done():
            return True
        return False
```

**Replacement**:
```python
    def is_active(self) -> bool:
        if self._active_task is not None and self._active_task.done():
            return False
        if self._runner is not None and self._runner.fsm.is_active:
            return True
        if self._active_task is not None and not self._active_task.done():
            return True
        return False
```

#### Patch 2.2: Ensure runner transitions to terminal state in `_run_wrapper` on error
**Location**: Lines 375-385  
**Original**:
```python
        except Exception as ex:
            logger.error("Workflow execution error: %s", ex, exc_info=True)
            err_data = {
                "execution_id": self._execution_id,
                "workflow_id": self._workflow_id,
                "error": str(ex),
                "status": "ERROR",
            }
            await self.hub.broadcast("step_failed", err_data)
            await self.hub.broadcast("execution_error", err_data)
```

**Replacement**:
```python
        except Exception as ex:
            logger.error("Workflow execution error: %s", ex, exc_info=True)
            err_data = {
                "execution_id": self._execution_id,
                "workflow_id": self._workflow_id,
                "error": str(ex),
                "status": "ERROR",
            }
            self._last_audit_summary = {
                "workflow_id": self._workflow_id,
                "execution_id": self._execution_id,
                "status": "ERROR",
                "error": str(ex),
                "duration_seconds": round(time.perf_counter() - self._start_time, 2),
                "total_steps": self._total_steps,
            }
            await self.hub.broadcast("step_failed", err_data)
            await self.hub.broadcast("execution_error", err_data)
            # Ensure runner is never trapped in PAUSED or non-terminal active state
            if runner and not runner.fsm.is_terminal:
                try:
                    if runner.fsm.can_trigger(FSMEvent.ABORT_TRIGGERED):
                        await runner.fsm.trigger(FSMEvent.ABORT_TRIGGERED)
                    elif runner.fsm.can_trigger(FSMEvent.POLICY_ABORT):
                        await runner.fsm.trigger(FSMEvent.POLICY_ABORT)
                    if runner.fsm.can_trigger(FSMEvent.CLEANUP_DONE):
                        await runner.fsm.trigger(FSMEvent.CLEANUP_DONE)
                except Exception as abort_err:
                    logger.warning("FSM terminal transition failed during error handler: %s", abort_err)
                if not runner.fsm.is_terminal:
                    runner.fsm._state = ExecutionState.ERROR
```

#### Patch 2.3: Verify task is alive and active in `ServerExecutionManager.resume()`
**Location**: Lines 427-436  
**Original**:
```python
    async def resume(self) -> Dict[str, Any]:
        if not self._runner or self._runner.state != ExecutionState.PAUSED:
            current = self._runner.state.value if self._runner else "IDLE"
            raise HTTPException(
                status_code=409,
                detail=f"Cannot resume runner in state '{current}'. Only PAUSED may be resumed.",
            )
        await self._runner.resume()
        return {"status": "resumed", "runner_state": "RUNNING"}
```

**Replacement**:
```python
    async def resume(self) -> Dict[str, Any]:
        if not self._runner or self._runner.state != ExecutionState.PAUSED:
            current = self._runner.state.value if self._runner else "IDLE"
            raise HTTPException(
                status_code=409,
                detail=f"Cannot resume runner in state '{current}'. Only PAUSED may be resumed.",
            )
        # Verify the background execution task is alive and active before transitioning state
        if self._active_task is None or self._active_task.done():
            if not self._runner.fsm.is_terminal:
                if self._runner.fsm.can_trigger(FSMEvent.ABORT_TRIGGERED):
                    await self._runner.fsm.trigger(FSMEvent.ABORT_TRIGGERED)
                else:
                    self._runner.fsm._state = ExecutionState.ERROR
            raise HTTPException(
                status_code=409,
                detail="Cannot resume workflow: background execution task is no longer active.",
            )
        await self._runner.resume()
        return {"status": "resumed", "runner_state": "RUNNING"}
```

---

### Proposed File 3: `tests/test_m4_empirical_challenge.py`

#### Patch 3.1: Remove xfail markers once patches 1.1-2.3 are applied
**Location**: Lines 596-597 & Lines 652-653  
Remove the `@pytest.mark.xfail(strict=True, ...)` decorators so that both tests execute as regular test cases asserting the resolved behavior:
```python
    @pytest.mark.asyncio
    async def test_vulnerability_post_delay_pause_causes_invalid_fsm_transition(self):
...
    @pytest.mark.asyncio
    async def test_vulnerability_pre_delay_pause_causes_invalid_fsm_transition(self):
```

---

## 5. Verification Method

Once `m4_worker_1` applies the changes, verify using the following commands:

1. **Verify All Empirical Adversarial Challenge Tests Pass (14/14)**:
   ```powershell
   python -m pytest tests/test_m4_empirical_challenge.py -v
   ```
   *Expected Result*: `14 passed in < 2.0s` (0 xfailed, 0 failed).

2. **Verify Server REST & WebSocket Baseline Tests Pass (17/17)**:
   ```powershell
   python -m pytest tests/test_api.py -v
   ```
   *Expected Result*: `17 passed in < 1.0s`.

3. **Verify Execution Engine & FSM Lifecycle Tests Pass (42/42)**:
   ```powershell
   python -m pytest tests/test_engine.py -v
   ```
   *Expected Result*: `42 passed in < 1.0s`.

4. **Verify Entire Test Suite Passes**:
   ```powershell
   python -m pytest tests/ -v
   ```

5. **Verify Ruff Code Quality & Formatting**:
   ```powershell
   python -m ruff check src/ tests/
   ```
   *Expected Result*: `All checks passed!`.
