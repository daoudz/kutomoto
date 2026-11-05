"""
Empirical Stress Test Suite for Milestone 3: Compiler and Schema
Testing spatial band sorting, extreme geometries, large layout scalability, and peephole optimizations.
Copyrights reserved to 90Studio
"""

import math
from pathlib import Path
import sys
import time
from typing import List, Tuple

# Ensure src/ is on sys.path
src_dir = Path(__file__).resolve().parents[3] / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import pytest
from pydantic import ValidationError

from kutomoto.designer.compiler import (
    _spatial_band_sort,
    compile_visual_boxes_to_workflow,
    compile_visual_layout_to_workflow,
)
from kutomoto.designer.exceptions import (
    CompilationError,
    DuplicateBoxIdError,
    EmptyLayoutError,
    GeometryError,
)
from kutomoto.designer.schema import (
    BoxGeometry,
    CanvasDimensions,
    DesignerActionType,
    NavigationAction,
    PeepholeOptimizationConfig,
    TargetApplicationSpec,
    VisualBox,
    VisualFormLayout,
)
from kutomoto.engine.schema import ActionType, KutomotoWorkflow


def make_box(
    name: str,
    x: float,
    y: float,
    w: float = 100.0,
    h: float = 30.0,
    seq: int = None,
    action: DesignerActionType = DesignerActionType.TYPE_TEXT,
    val: str = "test",
    nav: NavigationAction = NavigationAction.TAB,
    force_click: bool = False,
    clear_before: bool = True,
    box_id: str = None,
) -> VisualBox:
    kw = {
        "name": name,
        "geometry": BoxGeometry(x=x, y=y, width=w, height=h),
        "action_type": action,
        "value": val,
        "navigation": nav,
        "force_click": force_click,
        "clear_before": clear_before,
    }
    if seq is not None:
        kw["sequence_index"] = seq
    if box_id is not None:
        kw["id"] = box_id
    return VisualBox(**kw)


def make_layout(
    boxes: List[VisualBox],
    cw: float = 1920.0,
    ch: float = 1080.0,
    opt: PeepholeOptimizationConfig = None,
) -> VisualFormLayout:
    return VisualFormLayout(
        name="Stress Layout",
        canvas=CanvasDimensions(width=cw, height=ch),
        target_application=TargetApplicationSpec(window_title_pattern=".*Chrome.*"),
        boxes=boxes,
        optimization=opt or PeepholeOptimizationConfig(),
    )


# ==============================================================================
# VECTOR 1: SPATIAL BAND SORTING STRESS
# ==============================================================================

def test_v1_subpixel_and_1px_vertical_offsets():
    print("\n--- Running Vector 1: Subpixel & 1px Vertical Offsets ---")
    
    # 1. Subpixel offset: y=100.0, y=100.0001, y=100.5, y=100.999
    # All within default band tolerance 24px, different X
    boxes = [
        make_box("b4", x=400.0, y=100.999),
        make_box("b1", x=100.0, y=100.0),
        make_box("b3", x=300.0, y=100.5),
        make_box("b2", x=200.0, y=100.0001),
    ]
    sorted_boxes = _spatial_band_sort(boxes, band_tolerance_px=24.0)
    names = [b.name for b in sorted_boxes]
    print(f"Subpixel offset sort order: {names}")
    assert names == ["b1", "b2", "b3", "b4"], f"Expected left-to-right order b1..b4, got {names}"

    # 2. 1px vertical offset: y=100, y=101, y=102, y=103
    boxes_1px = [
        make_box("b4", x=400.0, y=103.0),
        make_box("b2", x=200.0, y=101.0),
        make_box("b1", x=100.0, y=100.0),
        make_box("b3", x=300.0, y=102.0),
    ]
    sorted_1px = _spatial_band_sort(boxes_1px, band_tolerance_px=24.0)
    names_1px = [b.name for b in sorted_1px]
    print(f"1px offset sort order: {names_1px}")
    assert names_1px == ["b1", "b2", "b3", "b4"], f"Expected b1..b4, got {names_1px}"

    # 3. Exact boundary condition around tolerance: 24.0 vs 24.0001
    b_anchor = make_box("anchor", x=100.0, y=100.0)
    b_inside = make_box("inside", x=50.0, y=124.0)     # dy = 24.0 <= 24.0 -> same band
    b_outside = make_box("outside", x=10.0, y=124.001) # dy = 24.001 > 24.0 -> new band
    
    sorted_bound = _spatial_band_sort([b_anchor, b_inside], band_tolerance_px=24.0)
    # b_inside is x=50, b_anchor is x=100. In same band, b_inside should be first!
    assert [b.name for b in sorted_bound] == ["inside", "anchor"]

    sorted_bound2 = _spatial_band_sort([b_anchor, b_outside], band_tolerance_px=24.0)
    # b_outside is in next band because dy > 24.0! Even though x=10 < 100, anchor band comes first!
    assert [b.name for b in sorted_bound2] == ["anchor", "outside"]
    print("Subpixel & 1px offsets passed successfully.")


def test_v1_zigzag_and_spiral_layouts():
    print("\n--- Running Vector 1: Zigzag & Spiral Layouts ---")
    
    # Zigzag layout across 3 rows:
    # Row 1 (y=50): left to right (x=10, x=100, x=200)
    # Row 2 (y=150): right to left (x=200, x=100, x=10)
    # Row 3 (y=250): left to right (x=10, x=100, x=200)
    boxes = [
        make_box("r1_c1", x=10, y=50),
        make_box("r1_c2", x=100, y=50),
        make_box("r1_c3", x=200, y=50),
        make_box("r2_c3", x=200, y=150),
        make_box("r2_c2", x=100, y=150),
        make_box("r2_c1", x=10, y=150),
        make_box("r3_c1", x=10, y=250),
        make_box("r3_c2", x=100, y=250),
        make_box("r3_c3", x=200, y=250),
    ]
    # Without sequence_index, spatial band sort enforces Western order (left-to-right on ALL bands)
    sorted_unindexed = _spatial_band_sort(boxes)
    names_unindexed = [b.name for b in sorted_unindexed]
    expected_unindexed = [
        "r1_c1", "r1_c2", "r1_c3",
        "r2_c1", "r2_c2", "r2_c3", # Row 2 sorted left to right
        "r3_c1", "r3_c2", "r3_c3",
    ]
    assert names_unindexed == expected_unindexed, f"Unindexed zigzag: got {names_unindexed}"
    print("Unindexed zigzag normalized to Western reading order: OK.")

    # Now spiral layout with explicit sequence_index:
    # Spiral: Top-Left (1) -> Top-Right (2) -> Bottom-Right (3) -> Bottom-Left (4) -> Center (5)
    spiral_boxes = [
        make_box("center", x=200, y=200, seq=5),
        make_box("top_right", x=400, y=50, seq=2),
        make_box("bottom_right", x=400, y=400, seq=3),
        make_box("top_left", x=50, y=50, seq=1),
        make_box("bottom_left", x=50, y=400, seq=4),
    ]
    layout = make_layout(spiral_boxes)
    wf = compile_visual_layout_to_workflow(layout)
    step_labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
    print(f"Spiral execution order: {step_labels}")
    assert "top_left" in step_labels[0]
    assert "top_right" in step_labels[1]
    assert "bottom_right" in step_labels[2]
    assert "bottom_left" in step_labels[3]
    assert "center" in step_labels[4]
    print("Explicit spiral layout strictly honored: OK.")


def test_v1_sequence_index_strict_override():
    print("\n--- Running Vector 1: Sequence Index Strict Override ---")
    
    # 4 boxes placed in reverse spatial order:
    # Physical position: b_tl at (0,0), b_tr at (500, 0), b_bl at (0, 500), b_br at (500, 500)
    # Explicit sequence: b_br = 1, b_bl = 2, b_tr = 3, b_tl = 4
    boxes = [
        make_box("b_tl", x=0, y=0, seq=4),
        make_box("b_tr", x=500, y=0, seq=3),
        make_box("b_bl", x=0, y=500, seq=2),
        make_box("b_br", x=500, y=500, seq=1),
    ]
    layout = make_layout(boxes)
    wf = compile_visual_layout_to_workflow(layout)
    click_steps = [s for s in wf.steps if s.action_type == ActionType.CLICK]
    labels = [s.label for s in click_steps]
    print(f"Reverse sequence index results: {labels}")
    assert "b_br" in labels[0]
    assert "b_bl" in labels[1]
    assert "b_tr" in labels[2]
    assert "b_tl" in labels[3]

    # Duplicate sequence indices: what is the tie-breaker?
    # Both have seq=1: box_y200 at y=200, box_y100 at y=100.
    dup_boxes = [
        make_box("dup_y200", x=100, y=200, seq=1),
        make_box("dup_y100", x=100, y=100, seq=1),
    ]
    wf_dup = compile_visual_layout_to_workflow(make_layout(dup_boxes))
    dup_labels = [s.label for s in wf_dup.steps if s.action_type == ActionType.CLICK]
    print(f"Duplicate sequence index tie-breaker results: {dup_labels}")
    assert "dup_y100" in dup_labels[0], "Tie-breaker must be y then x"
    assert "dup_y200" in dup_labels[1]

    # Hybrid layout: Some boxes explicit seq, some unindexed (seq=None or seq=0)
    hybrid_boxes = [
        make_box("unindexed_top", x=0, y=0, seq=None),
        make_box("explicit_bottom", x=500, y=500, seq=1),
        make_box("zero_seq", x=10, y=10, seq=0),
    ]
    wf_hybrid = compile_visual_layout_to_workflow(make_layout(hybrid_boxes))
    hybrid_labels = [s.label for s in wf_hybrid.steps if s.action_type == ActionType.CLICK]
    print(f"Hybrid layout results: {hybrid_labels}")
    # explicit_bottom (seq=1) must precede unindexed boxes!
    assert "explicit_bottom" in hybrid_labels[0]
    # between unindexed_top and zero_seq: unindexed_top (0,0) before zero_seq (10,10)
    assert "unindexed_top" in hybrid_labels[1]
    assert "zero_seq" in hybrid_labels[2]
    print("Sequence index strict override verified successfully.")


# ==============================================================================
# VECTOR 2: EXTREME GEOMETRIES & BOUNDARY CONDITIONS
# ==============================================================================

def test_v2_boundary_overflow_checks():
    print("\n--- Running Vector 2: Boundary Overflow Checks ---")
    
    # 1. Box with right edge exceeding canvas width
    # Canvas = 1000x1000. Box x=900, w=101 -> right = 1001 > 1000
    try:
        make_layout([make_box("overflow_x", x=900, y=100, w=101, h=30)], cw=1000, ch=1000)
        assert False, "Should have failed validation for right edge overflow"
    except (ValueError, ValidationError) as e:
        print(f"Caught expected right edge overflow: {type(e).__name__}")

    # 2. Box with bottom edge exceeding canvas height
    # Canvas = 1000x1000. Box y=900, h=101 -> bottom = 1001 > 1000
    try:
        make_layout([make_box("overflow_y", x=100, y=900, w=100, h=101)], cw=1000, ch=1000)
        assert False, "Should have failed validation for bottom edge overflow"
    except (ValueError, ValidationError) as e:
        print(f"Caught expected bottom edge overflow: {type(e).__name__}")

    # 3. Raw dict bypass test: pass dict directly to compile_visual_layout_to_workflow
    try:
        compile_visual_layout_to_workflow({
            "name": "Dict Overflow X",
            "canvas": {"width": 1000, "height": 1000},
            "target": {"window_title_pattern": ".*"},
            "boxes": [{"name": "b1", "geometry": {"x": 950, "y": 100, "width": 60, "height": 30}}]
        })
        assert False, "Dict compilation should fail on right edge overflow"
    except GeometryError as e:
        print(f"Caught expected GeometryError on dict overflow: {e}")

    try:
        compile_visual_layout_to_workflow({
            "name": "Dict Overflow Y",
            "canvas": {"width": 1000, "height": 1000},
            "target": {"window_title_pattern": ".*"},
            "boxes": [{"name": "b1", "geometry": {"x": 100, "y": 950, "width": 60, "height": 60}}]
        })
        assert False, "Dict compilation should fail on bottom edge overflow"
    except GeometryError as e:
        print(f"Caught expected GeometryError on dict overflow: {e}")


def test_v2_one_by_one_pixels_and_extreme_dimensions():
    print("\n--- Running Vector 2: 1x1 Pixel Boxes & 1x1 Canvas ---")
    
    # 1. 1x1 pixel canvas and 1x1 box at (0, 0)
    layout_1x1 = make_layout([make_box("pixel_box", x=0, y=0, w=1, h=1)], cw=1.0, ch=1.0)
    wf_1x1 = compile_visual_layout_to_workflow(layout_1x1)
    click_step = next(s for s in wf_1x1.steps if s.action_type == ActionType.CLICK)
    print(f"1x1 box click step params: norm_x={click_step.parameters.norm_x}, norm_y={click_step.parameters.norm_y}")
    # center is (0 + 0.5) / 1.0 = 0.5
    assert click_step.parameters.norm_x == 0.5
    assert click_step.parameters.norm_y == 0.5

    # 2. 1x1 pixel box on 4K canvas (3840 x 2160)
    layout_4k = make_layout([make_box("tiny_box", x=3839, y=2159, w=1, h=1)], cw=3840, ch=2160)
    wf_4k = compile_visual_layout_to_workflow(layout_4k)
    click_4k = next(s for s in wf_4k.steps if s.action_type == ActionType.CLICK)
    print(f"Tiny box on 4K: norm_x={click_4k.parameters.norm_x}, norm_y={click_4k.parameters.norm_y}")
    assert 0.0 <= click_4k.parameters.norm_x <= 1.0
    assert 0.0 <= click_4k.parameters.norm_y <= 1.0

    # 3. Sub-pixel dimensions: 0.5px x 0.5px box at (0.25, 0.25)
    layout_sub = make_layout([make_box("subpixel_box", x=0.25, y=0.25, w=0.5, h=0.5)], cw=100, ch=100)
    wf_sub = compile_visual_layout_to_workflow(layout_sub)
    click_sub = next(s for s in wf_sub.steps if s.action_type == ActionType.CLICK)
    assert click_sub.parameters.norm_x == 0.005 # (0.25 + 0.25)/100 = 0.5/100 = 0.005
    print("1x1 and sub-pixel geometries verified successfully.")


def test_v2_negative_and_zero_inputs():
    print("\n--- Running Vector 2: Negative and Zero Inputs ---")
    
    # 1. Negative coordinates: x=-1, y=0
    try:
        BoxGeometry(x=-1.0, y=0.0, width=10.0, height=10.0)
        assert False, "Negative x should fail BoxGeometry"
    except ValidationError as e:
        print(f"Caught negative x BoxGeometry validation error: {e.errors()[0]['type']}")

    try:
        BoxGeometry(x=0.0, y=-0.0001, width=10.0, height=10.0)
        assert False, "Negative y should fail BoxGeometry"
    except ValidationError as e:
        print(f"Caught negative y BoxGeometry validation error: {e.errors()[0]['type']}")

    # 2. Zero dimensions: width=0, height=0
    try:
        BoxGeometry(x=0.0, y=0.0, width=0.0, height=10.0)
        assert False, "Zero width should fail BoxGeometry"
    except ValidationError as e:
        print(f"Caught zero width BoxGeometry validation error: {e.errors()[0]['type']}")

    try:
        BoxGeometry(x=0.0, y=0.0, width=10.0, height=0.0)
        assert False, "Zero height should fail BoxGeometry"
    except ValidationError as e:
        print(f"Caught zero height BoxGeometry validation error: {e.errors()[0]['type']}")

    # 3. Canvas zero and negative dimensions
    try:
        CanvasDimensions(width=0, height=1080)
        assert False, "Zero canvas width should fail"
    except ValidationError:
        pass

    try:
        CanvasDimensions(width=1920, height=-100)
        assert False, "Negative canvas height should fail"
    except ValidationError:
        pass

    # 4. Dict input with negative coordinates
    try:
        compile_visual_layout_to_workflow({
            "canvas": {"width": 1000, "height": 1000},
            "boxes": [{"name": "b1", "geometry": {"x": -5, "y": 10, "width": 10, "height": 10}}]
        })
        assert False, "Dict with negative coordinate should raise GeometryError"
    except GeometryError as e:
        print(f"Caught GeometryError for negative coordinate: {e}")

    # 5. Dict input with zero dimensions
    try:
        compile_visual_layout_to_workflow({
            "canvas": {"width": 1000, "height": 1000},
            "boxes": [{"name": "b1", "geometry": {"x": 5, "y": 10, "width": 0, "height": 10}}]
        })
        assert False, "Dict with zero dimension should raise GeometryError"
    except GeometryError as e:
        print(f"Caught GeometryError for zero dimension: {e}")

    print("Negative and zero input guards verified successfully.")


# ==============================================================================
# VECTOR 3: LARGE LAYOUT SCALABILITY & SPEED BENCHMARK
# ==============================================================================

def test_v3_large_layout_scalability():
    print("\n--- Running Vector 3: Large Layout Scalability Benchmark ---")
    
    # 1. 100-field form
    # 10 rows x 10 columns
    boxes_100: List[VisualBox] = []
    for r in range(10):
        for c in range(10):
            boxes_100.append(
                make_box(
                    f"field_r{r}_c{c}",
                    x=c * 150.0 + 10.0,
                    y=r * 60.0 + 10.0,
                    w=120.0,
                    h=40.0,
                )
            )
    assert len(boxes_100) == 100
    layout_100 = make_layout(boxes_100, cw=2000.0, ch=1000.0)

    # Warmup
    _ = compile_visual_layout_to_workflow(layout_100)

    # Benchmark 100 fields over 10 iterations
    timings_100 = []
    for _ in range(10):
        t0 = time.perf_counter()
        wf_100 = compile_visual_layout_to_workflow(layout_100)
        dt = (time.perf_counter() - t0) * 1000.0  # ms
        timings_100.append(dt)
        assert len(wf_100.steps) > 100

    avg_100 = sum(timings_100) / len(timings_100)
    max_100 = max(timings_100)
    min_100 = min(timings_100)
    print(f"100-Field Form (10 runs): avg={avg_100:.2f}ms, min={min_100:.2f}ms, max={max_100:.2f}ms")
    print(f"Generated steps for 100 fields: {len(wf_100.steps)}")
    assert avg_100 < 100.0, f"100-field compilation exceeded 100ms: {avg_100:.2f}ms"
    assert max_100 < 100.0, f"100-field worst run exceeded 100ms: {max_100:.2f}ms"

    # 2. 200-field form
    # 20 rows x 10 columns
    boxes_200: List[VisualBox] = []
    for r in range(20):
        for c in range(10):
            boxes_200.append(
                make_box(
                    f"field_r{r}_c{c}",
                    x=c * 150.0 + 10.0,
                    y=r * 45.0 + 10.0,
                    w=120.0,
                    h=30.0,
                )
            )
    assert len(boxes_200) == 200
    layout_200 = make_layout(boxes_200, cw=2000.0, ch=1200.0)

    # Benchmark 200 fields over 10 iterations
    timings_200 = []
    for _ in range(10):
        t0 = time.perf_counter()
        wf_200 = compile_visual_layout_to_workflow(layout_200)
        dt = (time.perf_counter() - t0) * 1000.0  # ms
        timings_200.append(dt)
        assert len(wf_200.steps) > 200

    avg_200 = sum(timings_200) / len(timings_200)
    max_200 = max(timings_200)
    min_200 = min(timings_200)
    print(f"200-Field Form (10 runs): avg={avg_200:.2f}ms, min={min_200:.2f}ms, max={max_200:.2f}ms")
    print(f"Generated steps for 200 fields: {len(wf_200.steps)}")
    assert avg_200 < 100.0, f"200-field compilation exceeded 100ms: {avg_200:.2f}ms"
    assert max_200 < 100.0, f"200-field worst run exceeded 100ms: {max_200:.2f}ms"

    # 3. 500-field form scalability stress test
    boxes_500: List[VisualBox] = []
    for r in range(50):
        for c in range(10):
            boxes_500.append(
                make_box(
                    f"field_r{r}_c{c}",
                    x=c * 150.0 + 10.0,
                    y=r * 25.0 + 10.0,
                    w=120.0,
                    h=20.0,
                )
            )
    layout_500 = make_layout(boxes_500, cw=2000.0, ch=2000.0)
    t0 = time.perf_counter()
    wf_500 = compile_visual_layout_to_workflow(layout_500)
    dt_500 = (time.perf_counter() - t0) * 1000.0
    print(f"500-Field Form: {dt_500:.2f}ms, steps: {len(wf_500.steps)}")


# ==============================================================================
# VECTOR 4: PEEPHOLE OPTIMIZATIONS & STEP SYNTHESIS INTEGRITY
# ==============================================================================

def test_v4_peephole_and_action_synthesis():
    print("\n--- Running Vector 4: Peephole Optimizations & Action Synthesis ---")
    
    # 1. Delay collapsing: 3 consecutive DELAY boxes
    delay_boxes = [
        make_box("d1", x=10, y=10, action=DesignerActionType.DELAY, val="150"),
        make_box("d2", x=150, y=10, action=DesignerActionType.DELAY, val="250"),
        make_box("d3", x=300, y=10, action=DesignerActionType.DELAY, val="100"),
    ]
    opt_collapse = PeepholeOptimizationConfig(collapse_delays=True)
    wf_collapse = compile_visual_layout_to_workflow(make_layout(delay_boxes, opt=opt_collapse))
    # Focus window is step 1. Next step should be coalesced delay: 150 + 250 + 100 = 500ms
    delay_steps = [s for s in wf_collapse.steps if s.action_type == ActionType.DELAY]
    print(f"Collapsed delay steps count: {len(delay_steps)}, duration: {delay_steps[0].parameters.duration_ms}")
    assert len(delay_steps) == 1
    assert delay_steps[0].parameters.duration_ms == 500

    # 2. Prune empty (0ms) delay
    zero_delay_boxes = [
        make_box("t1", x=10, y=10, val="Hello"),
        make_box("d_zero", x=200, y=10, action=DesignerActionType.DELAY, val="0"),
        make_box("t2", x=400, y=10, val="World"),
    ]
    opt_prune = PeepholeOptimizationConfig(prune_empty_delays=True)
    wf_prune = compile_visual_layout_to_workflow(make_layout(zero_delay_boxes, opt=opt_prune))
    zero_delays = [s for s in wf_prune.steps if s.action_type == ActionType.DELAY]
    assert len(zero_delays) == 0, f"Expected 0ms delay to be pruned, found: {zero_delays}"

    # 3. Click-to-tab navigation optimization with force_click override
    flow_boxes = [
        make_box("f1", x=10, y=10, val="Name", nav=NavigationAction.TAB),
        make_box("f2", x=10, y=50, val="Email", nav=NavigationAction.TAB, force_click=False),
        make_box("f3", x=10, y=90, val="Phone", nav=NavigationAction.TAB, force_click=True),
    ]
    opt_tab = PeepholeOptimizationConfig(click_to_tab=True)
    wf_tab = compile_visual_layout_to_workflow(make_layout(flow_boxes, opt=opt_tab))
    click_steps = [s for s in wf_tab.steps if s.action_type == ActionType.CLICK]
    click_labels = [s.label for s in click_steps]
    print(f"Click-to-tab click steps retained: {click_labels}")
    # f1 click must be retained (first field click)
    assert any("f1" in lbl for lbl in click_labels)
    # f2 click must be pruned (follows tab, not force_click)
    assert not any("f2" in lbl for lbl in click_labels)
    # f3 click must be retained (force_click = True)
    assert any("f3" in lbl for lbl in click_labels)

    # 4. Strict sequence re-indexing: sequence indices are strictly 1..N
    for i, step in enumerate(wf_tab.steps, start=1):
        assert step.sequence_index == i, f"Step sequence index mismatch at {i}: got {step.sequence_index}"
    print("Peephole optimizations verified successfully.")


def run_all():
    print("=" * 70)
    print("STARTING KUTOMOTO COMPILER EMPIRICAL STRESS CHALLENGE")
    print("Copyrights reserved to 90Studio")
    print("=" * 70)

    try:
        test_v1_subpixel_and_1px_vertical_offsets()
        test_v1_zigzag_and_spiral_layouts()
        test_v1_sequence_index_strict_override()
        test_v2_boundary_overflow_checks()
        test_v2_one_by_one_pixels_and_extreme_dimensions()
        test_v2_negative_and_zero_inputs()
        test_v3_large_layout_scalability()
        test_v4_peephole_and_action_synthesis()
        print("\n" + "=" * 70)
        print("ALL EMPIRICAL STRESS TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        return 0
    except Exception as e:
        print(f"\nTEST FAILED WITH ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all())
