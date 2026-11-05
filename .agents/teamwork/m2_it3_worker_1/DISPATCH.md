# Dispatch for m2_it3_worker_1 (Milestone 2, Iteration 3)

## Objective
Fix the in-step abort race condition in `src/kutomoto/engine/runner.py` identified by `m2_fix_reviewer_2` and add regression tests in `tests/test_engine.py`.

## Exclusive Write Ownership
You exclusively own and may write to:
- `src/kutomoto/engine/runner.py`
- `tests/test_engine.py`
- Files within your own directory `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_it3_worker_1\`

DO NOT touch any other source files.

## Inputs
- ORIGINAL_REQUEST: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md`
- Master Architecture: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md`
- Reviewer 2 Handoff: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_fix_reviewer_2\handoff.md`

## Instructions
1. Review the exact failure reproduction in `m2_fix_reviewer_2\handoff.md`:
   ```powershell
   python -c "import sys, asyncio; sys.path.insert(0, 'src'); from kutomoto.engine import WorkflowRunner, KutomotoWorkflow, WorkflowStep, ActionType, StepParameters, TargetApplication, ExecutionSettings, MockWin32Driver; async def test(): d = MockWin32Driver(); wf = KutomotoWorkflow(name='T', target_application=TargetApplication(type='windows_desktop', window_title_pattern='.*Banking KYC.*'), execution_settings=ExecutionSettings(countdown_seconds=0), steps=[WorkflowStep(sequence_index=1, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=1000))]); r = WorkflowRunner(driver=d); t = asyncio.create_task(r.execute(wf)); await asyncio.sleep(0.05); await r.abort(); await t; asyncio.run(test())"
   ```
2. Modify `src/kutomoto/engine/runner.py`:
   - In `_execute_delay`: In the sleep loop, if `ctx.abort_requested`, break out immediately.
   - In `execute()`:
     - After `await self._check_loss_of_focus(ctx)`:
       ```python
       if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
           return self._finalize_audit(ctx, "ABORTED")
       ```
     - After `pre_delay_ms` sleep:
       ```python
       if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
           return self._finalize_audit(ctx, "ABORTED")
       ```
     - After `await self._dispatch_action(step, ctx)`:
       ```python
       if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
           return self._finalize_audit(ctx, "ABORTED")
       ```
     - In `except Exception as ex:`:
       ```python
       if ctx.abort_requested or self._fsm.state in (ExecutionState.STOPPED, ExecutionState.ERROR):
           return self._finalize_audit(ctx, "ABORTED")
       ```
3. Add regression tests to `tests/test_engine.py`:
   - `test_abort_during_delay_step`
   - `test_abort_during_pre_delay`
   - `test_abort_during_focus_loss_wait`
4. Verification:
   - Run the reproduction script: must complete cleanly without `InvalidTransitionError`!
   - Run `python -m pytest tests/ -v`: all tests must pass!
   - Run `python -m ruff check src/ tests/`: 0 errors!
5. Write your handoff report to `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_it3_worker_1\handoff.md`.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
