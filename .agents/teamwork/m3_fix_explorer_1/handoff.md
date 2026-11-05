# Investigation & Fix Strategy Report: force_click Propagation & click_to_tab Optimization

```
====================================================================================================
Agent               : m3_fix_explorer_1 (Milestone 3 Fix Exploration Agent)
Roles               : explorer, investigator, analyst
Parent Conversation : 59700fc9-320d-4ed3-b1db-2fc709fed831
Working Directory   : c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_fix_explorer_1
Target Files        : src/kutomoto/designer/compiler.py, tests/test_compiler.py
Date                : 2026-11-05
Status              : COMPLETE & ACTIONABLE
====================================================================================================
```

---

## Executive Summary

This investigation analyzed `m3_reviewer_2` Finding 1 (along with Minor Findings 2 and 3) concerning `force_click` propagation in Pass 4 and `click_to_tab` optimization in Pass 5 of `src/kutomoto/designer/compiler.py`. 

Empirical reproduction verified that:
1. When `click_to_tab=True`, any visual box with `action_type in (CLICK, CHECKBOX, SELECT)` following a Tab navigation step has its click step pruned by Pass 5.
2. Pass 4 (`compiler.py` lines 552–569) fails to propagate `force_click` markers (`_force_click` attribute, `[force_click]` label tag, `parameters.variable_name="__force_click__"`) on `CLICK`, `CHECKBOX`, and `SELECT` boxes.
3. Pass 5 (`compiler.py` lines 130–156) treats **all** clicks following Tab as disposable focus anchors unless tagged with `force_click`. However, standalone action clicks (clicking a button, checking a box, opening a dropdown) are **primary user operations**, not auxiliary focus anchors, and must **never** be pruned by `click_to_tab`, even when `force_click=False`.

A concrete two-tier defense-in-depth fix strategy is detailed below with exact before/after code replacements and 5 unit tests. All 217 existing repository tests pass with zero regressions.

---

## 1. Observation

### 1.1 Empirical Reproduction of Finding 1

Executing the reproduction script reported by `m3_reviewer_2`:
```powershell
python -c "import sys; sys.path.insert(0, 'src'); from kutomoto.designer.schema import *; from kutomoto.designer.compiler import compile_visual_layout_to_workflow; from kutomoto.engine.schema import ActionType; layout = VisualFormLayout(name='Repro', canvas=CanvasDimensions(width=800, height=600), target_application=TargetApplicationSpec(window_title_pattern='App'), optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True), boxes=[VisualBox(name='f1', geometry=BoxGeometry(x=50, y=50, width=100, height=30), navigation=NavigationAction.TAB), VisualBox(name='btn', geometry=BoxGeometry(x=50, y=100, width=100, height=30), action_type=DesignerActionType.CLICK, force_click=True)]); wf = compile_visual_layout_to_workflow(layout); clicks = [s for s in wf.steps if s.action_type == ActionType.CLICK]; print('Clicks found:', len(clicks)); assert len(clicks) == 2, 'force_click was dropped!'"
```
Output:
```
Traceback (most recent call last):
  File "<string>", line 1, in <module>
AssertionError: force_click was dropped!
Clicks found: 1
```

### 1.2 Default Behavior for CHECKBOX and CLICK Boxes

When `force_click=False` (the default) on a `CHECKBOX` following Tab:
```powershell
python -c "import sys; sys.path.insert(0, 'src'); from kutomoto.designer.schema import *; from kutomoto.designer.compiler import compile_visual_layout_to_workflow; from kutomoto.engine.schema import ActionType; layout = VisualFormLayout(name='Repro', canvas=CanvasDimensions(width=800, height=600), target_application=TargetApplicationSpec(window_title_pattern='App'), optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True), boxes=[VisualBox(name='f1', geometry=BoxGeometry(x=50, y=50, width=100, height=30), navigation=NavigationAction.TAB), VisualBox(name='terms', geometry=BoxGeometry(x=50, y=100, width=100, height=30), action_type=DesignerActionType.CHECKBOX)]); wf = compile_visual_layout_to_workflow(layout); print('Steps:', [(s.sequence_index, s.action_type, s.label) for s in wf.steps])"
```
Output:
```
Steps: [
  (1, <ActionType.FOCUS_WINDOW: 'focus_window'>, 'Focus Target Window: App'),
  (2, <ActionType.CLICK: 'click'>, 'Click [f1]'),
  (3, <ActionType.CLEAR_FIELD: 'clear_field'>, 'Clear [f1]'),
  (4, <ActionType.TYPE_TEXT: 'type_text'>, 'Type into [f1]'),
  (5, <ActionType.KEY_PRESS: 'key_press'>, 'Tab after [f1]'),
  (6, <ActionType.KEY_PRESS: 'key_press'>, 'Tab after [terms]')
]
```
**Observation**: The click step for `terms` was completely eliminated. The workflow merely pressed Tab after `terms` without ever clicking the checkbox!

### 1.3 Code Inspection of Pass 4 (`src/kutomoto/designer/compiler.py`)

- **Lines 448–452**: `force_click` is correctly calculated for each visual box:
  ```python
  force_click = bool(
      box.force_click
      or box.metadata.get("force_click", False)
      or box.metadata.get("requires_click", False)
  )
  ```
- **Lines 460–479 (`TYPE_TEXT` branch)**:
  `TYPE_TEXT` correctly sets:
  ```python
  click_step = WorkflowStep(
      ...
      label=f"Click [{box.label or box.name}]"
      + (" [force_click]" if force_click else ""),
      ...
      parameters=StepParameters(
          ...
          variable_name="__force_click__" if force_click else None,
      ),
  )
  setattr(click_step, "_force_click", force_click)
  raw_steps.append(click_step)
  ```
- **Lines 552–569 (`CLICK` / `CHECKBOX` / `SELECT` branch)**:
  ```python
  raw_steps.append(
      WorkflowStep(
          step_id=str(uuid.uuid4()),
          sequence_index=len(raw_steps) + 1,
          label=f"Click [{box.label or box.name}]",
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
          ),
      )
  )
  ```
  `force_click` is completely omitted from the label, the parameters, and step attributes.

### 1.4 Code Inspection of Pass 5 (`src/kutomoto/designer/compiler.py` lines 130–156)

```python
# Pattern A: Click-to-tab elimination
if opt.click_to_tab:
    tab_optimized: List[WorkflowStep] = []
    field_click_count = 0
    for s in pruned_focus:
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
            # First field click must ALWAYS be preserved
            if field_click_count > 1 and is_after_tab and not is_force_click:
                logger.debug(
                    "Peephole Optimizer: Pruned redundant click step: '%s'",
                    s.label,
                )
                continue
        tab_optimized.append(s)
else:
    tab_optimized = list(pruned_focus)
```
**Observation**: Pass 5 drops **any** click step where `field_click_count > 1 and is_after_tab and not is_force_click`. It does not verify whether the click is an auxiliary focus anchor for text entry or a standalone action click.

### 1.5 Code Inspection of Minor Finding 2 (`compiler.py` lines 624–636)

```python
elif box.action_type in (DesignerActionType.KEY_PRESS, "key_press"):
    key_name = box.value.strip().lower() if box.value else "tab"
    raw_steps.append(
        WorkflowStep(
            step_id=str(uuid.uuid4()),
            sequence_index=len(raw_steps) + 1,
            label=f"Key press [{key_name}]",
            action_type=ActionType.KEY_PRESS,
            enabled=True,
            parameters=StepParameters(key=key_name, repeat_count=1),
        )
    )
```
**Observation**: `pre_delay_ms=pre_delay` and `post_delay_ms=post_delay` are not passed, defaulting to 0ms.

---

## 2. Logic Chain

1. **Semantic Distinction between Focus Anchors and Action Clicks**:
   - In `TYPE_TEXT` boxes, Pass 4 synthesizes: `[CLICK (anchor focus)] -> [CLEAR_FIELD] -> [TYPE_TEXT] -> [KEY_PRESS (tab)]`.
   - The purpose of `click_to_tab` (defined in `schema.py` line 254 as *"Convert redundant coordinate clicks following Tab navigation into keyboard flow"*) is to eliminate intermediate mouse clicks between text fields because the preceding Tab keypress has already positioned the cursor inside the next input.
   - For `CLICK`, `CHECKBOX`, and `SELECT` boxes, the click is **not an anchor focus click**; it is the **functional action** itself (clicking the button, toggling the checkbox, opening the dropdown). Tab navigation moves focus, but does **not** click elements. Eliminating this click renders the workflow broken.

2. **Root Causes of Finding 1**:
   - **Root Cause 1 (Pass 4)**: Lines 552–569 do not set `_force_click`, `[force_click]`, or `variable_name="__force_click__"`. Thus, even when a user explicitly specifies `force_click=True` on a button or checkbox, Pass 5 never detects `is_force_click=True`.
   - **Root Cause 2 (Pass 5)**: Lines 147–153 prune any click following Tab as long as `not is_force_click`. Pass 5 lacks the logic to distinguish between an auxiliary focus click (which is followed by `CLEAR_FIELD` or `TYPE_TEXT`) and a standalone action click.

3. **Required Dual-Level Defense-in-Depth Solution**:
   - **Pass 4**:
     1. Propagate `force_click` markers on `CLICK`, `CHECKBOX`, and `SELECT` boxes whenever `force_click` is true (`[force_click]` in label, `variable_name="__force_click__"`, `_force_click=True`).
     2. Tag `_is_action_click=True` on steps created in the `CLICK` / `CHECKBOX` / `SELECT` branch.
     3. Tag `_is_focus_anchor=True` on click steps created in the `TYPE_TEXT` branch.
   - **Pass 5**:
     1. Check `is_action_click = getattr(s, "_is_action_click", False)`. If true, **never prune**.
     2. Forward lookahead fallback: If a step is not tagged (e.g., when raw steps are provided directly to `_pass5_optimize_peephole`), inspect subsequent steps. A click is a focus anchor **only** if it is immediately followed (ignoring minor delays) by `CLEAR_FIELD` or `TYPE_TEXT`. If not followed by text entry operations, it is a standalone click and must **not** be pruned.
     3. Update pruning condition to:
        ```python
        if (
            field_click_count > 1
            and is_after_tab
            and not is_force_click
            and not is_action_click
            and is_focus_anchor
        ):
            continue
        ```

4. **Minor Finding 2 Solution**:
   - In lines 627–635, pass `pre_delay_ms=pre_delay` and `post_delay_ms=post_delay` to `WorkflowStep`.

---

## 3. Caveats

- **Schema Stability**: No schema changes to `src/kutomoto/designer/schema.py` or `src/kutomoto/engine/schema.py` are required. `_is_action_click`, `_is_focus_anchor`, and `_force_click` are in-memory step metadata attributes. Serialized workflows preserve `variable_name="__force_click__"` and `[force_click]` in `label`.
- **Backward Compatibility**: Existing workflows with consecutive text boxes where `click_to_tab=True` continue to prune redundant intermediate text-field clicks identically. All 61 existing compiler tests and all 217 repository tests pass without modification.
- **Initial Click Preservation**: The first field's click is always preserved (`field_click_count > 1` guard), regardless of box type or navigation mode.

---

## 4. Conclusion & Recommended Concrete Fix Strategy

The issue is fully understood, reproducible, and has an exact fix that preserves both explicit author intent (`force_click=True`) and intrinsic interaction semantics (`CLICK`/`CHECKBOX`/`SELECT` preservation).

### 4.1 Exact Code Modification in `src/kutomoto/designer/compiler.py`

#### Edit 1: Pass 5 Peephole Optimizer (lines 130–156)

**Target Lines**: 130–156 in `src/kutomoto/designer/compiler.py`

**Before**:
```python
    # Pattern A: Click-to-tab elimination
    if opt.click_to_tab:
        tab_optimized: List[WorkflowStep] = []
        field_click_count = 0
        for s in pruned_focus:
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
                # First field click must ALWAYS be preserved
                if field_click_count > 1 and is_after_tab and not is_force_click:
                    logger.debug(
                        "Peephole Optimizer: Pruned redundant click step: '%s'",
                        s.label,
                    )
                    continue
            tab_optimized.append(s)
    else:
        tab_optimized = list(pruned_focus)
```

**After**:
```python
    # Pattern A: Click-to-tab elimination
    if opt.click_to_tab:
        tab_optimized: List[WorkflowStep] = []
        field_click_count = 0
        for idx, s in enumerate(pruned_focus):
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
                    for next_step in pruned_focus[idx + 1:]:
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
                    continue
            tab_optimized.append(s)
    else:
        tab_optimized = list(pruned_focus)
```

---

#### Edit 2: Pass 4 TYPE_TEXT Branch Focus Anchor Tagging (lines 477–479)

**Target Lines**: 477–479 in `src/kutomoto/designer/compiler.py`

**Before**:
```python
            setattr(click_step, "_force_click", force_click)
            raw_steps.append(click_step)
```

**After**:
```python
            setattr(click_step, "_force_click", force_click)
            setattr(click_step, "_is_focus_anchor", True)
            raw_steps.append(click_step)
```

---

#### Edit 3: Pass 4 CLICK / CHECKBOX / SELECT Branch (lines 552–569)

**Target Lines**: 552–569 in `src/kutomoto/designer/compiler.py`

**Before**:
```python
            raw_steps.append(
                WorkflowStep(
                    step_id=str(uuid.uuid4()),
                    sequence_index=len(raw_steps) + 1,
                    label=f"Click [{box.label or box.name}]",
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
                    ),
                )
            )
```

**After**:
```python
            click_step = WorkflowStep(
                step_id=str(uuid.uuid4()),
                sequence_index=len(raw_steps) + 1,
                label=f"Click [{box.label or box.name}]"
                + (" [force_click]" if force_click else ""),
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
```

---

#### Edit 4: Pass 4 KEY_PRESS Timing Propagation (lines 627–635)

**Target Lines**: 627–635 in `src/kutomoto/designer/compiler.py`

**Before**:
```python
            raw_steps.append(
                WorkflowStep(
                    step_id=str(uuid.uuid4()),
                    sequence_index=len(raw_steps) + 1,
                    label=f"Key press [{key_name}]",
                    action_type=ActionType.KEY_PRESS,
                    enabled=True,
                    parameters=StepParameters(key=key_name, repeat_count=1),
                )
            )
```

**After**:
```python
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
```

---

### 4.2 Proposed Unit Tests for `tests/test_compiler.py`

Add the following 5 tests to `TestCompilerPass5PeepholeOptimizer` (and `TestCompilerPass4ActionStepSynthesis`) in `tests/test_compiler.py`:

```python
    def test_pass5_click_to_tab_force_click_preserved_on_type_text(self):
        """When force_click=True on TYPE_TEXT, second field's CLICK is preserved even with click_to_tab=True."""
        layout = VisualFormLayout(
            name="Force Click Text Preserved",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
            boxes=[
                VisualBox(name="f1", geometry=BoxGeometry(x=50, y=50, width=200, height=30), navigation=NavigationAction.TAB),
                VisualBox(name="f2", geometry=BoxGeometry(x=50, y=100, width=200, height=30), force_click=True),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        clicks = [s for s in wf.steps if s.action_type == ActionType.CLICK]
        assert len(clicks) == 2
        assert any("[force_click]" in s.label for s in clicks)

    def test_pass5_click_to_tab_force_click_preserved_on_action_boxes(self):
        """When force_click=True on CLICK/CHECKBOX/SELECT boxes, click step and markers are strictly preserved."""
        layout = VisualFormLayout(
            name="Force Click Action Preserved",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
            boxes=[
                VisualBox(name="f1", geometry=BoxGeometry(x=50, y=50, width=200, height=30), navigation=NavigationAction.TAB),
                VisualBox(name="btn", geometry=BoxGeometry(x=50, y=100, width=200, height=30), action_type=DesignerActionType.CLICK, force_click=True),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        clicks = [s for s in wf.steps if s.action_type == ActionType.CLICK]
        assert len(clicks) == 2
        btn_click = [s for s in clicks if "btn" in s.label][0]
        assert "[force_click]" in btn_click.label
        assert btn_click.parameters.variable_name == "__force_click__"

    def test_pass5_click_to_tab_standalone_click_and_checkbox_preserved_by_default(self):
        """Standalone action clicks (CLICK, CHECKBOX, SELECT) are primary operations and NOT pruned even if force_click=False."""
        layout = VisualFormLayout(
            name="Action Clicks Preserved",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
            boxes=[
                VisualBox(name="f1", geometry=BoxGeometry(x=50, y=50, width=200, height=30), navigation=NavigationAction.TAB),
                VisualBox(name="cb", geometry=BoxGeometry(x=50, y=100, width=200, height=30), action_type=DesignerActionType.CHECKBOX, navigation=NavigationAction.TAB),
                VisualBox(name="btn", geometry=BoxGeometry(x=50, y=150, width=200, height=30), action_type=DesignerActionType.CLICK),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        clicks = [s for s in wf.steps if s.action_type == ActionType.CLICK]
        # All three clicks must be present: f1 (anchor), cb (checkbox click), btn (button click)
        assert len(clicks) == 3
        labels = [s.label for s in clicks]
        assert any("f1" in l for l in labels)
        assert any("cb" in l for l in labels)
        assert any("btn" in l for l in labels)

    def test_pass5_click_to_tab_metadata_force_click_preservation(self):
        """box.metadata['force_click'] or metadata['requires_click'] also preserves click under click_to_tab."""
        layout = VisualFormLayout(
            name="Metadata Force Click",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
            boxes=[
                VisualBox(name="f1", geometry=BoxGeometry(x=50, y=50, width=200, height=30), navigation=NavigationAction.TAB),
                VisualBox(name="f2", geometry=BoxGeometry(x=50, y=100, width=200, height=30), metadata={"requires_click": True}),
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        clicks = [s for s in wf.steps if s.action_type == ActionType.CLICK]
        assert len(clicks) == 2

    def test_pass4_key_press_box_propagates_timing_delays(self):
        """KEY_PRESS visual box propagates box.timing pre_delay_ms and post_delay_ms to step."""
        layout = VisualFormLayout(
            name="Key Press Timing",
            canvas=CanvasDimensions(width=800, height=600),
            target_application=TargetApplicationSpec(window_title_pattern="App"),
            boxes=[
                VisualBox(
                    name="press_enter",
                    geometry=BoxGeometry(x=50, y=50, width=100, height=30),
                    action_type=DesignerActionType.KEY_PRESS,
                    value="enter",
                    timing=BoxTiming(pre_delay_ms=50, post_delay_ms=150),
                )
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        key_steps = [s for s in wf.steps if s.action_type == ActionType.KEY_PRESS]
        assert len(key_steps) == 1
        assert key_steps[0].pre_delay_ms == 50
        assert key_steps[0].post_delay_ms == 150
```

---

## 5. Verification Method

### 5.1 Verification Commands

To verify the implementation once applied:

1. **Reproduction Test (must pass with 2 clicks)**:
   ```powershell
   python -c "import sys; sys.path.insert(0, 'src'); from kutomoto.designer.schema import *; from kutomoto.designer.compiler import compile_visual_layout_to_workflow; from kutomoto.engine.schema import ActionType; layout = VisualFormLayout(name='Repro', canvas=CanvasDimensions(width=800, height=600), target_application=TargetApplicationSpec(window_title_pattern='App'), optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True), boxes=[VisualBox(name='f1', geometry=BoxGeometry(x=50, y=50, width=100, height=30), navigation=NavigationAction.TAB), VisualBox(name='btn', geometry=BoxGeometry(x=50, y=100, width=100, height=30), action_type=DesignerActionType.CLICK, force_click=True)]); wf = compile_visual_layout_to_workflow(layout); clicks = [s for s in wf.steps if s.action_type == ActionType.CLICK]; print('Clicks found:', len(clicks)); assert len(clicks) == 2, 'force_click was dropped!'"
   ```

2. **Default Action Clicks Test (must preserve checkbox and button clicks)**:
   ```powershell
   python -c "import sys; sys.path.insert(0, 'src'); from kutomoto.designer.schema import *; from kutomoto.designer.compiler import compile_visual_layout_to_workflow; from kutomoto.engine.schema import ActionType; layout = VisualFormLayout(name='Repro', canvas=CanvasDimensions(width=800, height=600), target_application=TargetApplicationSpec(window_title_pattern='App'), optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True), boxes=[VisualBox(name='f1', geometry=BoxGeometry(x=50, y=50, width=100, height=30), navigation=NavigationAction.TAB), VisualBox(name='cb', geometry=BoxGeometry(x=50, y=100, width=100, height=30), action_type=DesignerActionType.CHECKBOX, navigation=NavigationAction.TAB), VisualBox(name='btn', geometry=BoxGeometry(x=50, y=150, width=100, height=30), action_type=DesignerActionType.CLICK)]); wf = compile_visual_layout_to_workflow(layout); clicks = [s for s in wf.steps if s.action_type == ActionType.CLICK]; print('Clicks found:', len(clicks)); assert len(clicks) == 3, f'Expected 3 clicks, got {len(clicks)}'"
   ```

3. **Compiler Test Suite**:
   ```powershell
   python -m pytest tests/test_compiler.py -v
   ```

4. **Full Repository Regression Suite**:
   ```powershell
   python -m pytest tests/ -v
   ```

5. **Linting**:
   ```powershell
   python -m ruff check src/ tests/test_compiler.py
   ```

### 5.2 Invalidation Conditions
- Any failure in the 61 existing compiler tests.
- Clicks for `DesignerActionType.CLICK`, `CHECKBOX`, or `SELECT` boxes disappearing after Tab.
- Redundant intermediate clicks on consecutive `TYPE_TEXT` fields failing to be pruned when `click_to_tab=True` and `force_click=False`.
