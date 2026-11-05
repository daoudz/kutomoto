# Milestone 3 Iteration 2 Empirical Challenge Report

```
====================================================================================================
Agent               : m3_it2_challenger_1 (Empirical Challenger & Verifier)
Roles               : critic, specialist
Parent Conversation : 59700fc9-320d-4ed3-b1db-2fc709fed831
Working Directory   : c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_it2_challenger_1\
Date                : 2026-11-05
Status              : Complete
Verdict             : PASS (100% Adversarial Test Pass Rate, Benchmark SLA Verified)
====================================================================================================
```

---

## 1. Observation

### 1.1 Empirical Verification Scope & Objectives

The empirical challenge suite was designed to stress-test the Milestone 3 compiler (`src/kutomoto/designer/compiler.py`) and schema (`src/kutomoto/designer/schema.py`) against four core challenge vectors:

1. **Spatial Band Sorting Stress**:
   - Dynamic 2D band clustering across randomized vertical coordinate jitter (±10px within 24px band tolerance).
   - Snake/zigzag layout reading order normalization.
   - Micro-subpixel offsets (1e-5 to 1e-1 px) within bands.
   - Explicit sequence index complete inversion and hybrid explicit/unindexed tail execution.
   - Pydantic schema validation enforcement for `sequence_index: ge=1` (rejecting 0, negative integers, and floats).
2. **Boundary and Extreme Geometries**:
   - 1x1 pixel canvas centering: exact `(0.5, 0.5)` normalized coordinate mapping.
   - 4K canvas (`3840x2160`): sub-pixel coordinate clamping at extreme corners and center.
   - Extreme canvas aspect ratios (`10000x200` ultra-wide, `200x10000` ultra-tall).
   - Sub-pixel box dimensions (`0.05px`) without float underflow.
   - Boundary overflow rejection (`x + w > cw`, `y + h > ch`, `x < 0`, `y < 0`, `w <= 0`, `h <= 0`) in both schema and raw dictionary compiler input.
3. **Large Layout Compilation Performance**:
   - Benchmark compilation latency on 100-field, 200-field, and 500-field layouts against the `< 100ms` SLA over 15 iterations.
   - Strict 4N+1 step count synthesis and contiguous 1..N sequence re-indexing verification.
4. **Peephole Optimizations Stress**:
   - Multi-block delay coalescing and 0ms delay pruning.
   - Settling delay transfer (`pre_delay_ms`) to `CLEAR_FIELD` and `TYPE_TEXT` under `click_to_tab=True`.
   - Defensive last-step settling delay synthesis into standalone `ActionType.DELAY` step.
   - Multi-field chain delay isolation (zero delay leakage across adjacent fields).
   - Standalone action click (`CLICK`, `CHECKBOX`, `SELECT`) preservation following Tab navigation.
   - Explicit `force_click=True` preservation on text and action fields.
   - Consecutive duplicate `FOCUS_WINDOW` pruning.

---

### 1.2 Benchmark Results (Target: < 100ms)

Compilation latency measured across 15 iterations per layout size (following 1 warmup execution) on Python 3.14 on Windows:

| Layout Size | Visual Boxes | Workflow Steps Generated | Min Latency (ms) | Avg Latency (ms) | Median Latency (ms) | P95 Latency (ms) | Max Latency (ms) | Target SLA | Verdict |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **100-field** | 100 | 401 | 5.73 ms | 6.29 ms | 6.07 ms | 9.54 ms | 9.54 ms | < 100.0 ms | **PASS** |
| **200-field** | 200 | 801 | 15.88 ms | 16.60 ms | 16.61 ms | 16.99 ms | 16.99 ms | < 100.0 ms | **PASS** |
| **500-field** | 500 | 2001 | 70.34 ms | 72.14 ms | 71.97 ms | 76.64 ms | 76.64 ms | < 100.0 ms | **PASS** |

*All layout sizes compile and validate well under the 100ms threshold (500-field max is 76.64ms, a 23.36ms safety margin).*

---

### 1.3 Test Suite Execution Summary

1. **New Empirical Adversarial Suite** (`tests/test_m3_it2_empirical_adversarial.py`):
   ```powershell
   python -m pytest tests/test_m3_it2_empirical_adversarial.py -v
   ```
   *Output*:
   ```
   ============================= test session starts =============================
   collected 30 items
   tests/test_m3_it2_empirical_adversarial.py::TestSpatialBandSortingAdversarial::test_jittered_coordinates_dynamic_clustering PASSED [  3%]
   tests/test_m3_it2_empirical_adversarial.py::TestSpatialBandSortingAdversarial::test_band_tolerance_boundary_exact_split PASSED [  6%]
   tests/test_m3_it2_empirical_adversarial.py::TestSpatialBandSortingAdversarial::test_zigzag_reading_order_normalization PASSED [ 10%]
   tests/test_m3_it2_empirical_adversarial.py::TestSpatialBandSortingAdversarial::test_subpixel_micro_offsets PASSED [ 13%]
   tests/test_m3_it2_empirical_adversarial.py::TestSpatialBandSortingAdversarial::test_explicit_sequence_overrides_spatial_inversion PASSED [ 16%]
   tests/test_m3_it2_empirical_adversarial.py::TestSpatialBandSortingAdversarial::test_hybrid_explicit_and_spatial_strict_tail PASSED [ 20%]
   tests/test_m3_it2_empirical_adversarial.py::TestSpatialBandSortingAdversarial::test_sequence_index_pydantic_ge_1_rejection PASSED [ 23%]
   tests/test_m3_it2_empirical_adversarial.py::TestSpatialBandSortingAdversarial::test_sequence_index_valid_integers_accepted PASSED [ 26%]
   tests/test_m3_it2_empirical_adversarial.py::TestSpatialBandSortingAdversarial::test_sequence_index_tie_breaking PASSED [ 30%]
   tests/test_m3_it2_empirical_adversarial.py::TestExtremeGeometriesAdversarial::test_1x1_canvas_exact_centering PASSED [ 33%]
   tests/test_m3_it2_empirical_adversarial.py::TestExtremeGeometriesAdversarial::test_1x1_canvas_subpixel_quadrants PASSED [ 36%]
   tests/test_m3_it2_empirical_adversarial.py::TestExtremeGeometriesAdversarial::test_4k_canvas_tiny_corner_and_center PASSED [ 40%]
   tests/test_m3_it2_empirical_adversarial.py::TestExtremeGeometriesAdversarial::test_extreme_aspect_ratios PASSED [ 43%]
   tests/test_m3_it2_empirical_adversarial.py::TestExtremeGeometriesAdversarial::test_subpixel_dimensions_precision PASSED [ 46%]
   tests/test_m3_it2_empirical_adversarial.py::TestExtremeGeometriesAdversarial::test_boundary_overflow_rejections PASSED [ 50%]
   tests/test_m3_it2_empirical_adversarial.py::TestExtremeGeometriesAdversarial::test_boundary_float_tolerance_boundary PASSED [ 53%]
   tests/test_m3_it2_empirical_adversarial.py::TestLargeLayoutCompilationBenchmarks::test_100_field_benchmark_under_100ms PASSED [ 56%]
   tests/test_m3_it2_empirical_adversarial.py::TestLargeLayoutCompilationBenchmarks::test_200_field_benchmark_under_100ms PASSED [ 60%]
   tests/test_m3_it2_empirical_adversarial.py::TestLargeLayoutCompilationBenchmarks::test_500_field_benchmark_under_100ms PASSED [ 63%]
   tests/test_m3_it2_empirical_adversarial.py::TestLargeLayoutCompilationBenchmarks::test_step_count_and_sequence_integrity PASSED [ 66%]
   tests/test_m3_it2_empirical_adversarial.py::TestPeepholeOptimizationsAdversarial::test_delay_coalescing_multi_block PASSED [ 70%]
   tests/test_m3_it2_empirical_adversarial.py::TestPeepholeOptimizationsAdversarial::test_empty_delay_pruning PASSED [ 73%]
   tests/test_m3_it2_empirical_adversarial.py::TestPeepholeOptimizationsAdversarial::test_settling_delay_transfer_to_clear_field PASSED [ 76%]
   tests/test_m3_it2_empirical_adversarial.py::TestPeepholeOptimizationsAdversarial::test_settling_delay_transfer_to_type_text_when_no_clear PASSED [ 80%]
   tests/test_m3_it2_empirical_adversarial.py::TestPeepholeOptimizationsAdversarial::test_settling_delay_transfer_defensive_last_step PASSED [ 83%]
   tests/test_m3_it2_empirical_adversarial.py::TestPeepholeOptimizationsAdversarial::test_settling_delay_multi_field_chain_no_leakage PASSED [ 86%]
   tests/test_m3_it2_empirical_adversarial.py::TestPeepholeOptimizationsAdversarial::test_force_click_preservation_on_text_and_action_boxes PASSED [ 90%]
   tests/test_m3_it2_empirical_adversarial.py::TestPeepholeOptimizationsAdversarial::test_standalone_action_clicks_preserved_without_force_click PASSED [ 93%]
   tests/test_m3_it2_empirical_adversarial.py::TestPeepholeOptimizationsAdversarial::test_duplicate_focus_window_pruning PASSED [ 96%]
   tests/test_m3_it2_empirical_adversarial.py::TestPeepholeOptimizationsAdversarial::test_peephole_master_switch_disabled PASSED [100%]
   ============================= 30 passed in 1.16s ==============================
   ```

2. **Standard Compiler Suite** (`tests/test_compiler.py`):
   ```powershell
   python -m pytest tests/test_compiler.py -v
   ```
   *Output*: `73 passed in 7.17s` (100% pass).

3. **Challenger 1 Suite** (`tests/test_compiler_empirical_challenge.py`):
   ```powershell
   python -m pytest tests/test_compiler_empirical_challenge.py -v
   ```
   *Output*: `24 passed in 0.29s` (100% pass).

4. **Total Milestone 3 Compiler Tests**:
   - `30 + 73 + 24 = 127 passed, 0 failed` (100% pass).

5. **Linter Verification**:
   ```powershell
   python -m ruff check src/ tests/
   ```
   *Output*: `All checks passed!` (0 lint errors across entire repository).

---

### 1.4 Verbatim Harness Script Code

The empirical test suite was committed to `tests/test_m3_it2_empirical_adversarial.py`. Key harness fixtures and tests:

```python
# [Snippet: Spatial Band Sorting Stress]
def test_jittered_coordinates_dynamic_clustering(self):
    random.seed(42)
    rows, cols, band_tolerance, row_spacing = 5, 6, 24.0, 80.0
    boxes = []
    for r in range(rows):
        base_y = 100.0 + r * row_spacing
        row_boxes = []
        for c in range(cols):
            jitter_y = random.uniform(-10.0, 10.0)
            row_boxes.append(_box(f"r{r}_c{c}", x=50.0 + c * 150.0, y=base_y + jitter_y, w=100.0, h=30.0))
        random.shuffle(row_boxes)
        boxes.extend(row_boxes)
    random.shuffle(boxes)
    sorted_boxes = _spatial_band_sort(boxes, band_tolerance_px=band_tolerance)
    expected_names = [f"r{r}_c{c}" for r in range(rows) for c in range(cols)]
    assert [b.name for b in sorted_boxes] == expected_names

# [Snippet: Settling Delay Transfer under click_to_tab]
def test_settling_delay_transfer_to_clear_field(self):
    b1 = _box("b1", x=10, y=10, nav=NavigationAction.TAB)
    b2 = _box("b2", x=10, y=50, nav=NavigationAction.TAB, clear_before=True, pre_delay=400)
    opt = PeepholeOptimizationConfig(click_to_tab=True)
    wf = compile_visual_layout_to_workflow(_layout([b1, b2], opt=opt))
    b2_steps = [s for s in wf.steps if "b2" in (s.label or "")]
    assert b2_steps[0].action_type == ActionType.CLEAR_FIELD
    assert b2_steps[0].pre_delay_ms == 400
    assert b2_steps[1].action_type == ActionType.TYPE_TEXT
    assert b2_steps[1].pre_delay_ms == 0

# [Snippet: Standalone Action Clicks Preservation]
def test_standalone_action_clicks_preserved_without_force_click(self):
    b1 = _box("f1", x=10, y=10, nav=NavigationAction.TAB)
    b_click = _box("btn", x=10, y=50, action=DesignerActionType.CLICK, nav=NavigationAction.TAB, force_click=False)
    b_cb = _box("chk", x=10, y=90, action=DesignerActionType.CHECKBOX, nav=NavigationAction.TAB, force_click=False)
    b_sel = _box("dropdown", x=10, y=130, action=DesignerActionType.SELECT, nav=NavigationAction.TAB, force_click=False)
    b_sub = _box("submit_btn", x=10, y=170, action=DesignerActionType.SUBMIT)
    opt = PeepholeOptimizationConfig(click_to_tab=True)
    wf = compile_visual_layout_to_workflow(_layout([b1, b_click, b_cb, b_sel, b_sub], opt=opt))
    clicks = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
    assert any("f1" in lbl for lbl in clicks)
    assert any("btn" in lbl for lbl in clicks)
    assert any("chk" in lbl for lbl in clicks)
    assert any("dropdown" in lbl for lbl in clicks)
```

---

## 2. Logic Chain

### 2.1 Spatial Band Sorting and Sequence Index Invariants
1. **Dynamic Band Clustering**: In `_spatial_band_sort` (`compiler.py:47-85`), boxes are sorted primarily by Y coordinate, and grouped into a band while `abs(b.geometry.y - anchor_y) <= tolerance`. When row spacing exceeds vertical jitter, every box in each row is captured in the active band, and the secondary sort `key=lambda b: (b.geometry.x, b.geometry.y)` orders columns from left to right. Even under ±10px random vertical noise, 100% of boxes in the 30-field jitter test sorted into exact Western reading order.
2. **Explicit vs Spatial Precedence**: In Pass 2 (`compiler.py:412-438`), `explicit_boxes` filters `b.sequence_index is not None and b.sequence_index >= 1`. Hybrid layouts strictly concatenate `ordered_explicit + ordered_unindexed`, ensuring author-defined execution order always runs first, with unindexed visual elements executing at the tail.
3. **1-Based Schema Validation**: `VisualBox.sequence_index` in `schema.py:154-158` specifies `ge=1`. Supplying 0, negative values (-1, -500), or non-integers immediately triggers Pydantic `ValidationError` at input parsing, eliminating off-by-one ordering bugs and matching `SPECIFICATION.md` Section 7.2.

### 2.2 Boundary Geometries and Normalization Robustness
1. **1x1 Pixel Canvas Centering**: In `VisualFormLayout.get_normalized_box` (`schema.py:348-373`), center coordinates are calculated as `(geom.x + geom.width / 2.0) / cw`. For a 1x1 box at `(0, 0)`, center is `0.5 / 1.0 = 0.5`. Four 0.5x0.5 quadrants yield exact quadrant midpoints `(0.25, 0.25)`, `(0.75, 0.25)`, `(0.25, 0.75)`, and `(0.75, 0.75)`.
2. **4K Sub-pixel Clamping**: For a 4K canvas (`3840x2160`), top-left 1x1 box centers at `(0.5 / 3840, 0.5 / 2160) = (0.0001, 0.0002)`. Bottom-right 1x1 box centers at `(3839.5 / 3840, 2159.5 / 2160) = (0.99987, 0.99977)`, which rounds cleanly to `(0.9999, 0.9998)`. Clamping guards (`max(0.0, min(1.0, ...))`) prevent out-of-bounds coordinate overflow.
3. **Strict Boundary Guards**: Both schema model validation (`schema.py:328-345`) and dictionary Pass 1 validation (`compiler.py:276-331`) enforce `geom.right <= cw + 1e-4` and `geom.bottom <= ch + 1e-4`. Boundary violations, negative origins, or zero dimensions raise immediate `GeometryError` or `ValidationError`.

### 2.3 Compilation Scalability and Performance (< 100ms)
1. **Linear Time Complexity**: Compilation is $O(N \log N)$ due to sorting in Pass 2 and linear lookahead in Pass 5.
2. **Empirical Benchmarks**:
   - 100 fields: 6.29ms average latency (93.71ms headroom).
   - 200 fields: 16.60ms average latency (83.40ms headroom).
   - 500 fields: 72.14ms average latency (27.86ms headroom).
3. **Contiguous Indexing**: Across all benchmark scales, Pass 5 re-indexes all emitted steps into a strictly contiguous sequence `1..N` without gaps or duplicate indices.

### 2.4 Peephole Optimizations Correctness
1. **Delay Coalescing & Pruning**: Consecutive `ActionType.DELAY` steps sum durations (`150ms + 250ms -> 400ms`), while non-consecutive delays preserve their positions. 0ms delays are discarded when `prune_empty_delays=True`.
2. **Settling Delay Transfer**: Under `click_to_tab=True`, when an auxiliary focus anchor click is pruned, its `pre_delay_ms` transfers directly to `pruned_focus[i + 1].pre_delay_ms`. If `clear_before=True`, `CLEAR_FIELD` receives the settling delay; if `clear_before=False`, `TYPE_TEXT` receives it. In the edge case where the pruned click is the tail step, a standalone `DELAY` step is generated.
3. **Action Click Immunity**: Standalone action clicks (`DesignerActionType.CLICK`, `CHECKBOX`, `SELECT`) carry `_is_action_click=True` and are never pruned by `click_to_tab`, ensuring interactive elements (checkbox toggles, dropdowns, submit buttons) execute reliably.

---

## 3. Caveats

1. **Non-Milestone 3 Test Failures**: During regression testing across the entire repository, two tests in `tests/test_roundtrip_execution_challenge.py` (authored by concurrent agent `m3_it2_challenger_2`) failed:
   - `test_escape_abort_during_settling_delay`: Asserted that an emergency Escape abort injected during a 2000ms delay would abort in `< 1.0s`, but the runner took 2.806s because `WorkflowRunner` executes sleep synchronously within handlers.
   - `test_credential_masking_in_audit_events`: Asserted `'***MASKED***' in event.parameters_summary`, whereas the runner formats secrets as `'********' (6 chars, masked)`.
   *Both of these failures pertain exclusively to `kutomoto.engine.runner` and `safety.py` (Milestone 2 runtime execution) and do not affect the Milestone 3 Designer Compiler or Schema.*
2. **No other caveats**: All 127 compiler unit, integration, and empirical challenge tests pass with 100% success.

---

## 4. Conclusion

The Milestone 3 Visual Form Designer Compiler and Schema fully satisfy all architectural requirements, edge case invariants, and performance specifications:
- Dynamic spatial band sorting is robust against coordinate jitter, sub-pixel offsets, and zigzag patterns.
- Sequence indexing strictly enforces 1-based indexing (`ge=1`), prioritizing explicit sequences before tail spatial reading order.
- Boundary geometries and dual-coordinate normalizations clamp reliably on 1x1 and 4K displays.
- Large layout compilation latency satisfies the `< 100ms` SLA across 100, 200, and 500-field forms.
- Peephole optimizations coalesce delays, preserve settling delays, and protect interactive action clicks.

### Final Verdict: **PASS**

---

## 5. Verification Method

To independently reproduce the empirical findings:

1. **Run the Milestone 3 Iteration 2 Empirical Adversarial Suite (30 tests)**:
   ```powershell
   python -m pytest tests/test_m3_it2_empirical_adversarial.py -v
   ```
   *Expected Output*: `30 passed in ~1.2s`.

2. **Run All Milestone 3 Compiler Tests (127 tests)**:
   ```powershell
   python -m pytest tests/test_compiler.py tests/test_compiler_empirical_challenge.py tests/test_m3_it2_empirical_adversarial.py -v
   ```
   *Expected Output*: `127 passed in ~8.5s`.

3. **Run Large Layout Latency Benchmark Script**:
   ```powershell
   python -c "import time, sys; sys.path.insert(0, 'src'); from kutomoto.designer.schema import *; from kutomoto.designer.compiler import compile_visual_layout_to_workflow;
for n, rows, cols in [(100, 10, 10), (200, 20, 10), (500, 50, 10)]:
    boxes = [VisualBox(name=f'f_{r}_{c}', geometry=BoxGeometry(x=c*120.0+10.0, y=r*25.0+10.0, width=100.0, height=20.0)) for r in range(rows) for c in range(cols)]
    layout = VisualFormLayout(name=f'B_{n}', canvas=CanvasDimensions(width=1500, height=1500), target_application=TargetApplicationSpec(window_title_pattern='App'), boxes=boxes)
    _ = compile_visual_layout_to_workflow(layout)
    timings = []
    for _ in range(10):
        t0 = time.perf_counter()
        compile_visual_layout_to_workflow(layout)
        timings.append((time.perf_counter() - t0) * 1000.0)
    print(f'{n}-field: min={min(timings):.2f}ms, avg={sum(timings)/len(timings):.2f}ms, max={max(timings):.2f}ms')
"
   ```
   *Expected Output*: All averages and maximums `< 100.0ms` (e.g., 100-field ~6ms, 200-field ~16ms, 500-field ~72ms).

4. **Verify Linter Cleanliness**:
   ```powershell
   python -m ruff check src/ tests/
   ```
   *Expected Output*: `All checks passed!`.

### Invalidation Conditions
- Any failure in `tests/test_m3_it2_empirical_adversarial.py` or `tests/test_compiler.py`.
- Any compilation latency exceeding 100.0ms for up to 500 fields.
- Acceptance of `sequence_index < 1` in `VisualBox`.
- Dropping or unhandled pruning of standalone action clicks (`CLICK`, `CHECKBOX`, `SELECT`) following Tab navigation.
- Loss of configured settling delay `box.timing.pre_delay_ms` when an anchor click is pruned under `click_to_tab=True`.
