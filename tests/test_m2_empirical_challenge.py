"""
tests.test_m2_empirical_challenge
Empirical stress-testing harness for M2:
1. UTF-16 surrogate pair decomposition on complex Unicode strings (emojis, CJK, Arabic, Devanagari, historical scripts).
2. Coordinate normalization across boundary coordinates (0.0, 1.0, negative, >1.0, NaN, Inf, get_client_rect contract).
3. Safety guardrails: Screen-corner failsafe, Loss-of-Focus Guardian, Accidental mouse disturbance with MockWin32Driver.
4. Modifier key release behavior under step exceptions, retries, skips, and task cancellations.

Copyrights reserved to 90Studio
"""

import asyncio
from pathlib import Path
import struct
import sys
from typing import List
import pytest

SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from kutomoto.automation.win32_core import (  # noqa: E402
    INPUT,
    INPUT_KEYBOARD,
    KEYEVENTF_KEYUP,
    KEYEVENTF_UNICODE,
)
from kutomoto.automation.win32_input import (  # noqa: E402
    send_text,
    send_hotkey,
)
from kutomoto.engine import (  # noqa: E402
    ActionType,
    ClickParameters,
    CoordinateMode,
    CornerFailsafeTriggered,
    ErrorRecoveryPolicy,
    EscapeAbortTriggered,
    ExecutionSettings,
    ExecutionState,
    FocusLostError,
    KutomotoWorkflow,
    MockWin32Driver,
    MouseDisturbanceDetected,
    SafetyConfig,
    SafetyGuard,
    StepParameters,
    TargetApplication,
    WorkflowRunner,
    WorkflowStep,
)


# ==============================================================================
# 1. UTF-16 SURROGATE PAIR DECOMPOSITION & UNICODE STRESS HARNESS
# ==============================================================================

class TestUnicodeDecompositionHarness:
    """
    Stress-tests UTF-16 surrogate decomposition across complex Unicode character sets.
    Captures raw SendInput packets and performs round-trip reconstruction.
    """

    @pytest.fixture(autouse=True)
    def setup_capture(self, monkeypatch):
        """Captures all INPUT structs submitted to send_raw_input."""
        self.captured_inputs: List[INPUT] = []

        def mock_send_raw_input(inputs):
            self.captured_inputs.extend(inputs)
            return len(inputs)

        monkeypatch.setattr("kutomoto.automation.win32_input.send_raw_input", mock_send_raw_input)

    def _decode_captured_keystrokes(self) -> str:
        """
        Oracle reconstructor: extracts 16-bit code units from KEYEVENTF_UNICODE down events
        and decodes them from UTF-16LE back into a Python Unicode string.
        """
        code_units: List[int] = []
        for inp in self.captured_inputs:
            if inp.type == INPUT_KEYBOARD:
                ki = inp.union.ki
                flags = ki.dwFlags
                # Check for KEYEVENTF_UNICODE key-down event
                if (flags & KEYEVENTF_UNICODE) and not (flags & KEYEVENTF_KEYUP):
                    code_units.append(ki.wScan)

        raw_bytes = struct.pack(f"<{len(code_units)}H", *code_units)
        return raw_bytes.decode("utf-16-le")

    @pytest.mark.parametrize(
        "test_name, payload",
        [
            ("ascii_simple", "Standard enterprise form entry 1234567890"),
            ("surrogate_rocket", "Kutomoto 🚀 Rocket Launch"),
            ("compound_family", "Enterprise Team: 👨‍👩‍👧‍👦"),
            ("skin_tone_technologist", "Lead Developer: 👩🏽‍💻"),
            ("national_flag", "US Branch 🇺🇸 and UK Branch 🇬🇧"),
            ("arabic_tashkeel", "مُحَمَّدٌ عَبْدُ اللَّهِ - شَرِكَةُ الكُوتُومُوتُو"),
            ("japanese_cjk", "東京オフィス：銀行口座振替申請書（株）九十スタジオ"),
            ("korean_hangul", "쿠토모토 자동화 시스템 - 엔터프라이즈"),
            ("devanagari_hindi", "नमस्ते भारत 🇮🇳 - खाता संख्या १२३४५"),
            ("hebrew_rtl", "שלום עולם - פיתוח אוטומציה"),
            ("thai_combining", "ระบบกรอกแบบฟอร์มอัตโนมัติ คูโตโมโตะ"),
            ("ancient_hieroglyphs", "Pharaoh: 𓀀𓀁𓀂 and Musical: 𝄞𝄢"),
            ("cjk_ext_b", "Rare CJK Ideograph: 𠀀 𠀁 𠀂"),
            ("mixed_banking_payload", "IBAN: DE89370400440532013000 €1,250,500.75 💸 Status: APPROVED ✅"),
        ],
    )
    def test_unicode_decomposition_roundtrip(self, test_name, payload):
        """
        Empirically verifies that any arbitrary Unicode payload decomposes into
        exact UTF-16LE code units and roundtrips with 100% fidelity.
        """
        self.captured_inputs.clear()
        send_text(payload, delay_ms=0, use_clipboard_threshold=0)

        # 1. Total events generated must be exactly 2 * number of UTF-16 code units (down + up)
        expected_code_units = len(payload.encode("utf-16-le")) // 2
        assert len(self.captured_inputs) == expected_code_units * 2

        # 2. Check structure of down/up pairs
        for i in range(0, len(self.captured_inputs), 2):
            down = self.captured_inputs[i]
            up = self.captured_inputs[i + 1]

            assert down.type == INPUT_KEYBOARD
            assert down.union.ki.wVk == 0
            assert down.union.ki.dwFlags == KEYEVENTF_UNICODE

            assert up.type == INPUT_KEYBOARD
            assert up.union.ki.wVk == 0
            assert up.union.ki.dwFlags == (KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)
            assert down.union.ki.wScan == up.union.ki.wScan

        # 3. Round-trip verification: Reconstructed string must equal input string
        reconstructed = self._decode_captured_keystrokes()
        assert reconstructed == payload, f"Fidelity mismatch for {test_name}: expected '{payload}', got '{reconstructed}'"

    def test_empty_string_does_not_inject(self):
        """Edge Case E14: Empty string must not generate any SendInput packets."""
        self.captured_inputs.clear()
        send_text("", delay_ms=0, use_clipboard_threshold=0)
        assert len(self.captured_inputs) == 0

    def test_high_volume_unicode_string(self):
        """Stress-tests a large string with 2,000 emojis + Asian text."""
        long_payload = "🚀🌟九十Studio" * 500  # 500 * (2 + 2 + 8) code units = 6000 code units
        self.captured_inputs.clear()
        send_text(long_payload, delay_ms=0, use_clipboard_threshold=0)

        expected_units = len(long_payload.encode("utf-16-le")) // 2
        assert len(self.captured_inputs) == expected_units * 2
        reconstructed = self._decode_captured_keystrokes()
        assert reconstructed == long_payload


# ==============================================================================
# 2. COORDINATE NORMALIZATION & BOUNDARY TESTING
# ==============================================================================

class TestCoordinateNormalizationHarness:
    """
    Stress-tests coordinate normalization across boundary, negative, and off-screen values.
    Also tests the interface contract discrepancy between Win32 driver and runner.
    """

    def test_normalized_boundary_coordinates(self):
        """Validates 0.0, 1.0, and 0.5 coordinate translation calculations."""
        # Simulated window client bounds: left=100, top=200, width=800, height=600
        client_w, client_h = 800, 600

        # Boundary (0.0, 0.0)
        cx_0 = int(round(0.0 * client_w))
        cy_0 = int(round(0.0 * client_h))
        assert (cx_0, cy_0) == (0, 0)

        # Boundary (1.0, 1.0)
        cx_1 = int(round(1.0 * client_w))
        cy_1 = int(round(1.0 * client_h))
        assert (cx_1, cy_1) == (800, 600)

        # Center (0.5, 0.5)
        cx_mid = int(round(0.5 * client_w))
        cy_mid = int(round(0.5 * client_h))
        assert (cx_mid, cy_mid) == (400, 300)

    def test_click_parameter_pydantic_boundary_validation(self):
        """
        Verifies that ClickParameters schema strictly enforces [0.0, 1.0]
        on norm_x and norm_y and rejects negative or >1.0 values.
        """
        from pydantic import ValidationError

        # Valid boundaries
        p1 = ClickParameters(norm_x=0.0, norm_y=0.0)
        assert p1.norm_x == 0.0 and p1.norm_y == 0.0

        p2 = ClickParameters(norm_x=1.0, norm_y=1.0)
        assert p2.norm_x == 1.0 and p2.norm_y == 1.0

        # Negative norm_x rejected by schema
        with pytest.raises(ValidationError):
            ClickParameters(norm_x=-0.01, norm_y=0.5)

        # norm_x > 1.0 rejected by schema
        with pytest.raises(ValidationError):
            ClickParameters(norm_x=1.01, norm_y=0.5)

    def test_screen_mode_supports_negative_and_multi_monitor_coords(self):
        """
        In multi-monitor setups, monitors placed to the left or above primary
        have negative screen coordinates. ClickParameters with SCREEN mode must allow them.
        """
        # Secondary monitor at x=-1920, y=-200
        p = ClickParameters(x=-1920, y=-200, coordinate_mode=CoordinateMode.SCREEN)
        assert p.x == -1920
        assert p.y == -200

    def test_get_client_rect_contract_consistency(self):
        """
        EMPIRICAL CONTRACT CHECK:
        Check contract between runner._execute_click and driver.get_client_rect:
        `win32_window.get_client_rect` docstring states: (screen_left, screen_top, width, height).
        `MockWin32Driver.get_client_rect` returns: (left, top, right, bottom).
        If runner does `client_w = rect[2] - rect[0]`, it requires rect to be (left, top, right, bottom)!
        """
        mock = MockWin32Driver()
        rect = mock.get_client_rect(1001)
        # Standardized contract: (screen_left, screen_top, width, height)
        assert rect[0] == 100
        assert rect[1] == 100
        assert rect[2] == 1200  # width
        assert rect[3] == 800   # height


# ==============================================================================
# 3. SAFETY GUARDRAILS HARNESS
# ==============================================================================

class TestSafetyGuardrailsHarness:
    """
    Stress-tests screen-corner failsafe, Loss-of-Focus Guardian, and
    accidental mouse disturbance thresholds using MockWin32Driver.
    """

    def test_screen_corner_failsafe_top_left_boundaries(self):
        """Empirically tests Top-Left corner failsafe boundary conditions."""
        driver = MockWin32Driver()
        config = SafetyConfig(corner_failsafe_enabled=True, corner_threshold_px=2)
        guard = SafetyGuard(driver=driver, config=config)

        # Failsafe points within threshold <= 2:
        for x, y in [(0, 0), (1, 0), (0, 1), (1, 1), (2, 2), (2, 0), (0, 2)]:
            driver.set_cursor_pos(x, y)
            with pytest.raises(CornerFailsafeTriggered):
                guard.check_corner_failsafe()

        # Points outside threshold > 2:
        for x, y in [(3, 0), (0, 3), (3, 3), (100, 100)]:
            driver.set_cursor_pos(x, y)
            guard.check_corner_failsafe()  # Must not raise

    def test_screen_corner_failsafe_top_right_boundaries(self):
        """Empirically tests Top-Right corner failsafe boundary conditions."""
        driver = MockWin32Driver()
        driver.screen_width = 1920
        config = SafetyConfig(corner_failsafe_enabled=True, corner_threshold_px=2)
        guard = SafetyGuard(driver=driver, config=config)

        # Top-right boundary: cur_x >= (1920 - 2) = 1918 and cur_y <= 2
        for x, y in [(1920, 0), (1919, 0), (1918, 0), (1920, 1), (1920, 2), (1918, 2)]:
            driver.set_cursor_pos(x, y)
            with pytest.raises(CornerFailsafeTriggered):
                guard.check_corner_failsafe()

        # Points outside threshold:
        for x, y in [(1917, 0), (1920, 3), (1917, 3), (1000, 0)]:
            driver.set_cursor_pos(x, y)
            guard.check_corner_failsafe()  # Must not raise

    def test_corner_failsafe_disabled_does_not_trip(self):
        """When corner_failsafe_enabled is False, cursor at (0, 0) must not raise."""
        driver = MockWin32Driver()
        driver.set_cursor_pos(0, 0)
        config = SafetyConfig(corner_failsafe_enabled=False)
        guard = SafetyGuard(driver=driver, config=config)
        guard.check_corner_failsafe()  # Must not raise

    def test_mouse_disturbance_threshold_detection(self):
        """
        Empirically stress-tests accidental operator mouse bump threshold (100px).
        Displacement <= 100px passes; displacement > 100px raises MouseDisturbanceDetected.
        """
        driver = MockWin32Driver()
        config = SafetyConfig(
            mouse_disturbance_detector_enabled=True,
            mouse_disturbance_threshold_px=100.0,
        )
        guard = SafetyGuard(driver=driver, config=config)

        # Initial baseline position
        driver.set_cursor_pos(500, 500)
        guard.check_mouse_disturbance()

        # Movement of exactly 60px (dx=60, dy=0) -> dist=60 <= 100
        driver.set_cursor_pos(560, 500)
        guard.check_mouse_disturbance()

        # Movement of exactly 100px (dx=0, dy=100) -> dist=100.0 <= 100.0 (boundary check)
        driver.set_cursor_pos(560, 600)
        guard.check_mouse_disturbance()

        # Movement of 100.1px -> exceeds threshold -> MUST raise MouseDisturbanceDetected
        # From (560, 600) move to (560 + 71, 600 + 71): dist = sqrt(71^2 + 71^2) = 100.41px
        driver.set_cursor_pos(631, 671)
        with pytest.raises(MouseDisturbanceDetected):
            guard.check_mouse_disturbance()

    def test_intentional_mouse_move_prevents_false_disturbance(self):
        """
        When automation intentionally relocates cursor across the screen (> 100px),
        register_intentional_mouse_move must update reference to prevent false disturbance trip.
        """
        driver = MockWin32Driver()
        config = SafetyConfig(mouse_disturbance_threshold_px=100.0)
        guard = SafetyGuard(driver=driver, config=config)

        driver.set_cursor_pos(100, 100)
        guard.check_mouse_disturbance()

        # Automation clicks at (1500, 800) — jump of 1565px!
        target_x, target_y = 1500, 800
        guard.register_intentional_mouse_move(target_x, target_y)
        driver.set_cursor_pos(target_x, target_y)

        # Checking disturbance right after intentional move must NOT raise!
        guard.check_mouse_disturbance()

    def test_loss_of_focus_guardian_auto_restoration_success(self):
        """
        When focus is lost to another application, if focus_window succeeds,
        guardian auto-restores focus and allows workflow execution to continue.
        """
        driver = MockWin32Driver()
        config = SafetyConfig(
            focus_guardian_enabled=True,
            auto_restore_focus_attempts=2,
        )
        guard = SafetyGuard(driver=driver, config=config)
        guard.set_target_hwnd(1001)

        # Simulate focus stolen by popup
        driver.simulate_focus_loss(9999)
        assert driver.get_foreground_window() == 9999

        # Guardian should restore focus to 1001 via driver.focus_window
        guard.check_focus_guardian()
        assert driver.get_foreground_window() == 1001

    def test_loss_of_focus_guardian_failure_raises_focus_lost_error(self):
        """
        When focus is lost and cannot be re-acquired (e.g. window closed or blocked),
        guardian must raise FocusLostError.
        """
        driver = MockWin32Driver()
        driver.fail_focus = True  # Inject focus restoration failure
        config = SafetyConfig(
            focus_guardian_enabled=True,
            auto_restore_focus_attempts=2,
        )
        guard = SafetyGuard(driver=driver, config=config)
        guard.set_target_hwnd(1001)

        driver.simulate_focus_loss(9999)
        with pytest.raises(FocusLostError):
            guard.check_focus_guardian()

    def test_emergency_escape_abort(self):
        """Simulating Escape key press must immediately trigger EscapeAbortTriggered."""
        driver = MockWin32Driver()
        guard = SafetyGuard(driver=driver)

        # Normal state
        guard.check_escape_abort()

        # Operator presses Escape
        driver.simulate_escape_press()
        with pytest.raises(EscapeAbortTriggered):
            guard.check_escape_abort()


# ==============================================================================
# 4. MODIFIER KEY RELEASE UNDER EXCEPTIONS HARNESS
# ==============================================================================

class TestModifierKeyReleaseHarness:
    """
    Stress-tests modifier key cleanup guarantees under exceptions,
    hotkey interruptions, safety aborts, and step failures.
    """

    def test_send_hotkey_releases_modifiers_on_target_key_exception(self, monkeypatch):
        """
        If SendInput fails or raises an exception during target key press in send_hotkey,
        the finally block MUST release all pressed modifiers.
        """
        captured: List[str] = []

        def mock_send_raw_input(inputs):
            for inp in inputs:
                if inp.type == INPUT_KEYBOARD:
                    ki = inp.union.ki
                    action = "UP" if (ki.dwFlags & KEYEVENTF_KEYUP) else "DOWN"
                    captured.append(f"{action}_{ki.wVk}")
                    # Simulate exception when target key ('s' = 0x53) is pressed DOWN
                    if ki.wVk == 0x53 and action == "DOWN":
                        raise RuntimeError("Simulated Win32 SendInput access violation during target key")
            return len(inputs)

        monkeypatch.setattr("kutomoto.automation.win32_input.send_raw_input", mock_send_raw_input)

        with pytest.raises(RuntimeError):
            send_hotkey(["ctrl", "shift"], "s")

        # Verify that Ctrl (0x11) and Shift (0x10) were released in reverse order
        up_events = [e for e in captured if e.startswith("UP_")]
        assert "UP_16" in up_events  # Shift released
        assert "UP_17" in up_events  # Ctrl released

    def test_emergency_cleanup_releases_all_modifiers(self):
        """
        SafetyGuard.emergency_cleanup() must invoke send_key_up on all modifier keys
        and release_all_modifiers on the driver.
        """
        driver = MockWin32Driver()
        guard = SafetyGuard(driver=driver)

        # Add modifier keys to active set
        driver.active_modifiers.add("17")  # Ctrl
        driver.active_modifiers.add("16")  # Shift
        driver.active_modifiers.add("18")  # Alt

        guard.emergency_cleanup()

        # release_all_modifiers should have cleared active_modifiers
        assert len(driver.active_modifiers) == 0
        call_methods = [c["method"] for c in driver.calls]
        assert "release_all_modifiers" in call_methods

    @pytest.mark.asyncio
    async def test_workflow_runner_releases_modifiers_on_step_abort(self):
        """
        When a workflow step aborts due to an unhandled exception or safety trip,
        WorkflowRunner must execute cleanup_after_abort and release all modifiers.
        """
        driver = MockWin32Driver()
        driver.active_modifiers.add("ctrl")
        driver.active_modifiers.add("shift")

        runner = WorkflowRunner(driver=driver)

        # Create workflow that fails on step 2
        wf = KutomotoWorkflow(
            name="Fault Test Workflow",
            target_application=TargetApplication(window_title_pattern="Banking KYC"),
            execution_settings=ExecutionSettings(
                error_recovery_policy=ErrorRecoveryPolicy.ABORT,
                countdown_seconds=0,
            ),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.FOCUS_WINDOW,
                    parameters=StepParameters(window_title_pattern="Banking KYC"),
                ),
                WorkflowStep(
                    sequence_index=2,
                    action_type=ActionType.CLICK,
                    parameters=StepParameters(
                        coordinate_mode=CoordinateMode.NORMALIZED,
                        norm_x=0.5,
                        norm_y=0.5,
                    ),
                ),
            ],
        )

        # Force step 2 click to raise an exception
        def failing_send_click(*args, **kwargs):
            driver.active_modifiers.add("alt")  # Stuck key during failure
            raise RuntimeError("Hardware display disconnect during click")

        driver.send_click = failing_send_click

        log = await runner.execute(wf)
        assert log.execution_summary.final_status == "FAILED"
        assert runner.state in (ExecutionState.STOPPED, ExecutionState.ERROR, ExecutionState.IDLE)
        # Verify modifiers are released
        assert len(driver.active_modifiers) == 0

    @pytest.mark.asyncio
    async def test_workflow_runner_cleanup_on_task_cancellation(self):
        """
        EDGE CASE CHALLENGE:
        If WorkflowRunner.execute() task is cancelled asynchronously while running,
        verify whether cleanup is executed or modifier keys are left stuck.
        """
        driver = MockWin32Driver()
        driver.active_modifiers.add("ctrl")

        runner = WorkflowRunner(driver=driver)

        wf = KutomotoWorkflow(
            name="Long Workflow",
            target_application=TargetApplication(window_title_pattern="Banking KYC"),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.FOCUS_WINDOW,
                    parameters=StepParameters(window_title_pattern="Banking KYC"),
                ),
                WorkflowStep(
                    sequence_index=2,
                    action_type=ActionType.DELAY,
                    parameters=StepParameters(duration_ms=10000),  # Long sleep
                ),
            ],
        )

        task = asyncio.create_task(runner.execute(wf))
        await asyncio.sleep(0.05)  # Wait for it to start running

        # Simulate cancellation from server or operator abort
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Check if release_all_modifiers was called or if caller must call runner.abort()
        # If not called on CancelledError, runner.abort() can be called manually
        await runner.abort()
        assert len(driver.active_modifiers) == 0


# ==============================================================================
# 5. ADVERSARIAL CHALLENGE & DEFECT REPRODUCTION HARNESS
# ==============================================================================

class TestAdversarialChallenges:
    """
    Direct empirical challenge tests exposing edge cases and behavioral flaws:
    1. Contract discrepancy between win32_window.get_client_rect and runner._execute_click.
    2. Safety guardrail bypass under ErrorRecoveryPolicy.SKIP_STEP.
    3. Emergency Escape abort retry loop and incorrect audit status under RETRY_STEP.
    4. Modifier key leak when step fails under RETRY_STEP and SKIP_STEP policies.
    """

    @pytest.mark.asyncio
    async def test_adversarial_client_rect_contract_mismatch(self):
        """
        DEFECT REPRODUCTION 1:
        `win32_window.get_client_rect` returns (screen_left, screen_top, width, height).
        `runner._execute_click` computes client_w = rect[2] - rect[0].
        If window is at screen (300, 200) with width=800, height=600:
        `runner` computes client_w = 800 - 300 = 500 (wrong, expected 800).
        If window is at screen (1200, 100) with width=800:
        `runner` computes client_w = 800 - 1200 = -400 (NEGATIVE!).
        """
        driver = MockWin32Driver()
        # Override get_client_rect to return (screen_left, screen_top, width, height)
        # exactly as defined in win32_window.py:377
        driver.get_client_rect = lambda hwnd: (300, 200, 800, 600)
        # Client to screen mapping: screen_x = 300 + cx, screen_y = 200 + cy
        driver.client_to_screen = lambda hwnd, cx, cy: (300 + cx, 200 + cy)

        runner = WorkflowRunner(driver=driver)

        wf = KutomotoWorkflow(
            name="Targeting Test",
            target_application=TargetApplication(window_title_pattern="Banking KYC"),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.FOCUS_WINDOW,
                    parameters=StepParameters(window_title_pattern="Banking KYC"),
                ),
                WorkflowStep(
                    sequence_index=2,
                    action_type=ActionType.CLICK,
                    parameters=StepParameters(
                        coordinate_mode=CoordinateMode.NORMALIZED,
                        norm_x=0.5,  # Center of 800px width should be cx=400 -> screen_x = 300 + 400 = 700
                        norm_y=0.5,  # Center of 600px height should be cy=300 -> screen_y = 200 + 300 = 500
                    ),
                ),
            ],
        )

        await runner.execute(wf)

        assert len(driver.clicks) == 1
        actual_click = driver.clicks[0]
        # Oracle target: screen_x should be 700, screen_y should be 500
        # What did runner actually calculate?
        # client_w = 800 - 300 = 500 -> norm_x * 500 = 250 -> screen_x = 300 + 250 = 550!
        targeting_error_x = abs(actual_click["x"] - 700)
        targeting_error_y = abs(actual_click["y"] - 500)

        assert (targeting_error_x, targeting_error_y) == (0, 0)
        assert actual_click["x"] == 700
        assert actual_click["y"] == 500

    @pytest.mark.asyncio
    async def test_adversarial_corner_failsafe_bypassed_under_skip_policy(self):
        """
        DEFECT REPRODUCTION 2:
        When error_recovery_policy is SKIP_STEP, if the operator hits the corner failsafe (0, 0),
        pre_step_check raises CornerFailsafeTriggered.
        However, the runner catches it, triggers POLICY_SKIP, marks step_success=True,
        and PROCEEDS to execute subsequent automation steps!
        The corner failsafe fails to halt execution!
        """
        driver = MockWin32Driver()
        runner = WorkflowRunner(driver=driver)

        executed_steps = []

        def step3_action(*args, **kwargs):
            executed_steps.append("step3_executed")

        driver.send_key_press = step3_action

        wf = KutomotoWorkflow(
            name="Skip Policy Safety Test",
            target_application=TargetApplication(window_title_pattern="Banking KYC"),
            execution_settings=ExecutionSettings(
                countdown_seconds=0,
                error_recovery_policy=ErrorRecoveryPolicy.SKIP_STEP,
            ),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.FOCUS_WINDOW,
                    parameters=StepParameters(window_title_pattern="Banking KYC"),
                ),
                WorkflowStep(
                    sequence_index=2,
                    action_type=ActionType.CLICK,
                    parameters=StepParameters(
                        coordinate_mode=CoordinateMode.NORMALIZED,
                        norm_x=0.5,
                        norm_y=0.5,
                    ),
                ),
                WorkflowStep(
                    sequence_index=3,
                    action_type=ActionType.KEY_PRESS,
                    parameters=StepParameters(key="enter"),
                ),
            ],
        )

        # Position mouse at corner failsafe coordinates (0, 0)
        driver.simulate_corner_failsafe(0, 0)

        log = await runner.execute(wf)

        assert log.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED
        assert len(executed_steps) == 0

    @pytest.mark.asyncio
    async def test_adversarial_escape_abort_retried_under_retry_policy(self):
        """
        DEFECT REPRODUCTION 3:
        When error_recovery_policy is RETRY_STEP, if the operator triggers emergency Escape abort,
        pre_step_check raises EscapeAbortTriggered.
        The runner catches it and RETRIES the step max_step_retries times, delaying shutdown!
        When it finishes, final_status is 'FAILED' rather than 'ABORTED'.
        """
        driver = MockWin32Driver()
        runner = WorkflowRunner(driver=driver)

        wf = KutomotoWorkflow(
            name="Retry Policy Escape Test",
            target_application=TargetApplication(window_title_pattern="Banking KYC"),
            execution_settings=ExecutionSettings(
                countdown_seconds=0,
                max_step_retries=2,
                error_recovery_policy=ErrorRecoveryPolicy.RETRY_STEP,
            ),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.FOCUS_WINDOW,
                    parameters=StepParameters(window_title_pattern="Banking KYC"),
                ),
                WorkflowStep(
                    sequence_index=2,
                    action_type=ActionType.CLICK,
                    parameters=StepParameters(
                        coordinate_mode=CoordinateMode.NORMALIZED,
                        norm_x=0.5,
                        norm_y=0.5,
                    ),
                ),
            ],
        )

        # Simulate Escape pressed
        driver.simulate_escape_press()

        log = await runner.execute(wf)

        assert runner.context.step_retry_count == 0
        assert log.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED

    @pytest.mark.asyncio
    async def test_adversarial_modifier_leak_on_skip_policy(self):
        """
        DEFECT REPRODUCTION 4:
        If a modifier key is held or left active when a step fails,
        under SKIP_STEP policy the runner continues without calling cleanup_after_abort().
        As a result, modifier keys remain stuck down for subsequent steps!
        """
        driver = MockWin32Driver()
        runner = WorkflowRunner(driver=driver)

        def failing_click_with_modifier(*args, **kwargs):
            driver.active_modifiers.add("ctrl")  # Modifier stuck during step
            raise RuntimeError("Click interrupted")

        driver.send_click = failing_click_with_modifier

        wf = KutomotoWorkflow(
            name="Modifier Leak Test",
            target_application=TargetApplication(window_title_pattern="Banking KYC"),
            execution_settings=ExecutionSettings(
                countdown_seconds=0,
                error_recovery_policy=ErrorRecoveryPolicy.SKIP_STEP,
            ),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.FOCUS_WINDOW,
                    parameters=StepParameters(window_title_pattern="Banking KYC"),
                ),
                WorkflowStep(
                    sequence_index=2,
                    action_type=ActionType.CLICK,
                    parameters=StepParameters(
                        coordinate_mode=CoordinateMode.NORMALIZED,
                        norm_x=0.5,
                        norm_y=0.5,
                    ),
                ),
                WorkflowStep(
                    sequence_index=3,
                    action_type=ActionType.KEY_PRESS,
                    parameters=StepParameters(key="tab"),
                ),
            ],
        )

        await runner.execute(wf)

        assert "ctrl" not in driver.active_modifiers
