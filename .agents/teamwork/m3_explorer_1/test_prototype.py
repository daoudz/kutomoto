"""
Verification prototype for Milestone 3 Designer Schema.
Tests all Pydantic V2 models, validators, and serialization.
Copyrights reserved to 90Studio
"""
import sys
from pathlib import Path

# Add src to python path
src_dir = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(src_dir))

from enum import Enum
from typing import List, Optional, Dict, Any, Literal
import uuid
import pytest
from pydantic import BaseModel, Field, AliasChoices, model_validator, field_validator, ConfigDict, ValidationError

from kutomoto.engine.schema import (
    KutomotoWorkflow, TargetApplication, ExecutionSettings,
    DesignerMetadata, WorkflowStep, StepParameters, ActionType,
    SourceMode, TargetAppType, MatchMode, CoordinateMode, ClearStrategy, SubmitMethod
)

# ==============================================================================
# ENUMS
# ==============================================================================

class DesignerActionType(str, Enum):
    TYPE_TEXT = "type_text"
    CLICK = "click"
    SUBMIT = "submit"
    CHECKBOX = "checkbox"
    SELECT = "select"
    KEY_PRESS = "key_press"

class NavigationAction(str, Enum):
    TAB = "tab"
    ENTER = "enter"
    NONE = "none"
    CLICK_NEXT = "click_next"

class ValueSourceType(str, Enum):
    STATIC = "static"
    VARIABLE = "variable"
    GENERATED = "generated"
    RUNTIME_PROMPT = "runtime_prompt"

class GeneratorPattern(str, Enum):
    TIMESTAMP_ISO = "timestamp_iso"
    TIMESTAMP_COMPACT = "timestamp_compact"
    UUID4 = "uuid4"
    COUNTER_INCREMENT = "counter_increment"

class FieldType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    SELECT = "select"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    TEXTAREA = "textarea"
    SUBMIT_BUTTON = "submit_button"

class TraversalMode(str, Enum):
    COORDINATE_TARGETED = "coordinate_targeted"
    TAB_CHAINED = "tab_chained"
    HYBRID = "hybrid"

# ==============================================================================
# MODELS
# ==============================================================================

class CanvasDimensions(BaseModel):
    model_config = ConfigDict(extra="ignore")
    width: float = Field(..., gt=0, description="Canvas width in pixels (> 0)")
    height: float = Field(..., gt=0, description="Canvas height in pixels (> 0)")
    scale: float = Field(default=1.0, gt=0, description="Canvas display scale factor")
    background_image_path: Optional[str] = Field(default=None, description="Backdrop screenshot image path")

class BoxGeometry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    x: float = Field(..., ge=0, description="Top-left X coordinate in pixels")
    y: float = Field(..., ge=0, description="Top-left Y coordinate in pixels")
    width: float = Field(..., gt=0, description="Box width in pixels (> 0)")
    height: float = Field(..., gt=0, description="Box height in pixels (> 0)")

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center_x(self) -> float:
        return self.x + (self.width / 2.0)

    @property
    def center_y(self) -> float:
        return self.y + (self.height / 2.0)

class NormBounds(BaseModel):
    norm_x: float = Field(..., ge=0.0, le=1.0)
    norm_y: float = Field(..., ge=0.0, le=1.0)
    norm_w: float = Field(..., ge=0.0, le=1.0)
    norm_h: float = Field(..., ge=0.0, le=1.0)

class ValueConfig(BaseModel):
    source_type: ValueSourceType = Field(default=ValueSourceType.STATIC)
    static_value: Optional[str] = Field(default="")
    variable_name: Optional[str] = None
    generator_pattern: Optional[GeneratorPattern] = None
    is_secret: bool = Field(default=False)
    clear_before_type: bool = Field(default=True)

class BoxTiming(BaseModel):
    pre_delay_ms: Optional[int] = Field(default=None, ge=0)
    typing_speed_ms: Optional[int] = Field(default=None, ge=1, le=500)
    post_delay_ms: Optional[int] = Field(default=None, ge=0)

class VisualBox(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, description="Unique identifier / field name")
    label: Optional[str] = Field(default=None, description="Human-readable UI label")
    geometry: BoxGeometry = Field(..., validation_alias=AliasChoices("geometry", "rect"))
    sequence_index: int = Field(default=1, ge=1, description="Contiguous 1-based order")
    action_type: DesignerActionType = Field(default=DesignerActionType.TYPE_TEXT)
    value: str = Field(default="")
    navigation: NavigationAction = Field(default=NavigationAction.TAB)
    clear_before: bool = Field(default=True)
    post_delay_ms: int = Field(default=120, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Optional Section 7.2 models
    norm_bounds: Optional[NormBounds] = None
    value_config: Optional[ValueConfig] = None
    timing: Optional[BoxTiming] = None
    field_type: Optional[FieldType] = None

    @property
    def rect(self) -> BoxGeometry:
        return self.geometry

    @property
    def center_x(self) -> float:
        return self.geometry.center_x

    @property
    def center_y(self) -> float:
        return self.geometry.center_y

    @model_validator(mode="before")
    @classmethod
    def harmonize_box_input(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if not d.get("label") and d.get("name"):
            d["label"] = d["name"]
        if "action_type" not in d and "field_type" in d:
            ft = d["field_type"]
            if ft == "submit_button":
                d["action_type"] = DesignerActionType.SUBMIT
            elif ft == "checkbox":
                d["action_type"] = DesignerActionType.CHECKBOX
            elif ft == "select":
                d["action_type"] = DesignerActionType.SELECT
            else:
                d["action_type"] = DesignerActionType.TYPE_TEXT
        if "value" not in d and "value_config" in d:
            vc = d["value_config"]
            if isinstance(vc, dict):
                d["value"] = vc.get("static_value", "")
                if "clear_before_type" in vc and "clear_before" not in d:
                    d["clear_before"] = vc["clear_before_type"]
        if "timing" in d and isinstance(d["timing"], dict):
            if "post_delay_ms" in d["timing"] and "post_delay_ms" not in d:
                d["post_delay_ms"] = d["timing"]["post_delay_ms"]
        return d

class TargetApplicationSpec(TargetApplication):
    window_title_pattern: str = Field(
        ..., min_length=1, validation_alias=AliasChoices("window_title_pattern", "match_pattern")
    )

class ExecutionSettingsSpec(ExecutionSettings):
    default_step_delay_ms: int = Field(
        default=120, ge=10, le=10000, validation_alias=AliasChoices("default_step_delay_ms", "post_delay_ms")
    )

class PeepholeOptimizationConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = Field(default=True, description="Master toggle for peephole optimizations")
    band_tolerance_px: float = Field(default=12.0, ge=0.0, description="Spatial tolerance for 2D reading-order banding")
    click_to_tab: bool = Field(default=True, description="Convert clicks to Tab navigation in tab_chained traversal")
    collapse_delays: bool = Field(default=True, description="Coalesce consecutive delay steps")

class VisualFormLayout(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    schema_version: Literal["1.0.0"] = Field(default="1.0.0")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=1024)
    copyright: Literal["Copyrights reserved to 90Studio"] = Field(
        default="Copyrights reserved to 90Studio",
        description="Mandatory 90Studio copyright watermark",
    )
    canvas: CanvasDimensions
    target_application: TargetApplicationSpec = Field(
        ..., validation_alias=AliasChoices("target_application", "target")
    )
    execution_settings: ExecutionSettingsSpec = Field(
        default_factory=ExecutionSettingsSpec,
        validation_alias=AliasChoices("execution_settings", "global_timing"),
    )
    optimization: PeepholeOptimizationConfig = Field(default_factory=PeepholeOptimizationConfig)
    boxes: List[VisualBox] = Field(default_factory=list)
    variables: List[Dict[str, Any]] = Field(default_factory=list)

    @field_validator("copyright")
    @classmethod
    def validate_copyright(cls, v: str) -> str:
        if v != "Copyrights reserved to 90Studio":
            raise ValueError("Invalid copyright. Must be exactly 'Copyrights reserved to 90Studio'")
        return v

    @model_validator(mode="after")
    def validate_layout_integrity(self) -> "VisualFormLayout":
        cw = self.canvas.width
        ch = self.canvas.height
        box_ids = [b.id for b in self.boxes]
        if len(box_ids) != len(set(box_ids)):
            dups = [bid for bid in box_ids if box_ids.count(bid) > 1]
            raise ValueError(f"VisualFormLayout contains duplicate box IDs: {set(dups)}")
        for b in self.boxes:
            geom = b.geometry
            if geom.x < 0 or geom.y < 0:
                raise ValueError(f"Box '{b.id}' (name='{b.name}') has negative origin ({geom.x}, {geom.y})")
            if geom.right > cw + 1e-4:
                raise ValueError(
                    f"Box '{b.id}' (name='{b.name}') right edge ({geom.right:.2f}) exceeds canvas width ({cw:.2f})"
                )
            if geom.bottom > ch + 1e-4:
                raise ValueError(
                    f"Box '{b.id}' (name='{b.name}') bottom edge ({geom.bottom:.2f}) exceeds canvas height ({ch:.2f})"
                )
        return self

    def get_normalized_box(self, box: VisualBox) -> Dict[str, float]:
        cw = self.canvas.width
        ch = self.canvas.height
        geom = box.geometry
        norm_x = max(0.0, min(1.0, round(geom.x / cw, 4)))
        norm_y = max(0.0, min(1.0, round(geom.y / ch, 4)))
        norm_w = max(0.0, min(1.0 - norm_x, round(geom.width / cw, 4)))
        norm_h = max(0.0, min(1.0 - norm_y, round(geom.height / ch, 4)))
        center_norm_x = round(norm_x + (norm_w / 2.0), 4)
        center_norm_y = round(norm_y + (norm_h / 2.0), 4)
        return {
            "norm_x": norm_x,
            "norm_y": norm_y,
            "norm_w": norm_w,
            "norm_h": norm_h,
            "center_norm_x": center_norm_x,
            "center_norm_y": center_norm_y,
        }

# ==============================================================================
# TESTS
# ==============================================================================

def test_full_roundtrip():
    layout = VisualFormLayout(
        name="Retail KYC Form",
        canvas=CanvasDimensions(width=1920, height=1080),
        target_application=TargetApplicationSpec(match_pattern="Chrome.*KYC"),
        boxes=[
            VisualBox(
                name="customer_name",
                geometry=BoxGeometry(x=100, y=150, width=300, height=40),
                value="Eleanor Vance",
            ),
            VisualBox(
                name="submit_btn",
                geometry=BoxGeometry(x=100, y=250, width=120, height=40),
                action_type=DesignerActionType.SUBMIT,
            ),
        ]
    )
    assert len(layout.boxes) == 2
    assert layout.copyright == "Copyrights reserved to 90Studio"
    
    # Check normalized coordinates
    norm1 = layout.get_normalized_box(layout.boxes[0])
    assert 0.0 <= norm1["center_norm_x"] <= 1.0
    assert 0.0 <= norm1["center_norm_y"] <= 1.0

    # JSON roundtrip
    dump_str = layout.model_dump_json()
    restored = VisualFormLayout.model_validate_json(dump_str)
    assert restored.name == layout.name
    assert len(restored.boxes) == 2
    print("test_full_roundtrip passed!")

def test_boundary_violations():
    # Box exceeding canvas width
    try:
        VisualFormLayout(
            name="OutOfBounds",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(match_pattern="Win"),
            boxes=[
                VisualBox(
                    name="overflow_box",
                    geometry=BoxGeometry(x=700, y=100, width=150, height=40),
                )
            ]
        )
        assert False, "Should have failed out-of-bounds width"
    except ValidationError as e:
        assert "exceeds canvas width" in str(e)
    print("test_boundary_violations passed!")

def test_duplicate_box_ids():
    try:
        VisualFormLayout(
            name="DupIDs",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(match_pattern="Win"),
            boxes=[
                VisualBox(
                    id="fixed_id",
                    name="box1",
                    geometry=BoxGeometry(x=10, y=10, width=50, height=20),
                ),
                VisualBox(
                    id="fixed_id",
                    name="box2",
                    geometry=BoxGeometry(x=10, y=50, width=50, height=20),
                )
            ]
        )
        assert False, "Should have failed duplicate box IDs"
    except ValidationError as e:
        assert "duplicate box IDs" in str(e)
    print("test_duplicate_box_ids passed!")

def test_copyright_validation():
    try:
        VisualFormLayout.model_validate({
            "name": "CopyrightTest",
            "copyright": "Unauthorized Studio",
            "canvas": {"width": 800, "height": 600},
            "target": {"match_pattern": "Win"},
            "boxes": []
        })
        assert False, "Should have failed copyright check"
    except ValidationError as e:
        assert "Copyrights reserved to 90Studio" in str(e)
    print("test_copyright_validation passed!")

def test_section_7_2_compatibility():
    raw_dict = {
        "name": "Legacy 7.2 Form",
        "target": {
            "type": "web_browser",
            "window_title_pattern": "Legacy Portal"
        },
        "canvas": {
            "width": 1024,
            "height": 768
        },
        "global_timing": {
            "pre_delay_ms": 100,
            "typing_speed_ms": 25,
            "post_delay_ms": 150
        },
        "boxes": [
            {
                "id": "b1",
                "name": "user_id",
                "label": "User ID",
                "field_type": "text",
                "sequence_index": 1,
                "rect": {"x": 50, "y": 60, "width": 200, "height": 30},
                "value_config": {
                    "source_type": "static",
                    "static_value": "admin",
                    "clear_before_type": True
                },
                "navigation": "tab"
            },
            {
                "id": "b2",
                "name": "login_btn",
                "field_type": "submit_button",
                "sequence_index": 2,
                "rect": {"x": 50, "y": 120, "width": 100, "height": 40}
            }
        ]
    }
    layout = VisualFormLayout.model_validate(raw_dict)
    assert layout.name == "Legacy 7.2 Form"
    assert layout.execution_settings.default_step_delay_ms == 150
    assert layout.boxes[0].action_type == DesignerActionType.TYPE_TEXT
    assert layout.boxes[0].value == "admin"
    assert layout.boxes[0].clear_before is True
    assert layout.boxes[1].action_type == DesignerActionType.SUBMIT
    print("test_section_7_2_compatibility passed!")

def test_interface_with_kutomoto_workflow():
    layout = VisualFormLayout(
        name="Loan Origination Layout",
        canvas=CanvasDimensions(width=1280, height=800),
        target_application=TargetApplicationSpec(match_pattern="Underwriting.*Loan"),
        boxes=[
            VisualBox(
                name="borrower_name",
                geometry=BoxGeometry(x=100, y=100, width=300, height=36),
                sequence_index=1,
                action_type=DesignerActionType.TYPE_TEXT,
                value="Acme Corp",
                navigation=NavigationAction.TAB,
                clear_before=True
            ),
            VisualBox(
                name="submit_btn",
                geometry=BoxGeometry(x=100, y=200, width=150, height=40),
                sequence_index=2,
                action_type=DesignerActionType.SUBMIT,
                navigation=NavigationAction.NONE
            )
        ]
    )

    # Synthesize KutomotoWorkflow from VisualFormLayout
    steps: List[WorkflowStep] = []
    # 1. Focus step
    steps.append(
        WorkflowStep(
            sequence_index=1,
            label=f"Focus Window: {layout.target_application.window_title_pattern}",
            action_type=ActionType.FOCUS_WINDOW,
            parameters=StepParameters(
                window_title_pattern=layout.target_application.window_title_pattern,
                match_mode=layout.target_application.match_mode
            )
        )
    )

    # 2. Box steps
    for box in sorted(layout.boxes, key=lambda b: b.sequence_index):
        norm = layout.get_normalized_box(box)
        if box.action_type == DesignerActionType.TYPE_TEXT:
            steps.append(WorkflowStep(
                sequence_index=len(steps) + 1,
                label=f"Click [{box.name}]",
                action_type=ActionType.CLICK,
                parameters=StepParameters(
                    norm_x=norm["center_norm_x"],
                    norm_y=norm["center_norm_y"],
                    coordinate_mode=CoordinateMode.NORMALIZED
                )
            ))
            if box.clear_before:
                steps.append(WorkflowStep(
                    sequence_index=len(steps) + 1,
                    label=f"Clear [{box.name}]",
                    action_type=ActionType.CLEAR_FIELD,
                    parameters=StepParameters(clear_strategy=ClearStrategy.SELECT_ALL_BACKSPACE)
                ))
            steps.append(WorkflowStep(
                sequence_index=len(steps) + 1,
                label=f"Type into [{box.name}]",
                action_type=ActionType.TYPE_TEXT,
                parameters=StepParameters(
                    text=box.value,
                    keystroke_delay_ms=layout.execution_settings.typing_speed_ms
                )
            ))
            if box.navigation == NavigationAction.TAB:
                steps.append(WorkflowStep(
                    sequence_index=len(steps) + 1,
                    label=f"Tab after [{box.name}]",
                    action_type=ActionType.KEY_PRESS,
                    parameters=StepParameters(key="tab")
                ))
        elif box.action_type == DesignerActionType.SUBMIT:
            steps.append(WorkflowStep(
                sequence_index=len(steps) + 1,
                label=f"Submit via [{box.name}]",
                action_type=ActionType.SUBMIT,
                parameters=StepParameters(
                    submit_method=SubmitMethod.BUTTON_CLICK,
                    norm_x=norm["center_norm_x"],
                    norm_y=norm["center_norm_y"]
                )
            ))

    workflow = KutomotoWorkflow(
        name=layout.name,
        description=layout.description,
        source_mode=SourceMode.VISUAL_DESIGNER_GENERATED,
        target_application=layout.target_application,
        execution_settings=layout.execution_settings,
        designer_metadata=DesignerMetadata(
            canvas_width=layout.canvas.width,
            canvas_height=layout.canvas.height,
            box_count=len(layout.boxes)
        ),
        steps=steps
    )

    assert workflow.copyright == "Copyrights reserved to 90Studio"
    assert workflow.source_mode == SourceMode.VISUAL_DESIGNER_GENERATED
    assert workflow.designer_metadata.box_count == 2
    assert len(workflow.steps) == 6
    print("test_interface_with_kutomoto_workflow passed!")

if __name__ == "__main__":
    test_full_roundtrip()
    test_boundary_violations()
    test_duplicate_box_ids()
    test_copyright_validation()
    test_section_7_2_compatibility()
    test_interface_with_kutomoto_workflow()
    print("\nALL VERIFICATION PROTOCOL TESTS PASSED SUCCESSFULLY!")
