"""
kutomoto.designer.compiler
5-Pass Visual Form Designer to Workflow Compiler.
Copyrights reserved to 90Studio
"""

import logging
from typing import Any, Dict, List, Optional, Union
import uuid

from pydantic import ValidationError

from kutomoto.designer.exceptions import (
    CompilationError,
    DuplicateBoxIdError,
    EmptyLayoutError,
    GeometryError,
)
from kutomoto.designer.schema import (
    CanvasDimensions,
    DesignerActionType,
    PeepholeOptimizationConfig,
    VisualBox,
    VisualFormLayout,
)
from kutomoto.engine.schema import (
    ActionType,
    ClearStrategy,
    CoordinateMode,
    DesignerMetadata,
    KutomotoWorkflow,
    MouseButton,
    SourceMode,
    StepParameters,
    SubmitMethod,
    WorkflowStep,
    WorkflowVariable,
)

logger = logging.getLogger("kutomoto.designer.compiler")


# ==============================================================================
# PASS 2 HELPER: 2D SPATIAL BAND SORTING
# ==============================================================================

def _spatial_band_sort(
    boxes: List[VisualBox], band_tolerance_px: float = 24.0
) -> List[VisualBox]:
    """
    Partitions visual boxes into horizontal bands according to vertical proximity
    and sorts boxes within each band from left to right (Western reading order).
    """
    if not boxes:
        return []

    tolerance = band_tolerance_px
    if tolerance <= 0:
        avg_h = sum(b.geometry.height for b in boxes) / len(boxes)
        tolerance = max(10.0, 0.5 * avg_h)

    # Sort primarily by vertical coordinate Y, tie-break by X
    sorted_by_y = sorted(boxes, key=lambda b: (b.geometry.y, b.geometry.x))

    bands: List[List[VisualBox]] = []
    current_band: List[VisualBox] = [sorted_by_y[0]]
    anchor_y = sorted_by_y[0].geometry.y

    for b in sorted_by_y[1:]:
        if abs(b.geometry.y - anchor_y) <= tolerance:
            current_band.append(b)
        else:
            bands.append(current_band)
            current_band = [b]
            anchor_y = b.geometry.y
    bands.append(current_band)

    # Sort each band horizontally left-to-right by X
    result: List[VisualBox] = []
    for band in bands:
        sorted_band = sorted(band, key=lambda b: (b.geometry.x, b.geometry.y))
        result.extend(sorted_band)

    return result


# ==============================================================================
# PASS 5 HELPER: PEEPHOLE OPTIMIZER & RE-INDEXING
# ==============================================================================

def _pass5_optimize_peephole(
    steps: List[WorkflowStep], opt: PeepholeOptimizationConfig
) -> List[WorkflowStep]:
    """
    Pass 5: Applies peephole pattern transformations to streamline workflow execution:
    1. Prunes redundant consecutive FOCUS_WINDOW steps targeting the same application.
    2. Prunes redundant CLICK steps following TAB keypress in reading order.
    3. Collapses consecutive DELAY steps by duration summation.
    4. Prunes empty (0ms) DELAY steps.
    5. Re-indexes steps strictly from 1 to N to guarantee contiguous uniqueness.
    """
    if not opt.enabled:
        for idx, s in enumerate(steps, start=1):
            s.sequence_index = idx
        return steps

    # Pattern C1: Redundant focus window elimination
    if opt.remove_redundant_focus:
        pruned_focus: List[WorkflowStep] = []
        for s in steps:
            if (
                s.action_type == ActionType.FOCUS_WINDOW
                and pruned_focus
                and pruned_focus[-1].action_type == ActionType.FOCUS_WINDOW
                and pruned_focus[-1].parameters.window_title_pattern
                == s.parameters.window_title_pattern
                and pruned_focus[-1].parameters.process_name
                == s.parameters.process_name
            ):
                logger.debug(
                    "Peephole Optimizer: Pruned redundant duplicate focus window: '%s'",
                    s.label,
                )
                continue
            pruned_focus.append(s)
    else:
        pruned_focus = list(steps)

    # Pattern A: Click-to-tab elimination
    if opt.click_to_tab:
        tab_optimized: List[WorkflowStep] = []
        field_click_count = 0
        for i, s in enumerate(pruned_focus):
            if s.action_type == ActionType.CLICK:
                field_click_count += 1
                is_force_click = (
                    getattr(s, "_force_click", False)
                    or (s.label and "[force_click]" in s.label.lower())
                    or (s.parameters.variable_name == "__force_click__")
                )
                is_after_tab = (
                    tab_optimized
                    and tab_optimized[-1].action_type == ActionType.KEY_PRESS
                    and (tab_optimized[-1].parameters.key or "").lower() == "tab"
                )
                # Standalone action clicks (CLICK, CHECKBOX, SELECT) represent primary
                # user operations and must never be pruned by click_to_tab.
                is_action_click = getattr(s, "_is_action_click", False)
                is_focus_anchor = getattr(s, "_is_focus_anchor", False)

                # Lookahead fallback if explicit tags are absent (e.g. raw steps):
                # A click is an auxiliary focus anchor ONLY if it immediately precedes
                # text entry operations (CLEAR_FIELD or TYPE_TEXT).
                if not is_action_click and not is_focus_anchor:
                    for next_step in pruned_focus[i + 1 :]:
                        if next_step.action_type in (
                            ActionType.CLEAR_FIELD,
                            ActionType.TYPE_TEXT,
                        ):
                            is_focus_anchor = True
                            break
                        if next_step.action_type != ActionType.DELAY:
                            break

                # Prune ONLY redundant focus anchor clicks following Tab keypress.
                # Explicit force_click and standalone action clicks are strictly preserved.
                if (
                    field_click_count > 1
                    and is_after_tab
                    and not is_force_click
                    and not is_action_click
                    and is_focus_anchor
                ):
                    logger.debug(
                        "Peephole Optimizer: Pruned redundant focus click step: '%s'",
                        s.label,
                    )
                    # Preserve field settling delay (pre_delay_ms) if configured
                    if s.pre_delay_ms and s.pre_delay_ms > 0:
                        if i + 1 < len(pruned_focus):
                            pruned_focus[i + 1].pre_delay_ms = (
                                pruned_focus[i + 1].pre_delay_ms or 0
                            ) + s.pre_delay_ms
                        else:
                            tab_optimized.append(
                                WorkflowStep(
                                    step_id=str(uuid.uuid4()),
                                    sequence_index=len(tab_optimized) + 1,
                                    label=f"Settling Delay ({s.pre_delay_ms}ms)",
                                    action_type=ActionType.DELAY,
                                    enabled=True,
                                    parameters=StepParameters(duration_ms=s.pre_delay_ms),
                                )
                            )
                    continue
            tab_optimized.append(s)
    else:
        tab_optimized = list(pruned_focus)

    # Pattern B: Delay collapsing and empty delay pruning
    collapsed_delays: List[WorkflowStep] = []
    for s in tab_optimized:
        # Discard 0ms delay steps if configured
        if opt.prune_empty_delays and s.action_type == ActionType.DELAY:
            dur = s.parameters.duration_ms if s.parameters.duration_ms is not None else 0
            if dur <= 0:
                logger.debug(
                    "Peephole Optimizer: Pruned 0ms delay step: '%s'", s.label
                )
                continue

        if (
            opt.collapse_delays
            and collapsed_delays
            and collapsed_delays[-1].action_type == ActionType.DELAY
            and s.action_type == ActionType.DELAY
        ):
            prev_dur = collapsed_delays[-1].parameters.duration_ms or 0
            curr_dur = s.parameters.duration_ms or 0
            total_dur = prev_dur + curr_dur
            collapsed_delays[-1].parameters.duration_ms = total_dur
            collapsed_delays[-1].label = f"Coalesced Delay ({total_dur}ms)"
            logger.debug(
                "Peephole Optimizer: Collapsed delay %d ms + %d ms -> %d ms",
                prev_dur,
                curr_dur,
                total_dur,
            )
        else:
            collapsed_delays.append(s)

    # Pattern C2: Strict contiguous 1-based sequential re-indexing
    for idx, s in enumerate(collapsed_delays, start=1):
        s.sequence_index = idx

    return collapsed_delays


# ==============================================================================
# PRIMARY COMPILER FUNCTION
# ==============================================================================

def compile_visual_layout_to_workflow(
    layout: Union[VisualFormLayout, Dict[str, Any]],
    optimization: Optional[PeepholeOptimizationConfig] = None,
) -> KutomotoWorkflow:
    """
    Translates a VisualFormLayout into an executable KutomotoWorkflow using
    a deterministic 5-pass compilation algorithm.

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
    # --------------------------------------------------------------------------
    # PASS 1: Structural & Geometry Integrity Validation
    # --------------------------------------------------------------------------
    if isinstance(layout, dict):
        raw_boxes = layout.get("boxes")
        if raw_boxes is None or len(raw_boxes) == 0:
            raise EmptyLayoutError("Compilation error: visual layout contains no visual boxes.")

        canvas_data = layout.get("canvas")
        if not canvas_data or not isinstance(canvas_data, (dict, CanvasDimensions)):
            raise GeometryError("Compilation error: layout canvas is missing or invalid.")

        cw = (
            canvas_data.get("width")
            if isinstance(canvas_data, dict)
            else getattr(canvas_data, "width", None)
        )
        ch = (
            canvas_data.get("height")
            if isinstance(canvas_data, dict)
            else getattr(canvas_data, "height", None)
        )
        if cw is None or ch is None or cw <= 0 or ch <= 0:
            raise GeometryError(
                f"Compilation error: Canvas dimensions must be strictly positive, got {cw}x{ch}."
            )

        visited_ids = set()
        for b in raw_boxes:
            bid = b.get("id") if isinstance(b, dict) else getattr(b, "id", None)
            bname = b.get("name") if isinstance(b, dict) else getattr(b, "name", "unnamed_box")
            if bid:
                if bid in visited_ids:
                    raise DuplicateBoxIdError(
                        f"Duplicate box ID detected: '{bid}'. Every box must have a unique ID."
                    )
                visited_ids.add(bid)

            geom = (
                b.get("geometry") or b.get("rect")
                if isinstance(b, dict)
                else getattr(b, "geometry", None)
            )
            if not geom:
                raise GeometryError(f"Box '{bid or bname}' is missing geometry/rect.")

            gx = geom.get("x") if isinstance(geom, dict) else getattr(geom, "x", None)
            gy = geom.get("y") if isinstance(geom, dict) else getattr(geom, "y", None)
            gw = geom.get("width") if isinstance(geom, dict) else getattr(geom, "width", None)
            gh = geom.get("height") if isinstance(geom, dict) else getattr(geom, "height", None)

            if gw is None or gh is None or gw <= 0 or gh <= 0:
                raise GeometryError(
                    f"Box '{bid or bname}' has invalid zero or negative dimensions: {gw}x{gh}."
                )
            if gx is None or gy is None or gx < 0 or gy < 0:
                raise GeometryError(
                    f"Box '{bid or bname}' has negative coordinates: ({gx}, {gy})."
                )
            if gx + gw > cw + 1e-4:
                raise GeometryError(
                    f"Box '{bid or bname}' right edge ({gx + gw:.2f}) exceeds canvas width ({cw:.2f})."
                )
            if gy + gh > ch + 1e-4:
                raise GeometryError(
                    f"Box '{bid or bname}' bottom edge ({gy + gh:.2f}) exceeds canvas height ({ch:.2f})."
                )

        dict_copy = dict(layout)
        if "name" not in dict_copy:
            dict_copy["name"] = "Compiled Visual Form"
        if "target_application" not in dict_copy and "target" not in dict_copy:
            dict_copy["target_application"] = {"window_title_pattern": ".*"}
        if "copyright" not in dict_copy:
            dict_copy["copyright"] = "Copyrights reserved to 90Studio"

        try:
            layout_model = VisualFormLayout.model_validate(dict_copy)
        except ValidationError as e:
            raise CompilationError(f"Compilation error validating layout model: {e}") from e
    else:
        layout_model = layout
        if not layout_model.boxes:
            raise EmptyLayoutError("Compilation error: visual layout contains no visual boxes.")
        if layout_model.canvas.width <= 0 or layout_model.canvas.height <= 0:
            raise GeometryError(
                f"Compilation error: Canvas dimensions must be strictly positive, "
                f"got {layout_model.canvas.width}x{layout_model.canvas.height}."
            )
        cw = layout_model.canvas.width
        ch = layout_model.canvas.height
        visited_ids = set()
        for b in layout_model.boxes:
            if b.id in visited_ids:
                raise DuplicateBoxIdError(
                    f"Duplicate box ID detected: '{b.id}'. Every box must have a unique ID."
                )
            visited_ids.add(b.id)
            if b.geometry.width <= 0 or b.geometry.height <= 0:
                raise GeometryError(
                    f"Box '{b.id}' (name='{b.name}') has invalid zero or negative dimensions: "
                    f"{b.geometry.width}x{b.geometry.height}."
                )
            if b.geometry.x < 0 or b.geometry.y < 0:
                raise GeometryError(
                    f"Box '{b.id}' (name='{b.name}') has negative coordinates: "
                    f"({b.geometry.x}, {b.geometry.y})."
                )
            if b.geometry.right > cw + 1e-4:
                raise GeometryError(
                    f"Box '{b.id}' (name='{b.name}') right edge ({b.geometry.right:.2f}) "
                    f"exceeds canvas width ({cw:.2f})."
                )
            if b.geometry.bottom > ch + 1e-4:
                raise GeometryError(
                    f"Box '{b.id}' (name='{b.name}') bottom edge ({b.geometry.bottom:.2f}) "
                    f"exceeds canvas height ({ch:.2f})."
                )

    # Detect box collisions (non-fatal warning diagnostics)
    boxes = layout_model.boxes
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            b1, b2 = boxes[i], boxes[j]
            g1, g2 = b1.geometry, b2.geometry
            if (
                g1.x < g2.right
                and g1.right > g2.x
                and g1.y < g2.bottom
                and g1.bottom > g2.y
            ):
                logger.warning(
                    "Visual layout warning: Box '%s' (name='%s') collides with Box '%s' (name='%s')",
                    b1.id,
                    b1.name,
                    b2.id,
                    b2.name,
                )

    # Resolve active optimization configuration
    effective_opt = (
        optimization if optimization is not None else layout_model.optimization
    )

    # --------------------------------------------------------------------------
    # PASS 2: Spatial Band Sorting & Sequence Ordering
    # --------------------------------------------------------------------------
    boxes_list = list(layout_model.boxes)
    explicit_boxes = [
        b for b in boxes_list if b.sequence_index is not None and b.sequence_index >= 1
    ]
    unindexed_boxes = [
        b for b in boxes_list if b.sequence_index is None or b.sequence_index < 1
    ]

    if len(explicit_boxes) == len(boxes_list):
        # All boxes have explicit sequence index
        ordered_boxes = sorted(
            boxes_list, key=lambda b: (b.sequence_index, b.geometry.y, b.geometry.x)
        )
    elif not explicit_boxes:
        # All boxes unindexed: 2D Spatial Band Sort
        ordered_boxes = _spatial_band_sort(
            boxes_list, effective_opt.band_tolerance_px
        )
    else:
        # Hybrid layout: explicit sequence first, unindexed resolved spatially
        ordered_explicit = sorted(
            explicit_boxes, key=lambda b: (b.sequence_index, b.geometry.y, b.geometry.x)
        )
        ordered_unindexed = _spatial_band_sort(
            unindexed_boxes, effective_opt.band_tolerance_px
        )
        ordered_boxes = ordered_explicit + ordered_unindexed

    # --------------------------------------------------------------------------
    # PASS 3: Dual-Coordinate Normalization
    # --------------------------------------------------------------------------
    norm_data = [layout_model.get_normalized_box(b) for b in ordered_boxes]

    # --------------------------------------------------------------------------
    # PASS 4: Action Step Synthesis
    # --------------------------------------------------------------------------
    raw_steps: List[WorkflowStep] = []

    # Header Step (Sequence Index 1): FOCUS_WINDOW
    raw_steps.append(
        WorkflowStep(
            step_id=str(uuid.uuid4()),
            sequence_index=1,
            label=f"Focus Target Window: {layout_model.target_application.window_title_pattern}",
            action_type=ActionType.FOCUS_WINDOW,
            enabled=True,
            pre_delay_ms=0,
            post_delay_ms=250,
            parameters=StepParameters(
                window_title_pattern=layout_model.target_application.window_title_pattern,
                process_name=layout_model.target_application.process_name,
                match_mode=layout_model.target_application.match_mode,
            ),
        )
    )

    default_delay = layout_model.execution_settings.default_step_delay_ms
    default_typing_speed = layout_model.execution_settings.typing_speed_ms

    for box, norm in zip(ordered_boxes, norm_data):
        pre_delay = (
            box.timing.pre_delay_ms
            if (box.timing and box.timing.pre_delay_ms is not None)
            else (getattr(box, "pre_delay_ms", 0) or 0)
        )
        post_delay = (
            box.timing.post_delay_ms
            if (box.timing and box.timing.post_delay_ms is not None)
            else (box.post_delay_ms or default_delay)
        )
        typing_speed = (
            box.timing.typing_speed_ms
            if (box.timing and box.timing.typing_speed_ms is not None)
            else default_typing_speed
        )
        is_secret = (
            box.value_config.is_secret
            if box.value_config is not None
            else bool(box.metadata.get("is_secret", False))
        )
        force_click = bool(
            box.force_click
            or box.metadata.get("force_click", False)
            or box.metadata.get("requires_click", False)
        )

        nav_str = str(
            box.navigation.value if hasattr(box.navigation, "value") else box.navigation
        ).lower()

        if box.action_type in (DesignerActionType.TYPE_TEXT, "type_text"):
            # 1. Click to anchor focus
            click_step = WorkflowStep(
                step_id=str(uuid.uuid4()),
                sequence_index=len(raw_steps) + 1,
                label=f"Click [{box.label or box.name}]"
                + (" [force_click]" if force_click else ""),
                action_type=ActionType.CLICK,
                enabled=True,
                pre_delay_ms=pre_delay,
                post_delay_ms=60,
                parameters=StepParameters(
                    norm_x=norm["center_norm_x"],
                    norm_y=norm["center_norm_y"],
                    coordinate_mode=CoordinateMode.NORMALIZED,
                    button=MouseButton.LEFT,
                    click_count=1,
                    variable_name="__force_click__" if force_click else None,
                ),
            )
            setattr(click_step, "_force_click", force_click)
            setattr(click_step, "_is_focus_anchor", True)
            raw_steps.append(click_step)

            # 2. Clear field if requested
            if box.clear_before:
                raw_steps.append(
                    WorkflowStep(
                        step_id=str(uuid.uuid4()),
                        sequence_index=len(raw_steps) + 1,
                        label=f"Clear [{box.label or box.name}]",
                        action_type=ActionType.CLEAR_FIELD,
                        enabled=True,
                        pre_delay_ms=0,
                        post_delay_ms=40,
                        parameters=StepParameters(
                            clear_strategy=ClearStrategy.SELECT_ALL_BACKSPACE,
                        ),
                    )
                )

            # 3. Type text
            raw_steps.append(
                WorkflowStep(
                    step_id=str(uuid.uuid4()),
                    sequence_index=len(raw_steps) + 1,
                    label=f"Type into [{box.label or box.name}]",
                    action_type=ActionType.TYPE_TEXT,
                    enabled=True,
                    pre_delay_ms=0,
                    post_delay_ms=post_delay,
                    parameters=StepParameters(
                        text=box.value or "",
                        is_secret=is_secret,
                        keystroke_delay_ms=typing_speed,
                    ),
                )
            )

            # 4. Navigation key press
            if nav_str == "tab":
                raw_steps.append(
                    WorkflowStep(
                        step_id=str(uuid.uuid4()),
                        sequence_index=len(raw_steps) + 1,
                        label=f"Tab after [{box.label or box.name}]",
                        action_type=ActionType.KEY_PRESS,
                        enabled=True,
                        pre_delay_ms=0,
                        post_delay_ms=100,
                        parameters=StepParameters(key="tab", repeat_count=1),
                    )
                )
            elif nav_str == "enter":
                raw_steps.append(
                    WorkflowStep(
                        step_id=str(uuid.uuid4()),
                        sequence_index=len(raw_steps) + 1,
                        label=f"Enter after [{box.label or box.name}]",
                        action_type=ActionType.KEY_PRESS,
                        enabled=True,
                        pre_delay_ms=0,
                        post_delay_ms=100,
                        parameters=StepParameters(key="enter", repeat_count=1),
                    )
                )

        elif box.action_type in (
            DesignerActionType.CLICK,
            "click",
            DesignerActionType.CHECKBOX,
            "checkbox",
            DesignerActionType.SELECT,
            "select",
        ):
            click_label = f"Click [{box.label or box.name}]" + (
                " [force_click]" if force_click else ""
            )
            click_step = WorkflowStep(
                step_id=str(uuid.uuid4()),
                sequence_index=len(raw_steps) + 1,
                label=click_label,
                action_type=ActionType.CLICK,
                enabled=True,
                pre_delay_ms=pre_delay,
                post_delay_ms=post_delay,
                parameters=StepParameters(
                    norm_x=norm["center_norm_x"],
                    norm_y=norm["center_norm_y"],
                    coordinate_mode=CoordinateMode.NORMALIZED,
                    button=MouseButton.LEFT,
                    click_count=1,
                    variable_name="__force_click__" if force_click else None,
                ),
            )
            setattr(click_step, "_force_click", force_click)
            setattr(click_step, "_is_action_click", True)
            raw_steps.append(click_step)
            if nav_str in ("tab", "enter"):
                raw_steps.append(
                    WorkflowStep(
                        step_id=str(uuid.uuid4()),
                        sequence_index=len(raw_steps) + 1,
                        label=f"{nav_str.capitalize()} after [{box.label or box.name}]",
                        action_type=ActionType.KEY_PRESS,
                        enabled=True,
                        pre_delay_ms=0,
                        post_delay_ms=100,
                        parameters=StepParameters(key=nav_str, repeat_count=1),
                    )
                )

        elif box.action_type in (
            DesignerActionType.SUBMIT,
            "submit",
            "submit_button",
        ):
            raw_steps.append(
                WorkflowStep(
                    step_id=str(uuid.uuid4()),
                    sequence_index=len(raw_steps) + 1,
                    label=f"Submit via [{box.label or box.name}]",
                    action_type=ActionType.SUBMIT,
                    enabled=True,
                    pre_delay_ms=pre_delay,
                    post_delay_ms=max(post_delay, 1000),
                    parameters=StepParameters(
                        submit_method=SubmitMethod.BUTTON_CLICK,
                        norm_x=norm["center_norm_x"],
                        norm_y=norm["center_norm_y"],
                        coordinate_mode=CoordinateMode.NORMALIZED,
                    ),
                )
            )

        elif box.action_type in (DesignerActionType.DELAY, "delay"):
            dur = (
                int(box.value)
                if (box.value and str(box.value).strip().isdigit())
                else post_delay
            )
            raw_steps.append(
                WorkflowStep(
                    step_id=str(uuid.uuid4()),
                    sequence_index=len(raw_steps) + 1,
                    label=f"Delay ({dur}ms)",
                    action_type=ActionType.DELAY,
                    enabled=True,
                    parameters=StepParameters(duration_ms=dur),
                )
            )

        elif box.action_type in (DesignerActionType.KEY_PRESS, "key_press"):
            key_name = box.value.strip().lower() if box.value else "tab"
            raw_steps.append(
                WorkflowStep(
                    step_id=str(uuid.uuid4()),
                    sequence_index=len(raw_steps) + 1,
                    label=f"Key press [{key_name}]",
                    action_type=ActionType.KEY_PRESS,
                    enabled=True,
                    pre_delay_ms=pre_delay,
                    post_delay_ms=post_delay,
                    parameters=StepParameters(key=key_name, repeat_count=1),
                )
            )

    # --------------------------------------------------------------------------
    # PASS 5: Peephole Navigation Optimizer & Safety Post-Processing
    # --------------------------------------------------------------------------
    optimized_steps = _pass5_optimize_peephole(raw_steps, effective_opt)

    # --------------------------------------------------------------------------
    # CONSTRUCT & VALIDATE KUTOMOTO WORKFLOW
    # --------------------------------------------------------------------------
    workflow = KutomotoWorkflow(
        schema_version="1.0.0",
        id=layout_model.id,
        name=layout_model.name,
        description=layout_model.description,
        copyright="Copyrights reserved to 90Studio",
        source_mode=SourceMode.VISUAL_DESIGNER_GENERATED,
        target_application=layout_model.target_application,
        execution_settings=layout_model.execution_settings,
        variables=[
            WorkflowVariable.model_validate(v) if isinstance(v, dict) else v
            for v in getattr(layout_model, "variables", [])
        ],
        designer_metadata=DesignerMetadata(
            canvas_width=layout_model.canvas.width,
            canvas_height=layout_model.canvas.height,
            background_image_path=layout_model.canvas.background_image_path,
            box_count=len(layout_model.boxes),
        ),
        steps=optimized_steps,
    )

    return workflow


def compile_visual_boxes_to_workflow(
    layout: Union[VisualFormLayout, Dict[str, Any]],
    traversal_mode: str = "coordinate_targeted",
    **kwargs: Any,
) -> KutomotoWorkflow:
    """
    Backward-compatible alias for compile_visual_layout_to_workflow.
    Maps traversal_mode='tab_chained' to optimization.click_to_tab = True.
    """
    opt = kwargs.get("optimization")
    if opt is None:
        click_to_tab = traversal_mode == "tab_chained"
        opt = PeepholeOptimizationConfig(click_to_tab=click_to_tab)
    return compile_visual_layout_to_workflow(layout, optimization=opt)
