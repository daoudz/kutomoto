"""
kutomoto.designer.schema
Pydantic V2 Schema Models for Visual Form Designer.
Copyrights reserved to 90Studio
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
import uuid

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from kutomoto.engine.schema import ExecutionSettings, TargetApplication


# ==============================================================================
# 1. ENUMERATIONS
# ==============================================================================

class DesignerActionType(str, Enum):
    TYPE_TEXT = "type_text"
    CLICK = "click"
    SUBMIT = "submit"
    CHECKBOX = "checkbox"
    SELECT = "select"
    KEY_PRESS = "key_press"
    DELAY = "delay"


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
# 2. GEOMETRY & ATOMIC BOX MODELS
# ==============================================================================

class CanvasDimensions(BaseModel):
    model_config = ConfigDict(extra="ignore")

    width: float = Field(..., gt=0, description="Canvas width in pixels (> 0)")
    height: float = Field(..., gt=0, description="Canvas height in pixels (> 0)")
    scale: float = Field(default=1.0, gt=0, description="Canvas display scale factor")
    background_image_path: Optional[str] = Field(
        default=None, description="Backdrop screenshot image path"
    )


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
    model_config = ConfigDict(extra="ignore")

    norm_x: float = Field(..., ge=0.0, le=1.0)
    norm_y: float = Field(..., ge=0.0, le=1.0)
    norm_w: float = Field(..., ge=0.0, le=1.0)
    norm_h: float = Field(..., ge=0.0, le=1.0)


class ValueConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_type: ValueSourceType = Field(default=ValueSourceType.STATIC)
    static_value: Optional[str] = Field(default="")
    variable_name: Optional[str] = None
    generator_pattern: Optional[GeneratorPattern] = None
    is_secret: bool = Field(default=False)
    clear_before_type: bool = Field(default=True)


class BoxTiming(BaseModel):
    model_config = ConfigDict(extra="ignore")

    pre_delay_ms: Optional[int] = Field(default=None, ge=0)
    typing_speed_ms: Optional[int] = Field(default=None, ge=1, le=500)
    post_delay_ms: Optional[int] = Field(default=None, ge=0)


class VisualBox(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique box UUID")
    name: str = Field(..., min_length=1, description="Identifier / field name token")
    label: Optional[str] = Field(default=None, description="Human-readable UI label")
    geometry: BoxGeometry = Field(
        ...,
        validation_alias=AliasChoices("geometry", "rect"),
        description="Bounding box pixel geometry",
    )
    sequence_index: Optional[int] = Field(
        default=None,
        ge=1,
        description="Explicit execution sequence rank (1-based, or None for spatial ordering)",
    )
    action_type: DesignerActionType = Field(default=DesignerActionType.TYPE_TEXT)
    value: str = Field(default="", description="Text payload or static string")
    navigation: NavigationAction = Field(default=NavigationAction.TAB)
    clear_before: bool = Field(default=True, description="Clear field before typing text")
    post_delay_ms: int = Field(default=120, ge=0, description="Settling delay after step in ms")
    force_click: bool = Field(
        default=False, description="Force physical coordinate click even in tab_chained traversal"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom extension metadata")

    # Optional Section 7.2 compatibility models
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
                if "is_secret" in vc:
                    d.setdefault("metadata", {})["is_secret"] = vc["is_secret"]
        if "timing" in d and isinstance(d["timing"], dict):
            if "post_delay_ms" in d["timing"] and "post_delay_ms" not in d:
                d["post_delay_ms"] = d["timing"]["post_delay_ms"]
        return d


# ==============================================================================
# 3. TARGET, SETTINGS, OPTIMIZATION SPECS
# ==============================================================================

class TargetApplicationSpec(TargetApplication):
    window_title_pattern: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("window_title_pattern", "match_pattern"),
        description="Regex or substring matching target window title",
    )


class ExecutionSettingsSpec(ExecutionSettings):
    default_step_delay_ms: int = Field(
        default=120,
        ge=10,
        le=10000,
        validation_alias=AliasChoices("default_step_delay_ms", "post_delay_ms"),
        description="Default inter-step settling delay in ms",
    )


class PeepholeOptimizationConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(
        default=True, description="Master toggle for compiler peephole optimizations"
    )
    band_tolerance_px: float = Field(
        default=24.0,
        ge=0.0,
        le=500.0,
        description="Spatial tolerance in pixels for 2D reading-order banding",
    )
    click_to_tab: bool = Field(
        default=False,
        description="Convert redundant coordinate clicks following Tab navigation into keyboard flow",
    )
    collapse_delays: bool = Field(
        default=True,
        description="Coalesce consecutive delay steps into a single consolidated delay",
    )
    remove_redundant_focus: bool = Field(
        default=True,
        description="Prune consecutive duplicate focus_window actions targeting the same window",
    )
    prune_empty_delays: bool = Field(
        default=True, description="Discard delay steps with duration_ms == 0"
    )


# ==============================================================================
# 4. ROOT VISUAL FORM LAYOUT
# ==============================================================================

class VisualFormLayout(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    schema_version: Literal["1.0.0"] = Field(default="1.0.0", description="Schema version")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Layout UUID")
    name: str = Field(..., min_length=1, max_length=128, description="Layout name")
    description: Optional[str] = Field(
        default=None, max_length=1024, description="Layout description"
    )
    copyright: Literal["Copyrights reserved to 90Studio"] = Field(
        default="Copyrights reserved to 90Studio",
        description="Mandatory 90Studio copyright watermark",
    )
    canvas: CanvasDimensions = Field(..., description="Canvas surface bounds")
    target_application: TargetApplicationSpec = Field(
        ...,
        validation_alias=AliasChoices("target_application", "target"),
        description="Target application descriptor",
    )
    execution_settings: ExecutionSettingsSpec = Field(
        default_factory=ExecutionSettingsSpec,
        validation_alias=AliasChoices("execution_settings", "global_timing"),
        description="Timing and recovery configuration",
    )
    optimization: PeepholeOptimizationConfig = Field(
        default_factory=PeepholeOptimizationConfig,
        description="Peephole optimization rules",
    )
    boxes: List[VisualBox] = Field(
        ..., min_length=1, description="Visual boxes drawn on canvas (at least 1 required)"
    )
    variables: List[Dict[str, Any]] = Field(
        default_factory=list, description="Optional workflow variables"
    )

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

        # 1. Unique Box IDs
        box_ids = [b.id for b in self.boxes]
        if len(box_ids) != len(set(box_ids)):
            dups = [bid for bid in box_ids if box_ids.count(bid) > 1]
            raise ValueError(f"VisualFormLayout contains duplicate box IDs: {set(dups)}")

        # 2. Strict Boundary Checks
        for b in self.boxes:
            geom = b.geometry
            if geom.x < 0 or geom.y < 0:
                raise ValueError(
                    f"Box '{b.id}' (name='{b.name}') has negative origin ({geom.x}, {geom.y})"
                )
            if geom.right > cw + 1e-4:
                raise ValueError(
                    f"Box '{b.id}' (name='{b.name}') right edge ({geom.right:.2f}) "
                    f"exceeds canvas width ({cw:.2f})"
                )
            if geom.bottom > ch + 1e-4:
                raise ValueError(
                    f"Box '{b.id}' (name='{b.name}') bottom edge ({geom.bottom:.2f}) "
                    f"exceeds canvas height ({ch:.2f})"
                )

        return self

    def get_normalized_box(self, box: VisualBox) -> Dict[str, float]:
        """
        Computes normalized coordinates and center points clamped to [0.0, 1.0].
        Enforces Hardening Directive 1 (Section 8.2).
        """
        cw = self.canvas.width
        ch = self.canvas.height
        geom = box.geometry
        norm_x = max(0.0, min(1.0, round(geom.x / cw, 4)))
        norm_y = max(0.0, min(1.0, round(geom.y / ch, 4)))
        norm_w = max(0.0, min(1.0 - norm_x, round(geom.width / cw, 4)))
        norm_h = max(0.0, min(1.0 - norm_y, round(geom.height / ch, 4)))
        center_norm_x = max(
            0.0, min(1.0, round((geom.x + (geom.width / 2.0)) / cw, 4))
        )
        center_norm_y = max(
            0.0, min(1.0, round((geom.y + (geom.height / 2.0)) / ch, 4))
        )
        return {
            "norm_x": norm_x,
            "norm_y": norm_y,
            "norm_w": norm_w,
            "norm_h": norm_h,
            "center_norm_x": center_norm_x,
            "center_norm_y": center_norm_y,
        }
