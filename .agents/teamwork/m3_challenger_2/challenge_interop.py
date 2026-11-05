"""
challenge_interop.py
Milestone 3 Execution Interoperability Empirical Challenge Harness.
Adversarially validates round-trip visual compiler and engine execution.
Copyrights reserved to 90Studio
"""

import asyncio
import inspect
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure src is on sys.path
SRC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Enable fast testing mode to avoid unnecessary wall-clock delays
os.environ["KUTOMOTO_TEST_FAST"] = "1"

from kutomoto.designer.schema import (
    BoxGeometry,
    CanvasDimensions,
    DesignerActionType,
    NavigationAction,
    PeepholeOptimizationConfig,
    VisualBox,
    VisualFormLayout,
)
from kutomoto.designer.compiler import (
    compile_visual_layout_to_workflow,
)
from kutomoto.engine.audit import AuditLogger
from kutomoto.engine.fsm import ExecutionState
from kutomoto.engine.runner import WorkflowRunner
from kutomoto.engine.safety import (
    CornerFailsafeTriggered,
    EscapeAbortTriggered,
    MockWin32Driver,
    SafetyConfig,
    SafetyGuard,
)
from kutomoto.engine.schema import (
    ActionType,
    ErrorRecoveryPolicy,
    KutomotoWorkflow,
    MouseButton,
)


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error: str = ""
        self.details: Dict[str, Any] = {}

    def __repr__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}" + (f" - Error: {self.error}" if self.error else "")


results: List[TestResult] = []


def run_test(name: str):
    def decorator(fn):
        async def async_wrapper():
            tr = TestResult(name)
            try:
                if inspect.iscoroutinefunction(fn):
                    await fn(tr)
                else:
                    fn(tr)
                tr.passed = True
            except Exception as ex:
                tr.passed = False
                tr.error = f"{type(ex).__name__}: {ex}"
            results.append(tr)
            print(tr)
            return tr
        return async_wrapper
    return decorator


# ==============================================================================
# VECTOR 1: PEEPHOLE NAVIGATION CORRECTNESS
# ==============================================================================

@run_test("Vector 1.1: click_to_tab preserves the first field click")
def test_click_to_tab_preserves_first_click(tr: TestResult):
    boxes = [
        VisualBox(name="f1", geometry=BoxGeometry(x=10, y=10, width=100, height=30), action_type=DesignerActionType.TYPE_TEXT, value="Val1", navigation=NavigationAction.TAB),
        VisualBox(name="f2", geometry=BoxGeometry(x=10, y=50, width=100, height=30), action_type=DesignerActionType.TYPE_TEXT, value="Val2", navigation=NavigationAction.TAB),
        VisualBox(name="f3", geometry=BoxGeometry(x=10, y=90, width=100, height=30), action_type=DesignerActionType.TYPE_TEXT, value="Val3", navigation=NavigationAction.TAB),
    ]
    layout = VisualFormLayout(
        name="Vector 1.1 Layout",
        canvas=CanvasDimensions(width=800, height=600),
        target_application={"window_title_pattern": ".*"},
        boxes=boxes,
        optimization=PeepholeOptimizationConfig(click_to_tab=True)
    )
    wf = compile_visual_layout_to_workflow(layout)
    click_steps = [s for s in wf.steps if s.action_type == ActionType.CLICK]
    tr.details["click_count"] = len(click_steps)
    tr.details["click_labels"] = [s.label for s in click_steps]

    # Invariant: First field click must ALWAYS be preserved
    assert len(click_steps) == 1, f"Expected exactly 1 click step (for first field), got {len(click_steps)}"
    assert "f1" in click_steps[0].label, f"First click step must target f1, got: {click_steps[0].label}"


@run_test("Vector 1.2: click_to_tab with initial delay preserves first field click")
def test_click_to_tab_with_initial_delay_preserves_first_click(tr: TestResult):
    boxes = [
        VisualBox(name="init_delay", geometry=BoxGeometry(x=10, y=10, width=50, height=20), action_type=DesignerActionType.DELAY, value="100"),
        VisualBox(name="f1", geometry=BoxGeometry(x=10, y=40, width=100, height=30), action_type=DesignerActionType.TYPE_TEXT, value="Val1", navigation=NavigationAction.TAB),
        VisualBox(name="f2", geometry=BoxGeometry(x=10, y=80, width=100, height=30), action_type=DesignerActionType.TYPE_TEXT, value="Val2", navigation=NavigationAction.TAB),
    ]
    layout = VisualFormLayout(
        name="Vector 1.2 Layout",
        canvas=CanvasDimensions(width=800, height=600),
        target_application={"window_title_pattern": ".*"},
        boxes=boxes,
        optimization=PeepholeOptimizationConfig(click_to_tab=True)
    )
    wf = compile_visual_layout_to_workflow(layout)
    click_steps = [s for s in wf.steps if s.action_type == ActionType.CLICK]
    assert len(click_steps) == 1, f"Expected 1 click step, got {len(click_steps)}"
    assert "f1" in click_steps[0].label


@run_test("Vector 1.3: TYPE_TEXT box with force_click=True preserves click")
def test_type_text_force_click_preserved(tr: TestResult):
    boxes = [
        VisualBox(name="f1", geometry=BoxGeometry(x=10, y=10, width=100, height=30), action_type=DesignerActionType.TYPE_TEXT, value="Val1", navigation=NavigationAction.TAB),
        VisualBox(name="f2", geometry=BoxGeometry(x=10, y=50, width=100, height=30), action_type=DesignerActionType.TYPE_TEXT, value="Val2", navigation=NavigationAction.TAB, force_click=True),
        VisualBox(name="f3", geometry=BoxGeometry(x=10, y=90, width=100, height=30), action_type=DesignerActionType.TYPE_TEXT, value="Val3", navigation=NavigationAction.TAB, force_click=False),
    ]
    layout = VisualFormLayout(
        name="Vector 1.3 Layout",
        canvas=CanvasDimensions(width=800, height=600),
        target_application={"window_title_pattern": ".*"},
        boxes=boxes,
        optimization=PeepholeOptimizationConfig(click_to_tab=True)
    )
    wf = compile_visual_layout_to_workflow(layout)
    click_steps = [s for s in wf.steps if s.action_type == ActionType.CLICK]
    tr.details["click_steps"] = [s.label for s in click_steps]
    # f1 preserved (first field), f2 preserved (force_click), f3 pruned
    assert len(click_steps) == 2, f"Expected 2 clicks (f1 and f2), got {len(click_steps)}: {[s.label for s in click_steps]}"
    assert any("f1" in s.label for s in click_steps)
    assert any("f2" in s.label for s in click_steps)


@run_test("Vector 1.4: CLICK box with force_click=True preserves click following Tab")
def test_click_box_force_click_preserved(tr: TestResult):
    boxes = [
        VisualBox(name="f1", geometry=BoxGeometry(x=10, y=10, width=100, height=30), action_type=DesignerActionType.TYPE_TEXT, value="Val1", navigation=NavigationAction.TAB),
        VisualBox(name="btn_click", geometry=BoxGeometry(x=10, y=50, width=100, height=30), action_type=DesignerActionType.CLICK, force_click=True),
    ]
    layout = VisualFormLayout(
        name="Vector 1.4 Layout",
        canvas=CanvasDimensions(width=800, height=600),
        target_application={"window_title_pattern": ".*"},
        boxes=boxes,
        optimization=PeepholeOptimizationConfig(click_to_tab=True)
    )
    wf = compile_visual_layout_to_workflow(layout)
    click_steps = [s for s in wf.steps if s.action_type == ActionType.CLICK]
    tr.details["click_steps"] = [s.label for s in click_steps]
    # Invariant: If a box has force_click=True, its click MUST be preserved!
    assert any("btn_click" in s.label for s in click_steps), (
        f"CLICK box 'btn_click' with force_click=True had its click pruned by click_to_tab! "
        f"Remaining clicks: {[s.label for s in click_steps]}"
    )


@run_test("Vector 1.5: Delay collapsing correctly sums durations without dropping metadata")
def test_delay_collapsing_duration_and_metadata(tr: TestResult):
    boxes = [
        VisualBox(name="d1", geometry=BoxGeometry(x=10, y=10, width=50, height=20), action_type=DesignerActionType.DELAY, value="100"),
        VisualBox(name="d2", geometry=BoxGeometry(x=10, y=35, width=50, height=20), action_type=DesignerActionType.DELAY, value="250"),
        VisualBox(name="d3", geometry=BoxGeometry(x=10, y=60, width=50, height=20), action_type=DesignerActionType.DELAY, value="150"),
        VisualBox(name="d0", geometry=BoxGeometry(x=10, y=85, width=50, height=20), action_type=DesignerActionType.DELAY, value="0"),
    ]
    layout = VisualFormLayout(
        name="Vector 1.5 Layout",
        canvas=CanvasDimensions(width=800, height=600),
        target_application={"window_title_pattern": ".*"},
        boxes=boxes,
        optimization=PeepholeOptimizationConfig(collapse_delays=True, prune_empty_delays=True)
    )
    wf = compile_visual_layout_to_workflow(layout)
    delays = [s for s in wf.steps if s.action_type == ActionType.DELAY]
    assert len(delays) == 1, f"Expected exactly 1 coalesced delay, got {len(delays)}"
    coalesced = delays[0]
    expected_sum = 100 + 250 + 150  # 500ms (0ms pruned)
    assert coalesced.parameters.duration_ms == expected_sum, f"Expected {expected_sum}ms, got {coalesced.parameters.duration_ms}ms"
    assert "500ms" in coalesced.label, f"Label must reflect coalesced duration, got: {coalesced.label}"
    assert coalesced.step_id is not None and len(coalesced.step_id) > 0
    assert coalesced.enabled is True
    assert coalesced.sequence_index == 2  # Step 1 is focus_window


@run_test("Vector 1.6: Contiguous 1..N sequence re-indexing")
def test_contiguous_reindexing(tr: TestResult):
    boxes = [
        VisualBox(name="b1", geometry=BoxGeometry(x=10, y=10, width=50, height=20), action_type=DesignerActionType.DELAY, value="100"),
        VisualBox(name="b2", geometry=BoxGeometry(x=10, y=35, width=50, height=20), action_type=DesignerActionType.DELAY, value="200"),
        VisualBox(name="b3", geometry=BoxGeometry(x=10, y=60, width=50, height=20), action_type=DesignerActionType.TYPE_TEXT, value="abc", navigation="tab"),
        VisualBox(name="b4", geometry=BoxGeometry(x=10, y=85, width=50, height=20), action_type=DesignerActionType.TYPE_TEXT, value="def", navigation="tab"),
    ]
    layout = VisualFormLayout(
        name="Vector 1.6 Layout",
        canvas=CanvasDimensions(width=800, height=600),
        target_application={"window_title_pattern": ".*"},
        boxes=boxes,
        optimization=PeepholeOptimizationConfig(click_to_tab=True, collapse_delays=True)
    )
    wf = compile_visual_layout_to_workflow(layout)
    indices = [s.sequence_index for s in wf.steps]
    expected = list(range(1, len(wf.steps) + 1))
    assert indices == expected, f"Sequence indices must be contiguous 1..{len(wf.steps)}, got: {indices}"


# ==============================================================================
# VECTOR 2: ROUND-TRIP EXECUTION WITH ENGINE
# ==============================================================================

@run_test("Vector 2.1: 10-box visual form round-trip execution with MockWin32Driver")
async def test_10_box_roundtrip_execution(tr: TestResult):
    boxes = [
        VisualBox(name="first_name", geometry=BoxGeometry(x=50, y=50, width=200, height=35), action_type=DesignerActionType.TYPE_TEXT, value="Alice", navigation=NavigationAction.TAB, clear_before=True),
        VisualBox(name="last_name", geometry=BoxGeometry(x=50, y=100, width=200, height=35), action_type=DesignerActionType.TYPE_TEXT, value="Smith", navigation=NavigationAction.TAB, clear_before=True),
        VisualBox(name="account_number", geometry=BoxGeometry(x=50, y=150, width=200, height=35), action_type=DesignerActionType.TYPE_TEXT, value="ACC-8839210", navigation=NavigationAction.TAB, clear_before=True),
        VisualBox(name="routing_code", geometry=BoxGeometry(x=50, y=200, width=200, height=35), action_type=DesignerActionType.TYPE_TEXT, value="021000021", navigation=NavigationAction.TAB, clear_before=True),
        VisualBox(name="delay_validation_1", geometry=BoxGeometry(x=50, y=250, width=200, height=20), action_type=DesignerActionType.DELAY, value="10"),
        VisualBox(name="corporate_email", geometry=BoxGeometry(x=50, y=280, width=200, height=35), action_type=DesignerActionType.TYPE_TEXT, value="alice.smith@90studio.bank", navigation=NavigationAction.TAB, clear_before=True),
        VisualBox(name="credit_limit", geometry=BoxGeometry(x=50, y=330, width=200, height=35), action_type=DesignerActionType.TYPE_TEXT, value="50000", navigation=NavigationAction.TAB, clear_before=True),
        VisualBox(name="delay_validation_2", geometry=BoxGeometry(x=50, y=380, width=200, height=20), action_type=DesignerActionType.DELAY, value="10"),
        VisualBox(name="compliance_ack", geometry=BoxGeometry(x=50, y=410, width=30, height=30), action_type=DesignerActionType.CLICK, navigation=NavigationAction.TAB),
        VisualBox(name="submit_application", geometry=BoxGeometry(x=50, y=460, width=150, height=45), action_type=DesignerActionType.SUBMIT, navigation=NavigationAction.NONE),
    ]

    layout = VisualFormLayout(
        name="10-Box Enterprise Onboarding",
        canvas=CanvasDimensions(width=1000, height=800),
        target_application={"window_title_pattern": "Banking KYC Customer Onboarding.*"},
        boxes=boxes,
        optimization=PeepholeOptimizationConfig(click_to_tab=False, collapse_delays=False)
    )

    wf = compile_visual_layout_to_workflow(layout)
    assert len(wf.steps) >= 10, f"Workflow must contain at least 10 steps, got {len(wf.steps)}"

    driver = MockWin32Driver()
    driver.reset()
    runner = WorkflowRunner(driver=driver)

    audit_log = await runner.execute(wf)

    # Invariant Verifications:
    # 1. FSM cleanly transitioned to COMPLETED
    assert runner.state == ExecutionState.COMPLETED, f"Expected FSM COMPLETED, got {runner.state}"

    # 2. Audit log has final_status="SUCCESS"
    assert audit_log.execution_summary.final_status == "SUCCESS", (
        f"Expected audit final_status SUCCESS, got {audit_log.execution_summary.final_status}"
    )

    # 3. driver.typed_text contains all expected values
    expected_texts = [
        "Alice",
        "Smith",
        "ACC-8839210",
        "021000021",
        "alice.smith@90studio.bank",
        "50000",
    ]
    for expected in expected_texts:
        assert expected in driver.typed_text, f"Expected '{expected}' in typed_text, got: {driver.typed_text}"

    # 4. driver.key_presses contains expected tabs
    tabs = [k for k in driver.key_presses if k.get("key") == "tab"]
    assert len(tabs) >= 6, f"Expected at least 6 tab keypresses, got {len(tabs)}"

    # 5. Cleared fields executed for text fields
    assert len(driver.cleared_fields) >= 6, f"Expected >= 6 cleared fields, got {len(driver.cleared_fields)}"

    # 6. Audit summary
    assert audit_log.execution_summary.failed_steps == 0
    assert audit_log.execution_summary.successful_steps == len(wf.steps)

    tr.details["total_steps"] = len(wf.steps)
    tr.details["typed_text"] = driver.typed_text
    tr.details["tabs_count"] = len(tabs)
    tr.details["clicks_count"] = len(driver.clicks)


# ==============================================================================
# VECTOR 3: EDGE CASE HANDLING & IN-STEP ABORT PROTECTION
# ==============================================================================

@run_test("Vector 3.1: Emergency abort via runner.abort() halts workflow immediately")
async def test_emergency_abort_halt(tr: TestResult):
    boxes = [
        VisualBox(name="f1", geometry=BoxGeometry(x=50, y=50, width=200, height=35), action_type=DesignerActionType.TYPE_TEXT, value="Initial", navigation=NavigationAction.TAB),
        VisualBox(name="d_long", geometry=BoxGeometry(x=50, y=100, width=200, height=20), action_type=DesignerActionType.DELAY, value="5000"),
        VisualBox(name="f2_unreachable", geometry=BoxGeometry(x=50, y=150, width=200, height=35), action_type=DesignerActionType.TYPE_TEXT, value="ShouldNeverBeTyped", navigation=NavigationAction.TAB),
    ]
    layout = VisualFormLayout(
        name="Abort Test Layout",
        canvas=CanvasDimensions(width=800, height=600),
        target_application={"window_title_pattern": "Banking KYC.*"},
        boxes=boxes,
    )
    wf = compile_visual_layout_to_workflow(layout)

    # Disable fast mode temporarily to simulate active delay
    os.environ.pop("KUTOMOTO_TEST_FAST", None)
    try:
        driver = MockWin32Driver()
        runner = WorkflowRunner(driver=driver)

        exec_task = asyncio.create_task(runner.execute(wf))

        # Wait until execution starts
        await asyncio.sleep(0.2)
        # Fire emergency abort
        await runner.abort()

        audit_log = await exec_task

        assert runner.state in (ExecutionState.STOPPED, ExecutionState.ERROR), f"Expected STOPPED state, got {runner.state}"
        assert audit_log.execution_summary.final_status == "ABORTED", f"Expected ABORTED, got {audit_log.execution_summary.final_status}"
        assert "ShouldNeverBeTyped" not in driver.typed_text, "Unreachable step was executed after abort!"
    finally:
        os.environ["KUTOMOTO_TEST_FAST"] = "1"


@run_test("Vector 3.2: Screen-corner failsafe trips and releases modifiers")
async def test_screen_corner_failsafe(tr: TestResult):
    boxes = [
        VisualBox(name="f1", geometry=BoxGeometry(x=50, y=50, width=200, height=35), action_type=DesignerActionType.TYPE_TEXT, value="Val1", navigation=NavigationAction.TAB),
        VisualBox(name="f2", geometry=BoxGeometry(x=50, y=100, width=200, height=35), action_type=DesignerActionType.TYPE_TEXT, value="Val2", navigation=NavigationAction.TAB),
    ]
    layout = VisualFormLayout(
        name="Corner Failsafe Layout",
        canvas=CanvasDimensions(width=800, height=600),
        target_application={"window_title_pattern": "Banking KYC.*"},
        boxes=boxes,
    )
    wf = compile_visual_layout_to_workflow(layout)

    driver = MockWin32Driver()
    driver.active_modifiers.add("ctrl")
    driver.active_modifiers.add("alt")

    # Hook driver to trigger corner failsafe after first click
    original_send_click = driver.send_click
    click_count = 0
    def intercept_click(*args, **kwargs):
        nonlocal click_count
        click_count += 1
        res = original_send_click(*args, **kwargs)
        if click_count >= 1:
            driver.simulate_corner_failsafe(0, 0)
        return res

    driver.send_click = intercept_click

    runner = WorkflowRunner(driver=driver)
    audit_log = await runner.execute(wf)

    assert audit_log.execution_summary.final_status == "ABORTED", f"Expected ABORTED, got {audit_log.execution_summary.final_status}"
    assert runner.state in (ExecutionState.STOPPED, ExecutionState.ERROR), f"Expected STOPPED/ERROR state, got {runner.state}"
    # Check modifier release invariant
    assert len(driver.active_modifiers) == 0, f"Modifiers leaked after corner failsafe: {driver.active_modifiers}"


@run_test("Vector 3.3: Escape key abort trips and cleans up state")
async def test_escape_key_abort(tr: TestResult):
    boxes = [
        VisualBox(name="f1", geometry=BoxGeometry(x=50, y=50, width=200, height=35), action_type=DesignerActionType.TYPE_TEXT, value="Val1", navigation=NavigationAction.TAB),
        VisualBox(name="f2", geometry=BoxGeometry(x=50, y=100, width=200, height=35), action_type=DesignerActionType.TYPE_TEXT, value="Val2", navigation=NavigationAction.TAB),
    ]
    layout = VisualFormLayout(
        name="Escape Abort Layout",
        canvas=CanvasDimensions(width=800, height=600),
        target_application={"window_title_pattern": "Banking KYC.*"},
        boxes=boxes,
    )
    wf = compile_visual_layout_to_workflow(layout)

    driver = MockWin32Driver()
    driver.active_modifiers.add("shift")

    original_send_text = driver.send_text
    def intercept_text(*args, **kwargs):
        driver.simulate_escape_press()
        return original_send_text(*args, **kwargs)

    driver.send_text = intercept_text

    runner = WorkflowRunner(driver=driver)
    audit_log = await runner.execute(wf)

    assert audit_log.execution_summary.final_status == "ABORTED"
    assert runner.state in (ExecutionState.STOPPED, ExecutionState.ERROR)
    assert len(driver.active_modifiers) == 0


@run_test("Vector 3.4: In-step abort protection with stuck modifiers during hardware fault")
async def test_in_step_hardware_fault_modifier_release(tr: TestResult):
    boxes = [
        VisualBox(name="f1", geometry=BoxGeometry(x=50, y=50, width=200, height=35), action_type=DesignerActionType.TYPE_TEXT, value="Val1", navigation=NavigationAction.TAB),
        VisualBox(name="f2", geometry=BoxGeometry(x=50, y=100, width=200, height=35), action_type=DesignerActionType.TYPE_TEXT, value="Val2", navigation=NavigationAction.TAB),
    ]
    layout = VisualFormLayout(
        name="Fault Layout",
        canvas=CanvasDimensions(width=800, height=600),
        target_application={"window_title_pattern": "Banking KYC.*"},
        boxes=boxes,
        execution_settings={"error_recovery_policy": ErrorRecoveryPolicy.ABORT}
    )
    wf = compile_visual_layout_to_workflow(layout)

    driver = MockWin32Driver()
    driver.active_modifiers.add("ctrl")

    # In-step fault injection during text typing
    def failing_send_text(*args, **kwargs):
        driver.active_modifiers.add("win")  # Emulate stuck Windows key
        raise RuntimeError("DirectX / GDI display handle corrupted during text rendering")

    driver.send_text = failing_send_text

    runner = WorkflowRunner(driver=driver)
    audit_log = await runner.execute(wf)

    assert audit_log.execution_summary.final_status == "FAILED"
    assert runner.state in (ExecutionState.STOPPED, ExecutionState.ERROR)
    # Crucial M2 invariant: Modifier release on step abort
    assert len(driver.active_modifiers) == 0, f"Expected 0 active modifiers, got: {driver.active_modifiers}"


async def main():
    print("=" * 80)
    print("M3 INTEROPERABILITY CHALLENGE SUITE: EMPIRICAL HARNESS")
    print("=" * 80)

    # Run all registered tests
    test_functions = [
        test_click_to_tab_preserves_first_click,
        test_click_to_tab_with_initial_delay_preserves_first_click,
        test_type_text_force_click_preserved,
        test_click_box_force_click_preserved,
        test_delay_collapsing_duration_and_metadata,
        test_contiguous_reindexing,
        test_10_box_roundtrip_execution,
        test_emergency_abort_halt,
        test_screen_corner_failsafe,
        test_escape_key_abort,
        test_in_step_hardware_fault_modifier_release,
    ]

    for tf in test_functions:
        await tf()

    print("\n" + "=" * 80)
    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    print(f"SUMMARY: {passed_count}/{total_count} PASSED")
    print("=" * 80)

    if passed_count < total_count:
        print("\nFAILED TESTS:")
        for r in results:
            if not r.passed:
                print(f" - {r.name}: {r.error}")

    return passed_count == total_count


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
