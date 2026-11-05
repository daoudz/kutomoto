# Technical Analysis: Peephole Navigation Optimizer & Compiler QA Test Strategy

**Module Target**: `src/kutomoto/designer/compiler.py` & `tests/test_compiler.py`  
**Author**: `m3_explorer_3` (Milestone 3 Optimization & QA Explorer)  
**Classification**: Enterprise Confidential / 90Studio Architecture Blueprint  
**Copyright**: Copyrights reserved to 90Studio  
**Date**: 2026-11-05  

---

## 1. Executive Summary & Purpose

In enterprise forms automation across commercial banking, telecommunications, and corporate ERP environments, automated data entry speed, mechanical precision, and deterministic execution are critical. When translating user-drawn visual layouts into actionable Win32 automation workflows, a naive translation strategy generates redundant mouse movements, unnecessary coordinate clicks, and fragmented delay intervals.

This document delivers:
1. **The Architectural Design and Mathematical Specification of the Peephole Navigation Optimizer (Pass 5)** in `src/kutomoto/designer/compiler.py`, recognizing and transforming sequential field navigation, collapsing consecutive delays, eliminating redundant focus/clear sequences, and enforcing strict 1-based step re-indexing.
2. **The Comprehensive Enterprise QA Test Strategy for `tests/test_compiler.py`**, structuring 7 test classes encompassing 50+ unit, algorithmic pass, edge case, and end-to-end integration test scenarios directly verified against `WorkflowRunner(driver=MockWin32Driver())` to ensure 100% interoperability with the M2 execution engine.

---

## 2. Peephole Navigation Optimizer (Pass 5) Design

### 2.1 Theoretical Rationale: Win32 Input Injection & DOM Navigation Dynamics

In desktop applications (WinForms, WPF, Qt, SAP GUI) and modern web browsers (Chromium, Edge, Firefox), input focus can be shifted via two distinct mechanisms:
1. **Coordinate-Targeted Mouse Click**: Moves cursor, issues `WM_LBUTTONDOWN` and `WM_LBUTTONUP` via Win32 `SendInput`.
   - *Overhead*: ~110–160ms (50ms pre-delay + input dispatch + 60ms settling post-delay).
   - *Risks*: Mouse cursor drift, triggering floating tooltips/flyout menus, and disturbing browser overlays.
2. **Sequential Keyboard Navigation (`Tab` Key Press)**: Dispatches `VK_TAB` keystrokes.
   - *Overhead*: ~10–20ms.
   - *Advantage*: Follows the application's natural accessibility focus chain without cursor displacement.

When a visual layout arranges fields in a standard reading sequence (e.g., First Name followed by Last Name), the naive Pass 4 step synthesizer produces:
- Field 1: Click -> Clear -> Type "Alice" -> Press Tab
- Field 2: Click -> Clear -> Type "Smith" -> Press Tab

Notice that Field 1's trailing Tab keystroke *already shifted focus into Field 2*. The subsequent coordinate click on Field 2 is completely redundant. In a 20-field banking KYC form, eliminating these 19 redundant clicks saves **~3.0 seconds** of dead execution time and prevents mouse drift artifacts.

However, coordinate clicks cannot be eliminated blindly. Pass 5 must evaluate safety preconditions before transforming or pruning any step.

---

### 2.2 Optimization Patterns Specification

#### Pattern A: Sequential Field Navigation in Reading Order (Click-to-Tab Transformation)

- **Goal**: Safely eliminate redundant `CLICK` steps that immediately follow a `KEY_PRESS(key="tab")` action.
- **Pattern Match Trigger**:
  1. `optimization.enabled == True` and `optimization.click_to_tab == True`.
  2. Current candidate step $S_i$ is an `ActionType.CLICK` targeting normalized coordinates (`parameters.coordinate_mode == CoordinateMode.NORMALIZED`).
  3. Preceding emitted step $S_{i-1}$ is an `ActionType.KEY_PRESS` with `parameters.key == "tab"`.
- **Safety Preconditions (When Click MUST Be Preserved)**:
  1. **First Form Field**: The very first field in a form layout requires a physical coordinate click to anchor window focus into the canvas element. A click can *never* be eliminated if no preceding field has been focused.
  2. **Non-Tab Preceding Navigation**: If the preceding field had `navigation == "none"` or `navigation == "enter"`, keyboard focus did not advance to the next field. The subsequent `CLICK` must be preserved.
  3. **Explicit Box Override (`force_click=True`)**: If a field has `force_click=True` or `requires_click=True` in its metadata (e.g., custom dropdowns, comboboxes, date pickers that require a click to expand), the click is strictly preserved.
  4. **Non-Tab-Navigable Elements**: If the target box is a canvas signature pad, image upload dropzone, or coordinate button, Tab navigation cannot focus it. Click must be preserved.
  5. **Cross-Section Discontinuities**: If Box $A$ and Box $B$ belong to different logical form sections or have a vertical/horizontal Euclidean distance exceeding a configured threshold (`section_gap_threshold_px`), DOM tab order cannot be assumed to match spatial order. Click must be preserved.
  6. **Default Configuration (`click_to_tab=False`)**: In default mode (`traversal_mode="coordinate_targeted"`), all clicks are preserved to guarantee fail-safe operation on non-standard web pages.

- **Formal Algorithm for Pattern A**:
```python
def optimize_click_to_tab(steps: List[WorkflowStep], opt: PeepholeOptimizationConfig) -> List[WorkflowStep]:
    if not opt.enabled or not opt.click_to_tab:
        return steps

    optimized: List[WorkflowStep] = []
    for step in steps:
        # Check candidate click
        if (
            step.action_type == ActionType.CLICK
            and step.parameters.coordinate_mode == CoordinateMode.NORMALIZED
            and optimized
            and optimized[-1].action_type == ActionType.KEY_PRESS
            and (optimized[-1].parameters.key or "").lower() == "tab"
        ):
            # Check explicit metadata overrides
            force_click = getattr(step.parameters, "force_click", False) or (
                step.label and "[force_click]" in step.label.lower()
            )
            if not force_click:
                logger.debug("Peephole Optimizer: Pruned redundant click step: '%s'", step.label)
                continue

        optimized.append(step)
    return optimized
```

---

#### Pattern B: Consecutive Delay Collapsing

- **Goal**: Merge multiple contiguous sleep/delay steps into a single consolidated delay, preserving the exact aggregate settling duration while eliminating async event loop ticks and redundant audit log entries.
- **Pattern Match Trigger**:
  1. `optimization.enabled == True` and `optimization.collapse_delays == True`.
  2. Consecutive steps $S_i, S_{i+1}, \dots, S_{i+k}$ all have `action_type == ActionType.DELAY`.
- **Transformation**:
  - Replace the sequence with a single `ActionType.DELAY` step whose `duration_ms` is the sum:
    $$\text{duration\_ms}_{\text{merged}} = \sum_{j=i}^{i+k} S_j.\text{parameters}.\text{duration\_ms}$$
  - Update label: `"Coalesced Delay ({duration_ms}ms)"`.
- **Empty Delay Pruning**:
  - If `optimization.prune_empty_delays == True`, any `DELAY` step with `duration_ms <= 0` is discarded entirely.

- **Formal Algorithm for Pattern B**:
```python
def optimize_delay_collapsing(steps: List[WorkflowStep], opt: PeepholeOptimizationConfig) -> List[WorkflowStep]:
    if not opt.enabled:
        return steps

    collapsed: List[WorkflowStep] = []
    for step in steps:
        # Prune zero/negative delays if configured
        if opt.prune_empty_delays and step.action_type == ActionType.DELAY:
            dur = step.parameters.duration_ms or 0
            if dur <= 0:
                logger.debug("Peephole Optimizer: Pruned 0ms delay step: '%s'", step.label)
                continue

        if (
            opt.collapse_delays
            and collapsed
            and collapsed[-1].action_type == ActionType.DELAY
            and step.action_type == ActionType.DELAY
        ):
            prev_dur = collapsed[-1].parameters.duration_ms or 0
            curr_dur = step.parameters.duration_ms or 0
            total_dur = prev_dur + curr_dur
            collapsed[-1].parameters.duration_ms = total_dur
            collapsed[-1].label = f"Coalesced Delay ({total_dur}ms)"
            logger.debug("Peephole Optimizer: Collapsed delays %d ms + %d ms -> %d ms", prev_dur, curr_dur, total_dur)
        else:
            collapsed.append(step)

    return collapsed
```

---

#### Pattern C: Redundant Focus & Step Post-Processing

- **Goal**: Eliminate redundant window focus operations and re-index all workflow steps.
- **Redundant Focus Window Elimination**:
  - If step $S_i$ is `FOCUS_WINDOW` and $S_{i-1}$ is also `FOCUS_WINDOW` with identical `window_title_pattern` and `process_name`, the second focus step is redundant (window already active) and is pruned.
- **Redundant Clear Field Elimination**:
  - If two `CLEAR_FIELD` actions occur consecutively without intervening typing or navigation, the second is pruned.
- **Contiguous 1-Based Sequence Re-Indexing**:
  - After any removals, insertions, or consolidations, Pass 5 must re-index every step sequentially:
    $$S_i.\text{sequence\_index} = i \quad \text{for } i \in \{1, \dots, N\}$$
  - This guarantees that `KutomotoWorkflow.validate_steps_sequence` passes without raising uniqueness or ordering errors.

---

### 2.3 Peephole Optimization Configuration Schema

The optimizer is configured via the `PeepholeOptimizationConfig` model in `src/kutomoto/designer/schema.py`:

```python
class PeepholeOptimizationConfig(BaseModel):
    """
    Configuration options for Pass 2 spatial band sorting and
    Pass 5 peephole navigation optimizations.
    """
    enabled: bool = Field(
        default=True,
        description="Master switch for Pass 5 peephole optimizations"
    )
    band_tolerance_px: float = Field(
        default=24.0,
        ge=0.0,
        le=500.0,
        description="Vertical band grouping tolerance in pixels for Pass 2 spatial sorting"
    )
    click_to_tab: bool = Field(
        default=False,
        description="Convert redundant coordinate clicks following Tab navigation into keyboard flow"
    )
    collapse_delays: bool = Field(
        default=True,
        description="Merge consecutive delay steps into a single consolidated delay"
    )
    remove_redundant_focus: bool = Field(
        default=True,
        description="Prune consecutive duplicate focus_window actions targeting the same window"
    )
    prune_empty_delays: bool = Field(
        default=True,
        description="Discard delay steps with duration_ms == 0"
    )
```

#### Pass-Through Behavior When `enabled = False`:
When `layout.optimization.enabled == False`:
1. No clicks are dropped.
2. No delays are merged.
3. No focus steps are removed.
4. **Mandatory Invariant**: Contiguous 1-based sequence re-indexing ($1 \dots N$) is **always executed** to ensure the generated workflow adheres to the Pydantic schema contract.

---

## 3. Comprehensive Test Suite Strategy for `tests/test_compiler.py`

The test suite in `tests/test_compiler.py` must provide 100% test coverage across all 5 compilation passes, schema boundary conditions, performance stress loads, and end-to-end execution with the M2 engine.

### 3.1 Test Architecture & Class Breakdown

```
tests/test_compiler.py
├── Class 1: TestVisualLayoutSchema (12 Unit Tests)
├── Class 2: TestCompilerPass1Validation (6 Unit & Pass 1 Tests)
├── Class 3: TestCompilerPass2SpatialBandSorting (8 Algorithmic Tests)
├── Class 4: TestCompilerPass3CoordinateNormalization (5 Precision Tests)
├── Class 5: TestCompilerPass4ActionStepSynthesis (9 Step Synthesis Tests)
├── Class 6: TestCompilerPass5PeepholeOptimizer (11 Optimization Tests)
└── Class 7: TestCompilerIntegrationAndEdgeCases (8 Integration & Stress Tests)
Total: 59 Rigorous Test Cases
```

---

### 3.2 Detailed Test Case Catalog

#### Class 1: `TestVisualLayoutSchema` (Schema Unit Tests)
Validates Pydantic V2 models in `src/kutomoto/designer/schema.py`:

| # | Test Name | Purpose / Input | Expected Assertion |
|---|---|---|---|
| 1 | `test_valid_minimal_layout` | Minimal valid layout (1 text box) | Successfully instantiates `VisualFormLayout` |
| 2 | `test_valid_enterprise_banking_layout` | 5-field KYC layout with Canvas, Target, ExecutionSettings, Optimization | All models validate, fields match |
| 3 | `test_schema_missing_canvas_fails` | Layout dictionary missing `"canvas"` key | Raises Pydantic `ValidationError` |
| 4 | `test_schema_zero_canvas_dimensions` | `CanvasDimensions(width=0, height=768)` | Raises `ValidationError` (`width > 0`) |
| 5 | `test_schema_negative_canvas_dimensions` | `CanvasDimensions(width=-800, height=600)` | Raises `ValidationError` (`width > 0`) |
| 6 | `test_schema_negative_box_coordinates` | `BoxGeometry(x=-10, y=50, width=100, height=30)` | Raises `ValidationError` (`x >= 0`) |
| 7 | `test_schema_zero_or_negative_box_dimensions` | `BoxGeometry(width=0, height=30)` or `height=-10` | Raises `ValidationError` (`width > 0, height > 0`) |
| 8 | `test_schema_out_of_canvas_bounds_fails` | Box with `x=900, width=200` on `canvas.width=1000` | Raises `ValidationError` (boundary violation) |
| 9 | `test_schema_empty_boxes_list_fails` | `VisualFormLayout(boxes=[])` | Raises `ValidationError` (`min_length=1`) |
| 10 | `test_schema_duplicate_box_ids_fails` | Two boxes with identical `id="box_duplicate"` | Raises `ValidationError` (unique ID validator) |
| 11 | `test_schema_copyright_watermark_enforcement` | `copyright="Copyrights reserved to OtherCorp"` | Raises `ValidationError` (strict 90Studio check) |
| 12 | `test_schema_json_serialization_roundtrip` | `layout.model_dump_json()` and `VisualFormLayout.model_validate_json()` | Round-trip identical data model |

---

#### Class 2: `TestCompilerPass1Validation` (Pass 1 Tests)
Validates structural and geometric validation during compilation:

| # | Test Name | Purpose / Input | Expected Assertion |
|---|---|---|---|
| 13 | `test_pass1_empty_layout_raises_empty_layout_error` | Layout dict with `"boxes": []` | Raises `EmptyLayoutError` |
| 14 | `test_pass1_out_of_bounds_box_x_raises_geometry_error` | Box exceeding canvas right edge ($x + w > W$) | Raises `GeometryError` |
| 15 | `test_pass1_out_of_bounds_box_y_raises_geometry_error` | Box exceeding canvas bottom edge ($y + h > H$) | Raises `GeometryError` |
| 16 | `test_pass1_zero_canvas_dimensions_raises_geometry_error` | Layout with `canvas.width = 0` | Raises `GeometryError` |
| 17 | `test_pass1_zero_box_dimensions_raises_geometry_error` | Box with `width = 0` or `height = 0` | Raises `GeometryError` |
| 18 | `test_pass1_error_message_contains_box_identity` | Error raised on invalid box | Message contains box name/id and offending coordinates |

---

#### Class 3: `TestCompilerPass2SpatialBandSorting` (Pass 2 Tests)
Validates spatial reading-order sorting and explicit sequence index priority:

| # | Test Name | Purpose / Input | Expected Assertion |
|---|---|---|---|
| 19 | `test_pass2_explicit_sequence_indices_strictly_honored` | 4 boxes with explicit `sequence_index = [1, 2, 3, 4]` placed in reverse visual order | Output order strictly matches `sequence_index` (ignores Y/X coords) |
| 20 | `test_pass2_spatial_single_column_top_to_bottom` | Column of 3 boxes with `sequence_index = None`, ordered by Y | Sorted top-to-bottom: Box 1 -> Box 2 -> Box 3 |
| 21 | `test_pass2_spatial_single_row_left_to_right` | Row of 3 boxes with identical Y, varying X | Sorted left-to-right: Col 1 -> Col 2 -> Col 3 |
| 22 | `test_pass2_spatial_2x2_grid_reading_order` | 2x2 form grid (R1C1, R1C2, R2C1, R2C2) shuffled in random order | Restores exact reading order: R1C1 -> R1C2 -> R2C1 -> R2C2 |
| 23 | `test_pass2_band_tolerance_close_fields_grouped` | Boxes at $y=100$ and $y=112$ with `band_tolerance_px=24` | Grouped into the same band; sorted left-to-right |
| 24 | `test_pass2_band_tolerance_distant_fields_split` | Boxes at $y=100$ and $y=135$ with `band_tolerance_px=24` | Split into separate bands; sorted top-to-bottom |
| 25 | `test_pass2_custom_band_tolerance_override` | Custom `band_tolerance_px=40` via optimization config | Correctly adjusts band partitioning |
| 26 | `test_pass2_hybrid_explicit_and_spatial_boxes` | 2 boxes with explicit index, 2 unindexed | Explicit boxes placed first/slotted, unindexed sorted spatially |

---

#### Class 4: `TestCompilerPass3CoordinateNormalization` (Pass 3 Tests)
Validates center coordinate calculation, clamping, and precision:

| # | Test Name | Purpose / Input | Expected Assertion |
|---|---|---|---|
| 27 | `test_pass3_center_calculation_precision` | Box at `(100, 200, 300, 100)` on canvas `(1000, 1000)` | Center = `(250, 250)`, `norm_x = 0.2500, norm_y = 0.2500` |
| 28 | `test_pass3_boundary_coordinates_strictly_clamped` | Box at `(0, 0, 50, 50)` on `(1000, 1000)` | `norm_x >= 0.0, norm_y >= 0.0, norm_x <= 1.0, norm_y <= 1.0` |
| 29 | `test_pass3_rounding_to_4_decimal_places` | Box with fractional center (e.g., width=100 on canvas=300) | Rounded to exactly 4 decimal places (`0.3333`) |
| 30 | `test_pass3_normalized_dimensions_accuracy` | Box `(100, 100, 200, 50)` on `(800, 600)` | `norm_w = 0.2500, norm_h = 0.0833` |
| 31 | `test_pass3_dual_coordinates_embedded_in_metadata` | Verify workflow designer metadata | Contains `canvas_width, canvas_height, box_count` |

---

#### Class 5: `TestCompilerPass4ActionStepSynthesis` (Pass 4 Tests)
Validates conversion of visual boxes into atomic workflow steps:

| # | Test Name | Purpose / Input | Expected Assertion |
|---|---|---|---|
| 32 | `test_pass4_step1_is_focus_window_header` | Any valid layout | Step 1 is `FOCUS_WINDOW` with target window pattern |
| 33 | `test_pass4_text_box_full_action_chain` | Visual box with `action_type="type_text"` | Produces: `CLICK` -> `CLEAR_FIELD` -> `TYPE_TEXT` -> `KEY_PRESS(tab)` |
| 34 | `test_pass4_clear_before_false_omits_clear_step` | Text box with `clear_before=False` | Produces `CLICK` -> `TYPE_TEXT` -> `KEY_PRESS` (no `CLEAR_FIELD`) |
| 35 | `test_pass4_navigation_enter_generates_enter_key` | Box with `navigation="enter"` | Step parameters: `key="enter", repeat_count=1` |
| 36 | `test_pass4_navigation_none_omits_key_press` | Box with `navigation="none"` | No trailing `KEY_PRESS` step emitted |
| 37 | `test_pass4_click_box_generates_click_step` | Box with `action_type="click"` | Produces `CLICK` at normalized center coordinates |
| 38 | `test_pass4_submit_box_generates_submit_step` | Box with `action_type="submit"` | Produces `SUBMIT` with `submit_method="button_click"` |
| 39 | `test_pass4_timing_parameters_propagation` | Box with custom `pre_delay_ms=80, post_delay_ms=200, typing_speed_ms=35` | Steps inherit custom timing values |
| 40 | `test_pass4_variable_template_preservation` | Text box with `value="{{account_number}}"` | `StepParameters.text` exactly equals `"{{account_number}}"` |

---

#### Class 6: `TestCompilerPass5PeepholeOptimizer` (Pass 5 Tests)
Validates peephole optimizations, delay coalescing, and sequence indexing:

| # | Test Name | Purpose / Input | Expected Assertion |
|---|---|---|---|
| 41 | `test_pass5_click_to_tab_disabled_by_default` | 2 sequential text fields, default config | Both Field 1 and Field 2 retain `CLICK` steps |
| 42 | `test_pass5_click_to_tab_enabled_drops_second_click` | 2 sequential text fields, `click_to_tab=True` | Field 1 has `CLICK`, Field 2's `CLICK` is pruned |
| 43 | `test_pass5_click_to_tab_first_field_click_preserved` | Any layout with `click_to_tab=True` | Step 2 (First field click) is NEVER pruned |
| 44 | `test_pass5_click_to_tab_preserved_after_navigation_none` | Field 1 `navigation="none"`, Field 2 follows | Field 2's `CLICK` is preserved (Tab was not pressed) |
| 45 | `test_pass5_consecutive_delay_collapse_two_delays` | `DELAY(100)` followed by `DELAY(200)` | Collapsed into single `DELAY(300)` |
| 46 | `test_pass5_consecutive_delay_collapse_three_delays` | `DELAY(100)` + `DELAY(150)` + `DELAY(250)` | Collapsed into single `DELAY(500)` |
| 47 | `test_pass5_delay_collapse_disabled` | Two delays, `collapse_delays=False` | Both delays remain separate steps |
| 48 | `test_pass5_prune_empty_zero_ms_delay` | Step list containing `DELAY(0)` | 0ms delay step is completely pruned |
| 49 | `test_pass5_prune_duplicate_focus_window` | Two consecutive identical `FOCUS_WINDOW` | Second `FOCUS_WINDOW` step is dropped |
| 50 | `test_pass5_master_switch_disabled_passthrough` | Layout with `optimization.enabled=False` | Raw steps preserved without peephole drops |
| 51 | `test_pass5_strict_contiguous_sequence_reindexing` | Workflow after removals and collapses | `[s.sequence_index for s in steps] == list(range(1, len(steps) + 1))` |

---

#### Class 7: `TestCompilerIntegrationAndEdgeCases` (Integration & Stress)
Validates round-trip execution against `WorkflowRunner` and edge cases:

| # | Test Name | Purpose / Input | Expected Assertion |
|---|---|---|---|
| 52 | `test_roundtrip_banking_kyc_workflow_execution` | Complete Banking KYC layout compiled & executed against `MockWin32Driver` | Returns `KutomotoAuditLog` with `final_status="SUCCESS"`, mock driver records all 4 typed texts and submit |
| 53 | `test_roundtrip_telecom_sim_provisioning_execution` | Telecom SIM provisioning layout compiled & executed | Execution reaches `COMPLETED` state; MSISDN and ICCID typed |
| 54 | `test_edge_case_single_box_layout` | Layout with exactly 1 box | Compiles and executes cleanly without index out-of-range |
| 55 | `test_edge_case_stress_50_fields_performance` | 50 boxes in a 10x5 grid | Compiles in < 50ms (budget < 1.0s); exactly expected step count |
| 56 | `test_edge_case_dense_overlapping_boxes` | Boxes with overlapping coordinates | Compiles deterministically without infinite loop or crash |
| 57 | `test_edge_case_extremely_close_boxes_1px_gap` | Boxes separated by 1px vertically within band tolerance | Correctly sorted left-to-right by X |
| 58 | `test_edge_case_extreme_canvas_aspect_ratios` | Ultrawide (3840x1080) and portrait (1080x1920) canvases | Normalized coordinates calculate accurately in `[0.0, 1.0]` |
| 59 | `test_edge_case_unicode_and_special_characters` | Values with Arabic, Cyrillic, accented characters, and quotes | Workflow compiles and executes text injection without corruption |

---

## 4. Round-Trip Engine Interoperability Verification

A core design requirement is guaranteeing that the output of `compile_visual_layout_to_workflow(layout)` is immediately acceptable to `WorkflowRunner.execute(workflow)`.

### 4.1 Verification Data Flow

```
+-------------------------------------------------------------+
|             VisualFormLayout (Pydantic Model)               |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| compile_visual_layout_to_workflow(layout) -> KutomotoWorkflow|
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| WorkflowRunner(driver=MockWin32Driver()).execute(workflow)  |
+-------------------------------------------------------------+
                              |
       +----------------------+----------------------+
       |                                             |
       v                                             v
+-----------------------------+       +-----------------------------+
|  KutomotoAuditLog Returned  |       |   MockWin32Driver Records   |
| - final_status: "SUCCESS"   |       | - focus_history: [1001]     |
| - successful_steps: N       |       | - typed_text: ["Jane", ...] |
| - failed_steps: 0           |       | - key_presses: ["tab", ...] |
| - copyright: "90Studio"     |       | - clicks: [{"x":...}, ...]  |
+-----------------------------+       +-----------------------------+
```

### 4.2 Integration Test Implementation Pattern

```python
@pytest.mark.asyncio
async def test_roundtrip_banking_kyc_workflow_execution(monkeypatch):
    """
    Round-trip integration test verifying that compile_visual_layout_to_workflow
    output executes flawlessly against WorkflowRunner with MockWin32Driver.
    """
    monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

    # 1. Author Visual Form Layout
    layout = VisualFormLayout(
        name="Banking KYC Customer Onboarding",
        target_application=TargetApplication(
            type="windows_desktop",
            window_title_pattern=".*Banking KYC.*",
            process_name="msedge.exe",
        ),
        canvas=CanvasDimensions(width=1024, height=768),
        execution_settings=ExecutionSettings(countdown_seconds=0),
        optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
        boxes=[
            VisualBox(
                name="full_name",
                label="Full Customer Name",
                geometry=BoxGeometry(x=100, y=100, width=250, height=36),
                action_type="type_text",
                value="Jane Doe",
                navigation="tab",
                clear_before=True,
            ),
            VisualBox(
                name="account_number",
                label="Account Number",
                geometry=BoxGeometry(x=100, y=160, width=250, height=36),
                action_type="type_text",
                value="9876543210",
                navigation="tab",
                clear_before=True,
            ),
            VisualBox(
                name="btn_submit",
                label="Submit KYC",
                geometry=BoxGeometry(x=100, y=240, width=120, height=40),
                action_type="submit",
                navigation="none",
            ),
        ],
    )

    # 2. Compile to Workflow
    workflow = compile_visual_layout_to_workflow(layout)
    assert isinstance(workflow, KutomotoWorkflow)
    assert workflow.copyright == "Copyrights reserved to 90Studio"

    # 3. Execute via M2 WorkflowRunner
    driver = MockWin32Driver()
    driver.reset()
    runner = WorkflowRunner(driver=driver)

    audit = await runner.execute(workflow)

    # 4. Verify Execution Results
    assert audit.execution_summary.final_status == "SUCCESS"
    assert audit.execution_summary.failed_steps == 0
    assert runner.state == ExecutionState.COMPLETED
    assert 1001 in driver.focus_history
    assert "Jane Doe" in driver.typed_text
    assert "9876543210" in driver.typed_text
    assert any(k["key"] == "tab" for k in driver.key_presses)
```

---

## 5. Edge Cases & Robustness Analysis

### 5.1 Zero-Height / Zero-Width Boxes
- **Risk**: Division by zero or degenerate bounding boxes.
- **Handling**:
  - Schema layer: `BoxGeometry` enforces `width > 0, height > 0` via Pydantic field constraints.
  - Pass 1 layer: If raw dictionary input bypasses Pydantic, Pass 1 checks `gw <= 0 or gh <= 0` and raises `GeometryError("Box '...' has non-positive dimensions")`.

### 5.2 Dense & Clustered Fields within Band Tolerance
- **Risk**: Fields in table columns or form grids having slight vertical offsets (`y=100` vs `y=102`) being sorted into different rows.
- **Handling**:
  - Pass 2 computes dynamic band threshold $T = \text{band\_tolerance\_px}$ (default 24px).
  - Boxes within $|y - \text{anchor\_y}| \le T$ are clustered into the same horizontal band and sorted left-to-right by X.

### 5.3 RTL (Right-to-Left) and Non-Standard Flows
- **Risk**: Western reading order sorts left-to-right, which inverts RTL forms (Arabic/Hebrew).
- **Handling**:
  - Operators assign explicit sequence index badges (`sequence_index=1, 2, ...`).
  - Pass 2 prioritizes explicit sequence indices: if all boxes (or explicit subsets) define indices, spatial sorting is bypassed.

### 5.4 High-Density Forms (50+ Fields)
- **Risk**: Combinatorial explosion in sorting or quadratic delay searches.
- **Handling**:
  - Pass 2 sorting is $O(N \log N)$.
  - Pass 3 normalization is $O(N)$.
  - Pass 5 peephole scans linearly in $O(N)$ with single-pass lookahead/lookbehind.
  - Stress test 55 verifies 50 fields compile in $< 50\text{ms}$, well within the $1.0\text{s}$ SLA.

---

## 6. Synthesized Recommendations for Worker Agents

1. **In `src/kutomoto/designer/schema.py`**:
   - Implement `PeepholeOptimizationConfig` with defaults: `enabled=True`, `band_tolerance_px=24.0`, `click_to_tab=False`, `collapse_delays=True`, `remove_redundant_focus=True`, `prune_empty_delays=True`.
   - Implement `BoxGeometry` with computed properties: `center_x`, `center_y`, `right`, `bottom`.
   - Implement root validator on `VisualFormLayout` enforcing box containment within canvas bounds and unique box IDs.

2. **In `src/kutomoto/designer/compiler.py`**:
   - Implement `_pass5_optimize_peephole(ctx)` supporting Pattern A (click-to-tab), Pattern B (delay collapsing), and Pattern C (focus pruning + 1..N re-indexing).
   - Ensure `compile_visual_layout_to_workflow` accepts both `VisualFormLayout` and `dict`.
   - Provide `compile_visual_boxes_to_workflow` alias mapping `traversal_mode="tab_chained"` to `click_to_tab=True`.

3. **In `tests/test_compiler.py`**:
   - Implement the complete 7-class, 59-test suite detailed in Section 3.
   - Use `MockWin32Driver` and `KUTOMOTO_TEST_FAST=1` for rapid, zero-flake CI test execution.
