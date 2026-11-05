# Technical Blueprint & Fix Strategy: VULN-M5-01, Audit Logger Isolation, and FINDING-M5-02

**Agent**: `m5_it2_explorer_2` (teamwork_explorer: investigator, synthesist)  
**Milestone**: Milestone 5 (Sample Target Forms & E2E Automated Verification) — Iteration 2  
**Target Modules**: `src/kutomoto/engine/safety.py`, `src/kutomoto/engine/audit.py`, `src/kutomoto/engine/runner.py`, `tests/`  
**Copyright**: Copyrights reserved to 90Studio  

---

## 1. Observation

Direct code and test observations from repository inspection:

### 1.1 `VULN-M5-01`: State Leakage in `SafetyGuard._last_cursor_pos` Across Sequential Executions
- **File**: `src/kutomoto/engine/safety.py` (lines 86–176, 220–240)
- In `SafetyGuard`:
  - `self._last_cursor_pos: Optional[Tuple[int, int]] = None` is set to `(cur_x, cur_y)` during `check_mouse_disturbance()` (lines 154, 169, 175) or via `register_intentional_mouse_move()` (line 109).
  - In `emergency_cleanup()` (line 239), `self._last_cursor_pos = None` and `self._abort_requested = False` are executed only upon emergency abort.
  - Upon standard successful completion (`COMPLETED` state), `emergency_cleanup()` is never called.
  - `SafetyGuard` contains **zero** `reset()` method to restore baseline state between executions.
- **File**: `src/kutomoto/engine/runner.py` (lines 393–424, 744–748)
  - `runner.execute()` resets the FSM if terminal (`if self._fsm.is_terminal: await self._fsm.trigger(FSMEvent.RESET)`), but does not reset `self._safety_guard`.
  - When the runner executes Run 1, cursor ends at e.g. `(200, 200)`.
  - If the cursor moves between runs to `(500, 500)` (displacement 424.3px > 100.0px), Step 1 of Run 2 calls `pre_step_check()` -> `check_mouse_disturbance()`.
  - Displacement exceeds `mouse_disturbance_threshold_px` (100.0px), raising `MouseDisturbanceDetected: Operator mouse disturbance detected: 424.3px displacement`, aborting Run 2 immediately.
- **Verbatim Error**:
  ```
  WARNING  kutomoto.safety:safety.py:163 Accidental mouse disturbance detected (E08): displacement 424.3px exceeds threshold 100.0px
  CRITICAL kutomoto.runner:runner.py:573 Emergency safety guardrail triggered: Operator mouse disturbance detected: 424.3px displacement
  Execution final status: ABORTED
  ```
- **Test Reference**: `tests/test_m5_adversarial_challenge.py::test_07_vulnerability_consecutive_success_executions_cursor_leakage` passes today solely because it asserts the presence of the defect (`assert audit2.execution_summary.final_status == "ABORTED"`).

---

### 1.2 Audit Logger Accumulation Across Executions on Reused `WorkflowRunner`
- **File**: `src/kutomoto/engine/runner.py` (lines 79–94, 468–470)
  ```python
  def __init__(
      self,
      driver: Any,
      audit_logger: Optional[AuditLogger] = None,
      ...
  ):
      self._driver = driver
      self._audit_logger = audit_logger
      ...
  ```
  ```python
  # Line 468:
  if not self._audit_logger:
      self._audit_logger = AuditLogger(execution_id=ctx.execution_id, workflow=workflow)
  ```
- **File**: `src/kutomoto/engine/audit.py` (lines 137–156)
  - `AuditLogger` initializes with a fixed `execution_id`, `start_perf = time.perf_counter()`, and `self.step_events: List[AuditStepEvent] = []`.
  - `AuditLogger` has no `reset()` method.
- **Mechanism of Defect**:
  - When a runner is instantiated without an explicit logger (`runner = WorkflowRunner(driver=mock_driver)`), `self._audit_logger` is `None`.
  - On Run 1, line 468 instantiates `self._audit_logger = AuditLogger(execution_id=ctx.execution_id, workflow=workflow)`. Run 1 records 21 step events.
  - On Run 2, `if not self._audit_logger:` evaluates to `False`. The runner retains the logger from Run 1.
  - Consequently:
    1. Step events from Run 1 remain in `self._audit_logger.step_events`, causing Run 2 to accumulate 42 events (`len(audit_2.step_events) == 42`).
    2. `audit_2.execution_id` remains the stale execution ID from Run 1 instead of matching `ctx.execution_id` from Run 2.
    3. `audit_2.execution_summary.duration_seconds` measures elapsed time since Run 1's inception.
    4. If Run 2 aborts during the countdown phase (lines 438–456), `_finalize_audit` uses Run 1's populated audit logger instead of generating a clean aborted log.
- **Test Reference**: `tests/test_m5_adversarial_empirical.py::test_03_runner_instance_reuse_state_pollution_demonstration` explicitly asserts `len(audit_2.step_events) == 42`.

---

### 1.3 `FINDING-M5-02`: Variable Template Whitespace Rigidity
- **File**: `src/kutomoto/engine/runner.py` (lines 116–130)
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
- Line 122 calls `var_name = match.group(1).strip()`, demonstrating clear architectural intent to support whitespace padding inside variable placeholders (standard mustache/jinja syntax: `{{ variable }}`).
- However, line 130 uses regex `r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}"`, which strictly rejects any template token containing whitespace (e.g. `{{ user_name }}` or `{{   amount   }}`).
- Verbatim evaluation:
  ```powershell
  python -c "import sys; sys.path.insert(0, 'src'); from kutomoto.engine.runner import WorkflowRunner; from kutomoto.engine.safety import MockWin32Driver; r = WorkflowRunner(MockWin32Driver()); print(r._interpolate_variables('Hello {{ user_name }} and {{user_name}}', {'user_name': 'Alice'}))"
  ```
  Output:
  ```
  Hello {{ user_name }} and Alice
  ```
  `{{ user_name }}` was ignored and left un-interpolated.

---

## 2. Logic Chain

1. **State Isolation in Batch/Repeated Automations**:
   Enterprise workflows in banking and telecom routinely execute in batch mode, processing multiple customer records sequentially using a shared `WorkflowRunner` instance. A reusable automation engine must guarantee complete isolation between execution cycles.

2. **Deduction on `SafetyGuard`**:
   `check_mouse_disturbance()` calculates relative displacement against `self._last_cursor_pos`. Because `_last_cursor_pos` is not cleared on workflow completion, the first step of a subsequent workflow compares the operator's current mouse position against the coordinates from the previous run. This produces a false-positive `MouseDisturbanceDetected` abort whenever the operator moves the mouse between runs.
   *Resolution*: Implementing `SafetyGuard.reset()` to reset `self._abort_requested = False`, `self._last_cursor_pos = None`, `self._active_target_hwnd = None`, and cancel any background watcher task; and calling `self._safety_guard.reset()` at the start of `execute()` and upon successful completion (`COMPLETED`) eliminates state leakage.

3. **Deduction on `AuditLogger`**:
   `AuditLogger` encapsulates telemetry and compliance records for a single workflow run. When `WorkflowRunner` retains `self._audit_logger` across runs, events bleed across boundaries.
   *Resolution*: Providing an explicit `AuditLogger.reset(execution_id, workflow)` method and ensuring `WorkflowRunner.execute()` either re-instantiates `self._audit_logger = AuditLogger(...)` (when managed internally) or invokes `.reset()` on any constructor-provided logger guarantees that each execution generates an independent, unpolluted audit log.

4. **Deduction on Variable Interpolation**:
   User-entered workflow templates frequently include spaces within curly braces (`{{ first_name }}`). The regex `r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}"` allows optional whitespace around the identifier while capturing the identifier itself in group 1. Line 122's `var_name = match.group(1).strip()` then resolves the variable name seamlessly.

---

## 3. Caveats

1. **Adversarial Challenge Tests Asserting Defects**:
   Both `tests/test_m5_adversarial_challenge.py::test_07_vulnerability_consecutive_success_executions_cursor_leakage` and `tests/test_m5_adversarial_empirical.py::test_03_runner_instance_reuse_state_pollution_demonstration` currently assert the *presence* of the defects (e.g. `final_status == "ABORTED"` and `len == 42`). Once the fixes are applied, these assertions must be updated to assert the *fixed, correct behavior* (`final_status == "SUCCESS"` and `len == 21`), or pytest will fail.
2. **Server Concurrency Contract**:
   `src/kutomoto/server/app.py` passes `audit_logger = AuditLogger(execution_id=self._execution_id, workflow=workflow)` to `WorkflowRunner`. On the initial run of a runner, `ctx.execution_id` should preserve `self._initial_audit_logger.execution_id` so that API queries to `/api/execute/audit/{execution_id}` remain 100% symmetric with `self._execution_id`.

---

## 4. Conclusion & Technical Blueprint

### Action 4.1: Update `src/kutomoto/engine/safety.py`

Add `reset(self) -> None` to `SafetyGuard` (insert around line 240, immediately following `emergency_cleanup()`):

```python
    def reset(self) -> None:
        """
        Resets internal safety state before a new workflow run.
        Clears abort request flag, last recorded cursor position, target HWND,
        and halts any active background watcher task.
        """
        self.stop_background_watcher()
        self._abort_requested = False
        self._last_cursor_pos = None
        self._active_target_hwnd = None
```

---

### Action 4.2: Update `src/kutomoto/engine/audit.py`

Add `reset()` to `AuditLogger` (insert around line 157, right after `set_target_app_details`):

```python
    def reset(self, execution_id: Optional[str] = None, workflow: Optional[Any] = None) -> None:
        """
        Resets internal audit logger state for an isolated workflow execution run.
        Clears step events, resets start timer, and optionally updates execution_id/workflow.
        """
        if execution_id is not None:
            self.execution_id = execution_id
        if workflow is not None:
            self.workflow = workflow
            self._target_app_info = AuditTargetApplication(
                title=getattr(workflow.target_application, "window_title_pattern", ""),
                hwnd=0,
                process_name=getattr(workflow.target_application, "process_name", "") or "unknown",
                pid=0,
            )
        self.start_perf = time.perf_counter()
        self.step_events.clear()
```

---

### Action 4.3: Update `src/kutomoto/engine/runner.py`

#### 4.3.1 In `WorkflowRunner.__init__`:
Store `self._initial_audit_logger` and track single execution vs reuse:
```python
    def __init__(
        self,
        driver: Any,
        audit_logger: Optional[AuditLogger] = None,
        telemetry_callback: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
        safety_guard: Optional[SafetyGuard] = None,
        prompt_resolver: Optional[Any] = None,
    ):
        self._driver = driver
        self._initial_audit_logger = audit_logger
        self._audit_logger = audit_logger
        self._telemetry_cb = telemetry_callback
        self._safety_guard = safety_guard or SafetyGuard(driver=driver)
        self._prompt_resolver = prompt_resolver
        self._fsm = ExecutionFSM()
        self._ctx: Optional[ExecutionContext] = None
        self._has_run_once = False
```

#### 4.3.2 In `_interpolate_variables` (line 129):
Update regex to accept optional whitespace around variable identifier:
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

        return re.sub(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", repl, text)
```

#### 4.3.3 In `execute()` initialization (lines 405–424):
Initialize clean execution context, reset `SafetyGuard`, and re-initialize/reset `AuditLogger`:
```python
        # Context Initialization
        try:
            op_user = os.getlogin()
        except Exception:
            op_user = "enterprise_user"

        # Determine execution ID: preserve provided audit logger ID on initial run, generate new UUID on reuse
        if self._initial_audit_logger is not None and not self._has_run_once:
            exec_id = self._initial_audit_logger.execution_id
        else:
            exec_id = str(uuid.uuid4())
        self._has_run_once = True

        ctx = ExecutionContext(
            workflow=workflow,
            execution_id=exec_id,
            variables={v.name: v.default_value for v in workflow.variables},
            start_time=time.perf_counter(),
            operator_username=op_user,
            host_machine=platform.node(),
        )
        if runtime_variables:
            ctx.variables.update(runtime_variables)
        ctx.pause_event.set()  # Unpaused initially
        self._ctx = ctx

        # Clean Execution State Isolation:
        # 1. Reset safety guard to purge stale cursor pos and abort flags from previous runs
        if hasattr(self._safety_guard, "reset"):
            self._safety_guard.reset()

        # 2. Reinitialize or reset audit logger so events do not accumulate across runs
        if self._initial_audit_logger is not None:
            self._audit_logger = self._initial_audit_logger
            if hasattr(self._audit_logger, "reset"):
                self._audit_logger.reset(execution_id=ctx.execution_id, workflow=workflow)
            else:
                self._audit_logger.execution_id = ctx.execution_id
                self._audit_logger.workflow = workflow
                self._audit_logger.step_events.clear()
                self._audit_logger.start_perf = time.perf_counter()
        else:
            self._audit_logger = AuditLogger(execution_id=ctx.execution_id, workflow=workflow)
```

#### 4.3.4 In `execute()` line 468:
Since `self._audit_logger` is now guaranteed to be initialized before the countdown and step loop, update lines 468–470 to serve as a fallback:
```python
        # Ensure audit logger is present (fallback safety check)
        if not self._audit_logger:
            self._audit_logger = AuditLogger(execution_id=ctx.execution_id, workflow=workflow)
```

#### 4.3.5 In `execute()` completion (lines 744–748):
Reset safety guard upon successful completion:
```python
        # T08: RUNNING -> COMPLETED (guarded against state PAUSED)
        if self._fsm.can_trigger(FSMEvent.ALL_STEPS_DONE):
            await self._fsm.trigger(FSMEvent.ALL_STEPS_DONE)
        if hasattr(self._safety_guard, "reset"):
            self._safety_guard.reset()
        return self._finalize_audit(ctx, "SUCCESS")
```

---

### Action 4.4: Update Challenge Tests to Assert Correct Behavior

#### 4.4.1 `tests/test_m5_adversarial_challenge.py`:
In `TestRapidConcurrencyAndLifecycleFSM::test_07_vulnerability_consecutive_success_executions_cursor_leakage`:
```python
        # Run 2 starts: verifies that reset _last_cursor_pos prevents false abort and completes successfully
        audit2 = await runner.execute(wf)
        assert audit2.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED
        assert len(audit2.step_events) == 3
```

#### 4.4.2 `tests/test_m5_adversarial_empirical.py`:
In `TestRepeatedSequentialSubmissionsStressAndNoLeaks::test_03_runner_instance_reuse_state_pollution_demonstration`:
```python
        # Verification 1: Audit logger isolation (run 2 does not accumulate run 1 events)
        assert len(audit_2.step_events) == 21, (
            "Audit logger must be isolated per execution and contain exactly 21 events"
        )
        assert audit_2.execution_summary.final_status == "SUCCESS"

        # Verification 2: Resetting cursor to (0,0) between runs does not trip false-positive disturbance
        driver.reset()
        driver.add_mock_window(
            1001,
            "Banking KYC Onboarding — kutomoto Automation Target — Copyrights reserved to 90Studio - Microsoft Edge",
            "msedge.exe",
            (100, 100, 1200, 800),
        )
        audit_3 = await runner.execute(workflow)
        assert audit_3.execution_summary.final_status == "SUCCESS", (
            "Runner safety guard reset must permit execution without spurious abort"
        )
        assert len(audit_3.step_events) == 21
```

---

### Action 4.5: Add Dedicated Unit Tests in `tests/test_engine.py`

Add 3 unit tests in `tests/test_engine.py` to lock down regression prevention:

1. `test_safety_guard_reset`:
   ```python
   def test_safety_guard_reset(mock_driver):
       guard = SafetyGuard(driver=mock_driver)
       guard._abort_requested = True
       guard._last_cursor_pos = (500, 500)
       guard._active_target_hwnd = 1234
       guard.reset()
       assert guard._abort_requested is False
       assert guard._last_cursor_pos is None
       assert guard._active_target_hwnd is None
   ```
2. `test_audit_logger_reset`:
   ```python
   def test_audit_logger_reset():
       class DummyWorkflow:
           id = "wf-1"
           name = "WF1"
           target_application = type("Target", (), {"window_title_pattern": "App1", "process_name": "app.exe"})()
           steps = []

       class DummyWorkflow2:
           id = "wf-2"
           name = "WF2"
           target_application = type("Target", (), {"window_title_pattern": "App2", "process_name": "app2.exe"})()
           steps = []

       logger = AuditLogger(execution_id="id-1", workflow=DummyWorkflow())
       logger.record_success(1, "click", "btn", "coords", 5.0)
       assert len(logger.step_events) == 1

       logger.reset(execution_id="id-2", workflow=DummyWorkflow2())
       assert logger.execution_id == "id-2"
       assert len(logger.step_events) == 0
       assert logger._target_app_info.title == "App2"
   ```
3. `test_variable_interpolation_whitespace_padding`:
   ```python
   def test_variable_interpolation_whitespace_padding(mock_driver):
       runner = WorkflowRunner(driver=mock_driver)
       text = "Name: {{ user_name }}, Age: {{age}}, Role: {{   role   }}, Missing: {{ unknown }}"
       vars = {"user_name": "Alice", "age": 30, "role": "Engineer"}
       res = runner._interpolate_variables(text, vars)
       assert res == "Name: Alice, Age: 30, Role: Engineer, Missing: {{ unknown }}"
   ```

---

## 5. Verification Method

Once the implementer applies the changes above, verify independently using:

1. **Verify `VULN-M5-01` Fix & Lifecycle Concurrency**:
   ```powershell
   python -m pytest tests/test_m5_adversarial_challenge.py -k test_07_vulnerability_consecutive_success_executions_cursor_leakage -v
   ```
   *Expected*: PASSED (Run 2 completes with `SUCCESS` and status `COMPLETED`).

2. **Verify Audit Logger Isolation & Multi-Run Reuse**:
   ```powershell
   python -m pytest tests/test_m5_adversarial_empirical.py -k test_03_runner_instance_reuse_state_pollution_demonstration -v
   ```
   *Expected*: PASSED (Run 2 records exactly 21 events; Run 3 completes with `SUCCESS` and 21 events).

3. **Verify Variable Template Whitespace Interpolation**:
   ```powershell
   python -c "import sys; sys.path.insert(0, 'src'); from kutomoto.engine.runner import WorkflowRunner; from kutomoto.engine.safety import MockWin32Driver; r = WorkflowRunner(MockWin32Driver()); assert r._interpolate_variables('Hello {{ user_name }}', {'user_name': 'Alice'}) == 'Hello Alice'; print('Variable interpolation whitespace verified!')"
   ```

4. **Verify Full E2E & Challenge Test Suites**:
   ```powershell
   python -m pytest tests/test_e2e_automation.py -v
   python -m pytest tests/test_m5_adversarial_challenge.py -v
   python -m pytest tests/test_m5_adversarial_empirical.py -v
   ```
   *Expected*: All tests pass with 0 failures.

5. **Code Quality, Formatting, and Zero Bare Passes**:
   ```powershell
   python -m ruff check src/ tests/ samples/
   python -c "import ast, glob; files = glob.glob('tests/*.py') + glob.glob('src/**/*.py', recursive=True); [print(f, count) for f in files if (count := sum(isinstance(n, ast.Pass) for n in ast.walk(ast.parse(open(f, encoding='utf-8').read())))) > 0]"
   ```
   *Expected*: 0 ruff errors, 0 bare pass statements.
