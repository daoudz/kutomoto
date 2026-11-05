"""
tests.test_m3_it2_empirical_adversarial
Empirical Adversarial Challenge & Stress Suite for kutomoto Compiler & Schema (Milestone 3 Iteration 2).
Copyrights reserved to 90Studio
"""

from pathlib import Path
import random
import sys
import time
from typing import List

import pytest
from pydantic import ValidationError

SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from kutomoto.designer.compiler import (  # noqa: E402
    _pass5_optimize_peephole,
    _spatial_band_sort,
    compile_visual_layout_to_workflow,
)
from kutomoto.designer.exceptions import (  # noqa: E402
    GeometryError,
)
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
from kutomoto.engine.schema import ActionType, StepParameters, WorkflowStep  # noqa: E402


def _box(
    name: str,
    x: float,
    y: float,
    w: float = 100.0,
    h: float = 30.0,
    seq: int = None,
    action: DesignerActionType = DesignerActionType.TYPE_TEXT,
    val: str = "text",
    nav: NavigationAction = NavigationAction.TAB,
    force_click: bool = False,
    clear_before: bool = True,
    box_id: str = None,
    pre_delay: int = 0,
    post_delay: int = 120,
) -> VisualBox:
    kw = {
        "name": name,
        "geometry": BoxGeometry(x=x, y=y, width=w, height=h),
        "action_type": action,
        "value": val,
        "navigation": nav,
        "force_click": force_click,
        "clear_before": clear_before,
        "post_delay_ms": post_delay,
    }
    if seq is not None:
        kw["sequence_index"] = seq
    if box_id is not None:
        kw["id"] = box_id
    if pre_delay > 0:
        kw["timing"] = BoxTiming(pre_delay_ms=pre_delay, post_delay_ms=post_delay)
    return VisualBox(**kw)


def _layout(
    boxes: List[VisualBox],
    cw: float = 1920.0,
    ch: float = 1080.0,
    opt: PeepholeOptimizationConfig = None,
    default_delay: int = 120,
) -> VisualFormLayout:
    return VisualFormLayout(
        name="Adversarial Layout",
        canvas=CanvasDimensions(width=cw, height=ch),
        target_application=TargetApplicationSpec(window_title_pattern=".*Target.*"),
        execution_settings=ExecutionSettingsSpec(default_step_delay_ms=default_delay),
        boxes=boxes,
        optimization=opt or PeepholeOptimizationConfig(),
    )


# ==============================================================================
# CLASS 1: Spatial Band Sorting Adversarial Stress
# ==============================================================================

class TestSpatialBandSortingAdversarial:

    def test_jittered_coordinates_dynamic_clustering(self):
        """Random vertical jitter within band tolerance clusters into distinct rows sorted left-to-right."""
        random.seed(42)
        rows = 5
        cols = 6
        band_tolerance = 24.0
        row_spacing = 80.0  # spacing >> tolerance to guarantee row separation

        boxes = []
        for r in range(rows):
            base_y = 100.0 + r * row_spacing
            row_boxes = []
            for c in range(cols):
                # Jitter within [-10.0, +10.0] px (well within 24px tolerance)
                jitter_y = random.uniform(-10.0, 10.0)
                box_x = 50.0 + c * 150.0
                box_y = base_y + jitter_y
                row_boxes.append(_box(f"r{r}_c{c}", x=box_x, y=box_y, w=100.0, h=30.0))
            # Shuffle row boxes before insertion to test order independence
            random.shuffle(row_boxes)
            boxes.extend(row_boxes)

        random.shuffle(boxes)
        sorted_boxes = _spatial_band_sort(boxes, band_tolerance_px=band_tolerance)

        # Expected: row 0 (c0..c5), row 1 (c0..c5), ..., row 4 (c0..c5)
        expected_names = [f"r{r}_c{c}" for r in range(rows) for c in range(cols)]
        actual_names = [b.name for b in sorted_boxes]
        assert actual_names == expected_names, "Jittered boxes failed reading order sorting"

    def test_band_tolerance_boundary_exact_split(self):
        """dy == 24.0 groups into same band, dy == 24.0001 splits into next band."""
        b_anchor = _box("anchor", x=100.0, y=100.0)
        b_inside = _box("inside", x=50.0, y=124.0)          # dy = 24.0 <= 24.0
        b_outside = _box("outside", x=10.0, y=124.0001)     # dy = 24.0001 > 24.0

        # Inside: same band, sorted by X -> inside (x=50) precedes anchor (x=100)
        res_inside = _spatial_band_sort([b_anchor, b_inside], band_tolerance_px=24.0)
        assert [b.name for b in res_inside] == ["inside", "anchor"]

        # Outside: different band -> anchor (y=100) precedes outside (y=124.0001)
        res_outside = _spatial_band_sort([b_anchor, b_outside], band_tolerance_px=24.0)
        assert [b.name for b in res_outside] == ["anchor", "outside"]

    def test_zigzag_reading_order_normalization(self):
        """Zigzag (snake-like) field input normalizes strictly to Western reading order."""
        zigzag_boxes = [
            # Row 1 (L -> R)
            _box("r1_1", x=50, y=50),
            _box("r1_2", x=200, y=50),
            _box("r1_3", x=350, y=50),
            # Row 2 (R -> L snake)
            _box("r2_3", x=350, y=150),
            _box("r2_2", x=200, y=150),
            _box("r2_1", x=50, y=150),
            # Row 3 (L -> R)
            _box("r3_1", x=50, y=250),
            _box("r3_2", x=200, y=250),
            _box("r3_3", x=350, y=250),
            # Row 4 (R -> L snake)
            _box("r4_3", x=350, y=350),
            _box("r4_2", x=200, y=350),
            _box("r4_1", x=50, y=350),
        ]
        sorted_boxes = _spatial_band_sort(zigzag_boxes, band_tolerance_px=24.0)
        expected = [
            "r1_1", "r1_2", "r1_3",
            "r2_1", "r2_2", "r2_3",
            "r3_1", "r3_2", "r3_3",
            "r4_1", "r4_2", "r4_3",
        ]
        assert [b.name for b in sorted_boxes] == expected

    def test_subpixel_micro_offsets(self):
        """Micro-subpixel offsets in Y (1e-5 to 1e-1) remain strictly clustered in same band."""
        micro_boxes = [
            _box("m5", x=500.0, y=100.00005),
            _box("m1", x=100.0, y=100.0),
            _box("m4", x=400.0, y=100.05),
            _box("m2", x=200.0, y=100.0001),
            _box("m3", x=300.0, y=100.001),
        ]
        sorted_boxes = _spatial_band_sort(micro_boxes, band_tolerance_px=24.0)
        assert [b.name for b in sorted_boxes] == ["m1", "m2", "m3", "m4", "m5"]

    def test_explicit_sequence_overrides_spatial_inversion(self):
        """Explicit sequence indices completely override physical geometry inversions."""
        boxes = [
            _box("bottom_right", x=800, y=800, seq=1),
            _box("bottom_left", x=100, y=800, seq=2),
            _box("top_right", x=800, y=100, seq=3),
            _box("top_left", x=100, y=100, seq=4),
        ]
        wf = compile_visual_layout_to_workflow(_layout(boxes))
        click_labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "bottom_right" in click_labels[0]
        assert "bottom_left" in click_labels[1]
        assert "top_right" in click_labels[2]
        assert "top_left" in click_labels[3]

    def test_hybrid_explicit_and_spatial_strict_tail(self):
        """Explicit sequence boxes strictly precede all unindexed boxes which sort at tail."""
        boxes = [
            _box("unindexed_row1_c1", x=50, y=50, seq=None),
            _box("unindexed_row1_c2", x=200, y=50, seq=None),
            _box("explicit_3", x=500, y=500, seq=3),
            _box("explicit_1", x=700, y=700, seq=1),
            _box("unindexed_row2_c1", x=50, y=150, seq=None),
            _box("explicit_2", x=600, y=600, seq=2),
        ]
        wf = compile_visual_layout_to_workflow(_layout(boxes))
        clicks = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        expected_clicks_order = [
            "explicit_1",
            "explicit_2",
            "explicit_3",
            "unindexed_row1_c1",
            "unindexed_row1_c2",
            "unindexed_row2_c1",
        ]
        assert len(clicks) == len(expected_clicks_order)
        for actual_lbl, exp_name in zip(clicks, expected_clicks_order):
            assert exp_name in actual_lbl

    def test_sequence_index_pydantic_ge_1_rejection(self):
        """sequence_index <= 0 or non-integers are rejected with Pydantic ValidationError."""
        invalid_values = [0, -1, -50, -999, 0.0, -0.5, 0.999]
        for val in invalid_values:
            with pytest.raises(ValidationError):
                VisualBox(
                    name="invalid_seq",
                    geometry=BoxGeometry(x=10, y=10, width=50, height=20),
                    sequence_index=val,
                )

    def test_sequence_index_valid_integers_accepted(self):
        """Positive integers >= 1 are accepted for sequence_index."""
        valid_values = [1, 2, 5, 100, 99999]
        for val in valid_values:
            b = VisualBox(
                name="valid_seq",
                geometry=BoxGeometry(x=10, y=10, width=50, height=20),
                sequence_index=val,
            )
            assert b.sequence_index == val

    def test_sequence_index_tie_breaking(self):
        """Duplicate sequence_index values break ties deterministically by Y then X."""
        boxes = [
            _box("b_y200_x100", x=100, y=200, seq=1),
            _box("b_y100_x200", x=200, y=100, seq=1),
            _box("b_y100_x100", x=100, y=100, seq=1),
        ]
        wf = compile_visual_layout_to_workflow(_layout(boxes))
        clicks = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "b_y100_x100" in clicks[0]
        assert "b_y100_x200" in clicks[1]
        assert "b_y200_x100" in clicks[2]


# ==============================================================================
# CLASS 2: Boundary and Extreme Geometries Stress
# ==============================================================================

class TestExtremeGeometriesAdversarial:

    def test_1x1_canvas_exact_centering(self):
        """1x1 pixel box on 1x1 canvas centers at (0.5, 0.5) in normalized space."""
        layout = _layout([_box("b1x1", x=0, y=0, w=1, h=1)], cw=1.0, ch=1.0)
        wf = compile_visual_layout_to_workflow(layout)
        click = next(s for s in wf.steps if s.action_type == ActionType.CLICK)
        assert click.parameters.norm_x == 0.5
        assert click.parameters.norm_y == 0.5

    def test_1x1_canvas_subpixel_quadrants(self):
        """4 subpixel boxes partitioning a 1x1 canvas normalize accurately."""
        quadrants = [
            _box("tl", x=0.0, y=0.0, w=0.5, h=0.5),
            _box("tr", x=0.5, y=0.0, w=0.5, h=0.5),
            _box("bl", x=0.0, y=0.5, w=0.5, h=0.5),
            _box("br", x=0.5, y=0.5, w=0.5, h=0.5),
        ]
        layout = _layout(quadrants, cw=1.0, ch=1.0)
        wf = compile_visual_layout_to_workflow(layout)
        clicks = {s.label: (s.parameters.norm_x, s.parameters.norm_y) for s in wf.steps if s.action_type == ActionType.CLICK}
        assert clicks["Click [tl]"] == (0.25, 0.25)
        assert clicks["Click [tr]"] == (0.75, 0.25)
        assert clicks["Click [bl]"] == (0.25, 0.75)
        assert clicks["Click [br]"] == (0.75, 0.75)

    def test_4k_canvas_tiny_corner_and_center(self):
        """Tiny 1x1 boxes on 4K canvas (3840x2160) normalize correctly at corners and center."""
        boxes = [
            _box("tl", x=0, y=0, w=1, h=1),
            _box("br", x=3839, y=2159, w=1, h=1),
            _box("center", x=1919.5, y=1079.5, w=1, h=1),
        ]
        layout = _layout(boxes, cw=3840.0, ch=2160.0)
        wf = compile_visual_layout_to_workflow(layout)
        clicks = {s.label: (s.parameters.norm_x, s.parameters.norm_y) for s in wf.steps if s.action_type == ActionType.CLICK}

        # TL: (0.5 / 3840, 0.5 / 2160) -> (0.0001, 0.0002)
        assert clicks["Click [tl]"] == (0.0001, 0.0002)
        # BR: (3839.5 / 3840, 2159.5 / 2160) -> (0.9999, 0.9998)
        assert clicks["Click [br]"] == (0.9999, 0.9998)
        # Center: (1920.0 / 3840, 1080.0 / 2160) -> (0.5, 0.5)
        assert clicks["Click [center]"] == (0.5, 0.5)

    def test_extreme_aspect_ratios(self):
        """Ultra-wide (10000x200) and ultra-tall (200x10000) canvases compile and normalize accurately."""
        # Ultra-wide
        wide_boxes = [_box("w1", x=100, y=50, w=200, h=50), _box("w2", x=9000, y=50, w=200, h=50)]
        wf_wide = compile_visual_layout_to_workflow(_layout(wide_boxes, cw=10000.0, ch=200.0))
        wide_clicks = [s for s in wf_wide.steps if s.action_type == ActionType.CLICK]
        assert wide_clicks[0].parameters.norm_x == 0.02
        assert wide_clicks[1].parameters.norm_x == 0.91

        # Ultra-tall
        tall_boxes = [_box("t1", x=50, y=100, w=50, h=200), _box("t2", x=50, y=9000, w=50, h=200)]
        wf_tall = compile_visual_layout_to_workflow(_layout(tall_boxes, cw=200.0, ch=10000.0))
        tall_clicks = [s for s in wf_tall.steps if s.action_type == ActionType.CLICK]
        assert tall_clicks[0].parameters.norm_y == 0.02
        assert tall_clicks[1].parameters.norm_y == 0.91

    def test_subpixel_dimensions_precision(self):
        """Micro dimensions (0.05px) normalize without float precision underflow."""
        b = _box("micro", x=10.0, y=10.0, w=0.05, h=0.05)
        wf = compile_visual_layout_to_workflow(_layout([b], cw=1000.0, ch=1000.0))
        click = next(s for s in wf.steps if s.action_type == ActionType.CLICK)
        assert click.parameters.norm_x == 0.01
        assert click.parameters.norm_y == 0.01

    def test_boundary_overflow_rejections(self):
        """Boundary overflows (x+w > cw, y+h > ch, negative, zero) strictly rejected in both schema and dict."""
        # Schema rejections
        with pytest.raises((ValueError, ValidationError)):
            _layout([_box("ov_x", x=950, y=100, w=60, h=20)], cw=1000, ch=1000)

        with pytest.raises((ValueError, ValidationError)):
            _layout([_box("ov_y", x=100, y=950, w=50, h=60)], cw=1000, ch=1000)

        with pytest.raises(ValidationError):
            BoxGeometry(x=-1.0, y=10.0, width=50.0, height=20.0)

        with pytest.raises(ValidationError):
            BoxGeometry(x=10.0, y=-0.5, width=50.0, height=20.0)

        with pytest.raises(ValidationError):
            BoxGeometry(x=10.0, y=10.0, width=0.0, height=20.0)

        with pytest.raises(ValidationError):
            BoxGeometry(x=10.0, y=10.0, width=50.0, height=0.0)

        # Dict compilation rejections (Pass 1)
        with pytest.raises(GeometryError):
            compile_visual_layout_to_workflow({
                "canvas": {"width": 1000, "height": 1000},
                "boxes": [{"name": "b", "geometry": {"x": 950, "y": 100, "width": 60, "height": 20}}],
            })

        with pytest.raises(GeometryError):
            compile_visual_layout_to_workflow({
                "canvas": {"width": 1000, "height": 1000},
                "boxes": [{"name": "b", "geometry": {"x": 100, "y": 950, "width": 50, "height": 60}}],
            })

    def test_boundary_float_tolerance_boundary(self):
        """cw + 1e-5 accepted within tolerance, cw + 1e-3 rejected."""
        # cw + 1e-5 <= cw + 1e-4 -> accepted
        b_ok = _box("ok_edge", x=900.0, y=100.0, w=100.00001, h=20.0)
        wf_ok = compile_visual_layout_to_workflow(_layout([b_ok], cw=1000.0, ch=1000.0))
        assert len(wf_ok.steps) >= 1

        # cw + 1e-3 > cw + 1e-4 -> rejected
        with pytest.raises((ValueError, ValidationError)):
            _layout([_box("err_edge", x=900.0, y=100.0, w=100.001, h=20.0)], cw=1000.0, ch=1000.0)


# ==============================================================================
# CLASS 3: Large Layout Compilation Performance Benchmarks (< 100ms)
# ==============================================================================

class TestLargeLayoutCompilationBenchmarks:

    def test_100_field_benchmark_under_100ms(self):
        """100-field layout compiles and validates in < 100ms across multiple iterations."""
        boxes = [
            _box(f"f_{r}_{c}", x=c * 120.0 + 10.0, y=r * 40.0 + 10.0, w=100.0, h=30.0)
            for r in range(10)
            for c in range(10)
        ]
        layout = _layout(boxes, cw=1500.0, ch=800.0)

        # Warmup
        _ = compile_visual_layout_to_workflow(layout)

        timings = []
        for _ in range(10):
            t0 = time.perf_counter()
            wf = compile_visual_layout_to_workflow(layout)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            timings.append(dt_ms)
            assert len(wf.steps) == 401

        avg_ms = sum(timings) / len(timings)
        max_ms = max(timings)
        assert avg_ms < 100.0, f"100-field avg {avg_ms:.2f}ms exceeds 100ms target"
        assert max_ms < 100.0, f"100-field max {max_ms:.2f}ms exceeds 100ms target"

    def test_200_field_benchmark_under_100ms(self):
        """200-field layout compiles and validates in < 100ms across multiple iterations."""
        boxes = [
            _box(f"f_{r}_{c}", x=c * 120.0 + 10.0, y=r * 35.0 + 10.0, w=100.0, h=25.0)
            for r in range(20)
            for c in range(10)
        ]
        layout = _layout(boxes, cw=1500.0, ch=1000.0)

        # Warmup
        _ = compile_visual_layout_to_workflow(layout)

        timings = []
        for _ in range(10):
            t0 = time.perf_counter()
            wf = compile_visual_layout_to_workflow(layout)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            timings.append(dt_ms)
            assert len(wf.steps) == 801

        avg_ms = sum(timings) / len(timings)
        max_ms = max(timings)
        assert avg_ms < 100.0, f"200-field avg {avg_ms:.2f}ms exceeds 100ms target"
        assert max_ms < 100.0, f"200-field max {max_ms:.2f}ms exceeds 100ms target"

    def test_500_field_benchmark_under_100ms(self):
        """500-field layout compiles and validates in < 100ms across multiple iterations."""
        boxes = [
            _box(f"f_{r}_{c}", x=c * 120.0 + 10.0, y=r * 25.0 + 10.0, w=100.0, h=20.0)
            for r in range(50)
            for c in range(10)
        ]
        layout = _layout(boxes, cw=1500.0, ch=1500.0)

        # Warmup
        _ = compile_visual_layout_to_workflow(layout)

        timings = []
        for _ in range(10):
            t0 = time.perf_counter()
            wf = compile_visual_layout_to_workflow(layout)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            timings.append(dt_ms)
            assert len(wf.steps) == 2001

        avg_ms = sum(timings) / len(timings)
        max_ms = max(timings)
        assert avg_ms < 100.0, f"500-field avg {avg_ms:.2f}ms exceeds 100ms target"
        assert max_ms < 100.0, f"500-field max {max_ms:.2f}ms exceeds 100ms target"

    def test_step_count_and_sequence_integrity(self):
        """Generated workflows strictly satisfy 4N+1 step count and contiguous sequence_index 1..N."""
        for n in [10, 50, 100]:
            boxes = [
                _box(f"f_{i}", x=(i % 5) * 100 + 10, y=(i // 5) * 40 + 10, w=80, h=30)
                for i in range(n)
            ]
            wf = compile_visual_layout_to_workflow(_layout(boxes, cw=1000, ch=2000))
            assert len(wf.steps) == 4 * n + 1
            indices = [s.sequence_index for s in wf.steps]
            assert indices == list(range(1, 4 * n + 2))


# ==============================================================================
# CLASS 4: Peephole Optimizations Adversarial Stress
# ==============================================================================

class TestPeepholeOptimizationsAdversarial:

    def test_delay_coalescing_multi_block(self):
        """Consecutive delays coalesce into single step; non-consecutive blocks remain separate."""
        boxes = [
            _box("f1", x=10, y=10),
            _box("d1", x=120, y=10, action=DesignerActionType.DELAY, val="100"),
            _box("d2", x=230, y=10, action=DesignerActionType.DELAY, val="200"),
            _box("f2", x=10, y=60),
            _box("d3", x=120, y=60, action=DesignerActionType.DELAY, val="50"),
            _box("d4", x=230, y=60, action=DesignerActionType.DELAY, val="75"),
            _box("d5", x=340, y=60, action=DesignerActionType.DELAY, val="125"),
        ]
        opt = PeepholeOptimizationConfig(collapse_delays=True)
        wf = compile_visual_layout_to_workflow(_layout(boxes, opt=opt))
        delays = [s for s in wf.steps if s.action_type == ActionType.DELAY]
        assert len(delays) == 2
        assert delays[0].parameters.duration_ms == 300  # 100 + 200
        assert delays[1].parameters.duration_ms == 250  # 50 + 75 + 125

    def test_empty_delay_pruning(self):
        """0ms delays are pruned when prune_empty_delays=True, kept when False."""
        boxes = [
            _box("f1", x=10, y=10),
            _box("d0", x=120, y=10, action=DesignerActionType.DELAY, val="0"),
            _box("f2", x=10, y=60),
        ]
        # Pruned
        opt_prune = PeepholeOptimizationConfig(prune_empty_delays=True, collapse_delays=False)
        wf_prune = compile_visual_layout_to_workflow(_layout(boxes, opt=opt_prune))
        delays_pruned = [s for s in wf_prune.steps if s.action_type == ActionType.DELAY]
        assert len(delays_pruned) == 0

        # Kept
        opt_keep = PeepholeOptimizationConfig(prune_empty_delays=False, collapse_delays=False)
        wf_keep = compile_visual_layout_to_workflow(_layout(boxes, opt=opt_keep))
        delays_kept = [s for s in wf_keep.steps if s.action_type == ActionType.DELAY]
        assert len(delays_kept) == 1
        assert delays_kept[0].parameters.duration_ms == 0

    def test_settling_delay_transfer_to_clear_field(self):
        """Pruned focus click under click_to_tab transfers pre_delay_ms to CLEAR_FIELD step."""
        b1 = _box("b1", x=10, y=10, nav=NavigationAction.TAB)
        b2 = _box("b2", x=10, y=50, nav=NavigationAction.TAB, clear_before=True, pre_delay=400)
        opt = PeepholeOptimizationConfig(click_to_tab=True)
        wf = compile_visual_layout_to_workflow(_layout([b1, b2], opt=opt))

        b2_steps = [s for s in wf.steps if "b2" in (s.label or "")]
        # b2 click is pruned; first step is Clear [b2]
        assert b2_steps[0].action_type == ActionType.CLEAR_FIELD
        assert b2_steps[0].pre_delay_ms == 400
        # Subsequent steps have 0 pre_delay
        assert b2_steps[1].action_type == ActionType.TYPE_TEXT
        assert b2_steps[1].pre_delay_ms == 0

    def test_settling_delay_transfer_to_type_text_when_no_clear(self):
        """When clear_before=False, pruned focus click transfers pre_delay_ms to TYPE_TEXT step."""
        b1 = _box("b1", x=10, y=10, nav=NavigationAction.TAB)
        b2 = _box("b2", x=10, y=50, nav=NavigationAction.TAB, clear_before=False, pre_delay=350)
        opt = PeepholeOptimizationConfig(click_to_tab=True)
        wf = compile_visual_layout_to_workflow(_layout([b1, b2], opt=opt))

        b2_steps = [s for s in wf.steps if "b2" in (s.label or "")]
        assert b2_steps[0].action_type == ActionType.TYPE_TEXT
        assert b2_steps[0].pre_delay_ms == 350

    def test_settling_delay_transfer_defensive_last_step(self):
        """If a pruned focus click has no subsequent step, a standalone DELAY step is synthesized."""
        # Test directly against Pass 5 helper
        raw_steps = [
            WorkflowStep(
                step_id="step1",
                sequence_index=1,
                label="Click [first_box]",
                action_type=ActionType.CLICK,
                parameters=StepParameters(norm_x=0.1, norm_y=0.1),
            ),
            WorkflowStep(
                step_id="step2",
                sequence_index=2,
                label="Tab navigation",
                action_type=ActionType.KEY_PRESS,
                parameters=StepParameters(key="tab"),
            ),
            WorkflowStep(
                step_id="step3",
                sequence_index=3,
                label="Click [tail_box]",
                action_type=ActionType.CLICK,
                pre_delay_ms=250,
                parameters=StepParameters(norm_x=0.5, norm_y=0.5),
            ),
        ]
        setattr(raw_steps[2], "_is_focus_anchor", True)

        opt = PeepholeOptimizationConfig(click_to_tab=True)
        optimized = _pass5_optimize_peephole(raw_steps, opt)

        # The second click step should be replaced by standalone DELAY step
        delay_steps = [s for s in optimized if s.action_type == ActionType.DELAY]
        assert len(delay_steps) == 1
        assert delay_steps[0].parameters.duration_ms == 250
        assert "Settling Delay (250ms)" in delay_steps[0].label

    def test_settling_delay_multi_field_chain_no_leakage(self):
        """Across a 3-field chain, each pruned click transfers only its own pre_delay without leak."""
        b1 = _box("f1", x=10, y=10, nav=NavigationAction.TAB, pre_delay=0)
        b2 = _box("f2", x=10, y=50, nav=NavigationAction.TAB, pre_delay=180)
        b3 = _box("f3", x=10, y=90, nav=NavigationAction.TAB, pre_delay=320)
        opt = PeepholeOptimizationConfig(click_to_tab=True)
        wf = compile_visual_layout_to_workflow(_layout([b1, b2, b3], opt=opt))

        f2_clear = next(s for s in wf.steps if s.label == "Clear [f2]")
        f3_clear = next(s for s in wf.steps if s.label == "Clear [f3]")
        assert f2_clear.pre_delay_ms == 180
        assert f3_clear.pre_delay_ms == 320

    def test_force_click_preservation_on_text_and_action_boxes(self):
        """Explicit force_click=True protects clicks from pruning under click_to_tab."""
        b1 = _box("f1", x=10, y=10, nav=NavigationAction.TAB)
        b2_force = _box("f2", x=10, y=50, nav=NavigationAction.TAB, force_click=True)
        b3_normal = _box("f3", x=10, y=90, nav=NavigationAction.TAB, force_click=False)
        opt = PeepholeOptimizationConfig(click_to_tab=True)
        wf = compile_visual_layout_to_workflow(_layout([b1, b2_force, b3_normal], opt=opt))

        click_labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert any("f1" in lbl for lbl in click_labels)
        assert any("f2" in lbl for lbl in click_labels)
        assert not any("f3" in lbl for lbl in click_labels)

    def test_standalone_action_clicks_preserved_without_force_click(self):
        """CLICK, CHECKBOX, and SELECT action boxes are never pruned by click_to_tab, even without force_click."""
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
        # Submit step
        submits = [s.label for s in wf.steps if s.action_type == ActionType.SUBMIT]
        assert len(submits) == 1

    def test_duplicate_focus_window_pruning(self):
        """Consecutive duplicate focus_window steps are pruned; differing targets are preserved."""
        raw_steps = [
            WorkflowStep(
                step_id="f1", sequence_index=1, label="Focus A", action_type=ActionType.FOCUS_WINDOW,
                parameters=StepParameters(window_title_pattern="AppA", process_name="app.exe"),
            ),
            WorkflowStep(
                step_id="f2", sequence_index=2, label="Duplicate Focus A", action_type=ActionType.FOCUS_WINDOW,
                parameters=StepParameters(window_title_pattern="AppA", process_name="app.exe"),
            ),
            WorkflowStep(
                step_id="c1", sequence_index=3, label="Click Field", action_type=ActionType.CLICK,
                parameters=StepParameters(norm_x=0.1, norm_y=0.1),
            ),
            WorkflowStep(
                step_id="f3", sequence_index=4, label="Non-consecutive Focus A", action_type=ActionType.FOCUS_WINDOW,
                parameters=StepParameters(window_title_pattern="AppA", process_name="app.exe"),
            ),
            WorkflowStep(
                step_id="f4", sequence_index=5, label="Focus B", action_type=ActionType.FOCUS_WINDOW,
                parameters=StepParameters(window_title_pattern="AppB", process_name="app.exe"),
            ),
        ]
        opt = PeepholeOptimizationConfig(remove_redundant_focus=True)
        optimized = _pass5_optimize_peephole(raw_steps, opt)

        focus_steps = [s for s in optimized if s.action_type == ActionType.FOCUS_WINDOW]
        # f2 should be pruned; f1, f3, and f4 should remain (3 total)
        assert len(focus_steps) == 3
        assert [s.label for s in focus_steps] == ["Focus A", "Non-consecutive Focus A", "Focus B"]

    def test_peephole_master_switch_disabled(self):
        """When optimization.enabled=False, no steps are pruned or collapsed, indices remain contiguous 1..N."""
        raw_steps = [
            WorkflowStep(
                step_id="f1", sequence_index=10, label="Focus A", action_type=ActionType.FOCUS_WINDOW,
                parameters=StepParameters(window_title_pattern="AppA"),
            ),
            WorkflowStep(
                step_id="f2", sequence_index=20, label="Duplicate Focus A", action_type=ActionType.FOCUS_WINDOW,
                parameters=StepParameters(window_title_pattern="AppA"),
            ),
            WorkflowStep(
                step_id="d1", sequence_index=30, label="Delay 0", action_type=ActionType.DELAY,
                parameters=StepParameters(duration_ms=0),
            ),
            WorkflowStep(
                step_id="d2", sequence_index=40, label="Delay 100", action_type=ActionType.DELAY,
                parameters=StepParameters(duration_ms=100),
            ),
        ]
        opt = PeepholeOptimizationConfig(enabled=False)
        optimized = _pass5_optimize_peephole(raw_steps, opt)

        assert len(optimized) == 4
        assert [s.sequence_index for s in optimized] == [1, 2, 3, 4]
