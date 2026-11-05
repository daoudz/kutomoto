# Milestone 3 Designer Schema Technical Analysis

```
====================================================================================================
Product Name       : kutomoto
Module             : Visual Form Designer Schema (src/kutomoto/designer/schema.py)
Copyright Notice   : Copyrights reserved to 90Studio
Author             : m3_explorer_1 (Milestone 3 Designer Schema Explorer)
Date               : 2026-11-05
Target Platform    : Python 3.14 + Pydantic V2 (x64 Windows 10/11)
Status             : COMPLETE / READY FOR IMPLEMENTATION
====================================================================================================
```

---

## 1. Executive Summary & Problem Boundary

The objective of Milestone 3 (`M3`) is to deliver the Visual Form Designer Box Model and its 5-pass compilation engine, transforming visual canvas interactions into deterministic, executable `KutomotoWorkflow` action pipelines.

This technical analysis defines the authoritative Pydantic V2 schema architecture for `src/kutomoto/designer/schema.py`. The design bridges:
1. **Interactive Canvas Operations**: Flexible user-drawn bounding boxes, 8-handle resizing, and post-action configurations (`docs/SPECIFICATION.md` Section 7.1).
2. **Formal Layout Contract**: Strict JSON Schema validation, positive dimension enforcement, unique box IDs, and mandatory 90Studio copyright attributions (`docs/SPECIFICATION.md` Section 7.2).
3. **Compiler Production Hardening Directives**: Non-zero canvas validation, boundary containment, normalized coordinate clamping `[0.0, 1.0]`, and tolerance for optional legacy draft elements (`docs/SPECIFICATION.md` Section 8.2).
4. **Clean Engine Interfacing**: Seamless 1:1 type compatibility and serialization parity with `KutomotoWorkflow` in `src/kutomoto/engine/schema.py`.

---

## 2. Key Architecture & Design Alignment

### 2.1 Alignment with `docs/SPECIFICATION.md`
- **Section 5.1 (Epic 1: US-VFD)**: Requires visual bounding boxes on an interactive canvas with sequence badges, positive dimensions, and geometric properties.
- **Section 5.3 (Epic 3: US-TRANS)**: Governs visual-to-workflow compilation, specifying dual-coordinate conversion from canvas pixels to normalized space ($0.0 \le \text{norm\_x}, \text{norm\_y} \le 1.0$).
- **Section 7.1 & 7.2**: Specifies formal JSON schema contracts for `VisualFormLayout` and `VisualBox` (including legacy aliases `rect`, `global_timing`, `target`).
- **Section 8.2**: Mandates 4 compiler production hardening directives:
  1. Coordinate boundary clamping `[0.0, 1.0]`.
  2. Strict non-zero canvas dimensions (`width > 0, height > 0`).
  3. Optionality for `norm_bounds` and `value_config` default factories.
  4. Submit button telemetry identifier fallback.

### 2.2 Alignment with `orchestrator/PROJECT.md`
- Defines the compiler input interface:
  ```json
  {
    "id": "string",
    "name": "string",
    "target": { "type": "window_title", "match_pattern": "string" },
    "canvas": { "width": 800, "height": 600 },
    "boxes": [
      {
        "id": "box_1",
        "name": "field_name",
        "rect": { "x": 100, "y": 150, "width": 200, "height": 36 },
        "sequence_index": 1,
        "action_type": "type_text",
        "value": "text to enter",
        "navigation": "tab",
        "clear_before": true
      }
    ]
  }
  ```
- Output interface: `KutomotoWorkflow` (Unified Action Schema Draft 2020-12).

### 2.3 Alignment with `src/kutomoto/engine/schema.py`
The designer models must cleanly integrate with the engine execution schemas:
- `TargetApplicationSpec` subclasses `TargetApplication`.
- `ExecutionSettingsSpec` subclasses `ExecutionSettings`.
- `VisualFormLayout.canvas` and `VisualFormLayout.boxes` directly populate `DesignerMetadata(canvas_width=..., canvas_height=..., box_count=...)`.
- `VisualFormLayout.copyright` and `KutomotoWorkflow.copyright` both enforce `"Copyrights reserved to 90Studio"`.

---

## 3. Detailed Pydantic V2 Model Catalog

### 3.1 Enumerations

| Enum Name | Members | Purpose |
|:---|:---|:---|
| `DesignerActionType` | `TYPE_TEXT = "type_text"`<br>`CLICK = "click"`<br>`SUBMIT = "submit"`<br>`CHECKBOX = "checkbox"`<br>`SELECT = "select"`<br>`KEY_PRESS = "key_press"` | High-level action types assignable to a visual designer box. |
| `NavigationAction` | `TAB = "tab"`<br>`ENTER = "enter"`<br>`NONE = "none"`<br>`CLICK_NEXT = "click_next"` | Post-step navigation trigger simulated after field input. |
| `ValueSourceType` | `STATIC = "static"`<br>`VARIABLE = "variable"`<br>`GENERATED = "generated"`<br>`RUNTIME_PROMPT = "runtime_prompt"` | Source strategy for field text values. |
| `GeneratorPattern` | `TIMESTAMP_ISO = "timestamp_iso"`<br>`TIMESTAMP_COMPACT = "timestamp_compact"`<br>`UUID4 = "uuid4"`<br>`COUNTER_INCREMENT = "counter_increment"` | Built-in value generators. |
| `FieldType` | `TEXT = "text"`<br>`NUMBER = "number"`<br>`DATE = "date"`<br>`SELECT = "select"`<br>`CHECKBOX = "checkbox"`<br>`RADIO = "radio"`<br>`TEXTAREA = "textarea"`<br>`SUBMIT_BUTTON = "submit_button"` | Backward compatibility with Section 7.2 formal schema. |
| `TraversalMode` | `COORDINATE_TARGETED = "coordinate_targeted"`<br>`TAB_CHAINED = "tab_chained"`<br>`HYBRID = "hybrid"` | Traversal optimization mode for compiler pass 3. |

---

### 3.2 `CanvasDimensions`
Represents the virtual drawing surface and backdrop screenshot geometry.

```python
class CanvasDimensions(BaseModel):
    model_config = ConfigDict(extra="ignore")
    width: float = Field(..., gt=0, description="Canvas width in pixels (> 0)")
    height: float = Field(..., gt=0, description="Canvas height in pixels (> 0)")
    scale: float = Field(default=1.0, gt=0, description="Canvas display scale factor")
    background_image_path: Optional[str] = Field(default=None, description="Backdrop screenshot image path")
```
- **Validation**: Enforces `width > 0` and `height > 0` using Pydantic V2 `gt=0`. This completely eliminates `ZeroDivisionError` during coordinate normalization.

---

### 3.3 `BoxGeometry`
Represents absolute pixel bounding rectangle on the canvas with dynamic geometric properties.

```python
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
```
- **Properties**:
  - `right`: $x + \text{width}$
  - `bottom`: $y + \text{height}$
  - `center_x`: $x + \frac{\text{width}}{2}$
  - `center_y`: $y + \frac{\text{height}}{2}$

---

### 3.4 `VisualBox`
The primary atomic input element of the visual designer.

```python
class VisualBox(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique box UUID")
    name: str = Field(..., min_length=1, description="Identifier / field token")
    label: Optional[str] = Field(default=None, description="Human-readable UI label")
    geometry: BoxGeometry = Field(
        ...,
        validation_alias=AliasChoices("geometry", "rect"),
        description="Bounding box pixel geometry"
    )
    sequence_index: int = Field(default=1, ge=1, description="Contiguous execution sequence rank")
    action_type: DesignerActionType = Field(default=DesignerActionType.TYPE_TEXT)
    value: str = Field(default="", description="Text payload or static string")
    navigation: NavigationAction = Field(default=NavigationAction.TAB)
    clear_before: bool = Field(default=True, description="Clear field before typing")
    post_delay_ms: int = Field(default=120, ge=0, description="Settling delay after step in ms")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom extension metadata")

    # Optional Section 7.2 Compatibility Attributes
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
```

---

### 3.5 `TargetApplicationSpec`
Derived directly from `src.kutomoto.engine.schema.TargetApplication` to ensure 100% type compatibility while supporting `match_pattern` alias.

```python
class TargetApplicationSpec(TargetApplication):
    window_title_pattern: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("window_title_pattern", "match_pattern"),
        description="Regex or substring matching target window title"
    )
```

---

### 3.6 `ExecutionSettingsSpec`
Derived directly from `src.kutomoto.engine.schema.ExecutionSettings` with alias support for `post_delay_ms` / `global_timing`.

```python
class ExecutionSettingsSpec(ExecutionSettings):
    default_step_delay_ms: int = Field(
        default=120,
        ge=10,
        le=10000,
        validation_alias=AliasChoices("default_step_delay_ms", "post_delay_ms"),
        description="Default inter-step settling delay in ms"
    )
```

---

### 3.7 `PeepholeOptimizationConfig`
Compiler pass control configuration.

```python
class PeepholeOptimizationConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = Field(default=True, description="Master toggle for compiler peephole optimizations")
    band_tolerance_px: float = Field(default=12.0, ge=0.0, description="Spatial tolerance in pixels for 2D reading-order banding")
    click_to_tab: bool = Field(default=True, description="Convert consecutive clicks on adjacent inputs to Tab navigation")
    collapse_delays: bool = Field(default=True, description="Coalesce consecutive delay steps into a single delay step")
```

---

### 3.8 `VisualFormLayout`
The root document model for visual forms.

```python
class VisualFormLayout(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    schema_version: Literal["1.0.0"] = Field(default="1.0.0", description="Schema version")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Layout UUID")
    name: str = Field(..., min_length=1, max_length=128, description="Layout name")
    description: Optional[str] = Field(default=None, max_length=1024, description="Layout description")
    copyright: Literal["Copyrights reserved to 90Studio"] = Field(
        default="Copyrights reserved to 90Studio",
        description="Mandatory 90Studio copyright watermark",
    )
    canvas: CanvasDimensions = Field(..., description="Canvas surface bounds")
    target_application: TargetApplicationSpec = Field(
        ...,
        validation_alias=AliasChoices("target_application", "target"),
        description="Target application descriptor"
    )
    execution_settings: ExecutionSettingsSpec = Field(
        default_factory=ExecutionSettingsSpec,
        validation_alias=AliasChoices("execution_settings", "global_timing"),
        description="Timing and recovery configuration"
    )
    optimization: PeepholeOptimizationConfig = Field(
        default_factory=PeepholeOptimizationConfig,
        description="Peephole optimization rules"
    )
    boxes: List[VisualBox] = Field(default_factory=list, description="Visual boxes drawn on canvas")
    variables: List[Dict[str, Any]] = Field(default_factory=list, description="Optional workflow variables")

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
                    f"Box '{b.id}' (name='{b.name}') right edge ({geom.right:.2f}) exceeds canvas width ({cw:.2f})"
                )
            if geom.bottom > ch + 1e-4:
                raise ValueError(
                    f"Box '{b.id}' (name='{b.name}') bottom edge ({geom.bottom:.2f}) exceeds canvas height ({ch:.2f})"
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
```

---

## 4. Key Validators & Error Handling Directives

| Constraint | Validation Type | Failure Trigger | Error Response |
|:---|:---|:---|:---|
| **Canvas Dimensions** | Field validator (`gt=0`) | `width <= 0` or `height <= 0` | `ValidationError: Input should be greater than 0` |
| **Box Geometry Dimensions** | Field validator (`gt=0`) | `width <= 0` or `height <= 0` | `ValidationError: Input should be greater than 0` |
| **Box Origin Coordinates** | Field validator (`ge=0`) | `x < 0` or `y < 0` | `ValidationError: Input should be greater than or equal to 0` |
| **Boundary Containment** | Model validator (`mode="after"`) | `x + width > canvas.width` or `y + height > canvas.height` | `ValueError: Box '<id>' right/bottom edge exceeds canvas width/height` |
| **Unique Box IDs** | Model validator (`mode="after"`) | Duplicate ID in `boxes` list | `ValueError: VisualFormLayout contains duplicate box IDs: {...}` |
| **90Studio Copyright** | Field validator + Literal | Value $\ne$ `"Copyrights reserved to 90Studio"` | `ValueError: Invalid copyright. Must be exactly 'Copyrights reserved to 90Studio'` |

---

## 5. Clean Interfacing with `KutomotoWorkflow` (`src/kutomoto/engine/schema.py`)

When the 5-pass compiler transforms `VisualFormLayout` into `KutomotoWorkflow`:
1. **Target Application Pass-Through**: `layout.target_application` is an instance of `TargetApplicationSpec` (which inherits directly from `TargetApplication`). It can be assigned directly to `KutomotoWorkflow.target_application`.
2. **Execution Settings Pass-Through**: `layout.execution_settings` is an instance of `ExecutionSettingsSpec` (which inherits from `ExecutionSettings`). It is directly compatible with `KutomotoWorkflow.execution_settings`.
3. **Canvas Metadata Sync**:
   `KutomotoWorkflow.designer_metadata` is instantiated directly from layout attributes:
   ```python
   DesignerMetadata(
       canvas_width=layout.canvas.width,
       canvas_height=layout.canvas.height,
       background_image_path=layout.canvas.background_image_path,
       box_count=len(layout.boxes),
   )
   ```
4. **Coordinate Mapping to Action Steps**:
   - `norm = layout.get_normalized_box(box)`
   - Clicks and button submits use `StepParameters(norm_x=norm["center_norm_x"], norm_y=norm["center_norm_y"], coordinate_mode=CoordinateMode.NORMALIZED)`.
   - Clamping guarantees values strictly within `[0.0, 1.0]`, passing `KutomotoWorkflow`'s Pydantic V2 bounds validator without exception.
5. **Source Mode Tracking**:
   `KutomotoWorkflow.source_mode` is automatically set to `SourceMode.VISUAL_DESIGNER_GENERATED`.

---

## 6. Verification and Empirical Testing

A complete standalone test harness was created in `.agents/teamwork/m3_explorer_1/test_prototype.py` and executed against Python 3.14 + Pydantic V2.

### Test Matrix Results
1. `test_full_roundtrip`: Passed (JSON serialization / deserialization roundtrip preserves 100% data integrity).
2. `test_boundary_violations`: Passed (Catches out-of-bounds boxes exceeding canvas width or height).
3. `test_duplicate_box_ids`: Passed (Catches duplicate box IDs across layout).
4. `test_copyright_validation`: Passed (Rejects any missing or altered copyright string).
5. `test_section_7_2_compatibility`: Passed (Parses Section 7.2 format with `rect`, `field_type`, `value_config`, and `timing`).
6. `test_interface_with_kutomoto_workflow`: Passed (Generates a fully valid `KutomotoWorkflow` matching `src/kutomoto/engine/schema.py` requirements).

Result: **6 passed in 0.07s**. Zero regressions.
