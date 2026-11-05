"""
tests.test_compiler
Enterprise QA Test Suite for Visual Form Designer Schema and 5-Pass Compiler.
Copyrights reserved to 90Studio
"""

from pathlib import Path
import sys
import time
import pytest
from pydantic import ValidationError

SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from kutomoto.designer.compiler import (  # noqa: E402
    _pass5_optimize_peephole,
    compile_visual_boxes_to_workflow,
    compile_visual_layout_to_workflow,
)
from kutomoto.designer.exceptions import (  # noqa: E402
    DuplicateBoxIdError,
    EmptyLayoutError,
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
from kutomoto.engine.fsm import ExecutionState  # noqa: E402
from kutomoto.engine.runner import WorkflowRunner  # noqa: E402
from kutomoto.engine.safety import MockWin32Driver  # noqa: E402
from kutomoto.engine.schema import (  # noqa: E402
    ActionType,
    KutomotoWorkflow,
    SourceMode,
    StepParameters,
    TargetAppType,
    WorkflowStep,
)


# ==============================================================================
# CLASS 1: TestVisualLayoutSchema (12 Unit Tests)
# ==============================================================================

class TestVisualLayoutSchema:
    def test_valid_minimal_layout(self):
        """Minimal valid layout with exactly 1 text box validates successfully."""
        layout = VisualFormLayout(
            name="Minimal Form",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="Notepad"),
            boxes=[
                VisualBox(
                    name="input_1",
                    geometry=BoxGeometry(x=50, y=50, width=200, height=30),
                )
            ],
        )
        assert layout.name == "Minimal Form"
        assert len(layout.boxes) == 1
        assert layout.copyright == "Copyrights reserved to 90Studio"

    def test_valid_enterprise_banking_layout(self):
        """5-field banking KYC layout with canvas, target, execution settings, optimization."""
        layout = VisualFormLayout(
            name="Banking KYC Customer Onboarding",
            canvas=CanvasDimensions(width=1280, height=800),
            target_application=TargetApplicationSpec(
                type=TargetAppType.WINDOWS_DESKTOP,
                window_title_pattern="Banking KYC",
                process_name="msedge.exe",
            ),
            execution_settings=ExecutionSettingsSpec(
                default_step_delay_ms=100, typing_speed_ms=15
            ),
            optimization=PeepholeOptimizationConfig(
                enabled=True, click_to_tab=True, band_tolerance_px=20.0
            ),
            boxes=[
                VisualBox(
                    name="cust_name",
                    label="Customer Name",
                    geometry=BoxGeometry(x=100, y=100, width=300, height=36),
                    sequence_index=1,
                    value="Jane Doe",
                ),
                VisualBox(
                    name="cust_ssn",
                    label="Social Security Number",
                    geometry=BoxGeometry(x=100, y=160, width=300, height=36),
                    sequence_index=2,
                    value="000-12-3456",
                ),
                VisualBox(
                    name="cust_dob",
                    label="Date of Birth",
                    geometry=BoxGeometry(x=100, y=220, width=200, height=36),
                    sequence_index=3,
                    value="1985-04-12",
                ),
                VisualBox(
                    name="account_type",
                    label="Account Selection",
                    geometry=BoxGeometry(x=100, y=280, width=200, height=36),
                    sequence_index=4,
                    action_type=DesignerActionType.SELECT,
                ),
                VisualBox(
                    name="submit_btn",
                    label="Submit Onboarding",
                    geometry=BoxGeometry(x=100, y=360, width=150, height=40),
                    sequence_index=5,
                    action_type=DesignerActionType.SUBMIT,
                ),
            ],
        )
        assert len(layout.boxes) == 5
        assert layout.execution_settings.typing_speed_ms == 15
        assert layout.optimization.click_to_tab is True

    def test_schema_missing_canvas_fails(self):
        """Layout dictionary missing canvas field raises ValidationError."""
        raw = {
            "name": "Missing Canvas",
            "target": {"window_title_pattern": "Win"},
            "boxes": [{"name": "f1", "rect": {"x": 10, "y": 10, "width": 50, "height": 20}}],
        }
        with pytest.raises(ValidationError):
            VisualFormLayout.model_validate(raw)

    def test_schema_zero_canvas_dimensions(self):
        """Canvas dimensions with width=0 or height=0 must fail validation (> 0)."""
        with pytest.raises(ValidationError):
            CanvasDimensions(width=0, height=768)
        with pytest.raises(ValidationError):
            CanvasDimensions(width=1024, height=0)

    def test_schema_negative_canvas_dimensions(self):
        """Negative canvas dimensions must fail validation."""
        with pytest.raises(ValidationError):
            CanvasDimensions(width=-800, height=600)

    def test_schema_negative_box_coordinates(self):
        """Negative box X or Y coordinates must fail validation."""
        with pytest.raises(ValidationError):
            BoxGeometry(x=-10, y=50, width=100, height=30)
        with pytest.raises(ValidationError):
            BoxGeometry(x=50, y=-5, width=100, height=30)

    def test_schema_zero_or_negative_box_dimensions(self):
        """Box dimensions with width <= 0 or height <= 0 must fail validation."""
        with pytest.raises(ValidationError):
            BoxGeometry(x=0, y=0, width=0, height=30)
        with pytest.raises(ValidationError):
            BoxGeometry(x=0, y=0, width=100, height=-10)

    def test_schema_out_of_canvas_bounds_fails(self):
        """Box exceeding canvas width or height must fail boundary containment validator."""
        with pytest.raises(ValidationError, match="exceeds canvas width"):
            VisualFormLayout(
                name="OutOfBounds",
                canvas=CanvasDimensions(width=1000, height=800),
                target_application=TargetApplicationSpec(window_title_pattern="Win"),
                boxes=[
                    VisualBox(
                        name="overflow_right",
                        geometry=BoxGeometry(x=900, y=100, width=200, height=30),
                    )
                ],
            )

        with pytest.raises(ValidationError, match="exceeds canvas height"):
            VisualFormLayout(
                name="OutOfBounds",
                canvas=CanvasDimensions(width=1000, height=800),
                target_application=TargetApplicationSpec(window_title_pattern="Win"),
                boxes=[
                    VisualBox(
                        name="overflow_bottom",
                        geometry=BoxGeometry(x=100, y=750, width=100, height=60),
                    )
                ],
            )

    def test_schema_empty_boxes_list_fails(self):
        """VisualFormLayout instantiated with boxes=[] must fail min_length=1 validator."""
        with pytest.raises(ValidationError):
            VisualFormLayout(
                name="EmptyBoxes",
                canvas=CanvasDimensions(width=800, height=600),
                target_application=TargetApplicationSpec(window_title_pattern="Win"),
                boxes=[],
            )

    def test_schema_duplicate_box_ids_fails(self):
        """Two boxes sharing an identical ID must fail unique ID validator."""
        with pytest.raises(ValidationError, match="duplicate box IDs"):
            VisualFormLayout(
                name="DuplicateIDs",
                canvas=CanvasDimensions(width=800, height=600),
                target_application=TargetApplicationSpec(window_title_pattern="Win"),
                boxes=[
                    VisualBox(
                        id="dup_id",
                        name="field_1",
                        geometry=BoxGeometry(x=10, y=10, width=100, height=30),
                    ),
                    VisualBox(
                        id="dup_id",
                        name="field_2",
                        geometry=BoxGeometry(x=10, y=50, width=100, height=30),
                    ),
                ],
            )

    def test_schema_copyright_watermark_enforcement(self):
        """Unauthorized or altered copyright watermark must fail strict validation."""
        with pytest.raises(ValidationError, match="Copyrights reserved to 90Studio"):
            VisualFormLayout.model_validate(
                {
                    "name": "CopyrightTest",
                    "copyright": "Unauthorized Copyright Notice",
                    "canvas": {"width": 800, "height": 600},
                    "target": {"match_pattern": "Win"},
                    "boxes": [
                        {"name": "f1", "rect": {"x": 10, "y": 10, "width": 50, "height": 20}}
                    ],
                }
            )

    def test_schema_json_serialization_roundtrip(self):
        """JSON serialization and deserialization preserves all layout and box fields."""
        layout = VisualFormLayout(
            name="Roundtrip Test",
            canvas=CanvasDimensions(width=1920, height=1080),
            target_application=TargetApplicationSpec(window_title_pattern="TestApp"),
            boxes=[
                VisualBox(
                    name="username",
                    label="Username Field",
                    geometry=BoxGeometry(x=100, y=150, width=250, height=35),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="admin_user",
                    navigation=NavigationAction.TAB,
                    clear_before=True,
                    post_delay_ms=150,
                )
            ],
        )
        json_str = layout.model_dump_json()
        restored = VisualFormLayout.model_validate_json(json_str)
        assert restored.name == layout.name
        assert restored.canvas.width == 1920
        assert restored.boxes[0].name == "username"
        assert restored.boxes[0].value == "admin_user"
        assert restored.copyright == "Copyrights reserved to 90Studio"


# ==============================================================================
# CLASS 2: TestCompilerPass1Validation (6 Tests)
# ==============================================================================

class TestCompilerPass1Validation:
    def test_pass1_empty_layout_raises_empty_layout_error(self):
        """Compiling a layout with 0 boxes raises EmptyLayoutError (and ValueError)."""
        raw_layout = {"canvas": {"width": 1000, "height": 800}, "boxes": []}
        with pytest.raises(EmptyLayoutError):
            compile_visual_layout_to_workflow(raw_layout)

    def test_pass1_out_of_bounds_box_x_raises_geometry_error(self):
        """Box exceeding canvas width triggers GeometryError with coordinates."""
        raw_layout = {
            "canvas": {"width": 800, "height": 600},
            "boxes": [
                {"name": "box_x_overflow", "rect": {"x": 750, "y": 100, "width": 100, "height": 30}}
            ],
        }
        with pytest.raises(GeometryError, match="exceeds canvas width"):
            compile_visual_layout_to_workflow(raw_layout)

    def test_pass1_out_of_bounds_box_y_raises_geometry_error(self):
        """Box exceeding canvas height triggers GeometryError with coordinates."""
        raw_layout = {
            "canvas": {"width": 800, "height": 600},
            "boxes": [
                {"name": "box_y_overflow", "rect": {"x": 100, "y": 550, "width": 100, "height": 80}}
            ],
        }
        with pytest.raises(GeometryError, match="exceeds canvas height"):
            compile_visual_layout_to_workflow(raw_layout)

    def test_pass1_zero_canvas_dimensions_raises_geometry_error(self):
        """Canvas with width=0 or height=0 triggers GeometryError."""
        raw_layout = {
            "canvas": {"width": 0, "height": 600},
            "boxes": [{"name": "f1", "rect": {"x": 10, "y": 10, "width": 50, "height": 20}}],
        }
        with pytest.raises(GeometryError, match="Canvas dimensions must be strictly positive"):
            compile_visual_layout_to_workflow(raw_layout)

    def test_pass1_zero_box_dimensions_raises_geometry_error(self):
        """Box with zero or negative width/height triggers GeometryError."""
        raw_layout = {
            "canvas": {"width": 800, "height": 600},
            "boxes": [{"name": "zero_w", "rect": {"x": 10, "y": 10, "width": 0, "height": 30}}],
        }
        with pytest.raises(GeometryError, match="invalid zero or negative dimensions"):
            compile_visual_layout_to_workflow(raw_layout)

    def test_pass1_error_message_contains_box_identity(self):
        """GeometryError contains the offending box name or ID and coordinate details."""
        raw_layout = {
            "canvas": {"width": 800, "height": 600},
            "boxes": [
                {
                    "id": "box_unique_123",
                    "name": "suspicious_field",
                    "rect": {"x": 750, "y": 100, "width": 150, "height": 30},
                }
            ],
        }
        with pytest.raises(GeometryError) as exc_info:
            compile_visual_layout_to_workflow(raw_layout)
        err_msg = str(exc_info.value)
        assert "box_unique_123" in err_msg or "suspicious_field" in err_msg
        assert "800.00" in err_msg or "900" in err_msg

    def test_pass1_duplicate_box_id_raises_duplicate_box_id_error(self):
        """Layout with duplicate box IDs triggers DuplicateBoxIdError."""
        raw_layout = {
            "canvas": {"width": 800, "height": 600},
            "boxes": [
                {"id": "box_dup_1", "name": "f1", "rect": {"x": 10, "y": 10, "width": 50, "height": 20}},
                {"id": "box_dup_1", "name": "f2", "rect": {"x": 10, "y": 50, "width": 50, "height": 20}},
            ],
        }
        with pytest.raises(DuplicateBoxIdError, match="Duplicate box ID detected"):
            compile_visual_layout_to_workflow(raw_layout)


# ==============================================================================
# CLASS 3: TestCompilerPass2SpatialBandSorting (8 Tests)
# ==============================================================================

class TestCompilerPass2SpatialBandSorting:
    def test_pass2_explicit_sequence_indices_strictly_honored(self):
        """Explicit sequence indices [1, 2, 3, 4] override visual Y/X coordinates."""
        layout = VisualFormLayout(
            name="Explicit Sequence Order",
            canvas=CanvasDimensions(width=1000, height=1000),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="step_4", geometry=BoxGeometry(x=50, y=50, width=100, height=30), sequence_index=4),
                VisualBox(name="step_1", geometry=BoxGeometry(x=50, y=400, width=100, height=30), sequence_index=1),
                VisualBox(name="step_3", geometry=BoxGeometry(x=50, y=200, width=100, height=30), sequence_index=3),
                VisualBox(name="step_2", geometry=BoxGeometry(x=50, y=300, width=100, height=30), sequence_index=2),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        step_labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "step_1" in step_labels[0]
        assert "step_2" in step_labels[1]
        assert "step_3" in step_labels[2]
        assert "step_4" in step_labels[3]

    def test_pass2_spatial_single_column_top_to_bottom(self):
        """Unindexed boxes arranged in a vertical column sort top-to-bottom by Y."""
        layout = VisualFormLayout(
            name="Single Column",
            canvas=CanvasDimensions(width=800, height=1000),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="col_3", geometry=BoxGeometry(x=100, y=300, width=200, height=30)),
                VisualBox(name="col_1", geometry=BoxGeometry(x=100, y=100, width=200, height=30)),
                VisualBox(name="col_2", geometry=BoxGeometry(x=100, y=200, width=200, height=30)),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        step_labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "col_1" in step_labels[0]
        assert "col_2" in step_labels[1]
        assert "col_3" in step_labels[2]

    def test_pass2_spatial_single_row_left_to_right(self):
        """Unindexed boxes in a single horizontal row sort left-to-right by X."""
        layout = VisualFormLayout(
            name="Single Row",
            canvas=CanvasDimensions(width=1000, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="cell_right", geometry=BoxGeometry(x=400, y=100, width=100, height=30)),
                VisualBox(name="cell_left", geometry=BoxGeometry(x=100, y=100, width=100, height=30)),
                VisualBox(name="cell_center", geometry=BoxGeometry(x=250, y=100, width=100, height=30)),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        step_labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "cell_left" in step_labels[0]
        assert "cell_center" in step_labels[1]
        assert "cell_right" in step_labels[2]

    def test_pass2_spatial_2x2_grid_reading_order(self):
        """Shuffled 2x2 grid (R1C1, R1C2, R2C1, R2C2) restores Western reading order."""
        layout = VisualFormLayout(
            name="2x2 Grid",
            canvas=CanvasDimensions(width=1000, height=1000),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="R2C2", geometry=BoxGeometry(x=350, y=200, width=150, height=30)),
                VisualBox(name="R1C2", geometry=BoxGeometry(x=350, y=100, width=150, height=30)),
                VisualBox(name="R2C1", geometry=BoxGeometry(x=100, y=200, width=150, height=30)),
                VisualBox(name="R1C1", geometry=BoxGeometry(x=100, y=100, width=150, height=30)),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        step_labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "R1C1" in step_labels[0]
        assert "R1C2" in step_labels[1]
        assert "R2C1" in step_labels[2]
        assert "R2C2" in step_labels[3]

    def test_pass2_band_tolerance_close_fields_grouped(self):
        """Boxes with |y2 - y1| = 12 <= 24px default tolerance are clustered into the same row."""
        layout = VisualFormLayout(
            name="Tolerance Grouping",
            canvas=CanvasDimensions(width=1000, height=1000),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="b_right", geometry=BoxGeometry(x=300, y=112, width=100, height=30)),
                VisualBox(name="b_left", geometry=BoxGeometry(x=100, y=100, width=100, height=30)),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        step_labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "b_left" in step_labels[0]
        assert "b_right" in step_labels[1]

    def test_pass2_band_tolerance_distant_fields_split(self):
        """Boxes with |y2 - y1| = 35 > 24px tolerance are split into distinct vertical bands."""
        layout = VisualFormLayout(
            name="Tolerance Splitting",
            canvas=CanvasDimensions(width=1000, height=1000),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="b_bottom_left", geometry=BoxGeometry(x=50, y=135, width=100, height=30)),
                VisualBox(name="b_top_right", geometry=BoxGeometry(x=400, y=100, width=100, height=30)),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        step_labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "b_top_right" in step_labels[0]
        assert "b_bottom_left" in step_labels[1]

    def test_pass2_custom_band_tolerance_override(self):
        """Custom band_tolerance_px=40 groups fields separated by 35px into the same row."""
        layout = VisualFormLayout(
            name="Custom Tolerance",
            canvas=CanvasDimensions(width=1000, height=1000),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            optimization=PeepholeOptimizationConfig(band_tolerance_px=40.0),
            boxes=[
                VisualBox(name="b_right", geometry=BoxGeometry(x=300, y=135, width=100, height=30)),
                VisualBox(name="b_left", geometry=BoxGeometry(x=100, y=100, width=100, height=30)),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        step_labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "b_left" in step_labels[0]
        assert "b_right" in step_labels[1]

    def test_pass2_hybrid_explicit_and_spatial_boxes(self):
        """Explicit boxes execute first in sequence_index order, followed by spatially sorted unindexed boxes."""
        layout = VisualFormLayout(
            name="Hybrid Layout",
            canvas=CanvasDimensions(width=1000, height=1000),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="unindexed_bottom", geometry=BoxGeometry(x=100, y=400, width=100, height=30)),
                VisualBox(name="explicit_2", geometry=BoxGeometry(x=100, y=300, width=100, height=30), sequence_index=2),
                VisualBox(name="unindexed_top", geometry=BoxGeometry(x=100, y=100, width=100, height=30)),
                VisualBox(name="explicit_1", geometry=BoxGeometry(x=100, y=200, width=100, height=30), sequence_index=1),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        step_labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "explicit_1" in step_labels[0]
        assert "explicit_2" in step_labels[1]
        assert "unindexed_top" in step_labels[2]
        assert "unindexed_bottom" in step_labels[3]


# ==============================================================================
# CLASS 4: TestCompilerPass3CoordinateNormalization (5 Tests)
# ==============================================================================

class TestCompilerPass3CoordinateNormalization:
    def test_pass3_center_calculation_precision(self):
        """Box at (100, 200, 300, 100) on canvas (1000, 1000) has center (250, 250) -> norm (0.2500, 0.2500)."""
        layout = VisualFormLayout(
            name="Precision Test",
            canvas=CanvasDimensions(width=1000, height=1000),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="b1", geometry=BoxGeometry(x=100, y=200, width=300, height=100))
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        click_step = next(s for s in wf.steps if s.action_type == ActionType.CLICK)
        assert click_step.parameters.norm_x == 0.25
        assert click_step.parameters.norm_y == 0.25

    def test_pass3_boundary_coordinates_strictly_clamped(self):
        """Boxes flush against edges produce norm coordinates strictly in [0.0, 1.0]."""
        layout = VisualFormLayout(
            name="Clamp Test",
            canvas=CanvasDimensions(width=1000, height=1000),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="top_left", geometry=BoxGeometry(x=0, y=0, width=50, height=50)),
                VisualBox(name="bottom_right", geometry=BoxGeometry(x=950, y=950, width=50, height=50)),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        clicks = [s for s in wf.steps if s.action_type == ActionType.CLICK]
        for c in clicks:
            assert 0.0 <= c.parameters.norm_x <= 1.0
            assert 0.0 <= c.parameters.norm_y <= 1.0

    def test_pass3_rounding_to_4_decimal_places(self):
        """Coordinates with non-terminating fractions round to 4 decimal places."""
        layout = VisualFormLayout(
            name="Rounding Test",
            canvas=CanvasDimensions(width=300, height=300),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="fractional", geometry=BoxGeometry(x=50, y=50, width=100, height=100))
            ],
        )
        norm = layout.get_normalized_box(layout.boxes[0])
        # Center = 50 + 50 = 100 / 300 = 0.333333... -> 0.3333
        assert norm["center_norm_x"] == 0.3333
        assert norm["center_norm_y"] == 0.3333

    def test_pass3_normalized_dimensions_accuracy(self):
        """Box (100, 100, 200, 50) on (800, 600) yields norm_w=0.2500, norm_h=0.0833."""
        layout = VisualFormLayout(
            name="Norm Dimensions",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="norm_dims", geometry=BoxGeometry(x=100, y=100, width=200, height=50))
            ],
        )
        norm = layout.get_normalized_box(layout.boxes[0])
        assert norm["norm_w"] == 0.25
        assert norm["norm_h"] == 0.0833

    def test_pass3_dual_coordinates_embedded_in_metadata(self):
        """Workflow metadata embeds canvas dimensions and box count."""
        layout = VisualFormLayout(
            name="Metadata Test",
            canvas=CanvasDimensions(width=1920, height=1080),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="b1", geometry=BoxGeometry(x=10, y=10, width=50, height=20)),
                VisualBox(name="b2", geometry=BoxGeometry(x=10, y=40, width=50, height=20)),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        assert wf.designer_metadata is not None
        assert wf.designer_metadata.canvas_width == 1920
        assert wf.designer_metadata.canvas_height == 1080
        assert wf.designer_metadata.box_count == 2


# ==============================================================================
# CLASS 5: TestCompilerPass4ActionStepSynthesis (9 Tests)
# ==============================================================================

class TestCompilerPass4ActionStepSynthesis:
    def test_pass4_step1_is_focus_window_header(self):
        """Step 1 is always FOCUS_WINDOW with target application window title pattern."""
        layout = VisualFormLayout(
            name="Focus Header",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(
                window_title_pattern=".*CRM Portal.*", process_name="chrome.exe"
            ),
            boxes=[VisualBox(name="b1", geometry=BoxGeometry(x=10, y=10, width=50, height=20))],
        )
        wf = compile_visual_layout_to_workflow(layout)
        assert len(wf.steps) >= 1
        step1 = wf.steps[0]
        assert step1.sequence_index == 1
        assert step1.action_type == ActionType.FOCUS_WINDOW
        assert step1.parameters.window_title_pattern == ".*CRM Portal.*"
        assert step1.parameters.process_name == "chrome.exe"

    def test_pass4_text_box_full_action_chain(self):
        """type_text box generates CLICK -> CLEAR_FIELD -> TYPE_TEXT -> KEY_PRESS(tab)."""
        layout = VisualFormLayout(
            name="Text Action Chain",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(
                    name="username",
                    geometry=BoxGeometry(x=50, y=50, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="alice_in_wonderland",
                    navigation=NavigationAction.TAB,
                    clear_before=True,
                )
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        # Steps: 1: FOCUS, 2: CLICK, 3: CLEAR, 4: TYPE, 5: KEY_PRESS
        action_types = [s.action_type for s in wf.steps]
        assert action_types == [
            ActionType.FOCUS_WINDOW,
            ActionType.CLICK,
            ActionType.CLEAR_FIELD,
            ActionType.TYPE_TEXT,
            ActionType.KEY_PRESS,
        ]

    def test_pass4_clear_before_false_omits_clear_step(self):
        """clear_before=False omits the CLEAR_FIELD action step."""
        layout = VisualFormLayout(
            name="No Clear",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(
                    name="append_field",
                    geometry=BoxGeometry(x=50, y=50, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="append_value",
                    clear_before=False,
                    navigation=NavigationAction.NONE,
                )
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        action_types = [s.action_type for s in wf.steps]
        assert ActionType.CLEAR_FIELD not in action_types
        assert action_types == [ActionType.FOCUS_WINDOW, ActionType.CLICK, ActionType.TYPE_TEXT]

    def test_pass4_navigation_enter_generates_enter_key(self):
        """navigation='enter' generates a KEY_PRESS step with key='enter'."""
        layout = VisualFormLayout(
            name="Enter Nav",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(
                    name="search_query",
                    geometry=BoxGeometry(x=50, y=50, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="kutomoto",
                    navigation=NavigationAction.ENTER,
                )
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        key_step = next(s for s in wf.steps if s.action_type == ActionType.KEY_PRESS)
        assert key_step.parameters.key == "enter"

    def test_pass4_navigation_none_omits_key_press(self):
        """navigation='none' emits no trailing KEY_PRESS step."""
        layout = VisualFormLayout(
            name="No Nav",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(
                    name="isolated_field",
                    geometry=BoxGeometry(x=50, y=50, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    navigation=NavigationAction.NONE,
                )
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        assert not any(s.action_type == ActionType.KEY_PRESS for s in wf.steps)

    def test_pass4_click_box_generates_click_step(self):
        """action_type='click' generates CLICK with normalized center coordinates."""
        layout = VisualFormLayout(
            name="Click Box",
            canvas=CanvasDimensions(width=1000, height=1000),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(
                    name="toggle_opt",
                    geometry=BoxGeometry(x=200, y=400, width=100, height=50),
                    action_type=DesignerActionType.CLICK,
                    navigation=NavigationAction.NONE,
                )
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        click_step = next(s for s in wf.steps if s.action_type == ActionType.CLICK)
        assert click_step.parameters.norm_x == 0.25
        assert click_step.parameters.norm_y == 0.425

    def test_pass4_submit_box_generates_submit_step(self):
        """action_type='submit' generates SUBMIT with BUTTON_CLICK method."""
        layout = VisualFormLayout(
            name="Submit Box",
            canvas=CanvasDimensions(width=1000, height=1000),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(
                    name="btn_submit",
                    geometry=BoxGeometry(x=400, y=800, width=200, height=50),
                    action_type=DesignerActionType.SUBMIT,
                )
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        submit_step = next(s for s in wf.steps if s.action_type == ActionType.SUBMIT)
        assert submit_step.parameters.norm_x == 0.5
        assert submit_step.parameters.norm_y == 0.825

    def test_pass4_timing_parameters_propagation(self):
        """Custom box timing parameters (pre_delay, post_delay, typing_speed) propagate to steps."""
        layout = VisualFormLayout(
            name="Timing Prop",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(
                    name="timed_field",
                    geometry=BoxGeometry(x=50, y=50, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="speedy",
                    timing=BoxTiming(pre_delay_ms=80, typing_speed_ms=35, post_delay_ms=220),
                    navigation=NavigationAction.NONE,
                )
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        click_step = next(s for s in wf.steps if s.action_type == ActionType.CLICK)
        type_step = next(s for s in wf.steps if s.action_type == ActionType.TYPE_TEXT)
        assert click_step.pre_delay_ms == 80
        assert type_step.parameters.keystroke_delay_ms == 35
        assert type_step.post_delay_ms == 220

    def test_pass4_variable_template_preservation(self):
        """Variable syntax {{account_id}} in value is preserved intact."""
        layout = VisualFormLayout(
            name="Variable Template",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(
                    name="acc_field",
                    geometry=BoxGeometry(x=50, y=50, width=200, height=30),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="{{customer_account_number}}",
                    navigation=NavigationAction.NONE,
                )
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        type_step = next(s for s in wf.steps if s.action_type == ActionType.TYPE_TEXT)
        assert type_step.parameters.text == "{{customer_account_number}}"


# ==============================================================================
# CLASS 6: TestCompilerPass5PeepholeOptimizer (11 Tests)
# ==============================================================================

class TestCompilerPass5PeepholeOptimizer:
    def test_pass5_click_to_tab_disabled_by_default(self):
        """Under default configuration (click_to_tab=False), all CLICK steps are preserved."""
        layout = VisualFormLayout(
            name="Default No Prune",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="f1", geometry=BoxGeometry(x=50, y=50, width=200, height=30), navigation=NavigationAction.TAB),
                VisualBox(name="f2", geometry=BoxGeometry(x=50, y=100, width=200, height=30), navigation=NavigationAction.TAB),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        clicks = [s for s in wf.steps if s.action_type == ActionType.CLICK]
        assert len(clicks) == 2

    def test_pass5_click_to_tab_enabled_drops_second_click(self):
        """When click_to_tab=True, redundant CLICK on field 2 following Tab is eliminated."""
        layout = VisualFormLayout(
            name="Click to Tab Enabled",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
            boxes=[
                VisualBox(name="f1", geometry=BoxGeometry(x=50, y=50, width=200, height=30), navigation=NavigationAction.TAB),
                VisualBox(name="f2", geometry=BoxGeometry(x=50, y=100, width=200, height=30), navigation=NavigationAction.TAB),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        clicks = [s for s in wf.steps if s.action_type == ActionType.CLICK]
        assert len(clicks) == 1
        assert "f1" in clicks[0].label

    def test_pass5_click_to_tab_first_field_click_preserved(self):
        """The initial field's anchor CLICK is NEVER pruned regardless of optimization config."""
        layout = VisualFormLayout(
            name="Preserve First Click",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
            boxes=[
                VisualBox(name="initial_box", geometry=BoxGeometry(x=50, y=50, width=200, height=30))
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        assert any(s.action_type == ActionType.CLICK and "initial_box" in s.label for s in wf.steps)

    def test_pass5_click_to_tab_preserved_after_navigation_none(self):
        """If field 1 specifies navigation='none', field 2's CLICK is preserved (tab not pressed)."""
        layout = VisualFormLayout(
            name="Nav None Preserved",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
            boxes=[
                VisualBox(name="f1", geometry=BoxGeometry(x=50, y=50, width=200, height=30), navigation=NavigationAction.NONE),
                VisualBox(name="f2", geometry=BoxGeometry(x=50, y=100, width=200, height=30)),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        clicks = [s for s in wf.steps if s.action_type == ActionType.CLICK]
        assert len(clicks) == 2

    def test_pass5_consecutive_delay_collapse_two_delays(self):
        """Consecutive DELAY(100) and DELAY(200) steps are coalesced into a single DELAY(300)."""
        steps = [
            WorkflowStep(sequence_index=1, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=100)),
            WorkflowStep(sequence_index=2, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=200)),
        ]
        opt = PeepholeOptimizationConfig(enabled=True, collapse_delays=True)
        res = _pass5_optimize_peephole(steps, opt)
        assert len(res) == 1
        assert res[0].action_type == ActionType.DELAY
        assert res[0].parameters.duration_ms == 300

    def test_pass5_consecutive_delay_collapse_three_delays(self):
        """Three consecutive delays (100 + 150 + 250) coalesce into a single DELAY(500)."""
        steps = [
            WorkflowStep(sequence_index=1, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=100)),
            WorkflowStep(sequence_index=2, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=150)),
            WorkflowStep(sequence_index=3, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=250)),
        ]
        opt = PeepholeOptimizationConfig(enabled=True, collapse_delays=True)
        res = _pass5_optimize_peephole(steps, opt)
        assert len(res) == 1
        assert res[0].parameters.duration_ms == 500

    def test_pass5_delay_collapse_disabled(self):
        """When collapse_delays=False, adjacent delays remain separate steps."""
        steps = [
            WorkflowStep(sequence_index=1, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=100)),
            WorkflowStep(sequence_index=2, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=200)),
        ]
        opt = PeepholeOptimizationConfig(enabled=True, collapse_delays=False)
        res = _pass5_optimize_peephole(steps, opt)
        assert len(res) == 2

    def test_pass5_prune_empty_zero_ms_delay(self):
        """DELAY(duration_ms=0) is pruned entirely when prune_empty_delays=True."""
        steps = [
            WorkflowStep(sequence_index=1, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=0)),
            WorkflowStep(sequence_index=2, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key="tab")),
        ]
        opt = PeepholeOptimizationConfig(enabled=True, prune_empty_delays=True)
        res = _pass5_optimize_peephole(steps, opt)
        assert len(res) == 1
        assert res[0].action_type == ActionType.KEY_PRESS

    def test_pass5_prune_duplicate_focus_window(self):
        """Two consecutive identical FOCUS_WINDOW steps drop the second step."""
        steps = [
            WorkflowStep(
                sequence_index=1,
                action_type=ActionType.FOCUS_WINDOW,
                parameters=StepParameters(window_title_pattern="App", process_name="app.exe"),
            ),
            WorkflowStep(
                sequence_index=2,
                action_type=ActionType.FOCUS_WINDOW,
                parameters=StepParameters(window_title_pattern="App", process_name="app.exe"),
            ),
        ]
        opt = PeepholeOptimizationConfig(enabled=True, remove_redundant_focus=True)
        res = _pass5_optimize_peephole(steps, opt)
        assert len(res) == 1

    def test_pass5_master_switch_disabled_passthrough(self):
        """When optimization.enabled=False, no steps are dropped or collapsed."""
        steps = [
            WorkflowStep(sequence_index=1, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=100)),
            WorkflowStep(sequence_index=2, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=200)),
        ]
        opt = PeepholeOptimizationConfig(enabled=False, collapse_delays=True)
        res = _pass5_optimize_peephole(steps, opt)
        assert len(res) == 2

    def test_pass5_strict_contiguous_sequence_reindexing(self):
        """After pruning or merging, steps are strictly renumbered 1..N without gaps."""
        steps = [
            WorkflowStep(sequence_index=10, action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=100)),
            WorkflowStep(sequence_index=20, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key="tab")),
            WorkflowStep(sequence_index=30, action_type=ActionType.KEY_PRESS, parameters=StepParameters(key="enter")),
        ]
        opt = PeepholeOptimizationConfig(enabled=True)
        res = _pass5_optimize_peephole(steps, opt)
        indices = [s.sequence_index for s in res]
        assert indices == [1, 2, 3]


# ==============================================================================
# CLASS 7: TestCompilerIntegrationAndEdgeCases (8 Tests)
# ==============================================================================

class TestCompilerIntegrationAndEdgeCases:
    @pytest.mark.asyncio
    async def test_roundtrip_banking_kyc_workflow_execution(self, monkeypatch):
        """Full round-trip compilation and asynchronous execution against WorkflowRunner and MockWin32Driver."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        layout = VisualFormLayout(
            name="Banking KYC Customer Onboarding",
            target_application=TargetApplicationSpec(
                window_title_pattern=".*Banking KYC.*", process_name="msedge.exe"
            ),
            canvas=CanvasDimensions(width=1024, height=768),
            execution_settings=ExecutionSettingsSpec(countdown_seconds=0),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
            boxes=[
                VisualBox(
                    name="full_name",
                    label="Customer Full Name",
                    geometry=BoxGeometry(x=100, y=100, width=250, height=36),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="Jane Doe",
                    navigation=NavigationAction.TAB,
                    clear_before=True,
                ),
                VisualBox(
                    name="account_number",
                    label="Account Number",
                    geometry=BoxGeometry(x=100, y=160, width=250, height=36),
                    action_type=DesignerActionType.TYPE_TEXT,
                    value="9876543210",
                    navigation=NavigationAction.TAB,
                    clear_before=True,
                ),
                VisualBox(
                    name="btn_submit",
                    label="Submit KYC Application",
                    geometry=BoxGeometry(x=100, y=240, width=120, height=40),
                    action_type=DesignerActionType.SUBMIT,
                    navigation=NavigationAction.NONE,
                ),
            ],
        )

        workflow = compile_visual_layout_to_workflow(layout)
        assert isinstance(workflow, KutomotoWorkflow)
        assert workflow.copyright == "Copyrights reserved to 90Studio"
        assert workflow.source_mode == SourceMode.VISUAL_DESIGNER_GENERATED

        driver = MockWin32Driver()
        driver.reset()
        runner = WorkflowRunner(driver=driver)

        audit = await runner.execute(workflow)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert audit.execution_summary.failed_steps == 0
        assert runner.state == ExecutionState.COMPLETED
        assert 1001 in driver.focus_history
        assert "Jane Doe" in driver.typed_text
        assert "9876543210" in driver.typed_text
        assert any(k["key"] == "tab" for k in driver.key_presses)

    @pytest.mark.asyncio
    async def test_roundtrip_telecom_sim_provisioning_execution(self, monkeypatch):
        """Telecom SIM Provisioning layout compilation and execution."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        driver = MockWin32Driver()
        driver.reset()
        driver.windows[1003] = {
            "title": "Telecom SIM Activation Terminal - 90Studio",
            "process_name": "sim_provision.exe",
            "pid": 6000,
            "rect": (50, 50, 900, 700),
            "is_iconic": False,
            "is_window": True,
        }

        layout = VisualFormLayout(
            name="Telecom SIM Provisioning",
            target_application=TargetApplicationSpec(
                window_title_pattern=".*Telecom SIM Activation.*", process_name="sim_provision.exe"
            ),
            canvas=CanvasDimensions(width=1000, height=800),
            execution_settings=ExecutionSettingsSpec(countdown_seconds=0),
            boxes=[
                VisualBox(
                    name="msisdn",
                    geometry=BoxGeometry(x=50, y=50, width=200, height=30),
                    value="+12025550199",
                    navigation=NavigationAction.TAB,
                ),
                VisualBox(
                    name="iccid",
                    geometry=BoxGeometry(x=50, y=100, width=200, height=30),
                    value="89014103211118510720",
                    navigation=NavigationAction.NONE,
                ),
            ],
        )

        wf = compile_visual_layout_to_workflow(layout)
        runner = WorkflowRunner(driver=driver)
        audit = await runner.execute(wf)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED
        assert "+12025550199" in driver.typed_text
        assert "89014103211118510720" in driver.typed_text

    def test_edge_case_single_box_layout(self):
        """Layout with exactly 1 box compiles cleanly without off-by-one errors."""
        layout = VisualFormLayout(
            name="Single Box",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(
                    name="lonely_box",
                    geometry=BoxGeometry(x=100, y=100, width=150, height=35),
                    value="solitary",
                    navigation=NavigationAction.NONE,
                )
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        assert len(wf.steps) >= 3  # FOCUS, CLICK, CLEAR, TYPE
        assert wf.designer_metadata.box_count == 1

    def test_edge_case_stress_50_fields_performance(self):
        """Stress-test compiling a 10x5 grid of 50 visual boxes completes in < 50ms."""
        boxes = []
        for i in range(50):
            row = i // 5
            col = i % 5
            boxes.append(
                VisualBox(
                    id=f"box_stress_{i}",
                    name=f"field_{i}",
                    geometry=BoxGeometry(
                        x=50 + col * 180, y=50 + row * 45, width=160, height=32
                    ),
                    value=f"value_{i}",
                    navigation=NavigationAction.TAB,
                )
            )

        layout = VisualFormLayout(
            name="Stress Grid Form",
            canvas=CanvasDimensions(width=1920, height=1080),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=boxes,
        )

        t0 = time.perf_counter()
        wf = compile_visual_layout_to_workflow(layout)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert elapsed_ms < 50.0, f"Compilation took {elapsed_ms:.2f}ms (budget < 50ms)"
        assert wf.designer_metadata.box_count == 50
        assert len(wf.steps) > 50

    def test_edge_case_dense_overlapping_boxes(self):
        """Boxes with overlapping geometries log collision warnings but compile deterministically."""
        layout = VisualFormLayout(
            name="Overlapping Boxes",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="layer_base", geometry=BoxGeometry(x=100, y=100, width=200, height=50)),
                VisualBox(name="layer_overlay", geometry=BoxGeometry(x=150, y=120, width=180, height=50)),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        assert len(wf.steps) >= 3
        assert wf.designer_metadata.box_count == 2

    def test_edge_case_extremely_close_boxes_1px_gap(self):
        """Boxes separated by 1px vertically cluster in the same band and sort horizontally."""
        layout = VisualFormLayout(
            name="1px Proximity",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="right_box", geometry=BoxGeometry(x=300, y=101, width=100, height=30)),
                VisualBox(name="left_box", geometry=BoxGeometry(x=100, y=100, width=100, height=30)),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        clicks = [s for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "left_box" in clicks[0].label
        assert "right_box" in clicks[1].label

    def test_edge_case_extreme_canvas_aspect_ratios(self):
        """Ultrawide (3840x1080) and portrait (1080x1920) canvases compute valid normalized bounds."""
        ultrawide = VisualFormLayout(
            name="Ultrawide Canvas",
            canvas=CanvasDimensions(width=3840, height=1080),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="wide_box", geometry=BoxGeometry(x=1920, y=540, width=500, height=50))
            ],
        )
        wf_wide = compile_visual_layout_to_workflow(ultrawide)
        click_wide = next(s for s in wf_wide.steps if s.action_type == ActionType.CLICK)
        assert 0.0 <= click_wide.parameters.norm_x <= 1.0
        assert 0.0 <= click_wide.parameters.norm_y <= 1.0

        portrait = VisualFormLayout(
            name="Portrait Canvas",
            canvas=CanvasDimensions(width=1080, height=1920),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="tall_box", geometry=BoxGeometry(x=200, y=1500, width=400, height=60))
            ],
        )
        wf_tall = compile_visual_layout_to_workflow(portrait)
        click_tall = next(s for s in wf_tall.steps if s.action_type == ActionType.CLICK)
        assert 0.0 <= click_tall.parameters.norm_x <= 1.0
        assert 0.0 <= click_tall.parameters.norm_y <= 1.0

    @pytest.mark.asyncio
    async def test_edge_case_unicode_and_special_characters(self, monkeypatch):
        """Special characters, quotes, accents, and Unicode payloads compile and inject without corruption."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        driver = MockWin32Driver()
        driver.reset()

        unicode_payload = "Müller & Söhne «90Studio» — 100€ — 'single' & \"double\""
        layout = VisualFormLayout(
            name="Unicode Form",
            canvas=CanvasDimensions(width=1024, height=768),
            target_application=TargetApplicationSpec(window_title_pattern="Banking KYC"),
            execution_settings=ExecutionSettingsSpec(countdown_seconds=0),
            boxes=[
                VisualBox(
                    name="company_name",
                    geometry=BoxGeometry(x=100, y=100, width=300, height=36),
                    value=unicode_payload,
                    navigation=NavigationAction.NONE,
                )
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        runner = WorkflowRunner(driver=driver)
        audit = await runner.execute(wf)

        assert audit.execution_summary.final_status == "SUCCESS"
        assert unicode_payload in driver.typed_text

    def test_compile_visual_boxes_to_workflow_alias(self):
        """Compatibility alias compile_visual_boxes_to_workflow maps traversal_mode='tab_chained'."""
        layout = {
            "canvas": {"width": 800, "height": 600},
            "boxes": [
                {"name": "f1", "rect": {"x": 50, "y": 50, "width": 200, "height": 30}, "navigation": "tab"},
                {"name": "f2", "rect": {"x": 50, "y": 100, "width": 200, "height": 30}, "navigation": "tab"},
            ],
        }
        wf_coord = compile_visual_boxes_to_workflow(layout, traversal_mode="coordinate_targeted")
        clicks_coord = [s for s in wf_coord.steps if s.action_type == ActionType.CLICK]
        assert len(clicks_coord) == 2

        wf_tab = compile_visual_boxes_to_workflow(layout, traversal_mode="tab_chained")
        clicks_tab = [s for s in wf_tab.steps if s.action_type == ActionType.CLICK]
        assert len(clicks_tab) == 1


# ==============================================================================
# CLASS 8: TestCompilerRegressionAndEdgeCases (Comprehensive Fix Suite)
# ==============================================================================

class TestCompilerRegressionAndEdgeCases:
    """
    Comprehensive regression and edge-case test suite covering:
    - Sequence index 1-based validation and ordering (Finding F1)
    - force_click=True preservation under click_to_tab for TYPE_TEXT (Reviewer Finding 1)
    - force_click=True preservation for CLICK, CHECKBOX, SELECT (Reviewer Finding 1)
    - Standalone CLICK, CHECKBOX, SELECT preservation without force_click (Reviewer Finding 1)
    - KEY_PRESS delay parameter inheritance (Reviewer Finding 2)
    - Pre-delay preservation when focus clicks are pruned (Challenger Finding F2)
    """

    # --------------------------------------------------------------------------
    # 1. Sequence Indexing Harmonization (Finding F1)
    # --------------------------------------------------------------------------

    def test_schema_sequence_index_ge_1_validation(self):
        """VisualBox rejects sequence_index < 1 (ge=1) and permits positive integers or None."""
        # Valid: sequence_index=1, 2, None
        b_valid1 = VisualBox(name="f1", geometry=BoxGeometry(x=10, y=10, width=50, height=20), sequence_index=1)
        b_valid2 = VisualBox(name="f2", geometry=BoxGeometry(x=10, y=10, width=50, height=20), sequence_index=None)
        assert b_valid1.sequence_index == 1
        assert b_valid2.sequence_index is None

        # Invalid: sequence_index=0 must fail schema validation (strictly 1-based)
        with pytest.raises(ValidationError) as exc_info:
            VisualBox(name="f0", geometry=BoxGeometry(x=10, y=10, width=50, height=20), sequence_index=0)
        assert "greater than or equal to 1" in str(exc_info.value).lower()

        # Invalid: negative sequence_index must fail schema validation
        with pytest.raises(ValidationError):
            VisualBox(name="f_neg", geometry=BoxGeometry(x=10, y=10, width=50, height=20), sequence_index=-1)

    def test_compiler_sequence_indexing_strictly_honored(self):
        """Explicit sequence indices [1, 2, 3] execute strictly in order regardless of inverted geometry."""
        layout = VisualFormLayout(
            name="Seq Index Order",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="b3", geometry=BoxGeometry(x=10, y=300, width=50, height=20), sequence_index=3),
                VisualBox(name="b1", geometry=BoxGeometry(x=10, y=100, width=50, height=20), sequence_index=1),
                VisualBox(name="b2", geometry=BoxGeometry(x=10, y=200, width=50, height=20), sequence_index=2),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        click_labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "b1" in click_labels[0]
        assert "b2" in click_labels[1]
        assert "b3" in click_labels[2]

    def test_compiler_sequence_indexing_hybrid_unindexed_at_tail(self):
        """Explicit boxes (sequence_index >= 1) execute first, unindexed boxes (None) resolve spatially at tail."""
        layout = VisualFormLayout(
            name="Hybrid Layout",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(name="unindexed_top", geometry=BoxGeometry(x=10, y=50, width=50, height=20), sequence_index=None),
                VisualBox(name="explicit_2", geometry=BoxGeometry(x=10, y=300, width=50, height=20), sequence_index=2),
                VisualBox(name="explicit_1", geometry=BoxGeometry(x=10, y=200, width=50, height=20), sequence_index=1),
                VisualBox(name="unindexed_bottom", geometry=BoxGeometry(x=10, y=400, width=50, height=20), sequence_index=None),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        click_labels = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]
        assert "explicit_1" in click_labels[0]
        assert "explicit_2" in click_labels[1]
        assert "unindexed_top" in click_labels[2]
        assert "unindexed_bottom" in click_labels[3]

    # --------------------------------------------------------------------------
    # 2. force_click=True under click_to_tab=True (Reviewer Finding 1 & Finding 3)
    # --------------------------------------------------------------------------

    def test_pass5_click_to_tab_preserves_force_click_on_type_text(self):
        """When click_to_tab=True, TYPE_TEXT box with force_click=True retains its anchor click step."""
        layout = VisualFormLayout(
            name="Force Click Text",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
            boxes=[
                VisualBox(name="f1", geometry=BoxGeometry(x=10, y=10, width=50, height=20), navigation=NavigationAction.TAB),
                VisualBox(name="f2", geometry=BoxGeometry(x=10, y=50, width=50, height=20), force_click=True, navigation=NavigationAction.TAB),
                VisualBox(name="f3", geometry=BoxGeometry(x=10, y=90, width=50, height=20), force_click=False, navigation=NavigationAction.NONE),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        clicks = [s for s in wf.steps if s.action_type == ActionType.CLICK]
        # f1 is first field (always kept), f2 has force_click=True (kept), f3 is unforced after tab (pruned)
        assert len(clicks) == 2
        assert "f1" in clicks[0].label
        assert "f2" in clicks[1].label
        assert "[force_click]" in clicks[1].label
        assert clicks[1].parameters.variable_name == "__force_click__"
        assert getattr(clicks[1], "_force_click", False) is True

    def test_pass5_click_to_tab_preserves_force_click_on_click_checkbox_select(self):
        """When click_to_tab=True, CLICK, CHECKBOX, and SELECT boxes with force_click=True retain their clicks."""
        layout = VisualFormLayout(
            name="Force Click Non-Text",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
            boxes=[
                VisualBox(name="txt1", geometry=BoxGeometry(x=10, y=10, width=50, height=20), navigation=NavigationAction.TAB),
                VisualBox(name="btn_click", geometry=BoxGeometry(x=10, y=50, width=50, height=20), action_type=DesignerActionType.CLICK, force_click=True, navigation=NavigationAction.TAB),
                VisualBox(name="chk_agree", geometry=BoxGeometry(x=10, y=90, width=50, height=20), action_type=DesignerActionType.CHECKBOX, force_click=True, navigation=NavigationAction.TAB),
                VisualBox(name="sel_role", geometry=BoxGeometry(x=10, y=130, width=50, height=20), action_type=DesignerActionType.SELECT, force_click=True, navigation=NavigationAction.NONE),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        clicks = [s for s in wf.steps if s.action_type == ActionType.CLICK]
        assert len(clicks) == 4
        assert "txt1" in clicks[0].label
        assert "btn_click" in clicks[1].label
        assert "chk_agree" in clicks[2].label
        assert "sel_role" in clicks[3].label
        for c in clicks[1:]:
            assert "[force_click]" in c.label
            assert c.parameters.variable_name == "__force_click__"
            assert getattr(c, "_force_click", False) is True

    # --------------------------------------------------------------------------
    # 3. Standalone Action Clicks Preservation without force_click (Reviewer Finding 1)
    # --------------------------------------------------------------------------

    def test_pass5_click_to_tab_preserves_standalone_actions_without_force_click(self):
        """Standalone CLICK, CHECKBOX, and SELECT boxes following Tab MUST be preserved even with force_click=False."""
        layout = VisualFormLayout(
            name="Standalone Actions Preserved",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
            boxes=[
                VisualBox(name="input1", geometry=BoxGeometry(x=10, y=10, width=50, height=20), navigation=NavigationAction.TAB),
                # Standalone button, checkbox, and select - NOT redundant focus clicks, but primary interactions!
                VisualBox(name="btn1", geometry=BoxGeometry(x=10, y=50, width=50, height=20), action_type=DesignerActionType.CLICK, force_click=False, navigation=NavigationAction.TAB),
                VisualBox(name="chk1", geometry=BoxGeometry(x=10, y=90, width=50, height=20), action_type=DesignerActionType.CHECKBOX, force_click=False, navigation=NavigationAction.TAB),
                VisualBox(name="sel1", geometry=BoxGeometry(x=10, y=130, width=50, height=20), action_type=DesignerActionType.SELECT, force_click=False, navigation=NavigationAction.TAB),
                # Subsequent text box: its focus click SHOULD be pruned by click_to_tab
                VisualBox(name="input2", geometry=BoxGeometry(x=10, y=170, width=50, height=20), action_type=DesignerActionType.TYPE_TEXT, force_click=False, navigation=NavigationAction.NONE),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        clicks = [s for s in wf.steps if s.action_type == ActionType.CLICK]
        # input1 (kept: first field), btn1 (kept: action), chk1 (kept: action), sel1 (kept: action)
        # input2 click pruned (redundant text focus after tab)
        assert len(clicks) == 4
        assert "input1" in clicks[0].label
        assert "btn1" in clicks[1].label
        assert "chk1" in clicks[2].label
        assert "sel1" in clicks[3].label
        assert not any("input2" in c.label for c in clicks)

    # --------------------------------------------------------------------------
    # 4. KEY_PRESS Delay Parameter Inheritance (Reviewer Finding 2)
    # --------------------------------------------------------------------------

    def test_pass4_key_press_inherits_box_timing_delays(self):
        """KEY_PRESS action boxes inherit pre_delay_ms and post_delay_ms from box.timing."""
        layout = VisualFormLayout(
            name="Key Press Timing",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(
                    name="kp_enter",
                    geometry=BoxGeometry(x=10, y=10, width=50, height=20),
                    action_type=DesignerActionType.KEY_PRESS,
                    value="enter",
                    timing=BoxTiming(pre_delay_ms=250, post_delay_ms=450),
                )
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        kp_step = next(s for s in wf.steps if s.action_type == ActionType.KEY_PRESS)
        assert kp_step.pre_delay_ms == 250
        assert kp_step.post_delay_ms == 450
        assert kp_step.parameters.key == "enter"

    def test_pass4_key_press_inherits_execution_settings_default_delays(self):
        """KEY_PRESS action boxes without box.timing inherit layout execution_settings defaults."""
        layout = VisualFormLayout(
            name="Key Press Defaults",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            execution_settings=ExecutionSettingsSpec(default_step_delay_ms=180),
            boxes=[
                VisualBox(
                    name="kp_tab",
                    geometry=BoxGeometry(x=10, y=10, width=50, height=20),
                    action_type=DesignerActionType.KEY_PRESS,
                    value="tab",
                    post_delay_ms=0,
                )
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        kp_step = next(s for s in wf.steps if s.action_type == ActionType.KEY_PRESS)
        assert kp_step.pre_delay_ms == 0
        assert kp_step.post_delay_ms == 180

    def test_pass4_key_press_inherits_box_post_delay_ms_field(self):
        """KEY_PRESS action boxes inherit post_delay_ms from legacy box field when timing is None."""
        layout = VisualFormLayout(
            name="Key Press Legacy Timing",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(
                    name="kp_esc",
                    geometry=BoxGeometry(x=10, y=10, width=50, height=20),
                    action_type=DesignerActionType.KEY_PRESS,
                    value="escape",
                    post_delay_ms=320,
                )
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        kp_step = next(s for s in wf.steps if s.action_type == ActionType.KEY_PRESS)
        assert kp_step.post_delay_ms == 320

    # --------------------------------------------------------------------------
    # 5. Pre-Delay Preservation Under Click-to-Tab Pruning (Challenger Finding F2)
    # --------------------------------------------------------------------------

    def test_pass5_click_to_tab_preserves_pre_delay_when_click_pruned(self):
        """When click_to_tab prunes a redundant focus click, the field's pre_delay_ms settling time is not dropped."""
        layout = VisualFormLayout(
            name="Settling Pre-Delay Preserved",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
            boxes=[
                VisualBox(name="b1", geometry=BoxGeometry(x=10, y=10, width=50, height=20), navigation=NavigationAction.TAB),
                VisualBox(
                    name="b2",
                    geometry=BoxGeometry(x=10, y=50, width=50, height=20),
                    action_type=DesignerActionType.TYPE_TEXT,
                    timing=BoxTiming(pre_delay_ms=500),
                    clear_before=True,
                    navigation=NavigationAction.NONE,
                ),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        b2_steps = [s for s in wf.steps if "b2" in (s.label or "")]
        # Focus click for b2 was pruned
        assert not any(s.action_type == ActionType.CLICK for s in b2_steps)
        # Settling delay (500ms) is preserved either on the first subsequent step (CLEAR_FIELD) or a preceding DELAY
        total_b2_pre_delay = sum(s.pre_delay_ms for s in b2_steps) + sum(
            s.parameters.duration_ms or 0 for s in wf.steps if s.action_type == ActionType.DELAY and "500" in (s.label or "")
        )
        assert total_b2_pre_delay >= 500, "500ms settling pre_delay must not be dropped when click is pruned"

    def test_pass5_click_to_tab_preserves_pre_delay_with_clear_before_false(self):
        """When clear_before=False, pruned focus click's pre_delay_ms transfers directly to TYPE_TEXT step."""
        layout = VisualFormLayout(
            name="Pre-Delay without Clear",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
            boxes=[
                VisualBox(name="b1", geometry=BoxGeometry(x=10, y=10, width=50, height=20), navigation=NavigationAction.TAB),
                VisualBox(
                    name="b2",
                    geometry=BoxGeometry(x=10, y=50, width=50, height=20),
                    action_type=DesignerActionType.TYPE_TEXT,
                    timing=BoxTiming(pre_delay_ms=400),
                    clear_before=False,
                    navigation=NavigationAction.NONE,
                ),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        b2_steps = [s for s in wf.steps if "b2" in (s.label or "")]
        type_step = next(s for s in b2_steps if s.action_type == ActionType.TYPE_TEXT)
        assert type_step.pre_delay_ms >= 400

    # --------------------------------------------------------------------------
    # 6. Comprehensive Multi-Feature Integration & Engine Execution
    # --------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_full_regression_all_fixes_integrated(self, monkeypatch):
        """Full enterprise workflow integrating sequence indexing, force_click, action clicks, and delays."""
        monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")

        layout = VisualFormLayout(
            name="Comprehensive Enterprise Regression",
            canvas=CanvasDimensions(width=1000, height=800),
            target_application=TargetApplicationSpec(window_title_pattern="Enterprise Portal", process_name="app.exe"),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True, collapse_delays=True),
            boxes=[
                # Step 1: Text box with tab
                VisualBox(name="user_id", geometry=BoxGeometry(x=50, y=50, width=200, height=30), sequence_index=1, navigation=NavigationAction.TAB, value="user_123"),
                # Step 2: Custom KEY_PRESS with explicit timing
                VisualBox(name="nav_tab", geometry=BoxGeometry(x=50, y=90, width=100, height=20), sequence_index=2, action_type=DesignerActionType.KEY_PRESS, value="tab", timing=BoxTiming(pre_delay_ms=80, post_delay_ms=120)),
                # Step 3: Checkbox without force_click (must be preserved!)
                VisualBox(name="remember_me", geometry=BoxGeometry(x=50, y=120, width=30, height=30), sequence_index=3, action_type=DesignerActionType.CHECKBOX, navigation=NavigationAction.TAB),
                # Step 4: Text box with force_click=True
                VisualBox(name="otp_code", geometry=BoxGeometry(x=50, y=160, width=200, height=30), sequence_index=4, action_type=DesignerActionType.TYPE_TEXT, force_click=True, value="998877", navigation=NavigationAction.NONE),
                # Step 5: Submit button
                VisualBox(name="login_btn", geometry=BoxGeometry(x=50, y=210, width=120, height=35), sequence_index=5, action_type=DesignerActionType.SUBMIT),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)

        # 1. Verify sequence indices strictly contiguous 1..N
        indices = [s.sequence_index for s in wf.steps]
        assert indices == list(range(1, len(wf.steps) + 1))

        # 2. Verify preserved clicks
        click_steps = [s for s in wf.steps if s.action_type == ActionType.CLICK]
        assert any("user_id" in s.label for s in click_steps)
        assert any("remember_me" in s.label for s in click_steps)
        assert any("otp_code" in s.label for s in click_steps)

        # 3. Verify key press delays
        kp_step = next(s for s in wf.steps if s.action_type == ActionType.KEY_PRESS and "Key press" in s.label)
        assert kp_step.pre_delay_ms == 80
        assert kp_step.post_delay_ms == 120

        # 4. Verify async execution against MockWin32Driver
        driver = MockWin32Driver()
        driver.add_mock_window(1005, "Enterprise Portal", "app.exe")
        runner = WorkflowRunner(driver=driver)
        audit = await runner.execute(wf)
        assert audit.execution_summary.final_status == "SUCCESS"
        assert runner.state == ExecutionState.COMPLETED
        assert audit.execution_summary.total_steps == len(wf.steps)
        assert len(audit.step_events) == len(wf.steps)

