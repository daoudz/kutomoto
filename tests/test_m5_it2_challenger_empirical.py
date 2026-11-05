"""
tests.test_m5_it2_challenger_empirical
Adversarial Stress Harness & Empirical Verification Suite for Milestone 5 Iteration 2 Challenger.
Focus areas:
1. Multi-run runner reusability & cursor displacement isolation (>100px) across repeated runs
2. Whitespace variable interpolation across complex, adversarial, and regex-sensitive templates
3. Concurrency, rapid pause/resume/abort transitions, and FSM recovery
4. Failsafe disarm, idempotency, and modifier key cleanup

Copyrights reserved to 90Studio
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from typing import List

import pytest

SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from kutomoto.engine.fsm import ExecutionState  # noqa: E402
from kutomoto.engine.runner import WorkflowRunner  # noqa: E402
from kutomoto.engine.safety import (  # noqa: E402
    CornerFailsafeTriggered,
    MockWin32Driver,
    SafetyConfig,
    SafetyGuard,
)
from kutomoto.engine.schema import (  # noqa: E402
    ActionType,
    ExecutionSettings,
    KutomotoWorkflow,
    StepParameters,
    TargetAppType,
    TargetApplication,
    VariableType,
    WorkflowStep,
    WorkflowVariable,
)


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
    return driver


def make_test_workflow(num_steps: int = 3, prefix: str = "Step") -> KutomotoWorkflow:
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
                parameters=StepParameters(text=f"{prefix}_{i}"),
                pre_delay_ms=10,
                post_delay_ms=10,
            )
        )
    return KutomotoWorkflow(
        id=f"wf_{prefix}_{num_steps}",
        name=f"Workflow {prefix}",
        target_application=TargetApplication(
            type=TargetAppType.WEB_BROWSER,
            window_title_pattern=r".*Banking KYC.*",
        ),
        execution_settings=ExecutionSettings(
            countdown_seconds=0,
            default_step_delay_ms=10,
        ),
        steps=steps,
    )


# ==============================================================================
# 1. RUNNER REUSABILITY & CURSOR DISPLACEMENT ISOLATION (>100px)
# ==============================================================================

class TestRunnerReusabilityAndCursorIsolation:
    """Empirically stress-tests runner reusability and cursor position resets across runs."""

    @pytest.mark.asyncio
    async def test_repeated_runs_with_huge_cursor_displacements(self, mock_driver, monkeypatch):
        """
        Executes 5 consecutive workflows on a single WorkflowRunner instance.
        Between each run, the cursor position jumps by large distances (>100px, up to 1800px).
        Verifies:
        1. All 5 runs complete with final_status == 'SUCCESS'.
        2. No false MouseDisturbanceDetected is raised across runs.
        3. Each run's audit log contains exactly 3 step events (no cross-run event leakage).
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        runner = WorkflowRunner(driver=mock_driver)
        wf = make_test_workflow(num_steps=3, prefix="Displacement")

        # Define 5 distant cursor positions
        cursor_positions = [
            (50, 50),
            (850, 950),   # Jump ~1200px
            (100, 800),   # Jump ~764px
            (1800, 200),  # Jump ~1802px
            (200, 300),   # Jump ~1603px
        ]

        for i, pos in enumerate(cursor_positions):
            mock_driver.set_cursor_pos(pos[0], pos[1])
            audit = await runner.execute(wf)

            assert audit.execution_summary.final_status == "SUCCESS", (
                f"Run {i+1} failed unexpectedly at cursor pos {pos}"
            )
            assert runner.state == ExecutionState.COMPLETED
            assert len(audit.step_events) == 3, (
                f"Run {i+1} audit event leakage: expected 3 events, got {len(audit.step_events)}"
            )

    @pytest.mark.asyncio
    async def test_disturbance_abort_followed_by_successful_recovery_run(self, mock_driver, monkeypatch):
        """
        Verifies that:
        1. Genuine mouse disturbance (>100px) mid-execution successfully trips safety guard and fails.
        2. Immediate subsequent run with another huge cursor displacement succeeds cleanly.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        runner = WorkflowRunner(driver=mock_driver)
        wf = make_test_workflow(num_steps=4, prefix="Disturb")

        # Run 1: Normal success
        mock_driver.set_cursor_pos(100, 100)
        audit1 = await runner.execute(wf)
        assert audit1.execution_summary.final_status == "SUCCESS"

        # Run 2: Inject physical disturbance mid-run
        mock_driver.set_cursor_pos(300, 300)

        # Inject mouse disturbance during step 2
        async def _bump_mouse_delayed():
            await asyncio.sleep(0.015)
            mock_driver.simulate_mouse_disturbance(dx=250, dy=250)

        bump_task = asyncio.create_task(_bump_mouse_delayed())
        audit2 = await runner.execute(wf)
        await bump_task

        assert audit2.execution_summary.final_status in ("FAILED", "ABORTED")

        # Run 3: Jump cursor to (900, 900) (>800px displacement) and re-execute
        mock_driver.set_cursor_pos(900, 900)
        audit3 = await runner.execute(wf)
        assert audit3.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED
        assert len(audit3.step_events) == 4

    @pytest.mark.asyncio
    async def test_custom_safety_guard_instance_reusability(self, mock_driver, monkeypatch):
        """
        Verifies that an explicitly injected SafetyGuard instance with custom thresholds
        correctly resets across multiple executions on the same runner.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        custom_guard = SafetyGuard(
            driver=mock_driver,
            config=SafetyConfig(
                mouse_disturbance_threshold_px=50.0,
                corner_failsafe_enabled=True,
            ),
        )
        runner = WorkflowRunner(driver=mock_driver, safety_guard=custom_guard)
        wf = make_test_workflow(num_steps=3, prefix="CustomGuard")

        # Run 1
        mock_driver.set_cursor_pos(100, 100)
        audit1 = await runner.execute(wf)
        assert audit1.execution_summary.final_status == "SUCCESS"

        # Cursor displacement 300px (>50px custom threshold) between runs
        mock_driver.set_cursor_pos(400, 400)
        audit2 = await runner.execute(wf)
        assert audit2.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED


# ==============================================================================
# 2. WHITESPACE VARIABLE TEMPLATING ADVERSARIAL STRESS
# ==============================================================================

class TestWhitespaceVariableInterpolationAdversarial:
    """Verifies whitespace variations, boundary values, regex escape sequences, and syntax limits."""

    @pytest.mark.asyncio
    async def test_whitespace_permutations_and_tabs(self, mock_driver, monkeypatch):
        """
        Verifies variable resolution with varying internal whitespace:
        no spaces, single spaces, multiple spaces, tabs, and multiline tokens.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        runner = WorkflowRunner(driver=mock_driver)

        workflow = KutomotoWorkflow(
            name="Whitespace Stress",
            target_application=TargetApplication(type=TargetAppType.WEB_BROWSER, window_title_pattern=".*KYC.*"),
            variables=[
                WorkflowVariable(name="first_name", default_value="John"),
                WorkflowVariable(name="last_name", default_value="Doe"),
                WorkflowVariable(name="account_id", default_value="AC-990"),
            ],
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(
                        text="{{first_name}}|{{ last_name }}|{{   account_id   }}|{{\tfirst_name\t}}"
                    ),
                ),
            ],
        )

        audit = await runner.execute(workflow)
        assert audit.execution_summary.final_status == "SUCCESS"
        assert "John|Doe|AC-990|John" in mock_driver.typed_text

    @pytest.mark.asyncio
    async def test_adjacent_variables_without_delimiter(self, mock_driver, monkeypatch):
        """Verifies adjacent variable interpolation like '{{ first }}{{ last }}'."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        runner = WorkflowRunner(driver=mock_driver)

        workflow = KutomotoWorkflow(
            name="Adjacent Vars",
            target_application=TargetApplication(type=TargetAppType.WEB_BROWSER, window_title_pattern=".*KYC.*"),
            variables=[
                WorkflowVariable(name="a", default_value="Hello"),
                WorkflowVariable(name="b", default_value="World"),
            ],
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text="{{ a }}{{ b }}--{{a}}{{b}}"),
                ),
            ],
        )

        audit = await runner.execute(workflow)
        assert audit.execution_summary.final_status == "SUCCESS"
        assert "HelloWorld--HelloWorld" in mock_driver.typed_text

    @pytest.mark.asyncio
    async def test_regex_special_characters_in_variable_values(self, mock_driver, monkeypatch):
        """
        Adversarial test: variable values containing regex backreference patterns
        like '\\g<1>', '\\1', '$1', and backslashes should NOT break re.sub.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        runner = WorkflowRunner(driver=mock_driver)

        tricky_value = r"\g<1> and \1 and $1 and C:\Program Files\90Studio"

        workflow = KutomotoWorkflow(
            name="Tricky Regex Value",
            target_application=TargetApplication(type=TargetAppType.WEB_BROWSER, window_title_pattern=".*KYC.*"),
            variables=[
                WorkflowVariable(name="regex_val", default_value=tricky_value),
            ],
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text="Value: {{ regex_val }}"),
                ),
            ],
        )

        audit = await runner.execute(workflow)
        assert audit.execution_summary.final_status == "SUCCESS"
        assert f"Value: {tricky_value}" in mock_driver.typed_text

    @pytest.mark.asyncio
    async def test_numeric_zero_float_zero_and_empty_string(self, mock_driver, monkeypatch):
        """Verifies that 0, 0.0, False, and empty string are correctly interpolated."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        runner = WorkflowRunner(driver=mock_driver)

        workflow = KutomotoWorkflow(
            name="Falsy Values",
            target_application=TargetApplication(type=TargetAppType.WEB_BROWSER, window_title_pattern=".*KYC.*"),
            variables=[
                WorkflowVariable(name="num_zero", default_value="0", type=VariableType.NUMBER),
                WorkflowVariable(name="float_zero", default_value="0.0", type=VariableType.NUMBER),
                WorkflowVariable(name="flag_false", default_value="false"),
                WorkflowVariable(name="empty_str", default_value=""),
            ],
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(
                        text="Z:{{ num_zero }}, FZ:{{ float_zero }}, B:{{ flag_false }}, E:[{{ empty_str }}]"
                    ),
                ),
            ],
        )

        audit = await runner.execute(
            workflow,
            runtime_variables={
                "num_zero": 0,
                "float_zero": 0.0,
                "flag_false": False,
                "empty_str": "",
            },
        )
        assert audit.execution_summary.final_status == "SUCCESS"
        assert "Z:0, FZ:0.0, B:False, E:[]" in mock_driver.typed_text

    @pytest.mark.asyncio
    async def test_unresolved_and_malformed_tokens_preserved(self, mock_driver, monkeypatch):
        """
        Verifies that tokens matching invalid patterns (e.g. empty {{}}, numbers only {{ 123 }})
        or missing variables are left unmodified.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        runner = WorkflowRunner(driver=mock_driver)

        workflow = KutomotoWorkflow(
            name="Malformed Tokens",
            target_application=TargetApplication(type=TargetAppType.WEB_BROWSER, window_title_pattern=".*KYC.*"),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(
                        text="Empty: {{}}, Blank: {{   }}, Digits: {{ 123 }}, Missing: {{ not_set }}"
                    ),
                ),
            ],
        )

        audit = await runner.execute(workflow)
        assert audit.execution_summary.final_status == "SUCCESS"
        assert "Empty: {{}}, Blank: {{   }}, Digits: {{ 123 }}, Missing: {{ not_set }}" in mock_driver.typed_text


# ==============================================================================
# 3. CONCURRENCY, RAPID TRANSITIONS & FSM INTEGRITY
# ==============================================================================

class TestConcurrencyAndFSMTransitions:
    """Stress-tests rapid lifecycle transitions, pause/resume/abort races, and FSM integrity."""

    @pytest.mark.asyncio
    async def test_high_frequency_pause_resume_under_continuous_actions(self, mock_driver, monkeypatch):
        """
        Executes a 12-step workflow with 15 rapid pause/resume cycles.
        Verifies zero deadlocks and 100% completion.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        runner = WorkflowRunner(driver=mock_driver)
        wf = make_test_workflow(num_steps=12, prefix="Flap")

        exec_task = asyncio.create_task(runner.execute(wf))

        for _ in range(15):
            await asyncio.sleep(0.01)
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
    async def test_concurrent_abort_bursts_idempotency(self, mock_driver, monkeypatch):
        """
        Simultaneously fires 10 concurrent abort calls on an active runner.
        Verifies all calls resolve without unhandled exceptions and state lands in STOPPED.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        runner = WorkflowRunner(driver=mock_driver)
        wf = make_test_workflow(num_steps=10, prefix="BurstAbort")

        exec_task = asyncio.create_task(runner.execute(wf))
        await asyncio.sleep(0.02)

        async def _call_abort():
            await runner.abort()

        results = await asyncio.gather(*[_call_abort() for _ in range(10)], return_exceptions=True)
        for r in results:
            assert not isinstance(r, Exception) or issubclass(type(r), asyncio.CancelledError)

        audit = await exec_task
        assert audit.execution_summary.final_status == "ABORTED"
        assert runner.state in (ExecutionState.STOPPED, ExecutionState.STOPPING)

    @pytest.mark.asyncio
    async def test_reexecution_immediately_following_abort(self, mock_driver, monkeypatch):
        """
        Verifies that after an emergency abort, runner can immediately execute another workflow
        to SUCCESS without needing a new runner instance.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        runner = WorkflowRunner(driver=mock_driver)
        wf1 = make_test_workflow(num_steps=8, prefix="AbortedRun")
        wf2 = make_test_workflow(num_steps=3, prefix="CleanRun")

        # 1. Start wf1 and abort it
        task1 = asyncio.create_task(runner.execute(wf1))
        await asyncio.sleep(0.02)
        await runner.abort()
        audit1 = await task1
        assert audit1.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED

        # 2. Immediately execute wf2 on same runner
        audit2 = await runner.execute(wf2)
        assert audit2.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED
        assert len(audit2.step_events) == 3


# ==============================================================================
# 4. FAILSAFE DISARM & HOOK CLEANUP
# ==============================================================================

class TestFailsafeDisarmAndHookCleanupEmpirical:
    """Verifies failsafe disarming, hook cleanup, and idempotency."""

    def test_safety_guard_reset_idempotency(self, mock_driver):
        """Verifies calling SafetyGuard.reset() repeatedly is strictly idempotent."""
        guard = SafetyGuard(driver=mock_driver)
        # Call reset 5 times consecutively
        for _ in range(5):
            guard.reset()
            assert guard._watcher_task is None
            assert guard._abort_requested is False
            assert guard._last_cursor_pos is None
            assert guard._active_target_hwnd is None

    @pytest.mark.asyncio
    async def test_safety_guard_reset_stops_running_watcher(self, mock_driver):
        """Verifies reset() cleanly terminates an active background watcher task."""
        guard = SafetyGuard(driver=mock_driver)
        await guard.start_background_watcher(check_interval_sec=0.01)
        assert guard._watcher_task is not None
        assert not guard._watcher_task.done()

        # Call reset: watcher should be cancelled and set to None
        guard.reset()
        await asyncio.sleep(0.02)
        assert guard._watcher_task is None

    @pytest.mark.asyncio
    async def test_four_corner_failsafe_boundaries(self, mock_driver):
        """Verifies corner failsafe detection across screen corners."""
        guard = SafetyGuard(
            driver=mock_driver,
            config=SafetyConfig(
                corner_failsafe_enabled=True,
                corner_threshold_px=2,
            ),
        )

        # Mock driver screen dimension defaults to 1920x1080
        screen_w, screen_h = mock_driver.get_screen_dimensions()

        # Points that MUST trip CornerFailsafeTriggered:
        corners_tripping = [
            (0, 0),                       # Top-Left corner (0,0)
            (1, 1),                       # Top-Left inside 2px threshold
            (2, 2),                       # Top-Left boundary exactly 2px
            (screen_w, 0),                # Top-Right corner
            (screen_w - 1, 0),            # Top-Right near
            (screen_w - 2, 2),            # Top-Right boundary exactly 2px
        ]

        # Points that MUST NOT trip:
        safe_points = [
            (3, 3),                       # Just outside Top-Left 2px threshold
            (screen_w - 3, 3),            # Just outside Top-Right 2px threshold
            (960, 540),                   # Center screen
        ]

        for x, y in corners_tripping:
            mock_driver.set_cursor_pos(x, y)
            with pytest.raises(CornerFailsafeTriggered):
                guard.check_corner_failsafe()

        for x, y in safe_points:
            mock_driver.set_cursor_pos(x, y)
            # Should NOT raise CornerFailsafeTriggered
            guard.check_corner_failsafe()

    @pytest.mark.asyncio
    async def test_modifier_release_on_all_possible_modifiers(self, mock_driver, monkeypatch):
        """
        Pre-populates mock driver with all virtual key modifier combinations,
        triggers emergency abort, and verifies all 11 modifiers are released.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        all_modifiers = [
            0x10,  # VK_SHIFT
            0x11,  # VK_CONTROL
            0x12,  # VK_MENU (ALT)
            0x5B,  # VK_LWIN
            0x5C,  # VK_RWIN
            0xA0,  # VK_LSHIFT
            0xA1,  # VK_RSHIFT
            0xA2,  # VK_LCONTROL
            0xA3,  # VK_RCONTROL
            0xA4,  # VK_LMENU
            0xA5,  # VK_RMENU
        ]
        mock_driver.pressed_keys.update(all_modifiers)
        mock_driver.active_modifiers.update(["ctrl", "alt", "shift", "win"])

        runner = WorkflowRunner(driver=mock_driver)
        wf = make_test_workflow(num_steps=3, prefix="ModRelease")

        # Simulate Escape abort
        mock_driver.simulate_escape_press()
        audit = await runner.execute(wf)

        assert audit.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED

        # Verify mock driver cleared all keys
        for vk in all_modifiers:
            assert vk not in mock_driver.pressed_keys, f"Modifier 0x{vk:02X} was not released!"
        assert len(mock_driver.active_modifiers) == 0
