"""
tests.test_engine_empirical_challenge
Empirical stress-testing and adversarial challenge suite for WorkflowRunner,
ExecutionFSM, Action Handlers, Recovery Policies, and Audit Logging.
Copyrights reserved to 90Studio
"""

import asyncio
from pathlib import Path
import sys
import time
import pytest

SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from kutomoto.engine import (  # noqa: E402
    ActionType,
    AuditLogger,
    CredentialMasker,
    ErrorRecoveryPolicy,
    ExecutionFSM,
    ExecutionSettings,
    ExecutionState,
    FSMEvent,
    KutomotoWorkflow,
    MockWin32Driver,
    StepParameters,
    TargetApplication,
    VariableType,
    WorkflowRunner,
    WorkflowStep,
    WorkflowVariable,
)


@pytest.fixture
def mock_driver():
    driver = MockWin32Driver()
    driver.reset()
    return driver


# ==============================================================================
# Challenge 1: Deep Step Chains & Scalability Stress
# ==============================================================================

class TestDeepStepChains:

    @pytest.mark.asyncio
    async def test_deep_step_chain_1000_steps(self, mock_driver, monkeypatch):
        """Stress-test deep workflow chain containing 1,000 steps."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        steps = [
            WorkflowStep(
                sequence_index=i,
                label=f"Step #{i}",
                action_type=ActionType.KEY_PRESS,
                parameters=StepParameters(key="tab", repeat_count=1),
            )
            for i in range(1, 1001)
        ]

        workflow = KutomotoWorkflow(
            name="Deep Chain 1000 Steps",
            target_application=TargetApplication(
                type="windows_desktop",
                window_title_pattern=".*Banking KYC.*",
            ),
            execution_settings=ExecutionSettings(
                countdown_seconds=0,
                default_step_delay_ms=10,
            ),
            steps=steps,
        )

        runner = WorkflowRunner(driver=mock_driver)
        t0 = time.perf_counter()
        audit = await runner.execute(workflow)
        elapsed = time.perf_counter() - t0

        assert audit.execution_summary.final_status == "SUCCESS"
        assert audit.execution_summary.total_steps == 1000
        assert audit.execution_summary.successful_steps == 1000
        assert len(mock_driver.key_presses) == 1000
        assert runner.state == ExecutionState.COMPLETED
        # Must execute within reasonable SLA (< 2.0s for 1000 mocked steps)
        assert elapsed < 2.0


# ==============================================================================
# Challenge 2: Variable Interpolation & Runtime Binding Defects
# ==============================================================================

class TestVariableAdversarial:

    @pytest.mark.asyncio
    async def test_vulnerability_zero_and_falsy_required_variables_rejected(self, mock_driver, monkeypatch):
        """
        EMPIRICAL VULNERABILITY REPRODUCTION:
        WorkflowRunner.execute blocks valid numeric 0 or boolean False for required variables
        because it evaluates `not ctx.variables.get(v.name)` instead of checking for None or empty string.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        workflow = KutomotoWorkflow(
            name="Zero Variable Test",
            target_application=TargetApplication(
                type="windows_desktop",
                window_title_pattern=".*Banking KYC.*",
            ),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            variables=[
                WorkflowVariable(name="retry_count", default_value="0", required=True, type=VariableType.NUMBER),
            ],
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text="Count: {{retry_count}}"),
                ),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver)

        audit = await runner.execute(workflow, runtime_variables={"retry_count": 0})
        assert audit.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED
        assert "Count: 0" in mock_driver.typed_text

    def test_variable_interpolation_edge_cases(self, mock_driver):
        """Tests unescaped braces, missing keys, special chars, and nested structures."""
        runner = WorkflowRunner(driver=mock_driver)

        # 1. Missing variable leaves placeholder unchanged
        res1 = runner._interpolate_variables("Hello {{unknown_var}}", {})
        assert res1 == "Hello {{unknown_var}}"

        # 2. Malformed tokens are not matched as variables
        res2 = runner._interpolate_variables("Values: {{}} and {{123bad}}", {})
        assert res2 == "Values: {{}} and {{123bad}}"

        # 3. Unicode and special characters inside bound variable value
        res3 = runner._interpolate_variables("Message: {{msg}}", {"msg": "مرحبا / Привет 🚀 <>&'\""})
        assert res3 == "Message: مرحبا / Привет 🚀 <>&'\""

        # 4. Billion laughs / recursive template is single-pass safe
        res4 = runner._interpolate_variables("Deep: {{a}}", {"a": "{{b}}", "b": "BOOM"})
        assert res4 == "Deep: {{b}}"  # Not recursively expanded to BOOM


# ==============================================================================
# Challenge 3: Rapid State Transitions, Pause, Resume, Abort Vulnerabilities
# ==============================================================================

class TestFSMTransitionsAdversarial:

    @pytest.mark.asyncio
    async def test_vulnerability_user_pause_does_not_pause_and_crashes_fsm(self, mock_driver, monkeypatch):
        """
        EMPIRICAL VULNERABILITY REPRODUCTION:
        Calling `await runner.pause()` while running does not pause the execution loop.
        The loop continues, executes the next step, and attempts `trigger(FSMEvent.STEP_SUCCESS)`
        from state `PAUSED`, which crashes with `InvalidTransitionError`.
        """
        monkeypatch.delenv("KUTOMOTO_TEST_FAST", raising=False)

        workflow = KutomotoWorkflow(
            name="Pause Crash Reproduction",
            target_application=TargetApplication(
                type="windows_desktop",
                window_title_pattern=".*Banking KYC.*",
            ),
            execution_settings=ExecutionSettings(countdown_seconds=0, default_step_delay_ms=20),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.FOCUS_WINDOW,
                    parameters=StepParameters(window_title_pattern=".*Banking KYC.*"),
                ),
                WorkflowStep(
                    sequence_index=2,
                    action_type=ActionType.DELAY,
                    parameters=StepParameters(duration_ms=60),
                ),
                WorkflowStep(
                    sequence_index=3,
                    action_type=ActionType.KEY_PRESS,
                    parameters=StepParameters(key="tab"),
                ),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver)
        task = asyncio.create_task(runner.execute(workflow))

        # Give small tick to enter RUNNING during DELAY step
        await asyncio.sleep(0.01)
        assert runner.state == ExecutionState.RUNNING

        # Trigger user pause
        await runner.pause()
        assert runner.state == ExecutionState.PAUSED
        await asyncio.sleep(0.05)
        assert runner.state == ExecutionState.PAUSED
        assert len(mock_driver.key_presses) == 0

        await runner.resume()
        assert runner.state == ExecutionState.RUNNING
        audit = await task
        assert audit.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED
        assert len(mock_driver.key_presses) == 1

    @pytest.mark.asyncio
    async def test_vulnerability_abort_while_paused_crashes_with_cleanup_done(self, mock_driver, monkeypatch):
        """
        EMPIRICAL VULNERABILITY REPRODUCTION:
        When a workflow is in `PAUSED` state and `await runner.abort()` is called,
        `ABORT_TRIGGERED` transitions to `STOPPED` (T14).
        Line 449 of runner.py then calls `trigger(FSMEvent.CLEANUP_DONE)`, which is invalid
        from state `STOPPED` and crashes with `InvalidTransitionError`.
        """
        runner = WorkflowRunner(driver=mock_driver)
        from kutomoto.engine.runner import ExecutionContext
        ctx = ExecutionContext(workflow=None, execution_id="test")  # type: ignore
        ctx.pause_event.clear()
        runner._ctx = ctx
        await runner._fsm.trigger(FSMEvent.EXECUTE_START)
        await runner._fsm.trigger(FSMEvent.VALIDATION_OK)
        await runner._fsm.trigger(FSMEvent.COUNTDOWN_DONE)
        await runner._fsm.trigger(FSMEvent.USER_PAUSE)
        assert runner.state == ExecutionState.PAUSED

        await runner.abort()
        assert runner.state == ExecutionState.STOPPED

    @pytest.mark.asyncio
    async def test_vulnerability_resume_without_target_hwnd_leaves_event_cleared(self, mock_driver):
        """
        EMPIRICAL VULNERABILITY REPRODUCTION:
        In `runner.resume()`, `self._ctx.pause_event.set()` is guarded by:
        `if self._ctx and self._ctx.target_hwnd:`.
        If `target_hwnd` is None, `pause_event.set()` is never called.
        """
        runner = WorkflowRunner(driver=mock_driver)
        await runner._fsm.trigger(FSMEvent.EXECUTE_START)
        await runner._fsm.trigger(FSMEvent.VALIDATION_OK)
        await runner._fsm.trigger(FSMEvent.COUNTDOWN_DONE)
        await runner._fsm.trigger(FSMEvent.USER_PAUSE)
        assert runner.state == ExecutionState.PAUSED

        from kutomoto.engine.runner import ExecutionContext
        ctx = ExecutionContext(
            workflow=None,  # type: ignore
            execution_id="test",
            target_hwnd=None,  # No hwnd
        )
        ctx.pause_event.clear()
        runner._ctx = ctx

        await runner.resume()
        assert runner.state == ExecutionState.RUNNING
        assert ctx.pause_event.is_set()


# ==============================================================================
# Challenge 4: All 4 Recovery Policies Stress Simulation
# ==============================================================================

class TestRecoveryPoliciesAdversarial:

    @pytest.mark.asyncio
    async def test_policy_abort_terminates_immediately(self, mock_driver, monkeypatch):
        """Policy ABORT: step failure triggers POLICY_ABORT (T17) and returns FAILED audit."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        workflow = KutomotoWorkflow(
            name="Policy ABORT Test",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(
                countdown_seconds=0,
                error_recovery_policy=ErrorRecoveryPolicy.ABORT,
            ),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.CLICK,
                    parameters=StepParameters(x=10, y=10, coordinate_mode="screen"),
                ),
            ],
        )

        mock_driver.send_click = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Fatal Click Failure"))

        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "FAILED"
        assert audit.execution_summary.failed_steps == 1
        assert runner.state == ExecutionState.ERROR

    @pytest.mark.asyncio
    async def test_policy_retry_exhaustion_terminates_in_error(self, mock_driver, monkeypatch):
        """Policy RETRY_STEP: exhausts retries and transitions to ERROR."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        workflow = KutomotoWorkflow(
            name="Policy RETRY Exhaustion Test",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(
                countdown_seconds=0,
                error_recovery_policy=ErrorRecoveryPolicy.RETRY_STEP,
                max_step_retries=3,
            ),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.KEY_PRESS,
                    parameters=StepParameters(key="enter"),
                ),
            ],
        )

        attempts = 0

        def always_fails(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            raise RuntimeError(f"Failure attempt {attempts}")

        mock_driver.send_key_press = always_fails

        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        # 1 initial attempt + 3 retries = 4 total attempts
        assert attempts == 4
        assert audit.execution_summary.final_status == "FAILED"
        assert audit.execution_summary.retried_steps == 3
        assert audit.execution_summary.failed_steps == 1
        assert runner.state == ExecutionState.ERROR

    @pytest.mark.asyncio
    async def test_policy_skip_continues_subsequent_steps(self, mock_driver, monkeypatch):
        """Policy SKIP_STEP: records skipped step and continues to next step."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        workflow = KutomotoWorkflow(
            name="Policy SKIP Test",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(
                countdown_seconds=0,
                error_recovery_policy=ErrorRecoveryPolicy.SKIP_STEP,
            ),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.CLICK,
                    parameters=StepParameters(x=10, y=10, coordinate_mode="screen"),
                ),
                WorkflowStep(
                    sequence_index=2,
                    action_type=ActionType.KEY_PRESS,
                    parameters=StepParameters(key="tab"),
                ),
            ],
        )

        mock_driver.send_click = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Click Skipped"))

        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert audit.execution_summary.successful_steps == 1
        assert len(mock_driver.key_presses) == 1
        assert runner.state == ExecutionState.COMPLETED

    @pytest.mark.asyncio
    async def test_vulnerability_policy_prompt_user_unhandled_and_aborts(self, mock_driver, monkeypatch):
        """
        EMPIRICAL VULNERABILITY REPRODUCTION:
        Policy PROMPT_USER has no handler in runner.py line 532.
        It falls into `else: # ABORT` without emitting any prompt event or querying prompt_resolver.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        workflow = KutomotoWorkflow(
            name="Policy PROMPT_USER Test",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(
                countdown_seconds=0,
                error_recovery_policy=ErrorRecoveryPolicy.PROMPT_USER,
            ),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.CLICK,
                    parameters=StepParameters(x=10, y=10, coordinate_mode="screen"),
                ),
            ],
        )

        telemetry_events = []
        runner = WorkflowRunner(
            driver=mock_driver,
            telemetry_callback=lambda evt, payload: telemetry_events.append(evt),
        )

        mock_driver.send_click = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Click Failed Under PROMPT"))
        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "FAILED"
        assert runner.state == ExecutionState.ERROR
        assert "user_prompt_requested" in telemetry_events


# ==============================================================================
# Challenge 5: Concurrent Listeners, Telemetry & High-Throughput Audit
# ==============================================================================

class TestConcurrencyAndAuditThroughput:

    @pytest.mark.asyncio
    async def test_concurrent_listeners_stress(self):
        """Stress-tests 50 concurrent sync and async listeners on ExecutionFSM."""
        fsm = ExecutionFSM()
        sync_counts = [0] * 25
        async_counts = [0] * 25

        def make_sync(i):
            def cb(old, new, evt):
                sync_counts[i] += 1
            return cb

        def make_async(i):
            async def cb(old, new, evt):
                await asyncio.sleep(0.001)
                async_counts[i] += 1
            return cb

        for i in range(25):
            fsm.add_listener(make_sync(i))
            fsm.add_listener(make_async(i))

        # Perform valid transition sequence
        await fsm.trigger(FSMEvent.EXECUTE_START)
        await fsm.trigger(FSMEvent.VALIDATION_OK)
        await fsm.trigger(FSMEvent.COUNTDOWN_DONE)
        await fsm.trigger(FSMEvent.ALL_STEPS_DONE)

        assert fsm.state == ExecutionState.COMPLETED
        assert all(c == 4 for c in sync_counts)
        assert all(c == 4 for c in async_counts)

    @pytest.mark.asyncio
    async def test_telemetry_resilience_to_listener_exceptions(self, mock_driver, monkeypatch):
        """Ensures runner does not crash if telemetry callback throws exceptions."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        def explosive_telemetry(evt, payload):
            raise RuntimeError(f"Telemetry boom on {evt}")

        workflow = KutomotoWorkflow(
            name="Telemetry Exception Test",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.KEY_PRESS,
                    parameters=StepParameters(key="tab"),
                ),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver, telemetry_callback=explosive_telemetry)
        # Execution must complete successfully despite failing telemetry
        audit = await runner.execute(workflow)
        assert audit.execution_summary.final_status == "SUCCESS"

    def test_audit_masking_high_throughput_10000_events(self):
        """Verifies CredentialMasker and AuditLogger throughput and secret masking on 10,000 events."""
        class DummyWorkflow:
            id = "stress-wf-10k"
            name = "High Volume Audit Test"
            source_mode = "manual_step_flow"
            target_application = type("T", (), {"window_title_pattern": "App", "process_name": "app.exe"})()
            steps = list(range(10000))

        logger = AuditLogger("exec-10k", DummyWorkflow())

        t0 = time.perf_counter()
        for i in range(1, 10001):
            is_secret = (i % 3 == 0)
            p = StepParameters(text=f"PasswordPayload_{i}", is_secret=is_secret)
            summary = CredentialMasker.mask_parameter_summary("type_text", p, is_secret=is_secret)
            if is_secret:
                assert "********" in summary
                assert f"PasswordPayload_{i}" not in summary
            logger.record_success(i, "type_text", f"Step {i}", summary, 0.5)

        log = logger.generate_log("SUCCESS")
        elapsed = time.perf_counter() - t0

        assert log.copyright == "Copyrights reserved to 90Studio"
        assert log.execution_summary.successful_steps == 10000
        assert len(log.step_events) == 10000
        # 10k events processed and validated in < 1.0s
        assert elapsed < 1.0
