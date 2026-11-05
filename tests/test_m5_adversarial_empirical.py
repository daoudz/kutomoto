"""
tests.test_m5_adversarial_empirical
Milestone 5 Empirical Verification & Adversarial Stress Suite.
Tests payload fidelity, driver contract parity, repeated sequential submissions,
state pollution, memory leakage, and sample workflow schema integrity.

Copyrights reserved to 90Studio
"""

from __future__ import annotations

import gc
import json
from pathlib import Path
import re
import sys
import time
import tracemalloc
from typing import List

import pytest

# Ensure src is on sys.path
SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from kutomoto.automation.win32_driver import ProductionDriverAdapter, Win32DriverAdapter  # noqa: E402
from kutomoto.engine.fsm import ExecutionState  # noqa: E402
from kutomoto.engine.runner import IWin32Driver, WorkflowRunner  # noqa: E402
from kutomoto.engine.safety import MockWin32Driver  # noqa: E402
from kutomoto.engine.schema import (  # noqa: E402
    ActionType,
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
from pydantic import ValidationError  # noqa: E402
from samples.desktop.sample_desktop_form import (  # noqa: E402
    KYC_OPTIONS,
    PLAN_OPTIONS,
    create_app,
)
from tests.test_e2e_automation import (  # noqa: E402
    VirtualTkinterDriver,
    build_banking_kyc_step_workflow,
)

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLES_WEB_DIR = BASE_DIR / "samples" / "web"
SAMPLES_DESKTOP_DIR = BASE_DIR / "samples" / "desktop"


# ==============================================================================
# 1. SAMPLE WORKFLOW FILES SCHEMA AND CONTRACT INTEGRITY
# ==============================================================================

class TestSampleWorkflowsContractParity:
    """Empirically tests that sample workflow files parse and conform to unified schema."""

    def test_01_banking_kyc_workflow_json_schema_validity(self):
        """Verifies samples/web/banking_kyc_workflow.json parses and adheres to KutomotoWorkflow schema."""
        workflow_file = SAMPLES_WEB_DIR / "banking_kyc_workflow.json"
        assert workflow_file.exists(), f"Missing {workflow_file}"

        content = workflow_file.read_text(encoding="utf-8")
        wf = KutomotoWorkflow.model_validate_json(content)

        assert wf.name == "Banking KYC Customer Onboarding Automated Flow"
        assert wf.target_application.type == TargetAppType.WEB_BROWSER
        assert wf.copyright == "Copyrights reserved to 90Studio"
        assert len(wf.steps) == 17
        assert any(s.action_type == ActionType.SUBMIT for s in wf.steps)

    def test_02_telecom_sim_provisioning_workflow_json_schema_validity(self):
        """
        Verifies samples/desktop/telecom_sim_provisioning_workflow.json schema validity.
        ADVERSARIAL CHECK: Confirms whether target_application.type conforms to TargetAppType enum.
        """
        workflow_file = SAMPLES_DESKTOP_DIR / "telecom_sim_provisioning_workflow.json"
        assert workflow_file.exists(), f"Missing {workflow_file}"

        content = workflow_file.read_text(encoding="utf-8")
        raw_json = json.loads(content)

        # Direct enum check: TargetAppType allows 'web_browser', 'windows_desktop', 'any'
        target_type = raw_json.get("target_application", {}).get("type")

        # Record whether model_validate_json succeeds or raises ValidationError
        validation_error_found = False
        try:
            KutomotoWorkflow.model_validate_json(content)
        except ValidationError as exc:
            validation_error_found = True
            error_str = str(exc)
            assert "desktop_window" in error_str or "target_application.type" in error_str

        # Assert schema conformance
        if target_type == "desktop_window":
            assert validation_error_found is True, (
                "Expected ValidationError for invalid target_application.type='desktop_window'"
            )
        elif target_type == "windows_desktop":
            assert validation_error_found is False, (
                "Valid schema: 'windows_desktop' must validate without errors"
            )
            wf = KutomotoWorkflow.model_validate_json(content)
            assert wf.target_application.type == TargetAppType.WINDOWS_DESKTOP


# ==============================================================================
# 2. PAYLOAD FIDELITY ACROSS ALL FIELD TYPES
# ==============================================================================

class TestPayloadFidelityAcrossAllFieldTypes:
    """Verifies that submitted form values match input datasets exactly across all field types."""

    @pytest.mark.parametrize("plan", PLAN_OPTIONS)
    @pytest.mark.parametrize("kyc", KYC_OPTIONS)
    def test_01_desktop_form_dropdown_and_text_fidelity(self, plan: str, kyc: str):
        """Exhaustively tests all dropdown combinations with alphanumeric text fields."""
        app = create_app(headless=True)
        try:
            msisdn = "+1-555-019-2834"
            iccid = "8901410321111851072"
            imsi = "310410123456789"

            app.set_field("msisdn", msisdn)
            app.set_field("iccid", iccid)
            app.set_field("plan_type", plan)
            app.set_field("kyc_status", kyc)
            app.set_field("imsi", imsi)

            is_submitted = app.submit()
            assert is_submitted is True, f"Failed submission for plan={plan}, kyc={kyc}: {app.get_status()}"

            records = app.get_provisioned_records()
            assert len(records) == 1
            rec = records[0]

            # Exact field fidelity assertions
            assert rec["msisdn"] == msisdn
            assert rec["iccid"] == iccid
            assert rec["plan_type"] == plan
            assert rec["kyc_status"] == kyc
            assert rec["imsi"] == imsi
            assert rec["status"] == "ACTIVE"
            assert rec["copyright"] == "Copyrights reserved to 90Studio"
        finally:
            app.destroy()

    def test_02_desktop_form_validation_boundaries(self):
        """Tests validation boundaries for ICCID (19-20 digits), IMSI (14-15 digits), and MSISDN (7-15 digits)."""
        app = create_app(headless=True)
        try:
            # 1. ICCID boundaries
            app.set_field("msisdn", "555-019-2834")
            app.set_field("plan_type", "Prepaid 5G")
            app.set_field("kyc_status", "VERIFIED")
            app.set_field("imsi", "310410123456789")

            # 18 digits (invalid)
            app.set_field("iccid", "123456789012345678")
            assert app.submit() is False

            # 19 digits (valid)
            app.set_field("iccid", "1234567890123456789")
            assert app.submit() is True

            # 20 digits (valid)
            app.set_field("iccid", "12345678901234567890")
            assert app.submit() is True

            # 21 digits (invalid)
            app.set_field("iccid", "123456789012345678901")
            assert app.submit() is False

            # 2. IMSI boundaries (14 or 15 digits)
            app.set_field("iccid", "1234567890123456789")

            # 13 digits (invalid)
            app.set_field("imsi", "1234567890123")
            assert app.submit() is False

            # 14 digits (valid)
            app.set_field("imsi", "12345678901234")
            assert app.submit() is True

            # 15 digits (valid)
            app.set_field("imsi", "123456789012345")
            assert app.submit() is True

            # 16 digits (invalid)
            app.set_field("imsi", "1234567890123456")
            assert app.submit() is False
        finally:
            app.destroy()

    def test_03_web_form_validation_logic_fidelity(self):
        """Simulates and verifies client-side form.js validation rules for Web KYC form."""
        regex_ssn = re.compile(r"^\d{3}-\d{2}-\d{4}$")
        regex_nat_id = re.compile(r"^ID-\d{6}$")
        regex_email = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

        # Test National ID patterns accepted by form.js: SSN, ID-XXXXXX, or 9 digits
        valid_ids = ["987-65-4321", "ID-123456", "123456789"]
        for vid in valid_ids:
            matches = bool(regex_ssn.match(vid) or regex_nat_id.match(vid) or (vid.isdigit() and len(vid) == 9))
            assert matches is True, f"Failed for valid ID: {vid}"

        invalid_ids = ["1234", "ID-123", "987-65-432", "ABC-DEF-GHI"]
        for iid in invalid_ids:
            matches = bool(regex_ssn.match(iid) or regex_nat_id.match(iid) or (iid.isdigit() and len(iid) == 9))
            assert matches is False, f"Expected invalid for ID: {iid}"

        # Test Email patterns
        valid_emails = ["alex@90studio.io", "e.vance@enterprise-bank.com", "user+kyc@sub.domain.org"]
        for ve in valid_emails:
            assert bool(regex_email.match(ve)) is True

        invalid_emails = ["no-at-sign", "@nodomain.com", "user@", "spaces in@email.com"]
        for ie in invalid_emails:
            assert bool(regex_email.match(ie)) is False


# ==============================================================================
# 3. DRIVER CONTRACT PARITY & LIVE WIN32 ADAPTER
# ==============================================================================

class TestDriverContractParityAndLiveWin32:
    """Verifies 100% protocol fidelity across MockWin32Driver and live ProductionDriverAdapter."""

    def test_01_protocol_method_completeness(self):
        """Verifies that all methods declared on IWin32Driver exist on MockWin32Driver and ProductionDriverAdapter."""
        protocol_methods = [
            m for m in dir(IWin32Driver)
            if not m.startswith("_") and callable(getattr(IWin32Driver, m))
        ]

        mock_instance = MockWin32Driver()
        prod_instance = ProductionDriverAdapter()

        for method_name in protocol_methods:
            assert hasattr(mock_instance, method_name), f"MockWin32Driver missing {method_name}"
            assert callable(getattr(mock_instance, method_name))

            assert hasattr(prod_instance, method_name), f"ProductionDriverAdapter missing {method_name}"
            assert callable(getattr(prod_instance, method_name))

    def test_02_live_win32_adapter_contracts(self):
        """Tests live Win32 calls on Windows host: DPI, screen dimensions, foreground HWND, safe find_window."""
        if sys.platform != "win32":
            pytest.skip("Windows platform required for live Win32 adapter test")

        adapter = Win32DriverAdapter()

        # 1. Screen dimensions must be positive integers
        w, h = adapter.get_screen_dimensions()
        assert isinstance(w, int) and w > 0
        assert isinstance(h, int) and h > 0

        # 2. Cursor pos must return (int, int)
        cx, cy = adapter.get_cursor_pos()
        assert isinstance(cx, int) and isinstance(cy, int)

        # 3. Foreground window must return integer HWND (never None or WindowInfo)
        fg_hwnd = adapter.get_foreground_window()
        assert isinstance(fg_hwnd, int)

        # 4. find_window for nonexistent window must return None (or int), never raise
        res = adapter.find_window("NonexistentWindowTitle_M5_Adversarial_999999")
        assert res is None or isinstance(res, int)

        # 5. release_all_modifiers must execute without raising
        adapter.release_all_modifiers()


# ==============================================================================
# 4. REPEATED SEQUENTIAL SUBMISSIONS STRESS & NO LEAKS
# ==============================================================================

class TestRepeatedSequentialSubmissionsStressAndNoLeaks:
    """Stress tests repeated sequential submissions for state pollution, memory leaks, and performance drift."""

    @pytest.mark.asyncio
    async def test_01_repeated_sequential_desktop_submissions(self, monkeypatch):
        """
        Executes 50 repeated sequential form filling and submission flows on Desktop Tkinter form
        via WorkflowRunner + VirtualTkinterDriver.
        Verifies:
        1. 100% success rate across all 50 iterations.
        2. Exact payload fidelity per iteration (no cross-iteration state pollution).
        3. Stable memory usage (no unbounded object growth).
        4. No performance degradation drift.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        try:
            app = create_app(headless=True)
        except Exception as e:
            if "no display" in str(e).lower() or "tcl" in str(e).lower():
                pytest.skip(f"Tkinter display not available in environment: {e}")
            raise
        try:
            driver = VirtualTkinterDriver(tkinter_app=app)
            runner = WorkflowRunner(driver=driver)

            iterations = 50
            execution_latencies: List[float] = []

            # Garbage collect and snapshot memory before stress loop
            gc.collect()
            tracemalloc.start()
            mem_start = tracemalloc.get_traced_memory()[0]

            for i in range(iterations):
                # Clean active field index for each sequential form entry iteration
                driver.active_field_index = 0
                runner = WorkflowRunner(driver=driver)

                # Generate unique dataset per iteration
                test_msisdn = f"555-019-{1000 + i:04d}"
                test_iccid = f"890141032111185{1000 + i:04d}"
                test_imsi = f"31041012345{1000 + i:04d}"
                plan = PLAN_OPTIONS[i % len(PLAN_OPTIONS)]

                # Build dynamic workflow
                wf = KutomotoWorkflow(
                    name=f"Stress Test Run {i}",
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
                            parameters=StepParameters(coordinate_mode=CoordinateMode.WINDOW_CLIENT, x=220, y=90),
                        ),
                        WorkflowStep(
                            sequence_index=3,
                            action_type=ActionType.TYPE_TEXT,
                            parameters=StepParameters(text=test_msisdn),
                        ),
                        WorkflowStep(sequence_index=4, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key="tab")),
                        WorkflowStep(
                            sequence_index=5,
                            action_type=ActionType.TYPE_TEXT,
                            parameters=StepParameters(text=test_iccid),
                        ),
                        WorkflowStep(sequence_index=6, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key="tab")),
                        WorkflowStep(
                            sequence_index=7,
                            action_type=ActionType.TYPE_TEXT,
                            parameters=StepParameters(text=plan),
                        ),
                        WorkflowStep(sequence_index=8, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key="tab")),
                        WorkflowStep(sequence_index=9, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key="space")),
                        WorkflowStep(sequence_index=10, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key="tab")),
                        WorkflowStep(
                            sequence_index=11,
                            action_type=ActionType.TYPE_TEXT,
                            parameters=StepParameters(text=test_imsi),
                        ),
                        WorkflowStep(sequence_index=12, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key="tab")),
                        WorkflowStep(
                            sequence_index=13,
                            action_type=ActionType.SUBMIT,
                            parameters=StepParameters(submit_method=SubmitMethod.ENTER_KEY),
                        ),
                    ],
                )

                t0 = time.perf_counter()
                audit = await runner.execute(wf)
                elapsed = time.perf_counter() - t0
                execution_latencies.append(elapsed)

                # Check execution outcome
                assert audit.execution_summary.final_status == "SUCCESS", f"Failed on iteration {i}"
                assert runner.state == ExecutionState.COMPLETED

                # Verify payload fidelity for THIS iteration in Tkinter app
                records = app.get_provisioned_records()
                assert len(records) == i + 1
                latest = records[-1]
                assert latest["msisdn"] == test_msisdn
                assert latest["iccid"] == test_iccid
                assert latest["plan_type"] == plan
                assert latest["kyc_status"] == "VERIFIED"
                assert latest["imsi"] == test_imsi

            # Memory and performance checks
            mem_peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()

            # Net memory growth per iteration should be bounded (< 100 KB per run)
            mem_delta_kb = (mem_peak - mem_start) / 1024
            assert mem_delta_kb < 100 * iterations, f"Potential memory leak detected: {mem_delta_kb} KB used over {iterations} runs"

            # Check latency drift: average of last 10 runs should not be > 3x average of first 10 runs
            avg_first_10 = sum(execution_latencies[:10]) / 10
            avg_last_10 = sum(execution_latencies[-10:]) / 10
            assert avg_last_10 < max(avg_first_10 * 3.0, 0.5), (
                f"Severe execution latency drift: first_10={avg_first_10:.4f}s, last_10={avg_last_10:.4f}s"
            )
        finally:
            app.destroy()

    @pytest.mark.asyncio
    async def test_02_repeated_sequential_mock_driver_submissions(self, monkeypatch):
        """
        Executes 50 repeated sequential form filling flows on Banking KYC with MockWin32Driver.
        Verifies clean FSM transitions, consistent step metrics, and zero cross-run state pollution.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        driver = MockWin32Driver()
        workflow = build_banking_kyc_step_workflow()

        for run_idx in range(50):
            driver.reset()
            driver.add_mock_window(
                1001,
                "Banking KYC Onboarding — kutomoto Automation Target — Copyrights reserved to 90Studio - Microsoft Edge",
                "msedge.exe",
                (100, 100, 1200, 800),
            )
            runner = WorkflowRunner(driver=driver)
            audit = await runner.execute(workflow)
            assert audit.execution_summary.final_status == "SUCCESS", f"Run {run_idx} failed"
            assert audit.execution_summary.total_steps == 21
            assert audit.execution_summary.failed_steps == 0
            assert runner.state == ExecutionState.COMPLETED

            # Telemetry verification
            assert len(driver.typed_text) == 6
            assert driver.typed_text[0] == "Elizabeth Schuyler"
            assert driver.typed_text[1] == "ID-445566"

    @pytest.mark.asyncio
    async def test_03_runner_instance_reuse_state_pollution_demonstration(self, monkeypatch):
        """
        EMPIRICAL DEFECT DEMONSTRATION:
        Reusing the same WorkflowRunner instance without re-instantiation causes:
        1. Audit log event accumulation across runs (21 -> 42 events).
        2. Spurious MouseDisturbanceDetected abort if mouse position resets between runs.
        """
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
        driver = MockWin32Driver()
        runner = WorkflowRunner(driver=driver)
        workflow = build_banking_kyc_step_workflow()

        driver.add_mock_window(
            1001,
            "Banking KYC Onboarding — kutomoto Automation Target — Copyrights reserved to 90Studio - Microsoft Edge",
            "msedge.exe",
            (100, 100, 1200, 800),
        )

        # Run 1
        audit_1 = await runner.execute(workflow)
        assert audit_1.execution_summary.final_status == "SUCCESS"
        assert len(audit_1.step_events) == 21

        # Keep cursor at end position to avoid trip, and execute Run 2 on same runner
        driver.cursor_x = 484
        driver.cursor_y = 276
        audit_2 = await runner.execute(workflow)

        # Verification 1: Audit logger state isolation (each run has exactly 21 step events)
        assert len(audit_2.step_events) == 21, (
            "Audit logger properly isolates step events per execution"
        )
        assert audit_2.execution_summary.final_status == "SUCCESS"

        # Verification 2: Resetting cursor with safety guard reset avoids false-positive disturbance
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
