"""
tests.test_compiler_empirical_challenge
Empirical stress-testing and adversarial challenge suite for kutomoto Compiler & Schema:
1. Spatial Band Sorting Stress: sub-pixel/1px offsets, zigzag, spiral, explicit sequence override, tie-breakers.
2. Extreme Geometries: boundary overflow, 1x1 pixels, 4K tiny box, sub-pixel dimensions, negative/zero guards.
3. Large Layout Scalability: 100-field and 200-field benchmarks (<100ms threshold enforcement).
4. Peephole Optimizations: delay coalescing, empty delay pruning, click_to_tab with force_click, contiguous re-indexing.
5. Edge cases: pre_delay loss under click_to_tab, sequence_index=0 handling, band_tolerance_px=0.0 override.

Copyrights reserved to 90Studio
"""

from pathlib import Path
import sys
import time
from typing import List

import pytest
from pydantic import ValidationError

SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from kutomoto.designer.compiler import (  # noqa: E402
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
    NavigationAction,
    PeepholeOptimizationConfig,
    TargetApplicationSpec,
    VisualBox,
    VisualFormLayout,
)
from kutomoto.engine.schema import ActionType  # noqa: E402


def _make_box(
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


def _make_layout(
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
# CLASS 1: Spatial Band Sorting Stress
# ==============================================================================

class TestSpatialBandSortingStress:

    def test_subpixel_vertical_offsets_within_band(self):
        """Subpixel vertical offsets (0.0001px to 0.999px) remain strictly clustered in same band."""
        boxes = [
            _make_box("b4", x=400.0, y=100.999),
            _make_box("b1", x=100.0, y=100.0),
            _make_box("b3", x=300.0, y=100.5),
            _make_box("b2", x=200.0, y=100.0001),
        ]
        sorted_boxes = _spatial_band_sort(boxes, band_tolerance_px=24.0)
        names = [b.name for b in sorted_boxes]
        assert names == ["b1", "b2", "b3", "b4"]

    def test_single_pixel_vertical_offsets(self):
        """1px stepped vertical offsets within tolerance sort strictly left-to-right."""
        boxes_1px = [
            _make_box("b4", x=400.0, y=103.0),
            _make_box("b2", x=200.0, y=101.0),
            _make_box("b1", x=100.0, y=100.0),
            _make_box("b3", x=300.0, y=102.0),
        ]
        sorted_1px = _spatial_band_sort(boxes_1px, band_tolerance_px=24.0)
        assert [b.name for b in sorted_1px] == ["b1", "b2", "b3", "b4"]

    def test_exact_band_tolerance_boundary_edge(self):
        """dy == 24.0 groups into band, whereas dy == 24.001 splits into new band."""
        b_anchor = _make_box("anchor", x=100.0, y=100.0)
        b_inside = _make_box("inside", x=50.0, y=124.0)      # dy = 24.0 <= 24.0
        b_outside = _make_box("outside", x=10.0, y=124.001)  # dy = 24.001 > 24.0

        sorted_inside = _spatial_band_sort([b_anchor, b_inside], band_tolerance_px=24.0)
        assert [b.name for b in sorted_inside] == ["inside", "anchor"]

        sorted_outside = _spatial_band_sort([b_anchor, b_outside], band_tolerance_px=24.0)
        assert [b.name for b in sorted_outside] == ["anchor", "outside"]

    def test_zigzag_unindexed_normalizes_to_reading_order(self):
        """Zigzag physical layout without sequence_index normalizes to row-by-row reading order."""
        boxes = [
            _make_box("r1_c1", x=10, y=50),
            _make_box("r1_c2", x=100, y=50),
            _make_box("r1_c3", x=200, y=50),
            _make_box("r2_c3", x=200, y=150),
            _make_box("r2_c2", x=100, y=150),
            _make_box("r2_c1", x=10, y=150),
            _make_box("r3_c1", x=10, y=250),
            _make_box("r3_c2", x=100, y=250),
            _make_box("r3_c3", x=200, y=250),
        ]
        sorted_boxes = _spatial_band_sort(boxes)
        names = [b.name for b in sorted_boxes]
        expected = [
            "r1_c1", "r1_c2", "r1_c3",
            "r2_c1", "r2_c2", "r2_c3",
            "r3_c1", "r3_c2", "r3_c3",
        ]
        assert names == expected

    def test_spiral_explicit_sequence_strictly_overrides(self):
        """Explicit sequence_index strictly preserves spiral order even when inverted to geometry."""
        spiral_boxes = [
            _make_box("center", x=200, y=200, seq=5),
            _make_box("top_right", x=400, y=50, seq=2),
            _make_box("bottom_right", x=400, y=400, seq=3),
            _make_box("top_left", x=50, y=50, seq=1),
            _make_box("bottom_left", x=50, y=400, seq=4),
        ]
        wf = compile_visual_layout_to_workflow(_make_layout(spiral_boxes))
        step_labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "top_left" in step_labels[0]
        assert "top_right" in step_labels[1]
        assert "bottom_right" in step_labels[2]
        assert "bottom_left" in step_labels[3]
        assert "center" in step_labels[4]

    def test_reverse_spatial_explicit_sequence(self):
        """Complete inversion of spatial layout via explicit sequence_index."""
        boxes = [
            _make_box("b_tl", x=0, y=0, seq=4),
            _make_box("b_tr", x=500, y=0, seq=3),
            _make_box("b_bl", x=0, y=500, seq=2),
            _make_box("b_br", x=500, y=500, seq=1),
        ]
        wf = compile_visual_layout_to_workflow(_make_layout(boxes))
        labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "b_br" in labels[0]
        assert "b_bl" in labels[1]
        assert "b_tr" in labels[2]
        assert "b_tl" in labels[3]

    def test_duplicate_sequence_index_tie_breaker(self):
        """Duplicate sequence_index breaks ties deterministically via vertical Y then horizontal X."""
        boxes = [
            _make_box("dup_y200", x=100, y=200, seq=1),
            _make_box("dup_y100", x=100, y=100, seq=1),
        ]
        wf = compile_visual_layout_to_workflow(_make_layout(boxes))
        labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "dup_y100" in labels[0]
        assert "dup_y200" in labels[1]

    def test_hybrid_explicit_and_unindexed_ordering(self):
        """Explicitly indexed boxes strictly precede unindexed boxes."""
        with pytest.raises(ValidationError):
            _make_box("zero_seq", x=10, y=10, seq=0)

        boxes = [
            _make_box("unindexed_top", x=0, y=0, seq=None),
            _make_box("explicit_bottom", x=500, y=500, seq=1),
            _make_box("unindexed_mid", x=10, y=10, seq=None),
        ]
        wf = compile_visual_layout_to_workflow(_make_layout(boxes))
        labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "explicit_bottom" in labels[0]
        assert "unindexed_top" in labels[1]
        assert "unindexed_mid" in labels[2]

    def test_band_tolerance_zero_forces_auto_tolerance(self):
        """Observation: band_tolerance_px=0.0 triggers dynamic auto-tolerance of at least 10px."""
        b1 = _make_box("b1", x=100, y=10, w=50, h=20)
        b2 = _make_box("b2", x=10, y=15, w=50, h=20)
        # Even with band_tolerance_px=0.0, dy=5 is clustered into same band because auto-tolerance >= 10px
        wf = compile_visual_layout_to_workflow(
            _make_layout([b1, b2], opt=PeepholeOptimizationConfig(band_tolerance_px=0.0))
        )
        labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "b2" in labels[0]  # b2 (x=10) precedes b1 (x=100) due to auto-tolerance grouping


# ==============================================================================
# CLASS 2: Extreme Geometries and Boundary Conditions
# ==============================================================================

class TestExtremeGeometriesStress:

    def test_box_right_overflow_rejected(self):
        """Box with right edge > canvas width is rejected by schema and compiler."""
        with pytest.raises((ValueError, ValidationError)):
            _make_layout([_make_box("overflow_x", x=900, y=100, w=101, h=30)], cw=1000, ch=1000)

        with pytest.raises(GeometryError):
            compile_visual_layout_to_workflow({
                "name": "Dict Overflow X",
                "canvas": {"width": 1000, "height": 1000},
                "target": {"window_title_pattern": ".*"},
                "boxes": [{"name": "b1", "geometry": {"x": 950, "y": 100, "width": 60, "height": 30}}],
            })

    def test_box_bottom_overflow_rejected(self):
        """Box with bottom edge > canvas height is rejected by schema and compiler."""
        with pytest.raises((ValueError, ValidationError)):
            _make_layout([_make_box("overflow_y", x=100, y=900, w=100, h=101)], cw=1000, ch=1000)

        with pytest.raises(GeometryError):
            compile_visual_layout_to_workflow({
                "name": "Dict Overflow Y",
                "canvas": {"width": 1000, "height": 1000},
                "target": {"window_title_pattern": ".*"},
                "boxes": [{"name": "b1", "geometry": {"x": 100, "y": 950, "width": 60, "height": 60}}],
            })

    def test_1x1_pixel_box_on_1x1_canvas(self):
        """1x1 box on 1x1 canvas centers precisely at (0.5, 0.5) in normalized space."""
        layout = _make_layout([_make_box("pixel_box", x=0, y=0, w=1, h=1)], cw=1.0, ch=1.0)
        wf = compile_visual_layout_to_workflow(layout)
        click_step = next(s for s in wf.steps if s.action_type == ActionType.CLICK)
        assert click_step.parameters.norm_x == 0.5
        assert click_step.parameters.norm_y == 0.5

    def test_tiny_box_on_4k_canvas(self):
        """1x1 box at the extreme bottom-right pixel of 4K canvas (3840x2160) produces valid coordinates."""
        layout = _make_layout([_make_box("tiny_4k", x=3839, y=2159, w=1, h=1)], cw=3840, ch=2160)
        wf = compile_visual_layout_to_workflow(layout)
        click_step = next(s for s in wf.steps if s.action_type == ActionType.CLICK)
        assert 0.999 <= click_step.parameters.norm_x <= 1.0
        assert 0.999 <= click_step.parameters.norm_y <= 1.0

    def test_subpixel_dimensions_normalized_correctly(self):
        """Sub-pixel dimensions (0.5px x 0.5px) normalize correctly without underflow."""
        layout = _make_layout([_make_box("subpixel", x=0.25, y=0.25, w=0.5, h=0.5)], cw=100, ch=100)
        wf = compile_visual_layout_to_workflow(layout)
        click_step = next(s for s in wf.steps if s.action_type == ActionType.CLICK)
        assert click_step.parameters.norm_x == 0.005
        assert click_step.parameters.norm_y == 0.005

    def test_negative_coordinates_strictly_guarded(self):
        """Negative coordinates in schema or dict input raise immediate validation error."""
        with pytest.raises(ValidationError):
            BoxGeometry(x=-1.0, y=0.0, width=10.0, height=10.0)

        with pytest.raises(ValidationError):
            BoxGeometry(x=0.0, y=-0.001, width=10.0, height=10.0)

        with pytest.raises(GeometryError):
            compile_visual_layout_to_workflow({
                "canvas": {"width": 1000, "height": 1000},
                "boxes": [{"name": "neg", "geometry": {"x": -5, "y": 10, "width": 10, "height": 10}}],
            })

    def test_zero_dimensions_strictly_guarded(self):
        """Zero width or height in schema or dict input raise immediate validation error."""
        with pytest.raises(ValidationError):
            BoxGeometry(x=0.0, y=0.0, width=0.0, height=10.0)

        with pytest.raises(ValidationError):
            BoxGeometry(x=0.0, y=0.0, width=10.0, height=0.0)

        with pytest.raises(GeometryError):
            compile_visual_layout_to_workflow({
                "canvas": {"width": 1000, "height": 1000},
                "boxes": [{"name": "zero_w", "geometry": {"x": 5, "y": 10, "width": 0, "height": 10}}],
            })


# ==============================================================================
# CLASS 3: Large Layout Scalability Benchmarks
# ==============================================================================

class TestLargeLayoutScalability:

    def test_100_field_form_compilation_under_100ms(self):
        """100-field grid compiles and validates in < 100ms (asserted across multiple runs)."""
        boxes = [
            _make_box(f"f_{r}_{c}", x=c * 150.0 + 10.0, y=r * 60.0 + 10.0, w=120.0, h=40.0)
            for r in range(10)
            for c in range(10)
        ]
        layout = _make_layout(boxes, cw=2000.0, ch=1000.0)

        # Warmup
        _ = compile_visual_layout_to_workflow(layout)

        timings = []
        for _ in range(5):
            t0 = time.perf_counter()
            wf = compile_visual_layout_to_workflow(layout)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            timings.append(dt_ms)
            assert len(wf.steps) == 401  # 1 focus + 100 * 4

        avg_ms = sum(timings) / len(timings)
        max_ms = max(timings)
        assert avg_ms < 100.0, f"100-field avg {avg_ms:.2f}ms exceeds 100ms"
        assert max_ms < 100.0, f"100-field max {max_ms:.2f}ms exceeds 100ms"

    def test_200_field_form_compilation_under_100ms(self):
        """200-field grid compiles and validates in < 100ms (asserted across multiple runs)."""
        boxes = [
            _make_box(f"f_{r}_{c}", x=c * 150.0 + 10.0, y=r * 45.0 + 10.0, w=120.0, h=30.0)
            for r in range(20)
            for c in range(10)
        ]
        layout = _make_layout(boxes, cw=2000.0, ch=1200.0)

        # Warmup
        _ = compile_visual_layout_to_workflow(layout)

        timings = []
        for _ in range(5):
            t0 = time.perf_counter()
            wf = compile_visual_layout_to_workflow(layout)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            timings.append(dt_ms)
            assert len(wf.steps) == 801  # 1 focus + 200 * 4

        avg_ms = sum(timings) / len(timings)
        max_ms = max(timings)
        assert avg_ms < 100.0, f"200-field avg {avg_ms:.2f}ms exceeds 100ms"
        assert max_ms < 100.0, f"200-field max {max_ms:.2f}ms exceeds 100ms"

    def test_500_field_form_stress(self):
        """500-field grid compiles within reasonable time bounds (< 500ms)."""
        boxes = [
            _make_box(f"f_{r}_{c}", x=c * 150.0 + 10.0, y=r * 25.0 + 10.0, w=120.0, h=20.0)
            for r in range(50)
            for c in range(10)
        ]
        layout = _make_layout(boxes, cw=2000.0, ch=2000.0)
        t0 = time.perf_counter()
        wf = compile_visual_layout_to_workflow(layout)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        assert len(wf.steps) == 2001
        assert dt_ms < 500.0, f"500-field compilation took {dt_ms:.2f}ms"


# ==============================================================================
# CLASS 4: Peephole Optimizations & Step Synthesis Stress
# ==============================================================================

class TestPeepholeOptimizationStress:

    def test_delay_collapsing_multiple_consecutive(self):
        """Multiple consecutive delay steps coalesce into a single combined duration."""
        delays = [
            _make_box("d1", x=10, y=10, action=DesignerActionType.DELAY, val="100"),
            _make_box("d2", x=120, y=10, action=DesignerActionType.DELAY, val="200"),
            _make_box("d3", x=230, y=10, action=DesignerActionType.DELAY, val="300"),
        ]
        opt = PeepholeOptimizationConfig(collapse_delays=True)
        wf = compile_visual_layout_to_workflow(_make_layout(delays, opt=opt))
        delay_steps = [s for s in wf.steps if s.action_type == ActionType.DELAY]
        assert len(delay_steps) == 1
        assert delay_steps[0].parameters.duration_ms == 600

    def test_prune_empty_delays(self):
        """0ms delay steps are pruned when prune_empty_delays=True."""
        boxes = [
            _make_box("t1", x=10, y=10, val="Hello"),
            _make_box("d0", x=150, y=10, action=DesignerActionType.DELAY, val="0"),
            _make_box("t2", x=300, y=10, val="World"),
        ]
        opt = PeepholeOptimizationConfig(prune_empty_delays=True)
        wf = compile_visual_layout_to_workflow(_make_layout(boxes, opt=opt))
        delay_steps = [s for s in wf.steps if s.action_type == ActionType.DELAY]
        assert len(delay_steps) == 0

    def test_click_to_tab_with_force_click(self):
        """click_to_tab prunes redundant click after Tab except when force_click is True."""
        boxes = [
            _make_box("f1", x=10, y=10, nav=NavigationAction.TAB),
            _make_box("f2", x=10, y=50, nav=NavigationAction.TAB, force_click=False),
            _make_box("f3", x=10, y=90, nav=NavigationAction.TAB, force_click=True),
        ]
        opt = PeepholeOptimizationConfig(click_to_tab=True)
        wf = compile_visual_layout_to_workflow(_make_layout(boxes, opt=opt))
        clicks = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert any("f1" in lbl for lbl in clicks)
        assert not any("f2" in lbl for lbl in clicks)
        assert any("f3" in lbl for lbl in clicks)

    def test_strict_contiguous_reindexing(self):
        """Re-indexing pass guarantees strictly contiguous 1..N indices across all steps."""
        boxes = [
            _make_box("f1", x=10, y=10, nav=NavigationAction.TAB),
            _make_box("f2", x=10, y=50, nav=NavigationAction.TAB, force_click=False),
            _make_box("f3", x=10, y=90, nav=NavigationAction.NONE),
        ]
        opt = PeepholeOptimizationConfig(click_to_tab=True)
        wf = compile_visual_layout_to_workflow(_make_layout(boxes, opt=opt))
        indices = [s.sequence_index for s in wf.steps]
        expected = list(range(1, len(wf.steps) + 1))
        assert indices == expected

    def test_vulnerability_click_to_tab_drops_pre_delay(self):
        """
        Remediated: When click_to_tab is enabled, the click step for field 2
        is pruned, and pre_delay_ms configured for that field is preserved on the field's initial step.
        """
        b1 = _make_box("b1", x=10, y=10, nav=NavigationAction.TAB)
        b2 = _make_box("b2", x=10, y=50, nav=NavigationAction.TAB, pre_delay=500)
        wf = compile_visual_layout_to_workflow(
            _make_layout([b1, b2], opt=PeepholeOptimizationConfig(click_to_tab=True))
        )
        b2_steps = [s for s in wf.steps if "b2" in (s.label or "")]
        assert b2_steps[0].pre_delay_ms == 500, "500ms pre_delay must be preserved when click is pruned"
