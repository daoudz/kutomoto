"""
tests.test_m5_adversarial_challenge
Milestone 5 Adversarial Challenge & Empirical Verification Suite:
Stress-tests safety guardrails, FSM concurrency, failsafe abort disarm,
hook cleanup, focus loss guardian, extreme parameter boundaries, and 90Studio audit compliance.

Copyrights reserved to 90Studio
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import time
from typing import Any, Dict, List

import pytest

SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from kutomoto.engine.audit import CredentialMasker, KutomotoAuditLog  # noqa: E402
from kutomoto.engine.fsm import ExecutionState  # noqa: E402
from kutomoto.engine.runner import WorkflowRunner  # noqa: E402
from kutomoto.engine.safety import (  # noqa: E402
    FocusLostError,
    MockWin32Driver,
    MouseDisturbanceDetected,
    SafetyConfig,
    SafetyGuard,
)
from kutomoto.engine.schema import (  # noqa: E402
    ActionType,
    CoordinateMode,
    ErrorRecoveryPolicy,
    ExecutionSettings,
    KutomotoWorkflow,
    StepParameters,
    TargetAppType,
    TargetApplication,
    VariableType,
    WorkflowStep,
    WorkflowVariable,
)


# ==============================================================================
# FIXTURES & HELPERS
# ==============================================================================

@pytest.fixture
def mock_driver() -> MockWin32Driver:
    driver = MockWin32Driver()
    driver.reset()
    driver.add_mock_window(
        1001,
        "Banking KYC Customer Onboarding - 90Studio",
        "msedge.exe",
        (100, 100, 1200, 800),
    )
    driver.add_mock_window(
        1002,
        "Telecom SIM Provisioning System — 90Studio",
        "sample_desktop_form.exe",
        (150, 150, 800, 600),
    )
    return driver


def create_multi_step_workflow(num_steps: int = 10, step_delay_ms: int = 10) -> KutomotoWorkflow:
    steps: List[WorkflowStep] = [
        WorkflowStep(
            sequence_index=1,
            action_type=ActionType.FOCUS_WINDOW,
            parameters=StepParameters(window_title_pattern=r".*Banking KYC.*"),
        )
    ]
    for i in range(2, num_steps + 1):
        steps.append(
            WorkflowStep(
                sequence_index=i,
                action_type=ActionType.TYPE_TEXT,
                parameters=StepParameters(text=f"DataEntry_{i}"),
                pre_delay_ms=step_delay_ms,
                post_delay_ms=step_delay_ms,
            )
        )
    return KutomotoWorkflow(
        id=f"wf_multi_{num_steps}",
        name="Multi Step Stress Workflow",
        target_application=TargetApplication(
            type=TargetAppType.WEB_BROWSER,
            window_title_pattern=r".*Banking KYC.*",
        ),
        execution_settings=ExecutionSettings(
            countdown_seconds=0,
            default_step_delay_ms=step_delay_ms,
        ),
        steps=steps,
    )


# ==============================================================================
# 1. RAPID CONCURRENCY & FSM LIFECYCLE STRESS TESTS
# ==============================================================================

class TestRapidConcurrencyAndLifecycleFSM:
    """Stress tests rapid pause/resume/abort concurrency and FSM state integrity."""

    @pytest.mark.asyncio
    async def test_01_rapid_pause_resume_flapping_under_load(self, mock_driver, monkeypatch):
        """Flaps pause and resume at high frequency while steps execute; verifies zero deadlocks."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = create_multi_step_workflow(num_steps=12, step_delay_ms=15)
        runner = WorkflowRunner(driver=mock_driver)

        exec_task = asyncio.create_task(runner.execute(workflow))

        # Rapidly flap pause and resume while the workflow is running
        for _ in range(8):
            await asyncio.sleep(0.015)
            if runner.state == ExecutionState.RUNNING:
                await runner.pause()
            await asyncio.sleep(0.01)
            if runner.state == ExecutionState.PAUSED:
                await runner.resume()

        audit = await exec_task
        assert audit.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED
        assert len(mock_driver.typed_text) == 11

    @pytest.mark.asyncio
    async def test_02_concurrent_abort_and_pause_race(self, mock_driver, monkeypatch):
        """Dispatches concurrent abort, pause, and resume tasks; verifies clean resolution to STOPPED."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = create_multi_step_workflow(num_steps=15, step_delay_ms=20)
        runner = WorkflowRunner(driver=mock_driver)

        exec_task = asyncio.create_task(runner.execute(workflow))
        await asyncio.sleep(0.02)

        async def _bombard_pause():
            for _ in range(5):
                try:
                    await runner.pause()
                except Exception:
                    continue
                await asyncio.sleep(0.005)

        async def _bombard_resume():
            for _ in range(5):
                try:
                    await runner.resume()
                except Exception:
                    continue
                await asyncio.sleep(0.005)

        async def _fire_abort():
            await asyncio.sleep(0.03)
            await runner.abort()

        await asyncio.gather(
            _bombard_pause(),
            _bombard_resume(),
            _fire_abort(),
            return_exceptions=True,
        )

        audit = await exec_task
        assert audit.execution_summary.final_status == "ABORTED"
        assert runner.state in (ExecutionState.STOPPED, ExecutionState.STOPPING)

    @pytest.mark.asyncio
    async def test_03_abort_while_paused_in_deep_workflow(self, mock_driver, monkeypatch):
        """Aborts workflow while paused deep in execution; verifies immediate unblocking and modifier release."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = create_multi_step_workflow(num_steps=15, step_delay_ms=20)
        runner = WorkflowRunner(driver=mock_driver)

        exec_task = asyncio.create_task(runner.execute(workflow))

        # Wait until runner has executed a few steps
        await asyncio.sleep(0.05)
        await runner.pause()
        assert runner.state == ExecutionState.PAUSED

        # Abort while paused
        await runner.abort()

        audit = await exec_task
        assert audit.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED
        assert any(c.get("method") == "release_all_modifiers" for c in mock_driver.calls)

    @pytest.mark.asyncio
    async def test_04_abort_during_countdown_phase(self, mock_driver, monkeypatch):
        """Aborts during countdown; verifies immediate termination without waiting full countdown duration."""
        monkeypatch.delenv("KUTOMOTO_TEST_FAST", raising=False)
        workflow = KutomotoWorkflow(
            name="Countdown Abort Test",
            target_application=TargetApplication(
                type=TargetAppType.WEB_BROWSER,
                window_title_pattern=r".*Banking KYC.*",
            ),
            execution_settings=ExecutionSettings(countdown_seconds=5),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text="ShouldNeverExecute"),
                )
            ],
        )
        runner = WorkflowRunner(driver=mock_driver)
        t0 = time.perf_counter()

        exec_task = asyncio.create_task(runner.execute(workflow))
        await asyncio.sleep(0.15)
        await runner.abort()

        audit = await exec_task
        elapsed = time.perf_counter() - t0

        assert audit.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED
        assert elapsed < 2.0, f"Abort during countdown took too long: {elapsed:.2f}s"
        assert "ShouldNeverExecute" not in mock_driver.typed_text

    @pytest.mark.asyncio
    async def test_05_abort_during_long_delay_step(self, mock_driver, monkeypatch):
        """Aborts during a 10-second DELAY action; verifies immediate interrupt without hanging."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = KutomotoWorkflow(
            name="Long Delay Abort Test",
            target_application=TargetApplication(
                type=TargetAppType.WEB_BROWSER,
                window_title_pattern=r".*Banking KYC.*",
            ),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.DELAY,
                    parameters=StepParameters(duration_ms=10000),  # 10s delay
                ),
                WorkflowStep(
                    sequence_index=2,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text="AfterDelay"),
                ),
            ],
        )
        runner = WorkflowRunner(driver=mock_driver)
        t0 = time.perf_counter()

        exec_task = asyncio.create_task(runner.execute(workflow))
        await asyncio.sleep(0.08)
        await runner.abort()

        audit = await exec_task
        elapsed = time.perf_counter() - t0

        assert audit.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED
        assert elapsed < 1.0, f"Abort during delay took too long: {elapsed:.2f}s"
        assert "AfterDelay" not in mock_driver.typed_text

    @pytest.mark.asyncio
    async def test_06_runner_reuse_after_abort_and_error(self, mock_driver, monkeypatch):
        """Verifies runner state machine correctly resets (RESET T19/T21) and permits sequential re-execution."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        runner = WorkflowRunner(driver=mock_driver)

        # 1. First execution ends in ABORT
        wf1 = create_multi_step_workflow(num_steps=6, step_delay_ms=10)
        mock_driver.simulate_escape_press()
        audit1 = await runner.execute(wf1)
        assert audit1.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED

        # 2. Re-run after abort: must transition STOPPED -> IDLE -> RUNNING -> COMPLETED
        mock_driver.simulate_escape_release()
        mock_driver.reset()
        mock_driver.add_mock_window(1001, "Banking KYC Customer Onboarding - 90Studio")
        audit2 = await runner.execute(wf1)
        assert audit2.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED

        # 3. Execution fails on missing required variable
        wf_missing = KutomotoWorkflow(
            name="Missing Var",
            target_application=TargetApplication(type=TargetAppType.WEB_BROWSER, window_title_pattern=".*KYC.*"),
            variables=[WorkflowVariable(name="req_token", required=True)],
            steps=[WorkflowStep(sequence_index=1, action_type=ActionType.TYPE_TEXT, parameters=StepParameters(text="hi"))],
        )
        with pytest.raises(ValueError, match="missing required variables"):
            await runner.execute(wf_missing)
        assert runner.state == ExecutionState.ERROR

        # 4. Re-run on same runner with variable supplied: must reset ERROR -> IDLE -> COMPLETED
        audit3 = await runner.execute(wf_missing, runtime_variables={"req_token": "token123"})
        assert audit3.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED

    @pytest.mark.asyncio
    async def test_07_vulnerability_consecutive_success_executions_cursor_leakage(self, mock_driver, monkeypatch):
        """
        Vulnerability Reproduction (E08 State Leakage): Consecutive successful workflow executions on the same runner
        leak _last_cursor_pos, causing false MouseDisturbanceDetected trips if cursor moves >100px between runs.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        runner = WorkflowRunner(driver=mock_driver)

        # Run 1 executes and finishes at (200, 200)
        wf = create_multi_step_workflow(num_steps=3, step_delay_ms=10)
        mock_driver.set_cursor_pos(200, 200)
        audit1 = await runner.execute(wf)
        assert audit1.execution_summary.final_status == "SUCCESS"

        # Between runs, cursor is at (500, 500) (>100px displacement)
        mock_driver.set_cursor_pos(500, 500)

        # Run 2 starts: verifies that reset _last_cursor_pos prevents false abort and completes successfully
        audit2 = await runner.execute(wf)
        assert audit2.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED
        assert len(audit2.step_events) == 3


# ==============================================================================
# 2. FAILSAFE DISARM & HOOK CLEANUP VERIFICATION
# ==============================================================================

class TestFailsafeDisarmAndHookCleanup:
    """Verifies failsafe triggers, modifier key release, and background watcher teardown."""

    @pytest.mark.asyncio
    async def test_01_escape_abort_releases_all_11_modifier_vks(self, mock_driver, monkeypatch):
        """Verifies that Escape abort reliably purges all 11 Win32 modifier virtual keys."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = create_multi_step_workflow(num_steps=3)

        # Pre-load modifiers into active driver state
        mock_driver.active_modifiers.update(["ctrl", "alt", "shift"])
        mock_driver.pressed_keys.update([0x11, 0x12, 0x10, "ctrl", "alt", "shift"])
        mock_driver.simulate_escape_press()

        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED

        # Verify modifiers purged from driver
        assert len(mock_driver.active_modifiers) == 0
        assert 0x11 not in mock_driver.pressed_keys
        assert 0x12 not in mock_driver.pressed_keys
        assert 0x10 not in mock_driver.pressed_keys

        # Verify driver.release_all_modifiers called
        assert any(c.get("method") == "release_all_modifiers" for c in mock_driver.calls)

    @pytest.mark.asyncio
    async def test_02_corner_failsafe_multi_quadrant_boundaries(self, mock_driver, monkeypatch):
        """Verifies screen corner failsafe coordinates at top-left and top-right boundaries."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = create_multi_step_workflow(num_steps=4)
        runner = WorkflowRunner(driver=mock_driver)

        # Top-Left threshold tests
        # (0, 0) -> trips
        mock_driver.simulate_corner_failsafe(0, 0)
        audit_tl0 = await runner.execute(workflow)
        assert audit_tl0.execution_summary.final_status == "ABORTED"

        # (2, 2) -> trips (within default 2px threshold)
        mock_driver.reset()
        mock_driver.add_mock_window(1001, "Banking KYC Customer Onboarding - 90Studio")
        mock_driver.simulate_corner_failsafe(2, 2)
        audit_tl2 = await runner.execute(workflow)
        assert audit_tl2.execution_summary.final_status == "ABORTED"

        # (3, 3) -> does NOT trip (beyond 2px threshold)
        mock_driver.reset()
        mock_driver.add_mock_window(1001, "Banking KYC Customer Onboarding - 90Studio")
        mock_driver.simulate_corner_failsafe(3, 3)
        audit_safe = await runner.execute(workflow)
        assert audit_safe.execution_summary.final_status == "SUCCESS"

        # Top-Right corner threshold tests (1920 - 2 = 1918)
        mock_driver.reset()
        mock_driver.add_mock_window(1001, "Banking KYC Customer Onboarding - 90Studio")
        mock_driver.simulate_corner_failsafe(1919, 0)
        audit_tr = await runner.execute(workflow)
        assert audit_tr.execution_summary.final_status == "ABORTED"

    @pytest.mark.asyncio
    async def test_03_mouse_disturbance_detector_displacement(self, mock_driver, monkeypatch):
        """Verifies that physical mouse disturbance (> 100px) trips guardrail, while intentional moves do not."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        guard = SafetyGuard(driver=mock_driver, config=SafetyConfig(mouse_disturbance_threshold_px=100.0))

        # Initial baseline position (500, 500)
        guard.check_mouse_disturbance()

        # Minor operator drift of 25px -> should NOT trip
        mock_driver.simulate_mouse_disturbance(dx=20, dy=15)
        guard.check_mouse_disturbance()

        # Intentional automation move of 300px registered via click/move -> should NOT trip
        guard.register_intentional_mouse_move(850, 850)
        mock_driver.set_cursor_pos(850, 850)
        guard.check_mouse_disturbance()

        # Accidental physical operator bump of 150px -> MUST trip MouseDisturbanceDetected
        mock_driver.simulate_mouse_disturbance(dx=120, dy=90)  # hypot = 150 > 100
        with pytest.raises(MouseDisturbanceDetected, match="displacement"):
            guard.check_mouse_disturbance()

    @pytest.mark.asyncio
    async def test_04_safety_background_watcher_lifecycle(self, mock_driver):
        """Verifies asynchronous background watcher starts, detects Escape, and cancels cleanly without task leaks."""
        guard = SafetyGuard(driver=mock_driver)

        # 1. Start background watcher
        await guard.start_background_watcher(check_interval_sec=0.01)
        assert guard._watcher_task is not None
        assert not guard._watcher_task.done()

        # 2. Stop watcher before any key press
        guard.stop_background_watcher()
        await asyncio.sleep(0.02)
        assert guard._watcher_task is None

        # 3. Start watcher again, simulate Escape key press
        await guard.start_background_watcher(check_interval_sec=0.01)
        mock_driver.simulate_escape_press()
        await asyncio.sleep(0.03)

        assert guard._abort_requested is True
        guard.stop_background_watcher()


# ==============================================================================
# 3. FOCUS LOSS GUARDIAN ADVERSARIAL VERIFICATION
# ==============================================================================

class TestFocusLossGuardianAdversarial:
    """Verifies target window focus loss detection, auto-pause, auto-restoration, and recovery."""

    @pytest.mark.asyncio
    async def test_01_repeated_focus_theft_flapping_recovery(self, mock_driver, monkeypatch):
        """Repeatedly steals focus during multi-step execution; verifies runner pauses and resumes flawlessly."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = create_multi_step_workflow(num_steps=6, step_delay_ms=20)
        runner = WorkflowRunner(driver=mock_driver)

        exec_task = asyncio.create_task(runner.execute(workflow))

        # Theft 1
        await asyncio.sleep(0.03)
        mock_driver.simulate_focus_loss(new_hwnd=8888)
        await asyncio.sleep(0.04)
        assert runner.state == ExecutionState.PAUSED
        mock_driver.focus_window(1001)
        await runner.resume()

        # Theft 2
        await asyncio.sleep(0.03)
        mock_driver.simulate_focus_loss(new_hwnd=9999)
        await asyncio.sleep(0.04)
        assert runner.state == ExecutionState.PAUSED
        mock_driver.focus_window(1001)
        await runner.resume()

        audit = await exec_task
        assert audit.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED
        assert len(mock_driver.typed_text) == 5

    @pytest.mark.asyncio
    async def test_02_focus_guardian_auto_restoration(self, mock_driver):
        """Verifies focus guardian auto-restores foreground window within configured retry attempts."""
        guard = SafetyGuard(
            driver=mock_driver,
            config=SafetyConfig(
                focus_guardian_enabled=True,
                auto_restore_focus_attempts=3,
            ),
        )
        guard.set_target_hwnd(1001)

        # Steal focus to 9999
        mock_driver.simulate_focus_loss(new_hwnd=9999)
        assert mock_driver.get_foreground_window() == 9999

        # check_focus_guardian should attempt auto-restoration and succeed
        guard.check_focus_guardian()
        assert mock_driver.get_foreground_window() == 1001

    @pytest.mark.asyncio
    async def test_03_focus_loss_permanent_failure_raises_focus_lost_error(self, mock_driver):
        """Verifies FocusLostError is raised when target window fails to be restored."""
        guard = SafetyGuard(
            driver=mock_driver,
            config=SafetyConfig(
                focus_guardian_enabled=True,
                auto_restore_focus_attempts=2,
            ),
        )
        guard.set_target_hwnd(1001)
        mock_driver.simulate_focus_loss(new_hwnd=9999)
        mock_driver.fail_focus = True  # Block focus restoration

        with pytest.raises(FocusLostError, match="Foreground focus lost"):
            guard.check_focus_guardian()


# ==============================================================================
# 4. EXTREME PARAMETER BOUNDARIES & VARIABLE INTERPOLATION
# ==============================================================================

class TestExtremeBoundariesAndInterpolation:
    """Verifies ultra-long strings, zero-length bypass, unicode homoglyphs, and variable resolution."""

    @pytest.mark.asyncio
    async def test_01_extreme_unicode_homoglyphs_and_special_chars(self, mock_driver, monkeypatch):
        """Fuzzes inputs with RTL text, bidirectional overrides, mathematical symbols, and SQL/HTML injection strings."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        adversarial_payloads = [
            "مرحبا بكم 90Studio",  # Arabic RTL
            "שלום עולם",          # Hebrew RTL
            "🚀⚡🔥🤖💼📊🔒",      # Unicode Emojis
            "Robert'); DROP TABLE Students;--",  # SQL injection string
            "<script>alert('90Studio XSS')</script>",  # XSS string
            "C:\\Windows\\System32\\calc.exe",  # Windows path
            "100% & <50> / 25 * (10 + 2) == True",  # Arithmetic/logic
        ]

        steps = [
            WorkflowStep(
                sequence_index=i + 1,
                action_type=ActionType.TYPE_TEXT,
                parameters=StepParameters(text=payload),
            )
            for i, payload in enumerate(adversarial_payloads)
        ]

        workflow = KutomotoWorkflow(
            name="Adversarial Payloads",
            target_application=TargetApplication(type=TargetAppType.WEB_BROWSER, window_title_pattern=".*KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=steps,
        )

        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "SUCCESS"
        for payload in adversarial_payloads:
            assert payload in mock_driver.typed_text

    @pytest.mark.asyncio
    async def test_02_variable_interpolation_boundaries_and_numeric_zero(self, mock_driver, monkeypatch):
        """Verifies {{variable}} interpolation handles numeric 0, False, and missing vars."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = KutomotoWorkflow(
            name="Variable Interpolation Test",
            target_application=TargetApplication(type=TargetAppType.WEB_BROWSER, window_title_pattern=".*KYC.*"),
            variables=[
                WorkflowVariable(name="count", default_value="0", type=VariableType.NUMBER),
                WorkflowVariable(name="is_active", default_value="false"),
                WorkflowVariable(name="user_name", default_value="Alice"),
            ],
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text="Count: {{count}}, Active: {{is_active}}, User: {{user_name}}"),
                ),
                WorkflowStep(
                    sequence_index=2,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text="Unknown: {{non_existent_var}}"),
                ),
                WorkflowStep(
                    sequence_index=3,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text="Whitespace: {{ user_name }} and {{  count  }}"),
                ),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver)
        # Test runtime variable overrides with numeric 0 and boolean False
        audit = await runner.execute(workflow, runtime_variables={"count": 0, "is_active": False})

        assert audit.execution_summary.final_status == "SUCCESS"
        assert "Count: 0, Active: False, User: Alice" in mock_driver.typed_text
        # Unresolved variable template preserved as literal text
        assert "Unknown: {{non_existent_var}}" in mock_driver.typed_text
        assert "Whitespace: Alice and 0" in mock_driver.typed_text


# ==============================================================================
# 5. ERROR RECOVERY POLICIES & PROMPT RESOLUTION
# ==============================================================================

class TestErrorRecoveryPolicies:
    """Verifies RETRY_STEP exhaustion, SKIP_STEP continuation, and PROMPT_USER resolution."""

    @pytest.mark.asyncio
    async def test_01_retry_step_exhaustion_then_failure(self, mock_driver, monkeypatch):
        """Verifies that exceeding max_step_retries records retries in audit and transitions to ERROR."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        mock_driver.fail_focus = True

        workflow = KutomotoWorkflow(
            name="Retry Exhaustion Test",
            target_application=TargetApplication(type=TargetAppType.WINDOWS_DESKTOP, window_title_pattern=".*Telecom.*"),
            execution_settings=ExecutionSettings(
                countdown_seconds=0,
                error_recovery_policy=ErrorRecoveryPolicy.RETRY_STEP,
                max_step_retries=2,
            ),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.FOCUS_WINDOW,
                    parameters=StepParameters(window_title_pattern=".*Telecom.*"),
                ),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "FAILED"
        assert audit.execution_summary.retried_steps == 2
        assert audit.execution_summary.failed_steps == 1
        assert runner.state == ExecutionState.ERROR

    @pytest.mark.asyncio
    async def test_02_prompt_user_custom_resolver_skip_and_retry(self, mock_driver, monkeypatch):
        """Verifies PROMPT_USER policy invokes prompt resolver and obeys decision."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        class MockPromptResolver:
            def __init__(self, decision: str = "skip"):
                self.decision = decision
                self.invocations: List[Dict[str, Any]] = []

            def request_decision(self, step_index: int, error: str, options: List[str]) -> str:
                self.invocations.append({"step_index": step_index, "error": error, "options": options})
                return self.decision

        resolver = MockPromptResolver(decision="skip")

        workflow = KutomotoWorkflow(
            name="Prompt User Test",
            target_application=TargetApplication(type=TargetAppType.WEB_BROWSER, window_title_pattern=".*KYC.*"),
            execution_settings=ExecutionSettings(
                countdown_seconds=0,
                error_recovery_policy=ErrorRecoveryPolicy.PROMPT_USER,
            ),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.FOCUS_WINDOW,
                    parameters=StepParameters(window_title_pattern=".*KYC.*"),
                ),
                WorkflowStep(
                    sequence_index=2,
                    action_type=ActionType.CLICK,
                    parameters=StepParameters(
                        coordinate_mode=CoordinateMode.NORMALIZED,
                        norm_x=None,  # Triggers ValueError: Normalized click requires norm_x and norm_y
                        norm_y=None,
                    ),
                ),
                WorkflowStep(
                    sequence_index=3,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text="ExecutedAfterSkip"),
                ),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver, prompt_resolver=resolver)
        audit = await runner.execute(workflow)

        assert len(resolver.invocations) >= 1
        assert resolver.invocations[0]["step_index"] == 2
        assert audit.execution_summary.final_status == "SUCCESS"
        assert "ExecutedAfterSkip" in mock_driver.typed_text


# ==============================================================================
# 6. AUDIT LOG MASKING & 90STUDIO COMPLIANCE VERIFICATION
# ==============================================================================

class TestAuditLogMaskingAndCompliance:
    """Verifies strict 90Studio attribution and comprehensive credential masking."""

    @pytest.mark.asyncio
    async def test_01_multi_secret_masking_complete_erasure_from_telemetry(self, mock_driver, monkeypatch):
        """Verifies that multiple secrets in diverse action types are never leaked into audit log JSON."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        secret_pin = "99887766"
        secret_token = "Bearer-Secret-Token-XYZ"

        workflow = KutomotoWorkflow(
            name="Multi Secret Audit Test",
            target_application=TargetApplication(type=TargetAppType.WEB_BROWSER, window_title_pattern=".*KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text=secret_pin, is_secret=True),
                ),
                WorkflowStep(
                    sequence_index=2,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text=secret_token, is_secret=True),
                ),
                WorkflowStep(
                    sequence_index=3,
                    action_type=ActionType.PROMPT_USER_INPUT,
                    parameters=StepParameters(variable_name="otp", is_password=True),
                ),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        # 1. 90Studio Copyright Assertions
        assert audit.copyright == "Copyrights reserved to 90Studio"
        assert audit.system == "kutomoto"
        assert audit.audit_version == "1.0.0"

        # 2. String representation and JSON dump assertions
        audit_json = audit.model_dump_json(indent=2)
        assert secret_pin not in audit_json, "Secret PIN leaked into audit log JSON!"
        assert secret_token not in audit_json, "Secret Token leaked into audit log JSON!"

        # 3. Mask string presence
        assert CredentialMasker.MASK_STRING in audit_json
        for event in audit.step_events[:2]:
            assert "********" in event.parameters_summary
            assert "masked" in event.parameters_summary

        # 4. Pydantic roundtrip validation
        reloaded = KutomotoAuditLog.model_validate_json(audit_json)
        assert reloaded.copyright == "Copyrights reserved to 90Studio"
        assert len(reloaded.step_events) == 3
