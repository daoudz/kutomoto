"""
tests.test_roundtrip_execution_challenge
Adversarial Empirical Challenge Suite for Milestone 3 Iteration 2:
Empirical round-trip execution verification:
1. Multi-step Enterprise Banking KYC form execution (click_to_tab=False and True).
2. Multi-step Enterprise Telecom SIM Provisioning form execution (click_to_tab=False and True).
3. Field typing sequence and payload integrity verification.
4. Checkbox preservation (not bypassed by Tab navigation).
5. Button click preservation (not pruned by peephole optimizer).
6. Emergency Escape abort and corner failsafe operation during compiled workflow execution.
7. Settling delay (pre_delay_ms) timing preservation and empirical latency verification.
8. Dense chained action stress test under peephole optimization.

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

from kutomoto.designer.compiler import compile_visual_layout_to_workflow  # noqa: E402
from kutomoto.designer.schema import (  # noqa: E402
    BoxGeometry,
    BoxTiming,
    CanvasDimensions,
    DesignerActionType,
    ExecutionSettingsSpec,
    NavigationAction,
    PeepholeOptimizationConfig,
    TargetApplicationSpec,
    VisualBox,
    VisualFormLayout,
)
from kutomoto.engine.fsm import ExecutionState  # noqa: E402
from kutomoto.engine.runner import WorkflowRunner  # noqa: E402
from kutomoto.engine.safety import MockWin32Driver  # noqa: E402
from kutomoto.engine.schema import ActionType, KutomotoWorkflow  # noqa: E402


@pytest.fixture
def mock_driver():
    """Provides a fresh, isolated MockWin32Driver instance with registered windows."""
    driver = MockWin32Driver()
    driver.reset()
    # Pre-register Telecom SIM provisioning window (hwnd: 1003)
    driver.windows[1003] = {
        "title": "Telecom SIM Activation Terminal - 90Studio",
        "process_name": "sim_provision.exe",
        "pid": 6000,
        "rect": (100, 100, 1200, 800),
        "is_iconic": False,
        "is_window": True,
    }
    return driver


# ==============================================================================
# 1. Banking KYC Multi-Step Form Round-Trip Execution
# ==============================================================================

class TestBankingKYCRoundTripExecution:
    """Verifies round-trip compilation and execution of realistic Banking KYC forms."""

    def _build_banking_kyc_layout(self, click_to_tab: bool) -> VisualFormLayout:
        return VisualFormLayout(
            name="Banking KYC Customer Onboarding",
            target_application=TargetApplicationSpec(
                window_title_pattern=".*Banking KYC.*",
                process_name="msedge.exe",
            ),
            canvas=CanvasDimensions(width=1200, height=800),
            execution_settings=ExecutionSettingsSpec(
                countdown_seconds=0,
                default_step_delay_ms=10,
            ),
            optimization=PeepholeOptimizationConfig(
                enabled=True,
                click_to_tab=click_to_tab,
            ),
            boxes=[
                VisualBox(
                    name="first_name",
                    label="Customer First Name",
                    geometry=BoxGeometry(x=100, y=100, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="Alexander",
                    navigation=NavigationAction.TAB,
                    clear_before=True,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="last_name",
                    label="Customer Last Name",
                    geometry=BoxGeometry(x=100, y=150, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="Hamilton",
                    navigation=NavigationAction.TAB,
                    clear_before=True,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="dob",
                    label="Date of Birth",
                    geometry=BoxGeometry(x=100, y=200, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="1980-01-11",
                    navigation=NavigationAction.TAB,
                    clear_before=True,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="ssn_tax_id",
                    label="SSN / Tax Identification Number",
                    geometry=BoxGeometry(x=100, y=250, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="987-65-4321",
                    navigation=NavigationAction.TAB,
                    clear_before=True,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="annual_income",
                    label="Stated Annual Income",
                    geometry=BoxGeometry(x=100, y=300, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="150000",
                    navigation=NavigationAction.TAB,
                    clear_before=True,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="pep_declaration",
                    label="Politically Exposed Person (PEP) Checkbox",
                    geometry=BoxGeometry(x=100, y=350, width=24, height=24),
                    action_type=DesignerActionType.CHECKBOX,
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="id_upload_browse",
                    label="Browse Government ID Document Button",
                    geometry=BoxGeometry(x=100, y=400, width=120, height=35),
                    action_type=DesignerActionType.CLICK,
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="terms_consent",
                    label="Terms and Conditions Consent Checkbox",
                    geometry=BoxGeometry(x=100, y=450, width=24, height=24),
                    action_type=DesignerActionType.CHECKBOX,
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="submit_application",
                    label="Submit KYC Application Button",
                    geometry=BoxGeometry(x=100, y=500, width=150, height=40),
                    action_type=DesignerActionType.SUBMIT,
                    navigation=NavigationAction.NONE,
                    post_delay_ms=0,
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_roundtrip_banking_kyc_click_to_tab_false(self, mock_driver, monkeypatch):
        """Banking KYC form execution with click_to_tab=False: all text focus clicks and action clicks occur."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        layout = self._build_banking_kyc_layout(click_to_tab=False)
        workflow = compile_visual_layout_to_workflow(layout)
        assert isinstance(workflow, KutomotoWorkflow)

        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        # 1. Execution status check
        assert audit.execution_summary.final_status == "SUCCESS"
        assert audit.execution_summary.failed_steps == 0
        assert runner.state == ExecutionState.COMPLETED
        assert 1001 in mock_driver.focus_history

        # 2. Sequence verification: text inputs received in exact expected sequence
        expected_texts = ["Alexander", "Hamilton", "1980-01-11", "987-65-4321", "150000"]
        assert mock_driver.typed_text == expected_texts

        # 3. Text field clearing called for all 5 clear_before=True fields
        assert len(mock_driver.cleared_fields) == 5

        # 4. Tab navigation key presses: 8 transitions
        tab_presses = [k for k in mock_driver.key_presses if k["key"] == "tab"]
        assert len(tab_presses) == 8

        # 5. Clicks verification:
        # Window 1001 rect: (100, 100, 1200, 800) -> screen coord = (100 + center_x, 100 + center_y)
        # All 5 text focus clicks + 1 PEP checkbox + 1 Browse button + 1 Terms checkbox + 1 Submit button = 9 clicks
        assert len(mock_driver.clicks) == 9

        # PEP Checkbox: center_x = 100 + 12 = 112, center_y = 350 + 12 = 362 -> screen (212, 462)
        pep_click = mock_driver.clicks[5]
        assert pep_click["x"] == 212 and pep_click["y"] == 462

        # Browse Button: center_x = 100 + 60 = 160, center_y = 400 + 17.5 = 417.5 -> round to 418 -> screen (260, 518)
        browse_click = mock_driver.clicks[6]
        assert browse_click["x"] == 260 and browse_click["y"] == 518

        # Terms Checkbox: center_x = 100 + 12 = 112, center_y = 450 + 12 = 462 -> screen (212, 562)
        terms_click = mock_driver.clicks[7]
        assert terms_click["x"] == 212 and terms_click["y"] == 562

        # Submit Button: center_x = 100 + 75 = 175, center_y = 500 + 20 = 520 -> screen (275, 620)
        submit_click = mock_driver.clicks[8]
        assert submit_click["x"] == 275 and submit_click["y"] == 620

    @pytest.mark.asyncio
    async def test_roundtrip_banking_kyc_click_to_tab_true(self, mock_driver, monkeypatch):
        """
        Banking KYC form execution with click_to_tab=True:
        Auxiliary focus clicks for fields 2-5 are pruned because Tab establishes focus.
        CRITICAL: Checkboxes, click buttons, and submit buttons MUST NOT be pruned!
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        layout = self._build_banking_kyc_layout(click_to_tab=True)
        workflow = compile_visual_layout_to_workflow(layout)

        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        # 1. Execution status check
        assert audit.execution_summary.final_status == "SUCCESS"
        assert audit.execution_summary.failed_steps == 0
        assert runner.state == ExecutionState.COMPLETED

        # 2. Sequence verification: text inputs received in exact expected sequence
        expected_texts = ["Alexander", "Hamilton", "1980-01-11", "987-65-4321", "150000"]
        assert mock_driver.typed_text == expected_texts

        # 3. Clicks count:
        # 1 (first text focus click) + 1 (PEP checkbox) + 1 (Browse button) + 1 (Terms checkbox) + 1 (Submit) = exactly 5 clicks!
        # Auxiliary focus clicks for fields 2, 3, 4, 5 were pruned!
        assert len(mock_driver.clicks) == 5, f"Expected 5 clicks under click_to_tab=True, got {len(mock_driver.clicks)}"

        # 4. Checkboxes are clicked (not bypassed by Tab navigation)
        # Click 1: PEP Checkbox at (212, 462)
        assert mock_driver.clicks[1]["x"] == 212 and mock_driver.clicks[1]["y"] == 462
        # Click 3: Terms Checkbox at (212, 562)
        assert mock_driver.clicks[3]["x"] == 212 and mock_driver.clicks[3]["y"] == 562

        # 5. Buttons are clicked (not pruned by peephole optimizer)
        # Click 2: Browse Button at (260, 518)
        assert mock_driver.clicks[2]["x"] == 260 and mock_driver.clicks[2]["y"] == 518
        # Click 4: Submit Button at (275, 620)
        assert mock_driver.clicks[4]["x"] == 275 and mock_driver.clicks[4]["y"] == 620


# ==============================================================================
# 2. Telecom SIM Provisioning Multi-Step Form Round-Trip Execution
# ==============================================================================

class TestTelecomSIMRoundTripExecution:
    """Verifies round-trip compilation and execution of Telecom SIM Provisioning forms."""

    def _build_telecom_sim_layout(
        self,
        click_to_tab: bool,
        iccid_force_click: bool = False,
    ) -> VisualFormLayout:
        return VisualFormLayout(
            name="Telecom SIM Provisioning Terminal",
            target_application=TargetApplicationSpec(
                window_title_pattern=".*Telecom SIM Activation.*",
                process_name="sim_provision.exe",
            ),
            canvas=CanvasDimensions(width=1200, height=800),
            execution_settings=ExecutionSettingsSpec(
                countdown_seconds=0,
                default_step_delay_ms=10,
            ),
            optimization=PeepholeOptimizationConfig(
                enabled=True,
                click_to_tab=click_to_tab,
            ),
            boxes=[
                VisualBox(
                    name="subscriber_name",
                    label="Subscriber Full Name",
                    geometry=BoxGeometry(x=50, y=50, width=250, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="Elena Rostova",
                    navigation=NavigationAction.TAB,
                    clear_before=True,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="msisdn",
                    label="Mobile Station International Subscriber Directory Number (MSISDN)",
                    geometry=BoxGeometry(x=50, y=100, width=250, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="+14155552671",
                    navigation=NavigationAction.TAB,
                    clear_before=True,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="iccid",
                    label="Integrated Circuit Card Identifier (ICCID)",
                    geometry=BoxGeometry(x=50, y=150, width=250, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="89014103211118510720",
                    navigation=NavigationAction.TAB,
                    force_click=iccid_force_click,
                    clear_before=True,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="imsi",
                    label="International Mobile Subscriber Identity (IMSI)",
                    geometry=BoxGeometry(x=50, y=200, width=250, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="310410123456789",
                    navigation=NavigationAction.TAB,
                    clear_before=True,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="plan_tier_select",
                    label="Select Plan Tier Dropdown",
                    geometry=BoxGeometry(x=50, y=250, width=200, height=30),
                    action_type=DesignerActionType.SELECT,
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="validate_chip_btn",
                    label="Validate SIM Chip Action Button",
                    geometry=BoxGeometry(x=50, y=300, width=140, height=35),
                    action_type=DesignerActionType.CLICK,
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="auto_recharge_check",
                    label="Auto-Recharge Checkbox",
                    geometry=BoxGeometry(x=50, y=350, width=22, height=22),
                    action_type=DesignerActionType.CHECKBOX,
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="esim_profile_check",
                    label="eSIM Profile Activation Checkbox",
                    geometry=BoxGeometry(x=50, y=400, width=22, height=22),
                    action_type=DesignerActionType.CHECKBOX,
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="complete_provision_btn",
                    label="Complete SIM Provisioning Submit Button",
                    geometry=BoxGeometry(x=50, y=450, width=180, height=40),
                    action_type=DesignerActionType.SUBMIT,
                    navigation=NavigationAction.NONE,
                    post_delay_ms=0,
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_roundtrip_telecom_sim_click_to_tab_false(self, mock_driver, monkeypatch):
        """Telecom SIM form execution with click_to_tab=False: all text focus clicks and action clicks occur."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        layout = self._build_telecom_sim_layout(click_to_tab=False)
        workflow = compile_visual_layout_to_workflow(layout)

        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED
        assert 1003 in mock_driver.focus_history

        # Sequence verification: text fields entered in exact author order
        expected_texts = ["Elena Rostova", "+14155552671", "89014103211118510720", "310410123456789"]
        assert mock_driver.typed_text == expected_texts

        # 4 text focus clicks + 1 SELECT click + 1 Action button + 2 Checkboxes + 1 Submit button = 9 clicks
        assert len(mock_driver.clicks) == 9

        # Target window 1003 rect: (100, 100, 1200, 800) -> screen = (100 + center_x, 100 + center_y)
        # Select: center_x = 50 + 100 = 150, center_y = 250 + 15 = 265 -> screen (250, 365)
        assert mock_driver.clicks[4]["x"] == 250 and mock_driver.clicks[4]["y"] == 365
        # Validate button: center_x = 50 + 70 = 120, center_y = 300 + 17.5 = 317.5 -> screen (220, 418)
        assert mock_driver.clicks[5]["x"] == 220 and mock_driver.clicks[5]["y"] == 418
        # Auto-recharge checkbox: center_x = 50 + 11 = 61, center_y = 350 + 11 = 361 -> screen (161, 461)
        assert mock_driver.clicks[6]["x"] == 161 and mock_driver.clicks[6]["y"] == 461
        # eSIM checkbox: center_x = 50 + 11 = 61, center_y = 400 + 11 = 411 -> screen (161, 511)
        assert mock_driver.clicks[7]["x"] == 161 and mock_driver.clicks[7]["y"] == 511
        # Submit button: center_x = 50 + 90 = 140, center_y = 450 + 20 = 470 -> screen (240, 570)
        assert mock_driver.clicks[8]["x"] == 240 and mock_driver.clicks[8]["y"] == 570

    @pytest.mark.asyncio
    async def test_roundtrip_telecom_sim_click_to_tab_true_with_force_click(self, mock_driver, monkeypatch):
        """
        Telecom SIM form execution with click_to_tab=True and iccid_force_click=True:
        - Field 1 (subscriber_name) focus click: preserved (initial anchor).
        - Field 2 (msisdn) focus click: pruned by click_to_tab.
        - Field 3 (iccid) focus click: PRESERVED because force_click=True!
        - Field 4 (imsi) focus click: pruned by click_to_tab.
        - Plan Tier (SELECT): PRESERVED.
        - Validate Chip (CLICK button): PRESERVED.
        - Auto-recharge (CHECKBOX): PRESERVED.
        - eSIM profile (CHECKBOX): PRESERVED.
        - Complete Provisioning (SUBMIT button): PRESERVED.
        Total clicks: exactly 7 clicks!
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        layout = self._build_telecom_sim_layout(click_to_tab=True, iccid_force_click=True)
        workflow = compile_visual_layout_to_workflow(layout)

        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED

        # Sequence verification: all texts received in sequence
        expected_texts = ["Elena Rostova", "+14155552671", "89014103211118510720", "310410123456789"]
        assert mock_driver.typed_text == expected_texts

        # 7 clicks total
        assert len(mock_driver.clicks) == 7, f"Expected 7 clicks, got {len(mock_driver.clicks)}"

        # Click 0: Field 1 anchor click
        assert mock_driver.clicks[0]["x"] == 275 and mock_driver.clicks[0]["y"] == 165
        # Click 1: Field 3 force_click at (100 + 175, 100 + 165) = (275, 265)
        assert mock_driver.clicks[1]["x"] == 275 and mock_driver.clicks[1]["y"] == 265
        # Click 2: SELECT dropdown at (250, 365)
        assert mock_driver.clicks[2]["x"] == 250 and mock_driver.clicks[2]["y"] == 365
        # Click 3: Validate Action button at (220, 418)
        assert mock_driver.clicks[3]["x"] == 220 and mock_driver.clicks[3]["y"] == 418
        # Click 4: Auto-recharge checkbox at (161, 461)
        assert mock_driver.clicks[4]["x"] == 161 and mock_driver.clicks[4]["y"] == 461
        # Click 5: eSIM checkbox at (161, 511)
        assert mock_driver.clicks[5]["x"] == 161 and mock_driver.clicks[5]["y"] == 511
        # Click 6: Submit button at (240, 570)
        assert mock_driver.clicks[6]["x"] == 240 and mock_driver.clicks[6]["y"] == 570


# ==============================================================================
# 3. Settling Delays (pre_delay_ms) Empirical Verification
# ==============================================================================

class TestSettlingDelaysEmpiricalVerification:
    """Empirically verifies that pre_delay_ms is respected during WorkflowRunner execution."""

    @pytest.mark.asyncio
    async def test_settling_delay_respected_click_to_tab_false(self, mock_driver, monkeypatch):
        """Under click_to_tab=False, configured pre_delay_ms is executed on the focus click step."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        layout = VisualFormLayout(
            name="Timing Test Unoptimized",
            target_application=TargetApplicationSpec(window_title_pattern=".*Banking KYC.*"),
            canvas=CanvasDimensions(width=1200, height=800),
            execution_settings=ExecutionSettingsSpec(countdown_seconds=0, default_step_delay_ms=10),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=False),
            boxes=[
                VisualBox(
                    name="f1",
                    geometry=BoxGeometry(x=100, y=100, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="First",
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="f2",
                    geometry=BoxGeometry(x=100, y=150, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="Second",
                    navigation=NavigationAction.NONE,
                    timing=BoxTiming(pre_delay_ms=200),
                    post_delay_ms=0,
                ),
            ],
        )

        wf = compile_visual_layout_to_workflow(layout)
        # Find step with pre_delay_ms == 200
        delayed_steps = [s for s in wf.steps if s.pre_delay_ms == 200]
        assert len(delayed_steps) == 1
        assert delayed_steps[0].action_type == ActionType.CLICK

        runner = WorkflowRunner(driver=mock_driver)
        t0 = time.perf_counter()
        audit = await runner.execute(wf)
        elapsed = time.perf_counter() - t0

        assert audit.execution_summary.final_status == "SUCCESS"
        assert elapsed >= 0.18, f"Expected elapsed >= 0.18s, got {elapsed:.3f}s"
        assert mock_driver.typed_text == ["First", "Second"]

    @pytest.mark.asyncio
    async def test_settling_delay_preserved_and_respected_click_to_tab_true(self, mock_driver, monkeypatch):
        """
        Under click_to_tab=True, when the focus click step is pruned,
        pre_delay_ms MUST be transferred to the subsequent Clear/Type step
        and physically executed by WorkflowRunner.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        layout = VisualFormLayout(
            name="Timing Test Optimized",
            target_application=TargetApplicationSpec(window_title_pattern=".*Banking KYC.*"),
            canvas=CanvasDimensions(width=1200, height=800),
            execution_settings=ExecutionSettingsSpec(countdown_seconds=0, default_step_delay_ms=10),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
            boxes=[
                VisualBox(
                    name="f1",
                    geometry=BoxGeometry(x=100, y=100, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="First",
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="f2",
                    geometry=BoxGeometry(x=100, y=150, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="Second",
                    navigation=NavigationAction.NONE,
                    timing=BoxTiming(pre_delay_ms=200),
                    post_delay_ms=0,
                ),
            ],
        )

        wf = compile_visual_layout_to_workflow(layout)
        # The focus click for f2 is pruned; pre_delay_ms must now be on CLEAR_FIELD
        delayed_steps = [s for s in wf.steps if s.pre_delay_ms == 200]
        assert len(delayed_steps) == 1
        assert delayed_steps[0].action_type == ActionType.CLEAR_FIELD
        assert "f2" in delayed_steps[0].label

        runner = WorkflowRunner(driver=mock_driver)
        t0 = time.perf_counter()
        audit = await runner.execute(wf)
        elapsed = time.perf_counter() - t0

        assert audit.execution_summary.final_status == "SUCCESS"
        assert elapsed >= 0.18, f"Expected elapsed >= 0.18s under click_to_tab=True, got {elapsed:.3f}s"
        assert mock_driver.typed_text == ["First", "Second"]


# ==============================================================================
# 4. Emergency Escape Abort & Corner Failsafe Operational Verification
# ==============================================================================

class TestSafetyGuardrailsInCompiledWorkflows:
    """Verifies that safety guardrails operate correctly during compiled workflow execution."""

    @pytest.mark.asyncio
    async def test_emergency_escape_abort_during_compiled_workflow(self, mock_driver, monkeypatch):
        """
        Emergency Escape abort during compiled Banking KYC execution immediately halts the runner,
        transitions FSM to STOPPED, marks audit ABORTED, and releases all modifiers.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        layout = VisualFormLayout(
            name="Banking KYC Abort Test",
            target_application=TargetApplicationSpec(window_title_pattern=".*Banking KYC.*"),
            canvas=CanvasDimensions(width=1200, height=800),
            execution_settings=ExecutionSettingsSpec(countdown_seconds=0, default_step_delay_ms=10),
            boxes=[
                VisualBox(
                    name="f1",
                    geometry=BoxGeometry(x=100, y=100, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="Step1Text",
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="f2",
                    geometry=BoxGeometry(x=100, y=150, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="Step2Text",
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="submit_btn",
                    geometry=BoxGeometry(x=100, y=200, width=120, height=40),
                    action_type=DesignerActionType.SUBMIT,
                    navigation=NavigationAction.NONE,
                    post_delay_ms=0,
                ),
            ],
        )

        wf = compile_visual_layout_to_workflow(layout)
        runner = WorkflowRunner(driver=mock_driver)

        # Trigger Escape press right before step 3 (clear/type for f1)
        async def on_step_started(event: str, payload: dict):
            if event == "step_started" and payload.get("step_index") == 3:
                mock_driver.simulate_escape_press()

        runner._telemetry_cb = on_step_started
        audit = await runner.execute(wf)

        # Assertions
        assert audit.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED
        # Step 3 was aborted before typing f1, and f2 + submit were never reached
        assert "Step2Text" not in mock_driver.typed_text
        assert not any(c.get("method") == "send_click" and c.get("y") == 320 for c in mock_driver.calls)
        # Emergency cleanup called
        assert any(c.get("method") == "release_all_modifiers" for c in mock_driver.calls)

    @pytest.mark.asyncio
    async def test_corner_failsafe_during_compiled_workflow(self, mock_driver, monkeypatch):
        """
        Moving cursor to (0, 0) triggers CornerFailsafeTriggered, aborting execution immediately.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        layout = VisualFormLayout(
            name="Telecom SIM Corner Failsafe Test",
            target_application=TargetApplicationSpec(window_title_pattern=".*Telecom SIM Activation.*"),
            canvas=CanvasDimensions(width=1200, height=800),
            execution_settings=ExecutionSettingsSpec(countdown_seconds=0, default_step_delay_ms=10),
            boxes=[
                VisualBox(
                    name="msisdn",
                    geometry=BoxGeometry(x=50, y=50, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="+14155552671",
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="iccid",
                    geometry=BoxGeometry(x=50, y=100, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="89014103211118510720",
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="submit",
                    geometry=BoxGeometry(x=50, y=150, width=120, height=40),
                    action_type=DesignerActionType.SUBMIT,
                    navigation=NavigationAction.NONE,
                    post_delay_ms=0,
                ),
            ],
        )

        wf = compile_visual_layout_to_workflow(layout)
        runner = WorkflowRunner(driver=mock_driver)

        # Trigger corner failsafe (0, 0) at step 3
        async def on_step_started(event: str, payload: dict):
            if event == "step_started" and payload.get("step_index") == 3:
                mock_driver.simulate_corner_failsafe(0, 0)

        runner._telemetry_cb = on_step_started
        audit = await runner.execute(wf)

        # Assertions
        assert audit.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED
        # Step 3 failed due to corner failsafe
        failed_events = [e for e in audit.step_events if e.status == "ERROR"]
        assert len(failed_events) >= 1
        assert any("Screen corner failsafe hit" in (e.error_details or "") for e in failed_events)
        # iccid and submit never executed
        assert "89014103211118510720" not in mock_driver.typed_text


# ==============================================================================
# 5. Peephole Optimizer Non-Regression: Chained Action Density
# ==============================================================================

class TestPeepholeOptimizerActionChainPreservation:
    """Stress tests adversarial chained action sequences under click_to_tab=True."""

    @pytest.mark.asyncio
    async def test_chained_action_boxes_under_click_to_tab(self, mock_driver, monkeypatch):
        """
        Adversarial chain: Text -> Checkbox -> Button -> Checkbox -> Select -> Button -> Submit.
        All preceding steps have navigation=TAB. Under click_to_tab=True, every action click
        must remain strictly intact without being dropped.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        layout = VisualFormLayout(
            name="Adversarial Action Chain",
            target_application=TargetApplicationSpec(window_title_pattern=".*Banking KYC.*"),
            canvas=CanvasDimensions(width=1200, height=800),
            execution_settings=ExecutionSettingsSpec(countdown_seconds=0, default_step_delay_ms=10),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
            boxes=[
                VisualBox(
                    name="txt",
                    geometry=BoxGeometry(x=100, y=50, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="UserText",
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="cb1",
                    geometry=BoxGeometry(x=100, y=100, width=20, height=20),
                    action_type=DesignerActionType.CHECKBOX,
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="btn1",
                    geometry=BoxGeometry(x=100, y=140, width=100, height=30),
                    action_type=DesignerActionType.CLICK,
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="cb2",
                    geometry=BoxGeometry(x=100, y=190, width=20, height=20),
                    action_type=DesignerActionType.CHECKBOX,
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="sel1",
                    geometry=BoxGeometry(x=100, y=230, width=150, height=30),
                    action_type=DesignerActionType.SELECT,
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="btn2",
                    geometry=BoxGeometry(x=100, y=280, width=100, height=30),
                    action_type=DesignerActionType.CLICK,
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="sub1",
                    geometry=BoxGeometry(x=100, y=330, width=120, height=40),
                    action_type=DesignerActionType.SUBMIT,
                    navigation=NavigationAction.NONE,
                    post_delay_ms=0,
                ),
            ],
        )

        wf = compile_visual_layout_to_workflow(layout)
        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(wf)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED
        assert mock_driver.typed_text == ["UserText"]

        # Exactly 7 clicks: 1 (txt focus click) + 1 (cb1) + 1 (btn1) + 1 (cb2) + 1 (sel1) + 1 (btn2) + 1 (sub1)
        assert len(mock_driver.clicks) == 7, f"Expected 7 clicks, got {len(mock_driver.clicks)}"

        # Verify all coordinates
        expected_clicks = [
            (300, 165),  # txt center (window_x=100 + center_x=200 = 300)
            (210, 210),  # cb1 center (window_x=100 + center_x=110 = 210)
            (250, 255),  # btn1 center
            (210, 300),  # cb2 center
            (275, 345),  # sel1 center
            (250, 395),  # btn2 center
            (260, 450),  # sub1 center
        ]
        actual_clicks = [(c["x"], c["y"]) for c in mock_driver.clicks]
        assert actual_clicks == expected_clicks, f"Actual clicks {actual_clicks} != expected {expected_clicks}"


# ==============================================================================
# 6. Advanced Edge Cases & Defense-in-Depth
# ==============================================================================

class TestAdvancedEdgeCasesRoundTrip:
    """Tests subtle edge cases in compiled workflow execution."""

    @pytest.mark.asyncio
    async def test_first_control_is_action_click_before_text(self, mock_driver, monkeypatch):
        """
        When the initial form control is a Checkbox or Button (not a text field),
        verify it receives its click immediately, and subsequent text fields are typed in order.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        layout = VisualFormLayout(
            name="Initial Action Control Layout",
            target_application=TargetApplicationSpec(window_title_pattern=".*Banking KYC.*"),
            canvas=CanvasDimensions(width=1200, height=800),
            execution_settings=ExecutionSettingsSpec(countdown_seconds=0, default_step_delay_ms=10),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
            boxes=[
                VisualBox(
                    name="consent_first",
                    label="Consent Checkbox",
                    geometry=BoxGeometry(x=100, y=50, width=20, height=20),
                    action_type=DesignerActionType.CHECKBOX,
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="username",
                    label="Username Field",
                    geometry=BoxGeometry(x=100, y=100, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="johndoe",
                    navigation=NavigationAction.TAB,
                    post_delay_ms=0,
                ),
                VisualBox(
                    name="submit",
                    geometry=BoxGeometry(x=100, y=150, width=120, height=40),
                    action_type=DesignerActionType.SUBMIT,
                    navigation=NavigationAction.NONE,
                    post_delay_ms=0,
                ),
            ],
        )

        wf = compile_visual_layout_to_workflow(layout)
        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(wf)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED
        assert mock_driver.typed_text == ["johndoe"]

        # Clicks:
        # 1. consent_first (checkbox at screen 100+110=210, 100+60=160)
        # 2. username focus click: pruned because preceding action had navigation=TAB and click_to_tab=True!
        # 3. submit click (at screen 100+160=260, 100+170=270)
        assert len(mock_driver.clicks) == 2
        assert mock_driver.clicks[0]["x"] == 210 and mock_driver.clicks[0]["y"] == 160
        assert mock_driver.clicks[1]["x"] == 260 and mock_driver.clicks[1]["y"] == 270

    @pytest.mark.asyncio
    async def test_escape_abort_during_settling_delay(self, mock_driver, monkeypatch):
        """
        Verify that emergency Escape abort triggered while sleeping in pre_delay_ms
        immediately wakes up and halts execution without waiting for the full delay.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        layout = VisualFormLayout(
            name="Escape During Delay Test",
            target_application=TargetApplicationSpec(window_title_pattern=".*Banking KYC.*"),
            canvas=CanvasDimensions(width=1200, height=800),
            execution_settings=ExecutionSettingsSpec(countdown_seconds=0, default_step_delay_ms=10),
            boxes=[
                VisualBox(
                    name="long_delay_field",
                    geometry=BoxGeometry(x=100, y=100, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="ShouldNeverFinish",
                    timing=BoxTiming(pre_delay_ms=2000),  # 2 full seconds
                    post_delay_ms=0,
                ),
            ],
        )

        wf = compile_visual_layout_to_workflow(layout)
        runner = WorkflowRunner(driver=mock_driver)

        # Trigger runner abort after 100ms
        async def abort_injector():
            await asyncio.sleep(0.1)
            await runner.abort()

        t0 = time.perf_counter()
        asyncio.create_task(abort_injector())
        audit = await runner.execute(wf)
        elapsed = time.perf_counter() - t0

        assert audit.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED
        # Must have aborted well before 2 seconds
        assert elapsed < 1.0, f"Expected abort in <1.0s, took {elapsed:.3f}s"
        assert mock_driver.typed_text == []

    @pytest.mark.asyncio
    async def test_credential_masking_in_audit_events(self, mock_driver, monkeypatch):
        """
        Verify that sensitive credentials (passwords, SSNs) marked with is_secret=True
        are masked in the structured audit log.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        from kutomoto.designer.schema import ValueConfig

        layout = VisualFormLayout(
            name="Confidential Banking Form",
            target_application=TargetApplicationSpec(window_title_pattern=".*Banking KYC.*"),
            canvas=CanvasDimensions(width=1200, height=800),
            execution_settings=ExecutionSettingsSpec(countdown_seconds=0, default_step_delay_ms=10),
            boxes=[
                VisualBox(
                    name="pin",
                    label="Customer Secret PIN",
                    geometry=BoxGeometry(x=100, y=100, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="123456",
                    value_config=ValueConfig(static_value="123456", is_secret=True),
                    navigation=NavigationAction.NONE,
                    post_delay_ms=0,
                ),
            ],
        )

        wf = compile_visual_layout_to_workflow(layout)
        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(wf)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert mock_driver.typed_text == ["123456"]

        # Audit events must NOT expose the plaintext PIN
        type_events = [e for e in audit.step_events if e.action_type == "type_text"]
        assert len(type_events) == 1
        assert "123456" not in type_events[0].parameters_summary
        assert "masked" in type_events[0].parameters_summary.lower()
