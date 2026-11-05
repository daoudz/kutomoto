## 2026-11-05T10:07:27Z

You are m5_it2_worker_1, a teamwork_worker for kutomoto Milestone 5 Iteration 2 (Sample Target Forms & E2E Automated Verification).
Your working directory is: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m5_it2_worker_1\

Mandatory inputs to read before starting:
1. c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md
3. c:\Users\daoud\projects\kutomoto\.agents\teamwork\m5_it2_explorer_1\handoff.md
4. c:\Users\daoud\projects\kutomoto\.agents\teamwork\m5_it2_explorer_2\handoff.md
5. c:\Users\daoud\projects\kutomoto\.agents\teamwork\m5_it2_explorer_3\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Write Boundaries:
You own exclusively:
- `samples/desktop/telecom_sim_provisioning_workflow.json`
- `src/kutomoto/engine/safety.py`
- `src/kutomoto/engine/audit.py`
- `src/kutomoto/engine/runner.py`
- `tests/test_e2e_automation.py`
- `tests/test_m5_adversarial_challenge.py`
- `tests/test_m5_adversarial_empirical.py`
- `tests/test_engine.py`

Your Tasks:
Task 1: Fix `samples/desktop/telecom_sim_provisioning_workflow.json`:
- Change `"type": "desktop_window"` to `"type": "windows_desktop"`.
- Set `"process_name": null` so window targeting relies on `"window_title_pattern": "Telecom SIM Provisioning System — 90Studio"`.
- Preserve full 90Studio copyright attribution.

Task 2: Fix `src/kutomoto/engine/safety.py`:
- Add `reset(self) -> None` to `SafetyGuard`:
  ```python
  def reset(self) -> None:
      """Resets internal safety state before or after a workflow run."""
      self.stop_background_watcher()
      self._abort_requested = False
      self._last_cursor_pos = None
      self._active_target_hwnd = None
  ```

Task 3: Fix `src/kutomoto/engine/audit.py`:
- Add `reset(self, execution_id: Optional[str] = None, workflow: Optional[Any] = None) -> None` to `AuditLogger` to clear step events, reset start timer, and prevent event leakage across runs.

Task 4: Fix `src/kutomoto/engine/runner.py`:
- In `WorkflowRunner.__init__`: preserve `self._initial_audit_logger = audit_logger`.
- In `execute()`: call `self._safety_guard.reset()` at execution start, and re-initialize/reset `self._audit_logger` so each workflow execution has clean audit events without accumulation. Call `self._safety_guard.reset()` upon completion (`COMPLETED`).
- In `_interpolate_variables` line 129: update regex to `r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}"` so whitespace-padded templates like `{{ user_name }}` match and interpolate properly.

Task 5: Fix `VirtualTkinterDriver` in `tests/test_e2e_automation.py`:
- Implement full candidate coordinate hit-testing `[(x, y), (x - win_x, y - win_y)]` against `CONTROL_GEOMETRY` in `send_click()`, resetting `active_field_index = 0` on `entry_msisdn` click. Add `reset()` and dual process matching in `find_window()`.

Task 6: Add on-disk workflow validation tests in `tests/test_e2e_automation.py`:
- Validate both `samples/web/banking_kyc_workflow.json` and `samples/desktop/telecom_sim_provisioning_workflow.json` via `KutomotoWorkflow.model_validate_json()`.
- Execute the on-disk desktop workflow against `VirtualTkinterDriver` and verify `final_status == "SUCCESS"`, `is_submitted is True`, and 90Studio copyright.
- Verify repeated execution on the same driver instance.

Task 7: Synchronize Challenge Suites:
- In `tests/test_m5_adversarial_challenge.py::test_07_vulnerability_consecutive_success_executions_cursor_leakage`: assert `audit2.execution_summary.final_status == "SUCCESS"` and status `COMPLETED`. Add whitespace test vector to `test_02`.
- In `tests/test_m5_adversarial_empirical.py::test_03_runner_instance_reuse_state_pollution_demonstration`: assert `len(audit_2.step_events) == 21` and `audit_3.execution_summary.final_status == "SUCCESS"`.
- In `tests/test_engine.py`: add unit tests for `safety_guard.reset()`, `audit_logger.reset()`, and whitespace template interpolation.

Task 8: Verification & Quality:
- Run `python -m pytest tests/test_e2e_automation.py -v`
- Run `python -m pytest tests/test_m5_adversarial_challenge.py -v`
- Run `python -m pytest tests/test_m5_adversarial_empirical.py -v`
- Run `python -m pytest tests/` (all 432+ tests must pass)
- Run `python -m ruff check src/ tests/ samples/` (0 errors)
- Verify 0 bare pass statements via AST analysis.

Write your completion handoff report to `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m5_it2_worker_1\handoff.md` and notify caller via `send_message`.
