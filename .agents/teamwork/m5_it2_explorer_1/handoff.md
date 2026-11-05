# Milestone 5 Iteration 2 Technical Blueprint & Investigation Report

**Agent**: `m5_it2_explorer_1` (teamwork_explorer: explorer, investigator, synthesizer)  
**Milestone**: Milestone 5 (Sample Target Forms & E2E Automated Verification — Iteration 2)  
**Target Files Analyzed**:
- `samples/desktop/telecom_sim_provisioning_workflow.json`
- `samples/web/banking_kyc_workflow.json`
- `src/kutomoto/engine/schema.py`
- `src/kutomoto/engine/runner.py`
- `src/kutomoto/engine/safety.py`
- `src/kutomoto/automation/win32_window.py`
- `src/kutomoto/automation/win32_driver.py`
- `tests/test_e2e_automation.py`
- `tests/test_m5_adversarial_challenge.py`
- `tests/test_m5_adversarial_empirical.py`

---

## 1. Observation

### 1.1 Verbatim Schema Defect in `samples/desktop/telecom_sim_provisioning_workflow.json`
- **Location**: `samples/desktop/telecom_sim_provisioning_workflow.json`, lines 9–14:
  ```json
    "target_application": {
      "type": "desktop_window",
      "window_title_pattern": "Telecom SIM Provisioning System — 90Studio",
      "process_name": "python.exe",
      "match_mode": "contains"
    },
  ```
- **Schema Definition**: `src/kutomoto/engine/schema.py`, lines 39–43 and 198–204:
  ```python
  class TargetAppType(str, Enum):
      WEB_BROWSER = "web_browser"
      WINDOWS_DESKTOP = "windows_desktop"
      ANY = "any"

  class TargetApplication(BaseModel):
      type: TargetAppType = Field(default=TargetAppType.WINDOWS_DESKTOP)
      window_title_pattern: str = Field(..., min_length=1)
      process_name: Optional[str] = None
      browser_url_pattern: Optional[str] = None
      match_mode: MatchMode = Field(default=MatchMode.CONTAINS)
  ```
- **Verbatim Error**:
  Executing `KutomotoWorkflow.model_validate_json(Path("samples/desktop/telecom_sim_provisioning_workflow.json").read_text(encoding="utf-8"))`:
  ```
  pydantic_core._pydantic_core.ValidationError: 1 validation error for KutomotoWorkflow
  target_application.type
    Input should be 'web_browser', 'windows_desktop' or 'any' [type=enum, input_value='desktop_window', input_type=str]
  ```
- **Comparison with Web Sample**:
  In `samples/web/banking_kyc_workflow.json`, line 12:
  ```json
    "target_application": {
      "type": "web_browser",
      "window_title_pattern": ".*Banking KYC.*",
      "process_name": "msedge.exe",
      "browser_url_pattern": null,
      "match_mode": "regex"
    },
  ```
  Deserializing `samples/web/banking_kyc_workflow.json` via `KutomotoWorkflow.model_validate_json()` succeeds with 0 errors (`TargetAppType.WEB_BROWSER`).

### 1.2 Mechanics of `process_name` Resolution Across Drivers
- **Runner Invocation (`src/kutomoto/engine/runner.py`, lines 228–236)**:
  ```python
  async def _execute_focus_window(self, step: WorkflowStep, ctx: ExecutionContext) -> None:
      pattern = step.parameters.window_title_pattern or ctx.workflow.target_application.window_title_pattern
      mode = step.parameters.match_mode or ctx.workflow.target_application.match_mode
      proc = step.parameters.process_name or ctx.workflow.target_application.process_name

      mode_str = mode.value if hasattr(mode, "value") else str(mode)
      hwnd = self._driver.find_window(pattern, match_mode=mode_str, process_name=proc)
      if not hwnd:
          raise RuntimeError(f"Target window matching '{pattern}' (process: {proc}) not found.")
  ```
- **Mock / Virtual Driver Implementation (`src/kutomoto/engine/safety.py`, lines 423–431)**:
  ```python
  pattern = re.compile(title_pattern, re.IGNORECASE)
  for hwnd, win in self.windows.items():
      if pattern.search(win["title"]):
          if process_name:
              if win["process_name"].lower() == process_name.lower():
                  return hwnd
          else:
              return hwnd
  return None
  ```
- **Native Win32 Implementation (`src/kutomoto/automation/win32_window.py`, lines 189–217)**:
  ```python
  for win in windows:
      # Check executable name filter
      if exe_name:
          if case_sensitive:
              if win.executable_name != exe_name:
                  continue
          else:
              if win.executable_name.lower() != exe_name.lower():
                  continue

      # Check title filter
      if title_pattern:
          ...
          return win
  ```
- **Key Observation on Process Filtering**:
  1. Both `MockWin32Driver` and `win32_window.py` implement `if process_name:` (or `if exe_name:`).
  2. Both do **strict case-insensitive exact string equality** (`win["process_name"].lower() == process_name.lower()`). Neither supports regex patterns or comma/pipe separated lists in `process_name`.
  3. In `tests/test_e2e_automation.py` line 106, `VirtualTkinterDriver` registers:
     ```python
     self.add_mock_window(
         hwnd=1002,
         title="Telecom SIM Provisioning System — 90Studio",
         process_name="sample_desktop_form.exe",
         rect=(150, 150, 640, 580),
     )
     ```
  4. In live interactive execution on Windows via `python samples/desktop/sample_desktop_form.py`, the OS executable name is `python.exe` (or `pythonw.exe`).
  5. If `process_name` is set to `"python.exe"`, `VirtualTkinterDriver` fails (`"sample_desktop_form.exe" != "python.exe"`).
  6. If `process_name` is set to `"sample_desktop_form.exe"`, live Python execution fails (`"python.exe" != "sample_desktop_form.exe"`).
  7. If `process_name` is set to `null` (`None`): `if process_name:` evaluates to `False`. The driver matches window HWND purely by `window_title_pattern: "Telecom SIM Provisioning System — 90Studio"`. This succeeds universally across `VirtualTkinterDriver`, interactive `python.exe`, and compiled `sample_desktop_form.exe`.

### 1.3 Missing On-Disk Workflow Tests in `tests/test_e2e_automation.py`
- In `tests/test_e2e_automation.py`:
  - `TestBankingKYCWebFormE2E` (lines 486–598) tests in-memory visual layout compilation (`test_02`), in-memory step workflow construction (`test_03`), and static file validation (`test_01`, `test_04`). It does not load or execute `samples/web/banking_kyc_workflow.json`.
  - `TestTelecomSIMDesktopFormE2E` (lines 604–718) tests headless Tkinter (`test_02`), window focus (`test_03`), in-memory step workflow (`test_04`), and virtual driver with in-memory workflow (`test_05`). It does not load or execute `samples/desktop/telecom_sim_provisioning_workflow.json`.

### 1.4 Virtual Driver Click Focus Reset Defect
- In `tests/test_e2e_automation.py` (lines 130–141), `VirtualTkinterDriver.send_click()` only checks for clicks on `btn_provision`.
- Step 2 in `samples/desktop/telecom_sim_provisioning_workflow.json` executes a click on the `MSISDN` entry field (`norm_x: 0.625, norm_y: 0.179`, matching `(400, 104)` in client pixels).
- When a driver is reused across multiple runs, `self.active_field_index` remains at the end of the previous run (index 5) unless reset to 0 upon clicking `entry_msisdn`.

---

## 2. Logic Chain

1. *Premise*: Deliverables in `samples/` must be directly loadable by `WorkflowRunner`, conform to Pydantic schemas, and run cleanly without manual adjustments.
2. *Observation Reference (1.1)*: `samples/desktop/telecom_sim_provisioning_workflow.json` defines `"type": "desktop_window"`. `TargetAppType` enum defines members `WEB_BROWSER = "web_browser"`, `WINDOWS_DESKTOP = "windows_desktop"`, and `ANY = "any"`.
3. *Inference*: Changing `"type": "desktop_window"` to `"type": "windows_desktop"` satisfies `TargetAppType` schema validation.
4. *Observation Reference (1.2)*: `find_window` in both `MockWin32Driver` and `win32_window.py` checks `if process_name: win.proc.lower() == process_name.lower()`. Specifying either `python.exe` or `sample_desktop_form.exe` breaks one execution environment while passing the other.
5. *Inference*: Setting `"process_name": null` eliminates the brittle executable name constraint while preserving strict window targeting via the unique title `"Telecom SIM Provisioning System — 90Studio"`.
6. *Observation Reference (1.3)*: The test suite previously passed 100% despite the invalid JSON file because `tests/test_e2e_automation.py` only tested in-memory Python objects.
7. *Inference*: Adding test methods in `TestBankingKYCWebFormE2E` and `TestTelecomSIMDesktopFormE2E` that directly load, validate, and execute the on-disk JSON files closes the validation gap.
8. *Observation Reference (1.4)*: Adding coordinate matching for `entry_msisdn` in `VirtualTkinterDriver.send_click` ensures that step 2 clicks reset field focus to 0, providing complete resilience for runner and driver reuse.

---

## 3. Caveats

- **No Caveats on Schema & Tests**: The proposed JSON changes and test cases have been empirically executed and proven with `SUCCESS` status in isolated Python execution.
- **Related Engine State Issues**: Challengers `m5_challenger_1` and `m5_challenger_2` documented two runner-level bugs:
  1. `VULN-M5-01`: `SafetyGuard._last_cursor_pos` state leakage across consecutive runs on the same runner instance.
  2. `FINDING-M5-02`: Regex in `_interpolate_variables()` rejecting whitespace within templates (`{{ var }}`).
  While our primary mandate is formulating the blueprint for the sample JSON workflow and E2E on-disk tests, the blueprint includes precise instructions for the implementer to address these companion findings to ensure a 100% green gate.

---

## 4. Conclusion & Technical Blueprint

### Blueprint 4.1: Fix `samples/desktop/telecom_sim_provisioning_workflow.json`

#### Target File
`samples/desktop/telecom_sim_provisioning_workflow.json` (lines 9–14)

#### Proposed Diff
```diff
--- a/samples/desktop/telecom_sim_provisioning_workflow.json
+++ b/samples/desktop/telecom_sim_provisioning_workflow.json
@@ -9,4 +9,4 @@
   "target_application": {
-    "type": "desktop_window",
+    "type": "windows_desktop",
     "window_title_pattern": "Telecom SIM Provisioning System — 90Studio",
-    "process_name": "python.exe",
+    "process_name": null,
     "match_mode": "contains"
   },
```

#### Full Context Replacement Chunk
```json
  "source_mode": "manual_step_flow",
  "target_application": {
    "type": "windows_desktop",
    "window_title_pattern": "Telecom SIM Provisioning System — 90Studio",
    "process_name": null,
    "match_mode": "contains"
  },
  "execution_settings": {
```

#### Rationale & Decisions Made
1. `"type": "windows_desktop"` matches `TargetAppType.WINDOWS_DESKTOP.value` in `src/kutomoto/engine/schema.py`.
2. `"process_name": null`:
   - Setting to `null` is strictly optimal compared to hardcoding `sample_desktop_form.exe` or `python.exe`.
   - In `VirtualTkinterDriver` (CI), `find_window` matches `title_pattern` and ignores `process_name`.
   - In live execution (`python samples/desktop/sample_desktop_form.py`), `find_window` matches `title_pattern` and ignores `process_name`.
   - If compiled to binary (`sample_desktop_form.exe`), `find_window` matches `title_pattern` and ignores `process_name`.
   - `window_title_pattern: "Telecom SIM Provisioning System — 90Studio"` is globally unique, highly specific, and carries the 90Studio brand attribution.
3. 90Studio copyright branding is fully maintained at root (`"copyright": "Copyrights reserved to 90Studio"`), author (`"author": "90Studio QA Engineer"`), and window title (`"Telecom SIM Provisioning System — 90Studio"`).

---

### Blueprint 4.2: Add Focus Reset to `VirtualTkinterDriver` in `tests/test_e2e_automation.py`

#### Target File
`tests/test_e2e_automation.py` (lines 130–142)

#### Proposed Code
```python
    def send_click(self, x: int, y: int, button: str = "left", click_count: int = 1) -> None:
        super().send_click(x, y, button, click_count)
        coords = self.app.get_control_coordinates()
        
        # Reset active field index to 0 if MSISDN entry field clicked (supports Step 2 of workflow)
        msisdn = coords.get("entry_msisdn", {})
        if msisdn:
            mx = msisdn.get("x", 220)
            my = msisdn.get("y", 90)
            mw = msisdn.get("width", 360)
            mh = msisdn.get("height", 28)
            if (mx <= x <= mx + mw and my <= y <= my + mh) or (y <= 125 and x >= 200):
                self.active_field_index = 0

        # Trigger submission if Provision button clicked
        btn = coords.get("btn_provision", {})
        if btn:
            bx = btn.get("x", 220)
            by = btn.get("y", 315)
            bw = btn.get("width", 175)
            bh = btn.get("height", 34)
            if (bx <= x <= bx + bw and by <= y <= by + bh) or (x >= 200 and y >= 300):
                self.app.submit()
```

---

### Blueprint 4.3: Formulate On-Disk Tests in `tests/test_e2e_automation.py`

#### 1. In `TestBankingKYCWebFormE2E`
Add `test_05_web_workflow_json_file_schema_and_execution` after line 598:

```python
    @pytest.mark.asyncio
    async def test_05_web_workflow_json_file_schema_and_execution(self, mock_driver, monkeypatch):
        """
        Directly loads samples/web/banking_kyc_workflow.json from disk,
        deserializes via KutomotoWorkflow.model_validate_json(), and executes
        against MockWin32Driver to verify end-to-end SUCCESS.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow_path = SAMPLES_WEB_DIR / "banking_kyc_workflow.json"
        assert workflow_path.exists(), f"Missing on-disk workflow file at {workflow_path}"

        raw_json = workflow_path.read_text(encoding="utf-8")
        workflow = KutomotoWorkflow.model_validate_json(raw_json)

        assert isinstance(workflow, KutomotoWorkflow)
        assert workflow.target_application.type == TargetAppType.WEB_BROWSER
        assert workflow.copyright == "Copyrights reserved to 90Studio"
        assert len(workflow.steps) == 17

        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert audit.execution_summary.failed_steps == 0
        assert audit.execution_summary.total_steps == 17
        assert runner.state == ExecutionState.COMPLETED
        assert audit.copyright == "Copyrights reserved to 90Studio"

        # Verify default variable values were interpolated and typed
        expected_typed = [
            "Eleanor Vance",
            "987-65-4321",
            "Checking",
            "125000",
            "Low",
            "e.vance@enterprise-bank.com",
        ]
        assert mock_driver.typed_text == expected_typed

        # Verify submission triggered
        assert any(k["key"] in ("enter", "return") for k in mock_driver.key_presses)
```

#### 2. In `TestTelecomSIMDesktopFormE2E`
Add `test_06_desktop_workflow_json_file_schema_and_execution` after line 718:

```python
    @pytest.mark.asyncio
    async def test_06_desktop_workflow_json_file_schema_and_execution(self, monkeypatch):
        """
        Directly loads samples/desktop/telecom_sim_provisioning_workflow.json from disk,
        deserializes via KutomotoWorkflow.model_validate_json(), and executes
        against in-memory Tkinter form via VirtualTkinterDriver to verify end-to-end SUCCESS.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        from samples.desktop.sample_desktop_form import create_app

        workflow_path = SAMPLES_DESKTOP_DIR / "telecom_sim_provisioning_workflow.json"
        assert workflow_path.exists(), f"Missing on-disk workflow file at {workflow_path}"

        raw_json = workflow_path.read_text(encoding="utf-8")
        workflow = KutomotoWorkflow.model_validate_json(raw_json)

        assert isinstance(workflow, KutomotoWorkflow)
        assert workflow.target_application.type == TargetAppType.WINDOWS_DESKTOP
        assert workflow.target_application.process_name is None
        assert workflow.copyright == "Copyrights reserved to 90Studio"
        assert len(workflow.steps) == 13

        try:
            app = create_app(headless=True)
            app.withdraw()

            driver = VirtualTkinterDriver(tkinter_app=app)
            runner = WorkflowRunner(driver=driver)

            audit = await runner.execute(workflow)
            assert audit.execution_summary.final_status == "SUCCESS"
            assert audit.execution_summary.failed_steps == 0
            assert audit.execution_summary.total_steps == 13
            assert runner.state == ExecutionState.COMPLETED
            assert audit.copyright == "Copyrights reserved to 90Studio"

            # Check that Tkinter app state was updated and submitted by runner
            state = app.get_state()
            assert state["is_submitted"] is True
            assert "SIM PROVISIONED SUCCESSFULLY" in state["status_text"].upper()

            # Verify provisioned payload fields and 90Studio copyright
            payload = state["last_payload"]
            assert payload["msisdn"] == "555-019-2834"
            assert payload["iccid"] == "8901410321111851072"
            assert payload["plan_type"] == "Postpaid Unlimited"
            assert payload["kyc_status"] == "VERIFIED"
            assert payload["imsi"] == "310410123456789"
            assert payload["copyright"] == "Copyrights reserved to 90Studio"

            app.destroy()
        except Exception as e:
            if "no display" in str(e).lower() or "tcl" in str(e).lower():
                pytest.skip(f"Tkinter display not available in environment: {e}")
            raise
```

---

### Blueprint 4.4: Companion Engine & Test Fixes for Worker Reference

To ensure complete gate passage across challenger suites (`test_m5_adversarial_challenge.py` and `test_m5_adversarial_empirical.py`):

1. **`SafetyGuard.reset()` (`src/kutomoto/engine/safety.py`)**:
   Add method to `SafetyGuard`:
   ```python
   def reset(self) -> None:
       """Resets internal safety state before a new workflow run."""
       self._abort_requested = False
       self._last_cursor_pos = None
   ```
2. **`WorkflowRunner.execute()` State Reset (`src/kutomoto/engine/runner.py`)**:
   - In `runner.execute()`, invoke `self._safety_guard.reset()` when initializing context or resetting terminal FSM.
   - Reset `self._audit_logger = None` upon starting a new execution so step events do not accumulate across runs on the same runner instance.
   - In `_interpolate_variables()`, change regex to `r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}"` so whitespace-padded templates like `{{ var }}` interpolate properly.
3. **`test_m5_adversarial_empirical.py`**:
   In `test_02_telecom_sim_provisioning_workflow_json_schema_validity`, update assertions so that when `target_type == "windows_desktop"`, it asserts `validation_error_found is False` and `wf.target_application.type == TargetAppType.WINDOWS_DESKTOP`.

---

## 5. Verification Method

Once the worker implements the blueprint, verify independently via the following commands:

### 1. Validate JSON Files Directly
```powershell
python -c "import sys; sys.path.insert(0, 'src'); from kutomoto.engine.schema import KutomotoWorkflow, TargetAppType; from pathlib import Path; wf_desk = KutomotoWorkflow.model_validate_json(Path('samples/desktop/telecom_sim_provisioning_workflow.json').read_text(encoding='utf-8')); assert wf_desk.target_application.type == TargetAppType.WINDOWS_DESKTOP; assert wf_desk.target_application.process_name is None; wf_web = KutomotoWorkflow.model_validate_json(Path('samples/web/banking_kyc_workflow.json').read_text(encoding='utf-8')); assert wf_web.target_application.type == TargetAppType.WEB_BROWSER; print('SUCCESS: Both sample workflows valid and conform to schema!')"
```
*Expected output*: `SUCCESS: Both sample workflows valid and conform to schema!`

### 2. Run E2E Automated Verification Suite
```powershell
python -m pytest tests/test_e2e_automation.py -v
```
*Expected*: All 20 tests pass (18 existing + 2 new on-disk workflow tests).

### 3. Run Challenger Verification Suites
```powershell
python -m pytest tests/test_m5_adversarial_challenge.py tests/test_m5_adversarial_empirical.py -v
```
*Expected*: All 37 tests pass.

### 4. Run Full Regression Suite
```powershell
python -m pytest tests/
```
*Expected*: All 430+ tests pass with zero failures.

### 5. Check Code Style & Bare `pass` Compliance
```powershell
python -m ruff check samples/ src/ tests/
python -c "import ast, glob; files = glob.glob('tests/*.py') + glob.glob('src/**/*.py', recursive=True); [print(f, count) for f in files if (count := sum(isinstance(n, ast.Pass) for n in ast.walk(ast.parse(open(f, encoding='utf-8').read())))) > 0]"
```
*Expected*: Ruff reports `All checks passed!` and bare `pass` count is 0.
