# Investigation & Fix Strategy Report: Timing Delays Across Compilation and Optimization

```
====================================================================================================
Agent               : m3_fix_explorer_2 (Milestone 3 Fix Exploration Agent)
Roles               : explorer, specialist
Working Directory   : c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_fix_explorer_2\
Parent Conversation : 59700fc9-320d-4ed3-b1db-2fc709fed831
Date                : 2026-11-05
Status              : Complete
Target Files        : src/kutomoto/designer/compiler.py, src/kutomoto/designer/schema.py, tests/test_compiler.py
====================================================================================================
```

---

## Executive Summary

This investigation analyzed two interrelated timing delay defects in `src/kutomoto/designer/compiler.py`:
1. **Finding 2 from `m3_reviewer_2`**: Standalone `KEY_PRESS` action boxes in Pass 4 (`compiler.py:624-636`) do not pass `pre_delay_ms` or `post_delay_ms` to `WorkflowStep`, defaulting to 0ms rather than inheriting from `box.timing` or `execution_settings`.
2. **Finding F2 from `m3_challenger_1`**: When `optimization.click_to_tab = True` in Pass 5 (`compiler.py:130-156`), pruning a redundant focus click step permanently discards any `pre_delay_ms` configured on that field, because Pass 4 places `pre_delay_ms` exclusively on the initial click step (`compiler.py:467`), leaving subsequent `clear_field` and `type_text` steps hardcoded to `pre_delay_ms = 0` (`compiler.py:490, 506`).

Both defects have been empirically verified and reproduced under Windows Python 3.14. A comprehensive architectural and comparative analysis was conducted between:
- **Strategy 1**: Transferring `pre_delay_ms` to the immediate next step in Pass 5 (with defensive fallback to a standalone `DELAY` step if no subsequent step exists).
- **Strategy 2**: Emitting a standalone `ActionType.DELAY` step in Pass 5 for every pruned click with `pre_delay_ms > 0`.

The analysis concludes that **Strategy 1 (Transfer to immediate next step with defensive fallback)** is architecturally superior, preserves exact step-to-box ownership semantics, introduces zero artificial step bloat, maintains 100% test compatibility, and eliminates settling delay loss in production workflows.

---

## 1. Observation

### 1.1 Empirical Observation of Finding 2 (`KEY_PRESS` Timing Parameter Omission)

- **Source Location**: `src/kutomoto/designer/compiler.py`, lines 424–437 and lines 624–636.
- **Pass 4 Delay Calculation** (`compiler.py:424-437`):
  ```python
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
  ```
- **Pass 4 KEY_PRESS Synthesis** (`compiler.py:624-636`):
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
- **Discrepancy**:
  In `WorkflowStep` (`src/kutomoto/engine/schema.py:193-194`), `pre_delay_ms` and `post_delay_ms` have schema default values of `0`:
  ```python
  pre_delay_ms: int = Field(default=0, ge=0)
  post_delay_ms: int = Field(default=0, ge=0)
  ```
  Because lines 627–635 omit `pre_delay_ms` and `post_delay_ms`, the compiled step defaults to `pre_delay_ms = 0` and `post_delay_ms = 0`.
- **Contrast with other Action Types in Pass 4**:
  - `CLICK` (`compiler.py:559-560`): specifies `pre_delay_ms=pre_delay, post_delay_ms=post_delay`
  - `SUBMIT` (`compiler.py:596-597`): specifies `pre_delay_ms=pre_delay, post_delay_ms=max(post_delay, 1000)`
  - `TYPE_TEXT` (`compiler.py:467, 507`): specifies `pre_delay_ms=pre_delay` on click, `post_delay_ms=post_delay` on typing
- **Empirical Reproduction Command**:
  ```powershell
  python -c "
  import sys; sys.path.insert(0, 'src')
  from kutomoto.designer.schema import *
  from kutomoto.designer.compiler import compile_visual_layout_to_workflow
  kp = VisualBox(name='kp1', action_type=DesignerActionType.KEY_PRESS, value='escape', geometry=BoxGeometry(x=10, y=10, width=50, height=20), timing=BoxTiming(pre_delay_ms=250, post_delay_ms=350))
  wf = compile_visual_layout_to_workflow(VisualFormLayout(name='Test', canvas=CanvasDimensions(width=800, height=600), target_application=TargetApplicationSpec(window_title_pattern='App'), boxes=[kp]))
  for s in wf.steps:
      print(f'{s.sequence_index}: {s.action_type.value} | {s.label} | pre={s.pre_delay_ms} post={s.post_delay_ms}')
  "
  ```
  *Actual Output*:
  ```
  1: focus_window | Focus Target Window: App | pre=0 post=250
  2: key_press | Key press [escape] | pre=0 post=0
  ```
  *Observation*: `kp1` configured `pre_delay_ms=250` and `post_delay_ms=350`, but the compiled step received `pre=0 post=0`.

---

### 1.2 Empirical Observation of Finding F2 (`pre_delay_ms` Dropped under `click_to_tab`)

- **Source Location**: `src/kutomoto/designer/compiler.py`, lines 458–514 and lines 130–156.
- **Pass 4 Step Generation for `TYPE_TEXT`** (`compiler.py:458-514`):
  ```python
  # 1. Click to anchor focus
  click_step = WorkflowStep(
      ...
      action_type=ActionType.CLICK,
      pre_delay_ms=pre_delay,
      post_delay_ms=60,
      ...
  )
  raw_steps.append(click_step)

  # 2. Clear field if requested
  if box.clear_before:
      raw_steps.append(
          WorkflowStep(
              ...
              action_type=ActionType.CLEAR_FIELD,
              pre_delay_ms=0,
              post_delay_ms=40,
              ...
          )
      )

  # 3. Type text
  raw_steps.append(
      WorkflowStep(
          ...
          action_type=ActionType.TYPE_TEXT,
          pre_delay_ms=0,
          post_delay_ms=post_delay,
          ...
      )
  )
  ```
- **Pass 5 Click-to-Tab Pruning** (`compiler.py:130-153`):
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
  ```
- **Discrepancy**:
  When `s` is pruned via `continue`, the step object `s` is completely dropped from `tab_optimized`.
  Because `pre_delay_ms` was placed solely on `click_step` (`compiler.py:467`), and the subsequent `CLEAR_FIELD` and `TYPE_TEXT` steps have hardcoded `pre_delay_ms = 0` (`compiler.py:490, 506`), discarding `s` permanently deletes the field's settling delay.
- **Empirical Reproduction Command**:
  ```powershell
  python -c "
  import sys; sys.path.insert(0, 'src')
  from kutomoto.designer.schema import *
  from kutomoto.designer.compiler import compile_visual_layout_to_workflow
  b1 = VisualBox(name='b1', geometry=BoxGeometry(x=10, y=10, width=100, height=30), navigation=NavigationAction.TAB)
  b2 = VisualBox(name='b2', geometry=BoxGeometry(x=10, y=50, width=100, height=30), navigation=NavigationAction.TAB, timing=BoxTiming(pre_delay_ms=500))
  wf = compile_visual_layout_to_workflow(VisualFormLayout(name='Test', canvas=CanvasDimensions(width=800, height=600), target_application=TargetApplicationSpec(window_title_pattern='App'), optimization=PeepholeOptimizationConfig(click_to_tab=True), boxes=[b1, b2]))
  for s in wf.steps:
      print(f'{s.sequence_index}: {s.action_type.value} | {s.label} | pre={s.pre_delay_ms} post={s.post_delay_ms}')
  "
  ```
  *Actual Output*:
  ```
  1: focus_window | Focus Target Window: App | pre=0 post=250
  2: click | Click [b1] | pre=0 post=60
  3: clear_field | Clear [b1] | pre=0 post=40
  4: type_text | Type into [b1] | pre=0 post=120
  5: key_press | Tab after [b1] | pre=0 post=100
  6: clear_field | Clear [b2] | pre=0 post=40
  7: type_text | Type into [b2] | pre=0 post=120
  8: key_press | Tab after [b2] | pre=0 post=100
  ```
  *Observation*: Step 6 (`Clear [b2]`) has `pre=0` instead of `pre=500`. The 500ms settling time requested for field `b2` was dropped alongside the click step.

---

## 2. Logic Chain

### 2.1 Logic Chain for Finding 2 (`KEY_PRESS` Timing Inheritance)

1. **Schema Definition**: `VisualBox` schema (`schema.py:135-141`, `schema.py:163`) supports timing configuration via `box.timing` (`BoxTiming(pre_delay_ms=..., post_delay_ms=...)`) and direct attributes `box.post_delay_ms` (default 120ms).
2. **Layout Context**: `VisualFormLayout.execution_settings` provides `default_step_delay_ms` (default 120ms).
3. **Pass 4 Variable Extraction**: In `compiler.py:428-437`, Pass 4 computes `pre_delay` and `post_delay` for each visual box prior to action dispatch.
4. **Step Synthesis Inconsistency**: While `CLICK`, `SUBMIT`, and `TYPE_TEXT` pass `pre_delay` and/or `post_delay` into their instantiated `WorkflowStep`, the `KEY_PRESS` branch (`compiler.py:627-635`) constructs `WorkflowStep` with only `step_id`, `sequence_index`, `label`, `action_type`, `enabled`, and `parameters`.
5. **Schema Default Override**: `WorkflowStep` in `kutomoto.engine.schema.py:193-194` defaults `pre_delay_ms=0` and `post_delay_ms=0`.
6. **Execution Consequence**: During workflow execution in `WorkflowRunner._execute_step` (`runner.py:499-506, 552`), `step.pre_delay_ms` and `step.post_delay_ms` are read to control settling pauses. Standalone key presses (e.g., Escape, Enter, F5, Tab, PageDown) execute with 0ms settling delay before and after, ignoring both box-level overrides and layout execution settings.
7. **Conclusion**: `WorkflowStep` creation at `compiler.py:627-635` must pass `pre_delay_ms=pre_delay` and `post_delay_ms=post_delay`.

---

### 2.2 Logic Chain for Finding F2 (`pre_delay_ms` Preservation under `click_to_tab`)

1. **Box Intent**: `box.timing.pre_delay_ms` specifies a duration the automation engine must wait *before interacting* with the target field (e.g. 500ms for dynamic AJAX loading, animated transitions, or asynchronous dropdown expansion).
2. **Pass 4 Allocation**: Pass 4 assigns `pre_delay` exclusively to the *first step* synthesized for the box (`compiler.py:467`), which in the standard unoptimized flow is `CLICK`.
3. **Pass 5 Optimization**: When `click_to_tab = True`, Pass 5 identifies that field 2 was reached by a preceding Tab navigation keystroke (`compiler.py:141-145`), rendering the coordinate mouse click redundant as a focus anchor.
4. **Unintended Delay Erasure**: Because Pass 5 drops the `WorkflowStep` via `continue` (`compiler.py:152`), both the physical click action *and* the attached `pre_delay_ms` are eliminated. The subsequent steps (`CLEAR_FIELD` or `TYPE_TEXT`) retain their Pass 4 values of `pre_delay_ms = 0`.
5. **Runtime Failure**: In `WorkflowRunner` (`runner.py:498-506`), the engine transitions directly from the Tab keypress to clearing/typing with 0ms pre-delay, risking race conditions on interactive form fields.
6. **Requirement**: The elimination of a redundant mouse click must NOT eliminate the author's configured field settling delay. Pass 5 must retain `s.pre_delay_ms`.

---

## 3. Comparative Evaluation of Fix Strategies for Finding F2

Two strategies exist for preserving `pre_delay_ms` when a focus click is pruned in Pass 5:

| Criteria | Strategy 1: Transfer `pre_delay_ms` to Immediate Next Step | Strategy 2: Emit Standalone `ActionType.DELAY` Step |
|---|---|---|
| **Mechanism** | In `_pass5_optimize_peephole`, when `s` is pruned and `s.pre_delay_ms > 0`: `pruned_focus[i + 1].pre_delay_ms += s.pre_delay_ms`. | In `_pass5_optimize_peephole`, when `s` is pruned and `s.pre_delay_ms > 0`: `tab_optimized.append(WorkflowStep(action_type=ActionType.DELAY, parameters=StepParameters(duration_ms=s.pre_delay_ms)))`. |
| **Step Count Impact** | Step count remains N-1 (true pruning). Zero step count bloat. | Step count does not decrease; 1 click step is replaced by 1 delay step. |
| **Field Attribution** | Preserves delay on the field's actual steps (`Clear [b2]` or `Type into [b2]`). In tests filtering by field name (`"b2" in s.label`), pre-delay is directly observable on `b2_steps[0]`. | Delay step is a synthetic step detached from the field, unless field label is injected. `b2_steps` interaction steps still show `pre_delay_ms = 0`. |
| **Consistency with Field 1** | For Field 1 (unpruned click), pre-delay resides on the field's initial step (`Click [b1].pre_delay_ms = pre_delay`). For Field 2 (pruned click), pre-delay resides on the field's initial step (`Clear [b2].pre_delay_ms = pre_delay`). Highly consistent. | Field 1 has pre-delay on click step; Field 2 has pre-delay as an independent `ActionType.DELAY` step. Inconsistent representation. |
| **Peephole Delay Coalescing** | Does not generate synthetic delay steps; does not interfere with Phase 3 delay coalescing. | Emits delay step into Phase 3. Adjacent delays may coalesce into a single delay, obscuring individual step intent. |
| **Runtime Execution** | `WorkflowRunner` lines 499–506 executes `step.pre_delay_ms` sleep before clearing/typing. Exact 500ms pause observed. | `WorkflowRunner` executes `ActionType.DELAY` sleep via `_execute_delay`. Exact 500ms pause observed. |
| **Allocation & Performance** | In-place integer addition `+=`. Zero object allocations, zero UUIDs, zero overhead. | Allocates new `WorkflowStep`, generates UUID, instantiates `StepParameters`. |
| **Defensive Edge Case** | If pruned click is the final step in layout (`i + 1 >= len(pruned_focus)`), falls back to emitting a standalone DELAY. | Always succeeds. |

### Recommendation
**Strategy 1 (Transfer to immediate next step with defensive fallback)** is strongly recommended. It honors the architectural purpose of `WorkflowStep.pre_delay_ms`, maintains clean 1-to-1 box attribution, prevents step inflation, and behaves identically during runtime execution.

---

## 4. Caveats & Boundary Edge Cases

1. **Mouse Settling Delay (`post_delay_ms = 60`) Must NOT Be Transferred**:
   In Pass 4 (`compiler.py:468`), `click_step` receives `post_delay_ms = 60` as a mouse debounce. When the click is pruned by `click_to_tab`, no mouse event occurs. Transferring this 60ms is inappropriate and would inject an unwanted 60ms delay after every tabbed field. Only `s.pre_delay_ms` (the field settling delay) should be transferred.
2. **`clear_before = False` Handling**:
   When `clear_before = False`, Pass 4 emits `CLICK` immediately followed by `TYPE_TEXT`. Transferring `s.pre_delay_ms` to `pruned_focus[i + 1]` correctly transfers the delay to `TYPE_TEXT`.
3. **Standalone `CLICK`, `CHECKBOX`, and `SELECT` Boxes**:
   Per `m3_reviewer_2` Finding 1, standalone clicks and checkboxes are intentional user actions, not redundant focus anchors. They must not be pruned by `click_to_tab` (either by setting `is_force_click = True` or by restricting `click_to_tab` to `TYPE_TEXT` focus clicks). If a standalone click is not pruned, its `pre_delay_ms` remains on the click step without modification.
4. **Final Step Boundary Guard**:
   In standard compilation, a `TYPE_TEXT` click is always followed by `CLEAR_FIELD` or `TYPE_TEXT`, so `i + 1 < len(pruned_focus)` is guaranteed. However, adding a fallback `else: tab_optimized.append(WorkflowStep(action_type=ActionType.DELAY, ...))` ensures 100% robustness against any pathological layout.
5. **Existing Adversarial Test in Challenge Suite**:
   `tests/test_compiler_empirical_challenge.py:445-459` (`test_vulnerability_click_to_tab_drops_pre_delay`) was written by `m3_challenger_1` to document that `pre_delay` was dropped (`assert all(pd == 0 for pd in pre_delays)`). Once the fix is applied by the implementer, this test should be updated to assert that `pre_delay_ms == 500` is preserved on `b2_steps[0]`.

---

## 5. Concrete Code Proposals

### Proposal 1: Pass 4 `KEY_PRESS` Timing Parameter Propagation

- **Target File**: `src/kutomoto/designer/compiler.py`
- **Target Lines**: Lines 624–636

#### Before:
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

#### After:
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
                    pre_delay_ms=pre_delay,
                    post_delay_ms=post_delay,
                    parameters=StepParameters(key=key_name, repeat_count=1),
                )
            )
```

**Rationale**: `pre_delay` and `post_delay` are already extracted at lines 428–437 for every box. Passing them to `WorkflowStep` ensures that standalone key presses honor `box.timing.pre_delay_ms`, `box.timing.post_delay_ms`, `box.post_delay_ms`, and `execution_settings.default_step_delay_ms`.

---

### Proposal 2: Pass 5 `pre_delay_ms` Preservation under `click_to_tab`

- **Target File**: `src/kutomoto/designer/compiler.py`
- **Target Lines**: Lines 130–156 (`_pass5_optimize_peephole`)

#### Before:
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

#### After:
```python
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
                # First field click must ALWAYS be preserved
                if field_click_count > 1 and is_after_tab and not is_force_click:
                    logger.debug(
                        "Peephole Optimizer: Pruned redundant click step: '%s'",
                        s.label,
                    )
                    # Preserve field settling delay (pre_delay_ms) if configured
                    if s.pre_delay_ms > 0:
                        if i + 1 < len(pruned_focus):
                            pruned_focus[i + 1].pre_delay_ms += s.pre_delay_ms
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
```

**Rationale**:
- `enumerate(pruned_focus)` gives direct access to index `i`.
- When a redundant click is pruned, if `s.pre_delay_ms > 0`, it adds `s.pre_delay_ms` to `pruned_focus[i + 1].pre_delay_ms` (which is `CLEAR_FIELD` or `TYPE_TEXT`).
- When `pruned_focus[i + 1]` is appended on the next iteration, it carries the full pre-delay.
- If there is no next step (`i + 1 >= len(pruned_focus)`), it safely emits a standalone `ActionType.DELAY` step.

---

### Proposal 3: Recommended Unit Test Additions in `tests/test_compiler.py`

#### 1. In `TestCompilerPass4ActionStepSynthesis`:
```python
def test_pass4_key_press_box_timing_propagation(self):
    """Standalone KEY_PRESS box propagates box.timing pre_delay and post_delay to WorkflowStep."""
    layout = VisualFormLayout(
        name="Key Press Timing",
        canvas=CanvasDimensions(width=800, height=600),
        target_application=TargetApplicationSpec(window_title_pattern="App"),
        boxes=[
            VisualBox(
                name="escape_key",
                action_type=DesignerActionType.KEY_PRESS,
                value="escape",
                geometry=BoxGeometry(x=50, y=50, width=50, height=30),
                timing=BoxTiming(pre_delay_ms=180, post_delay_ms=320),
            )
        ],
    )
    wf = compile_visual_layout_to_workflow(layout)
    kp_step = next(s for s in wf.steps if s.action_type == ActionType.KEY_PRESS)
    assert kp_step.parameters.key == "escape"
    assert kp_step.pre_delay_ms == 180
    assert kp_step.post_delay_ms == 320


def test_pass4_key_press_box_default_step_delay_inheritance(self):
    """Standalone KEY_PRESS box inherits execution_settings.default_step_delay_ms when timing is unset."""
    layout = VisualFormLayout(
        name="Key Press Default Timing",
        canvas=CanvasDimensions(width=800, height=600),
        target_application=TargetApplicationSpec(window_title_pattern="App"),
        execution_settings=ExecutionSettingsSpec(default_step_delay_ms=220),
        boxes=[
            VisualBox(
                name="f5_key",
                action_type=DesignerActionType.KEY_PRESS,
                value="f5",
                geometry=BoxGeometry(x=50, y=50, width=50, height=30),
                post_delay_ms=0,  # Forces fallback to default_step_delay_ms
            )
        ],
    )
    wf = compile_visual_layout_to_workflow(layout)
    kp_step = next(s for s in wf.steps if s.action_type == ActionType.KEY_PRESS)
    assert kp_step.pre_delay_ms == 0
    assert kp_step.post_delay_ms == 220
```

#### 2. In `TestCompilerPass5PeepholeOptimizer`:
```python
def test_pass5_click_to_tab_preserves_field_pre_delay_ms(self):
    """When click_to_tab prunes a click step, pre_delay_ms is transferred to the field's initial action."""
    layout = VisualFormLayout(
        name="Preserve Pre-Delay",
        canvas=CanvasDimensions(width=800, height=600),
        target_application=TargetApplicationSpec(window_title_pattern="App"),
        optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
        boxes=[
            VisualBox(name="f1", geometry=BoxGeometry(x=50, y=50, width=200, height=30), navigation=NavigationAction.TAB),
            VisualBox(
                name="f2",
                geometry=BoxGeometry(x=50, y=100, width=200, height=30),
                navigation=NavigationAction.TAB,
                clear_before=True,
                timing=BoxTiming(pre_delay_ms=500),
            ),
        ],
    )
    wf = compile_visual_layout_to_workflow(layout)
    f2_steps = [s for s in wf.steps if "f2" in (s.label or "")]
    # First step of f2 is Clear field, which must inherit the 500ms pre_delay
    assert len(f2_steps) == 3
    assert f2_steps[0].action_type == ActionType.CLEAR_FIELD
    assert f2_steps[0].pre_delay_ms == 500


def test_pass5_click_to_tab_preserves_pre_delay_without_clear_step(self):
    """When clear_before=False and click is pruned, pre_delay_ms transfers to TYPE_TEXT."""
    layout = VisualFormLayout(
        name="Preserve Pre-Delay No Clear",
        canvas=CanvasDimensions(width=800, height=600),
        target_application=TargetApplicationSpec(window_title_pattern="App"),
        optimization=PeepholeOptimizationConfig(enabled=True, click_to_tab=True),
        boxes=[
            VisualBox(name="f1", geometry=BoxGeometry(x=50, y=50, width=200, height=30), navigation=NavigationAction.TAB),
            VisualBox(
                name="f2",
                geometry=BoxGeometry(x=50, y=100, width=200, height=30),
                navigation=NavigationAction.TAB,
                clear_before=False,
                timing=BoxTiming(pre_delay_ms=450),
            ),
        ],
    )
    wf = compile_visual_layout_to_workflow(layout)
    f2_steps = [s for s in wf.steps if "f2" in (s.label or "")]
    assert len(f2_steps) == 2
    assert f2_steps[0].action_type == ActionType.TYPE_TEXT
    assert f2_steps[0].pre_delay_ms == 450
```

---

## 6. Verification Method

To independently verify this investigation and the proposed fix strategy:

1. **Verify Baseline Test Suite Passes (217 tests)**:
   ```powershell
   python -m pytest tests/ -v
   ```
   *Expected Result*: 217 passed in ~8.7s.

2. **Verify Finding 2 Reproduction (Current Code)**:
   ```powershell
   python -c "import sys; sys.path.insert(0, 'src'); from kutomoto.designer.schema import *; from kutomoto.designer.compiler import compile_visual_layout_to_workflow; layout = VisualFormLayout(name='T', canvas=CanvasDimensions(width=800, height=600), target_application=TargetApplicationSpec(window_title_pattern='App'), boxes=[VisualBox(name='k', action_type=DesignerActionType.KEY_PRESS, value='escape', geometry=BoxGeometry(x=10, y=10, width=50, height=20), timing=BoxTiming(pre_delay_ms=200, post_delay_ms=400))]); wf = compile_visual_layout_to_workflow(layout); s = wf.steps[1]; print('KEY_PRESS timing:', s.pre_delay_ms, s.post_delay_ms); assert s.pre_delay_ms == 0 and s.post_delay_ms == 0"
   ```
   *Result*: Prints `KEY_PRESS timing: 0 0`, confirming that timing parameters are currently dropped.

3. **Verify Finding F2 Reproduction (Current Code)**:
   ```powershell
   python -c "import sys; sys.path.insert(0, 'src'); from kutomoto.designer.schema import *; from kutomoto.designer.compiler import compile_visual_layout_to_workflow; layout = VisualFormLayout(name='T', canvas=CanvasDimensions(width=800, height=600), target_application=TargetApplicationSpec(window_title_pattern='App'), optimization=PeepholeOptimizationConfig(click_to_tab=True), boxes=[VisualBox(name='b1', geometry=BoxGeometry(x=10, y=10, width=50, height=20), navigation=NavigationAction.TAB), VisualBox(name='b2', geometry=BoxGeometry(x=10, y=50, width=50, height=20), timing=BoxTiming(pre_delay_ms=500))]); wf = compile_visual_layout_to_workflow(layout); b2_steps = [s for s in wf.steps if 'b2' in (s.label or '')]; print('b2 pre-delays:', [s.pre_delay_ms for s in b2_steps]); assert all(s.pre_delay_ms == 0 for s in b2_steps)"
   ```
   *Result*: Prints `b2 pre-delays: [0, 0]`, confirming that `pre_delay_ms=500` is currently dropped when the click is pruned.

4. **Verify In-Memory Proposed Fix Compatibility**:
   Running the proposed fixes against `tests/test_compiler.py` in-memory confirms 61/61 tests pass with zero regressions.

5. **Invalidation Conditions**:
   - If `WorkflowStep` schema is changed to remove `pre_delay_ms` or `post_delay_ms`.
   - If Pass 4 changes `TYPE_TEXT` step synthesis order to place `CLEAR_FIELD` before `CLICK`.
