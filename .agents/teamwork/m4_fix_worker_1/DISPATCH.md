## 2026-11-05T04:41:01Z
You are m4_fix_worker_1, an implementation worker tasked with Milestone 4 Iteration 2 Remediation.
Working directory: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_fix_worker_1\

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY INPUTS (read before writing code):
- ORIGINAL_REQUEST.md: c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md
- PROJECT.md: c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md
- Auditor Evidence Report: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_auditor_1\handoff.md
- Challenger Evidence Report: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_challenger_1\handoff.md
- Fix Explorer 1 Blueprint (Auditor Items): c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_fix_explorer_1\handoff.md
- Fix Explorer 2 Blueprint (Runner/FSM Race Conditions): c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_fix_explorer_2\handoff.md
- Fix Explorer 3 Blueprint (Test Suite & QA): c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_fix_explorer_3\handoff.md

EXCLUSIVE FILE WRITE OWNERSHIP:
You own exclusively:
1. `src/kutomoto/ui/index.html`
2. `src/kutomoto/server/app.py`
3. `src/kutomoto/engine/runner.py`
4. `tests/test_api.py`
5. `tests/test_m4_empirical_challenge.py`
6. `tests/test_ui_m4_challenge.py`

TASKS TO EXECUTE:
1. In `src/kutomoto/ui/index.html`:
   - Update line 6 title tag to:
     `<title>kutomoto — Enterprise Form Automation — Copyrights reserved to 90Studio</title>`
2. In `src/kutomoto/engine/runner.py`:
   - Implement pause-awareness inside `pre_delay` loop and `post_delay` loop: check `if not ctx.pause_event.is_set(): await ctx.pause_event.wait()`.
   - Add post-loop pause checks before step dispatch and before `ALL_STEPS_DONE`.
   - Guard FSM transitions with `if self._fsm.can_trigger(...)` before `STEP_SUCCESS`, `STEP_EXCEPTION`, and `ALL_STEPS_DONE`.
   - In `resume()`: call `await self._fsm.trigger(FSMEvent.USER_RESUME)` first to transition to `RUNNING`, then call `self._ctx.pause_event.set()` to unblock waiters.
   - Ensure "Copyrights reserved to 90Studio" header is intact.
3. In `src/kutomoto/server/app.py`:
   - Defend `is_active()`: if `self._active_task is not None and self._active_task.done(): return False`.
   - In `_run_wrapper` exception handler: ensure runner is transitioned out of `PAUSED` into a terminal state (`ERROR` or `STOPPED`) so ghost running state is prevented.
   - In `resume()`: check `if self._active_task is None or self._active_task.done()` and reject with 409 if the background task is dead.
   - Implement `ServerExecutionManager.get_audit_summary(workflow_id: str)`: index execution summaries in `self._audit_summaries` stamped with `__copyright__` ("Copyrights reserved to 90Studio"), supporting active, completed, and on-disk audit queries.
   - Register route `GET /api/execute/audit/{workflow_id}` in `create_app()` returning the audit summary or 404 Problem Details.
4. In `tests/test_api.py`:
   - In `MockWin32Driver`: replace the 6 bare `pass` methods (`clear_field`, `send_scroll`, `send_key_down`, `send_key_up`, `send_mouse_down`, `send_mouse_up`) with concrete recording operations into instance lists (`cleared_fields`, `scrolls`, `held_keys`, `released_keys`, `mouse_buttons_down`, `mouse_buttons_up`). Zero bare passes!
   - In `test_root_endpoint_serves_spa_html`: add explicit assertion verifying `<title>kutomoto — Enterprise Form Automation — Copyrights reserved to 90Studio</title>` is in `resp.text`.
   - Add `TestAuditLogEndpoint` covering 404 on unexecuted workflow, 200 on completed workflow with 90Studio copyright watermark, and 200 on aborted workflow.
5. In `tests/test_m4_empirical_challenge.py`:
   - In `MockWin32Driver`: replace the duplicate 6 bare `pass` methods with recording operations so the file has zero bare passes.
   - In `test_vulnerability_post_delay_pause_causes_invalid_fsm_transition` and `test_vulnerability_pre_delay_pause_causes_invalid_fsm_transition`: remove the `@pytest.mark.xfail(strict=True)` markers and verify that both tests pass cleanly as active regression tests.
6. In `tests/test_ui_m4_challenge.py`:
   - In line 96: synchronize the expected page title assertion to `<title>kutomoto — Enterprise Form Automation — Copyrights reserved to 90Studio</title>`.

MANDATORY VERIFICATION (You MUST run these commands and report outputs):
1. `python -c "assert 'Copyrights reserved to 90Studio' in open('src/kutomoto/ui/index.html', encoding='utf-8').readlines()[5]"`
2. `python -c "import re; c = open('tests/test_api.py', encoding='utf-8').read(); p = [m.start() for m in re.finditer(r'^\s*pass\b', c, re.M)]; assert len(p) == 0, f'Found {len(p)} bare passes'"`
3. `python -m pytest tests/test_api.py -v`
4. `python -m pytest tests/test_m4_empirical_challenge.py -v`
5. `python -m pytest tests/test_ui_m4_challenge.py -v`
6. `python -m pytest tests/ -v`
7. `python -m ruff check src/ tests/`

DELIVERABLE:
Write `handoff.md` in your working directory with all changes, verification command outputs, and send a message to parent when complete.
