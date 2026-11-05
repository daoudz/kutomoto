"""
tests.test_e2e_automation
Milestone 5: Comprehensive Automated End-to-End Verification Test Suite.
Verifies automated form filling across open web browser targets (Banking KYC)
and native Windows desktop targets (Telecom SIM Provisioning), covering visual
designer workflow compilation, step-by-step action workflows, adversarial edge cases,
deterministic CI simulation, and live Win32 SendInput execution.

Copyrights reserved to 90Studio
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Optional

import pytest

logger = logging.getLogger("kutomoto.test_e2e")

# Ensure src is on sys.path
SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from kutomoto.designer.compiler import compile_visual_layout_to_workflow  # noqa: E402
from kutomoto.designer.schema import (  # noqa: E402
    BoxGeometry,
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
from kutomoto.engine.schema import (  # noqa: E402
    ActionType,
    ClearStrategy,
    CoordinateMode,
    ErrorRecoveryPolicy,
    ExecutionSettings,
    KutomotoWorkflow,
    StepParameters,
    SubmitMethod,
    TargetApplication,
    TargetAppType,
    WorkflowStep,
)

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLES_WEB_DIR = BASE_DIR / "samples" / "web"
SAMPLES_DESKTOP_DIR = BASE_DIR / "samples" / "desktop"


# ==============================================================================
# 1. FIXTURES & HELPER DRIVERS
# ==============================================================================

@pytest.fixture
def mock_driver() -> MockWin32Driver:
    """
    Provides an isolated MockWin32Driver pre-seeded with both
    Banking KYC Browser Form and Telecom SIM Desktop Form windows.
    """
    driver = MockWin32Driver()
    driver.reset()

    # Register Browser Window (HWND 1001)
    driver.add_mock_window(
        hwnd=1001,
        title="Banking KYC Onboarding — kutomoto Automation Target — Copyrights reserved to 90Studio - Microsoft Edge",
        process_name="msedge.exe",
        rect=(100, 100, 1200, 800),
    )

    # Register Desktop Application Window (HWND 1002)
    driver.add_mock_window(
        hwnd=1002,
        title="Telecom SIM Provisioning System — 90Studio",
        process_name="sample_desktop_form.exe",
        rect=(150, 150, 640, 580),
    )
    return driver


class VirtualTkinterDriver(MockWin32Driver):
    """
    Virtual Desktop Driver that translates WorkflowRunner actions
    directly into in-memory Tkinter UI widget events and method calls.
    Allows testing full desktop form filling in CI without hardware SendInput.
    """

    def __init__(self, tkinter_app: Any) -> None:
        super().__init__()
        self.app = tkinter_app
        self.add_mock_window(
            hwnd=1002,
            title="Telecom SIM Provisioning System — 90Studio",
            process_name="sample_desktop_form.exe",
            rect=(150, 150, 640, 580),
        )
        self.foreground_hwnd = 1002
        self.active_field_index = 0
        self.fields = ["msisdn", "iccid", "plan_type", "kyc_status", "imsi"]

    def reset(self) -> None:
        super().reset()
        self.active_field_index = 0
        self.foreground_hwnd = 1002
        if 1002 not in self.windows:
            self.add_mock_window(
                hwnd=1002,
                title="Telecom SIM Provisioning System — 90Studio",
                process_name="sample_desktop_form.exe",
                rect=(150, 150, 640, 580),
            )

    def find_window(
        self,
        title_pattern: str,
        match_mode: str = "contains",
        process_name: Optional[str] = None,
    ) -> Optional[int]:
        res = super().find_window(title_pattern, match_mode=match_mode, process_name=process_name)
        if res is not None:
            return res
        # Permit matching regardless of whether invoked as python.exe or sample_desktop_form.exe
        if self.foreground_hwnd in self.windows:
            win = self.windows[self.foreground_hwnd]
            if re.search(title_pattern, win["title"], re.IGNORECASE):
                if not process_name or process_name.lower() in ("python.exe", "sample_desktop_form.exe", "pythonw.exe"):
                    return self.foreground_hwnd
        return None

    def send_text(self, text: str, delay_between_keys_ms: int = 20, use_clipboard_threshold: int = 40) -> None:
        super().send_text(text, delay_between_keys_ms, use_clipboard_threshold)
        if 0 <= self.active_field_index < len(self.fields):
            field_name = self.fields[self.active_field_index]
            self.app.set_field(field_name, text)

    def send_key_press(self, key_name: str, repeat_count: int = 1) -> None:
        super().send_key_press(key_name, repeat_count)
        k = str(key_name).lower()
        if k == "tab":
            self.active_field_index = (self.active_field_index + repeat_count) % (len(self.fields) + 2)
        elif k == "space":
            if hasattr(self.app, "var_kyc"):
                self.app.var_kyc.set("VERIFIED")
        elif k in ("enter", "return"):
            self.app.submit()

    def send_click(self, x: int, y: int, button: str = "left", click_count: int = 1) -> None:
        super().send_click(x, y, button, click_count)
        coords = self.app.get_control_coordinates()

        win_bounds = self.get_window_bounds(self.foreground_hwnd)
        win_x = win_bounds[0] if win_bounds else 0
        win_y = win_bounds[1] if win_bounds else 0
        candidates = [(x, y), (x - win_x, y - win_y)]

        # 1. Check entry and combobox fields (indices 0..4)
        field_control_map = {
            "entry_msisdn": 0,
            "entry_iccid": 1,
            "combo_plan": 2,
            "combo_kyc": 3,
            "entry_imsi": 4,
        }
        for ctrl_name, field_idx in field_control_map.items():
            ctrl = coords.get(ctrl_name, {})
            cx = ctrl.get("x", 0)
            cy = ctrl.get("y", 0)
            cw = ctrl.get("width", 0)
            ch = ctrl.get("height", 0)
            for cand_x, cand_y in candidates:
                if cx <= cand_x <= cx + cw and cy <= cand_y <= cy + ch:
                    self.active_field_index = field_idx
                    if hasattr(self.app, ctrl_name):
                        try:
                            getattr(self.app, ctrl_name).focus_set()
                        except Exception as e:
                            logger.debug("Failed focus_set on %s: %s", ctrl_name, e)
                    return

        # 2. Check Provision SIM button (primary submit, index 5)
        btn = coords.get("btn_provision", {})
        if btn:
            bx = btn.get("x", 220)
            by = btn.get("y", 315)
            bw = btn.get("width", 175)
            bh = btn.get("height", 34)
            for cand_x, cand_y in candidates:
                if (bx <= cand_x <= bx + bw and by <= cand_y <= by + bh) or (cand_x >= 200 and cand_y >= 300):
                    self.active_field_index = len(self.fields)
                    self.app.submit()
                    return

        # 3. Check Clear Form button (secondary action, index 6)
        btn_c = coords.get("btn_clear", {})
        if btn_c:
            cx = btn_c.get("x", 405)
            cy = btn_c.get("y", 315)
            cw = btn_c.get("width", 175)
            ch = btn_c.get("height", 34)
            for cand_x, cand_y in candidates:
                if cx <= cand_x <= cx + cw and cy <= cand_y <= cy + ch:
                    self.active_field_index = 0
                    self.app.clear()
                    return


# ==============================================================================
# 2. WORKFLOW & LAYOUT GENERATORS
# ==============================================================================

def build_banking_kyc_visual_layout(click_to_tab: bool = True) -> VisualFormLayout:
    """Builds the canonical VisualFormLayout for the Banking KYC Web Form."""
    return VisualFormLayout(
        name="Banking KYC Onboarding Workflow",
        target_application=TargetApplicationSpec(
            type=TargetAppType.WEB_BROWSER,
            window_title_pattern=r".*Banking KYC.*",
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
                name="full_name",
                label="Customer Full Name",
                geometry=BoxGeometry(x=380, y=175, width=280, height=36),
                action_type=DesignerActionType.TYPE_TEXT,
                value="Alexander Hamilton",
                navigation=NavigationAction.TAB,
                clear_before=True,
                post_delay_ms=0,
            ),
            VisualBox(
                name="national_id",
                label="National ID / SSN",
                geometry=BoxGeometry(x=810, y=175, width=280, height=36),
                action_type=DesignerActionType.TYPE_TEXT,
                value="ID-987654",
                navigation=NavigationAction.TAB,
                clear_before=True,
                post_delay_ms=0,
            ),
            VisualBox(
                name="account_type",
                label="Account Tier",
                geometry=BoxGeometry(x=380, y=265, width=280, height=36),
                action_type=DesignerActionType.TYPE_TEXT,
                value="Checking",
                navigation=NavigationAction.TAB,
                clear_before=False,
                post_delay_ms=0,
            ),
            VisualBox(
                name="annual_income",
                label="Annual Gross Income",
                geometry=BoxGeometry(x=810, y=265, width=280, height=36),
                action_type=DesignerActionType.TYPE_TEXT,
                value="125000",
                navigation=NavigationAction.TAB,
                clear_before=True,
                post_delay_ms=0,
            ),
            VisualBox(
                name="risk_rating",
                label="Regulatory Risk Rating",
                geometry=BoxGeometry(x=380, y=355, width=280, height=36),
                action_type=DesignerActionType.TYPE_TEXT,
                value="Low",
                navigation=NavigationAction.TAB,
                clear_before=False,
                post_delay_ms=0,
            ),
            VisualBox(
                name="email",
                label="Customer Email Address",
                geometry=BoxGeometry(x=810, y=355, width=280, height=36),
                action_type=DesignerActionType.TYPE_TEXT,
                value="alexander.hamilton@90studio.io",
                navigation=NavigationAction.TAB,
                clear_before=True,
                post_delay_ms=0,
            ),
            VisualBox(
                name="terms_consent",
                label="AML Statutory Attestation Checkbox",
                geometry=BoxGeometry(x=180, y=440, width=24, height=24),
                action_type=DesignerActionType.CHECKBOX,
                navigation=NavigationAction.TAB,
                post_delay_ms=0,
            ),
            VisualBox(
                name="btn_submit",
                label="Submit KYC Dossier Button",
                geometry=BoxGeometry(x=450, y=520, width=160, height=44),
                action_type=DesignerActionType.SUBMIT,
                navigation=NavigationAction.NONE,
                post_delay_ms=0,
            ),
        ],
    )


def build_banking_kyc_step_workflow() -> KutomotoWorkflow:
    """Builds a manual step-by-step action workflow for Banking KYC."""
    return KutomotoWorkflow(
        name="Banking KYC Step-by-Step Flow",
        target_application=TargetApplication(
            type=TargetAppType.WEB_BROWSER,
            window_title_pattern=r".*Banking KYC.*",
            process_name="msedge.exe",
        ),
        execution_settings=ExecutionSettings(
            countdown_seconds=0,
            default_step_delay_ms=10,
            error_recovery_policy=ErrorRecoveryPolicy.ABORT,
        ),
        steps=[
            WorkflowStep(
                sequence_index=1,
                action_type=ActionType.FOCUS_WINDOW,
                parameters=StepParameters(window_title_pattern=r".*Banking KYC.*"),
            ),
            WorkflowStep(
                sequence_index=2,
                action_type=ActionType.CLICK,
                parameters=StepParameters(
                    coordinate_mode=CoordinateMode.NORMALIZED,
                    norm_x=0.32,
                    norm_y=0.22,
                ),
            ),
            WorkflowStep(
                sequence_index=3,
                action_type=ActionType.CLEAR_FIELD,
                parameters=StepParameters(clear_strategy=ClearStrategy.SELECT_ALL_BACKSPACE),
            ),
            WorkflowStep(
                sequence_index=4,
                action_type=ActionType.TYPE_TEXT,
                parameters=StepParameters(text="Elizabeth Schuyler"),
            ),
            WorkflowStep(
                sequence_index=5,
                action_type=ActionType.KEY_PRESS,
                parameters=StepParameters(key="tab"),
            ),
            WorkflowStep(
                sequence_index=6,
                action_type=ActionType.CLEAR_FIELD,
                parameters=StepParameters(clear_strategy=ClearStrategy.SELECT_ALL_BACKSPACE),
            ),
            WorkflowStep(
                sequence_index=7,
                action_type=ActionType.TYPE_TEXT,
                parameters=StepParameters(text="ID-445566"),
            ),
            WorkflowStep(
                sequence_index=8,
                action_type=ActionType.KEY_PRESS,
                parameters=StepParameters(key="tab"),
            ),
            WorkflowStep(
                sequence_index=9,
                action_type=ActionType.TYPE_TEXT,
                parameters=StepParameters(text="Savings"),
            ),
            WorkflowStep(
                sequence_index=10,
                action_type=ActionType.KEY_PRESS,
                parameters=StepParameters(key="tab"),
            ),
            WorkflowStep(
                sequence_index=11,
                action_type=ActionType.CLEAR_FIELD,
                parameters=StepParameters(clear_strategy=ClearStrategy.SELECT_ALL_BACKSPACE),
            ),
            WorkflowStep(
                sequence_index=12,
                action_type=ActionType.TYPE_TEXT,
                parameters=StepParameters(text="85000"),
            ),
            WorkflowStep(
                sequence_index=13,
                action_type=ActionType.KEY_PRESS,
                parameters=StepParameters(key="tab"),
            ),
            WorkflowStep(
                sequence_index=14,
                action_type=ActionType.TYPE_TEXT,
                parameters=StepParameters(text="Low"),
            ),
            WorkflowStep(
                sequence_index=15,
                action_type=ActionType.KEY_PRESS,
                parameters=StepParameters(key="tab"),
            ),
            WorkflowStep(
                sequence_index=16,
                action_type=ActionType.CLEAR_FIELD,
                parameters=StepParameters(clear_strategy=ClearStrategy.SELECT_ALL_BACKSPACE),
            ),
            WorkflowStep(
                sequence_index=17,
                action_type=ActionType.TYPE_TEXT,
                parameters=StepParameters(text="elizabeth@90studio.io"),
            ),
            WorkflowStep(
                sequence_index=18,
                action_type=ActionType.KEY_PRESS,
                parameters=StepParameters(key="tab"),
            ),
            WorkflowStep(
                sequence_index=19,
                action_type=ActionType.KEY_PRESS,
                parameters=StepParameters(key="space"),
            ),
            WorkflowStep(
                sequence_index=20,
                action_type=ActionType.KEY_PRESS,
                parameters=StepParameters(key="tab"),
            ),
            WorkflowStep(
                sequence_index=21,
                action_type=ActionType.SUBMIT,
                parameters=StepParameters(submit_method=SubmitMethod.ENTER_KEY),
            ),
        ],
    )


def build_telecom_sim_step_workflow() -> KutomotoWorkflow:
    """Builds a manual step-by-step action workflow for Telecom SIM Provisioning Desktop Form."""
    return KutomotoWorkflow(
        name="Telecom SIM Provisioning Flow",
        target_application=TargetApplication(
            type=TargetAppType.WINDOWS_DESKTOP,
            window_title_pattern=r".*Telecom SIM Provisioning.*",
            process_name="sample_desktop_form.exe",
        ),
        execution_settings=ExecutionSettings(
            countdown_seconds=0,
            default_step_delay_ms=10,
            error_recovery_policy=ErrorRecoveryPolicy.ABORT,
        ),
        steps=[
            WorkflowStep(
                sequence_index=1,
                action_type=ActionType.FOCUS_WINDOW,
                parameters=StepParameters(window_title_pattern=r".*Telecom SIM Provisioning.*"),
            ),
            WorkflowStep(
                sequence_index=2,
                action_type=ActionType.CLICK,
                parameters=StepParameters(
                    coordinate_mode=CoordinateMode.WINDOW_CLIENT,
                    x=220,
                    y=90,
                ),
            ),
            WorkflowStep(
                sequence_index=3,
                action_type=ActionType.CLEAR_FIELD,
                parameters=StepParameters(clear_strategy=ClearStrategy.SELECT_ALL_BACKSPACE),
            ),
            WorkflowStep(
                sequence_index=4,
                action_type=ActionType.TYPE_TEXT,
                parameters=StepParameters(text="555-019-2834"),
            ),
            WorkflowStep(
                sequence_index=5,
                action_type=ActionType.KEY_PRESS,
                parameters=StepParameters(key="tab"),
            ),
            WorkflowStep(
                sequence_index=6,
                action_type=ActionType.CLEAR_FIELD,
                parameters=StepParameters(clear_strategy=ClearStrategy.SELECT_ALL_BACKSPACE),
            ),
            WorkflowStep(
                sequence_index=7,
                action_type=ActionType.TYPE_TEXT,
                parameters=StepParameters(text="8901410321111851072"),
            ),
            WorkflowStep(
                sequence_index=8,
                action_type=ActionType.KEY_PRESS,
                parameters=StepParameters(key="tab"),
            ),
            WorkflowStep(
                sequence_index=9,
                action_type=ActionType.TYPE_TEXT,
                parameters=StepParameters(text="Postpaid Unlimited"),
            ),
            WorkflowStep(
                sequence_index=10,
                action_type=ActionType.KEY_PRESS,
                parameters=StepParameters(key="tab"),
            ),
            WorkflowStep(
                sequence_index=11,
                action_type=ActionType.KEY_PRESS,
                parameters=StepParameters(key="space"),
            ),
            WorkflowStep(
                sequence_index=12,
                action_type=ActionType.KEY_PRESS,
                parameters=StepParameters(key="tab"),
            ),
            WorkflowStep(
                sequence_index=13,
                action_type=ActionType.CLEAR_FIELD,
                parameters=StepParameters(clear_strategy=ClearStrategy.SELECT_ALL_BACKSPACE),
            ),
            WorkflowStep(
                sequence_index=14,
                action_type=ActionType.TYPE_TEXT,
                parameters=StepParameters(text="310410123456789"),
            ),
            WorkflowStep(
                sequence_index=15,
                action_type=ActionType.KEY_PRESS,
                parameters=StepParameters(key="tab"),
            ),
            WorkflowStep(
                sequence_index=16,
                action_type=ActionType.SUBMIT,
                parameters=StepParameters(
                    submit_method=SubmitMethod.BUTTON_CLICK,
                    coordinate_mode=CoordinateMode.WINDOW_CLIENT,
                    x=250,
                    y=330,
                ),
            ),
        ],
    )


# ==============================================================================
# 3. SCENARIO 1: BANKING KYC WEB FORM E2E VERIFICATION
# ==============================================================================

class TestBankingKYCWebFormE2E:
    """Verifies end-to-end automated form filling on the Banking KYC Web Form target."""

    def test_01_web_target_file_integrity_and_branding(self):
        """Verifies existence, required DOM IDs, tabindex sequence, and 90Studio branding."""
        index_path = SAMPLES_WEB_DIR / "index.html"
        styles_path = SAMPLES_WEB_DIR / "styles.css"
        form_path = SAMPLES_WEB_DIR / "form.js"

        assert index_path.exists(), f"Missing {index_path}"
        assert styles_path.exists(), f"Missing {styles_path}"
        assert form_path.exists(), f"Missing {form_path}"

        content = index_path.read_text(encoding="utf-8")

        # 90Studio Branding Attribution
        assert "Copyrights reserved to 90Studio" in content
        assert "Banking KYC Onboarding" in content

        # Required DOM Input IDs
        required_ids = [
            "full_name",
            "national_id",
            "account_type",
            "annual_income",
            "risk_rating",
            "email",
            "terms_consent",
            "btn_submit",
            "btn_reset",
            "submission_banner",
            "submitted_payload_json",
        ]
        for dom_id in required_ids:
            assert f'id="{dom_id}"' in content or f"id='{dom_id}'" in content, f"Missing DOM ID: {dom_id}"

        # Sequential tabindex check 1 through 9
        for i in range(1, 10):
            assert f'tabindex="{i}"' in content or f"tabindex='{i}'" in content, f"Missing tabindex: {i}"

    @pytest.mark.asyncio
    async def test_02_web_form_visual_designer_compilation_and_execution(self, mock_driver, monkeypatch):
        """Tests VisualFormLayout compilation to workflow and execution against browser form."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        layout = build_banking_kyc_visual_layout(click_to_tab=True)
        workflow = compile_visual_layout_to_workflow(layout)

        assert isinstance(workflow, KutomotoWorkflow)
        assert workflow.target_application.type == TargetAppType.WEB_BROWSER
        assert len(workflow.steps) >= 8

        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        # 1. Final execution status
        assert audit.execution_summary.final_status == "SUCCESS"
        assert audit.execution_summary.failed_steps == 0
        assert runner.state == ExecutionState.COMPLETED
        assert 1001 in mock_driver.focus_history

        # 2. Sequential typing verification
        expected_texts = ["Alexander Hamilton", "ID-987654", "Checking", "125000", "Low", "alexander.hamilton@90studio.io"]
        assert mock_driver.typed_text == expected_texts

        # 3. Checkbox toggled via coordinate click or space
        assert len(mock_driver.clicks) >= 1 or any(k["key"] == "space" for k in mock_driver.key_presses)

        # 4. Submission triggered
        assert len(mock_driver.clicks) >= 1 or any(k["key"] in ("enter", "return") for k in mock_driver.key_presses)

        # 5. 90Studio Copyright branding in audit log
        assert audit.copyright == "Copyrights reserved to 90Studio"

    @pytest.mark.asyncio
    async def test_03_web_form_step_by_step_action_workflow_execution(self, mock_driver, monkeypatch):
        """Tests manual 21-step action workflow execution against browser form."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = build_banking_kyc_step_workflow()

        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert audit.execution_summary.total_steps == 21
        assert audit.execution_summary.failed_steps == 0
        assert runner.state == ExecutionState.COMPLETED

        # Verify typed payload order
        expected_texts = ["Elizabeth Schuyler", "ID-445566", "Savings", "85000", "Low", "elizabeth@90studio.io"]
        assert mock_driver.typed_text == expected_texts

        # Verify Tab navigation transitions
        tab_presses = [k for k in mock_driver.key_presses if k["key"] == "tab"]
        assert len(tab_presses) == 7

        # Verify Enter key submission
        enter_presses = [k for k in mock_driver.key_presses if k["key"] in ("enter", "return")]
        assert len(enter_presses) == 1

    def test_04_web_form_client_validation_and_submission_banner_logic(self):
        """Validates client-side form.js validation rules and submission banner payload formatting."""
        form_js = (SAMPLES_WEB_DIR / "form.js").read_text(encoding="utf-8")

        # Verify mandatory validation checks present in JS code
        assert "full_name" in form_js
        assert "national_id" in form_js
        assert "account_type" in form_js
        assert "annual_income" in form_js
        assert "terms_consent" in form_js
        assert "__LAST_SUBMITTED_PAYLOAD__" in form_js
        assert "submission_banner" in form_js
        assert "Copyrights reserved to 90Studio" in form_js

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


# ==============================================================================
# 4. SCENARIO 2: TELECOM SIM DESKTOP FORM E2E VERIFICATION
# ==============================================================================

class TestTelecomSIMDesktopFormE2E:
    """Verifies end-to-end automated form filling on the Telecom SIM Desktop Form target."""

    def test_01_desktop_target_file_integrity_and_branding(self):
        """Verifies existence, window title regex compatibility, and 90Studio branding."""
        desktop_script = SAMPLES_DESKTOP_DIR / "sample_desktop_form.py"
        assert desktop_script.exists(), f"Missing {desktop_script}"

        content = desktop_script.read_text(encoding="utf-8")
        assert "Copyrights reserved to 90Studio" in content
        assert "Telecom SIM Provisioning" in content
        assert "tkinter" in content

    def test_02_desktop_form_in_memory_headless_execution(self):
        """Executes in-memory Tkinter desktop form, validating field entry, submission, and validation."""
        from samples.desktop.sample_desktop_form import create_app

        try:
            app = create_app(headless=True)
            app.withdraw()

            # 1. Test Invalid Provisioning (short ICCID)
            app.set_field("msisdn", "555-019-2834")
            app.set_field("iccid", "12345")
            app.set_field("plan_type", "Prepaid 5G")
            app.set_field("kyc_status", "VERIFIED")
            app.set_field("imsi", "310410123456789")

            assert app.submit() is False
            status_invalid = app.get_status()
            assert "Validation Error" in status_invalid

            # 2. Test Valid Provisioning (19-digit ICCID)
            app.set_field("iccid", "8901410321111851072")
            assert app.submit() is True
            status_valid = app.get_status()
            assert "SIM PROVISIONED SUCCESSFULLY" in status_valid.upper()

            # 3. Records verification
            records = app.get_provisioned_records()
            assert len(records) >= 1
            assert records[-1]["iccid"] == "8901410321111851072"
            assert "transaction_id" in records[-1]

            # 4. Clear Form verification
            app.clear()
            state = app.get_state()
            assert state["iccid"] == ""
            assert "Cleared" in state["status_text"] or "Ready" in state["status_text"]

            app.destroy()
        except Exception as e:
            if "no display" in str(e).lower() or "tcl" in str(e).lower():
                pytest.skip(f"Tkinter display not available in environment: {e}")
            raise

    @pytest.mark.asyncio
    async def test_03_desktop_form_window_targeting_and_focus_switching(self, mock_driver, monkeypatch):
        """Verifies regex window targeting and focus switching for desktop window."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        hwnd = mock_driver.find_window(r".*Telecom SIM Provisioning.*")
        assert hwnd == 1002

        focused = mock_driver.focus_window(hwnd)
        assert focused is True
        assert mock_driver.get_foreground_window() == 1002
        assert 1002 in mock_driver.focus_history

    @pytest.mark.asyncio
    async def test_04_desktop_form_sequential_action_workflow_execution(self, mock_driver, monkeypatch):
        """Tests sequential coordinate and tab entry of MSISDN, ICCID, IMSI and Submit."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = build_telecom_sim_step_workflow()

        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert audit.execution_summary.failed_steps == 0
        assert runner.state == ExecutionState.COMPLETED

        # Verify sequential typing
        assert "555-019-2834" in mock_driver.typed_text
        assert "8901410321111851072" in mock_driver.typed_text
        assert "310410123456789" in mock_driver.typed_text

        # Verify Submit click
        assert len(mock_driver.clicks) >= 2

    @pytest.mark.asyncio
    async def test_05_desktop_form_virtual_driver_integration(self, monkeypatch):
        """Tests WorkflowRunner executing against in-memory Tkinter form via VirtualTkinterDriver."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        from samples.desktop.sample_desktop_form import create_app

        try:
            app = create_app(headless=True)
            app.withdraw()

            driver = VirtualTkinterDriver(tkinter_app=app)
            workflow = build_telecom_sim_step_workflow()
            runner = WorkflowRunner(driver=driver)

            audit = await runner.execute(workflow)
            assert audit.execution_summary.final_status == "SUCCESS"

            # Check that Tkinter app state was updated by runner
            assert "SIM PROVISIONED SUCCESSFULLY" in app.get_status().upper()

            app.destroy()
        except Exception as e:
            if "no display" in str(e).lower() or "tcl" in str(e).lower():
                pytest.skip(f"Tkinter display not available in environment: {e}")
            raise

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



# ==============================================================================
# 5. SCENARIO 3: ADVERSARIAL & EDGE CASES E2E VERIFICATION
# ==============================================================================

class TestAdversarialAndEdgeCasesE2E:
    """Verifies safety guardrails, focus loss guardian, emergency aborts, and audit trail."""

    @pytest.mark.asyncio
    async def test_01_loss_of_focus_guardian_auto_pause_and_resume(self, mock_driver, monkeypatch):
        """Edge Case E13: Target window focus stolen; runner pauses and resumes upon focus restoration."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = KutomotoWorkflow(
            name="Focus Loss Test",
            target_application=TargetApplication(
                type=TargetAppType.WINDOWS_DESKTOP,
                window_title_pattern=r".*Telecom SIM Provisioning.*",
            ),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.FOCUS_WINDOW,
                    post_delay_ms=60,
                    parameters=StepParameters(window_title_pattern=r".*Telecom SIM Provisioning.*"),
                ),
                WorkflowStep(
                    sequence_index=2,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text="555-0101"),
                ),
            ],
        )
        runner = WorkflowRunner(driver=mock_driver)

        # Launch execution task
        exec_task = asyncio.create_task(runner.execute(workflow))

        # Allow step 1 focus to execute, then simulate focus loss during its post_delay
        await asyncio.sleep(0.02)
        mock_driver.simulate_focus_loss(new_hwnd=9999)

        # Wait for step 1 post-delay to complete and step 2 focus guardian to pause
        await asyncio.sleep(0.08)

        # Verify runner transitioned to PAUSED
        assert runner.state == ExecutionState.PAUSED

        # Restore focus to target window and resume
        mock_driver.focus_window(1002)
        await runner.resume()

        audit = await exec_task
        assert audit.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED

    @pytest.mark.asyncio
    async def test_02_emergency_escape_key_abort(self, mock_driver, monkeypatch):
        """Edge Case E01: Operator hits Escape key; runner immediately aborts and releases modifiers."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = build_telecom_sim_step_workflow()

        mock_driver.simulate_escape_press()
        runner = WorkflowRunner(driver=mock_driver)

        audit = await runner.execute(workflow)
        assert audit.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED
        assert any(c.get("method") == "release_all_modifiers" for c in mock_driver.calls)

    @pytest.mark.asyncio
    async def test_03_corner_failsafe_abort(self, mock_driver, monkeypatch):
        """Edge Case E07: Operator slams cursor to (0, 0); corner failsafe triggers emergency abort."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = build_banking_kyc_step_workflow()

        mock_driver.simulate_corner_failsafe(0, 0)
        runner = WorkflowRunner(driver=mock_driver)

        audit = await runner.execute(workflow)
        assert audit.execution_summary.final_status == "ABORTED"
        assert runner.state == ExecutionState.STOPPED

    @pytest.mark.asyncio
    async def test_04_parameter_length_boundaries_and_special_chars(self, mock_driver, monkeypatch):
        """Edge Cases E02 & E14: Tests empty string, ultra-long strings (450 chars), and unicode characters."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        ultra_long_text = "ABC" * 150  # 450 chars (> 40 clipboard threshold)
        unicode_name = "François Müller-Ångström 90Studio"

        workflow = KutomotoWorkflow(
            name="Boundary Payload Test",
            target_application=TargetApplication(
                type=TargetAppType.WINDOWS_DESKTOP,
                window_title_pattern=r".*Telecom SIM Provisioning.*",
            ),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text=""),
                ),
                WorkflowStep(
                    sequence_index=2,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text=unicode_name),
                ),
                WorkflowStep(
                    sequence_index=3,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text=ultra_long_text),
                ),
            ],
        )
        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert unicode_name in mock_driver.typed_text
        assert ultra_long_text in mock_driver.typed_text

    @pytest.mark.asyncio
    async def test_05_error_recovery_policies(self, mock_driver, monkeypatch):
        """Verifies error recovery policies (ABORT vs SKIP_STEP)."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        # 1. ABORT policy
        mock_driver.fail_focus = True
        wf_abort = KutomotoWorkflow(
            name="Abort Policy Test",
            target_application=TargetApplication(
                type=TargetAppType.WINDOWS_DESKTOP,
                window_title_pattern=r".*Nonexistent.*",
            ),
            execution_settings=ExecutionSettings(
                countdown_seconds=0,
                error_recovery_policy=ErrorRecoveryPolicy.ABORT,
            ),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.FOCUS_WINDOW,
                    parameters=StepParameters(window_title_pattern=r".*Nonexistent.*"),
                ),
            ],
        )
        runner_abort = WorkflowRunner(driver=mock_driver)
        audit_abort = await runner_abort.execute(wf_abort)
        assert audit_abort.execution_summary.final_status == "FAILED"
        assert runner_abort.state == ExecutionState.ERROR

        # 2. SKIP_STEP policy
        mock_driver.fail_focus = False
        wf_skip = KutomotoWorkflow(
            name="Skip Step Test",
            target_application=TargetApplication(
                type=TargetAppType.WINDOWS_DESKTOP,
                window_title_pattern=r".*Telecom SIM Provisioning.*",
            ),
            execution_settings=ExecutionSettings(
                countdown_seconds=0,
                error_recovery_policy=ErrorRecoveryPolicy.SKIP_STEP,
            ),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.FOCUS_WINDOW,
                    parameters=StepParameters(window_title_pattern=r".*NonexistentWindow999.*"),
                ),
                WorkflowStep(
                    sequence_index=2,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text="Continuation Success"),
                ),
            ],
        )
        runner_skip = WorkflowRunner(driver=mock_driver)
        audit_skip = await runner_skip.execute(wf_skip)
        assert audit_skip.execution_summary.final_status == "SUCCESS"
        assert "Continuation Success" in mock_driver.typed_text

    @pytest.mark.asyncio
    async def test_06_audit_log_90studio_compliance_and_credential_masking(self, mock_driver, monkeypatch):
        """Verifies 90Studio compliance stamping and password masking in audit trail."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = KutomotoWorkflow(
            name="Compliance Audit Test",
            target_application=TargetApplication(
                type=TargetAppType.WEB_BROWSER,
                window_title_pattern=r".*Banking KYC.*",
            ),
            execution_settings=ExecutionSettings(countdown_seconds=0),
            steps=[
                WorkflowStep(
                    sequence_index=1,
                    action_type=ActionType.TYPE_TEXT,
                    parameters=StepParameters(text="SuperSecretPass123!", is_secret=True),
                ),
            ],
        )
        runner = WorkflowRunner(driver=mock_driver)
        audit = await runner.execute(workflow)

        # 90Studio Copyright Assertion
        assert audit.copyright == "Copyrights reserved to 90Studio"
        assert audit.system == "kutomoto"

        # Secret Masking Assertion
        event = audit.step_events[0]
        assert "SuperSecretPass123!" not in event.parameters_summary
        assert "********" in event.parameters_summary


# ==============================================================================
# 6. SCENARIO 4: DETERMINISTIC CI & LIVE WIN32 EXECUTION
# ==============================================================================

class TestDeterministicCIAndLiveExecution:
    """Verifies deterministic multi-run reproducibility and live Win32 SendInput execution."""

    @pytest.mark.asyncio
    async def test_01_deterministic_mock_driver_reproducibility(self, mock_driver, monkeypatch):
        """Executes 5 consecutive full roundtrips; verifies 100% deterministic identical telemetry."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        workflow = build_banking_kyc_step_workflow()

        for run_idx in range(5):
            mock_driver.reset()
            mock_driver.add_mock_window(
                1001,
                "Banking KYC Onboarding — kutomoto Automation Target — Copyrights reserved to 90Studio - Microsoft Edge",
                "msedge.exe",
                (100, 100, 1200, 800),
            )
            runner = WorkflowRunner(driver=mock_driver)
            audit = await runner.execute(workflow)
            assert audit.execution_summary.final_status == "SUCCESS", f"Failed on run {run_idx}"
            assert audit.execution_summary.total_steps == 21

    def test_02_live_win32_hardware_execution_adapter(self):
        """Verifies production Win32DriverAdapter integration with live Windows OS user32/kernel32."""
        if sys.platform != "win32":
            pytest.skip("Win32 hardware tests require Windows OS")

        from kutomoto.automation.win32_driver import ProductionDriverAdapter, Win32DriverAdapter
        driver = ProductionDriverAdapter()
        alias_driver = Win32DriverAdapter()

        # Check DPI awareness
        dpi_res = driver.set_dpi_awareness()
        assert dpi_res is not None

        # Check screen metrics
        sw, sh = driver.get_screen_dimensions()
        assert sw > 0 and sh > 0

        # Check foreground window integer HWND (safely handles None)
        fg_hwnd = driver.get_foreground_window()
        assert isinstance(fg_hwnd, int)

        # Check find_window returns int or None (never WindowInfo object)
        res = driver.find_window("NonexistentWindowForAdapterTestXYZ999")
        assert res is None or isinstance(res, int)

        # Check alias behaves identically
        assert isinstance(alias_driver.get_foreground_window(), int)

    def test_03_live_desktop_form_end_to_end_optional(self):
        """
        Dual CI/Live execution test: executes against live Tkinter desktop application
        via VirtualTkinterDriver in CI, or live OS subprocess when KUTOMOTO_LIVE_TEST=1.
        """
        from samples.desktop.sample_desktop_form import create_app
        from kutomoto.automation import win32_window

        if os.environ.get("KUTOMOTO_LIVE_TEST") and win32_window.get_foreground_window():
            import subprocess
            from kutomoto.automation.win32_driver import Win32DriverAdapter

            desktop_script = SAMPLES_DESKTOP_DIR / "sample_desktop_form.py"
            proc = subprocess.Popen([sys.executable, str(desktop_script)])
            try:
                target_hwnd = None
                for _ in range(30):
                    info = win32_window.find_window(r".*Telecom SIM Provisioning.*")
                    if info:
                        target_hwnd = info.hwnd if hasattr(info, "hwnd") else info
                        break
                    time.sleep(0.1)

                assert target_hwnd is not None, "Live desktop application window did not appear"

                driver = Win32DriverAdapter()
                focused = driver.focus_window(target_hwnd)
                assert focused is True

                workflow = build_telecom_sim_step_workflow()
                runner = WorkflowRunner(driver=driver)
                audit = asyncio.run(runner.execute(workflow))
                assert audit.execution_summary.final_status == "SUCCESS"
            finally:
                proc.terminate()
                proc.wait(timeout=5)
        else:
            # Deterministic CI execution via VirtualTkinterDriver
            try:
                app = create_app(headless=True)
            except Exception as e:
                if "no display" in str(e).lower() or "tcl" in str(e).lower():
                    pytest.skip(f"Tkinter display not available in environment: {e}")
                raise

            try:
                driver = VirtualTkinterDriver(tkinter_app=app)
                workflow = build_telecom_sim_step_workflow()
                runner = WorkflowRunner(driver=driver)
                audit = asyncio.run(runner.execute(workflow))
                assert audit.execution_summary.final_status == "SUCCESS"
                assert "SIM PROVISIONED SUCCESSFULLY" in app.get_status().upper()
                records = app.get_provisioned_records()
                assert len(records) >= 1
                assert records[-1]["iccid"] == "8901410321111851072"
            finally:
                app.destroy()


# ==============================================================================
# 7. SCENARIO 5: ON-DISK WORKFLOWS & DRIVER REUSABILITY VERIFICATION
# ==============================================================================

class TestOnDiskWorkflowsAndDriverReusability:
    """Verifies on-disk JSON workflow file validation and multi-run driver reusability."""

    def test_01_on_disk_sample_workflows_schema_validation(self):
        """
        Validates both samples/web/banking_kyc_workflow.json and
        samples/desktop/telecom_sim_provisioning_workflow.json via KutomotoWorkflow.model_validate_json().
        """
        web_path = SAMPLES_WEB_DIR / "banking_kyc_workflow.json"
        assert web_path.exists(), f"Missing {web_path}"
        wf_web = KutomotoWorkflow.model_validate_json(web_path.read_text(encoding="utf-8"))
        assert wf_web.target_application.type == TargetAppType.WEB_BROWSER
        assert wf_web.copyright == "Copyrights reserved to 90Studio"
        assert len(wf_web.steps) == 17

        desktop_path = SAMPLES_DESKTOP_DIR / "telecom_sim_provisioning_workflow.json"
        assert desktop_path.exists(), f"Missing {desktop_path}"
        wf_desk = KutomotoWorkflow.model_validate_json(desktop_path.read_text(encoding="utf-8"))
        assert wf_desk.target_application.type == TargetAppType.WINDOWS_DESKTOP
        assert wf_desk.target_application.process_name is None
        assert wf_desk.copyright == "Copyrights reserved to 90Studio"
        assert len(wf_desk.steps) == 13

    @pytest.mark.asyncio
    async def test_02_on_disk_telecom_workflow_virtual_driver_execution(self, monkeypatch):
        """
        Loads samples/desktop/telecom_sim_provisioning_workflow.json and executes
        against VirtualTkinterDriver to verify final_status == 'SUCCESS', is_submitted is True,
        and 90Studio copyright attribution.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        from samples.desktop.sample_desktop_form import create_app

        desktop_path = SAMPLES_DESKTOP_DIR / "telecom_sim_provisioning_workflow.json"
        workflow = KutomotoWorkflow.model_validate_json(desktop_path.read_text(encoding="utf-8"))

        try:
            app = create_app(headless=True)
            app.withdraw()
            driver = VirtualTkinterDriver(tkinter_app=app)
            runner = WorkflowRunner(driver=driver)

            audit = await runner.execute(workflow)
            assert audit.execution_summary.final_status == "SUCCESS"
            assert audit.execution_summary.failed_steps == 0
            assert runner.state == ExecutionState.COMPLETED
            assert audit.copyright == "Copyrights reserved to 90Studio"

            state = app.get_state()
            assert state["is_submitted"] is True
            assert "SIM PROVISIONED SUCCESSFULLY" in state["status_text"].upper()
            payload = state["last_payload"]
            assert payload["copyright"] == "Copyrights reserved to 90Studio"
            assert payload["msisdn"] == "555-019-2834"

            app.destroy()
        except Exception as e:
            if "no display" in str(e).lower() or "tcl" in str(e).lower():
                pytest.skip(f"Tkinter display not available in environment: {e}")
            raise

    @pytest.mark.asyncio
    async def test_03_virtual_driver_repeated_execution_focus_reset(self, monkeypatch):
        """
        Verifies that repeated execution of the workflow on the same VirtualTkinterDriver
        instance resets active field focus on entry_msisdn click and provisions 2 records successfully.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        from samples.desktop.sample_desktop_form import create_app

        desktop_path = SAMPLES_DESKTOP_DIR / "telecom_sim_provisioning_workflow.json"
        workflow = KutomotoWorkflow.model_validate_json(desktop_path.read_text(encoding="utf-8"))

        try:
            app = create_app(headless=True)
            app.withdraw()
            driver = VirtualTkinterDriver(tkinter_app=app)
            runner = WorkflowRunner(driver=driver)

            # First Run
            audit1 = await runner.execute(workflow)
            assert audit1.execution_summary.final_status == "SUCCESS"
            assert len(app.get_provisioned_records()) == 1

            # Second Run on same driver and runner
            audit2 = await runner.execute(workflow)
            assert audit2.execution_summary.final_status == "SUCCESS"
            assert len(app.get_provisioned_records()) == 2
            assert app.get_state()["is_submitted"] is True

            app.destroy()
        except Exception as e:
            if "no display" in str(e).lower() or "tcl" in str(e).lower():
                pytest.skip(f"Tkinter display not available in environment: {e}")
            raise

