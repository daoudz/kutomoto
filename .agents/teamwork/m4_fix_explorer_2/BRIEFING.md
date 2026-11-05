# BRIEFING — 2026-11-05T04:39:00Z

## Mission
Formulate exact line-level fix strategies for F-M4-01 (pause race during pre/post-delay and transitions in PAUSED) and F-M4-02 (unhandled exception in _run_wrapper and resume dead task trap) in runner.py and app.py.

## 🔒 My Identity
- Archetype: explorer
- Roles: Concurrency and FSM execution mechanics exploration, read-only investigation
- Working directory: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_fix_explorer_2\
- Original parent: 59700fc9-320d-4ed3-b1db-2fc709fed831
- Milestone: M4

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Write only to own folder (.agents/teamwork/m4_fix_explorer_2/)
- Deliver exact line-level code replacements in handoff.md

## Current Parent
- Conversation ID: 59700fc9-320d-4ed3-b1db-2fc709fed831
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `src/kutomoto/engine/runner.py` (lines 340-351, 470-585, 685-746)
  - `src/kutomoto/engine/fsm.py` (lines 60-130)
  - `src/kutomoto/server/app.py` (lines 280-450)
  - `tests/test_m4_empirical_challenge.py` (lines 310-687)
  - `tests/test_api.py`, `tests/test_engine.py`
- **Key findings**:
  - `pre_delay` (lines 499-506) and `post_delay` (lines 694-702) in `runner.py` omit `if not ctx.pause_event.is_set(): await ctx.pause_event.wait()`, unlike `_execute_delay` (lines 346-347).
  - Calling `pause()` during `pre_delay` leaves state in `PAUSED`; after delay, step action runs and triggers `STEP_SUCCESS` or `STEP_EXCEPTION`, neither of which is valid in `PAUSED`.
  - Calling `pause()` during `post_delay` leaves state in `PAUSED`; after delay, step loop finishes and triggers `ALL_STEPS_DONE`, which is invalid in `PAUSED`.
  - In `WorkflowRunner.resume()`, calling `pause_event.set()` before `fsm.trigger(USER_RESUME)` risks waking waiting loops before FSM reaches `RUNNING`.
  - In `app.py`: `_run_wrapper` catches exceptions and broadcasts errors, but never transitions runner FSM to a terminal state (`STOPPED` / `ERROR`), leaving it in `PAUSED` or `RUNNING`.
  - In `app.py`: `is_active()` returns True whenever `_runner.fsm.is_active` is True, even if `_active_task.done()` is True (dead task).
  - In `app.py`: `resume()` fails to verify that `_active_task` is alive before transitioning `PAUSED` -> `RUNNING`.
- **Unexplored areas**: None. Complete root-cause and line-level fix strategy mapped.

## Key Decisions Made
- Guard both delay loops (`pre_delay` and `post_delay`) and their loop exits with `pause_event.wait()`.
- Guard `STEP_SUCCESS`, `STEP_EXCEPTION`, and `ALL_STEPS_DONE` triggers with `pause_event.wait()` and `fsm.can_trigger(...)`.
- In `WorkflowRunner.resume()`, trigger `USER_RESUME` *before* setting `pause_event.set()`.
- In `app.py`: In `_run_wrapper` exception handler, ensure runner FSM transitions to terminal state (`STOPPED` / `ERROR`).
- In `app.py`: In `is_active()`, immediately return `False` if `_active_task` is done.
- In `app.py`: In `resume()`, check if `_active_task` is dead, transition runner to terminal state, and raise HTTP 409.

## Artifact Index
- DISPATCH.md — Dispatch log
- BRIEFING.md — Persistent memory
- progress.md — Liveness heartbeat
- handoff.md — Final investigation report
