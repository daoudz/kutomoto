# Milestone 5 Challenger Verification Report — m5_challenger_2

## Verdict: `REQUEST_CHANGES`

---

## 1. Observation

### Observation 1: Deliverable Schema Violation in `samples/desktop/telecom_sim_provisioning_workflow.json`
- **File**: `samples/desktop/telecom_sim_provisioning_workflow.json`, lines 9–14:
  ```json
  "target_application": {
    "type": "desktop_window",
    "window_title_pattern": "Telecom SIM Provisioning System — 90Studio",
    "process_name": "python.exe",
    "match_mode": "contains"
  }
  ```
- **Enum Specification**: `src/kutomoto/engine/schema.py`, lines 39–43:
  ```python
  class TargetAppType(str, Enum):
      WEB_BROWSER = "web_browser"
      WINDOWS_DESKTOP = "windows_desktop"
      ANY = "any"
  ```
- **Verbatim Error**: Executing `KutomotoWorkflow.model_validate_json(Path("samples/desktop/telecom_sim_provisioning_workflow.json").read_text(encoding="utf-8"))`:
  ```
  pydantic_core._pydantic_core.ValidationError: 1 validation error for KutomotoWorkflow
  target_application.type
    Input should be 'web_browser', 'windows_desktop' or 'any' [type=enum, input_value='desktop_window', input_type=str]
      For further information visit https://errors.pydantic.dev/2.12/v/enum
  ```
- **Impact**: Any user or API client loading this deliverable via `KutomotoWorkflow.model_validate_json()` or POSTing it to `/api/execute/start` will crash with a 422 Unprocessable Entity / Pydantic `ValidationError`. Furthermore, neither `samples/desktop/telecom_sim_provisioning_workflow.json` nor `samples/web/banking_kyc_workflow.json` was referenced, validated, or executed in `tests/test_e2e_automation.py`.

### Observation 2: `WorkflowRunner` Instance Reusability & State Pollution Bug
- **File**: `src/kutomoto/engine/runner.py`, lines 398–400 and 468–470:
  ```python
  # Support repeated execution: reset FSM if in terminal state
  if self._fsm.is_terminal:
      await self._fsm.trigger(FSMEvent.RESET)
  ...
  # Initialize audit logger if provided
  if not self._audit_logger:
      self._audit_logger = AuditLogger(execution_id=ctx.execution_id, workflow=workflow)
  ```
- **Verbatim Observation**: When a single `WorkflowRunner` instance executes a workflow sequentially:
  ```python
  runner = WorkflowRunner(driver=driver)
  audit_1 = await runner.execute(workflow)  # len(audit_1.step_events) == 21
  driver.cursor_x = 484; driver.cursor_y = 276
  audit_2 = await runner.execute(workflow)  # len(audit_2.step_events) == 42
  ```
  `self._audit_logger` is not reset; it retains all events from previous executions and continues appending.
- **Verbatim Safety Trip**: If the mouse cursor is reset between executions (e.g., operator returns cursor to home or driver resets to 0, 0):
  ```
  WARNING  kutomoto.safety:safety.py:163 Accidental mouse disturbance detected (E08): displacement 224.6px exceeds threshold 100.0px
  CRITICAL kutomoto.runner:runner.py:573 Emergency safety guardrail triggered: Operator mouse disturbance detected: 224.6px displacement
  Execution final status: ABORTED
  ```
  Because `self._safety_guard._last_cursor_pos` is not reset to `None` at the start of `execute()`, subsequent executions calculate displacement from where the previous execution terminated, raising false-positive `MouseDisturbanceDetected` aborts.
- **Worker Test Masking**: In `tests/test_e2e_automation.py::TestDeterministicCIAndLiveExecution::test_01_deterministic_mock_driver_reproducibility` (lines 946–955), this bug was concealed because the test instantiated `runner = WorkflowRunner(driver=mock_driver)` inside the loop on every single iteration instead of testing runner reuse.

### Observation 3: `VirtualTkinterDriver` Focus Tracking Defect
- **File**: `tests/test_e2e_automation.py`, lines 110–141 (`VirtualTkinterDriver`):
  `self.active_field_index` is initialized to 0 and incremented on Tab. It is never reset to 0 when `send_click(x, y)` is performed on field 1 (`entry_msisdn`).
- **Verbatim Error**: In repeated executions using the same `VirtualTkinterDriver`:
  At the end of run 0, `active_field_index == 5`. When run 1 starts and clicks at (220, 90), `active_field_index` remains 5. Keystrokes are injected into wrong widgets, leading to:
  ```
  Status: Validation Error - MSISDN must contain 7-15 digits (e.g. 555-019-2834)
  Records provisioned: 1 / 2
  ```

### Observation 4: Inaccurate Worker Handoff Documentation
- **File**: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m5_worker_1\handoff.md`, lines 8 and 11:
  - Worker claims `banking_kyc_workflow.json` has 21 sequential action steps; inspection reveals it has 17 steps.
  - Worker claims `telecom_sim_provisioning_workflow.json` has 21 sequential action steps and targets `sample_desktop_form.exe`; inspection reveals it has 13 steps and targets `python.exe`.

### Observation 5: Valid Deliverables and Passing Baseline Suites
- **Mandatory E2E Execution**:
  ```powershell
  python -m pytest tests/test_e2e_automation.py -k TestDeterministicCIAndLiveExecution -v
  ```
  Result: 3 passed, 15 deselected in 0.52s.
- **Full E2E Suite**:
  ```powershell
  python -m pytest tests/test_e2e_automation.py -v
  ```
  Result: 18 passed in 3.71s.
- **Empirical Adversarial & Stress Harness**:
  ```powershell
  python -m pytest tests/test_m5_adversarial_empirical.py -v
  ```
  Result: 18 passed in 1.06s.
  - Verifies payload fidelity across strings, numeric IDs, all 3 `PLAN_OPTIONS` ("Prepaid 5G", "Postpaid Unlimited", "Corporate Data"), all 3 `KYC_OPTIONS` ("VERIFIED", "PENDING_REVIEW", "CORPORATE_EXEMPT"), and boundary conditions.
  - Verifies contract fidelity across all 18 `IWin32Driver` protocol methods on both `MockWin32Driver` and live `ProductionDriverAdapter` / `Win32DriverAdapter`.
  - Verifies 50-iteration repeated sequential submission stress run: 50/50 records provisioned, stable memory (peak 395 KB, 0 leaks), and latency stability (< 0.25s per run).
- **Full Repository Test Suite**:
  ```powershell
  python -m pytest tests/
  ```
  Result: 429 passed in 52.95s.
- **Code Integrity & Formatting**:
  `python -m ruff check src/ tests/ samples/`: All checks passed.
  Bare `pass` statements across modified/created files: 0.

---

## 2. Logic Chain

1. **Premise 1 (Deliverable Conformance)**: Every sample workflow provided in `samples/` must be a valid `KutomotoWorkflow` JSON instance adhering to the unified schema.
   - *Observation*: `samples/desktop/telecom_sim_provisioning_workflow.json` specifies `"type": "desktop_window"`. `TargetAppType` enum only accepts `'web_browser'`, `'windows_desktop'`, `'any'`.
   - *Deduction*: `samples/desktop/telecom_sim_provisioning_workflow.json` crashes on load with `ValidationError`. The deliverable is broken out of the box.

2. **Premise 2 (Engine Reusability & State Cleanliness)**: `WorkflowRunner.execute()` claims to support repeated execution (`# Support repeated execution: reset FSM if in terminal state`).
   - *Observation*: `WorkflowRunner` does not clear `self._audit_logger` or `self._safety_guard._last_cursor_pos` upon starting a new execution.
   - *Deduction*: Calling `runner.execute()` more than once causes audit events to leak and accumulate from run to run, and triggers spurious `MouseDisturbanceDetected` aborts if the mouse cursor resets between runs.

3. **Premise 3 (Test Fidelity)**: `tests/test_e2e_automation.py` did not validate either of the delivered JSON workflow files in `samples/`, and avoided the runner reuse bug by instantiating new `WorkflowRunner` instances on each loop iteration.
   - *Deduction*: The tests tested synthetic, programmatic workflows rather than the actual deliverables, allowing schema and state pollution bugs to escape detection.

---

## 3. Caveats

1. The core form filling functionality, visual-to-workflow compilation, DOM and Tkinter form layouts, and Win32 hardware adapter methods are well implemented and structurally sound.
2. In-memory headless Tkinter execution operates smoothly across all field types once driver focus index is properly reset.
3. Live Win32 SendInput execution requires an active interactive Windows desktop session (standard constraint for desktop GUI automation).

---

## 4. Conclusion

Milestone 5 deliverables demonstrate strong foundational architecture, 100% Win32 adapter protocol parity, and high payload fidelity across field types. However, due to:
1. Deliverable schema invalidity in `samples/desktop/telecom_sim_provisioning_workflow.json` (`desktop_window` vs `windows_desktop`),
2. State pollution and false-positive aborts in `WorkflowRunner` upon repeated execution,
3. Lack of focus reset on field clicks in `VirtualTkinterDriver`,

The milestone cannot be approved in its current state.
**Verdict: `REQUEST_CHANGES`**

### Required Action Items for Milestone 5 Worker:
1. **Fix `samples/desktop/telecom_sim_provisioning_workflow.json`**:
   - Change `"type": "desktop_window"` to `"type": "windows_desktop"`.
   - Update `process_name` to match runtime execution (or set to `null` to rely on `window_title_pattern`).
2. **Add Sample JSON Workflow Tests to `tests/test_e2e_automation.py`**:
   - Add explicit assertions loading and validating both `samples/web/banking_kyc_workflow.json` and `samples/desktop/telecom_sim_provisioning_workflow.json` via `KutomotoWorkflow.model_validate_json()`.
3. **Fix `WorkflowRunner.execute` State Reset in `src/kutomoto/engine/runner.py`**:
   - At the beginning of `execute()` (or when resetting terminal FSM), reset `self._audit_logger = None` (or re-initialize if internally managed).
   - Reset `self._safety_guard._last_cursor_pos = None` and `self._safety_guard._abort_requested = False`.
4. **Update `VirtualTkinterDriver` in `tests/test_e2e_automation.py`**:
   - In `send_click()`, if the coordinates correspond to field 1 / `entry_msisdn`, reset `self.active_field_index = 0`.
5. **Correct Handoff Claims**:
   - Update `m5_worker_1/handoff.md` to reflect actual step counts (17 for web, 13 for desktop).

---

## 5. Verification Method

Execute the following commands to independently reproduce the findings and verify the test harness:

1. **Verify Deliverable Schema Error**:
   ```powershell
   python -c "import sys; sys.path.insert(0, 'src'); from kutomoto.engine.schema import KutomotoWorkflow; from pathlib import Path; KutomotoWorkflow.model_validate_json(Path('samples/desktop/telecom_sim_provisioning_workflow.json').read_text(encoding='utf-8'))"
   ```
   *Expected*: `pydantic_core._pydantic_core.ValidationError: 1 validation error for KutomotoWorkflow: target_application.type: Input should be 'web_browser', 'windows_desktop' or 'any'`.

2. **Verify Runner Reusability State Pollution & Disturbance Abort**:
   ```powershell
   python -m pytest tests/test_m5_adversarial_empirical.py -k test_03_runner_instance_reuse_state_pollution_demonstration -v
   ```
   *Expected*: PASSED (demonstrates 42 accumulated events on run 2 and ABORTED on run 3).

3. **Verify Empirical Adversarial & Stress Suite**:
   ```powershell
   python -m pytest tests/test_m5_adversarial_empirical.py -v
   ```
   *Expected*: 18 passed in ~1.1s.

4. **Verify Mandatory Milestone 5 E2E Tests**:
   ```powershell
   python -m pytest tests/test_e2e_automation.py -k TestDeterministicCIAndLiveExecution -v
   ```
   *Expected*: 3 passed in ~0.5s.

5. **Verify Full Repository Regression**:
   ```powershell
   python -m pytest tests/
   ```
   *Expected*: All 429 tests pass.
