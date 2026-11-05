# Dispatch for m2_fix_explorer_1 (Milestone 2, Iteration 2)

## Objective
Synthesize the failure reports from `m2_reviewer_1`, `m2_reviewer_2`, `m2_challenger_1`, and `m2_challenger_2` into an exact, comprehensive remediation plan for `m2_fix_worker_1`.

## Inputs
- ORIGINAL_REQUEST: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md`
- Master Architecture: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md`
- Master Specification: `c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md`
- Reviewer 1 Handoff: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_reviewer_1\handoff.md`
- Reviewer 2 Handoff: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_reviewer_2\handoff.md`
- Challenger 1 Handoff: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_challenger_1\handoff.md`
- Challenger 2 Handoff: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_challenger_2\handoff.md`

## Instructions
1. Review the four failure reports and the empirical reproduction tests in `tests/test_m2_empirical_challenge.py` and `tests/test_engine_empirical_challenge.py`.
2. Formulate the exact drop-in code modifications for:
   - `src/kutomoto/engine/runner.py`:
     1. Fix coordinate arithmetic: use `client_w = rect[2]` and `client_h = rect[3]` directly.
     2. Prioritize `SafetyException` handling over error recovery policies: catch `SafetyException` (Escape, Corner Failsafe, Mouse Disturbance) to trigger immediate abort, modifier release, and audit finalize.
     3. Fix user pause: `await ctx.pause_event.wait()` at the start of step iteration loop.
     4. Fix resume: set `pause_event` reliably.
     5. Fix abort from paused: do not call `CLEANUP_DONE` if state is already terminal.
     6. Fix re-execution: call `RESET` if FSM is in terminal state at start of `execute()`.
     7. Release modifiers on step retry and skip branches.
     8. Support `0` and `False` in variable interpolation.
     9. Implement `PROMPT_USER` handling.
   - `src/kutomoto/engine/safety.py`:
     1. Align `MockWin32Driver.get_client_rect` to return `(screen_left, screen_top, width, height)`.
   - `tests/test_win32_driver.py` and `tests/test_engine.py`:
     1. Replace all tautological tests with genuine tests calling production code and mock driver.
     2. Add tests for `pause()`, `resume()`, `abort()`, `hotkey`, `delay`, `scroll`, and `prompt_user_input`.
3. Write your report to `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_fix_explorer_1\report.md` and deliver `handoff.md`.


## 2026-11-04T23:28:17Z
You are m2_fix_explorer_1.
Your working directory is: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_fix_explorer_1
Your task instructions are in: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_fix_explorer_1\DISPATCH.md
Read c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md, c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md, and your DISPATCH.md.
Synthesize the failure reports from m2_reviewer_1, m2_reviewer_2, m2_challenger_1, and m2_challenger_2 into an exact remediation plan.
Write your report to c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_fix_explorer_1\report.md and deliver handoff.md. Report back via send_message when done.
