# Milestone 5 Adversarial Challenge & Empirical Verification Report

**Agent**: `m5_challenger_1` (EMPIRICAL CHALLENGER: critic, specialist)  
**Milestone**: Milestone 5 (Sample Target Forms & E2E Automated Verification)  
**Verdict**: **`REQUEST_CHANGES`**

---

## 1. Observation

### Observation 1.1: Baseline E2E Suite Execution
Ran baseline adversarial verification command from dispatch:
```powershell
python -m pytest tests/test_e2e_automation.py -k TestAdversarialAndEdgeCasesE2E -v
```
Output:
```
tests/test_e2e_automation.py::TestAdversarialAndEdgeCasesE2E::test_01_loss_of_focus_guardian_auto_pause_and_resume PASSED [ 16%]
tests/test_e2e_automation.py::TestAdversarialAndEdgeCasesE2E::test_02_emergency_escape_key_abort PASSED [ 33%]
tests/test_e2e_automation.py::TestAdversarialAndEdgeCasesE2E::test_03_corner_failsafe_abort PASSED [ 50%]
tests/test_e2e_automation.py::TestAdversarialAndEdgeCasesE2E::test_04_parameter_length_boundaries_and_special_chars PASSED [ 66%]
tests/test_e2e_automation.py::TestAdversarialAndEdgeCasesE2E::test_05_error_recovery_policies PASSED [ 83%]
tests/test_e2e_automation.py::TestAdversarialAndEdgeCasesE2E::test_06_audit_log_90studio_compliance_and_credential_masking PASSED [100%]
====================== 6 passed, 12 deselected in 0.25s =======================
```
All 6 isolated adversarial tests pass when executed individually with fresh `WorkflowRunner` instances.

---

### Observation 1.2: Empirical Vulnerability VULN-M5-01: State Leakage in `SafetyGuard._last_cursor_pos` Across Consecutive Executions
Created dedicated empirical stress suite `tests/test_m5_adversarial_challenge.py` to evaluate runner lifecycle, rapid concurrency, failsafe disarm, hook cleanup, and sequential batch execution.

In `tests/test_m5_adversarial_challenge.py::TestRapidConcurrencyAndLifecycleFSM::test_07_vulnerability_consecutive_success_executions_cursor_leakage`:
```python
runner = WorkflowRunner(driver=mock_driver)
# Workflow 1 executes successfully, ending at cursor (200, 200)
audit1 = await runner.execute(wf)
assert audit1.execution_summary.final_status == "SUCCESS"

# In between workflows, operator or system moves cursor to (500, 500) (>100px away)
mock_driver.set_cursor_pos(500, 500)

# Workflow 2 executes on the same runner instance
audit2 = await runner.execute(wf)
```
Execution log:
```
WARNING  kutomoto.safety:safety.py:163 Accidental mouse disturbance detected (E08): displacement 424.3px exceeds threshold 100.0px
CRITICAL kutomoto.runner:runner.py:573 Emergency safety guardrail triggered: Operator mouse disturbance detected: 424.3px displacement
```
Direct reproduction via standalone Python command:
```powershell
python -c "import sys; sys.path.insert(0, 'src'); from kutomoto.engine.safety import SafetyGuard, MockWin32Driver, MouseDisturbanceDetected; driver = MockWin32Driver(); guard = SafetyGuard(driver=driver); driver.set_cursor_pos(250, 330); guard.check_mouse_disturbance(); driver.set_cursor_pos(500, 500); guard.check_mouse_disturbance()"
```
Output:
```
Accidental mouse disturbance detected (E08): displacement 302.3px exceeds threshold 100.0px
Traceback (most recent call last):
  ...
kutomoto.engine.safety.MouseDisturbanceDetected: Operator mouse disturbance detected: 302.3px displacement
```

Code inspection of `src/kutomoto/engine/runner.py` (lines 405–424 and lines 744–748):
```python
        # Context Initialization
        ctx = ExecutionContext(
            workflow=workflow,
            execution_id=str(uuid.uuid4()),
            variables={v.name: v.default_value for v in workflow.variables},
            start_time=time.perf_counter(),
            operator_username=op_user,
            host_machine=platform.node(),
        )
        if runtime_variables:
            ctx.variables.update(runtime_variables)
        ctx.pause_event.set()
        self._ctx = ctx
```
Neither `runner.execute()` initialization nor `runner.execute()` completion resets `self._safety_guard._last_cursor_pos`. `self._last_cursor_pos` is ONLY reset to `None` inside `SafetyGuard.emergency_cleanup()` (line 239 of `safety.py`), which is exclusively called on emergency aborts, never on normal successful completions or routine resets.

---

### Observation 1.3: Finding FINDING-M5-02: Variable Interpolation Rejects Whitespace-Padded Templates
In `src/kutomoto/engine/runner.py` (lines 116–130):
```python
    def _interpolate_variables(self, text: str, variables: Dict[str, Any]) -> str:
        """Replaces {{var_name}} occurrences with runtime variable values."""
        if not text or "{{" not in text:
            return text

        def repl(match):
            var_name = match.group(1).strip()
            if var_name in variables:
                val = variables[var_name]
                if val is not None:
                    return str(val)
            return match.group(0)

        return re.sub(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}", repl, text)
```
- Line 122 calls `var_name = match.group(1).strip()`, demonstrating design intent to support whitespace padding inside templates (e.g. `{{ var_name }}`).
- However, line 130 uses regex `r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}"`, which requires immediate non-whitespace character after `{{`, completely ignoring `{{ var_name }}`.
Verification command:
```powershell
python -c "import re; print(re.sub(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}', 'MATCH', 'Hello {{ name }} and {{name}}'))"
```
Output:
```
Hello {{ name }} and MATCH
```

---

### Observation 1.4: Empirical Stress Suite Results (`tests/test_m5_adversarial_challenge.py`)
Ran all 19 adversarial challenge tests:
```powershell
python -m pytest tests/test_m5_adversarial_challenge.py -v
```
Output:
```
tests/test_m5_adversarial_challenge.py::TestRapidConcurrencyAndLifecycleFSM::test_01_rapid_pause_resume_flapping_under_load PASSED [  5%]
tests/test_m5_adversarial_challenge.py::TestRapidConcurrencyAndLifecycleFSM::test_02_concurrent_abort_and_pause_race PASSED [ 10%]
tests/test_m5_adversarial_challenge.py::TestRapidConcurrencyAndLifecycleFSM::test_03_abort_while_paused_in_deep_workflow PASSED [ 15%]
tests/test_m5_adversarial_challenge.py::TestRapidConcurrencyAndLifecycleFSM::test_04_abort_during_countdown_phase PASSED [ 21%]
tests/test_m5_adversarial_challenge.py::TestRapidConcurrencyAndLifecycleFSM::test_05_abort_during_long_delay_step PASSED [ 26%]
tests/test_m5_adversarial_challenge.py::TestRapidConcurrencyAndLifecycleFSM::test_06_runner_reuse_after_abort_and_error PASSED [ 31%]
tests/test_m5_adversarial_challenge.py::TestRapidConcurrencyAndLifecycleFSM::test_07_vulnerability_consecutive_success_executions_cursor_leakage PASSED [ 36%]
tests/test_m5_adversarial_challenge.py::TestFailsafeDisarmAndHookCleanup::test_01_escape_abort_releases_all_11_modifier_vks PASSED [ 42%]
tests/test_m5_adversarial_challenge.py::TestFailsafeDisarmAndHookCleanup::test_02_corner_failsafe_multi_quadrant_boundaries PASSED [ 47%]
tests/test_m5_adversarial_challenge.py::TestFailsafeDisarmAndHookCleanup::test_03_mouse_disturbance_detector_displacement PASSED [ 52%]
tests/test_m5_adversarial_cleanup::TestFailsafeDisarmAndHookCleanup::test_04_safety_background_watcher_lifecycle PASSED [ 57%]
tests/test_m5_adversarial_challenge.py::TestFocusLossGuardianAdversarial::test_01_repeated_focus_theft_flapping_recovery PASSED [ 63%]
tests/test_m5_adversarial_challenge.py::TestFocusLossGuardianAdversarial::test_02_focus_guardian_auto_restoration PASSED [ 68%]
tests/test_m5_adversarial_challenge.py::TestFocusLossGuardianAdversarial::test_03_focus_loss_permanent_failure_raises_focus_lost_error PASSED [ 73%]
tests/test_m5_adversarial_challenge.py::TestExtremeBoundariesAndInterpolation::test_01_extreme_unicode_homoglyphs_and_special_chars PASSED [ 78%]
tests/test_m5_adversarial_challenge.py::TestExtremeBoundariesAndInterpolation::test_02_variable_interpolation_boundaries_and_numeric_zero PASSED [ 84%]
tests/test_m5_adversarial_challenge.py::TestErrorRecoveryPolicies::test_01_retry_step_exhaustion_then_failure PASSED [ 89%]
tests/test_m5_adversarial_challenge.py::TestErrorRecoveryPolicies::test_02_prompt_user_custom_resolver_skip_and_retry PASSED [ 94%]
tests/test_m5_adversarial_challenge.py::TestAuditLogMaskingAndCompliance::test_01_multi_secret_masking_complete_erasure_from_telemetry PASSED [100%]
============================= 19 passed in 3.50s ==============================
```
- Linting: `python -m ruff check tests/test_m5_adversarial_challenge.py` -> `All checks passed!` (0 errors).
- AST Analysis: `python -c "import ast; f = 'tests/test_m5_adversarial_challenge.py'; print(sum(isinstance(n, ast.Pass) for n in ast.walk(ast.parse(open(f, encoding='utf-8').read()))))"` -> `0` bare pass statements.
- Attribution: Checked `"Copyrights reserved to 90Studio"` -> present.

---

## 2. Logic Chain

1. **State Isolation Requirement**: In enterprise form filling automation (e.g. processing batches of banking KYC requests or telecom SIMs sequentially), a workflow runner must safely execute consecutive workflows without cross-execution state contamination.
2. **Safety Guardrail Function**: `SafetyGuard.check_mouse_disturbance()` is intended to abort an active workflow if the human operator accidentally bumps or moves the physical mouse cursor by more than 100 pixels *during execution*.
3. **Observation Reference (1.2)**: `self._last_cursor_pos` records the physical cursor coordinates of the last automation action. When a workflow finishes with `COMPLETED`, `_last_cursor_pos` is not cleared.
4. **Vulnerability Mechanics**: When the runner subsequently executes another workflow (or re-executes the same workflow for the next record), Step 1 calls `pre_step_check()`. `check_mouse_disturbance()` compares the current initial cursor position against `_last_cursor_pos` from the *previous workflow*. If the cursor was moved in between workflows (e.g., operator clicking a UI button or switching tasks), `hypot(dx, dy)` exceeds 100px, triggering `MouseDisturbanceDetected`.
5. **Impact / Blast Radius**: The subsequent workflow is immediately aborted with `ABORTED` status before performing any productive work, completely breaking sequential/batch automation workflows.
6. **Observation Reference (1.3)**: `_interpolate_variables` has dead code `var_name = match.group(1).strip()` because regex `r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}"` prevents matching any template containing whitespace, leaving valid user templates like `{{ full_name }}` un-interpolated.

---

## 3. Caveats

- In single-run scenarios where a fresh `WorkflowRunner` is instantiated for every individual workflow execution, `VULN-M5-01` is not triggered because `_last_cursor_pos` initializes to `None`. The vulnerability strictly impacts runner reuse and sequential multi-workflow sessions.
- In `tests/test_m3_it2_empirical_adversarial.py`, `test_500_field_benchmark_under_100ms` may occasionally take ~120ms when executed concurrently during full 390+ test suite runs under high background CPU load, but passes in < 85ms when executed in isolation.
- Hardware Win32 tests in CI run in deterministic mock driver mode unless `KUTOMOTO_LIVE_TEST=1` is explicitly set in an active Windows desktop session.

---

## 4. Conclusion & Verdict

**Verdict**: **`REQUEST_CHANGES`**

Milestone 5 has delivered robust sample targets, comprehensive action flows, and strong FSM concurrency controls. However, acceptance is blocked due to the confirmed state leakage bug `VULN-M5-01` in the safety engine.

### Required Actions for Worker:
1. **Fix `VULN-M5-01` (SafetyGuard State Leakage)**:
   - In `src/kutomoto/engine/safety.py`, add a `reset()` method to `SafetyGuard`:
     ```python
     def reset(self) -> None:
         """Resets internal safety state before a new workflow run."""
         self._abort_requested = False
         self._last_cursor_pos = None
     ```
   - In `src/kutomoto/engine/runner.py`, call `self._safety_guard.reset()` at the beginning of `execute()` (e.g., right after `self._ctx = ctx` around line 423), and optionally in `_finalize_audit()` upon completion.
2. **Fix `FINDING-M5-02` (Variable Interpolation Whitespace Rigidity)**:
   - In `src/kutomoto/engine/runner.py` line 130, update the regex to allow optional whitespace:
     ```python
     return re.sub(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", repl, text)
     ```
3. **Verify Zero Regressions**:
   - Ensure `tests/test_m5_adversarial_challenge.py` and `tests/test_e2e_automation.py` pass cleanly.
   - Ensure `python -m ruff check src/ tests/ samples/` reports 0 errors.

---

## 5. Verification Method

To verify the findings and confirm the fix:

1. **Run State Leakage Reproducer**:
   ```powershell
   python -m pytest tests/test_m5_adversarial_challenge.py -k test_07_vulnerability_consecutive_success_executions_cursor_leakage -v
   ```
   *Current Observation*: Fails if asserting `final_status == "SUCCESS"` on Run 2 because Run 2 aborts due to leaked `_last_cursor_pos`. After the worker fix, Run 2 should complete with `SUCCESS`.

2. **Run Full M5 Adversarial Challenge Suite**:
   ```powershell
   python -m pytest tests/test_m5_adversarial_challenge.py -v
   ```
   *Expected*: All 19 tests pass in ~3.5s.

3. **Run M5 E2E Automated Suite**:
   ```powershell
   python -m pytest tests/test_e2e_automation.py -v
   ```
   *Expected*: All 18 tests pass in ~3.6s.

4. **Verify Linting & AST Pass Compliance**:
   ```powershell
   python -m ruff check src/ tests/ samples/
   python -c "import ast, glob; files = glob.glob('tests/*.py') + glob.glob('src/**/*.py', recursive=True); [print(f, count) for f in files if (count := sum(isinstance(n, ast.Pass) for n in ast.walk(ast.parse(open(f, encoding='utf-8').read())))) > 0]"
   ```
   *Expected*: Ruff `All checks passed!` and 0 bare pass statements across all project code.
