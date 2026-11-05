# Dispatch for m2_fix_worker_1 (Milestone 2, Iteration 2)

## Objective
Apply the exact drop-in remediation formulated by `m2_fix_explorer_1` to fix all 11 defects across `src/kutomoto/engine/runner.py`, `src/kutomoto/engine/safety.py`, `tests/test_win32_driver.py`, and `tests/test_engine.py`.

## Exclusive Write Ownership
You exclusively own and may write to:
- `src/kutomoto/engine/runner.py`
- `src/kutomoto/engine/safety.py`
- `src/kutomoto/automation/win32_window.py` (if any contract alias is added)
- `tests/test_win32_driver.py`
- `tests/test_engine.py`
- Files within your own directory `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_fix_worker_1\`

DO NOT touch `docs/SPECIFICATION.md` or any designer/server files.

## Inputs
- ORIGINAL_REQUEST: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md`
- Master Architecture: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md`
- Master Specification: `c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md`
- Remediation Plan: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_fix_explorer_1\report.md`
- Explorer Handoff: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_fix_explorer_1\handoff.md`

## Instructions
1. Read `m2_fix_explorer_1\report.md` thoroughly.
2. Apply the exact code fixes specified in the report:
   - **Fix 1 (Coordinate Contract)**: In `runner._execute_click`, use `client_w = rect[2]` and `client_h = rect[3]` directly. In `MockWin32Driver.get_client_rect`, return `(bounds[0], bounds[1], bounds[2], bounds[3])` matching `(screen_left, screen_top, width, height)`.
   - **Fix 2 (Safety Exceptions)**: Catch `SafetyException` (and its subclasses `EscapeAbortTriggered`, `CornerFailsafeTriggered`, `MouseDisturbanceDetected`) explicitly before general step error recovery. Immediately trigger `FSMEvent.ABORT_TRIGGERED`, perform cleanup, release all modifiers, finalize audit with `"ABORTED"`, and return `False`.
   - **Fix 3 (User Pause)**: At the beginning of each step iteration in `WorkflowRunner.execute()`, check `await ctx.pause_event.wait()` so pause actually pauses the loop before starting the next step.
   - **Fix 4 (Resume Logic)**: In `runner.resume()`, set `ctx.pause_event.set()` reliably and cleanly transition FSM.
   - **Fix 5 (Abort from Paused State)**: In `runner.abort()`, avoid invalid FSM transitions when state is already terminal or stopping.
   - **Fix 6 (Re-running Workflows)**: In `runner.execute()`, check `if self._fsm.is_terminal(): await self._fsm.trigger(FSMEvent.RESET)`.
   - **Fix 7 (Modifier Release on Retry & Skip)**: In both `RETRY_STEP` and `SKIP_STEP` exception branches, call `self._driver.release_all_modifiers()`.
   - **Fix 8 (Variable Interpolation Falsy Support)**: In `_substitute_variables`, support `0` and `False` values properly (`if val is not None:`).
   - **Fix 9 (Prompt User Recovery)**: Handle `ErrorRecoveryPolicy.PROMPT_USER` cleanly.
   - **Fix 10 & 11 (Unit Tests Integrity & Full Coverage)**: Replace all self-certifying tautological tests in `tests/test_win32_driver.py` and `tests/test_engine.py` with authentic unit tests that invoke the production methods (`clear_field`, `client_to_screen_coords`, `normalized_to_screen_coords`, `send_text`, `runner.pause()`, `runner.resume()`, `runner.abort()`, `hotkey`, `delay`, `scroll`, `prompt_user_input`).
3. Verification:
   - Run `python -m pytest tests/test_m2_empirical_challenge.py -v` -> All 36 tests must pass!
   - Run `python -m pytest tests/test_engine_empirical_challenge.py -v` -> All 13 tests must pass!
   - Run full test suite: `python -m pytest tests/ -v` -> All tests must pass!
   - Run `ruff check src/ tests/` -> 0 errors!
4. Write your handoff report to `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_fix_worker_1\handoff.md`.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.


## 2026-11-04T23:35:24Z
[Message] timestamp=2026-11-04T23:35:24Z sender=ce2dd708-d288-4e8f-9834-dfdb673a5856 priority=MESSAGE_PRIORITY_HIGH content=You are m2_fix_worker_1.
Your working directory is: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_fix_worker_1
Your task instructions are in: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_fix_worker_1\DISPATCH.md
Read c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md, c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md, c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_fix_explorer_1\report.md, and your DISPATCH.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Apply the exact remediation to src/kutomoto/engine/runner.py, src/kutomoto/engine/safety.py, tests/test_win32_driver.py, and tests/test_engine.py.
Run pytest on all test suites (including challenge tests), ensure 100% pass, and deliver handoff.md. Report back via send_message when complete.
