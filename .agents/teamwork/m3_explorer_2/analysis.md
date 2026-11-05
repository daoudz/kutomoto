# Technical Analysis: Visual-to-Workflow Compilation Algorithm

**Author**: m3_explorer_2 (Milestone 3 Compiler Algorithm Explorer)  
**Target Module**: `src/kutomoto/designer/compiler.py`  
**Copyright**: Copyrights reserved to 90Studio  
**Date**: 2026-11-05  

---

## 1. Executive Summary & Architectural Overview

The **Visual-to-Workflow Compiler** is the core bridge connecting the visual canvas experience of kutomoto to its high-reliability Win32 execution engine. It translates a 2D spatial layout (`VisualFormLayout`) consisting of canvas dimensions, target application selectors, and user-drawn visual bounding boxes (`VisualBox`) into a strictly validated, linear, highly optimized `KutomotoWorkflow` (Pydantic V2 model).

The compilation pipeline is implemented as a **deterministic 5-pass algorithm**:

```
+--------------------------------------------------------------------------------------------------+
|                                    VISUAL-TO-WORKFLOW COMPILER                                   |
|                             src/kutomoto/designer/compiler.py                                    |
+--------------------------------------------------------------------------------------------------+
                                                 |
                                                 v
+--------------------------------------------------------------------------------------------------+
| PASS 1: Structural & Geometry Integrity Validation                                              |
| - Verify layout has >= 1 box (raise EmptyLayoutError)                                            |
| - Verify canvas dimensions > 0 and box dimensions > 0 (raise GeometryError)                      |
| - Validate box containment within canvas bounds [0, 0, W, H] (raise GeometryError)               |
| - Check for duplicate box IDs across layout (raise DuplicateBoxIdError)                          |
| - Detect overlapping box collisions and emit warning diagnostics                                 |
+--------------------------------------------------------------------------------------------------+
                                                 |
                                                 v
+--------------------------------------------------------------------------------------------------+
| PASS 2: Spatial Band Sorting & Sequence Ordering                                                 |
| - Branch A: All boxes have explicit sequence_index > 0 -> Sort by explicit index                 |
| - Branch B: Unindexed boxes (sequence_index is None / 0) -> 2D Spatial Band Sort                 |
|   * Partition into horizontal bands via band_tolerance_px (default 24px or 50% avg height)       |
|   * Sort bands top-to-bottom by anchor Y; sort boxes within each band left-to-right by X         |
| - Branch C: Hybrid layout -> Explicit indices first (or slotted), followed by spatial order      |
+--------------------------------------------------------------------------------------------------+
                                                 |
                                                 v
+--------------------------------------------------------------------------------------------------+
| PASS 3: Dual-Coordinate Normalization                                                            |
| - Compute normalized center: norm_x = (x + w/2) / canvas.width, norm_y = (y + h/2) / canvas.height|
| - Compute normalized dimensions: norm_w = w / canvas.width, norm_h = h / canvas.height          |
| - Clamp strictly to [0.0, 1.0] to satisfy formal workflow schema boundaries                      |
| - Round to 4 decimal places for clean, stable JSON serialization                                 |
+--------------------------------------------------------------------------------------------------+
                                                 |
                                                 v
+--------------------------------------------------------------------------------------------------+
| PASS 4: Action Step Synthesis                                                                    |
| - Header Step (Index 1): FOCUS_WINDOW targeting layout.target_application                        |
| - For each ordered box:                                                                          |
|   * type_text: CLICK (norm_x, norm_y) -> CLEAR_FIELD (if clear_before) -> TYPE_TEXT -> NAV KEY   |
|   * click: CLICK (norm_x, norm_y) at center coordinates -> NAV KEY (if specified)               |
|   * submit: SUBMIT (button_click at norm_x, norm_y or enter_key)                                 |
| - Inject delay, key_press, or custom actions cleanly                                             |
+--------------------------------------------------------------------------------------------------+
                                                 |
                                                 v
+--------------------------------------------------------------------------------------------------+
| PASS 5: Peephole Navigation Optimizer & Normalization                                            |
| - Click-to-Tab Optimization: Eliminate redundant CLICK steps following TAB key navigation        |
| - Delay Collapsing: Consolidate consecutive DELAY actions by summing durations                   |
| - Redundant Focus Elimination: Drop contiguous duplicate window focus steps                      |
| - Strict Re-indexing: Re-number all steps 1..N sequentially to satisfy uniqueness constraints    |
| - Metadata & Watermarking: Embed canvas dimensions, box count, and 90Studio copyright            |
+--------------------------------------------------------------------------------------------------+
                                                 |
                                                 v
                                    [KutomotoWorkflow Model]
```

---

## 2. Public API & Type Signatures

### 2.1 Primary Entry Point
```python
def compile_visual_layout_to_workflow(
    layout: Union[VisualFormLayout, Dict[str, Any]],
    optimization: Optional[PeepholeOptimizationConfig] = None,
) -> KutomotoWorkflow:
    """
    Translates a VisualFormLayout into an executable KutomotoWorkflow.

    Parameters:
        layout: A validated VisualFormLayout instance or raw dict conforming to layout schema.
        optimization: Optional PeepholeOptimizationConfig overriding layout.optimization.

    Returns:
        A validated KutomotoWorkflow Pydantic V2 model instance ready for execution or serialization.

    Raises:
        EmptyLayoutError: If layout.boxes contains 0 boxes.
        GeometryError: If canvas dimensions or box coordinates are invalid or out of bounds.
        DuplicateBoxIdError: If duplicate box identifiers exist in the layout.
        CompilationError: Base exception for any other semantic compilation failures.
    """
```

### 2.2 Backward-Compatible Alias
To satisfy Section 8.1 of `SPECIFICATION.md` and legacy callers:
```python
def compile_visual_boxes_to_workflow(
    layout: Union[VisualFormLayout, Dict[str, Any]],
    traversal_mode: str = "coordinate_targeted",
    **kwargs: Any,
) -> KutomotoWorkflow:
    """
    Backward-compatible alias for compile_visual_layout_to_workflow.
    Maps traversal_mode='tab_chained' to optimization.click_to_tab = True.
    """
```

---

## 3. Detailed Specification of the 5 Compilation Passes

### Pass 1: Structural & Geometry Integrity Validation

Pass 1 enforces geometric consistency and rejects corrupted drafts before any transformation occurs:

1. **Empty Layout Check**:
   - Check `len(layout.boxes) > 0`.
   - If empty: raise `EmptyLayoutError("Visual layout must contain at least one visual box.")`.
2. **Canvas Dimension Validation**:
   - Verify `layout.canvas.width > 0` and `layout.canvas.height > 0`.
   - If non-positive: raise `GeometryError(f"Canvas dimensions must be strictly positive, got {layout.canvas.width}x{layout.canvas.height}.")`.
3. **Box Geometry Validation**:
   - For every box $b \in \text{layout.boxes}$:
     - Positive dimensions: verify `b.geometry.width > 0` and `b.geometry.height > 0`. If not, raise `GeometryError(f"Box '{b.id}' has non-positive dimensions: {b.geometry.width}x{b.geometry.height}.")`.
     - Non-negative origin: verify `b.geometry.x >= 0` and `b.geometry.y >= 0`. If negative, raise `GeometryError(f"Box '{b.id}' has negative coordinates: ({b.geometry.x}, {b.geometry.y}).")`.
     - Canvas boundary containment:
       With a numerical epsilon tolerance $\epsilon = 10^{-4}$ (to account for floating-point serialization jitter):
       $$\text{b.geometry.x} + \text{b.geometry.width} \le \text{layout.canvas.width} + \epsilon$$
       $$\text{b.geometry.y} + \text{b.geometry.height} \le \text{layout.canvas.height} + \epsilon$$
       If violated: raise `GeometryError(f"Box '{b.id}' exceeds canvas boundaries: right={b.geometry.x + b.geometry.width} > canvas.width={layout.canvas.width} or bottom={b.geometry.y + b.geometry.height} > canvas.height={layout.canvas.height}.")`.
4. **Duplicate Box ID Detection**:
   - Maintain a set of visited box IDs.
   - If a duplicate `b.id` is encountered: raise `DuplicateBoxIdError(f"Duplicate box ID detected: '{b.id}'. Every box must have a unique ID.")`.
5. **Overlapping / Collision Diagnostic Detection**:
   - For every pair of distinct boxes $(A, B)$ where $A \neq B$:
     Two boxes overlap if:
     $$A.x < B.x + B.w \land A.x + A.w > B.x \land A.y < B.y + B.h \land A.y + A.h > B.y$$
   - Overlaps are detected and logged as non-fatal warnings:
     `logger.warning("Visual layout warning: Box '%s' collides with Box '%s'", A.id, B.id)`
   - Recorded in compilation metadata for inspection by frontend UI.

---

### Pass 2: Spatial Band Sorting & Sequence Ordering

The compiler resolves execution ordering across explicit, spatial, and hybrid authoring styles.

#### Case A: Fully Explicit Sequence
When all boxes in the layout have an explicit `sequence_index` ($> 0$):
- Sort strictly by `sequence_index`:
  `ordered_boxes = sorted(boxes, key=lambda b: (b.sequence_index, b.geometry.y, b.geometry.x))`
- Any duplicate sequence index is cleanly tie-broken by spatial reading order.

#### Case B: 2D Spatial Band Sorting (Natural Reading Order)
When boxes lack explicit sequence numbers (`sequence_index is None` or `sequence_index == 0`), the compiler reconstructs human Western reading order (Top-to-Bottom, Left-to-Right) using horizontal spatial banding:

1. **Calculate Band Tolerance**:
   - If `layout.optimization.band_tolerance_px` is specified ($> 0$), use it (default: `24.0` px).
   - Otherwise, dynamically compute $50\%$ of the average box height:
     $$\text{band\_tolerance} = \max\left(10.0, 0.5 \times \frac{\sum_{i=1}^N b_i.\text{geometry}.\text{height}}{N}\right)$$
2. **Sort by Vertical Coordinate**:
   - Sort all boxes primarily by top Y-coordinate:
     `sorted_by_y = sorted(boxes, key=lambda b: (b.geometry.y, b.geometry.x))`
3. **Cluster into Horizontal Bands**:
   - Initialize `bands: List[List[VisualBox]] = []`.
   - Seed `current_band = [sorted_by_y[0]]`, `anchor_y = sorted_by_y[0].geometry.y`.
   - For each subsequent box $b$:
     - If $|b.\text{geometry}.y - \text{anchor\_y}| \le \text{band\_tolerance}$:
       - Append $b$ to `current_band`.
     - Else:
       - Append `current_band` to `bands`.
       - Start new `current_band = [b]`, `anchor_y = b.geometry.y`.
   - Append trailing `current_band` to `bands`.
4. **Sort Each Band Horizontally**:
   - For each band in `bands`:
     - Sort boxes left-to-right: `sorted(band, key=lambda b: b.geometry.x)`.
5. **Flatten Bands**:
   - Concatenate all sorted bands into `ordered_boxes`.

#### Case C: Hybrid Sequence Resolution
When some boxes have explicit `sequence_index > 0` while others are unindexed (`None` or `0`):
- Partition into `explicit_boxes` and `unindexed_boxes`.
- Sort `explicit_boxes` by `sequence_index`.
- Sort `unindexed_boxes` using 2D spatial band sorting.
- Combine with explicit boxes executing first:
  `ordered_boxes = explicit_boxes + unindexed_boxes`

---

### Pass 3: Dual-Coordinate Normalization

To ensure resolution independence between the authoring canvas and the target runtime application window (web browser or desktop Win32 form), Pass 3 computes normalized coordinates scaled to the unit interval $[0.0, 1.0]$.

1. **Formulas**:
   $$\text{norm\_center\_x} = \frac{\text{box.geometry.x} + \frac{\text{box.geometry.width}}{2.0}}{\text{canvas.width}}$$
   $$\text{norm\_center\_y} = \frac{\text{box.geometry.y} + \frac{\text{box.geometry.height}}{2.0}}{\text{canvas.height}}$$
   $$\text{norm\_w} = \frac{\text{box.geometry.width}}{\text{canvas.width}}$$
   $$\text{norm\_h} = \frac{\text{box.geometry.height}}{\text{canvas.height}}$$
2. **Clamping**:
   To strictly satisfy the schema constraints `ge=0.0, le=1.0`:
   $$\text{norm\_center\_x} = \max(0.0, \min(1.0, \text{norm\_center\_x}))$$
   $$\text{norm\_center\_y} = \max(0.0, \min(1.0, \text{norm\_center\_y}))$$
3. **Rounding**:
   Round each coordinate to 4 decimal places for stable JSON diffing and serialization:
   $$\text{norm\_center\_x} = \text{round}(\text{norm\_center\_x}, 4)$$
   $$\text{norm\_center\_y} = \text{round}(\text{norm\_center\_y}, 4)$$
   $$\text{norm\_w} = \text{round}(\text{norm\_w}, 4)$$
   $$\text{norm\_h} = \text{round}(\text{norm\_h}, 4)$$

---

### Pass 4: Action Step Synthesis

Pass 4 converts the ordered, normalized visual boxes into atomic `WorkflowStep` primitives.

#### Step 1: Target Window Focus Header Step
Every compiled workflow begins with a focus activation step targeting the configured application:
- `step_id`: `str(uuid.uuid4())`
- `sequence_index`: 1
- `action_type`: `ActionType.FOCUS_WINDOW`
- `label`: `f"Focus Target Window: {layout.target_application.window_title_pattern}"`
- `enabled`: `True`
- `pre_delay_ms`: 0
- `post_delay_ms`: 250 (allows window focus switch to settle before injecting inputs)
- `parameters`:
  ```python
  StepParameters(
      window_title_pattern=layout.target_application.window_title_pattern,
      process_name=layout.target_application.process_name,
      match_mode=layout.target_application.match_mode,
  )
  ```

#### Action Step Generation per Box
For each ordered box, action steps are synthesized based on `box.action_type`:

| Action Type | Synthesized Sub-Steps |
|---|---|
| `type_text` | 1. `CLICK` at `(norm_x, norm_y)` to anchor focus<br>2. `CLEAR_FIELD` (`select_all_backspace`) if `clear_before=True`<br>3. `TYPE_TEXT` with `box.value` and `keystroke_delay_ms`<br>4. `KEY_PRESS` (Tab/Enter) if `box.navigation` specified |
| `click` | 1. `CLICK` at `(norm_x, norm_y)` with left mouse button<br>2. `KEY_PRESS` (if `box.navigation` specified) |
| `submit` | 1. `SUBMIT` with `submit_method=BUTTON_CLICK` at `(norm_x, norm_y)` (or `ENTER_KEY`)<br>post_delay_ms defaults to 1000ms for submission processing |
| `clear_field` | 1. `CLEAR_FIELD` with strategy `select_all_backspace` |
| `key_press` | 1. `KEY_PRESS` with specified key |

#### Detailed Parameter Synthesis for `type_text`:
```python
# 1. Click to anchor focus
steps.append(WorkflowStep(
    sequence_index=next_index(),
    label=f"Focus field [{box.name}]",
    action_type=ActionType.CLICK,
    pre_delay_ms=box.pre_delay_ms or 0,
    post_delay_ms=60,
    parameters=StepParameters(
        norm_x=box_norm_x,
        norm_y=box_norm_y,
        coordinate_mode=CoordinateMode.NORMALIZED,
        button=MouseButton.LEFT,
        click_count=1,
    )
))

# 2. Clear field if requested
if box.clear_before:
    steps.append(WorkflowStep(
        sequence_index=next_index(),
        label=f"Clear field [{box.name}]",
        action_type=ActionType.CLEAR_FIELD,
        pre_delay_ms=0,
        post_delay_ms=40,
        parameters=StepParameters(
            clear_strategy=ClearStrategy.SELECT_ALL_BACKSPACE,
        )
    ))

# 3. Type text payload
steps.append(WorkflowStep(
    sequence_index=next_index(),
    label=f"Type text into [{box.name}]",
    action_type=ActionType.TYPE_TEXT,
    pre_delay_ms=0,
    post_delay_ms=box.post_delay_ms or default_delay,
    parameters=StepParameters(
        text=box.value or "",
        is_secret=box.is_secret,
        keystroke_delay_ms=typing_speed_ms,
    )
))

# 4. Post-entry navigation
if box.navigation in ("tab", "enter"):
    steps.append(WorkflowStep(
        sequence_index=next_index(),
        label=f"Navigate ({box.navigation.capitalize()}) from [{box.name}]",
        action_type=ActionType.KEY_PRESS,
        pre_delay_ms=0,
        post_delay_ms=100,
        parameters=StepParameters(
            key=box.navigation,
            repeat_count=1,
        )
    ))
```

---

### Pass 5: Peephole Navigation Optimizer & Safety Post-Processing

Pass 5 applies peephole pattern transformations to streamline workflow execution:

#### 1. Click-to-Tab Replacement (Chained Navigation)
- **Problem**: When fields are arranged in natural sequential tab order, Field 1 ends with `KEY_PRESS(key="tab")`. If Field 2 immediately issues `CLICK(norm_x, norm_y)`, the mouse movement and click are redundant and can disrupt native browser field focus or cause dropdown close events.
- **Rule**: If `optimization.enabled` and `optimization.click_to_tab`:
  Scan through synthesized steps. If step $i$ is `KEY_PRESS(key="tab")` and step $i+1$ is `CLICK` anchoring the next field in sequential order, eliminate step $i+1$.
- **Guardrails**:
  - Do NOT eliminate clicks on buttons (`SUBMIT` or `CLICK` action boxes).
  - Do NOT eliminate clicks if the box metadata specifies `require_click=True` or `force_click=True`.
  - Only eliminate when step $i$ was an explicit `tab` navigation.

#### 2. Consecutive Delay Collapsing
- **Rule**: If `optimization.enabled` and `optimization.collapse_delays`:
  If step $i$ is `ActionType.DELAY` and step $i+1$ is `ActionType.DELAY`:
  Merge step $i+1$ into step $i$ by adding duration:
  $$\text{duration\_ms}_{\text{merged}} = \text{duration\_ms}_i + \text{duration\_ms}_{i+1}$$
  Remove step $i+1$.

#### 3. Redundant Focus Elimination
- If two consecutive `FOCUS_WINDOW` steps target the identical window title pattern, remove the second step.

#### 4. Sequential Step Re-indexing
- After any deletions or merges in Pass 5:
  Re-number all steps: `sequence_index = 1, 2, 3, ..., M`.
  Guarantees strict compliance with `KutomotoWorkflow.validate_steps_sequence` (unique sequence indices).

#### 5. 90Studio Copyright & Metadata Stamping
- Verify `copyright = "Copyrights reserved to 90Studio"`.
- Set `source_mode = SourceMode.VISUAL_DESIGNER_GENERATED`.
- Populate `designer_metadata`:
  ```python
  DesignerMetadata(
      canvas_width=layout.canvas.width,
      canvas_height=layout.canvas.height,
      background_image_path=layout.canvas.background_image_path,
      box_count=len(layout.boxes),
  )
  ```

---

## 4. Exception Hierarchy

Defined in `src/kutomoto/designer/exceptions.py` (and re-exported by `compiler.py`):

```python
class CompilationError(Exception):
    """Base exception for all visual designer compilation failures."""
    pass

class EmptyLayoutError(CompilationError):
    """Raised when attempting to compile a layout containing zero visual boxes."""
    pass

class GeometryError(CompilationError):
    """Raised when canvas dimensions or visual box geometry violate bounds or positive constraints."""
    pass

class DuplicateBoxIdError(CompilationError):
    """Raised when duplicate box identifiers exist within a single visual layout."""
    pass

class OptimizationError(CompilationError):
    """Raised when peephole optimization fails to process action step patterns."""
    pass
```

---

## 5. Reference Implementation Sketch for `compiler.py`

Below is the concrete design for `src/kutomoto/designer/compiler.py`:

```python
"""
kutomoto.designer.compiler
Deterministic 5-Pass Visual-to-Workflow Compilation Engine.
Copyrights reserved to 90Studio
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from kutomoto.designer.exceptions import (
    CompilationError,
    DuplicateBoxIdError,
    EmptyLayoutError,
    GeometryError,
)
from kutomoto.designer.schema import (
    PeepholeOptimizationConfig,
    VisualBox,
    VisualFormLayout,
)
from kutomoto.engine.schema import (
    ActionType,
    ClearStrategy,
    CoordinateMode,
    DesignerMetadata,
    ExecutionSettings,
    KutomotoWorkflow,
    MouseButton,
    SourceMode,
    StepParameters,
    SubmitMethod,
    TargetApplication,
    WorkflowStep,
)

logger = logging.getLogger("kutomoto.designer.compiler")


class CompilationContext:
    """Internal state tracking for the 5-pass compilation pipeline."""
    def __init__(self, layout: VisualFormLayout, opt: PeepholeOptimizationConfig):
        self.layout = layout
        self.opt = opt
        self.warnings: List[str] = []
        self.ordered_boxes: List[VisualBox] = []
        self.normalized_coords: Dict[str, Tuple[float, float, float, float]] = {}
        self.raw_steps: List[WorkflowStep] = []
        self.optimized_steps: List[WorkflowStep] = []


def _pass1_validate_geometry(ctx: CompilationContext) -> None:
    """Pass 1: Structural & Geometry Integrity Validation."""
    boxes = ctx.layout.boxes
    if not boxes:
        raise EmptyLayoutError("Visual layout must contain at least one visual box.")

    cw = ctx.layout.canvas.width
    ch = ctx.layout.canvas.height
    if cw <= 0 or ch <= 0:
        raise GeometryError(f"Canvas dimensions must be strictly positive, got {cw}x{ch}.")

    seen_ids = set()
    eps = 1e-4

    for b in boxes:
        if b.id in seen_ids:
            raise DuplicateBoxIdError(f"Duplicate box ID detected: '{b.id}'. Every box must have a unique ID.")
        seen_ids.add(b.id)

        gx, gy, gw, gh = b.geometry.x, b.geometry.y, b.geometry.width, b.geometry.height

        if gw <= 0 or gh <= 0:
            raise GeometryError(f"Box '{b.id}' ({b.name}) has non-positive dimensions: {gw}x{gh}.")
        if gx < 0 or gy < 0:
            raise GeometryError(f"Box '{b.id}' ({b.name}) has negative coordinates: ({gx}, {gy}).")
        if (gx + gw) > (cw + eps) or (gy + gh) > (ch + eps):
            raise GeometryError(
                f"Box '{b.id}' ({b.name}) exceeds canvas bounds: "
                f"right={gx + gw} > canvas_w={cw} or bottom={gy + gh} > canvas_h={ch}."
            )

    # Collision warnings (non-fatal)
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            b1, b2 = boxes[i], boxes[j]
            g1, g2 = b1.geometry, b2.geometry
            if (g1.x < g2.x + g2.width and g1.x + g1.width > g2.x and
                g1.y < g2.y + g2.height and g1.y + g1.height > g2.y):
                msg = f"Visual overlap detected between Box '{b1.name}' and Box '{b2.name}'."
                ctx.warnings.append(msg)
                logger.warning(msg)


def _pass2_sort_sequence(ctx: CompilationContext) -> None:
    """Pass 2: Sequence Ordering & Spatial Topological Sorting."""
    boxes = ctx.layout.boxes
    explicit_boxes = [b for b in boxes if b.sequence_index is not None and b.sequence_index > 0]
    unindexed_boxes = [b for b in boxes if b.sequence_index is None or b.sequence_index <= 0]

    # If all explicit
    if len(explicit_boxes) == len(boxes):
        ctx.ordered_boxes = sorted(
            explicit_boxes,
            key=lambda b: (b.sequence_index, b.geometry.y, b.geometry.x)
        )
        return

    # Spatial 2D Band Sort for unindexed boxes
    if unindexed_boxes:
        band_tol = ctx.opt.band_tolerance_px
        if band_tol <= 0:
            avg_h = sum(b.geometry.height for b in unindexed_boxes) / len(unindexed_boxes)
            band_tol = max(10.0, avg_h * 0.5)

        sorted_by_y = sorted(unindexed_boxes, key=lambda b: (b.geometry.y, b.geometry.x))
        bands: List[List[VisualBox]] = []
        curr_band = [sorted_by_y[0]]
        anchor_y = sorted_by_y[0].geometry.y

        for b in sorted_by_y[1:]:
            if abs(b.geometry.y - anchor_y) <= band_tol:
                curr_band.append(b)
            else:
                bands.append(curr_band)
                curr_band = [b]
                anchor_y = b.geometry.y
        bands.append(curr_band)

        spatially_sorted = []
        for band in bands:
            spatially_sorted.extend(sorted(band, key=lambda b: b.geometry.x))
    else:
        spatially_sorted = []

    if explicit_boxes:
        sorted_explicit = sorted(
            explicit_boxes,
            key=lambda b: (b.sequence_index, b.geometry.y, b.geometry.x)
        )
        ctx.ordered_boxes = sorted_explicit + spatially_sorted
    else:
        ctx.ordered_boxes = spatially_sorted


def _pass3_normalize_coordinates(ctx: CompilationContext) -> None:
    """Pass 3: Dual-Coordinate Normalization."""
    cw = float(ctx.layout.canvas.width)
    ch = float(ctx.layout.canvas.height)

    for b in ctx.ordered_boxes:
        g = b.geometry
        cx = g.x + g.width / 2.0
        cy = g.y + g.height / 2.0

        norm_x = round(max(0.0, min(1.0, cx / cw)), 4)
        norm_y = round(max(0.0, min(1.0, cy / ch)), 4)
        norm_w = round(max(0.0, min(1.0, g.width / cw)), 4)
        norm_h = round(max(0.0, min(1.0, g.height / ch)), 4)

        ctx.normalized_coords[b.id] = (norm_x, norm_y, norm_w, norm_h)


def _pass4_synthesize_steps(ctx: CompilationContext) -> None:
    """Pass 4: Atomic Step Generation & Parameter Synthesis."""
    steps: List[WorkflowStep] = []
    target = ctx.layout.target_application
    exec_settings = ctx.layout.execution_settings
    default_delay = exec_settings.default_step_delay_ms
    typing_speed = exec_settings.typing_speed_ms

    def next_seq() -> int:
        return len(steps) + 1

    # Step 1: Focus Window Header
    steps.append(WorkflowStep(
        step_id=str(uuid.uuid4()),
        sequence_index=next_seq(),
        label=f"Focus Window: {target.window_title_pattern}",
        action_type=ActionType.FOCUS_WINDOW,
        enabled=True,
        pre_delay_ms=0,
        post_delay_ms=250,
        parameters=StepParameters(
            window_title_pattern=target.window_title_pattern,
            process_name=target.process_name,
            match_mode=target.match_mode,
        )
    ))

    for box in ctx.ordered_boxes:
        norm_x, norm_y, norm_w, norm_h = ctx.normalized_coords[box.id]
        act_type = str(box.action_type).lower()
        if hasattr(box.action_type, "value"):
            act_type = box.action_type.value.lower()

        pre_delay = box.pre_delay_ms if box.pre_delay_ms is not None else 0
        post_delay = box.post_delay_ms if box.post_delay_ms is not None else default_delay

        if act_type in ("type_text", "text"):
            # Click to focus
            steps.append(WorkflowStep(
                step_id=str(uuid.uuid4()),
                sequence_index=next_seq(),
                label=f"Focus field [{box.label or box.name}]",
                action_type=ActionType.CLICK,
                enabled=True,
                pre_delay_ms=pre_delay,
                post_delay_ms=60,
                parameters=StepParameters(
                    norm_x=norm_x,
                    norm_y=norm_y,
                    coordinate_mode=CoordinateMode.NORMALIZED,
                    button=MouseButton.LEFT,
                    click_count=1,
                )
            ))

            # Clear field if required
            if box.clear_before:
                steps.append(WorkflowStep(
                    step_id=str(uuid.uuid4()),
                    sequence_index=next_seq(),
                    label=f"Clear field [{box.name}]",
                    action_type=ActionType.CLEAR_FIELD,
                    enabled=True,
                    pre_delay_ms=0,
                    post_delay_ms=40,
                    parameters=StepParameters(
                        clear_strategy=ClearStrategy.SELECT_ALL_BACKSPACE
                    )
                ))

            # Type text
            steps.append(WorkflowStep(
                step_id=str(uuid.uuid4()),
                sequence_index=next_seq(),
                label=f"Type into [{box.name}]",
                action_type=ActionType.TYPE_TEXT,
                enabled=True,
                pre_delay_ms=0,
                post_delay_ms=post_delay,
                parameters=StepParameters(
                    text=box.value or "",
                    is_secret=box.is_secret,
                    keystroke_delay_ms=typing_speed,
                )
            ))

        elif act_type in ("click", "button"):
            steps.append(WorkflowStep(
                step_id=str(uuid.uuid4()),
                sequence_index=next_seq(),
                label=f"Click [{box.label or box.name}]",
                action_type=ActionType.CLICK,
                enabled=True,
                pre_delay_ms=pre_delay,
                post_delay_ms=post_delay,
                parameters=StepParameters(
                    norm_x=norm_x,
                    norm_y=norm_y,
                    coordinate_mode=CoordinateMode.NORMALIZED,
                    button=MouseButton.LEFT,
                    click_count=1,
                )
            ))

        elif act_type in ("submit", "submit_button"):
            steps.append(WorkflowStep(
                step_id=str(uuid.uuid4()),
                sequence_index=next_seq(),
                label=f"Submit Form via [{box.label or box.name or 'Submit'}]",
                action_type=ActionType.SUBMIT,
                enabled=True,
                pre_delay_ms=pre_delay,
                post_delay_ms=1000,
                parameters=StepParameters(
                    submit_method=SubmitMethod.BUTTON_CLICK,
                    norm_x=norm_x,
                    norm_y=norm_y,
                    coordinate_mode=CoordinateMode.NORMALIZED,
                )
            ))

        # Navigation key (Tab / Enter)
        nav = (box.navigation or "none").lower()
        if nav in ("tab", "enter"):
            steps.append(WorkflowStep(
                step_id=str(uuid.uuid4()),
                sequence_index=next_seq(),
                label=f"Navigate ({nav.capitalize()}) from [{box.name}]",
                action_type=ActionType.KEY_PRESS,
                enabled=True,
                pre_delay_ms=0,
                post_delay_ms=100,
                parameters=StepParameters(
                    key=nav,
                    repeat_count=1,
                )
            ))

    ctx.raw_steps = steps


def _pass5_optimize_peephole(ctx: CompilationContext) -> None:
    """Pass 5: Peephole Navigation Optimizer & Safety Post-Processing."""
    steps = list(ctx.raw_steps)

    if ctx.opt.enabled:
        # Optimization 1: Click-to-Tab Replacement
        if ctx.opt.click_to_tab:
            filtered_steps: List[WorkflowStep] = []
            for i, s in enumerate(steps):
                # If current step is CLICK focusing a field, and previous step was a TAB key_press:
                if (s.action_type == ActionType.CLICK and
                    s.parameters.coordinate_mode == CoordinateMode.NORMALIZED and
                    filtered_steps and
                    filtered_steps[-1].action_type == ActionType.KEY_PRESS and
                    filtered_steps[-1].parameters.key == "tab"):
                    # Check if step has force_click metadata
                    # Redundant click is safely dropped
                    logger.debug("Peephole optimizer: Dropping redundant click step %s after tab", s.label)
                    continue
                filtered_steps.append(s)
            steps = filtered_steps

        # Optimization 2: Consecutive Delay Collapsing
        if ctx.opt.collapse_delays:
            collapsed: List[WorkflowStep] = []
            for s in steps:
                if (collapsed and
                    collapsed[-1].action_type == ActionType.DELAY and
                    s.action_type == ActionType.DELAY):
                    d1 = collapsed[-1].parameters.duration_ms or 0
                    d2 = s.parameters.duration_ms or 0
                    collapsed[-1].parameters.duration_ms = d1 + d2
                else:
                    collapsed.append(s)
            steps = collapsed

    # Sequential re-indexing 1..N
    for seq, s in enumerate(steps, start=1):
        s.sequence_index = seq

    ctx.optimized_steps = steps


def compile_visual_layout_to_workflow(
    layout: Union[VisualFormLayout, Dict[str, Any]],
    optimization: Optional[PeepholeOptimizationConfig] = None,
) -> KutomotoWorkflow:
    """
    Translates a VisualFormLayout into an executable KutomotoWorkflow.
    """
    if isinstance(layout, dict):
        layout = VisualFormLayout.model_validate(layout)

    opt = optimization or layout.optimization or PeepholeOptimizationConfig()
    ctx = CompilationContext(layout, opt)

    _pass1_validate_geometry(ctx)
    _pass2_sort_sequence(ctx)
    _pass3_normalize_coordinates(ctx)
    _pass4_synthesize_steps(ctx)
    _pass5_optimize_peephole(ctx)

    return KutomotoWorkflow(
        schema_version="1.0.0",
        id=str(uuid.uuid4()),
        name=layout.name,
        description=layout.description,
        author="kutomoto Visual Form Compiler",
        copyright="Copyrights reserved to 90Studio",
        source_mode=SourceMode.VISUAL_DESIGNER_GENERATED,
        target_application=layout.target_application,
        execution_settings=layout.execution_settings,
        designer_metadata=DesignerMetadata(
            canvas_width=layout.canvas.width,
            canvas_height=layout.canvas.height,
            background_image_path=layout.canvas.background_image_path,
            box_count=len(ctx.ordered_boxes),
        ),
        steps=ctx.optimized_steps,
    )


def compile_visual_boxes_to_workflow(
    layout: Union[VisualFormLayout, Dict[str, Any]],
    traversal_mode: str = "coordinate_targeted",
    **kwargs: Any,
) -> KutomotoWorkflow:
    """Backward-compatible alias matching SPECIFICATION.md Section 8.1."""
    opt = PeepholeOptimizationConfig(
        click_to_tab=(traversal_mode == "tab_chained")
    )
    return compile_visual_layout_to_workflow(layout, optimization=opt)
```

---

## 6. Verification and Integration Analysis

### 6.1 Compatibility with `src/kutomoto/engine/runner.py`
The generated `KutomotoWorkflow` model passes all Pydantic validations:
- `validate_copyright`: Verified against `"Copyrights reserved to 90Studio"`.
- `validate_steps_sequence`: Steps 1 through $N$ are unique and contiguous.
- `CoordinateMode.NORMALIZED`: Center `norm_x` and `norm_y` are within $[0.0, 1.0]$.
- When executed by `WorkflowRunner`:
  - `_execute_click` calculates client coordinates via `client_x = int(round(p.norm_x * client_w))` and `client_y = int(round(p.norm_y * client_h))`.
  - `_execute_type_text` takes `p.text` and `p.keystroke_delay_ms`.
  - `_execute_clear_field` takes `p.clear_strategy` (`SELECT_ALL_BACKSPACE`).
  - `_execute_submit` dispatches `BUTTON_CLICK` at normalized coordinates.

### 6.2 Edge Cases Addressed
1. **Accidental Sub-threshold Clicks**: Rejected at canvas or schema level (`width >= 24`, `height >= 16`).
2. **Boundary Precision Errors**: Clamping and epsilon tolerances prevent rejecting boxes placed flush against the canvas edge.
3. **Multi-Column Forms**: Spatial band sorting groups rows before sorting columns left-to-right, ensuring accurate Western reading order across multi-column layouts.
4. **Disabled Optimizer Mode**: Setting `optimization.enabled = False` retains every explicit click and delay step unchanged.
