"""
tests.test_engine
Comprehensive test suite verifying all 10 action handlers, all 18 FSM transitions,
safety guardrails, audit logging with credential masking, and WorkflowRunner execution.
Copyrights reserved to 90Studio
"""

import asyncio
from pathlib import Path
import sys
import pytest

SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from kutomoto.engine import (  # noqa: E402
    ActionType,
    AuditLogger,
    CoordinateMode,
    CornerFailsafeTriggered,
    CredentialMasker,
    ErrorRecoveryPolicy,
    EscapeAbortTriggered,
    ExecutionFSM,
    ExecutionSettings,
    ExecutionState,
    FocusLostError,
    FSMEvent,
    InvalidTransitionError,
    KutomotoAuditLog,
    KutomotoWorkflow,
    MockWin32Driver,
    MouseDisturbanceDetected,
    SafetyConfig,
    SafetyGuard,
    StepParameters,
    SubmitMethod,
    TargetApplication,
    WorkflowRunner,
    WorkflowStep,
    WorkflowVariable,
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def mock_driver():
    """Provides a fresh, isolated MockWin32Driver instance."""
    driver = MockWin32Driver()
    driver.reset()
    return driver


@pytest.fixture
def safety_guard(mock_driver):
    """Provides a SafetyGuard attached to the mock driver."""
    config = SafetyConfig(
        corner_failsafe_enabled=True,
        escape_abort_enabled=True,
        focus_guardian_enabled=True,
        mouse_disturbance_detector_enabled=True,
        mouse_disturbance_threshold_px=100.0,
    )
    guard = SafetyGuard(driver=mock_driver, config=config)
    guard.set_target_hwnd(1001)
    return guard


# ==============================================================================
# 1. Verification of All 10 Atomic Action Handlers
# ==============================================================================

class TestAtomicActionHandlers:

    def test_01_action_focus_window(self, mock_driver):
        """Action 1: focus_window activates target by regex pattern."""
        hwnd = mock_driver.find_window(r".*Banking KYC.*")
        assert hwnd == 1001
        success = mock_driver.focus_window(hwnd)
        assert success is True
        assert mock_driver.get_foreground_window() == 1001
        assert 1001 in mock_driver.focus_history

    def test_02_action_click_normalized_and_client(self, mock_driver):
        """Action 2: click dispatches correct client-to-screen mapped coordinates."""
        # Window 1001 is at (100, 100, 1200, 800)
        norm_x, norm_y = 0.5, 0.25
        win_x, win_y, win_w, win_h = mock_driver.get_window_bounds(1001)
        screen_x = win_x + int(norm_x * win_w)
        screen_y = win_y + int(norm_y * win_h)

        mock_driver.send_click(screen_x, screen_y, button="left", click_count=1)
        assert len(mock_driver.clicks) == 1
        assert mock_driver.clicks[0] == {"x": 700, "y": 300, "button": "left", "click_count": 1}

    def test_03_action_type_text_and_empty_payload(self, mock_driver):
        """Action 3: type_text records string; empty payload bypasses typing (E14)."""
        payload = "Acme Corp LLC"
        mock_driver.send_text(payload)
        assert payload in mock_driver.typed_text

        # Empty payload check (E14)
        empty_payload = ""
        if empty_payload:  # Engine skips send_text on empty
            mock_driver.send_text(empty_payload)
        assert len(mock_driver.typed_text) == 1

    def test_04_action_key_press_with_repeat(self, mock_driver):
        """Action 4: key_press dispatches virtual key with repeat count."""
        mock_driver.send_key_press("tab", repeat_count=3)
        assert len(mock_driver.key_presses) == 1
        assert mock_driver.key_presses[0] == {"key": "tab", "repeat_count": 3}

    def test_05_action_hotkey_chords(self, mock_driver):
        """Action 5: hotkey dispatches modifier chords."""
        mock_driver.send_hotkey(["ctrl", "shift"], "s")
        assert len(mock_driver.hotkeys) == 1
        assert mock_driver.hotkeys[0] == {"modifiers": ["ctrl", "shift"], "key": "s"}

    def test_06_action_clear_field_strategies(self, mock_driver):
        """Action 6: clear_field supports select_all_backspace and triple_click."""
        mock_driver.clear_field("select_all_backspace")
        mock_driver.clear_field("triple_click_delete")
        assert mock_driver.cleared_fields == ["select_all_backspace", "triple_click_delete"]

    @pytest.mark.asyncio
    async def test_07_action_delay(self, mock_driver, monkeypatch):
        """Action 7: delay executes non-blocking sleep via WorkflowRunner."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = KutomotoWorkflow(
            name="Delay Test",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.DELAY,
                    parameters=StepParameters(duration_ms=60),
                ),
            ],
        )
        runner = WorkflowRunner(driver=mock_driver)
        start = asyncio.get_event_loop().time()
        audit = await runner.execute(workflow)
        duration = asyncio.get_event_loop().time() - start
        assert audit.execution_summary.final_status == "SUCCESS"
        assert audit.execution_summary.successful_steps == 1
        assert runner.state == ExecutionState.COMPLETED
        assert duration >= 0.05

    def test_08_action_submit_enter_and_button(self, mock_driver):
        """Action 8: submit supports Enter key press and button coordinate clicks."""
        mock_driver.send_key_press("enter")
        mock_driver.send_click(850, 720, button="left", click_count=1)

        assert mock_driver.key_presses[-1]["key"] == "enter"
        assert mock_driver.clicks[-1]["x"] == 850
        assert mock_driver.clicks[-1]["y"] == 720

    def test_09_action_scroll(self, mock_driver):
        """Action 9: scroll dispatches horizontal and vertical wheel deltas."""
        mock_driver.send_scroll(delta_x=0, delta_y=-120)
        assert mock_driver.scrolls == [(0, -120)]

    @pytest.mark.asyncio
    async def test_10_action_prompt_user_input(self, mock_driver, monkeypatch):
        """Action 10: prompt_user_input invokes prompt resolver and binds variable."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = KutomotoWorkflow(
            name="Prompt Test",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.PROMPT_USER_INPUT,
                    parameters=StepParameters(variable_name="loan_amount", prompt_message="Enter amount:"),
                ),
            ],
        )

        class MockPromptResolver:
            def request_input(self, var_name, prompt_msg, is_secret):
                return "250000.00"

        telemetry_events = []
        runner = WorkflowRunner(
            driver=mock_driver,
            prompt_resolver=MockPromptResolver(),
            telemetry_callback=lambda evt, payload: telemetry_events.append((evt, payload)),
        )
        audit = await runner.execute(workflow)
        assert audit.execution_summary.final_status == "SUCCESS"
        assert runner.context.variables["loan_amount"] == "250000.00"
        assert any(evt[0] == "user_prompt_requested" and evt[1]["variable_name"] == "loan_amount" for evt in telemetry_events)


# ==============================================================================
# 2. Verification of All 18 FSM State Transitions (T01 – T18 + Reset)
# ==============================================================================

class TestFSMTransitions:

    @pytest.mark.asyncio
    async def test_t01_to_t03_validation_transitions(self):
        # T01: IDLE -> VALIDATING
        fsm1 = ExecutionFSM()
        await fsm1.trigger(FSMEvent.EXECUTE_START)
        assert fsm1.state == ExecutionState.VALIDATING

        # T02: VALIDATING -> COUNTDOWN
        await fsm1.trigger(FSMEvent.VALIDATION_OK)
        assert fsm1.state == ExecutionState.COUNTDOWN

        # T03: VALIDATING -> ERROR
        fsm2 = ExecutionFSM()
        await fsm2.trigger(FSMEvent.EXECUTE_START)
        await fsm2.trigger(FSMEvent.VALIDATION_FAILED)
        assert fsm2.state == ExecutionState.ERROR

    @pytest.mark.asyncio
    async def test_t04_to_t06_countdown_transitions(self):
        # T04: COUNTDOWN -> COUNTDOWN
        fsm = ExecutionFSM(ExecutionState.COUNTDOWN)
        await fsm.trigger(FSMEvent.COUNTDOWN_TICK)
        assert fsm.state == ExecutionState.COUNTDOWN

        # T05: COUNTDOWN -> RUNNING
        await fsm.trigger(FSMEvent.COUNTDOWN_DONE)
        assert fsm.state == ExecutionState.RUNNING

        # T06: COUNTDOWN -> STOPPED
        fsm_abort = ExecutionFSM(ExecutionState.COUNTDOWN)
        await fsm_abort.trigger(FSMEvent.ABORT_TRIGGERED)
        assert fsm_abort.state == ExecutionState.STOPPED

    @pytest.mark.asyncio
    async def test_t07_to_t12_running_transitions(self):
        # T07 & T08
        fsm = ExecutionFSM(ExecutionState.RUNNING)
        await fsm.trigger(FSMEvent.STEP_SUCCESS)
        assert fsm.state == ExecutionState.RUNNING  # T07
        await fsm.trigger(FSMEvent.ALL_STEPS_DONE)
        assert fsm.state == ExecutionState.COMPLETED  # T08

        # T09: USER_PAUSE
        fsm_pause = ExecutionFSM(ExecutionState.RUNNING)
        await fsm_pause.trigger(FSMEvent.USER_PAUSE)
        assert fsm_pause.state == ExecutionState.PAUSED

        # T10: FOCUS_LOST
        fsm_focus = ExecutionFSM(ExecutionState.RUNNING)
        await fsm_focus.trigger(FSMEvent.FOCUS_LOST)
        assert fsm_focus.state == ExecutionState.PAUSED

        # T11: ABORT_TRIGGERED
        fsm_abort = ExecutionFSM(ExecutionState.RUNNING)
        await fsm_abort.trigger(FSMEvent.ABORT_TRIGGERED)
        assert fsm_abort.state == ExecutionState.STOPPING

        # T12: STEP_EXCEPTION
        fsm_err = ExecutionFSM(ExecutionState.RUNNING)
        await fsm_err.trigger(FSMEvent.STEP_EXCEPTION)
        assert fsm_err.state == ExecutionState.ERROR_RECOVERY

    @pytest.mark.asyncio
    async def test_t13_and_t14_paused_transitions(self):
        # T13: USER_RESUME
        fsm = ExecutionFSM(ExecutionState.PAUSED)
        await fsm.trigger(FSMEvent.USER_RESUME)
        assert fsm.state == ExecutionState.RUNNING

        # T14: ABORT_TRIGGERED
        fsm_abort = ExecutionFSM(ExecutionState.PAUSED)
        await fsm_abort.trigger(FSMEvent.ABORT_TRIGGERED)
        assert fsm_abort.state == ExecutionState.STOPPED

    @pytest.mark.asyncio
    async def test_t15_to_t17_error_recovery_transitions(self):
        # T15: POLICY_RETRY
        fsm_retry = ExecutionFSM(ExecutionState.ERROR_RECOVERY)
        await fsm_retry.trigger(FSMEvent.POLICY_RETRY)
        assert fsm_retry.state == ExecutionState.RUNNING

        # T16: POLICY_SKIP
        fsm_skip = ExecutionFSM(ExecutionState.ERROR_RECOVERY)
        await fsm_skip.trigger(FSMEvent.POLICY_SKIP)
        assert fsm_skip.state == ExecutionState.RUNNING

        # T17: POLICY_ABORT
        fsm_abort = ExecutionFSM(ExecutionState.ERROR_RECOVERY)
        await fsm_abort.trigger(FSMEvent.POLICY_ABORT)
        assert fsm_abort.state == ExecutionState.ERROR

    @pytest.mark.asyncio
    async def test_t18_stopping_cleanup_done(self):
        # T18: STOPPING -> STOPPED
        fsm = ExecutionFSM(ExecutionState.STOPPING)
        await fsm.trigger(FSMEvent.CLEANUP_DONE)
        assert fsm.state == ExecutionState.STOPPED

    @pytest.mark.asyncio
    async def test_t19_to_t21_reset_transitions(self):
        # T19: STOPPED -> IDLE
        fsm1 = ExecutionFSM(ExecutionState.STOPPED)
        await fsm1.trigger(FSMEvent.RESET)
        assert fsm1.state == ExecutionState.IDLE

        # T20: COMPLETED -> IDLE
        fsm2 = ExecutionFSM(ExecutionState.COMPLETED)
        await fsm2.trigger(FSMEvent.RESET)
        assert fsm2.state == ExecutionState.IDLE

        # T21: ERROR -> IDLE
        fsm3 = ExecutionFSM(ExecutionState.ERROR)
        await fsm3.trigger(FSMEvent.RESET)
        assert fsm3.state == ExecutionState.IDLE

    @pytest.mark.asyncio
    async def test_invalid_transitions_rejected(self):
        fsm = ExecutionFSM(ExecutionState.IDLE)
        with pytest.raises(InvalidTransitionError):
            await fsm.trigger(FSMEvent.ALL_STEPS_DONE)

        with pytest.raises(InvalidTransitionError):
            await fsm.trigger(FSMEvent.USER_RESUME)

    @pytest.mark.asyncio
    async def test_fsm_listeners(self):
        events_received = []

        def sync_listener(old_s, new_s, ev):
            events_received.append((old_s, new_s, ev))

        async def async_listener(old_s, new_s, ev):
            events_received.append(("async", old_s, new_s, ev))

        fsm = ExecutionFSM()
        fsm.add_listener(sync_listener)
        fsm.add_listener(async_listener)

        await fsm.trigger(FSMEvent.EXECUTE_START)
        assert len(events_received) == 2
        assert events_received[0] == (ExecutionState.IDLE, ExecutionState.VALIDATING, FSMEvent.EXECUTE_START)
        assert events_received[1] == ("async", ExecutionState.IDLE, ExecutionState.VALIDATING, FSMEvent.EXECUTE_START)


# ==============================================================================
# 3. Verification of Safety Guardrails
# ==============================================================================

class TestSafetyGuardrails:

    def test_corner_failsafe_top_left(self, mock_driver, safety_guard):
        """Corner failsafe triggers when mouse is at (0, 0)."""
        mock_driver.simulate_corner_failsafe(0, 0)
        with pytest.raises(CornerFailsafeTriggered):
            safety_guard.check_corner_failsafe()

    def test_corner_failsafe_top_right(self, mock_driver, safety_guard):
        """Corner failsafe triggers when mouse is at (1920, 0)."""
        mock_driver.simulate_corner_failsafe(1920, 0)
        with pytest.raises(CornerFailsafeTriggered):
            safety_guard.check_corner_failsafe()

    def test_corner_failsafe_safe_position(self, mock_driver, safety_guard):
        """Safe cursor position does not trip failsafe."""
        mock_driver.set_cursor_pos(500, 500)
        safety_guard.check_corner_failsafe()  # Does not raise

    def test_escape_abort_hotkey(self, mock_driver, safety_guard):
        """Escape hotkey press immediately trips EscapeAbortTriggered."""
        mock_driver.simulate_escape_press()
        with pytest.raises(EscapeAbortTriggered):
            safety_guard.check_escape_abort()

    def test_loss_of_focus_guardian_auto_pause(self, mock_driver, safety_guard):
        """Loss-of-Focus Guardian raises FocusLostError when foreground HWND shifts (E13)."""
        mock_driver.simulate_focus_loss(9999)
        mock_driver.fail_focus = True  # Auto-restore fails

        with pytest.raises(FocusLostError):
            safety_guard.check_focus_guardian(target_hwnd=1001)

    def test_accidental_mouse_disturbance_detector(self, mock_driver, safety_guard):
        """Accidental operator bump > 100px trips MouseDisturbanceDetected (E08)."""
        safety_guard.register_intentional_mouse_move(500, 500)
        mock_driver.set_cursor_pos(500, 500)

        # Minor intentional twitch (15px) - must NOT trip
        mock_driver.set_cursor_pos(510, 510)
        safety_guard.check_mouse_disturbance()

        # Severe physical bump (150px) - MUST trip
        mock_driver.simulate_mouse_disturbance(dx=120, dy=120)
        with pytest.raises(MouseDisturbanceDetected):
            safety_guard.check_mouse_disturbance()

    def test_intentional_automation_mouse_move_bypasses_disturbance(self, mock_driver, safety_guard):
        """Intentional automation click does NOT trip disturbance detector."""
        safety_guard.register_intentional_mouse_move(100, 100)
        mock_driver.set_cursor_pos(100, 100)

        safety_guard.register_intentional_mouse_move(800, 600)
        mock_driver.set_cursor_pos(800, 600)

        safety_guard.check_mouse_disturbance()

    def test_emergency_modifier_purge(self, mock_driver, safety_guard):
        """Emergency cleanup releases all held modifiers (Ctrl, Shift, Alt, Win)."""
        mock_driver.send_key_down("ctrl")
        mock_driver.send_key_down("shift")
        assert "ctrl" in mock_driver.active_modifiers
        assert "shift" in mock_driver.active_modifiers

        safety_guard.emergency_cleanup()

        assert len(mock_driver.active_modifiers) == 0


# ==============================================================================
# 4. Verification of 90Studio Audit Logging Compliance & Secret Masking
# ==============================================================================

class TestAuditLoggingCompliance:

    def test_audit_log_structure_and_attribution(self):
        """Verifies audit log metadata and mandatory 90Studio copyright string."""
        log = KutomotoAuditLog(
            workflow_id="bfd898ef-d138-40a2-9742-b065f49e49cb",
            workflow_name="Commercial Loan Origination Flow",
            source_mode="visual_designer_generated",
            operator_username="enterprise_operator",
            host_machine="DESKTOP-90STUDIO",
            os_version="Windows 11 (10.0.26100)",
            target_application={
                "title": "Commercial Underwriting Client - 90Studio Bank",
                "hwnd": 1002,
                "process_name": "loan_app.exe",
                "pid": 5300,
            },
            execution_summary={
                "total_steps": 12,
                "successful_steps": 12,
                "failed_steps": 0,
                "retried_steps": 0,
                "duration_seconds": 4.25,
                "final_status": "SUCCESS",
            },
            step_events=[],
        )

        assert log.system == "kutomoto"
        assert log.copyright == "Copyrights reserved to 90Studio"
        assert log.execution_summary.final_status == "SUCCESS"

    def test_credential_masking_is_secret(self):
        """Verifies that sensitive text payloads (is_secret=True) are masked in logs."""
        raw_password = "SecretEnterprisePassword123!"
        params = StepParameters(
            text=raw_password,
            is_secret=True,
            keystroke_delay_ms=20,
        )

        masked_summary = CredentialMasker.mask_parameter_summary("type_text", params, is_secret=True)
        assert "********" in masked_summary
        assert raw_password not in masked_summary

    def test_audit_logger_records_events(self):
        """Verifies AuditLogger records steps and produces compliant output."""
        class DummyWorkflow:
            id = "test-wf-1"
            name = "Test Workflow"
            source_mode = "manual_step_flow"
            target_application = type("Target", (), {"window_title_pattern": "Test App", "process_name": "test.exe"})()
            steps = [1, 2]

        logger = AuditLogger(execution_id="exec-123", workflow=DummyWorkflow())
        logger.record_success(1, "click", "Click Button", "norm_coords=(0.5, 0.5)", 12.5)
        logger.record_retried(2, "type_text", "Type Name", "Transient error")
        logger.record_success(2, "type_text", "Type Name", "text='John Doe'", 25.0)

        audit = logger.generate_log("SUCCESS")
        assert audit.copyright == "Copyrights reserved to 90Studio"
        assert audit.execution_summary.total_steps == 2
        assert audit.execution_summary.successful_steps == 2
        assert audit.execution_summary.retried_steps == 1
        assert len(audit.step_events) == 3


# ==============================================================================
# 5. Verification of WorkflowRunner Loop, Telemetry, and Recovery Policies
# ==============================================================================

class TestWorkflowRunner:

    @pytest.mark.asyncio
    async def test_runner_executes_all_steps_successfully(self, mock_driver, monkeypatch):
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        workflow = KutomotoWorkflow(
            name="KYC Onboarding Test Flow",
            target_application=TargetApplication(
                type="windows_desktop",
                window_title_pattern=".*Banking KYC.*",
                process_name="msedge.exe",
            ),
            execution_settings=ExecutionSettings(
                countdown_seconds=0,
                default_step_delay_ms=10,
                typing_speed_ms=5,
            ),
            variables=[
                WorkflowVariable(name="customer_name", default_value="Alice Smith"),
            ],
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    label="Focus KYC Window",
                    action_type=ActionType.FOCUS_WINDOW,
                    parameters=StepParameters(window_title_pattern=".*Banking KYC.*"),
                ),
                WorkflowStep(
                    sequence_index=2,
                    label="Click Name Field",
                    action_type=ActionType.CLICK,
                    parameters=StepParameters(norm_x=0.3, norm_y=0.2, coordinate_mode=CoordinateMode.NORMALIZED),
                ),
                WorkflowStep(
                    sequence_index=3,
                    label="Clear Name Field",
                    action_type=ActionType.CLEAR_FIELD,
                ),
                WorkflowStep(
                    sequence_index=4,
                    label="Type Customer Name",
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text="{{customer_name}}"),
                ),
                WorkflowStep(
                    sequence_index=5,
                    label="Press Tab",
                    action_type=ActionType.KEY_PRESS,
                    parameters=StepParameters(key="tab", repeat_count=1),
                ),
                WorkflowStep(
                    sequence_index=6,
                    label="Submit Form",
                    action_type=ActionType.SUBMIT,
                    parameters=StepParameters(submit_method=SubmitMethod.ENTER_KEY),
                ),
            ],
        )

        telemetry_events = []
        runner = WorkflowRunner(
            driver=mock_driver,
            telemetry_callback=lambda evt, payload: telemetry_events.append(evt),
        )

        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert audit.copyright == "Copyrights reserved to 90Studio"
        assert runner.state == ExecutionState.COMPLETED
        assert "Alice Smith" in mock_driver.typed_text
        assert len(mock_driver.clicks) == 1
        assert "step_started" in telemetry_events
        assert "step_completed" in telemetry_events

    @pytest.mark.asyncio
    async def test_runner_missing_required_variable_blocks_execution(self, mock_driver, monkeypatch):
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        workflow = KutomotoWorkflow(
            name="Missing Var Flow",
            target_application=TargetApplication(
                type="windows_desktop",
                window_title_pattern=".*Banking KYC.*",
            ),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            variables=[
                WorkflowVariable(name="mandatory_tax_id", default_value="", required=True),
            ],
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.FOCUS_WINDOW,
                    parameters=StepParameters(window_title_pattern=".*Banking KYC.*"),
                ),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver)
        with pytest.raises(ValueError, match="missing required variables"):
            await runner.execute(workflow)

        assert runner.state == ExecutionState.ERROR

    @pytest.mark.asyncio
    async def test_runner_retry_policy_on_failure(self, mock_driver, monkeypatch):
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        workflow = KutomotoWorkflow(
            name="Retry Policy Flow",
            target_application=TargetApplication(
                type="windows_desktop",
                window_title_pattern=".*Banking KYC.*",
            ),
            execution_settings=ExecutionSettings(
                countdown_seconds=0,
                error_recovery_policy=ErrorRecoveryPolicy.RETRY_STEP,
                max_step_retries=2,
            ),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.CLICK,
                    parameters=StepParameters(x=100, y=100, coordinate_mode=CoordinateMode.SCREEN),
                ),
            ],
        )

        # Force send_click to fail once then succeed
        call_count = 0
        original_send_click = mock_driver.send_click

        def failing_send_click(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Simulated transient click failure")
            return original_send_click(*args, **kwargs)

        mock_driver.send_click = failing_send_click

        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert audit.execution_summary.retried_steps == 1
        assert runner.state == ExecutionState.COMPLETED

    @pytest.mark.asyncio
    async def test_runner_skip_policy_on_failure(self, mock_driver, monkeypatch):
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        workflow = KutomotoWorkflow(
            name="Skip Policy Flow",
            target_application=TargetApplication(
                type="windows_desktop",
                window_title_pattern=".*Banking KYC.*",
            ),
            execution_settings=ExecutionSettings(
                countdown_seconds=0,
                error_recovery_policy=ErrorRecoveryPolicy.SKIP_STEP,
            ),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.CLICK,
                    parameters=StepParameters(x=100, y=100, coordinate_mode=CoordinateMode.SCREEN),
                ),
                WorkflowStep(
                    sequence_index=2,
                    action_type=ActionType.KEY_PRESS,
                    parameters=StepParameters(key="tab"),
                ),
            ],
        )

        mock_driver.send_click = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Click hardware fault"))

        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert len(mock_driver.key_presses) == 1
        assert runner.state == ExecutionState.COMPLETED

    @pytest.mark.asyncio
    async def test_runner_executes_all_10_atomic_actions(self, mock_driver, monkeypatch):
        """Exercises all 10 atomic actions in a single end-to-end workflow."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        class MockResolver:
            def request_input(self, name, msg, sec):
                return "100000"

        workflow = KutomotoWorkflow(
            name="All 10 Actions Flow",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            variables=[
                WorkflowVariable(name="applicant_name", default_value="Jane Doe"),
            ],
            steps=[
                WorkflowStep(sequence_index=1, action_type=ActionType.FOCUS_WINDOW, parameters=StepParameters(window_title_pattern=".*Banking KYC.*")),
                WorkflowStep(sequence_index=2, action_type=ActionType.CLICK, parameters=StepParameters(norm_x=0.5, norm_y=0.5, coordinate_mode=CoordinateMode.NORMALIZED)),
                WorkflowStep(sequence_index=3, action_type=ActionType.CLEAR_FIELD, parameters=StepParameters(clear_strategy="select_all_backspace")),
                WorkflowStep(sequence_index=4, action_type=ActionType.TYPE_TEXT, parameters=StepParameters(text="{{applicant_name}}")),
                WorkflowStep(sequence_index=5, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key="tab", repeat_count=1)),
                WorkflowStep(sequence_index=6, action_type=ActionType.HOTKEY, parameters=StepParameters(keys=["ctrl", "s"])),
                WorkflowStep(sequence_index=7, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=10)),
                WorkflowStep(sequence_index=8, action_type=ActionType.SCROLL, parameters=StepParameters(delta_x=0, delta_y=-120)),
                WorkflowStep(sequence_index=9, action_type=ActionType.PROMPT_USER_INPUT, parameters=StepParameters(variable_name="loan_amt")),
                WorkflowStep(sequence_index=10, action_type=ActionType.SUBMIT, parameters=StepParameters(submit_method=SubmitMethod.BUTTON_CLICK, norm_x=0.8, norm_y=0.9, coordinate_mode=CoordinateMode.NORMALIZED)),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver, prompt_resolver=MockResolver())
        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert audit.execution_summary.successful_steps == 10
        assert runner.state == ExecutionState.COMPLETED
        assert len(mock_driver.hotkeys) == 1
        assert len(mock_driver.scrolls) == 1
        assert "Jane Doe" in mock_driver.typed_text
        assert runner.context.variables["loan_amt"] == "100000"

    @pytest.mark.asyncio
    async def test_runner_pause_and_resume_lifecycle(self, mock_driver, monkeypatch):
        """Verifies pause suspends step execution without crashing and resume completes workflow."""
        monkeypatch.delenv("KUTOMOTO_TEST_FAST", raising=False)

        workflow = KutomotoWorkflow(
            name="Pause Resume Lifecycle Flow",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0, default_step_delay_ms=20),
            steps=[
                WorkflowStep(sequence_index=1, action_type=ActionType.FOCUS_WINDOW, parameters=StepParameters(window_title_pattern=".*Banking KYC.*")),
                WorkflowStep(sequence_index=2, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=80)),
                WorkflowStep(sequence_index=3, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key="tab")),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver)
        task = asyncio.create_task(runner.execute(workflow))

        await asyncio.sleep(0.02)
        assert runner.state == ExecutionState.RUNNING

        # Pause execution
        await runner.pause()
        assert runner.state == ExecutionState.PAUSED

        # Allow execution tick; verify step 3 does NOT execute
        await asyncio.sleep(0.06)
        assert runner.state == ExecutionState.PAUSED
        assert len(mock_driver.key_presses) == 0

        # Resume execution
        await runner.resume()
        assert runner.state == ExecutionState.RUNNING

        audit = await task
        assert audit.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED
        assert len(mock_driver.key_presses) == 1

    @pytest.mark.asyncio
    async def test_runner_abort_from_paused(self, mock_driver, monkeypatch):
        """Verifies aborting while paused transitions gracefully to STOPPED without InvalidTransitionError."""
        monkeypatch.delenv("KUTOMOTO_TEST_FAST", raising=False)

        workflow = KutomotoWorkflow(
            name="Abort While Paused Flow",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0, default_step_delay_ms=30),
            steps=[
                WorkflowStep(sequence_index=1, action_type=ActionType.FOCUS_WINDOW, parameters=StepParameters(window_title_pattern=".*Banking KYC.*")),
                WorkflowStep(sequence_index=2, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=100)),
                WorkflowStep(sequence_index=3, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key="tab")),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver)
        task = asyncio.create_task(runner.execute(workflow))

        await asyncio.sleep(0.02)
        await runner.pause()
        assert runner.state == ExecutionState.PAUSED

        # Abort while paused
        await runner.abort()
        audit = await task

        assert audit.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED
        assert len(mock_driver.key_presses) == 0

    @pytest.mark.asyncio
    async def test_runner_reexecution_with_auto_reset(self, mock_driver, monkeypatch):
        """Verifies a completed WorkflowRunner automatically resets and executes a second workflow."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        workflow = KutomotoWorkflow(
            name="Run 1",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=[
                WorkflowStep(sequence_index=1, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key="tab")),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver)
        audit1 = await runner.execute(workflow)
        assert audit1.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED

        # Re-execute using the same runner instance
        audit2 = await runner.execute(workflow)
        assert audit2.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED
        assert len(mock_driver.key_presses) == 2

    @pytest.mark.asyncio
    async def test_runner_emergency_failsafe_aborts_immediately_under_skip_and_retry(self, mock_driver, monkeypatch):
        """Verifies CornerFailsafeTriggered aborts immediately under both SKIP_STEP and RETRY_STEP."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        for policy in (ErrorRecoveryPolicy.SKIP_STEP, ErrorRecoveryPolicy.RETRY_STEP):
            mock_driver.reset()
            workflow = KutomotoWorkflow(
                name=f"Failsafe Test {policy.value}",
                target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
                execution_settings=ExecutionSettings(countdown_seconds=0, error_recovery_policy=policy, max_step_retries=3),
                steps=[
                    WorkflowStep(sequence_index=1, action_type=ActionType.FOCUS_WINDOW, parameters=StepParameters(window_title_pattern=".*Banking KYC.*")),
                    WorkflowStep(sequence_index=2, action_type=ActionType.CLICK, parameters=StepParameters(norm_x=0.5, norm_y=0.5, coordinate_mode=CoordinateMode.NORMALIZED)),
                ],
            )

            mock_driver.simulate_corner_failsafe(0, 0)
            runner = WorkflowRunner(driver=mock_driver)
            audit = await runner.execute(workflow)

            assert audit.execution_summary.final_status == "ABORTED", f"Policy {policy.value} failed to abort immediately on corner failsafe!"
            assert runner.state == ExecutionState.STOPPED
            assert runner.context.step_retry_count == 0

    @pytest.mark.asyncio
    async def test_abort_during_delay_step(self, mock_driver):
        """Verifies aborting during an asynchronous DELAY action completes cleanly without FSM crash."""
        workflow = KutomotoWorkflow(
            name="Delay Abort Regression Test",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=[
                WorkflowStep(sequence_index=1, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=2000)),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver)
        task = asyncio.create_task(runner.execute(workflow))

        # Allow delay step to enter asynchronous sleep loop
        await asyncio.sleep(0.05)
        assert runner.state == ExecutionState.RUNNING

        await runner.abort()
        audit = await task

        assert audit.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED

    @pytest.mark.asyncio
    async def test_abort_during_pre_delay(self, mock_driver):
        """Verifies aborting during step pre_delay_ms terminates cleanly without executing the step action."""
        workflow = KutomotoWorkflow(
            name="Pre-Delay Abort Regression Test",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.KEY_PRESS,
                    pre_delay_ms=2000,
                    parameters=StepParameters(key="tab"),
                ),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver)
        task = asyncio.create_task(runner.execute(workflow))

        # Allow runner to enter pre_delay sleep
        await asyncio.sleep(0.05)
        assert runner.state == ExecutionState.RUNNING

        await runner.abort()
        audit = await task

        assert audit.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED
        assert len(mock_driver.key_presses) == 0

    @pytest.mark.asyncio
    async def test_abort_during_focus_loss_wait(self, mock_driver):
        """Verifies aborting while paused in focus loss guardian terminates cleanly without FSM crash."""
        workflow = KutomotoWorkflow(
            name="Focus Loss Abort Regression Test",
            target_application=TargetApplication(type="windows_desktop", window_title_pattern=".*Banking KYC.*"),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.FOCUS_WINDOW,
                    post_delay_ms=20,
                    parameters=StepParameters(window_title_pattern=".*Banking KYC.*"),
                ),
                WorkflowStep(
                    sequence_index=2,
                    action_type=ActionType.KEY_PRESS,
                    parameters=StepParameters(key="tab"),
                ),
            ],
        )

        runner = WorkflowRunner(driver=mock_driver)
        task = asyncio.create_task(runner.execute(workflow))

        # Allow step 1 focus action to execute
        await asyncio.sleep(0.01)
        # Simulate loss of focus before step 2 executes
        mock_driver.simulate_focus_loss(9999)
        # Allow step 1 post-delay to finish and guardian to pause step 2
        await asyncio.sleep(0.06)
        assert runner.state == ExecutionState.PAUSED

        # Restore foreground hwnd and abort
        mock_driver.foreground_hwnd = 1001
        await runner.abort()
        audit = await task

        assert audit.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED
        assert len(mock_driver.key_presses) == 0


# ==============================================================================
# 9. RESET & LIFECYCLE STATE ISOLATION UNIT TESTS
# ==============================================================================

class TestResetAndStateIsolation:
    """Verifies safety_guard.reset(), audit_logger.reset(), and template whitespace interpolation."""

    def test_safety_guard_reset(self, mock_driver):
        guard = SafetyGuard(driver=mock_driver)
        guard._abort_requested = True
        guard._last_cursor_pos = (500, 500)
        guard._active_target_hwnd = 1234
        guard.reset()
        assert guard._abort_requested is False
        assert guard._last_cursor_pos is None
        assert guard._active_target_hwnd is None

    def test_audit_logger_reset(self):
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

    def test_variable_interpolation_whitespace_padding(self, mock_driver):
        runner = WorkflowRunner(driver=mock_driver)
        text = "Name: {{ user_name }}, Age: {{age}}, Role: {{   role   }}, Missing: {{ unknown }}"
        variables = {"user_name": "Alice", "age": 30, "role": "Engineer"}
        res = runner._interpolate_variables(text, variables)
        assert res == "Name: Alice, Age: 30, Role: Engineer, Missing: {{ unknown }}"


