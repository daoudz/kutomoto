# Milestone 3 Fix Investigation & Test Suite Specification Report

```
====================================================================================================
Agent               : m3_fix_explorer_3 (Read-only Investigation & Test Suite Designer)
Roles               : explorer, specialist, test designer
Parent Conversation : 59700fc9-320d-4ed3-b1db-2fc709fed831
Working Directory   : c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_fix_explorer_3
Date                : 2026-11-05
Status              : Complete
Verdict             : Harmonization & Test Plan Formulated
====================================================================================================
```

---

## 1. Observation

Direct empirical observations, verbatim code references, schema definitions, and reproduction commands across the codebase:

### 1.1 Sequence Index Inconsistency (Challenger Finding F1)
- **`src/kutomoto/designer/schema.py` lines 154–158**:
  ```python
  sequence_index: Optional[int] = Field(
      default=None,
      ge=0,
      description="Explicit execution sequence rank (1-based, or None for spatial ordering)",
  )
  ```
  *Contradiction within the same declaration*: `ge=0` permits `0`, while the description explicitly documents `"1-based, or None for spatial ordering"`.
- **`src/kutomoto/designer/compiler.py` lines 368–374**:
  ```python
  boxes_list = list(layout_model.boxes)
  explicit_boxes = [
      b for b in boxes_list if b.sequence_index is not None and b.sequence_index > 0
  ]
  unindexed_boxes = [
      b for b in boxes_list if b.sequence_index is None or b.sequence_index <= 0
  ]
  ```
  *Empirical Behavior*:
  When a box has `sequence_index=0`, it passes `VisualBox` validation (`ge=0`), but `b.sequence_index > 0` evaluates to `False`. It is grouped into `unindexed_boxes` (`<= 0`).
  In lines 388–394 (hybrid ordering), `ordered_boxes = ordered_explicit + ordered_unindexed`.
  Reproduction via shell:
  ```powershell
  python -c "import sys; sys.path.insert(0, 'src'); from kutomoto.designer.schema import *; from kutomoto.designer.compiler import compile_visual_layout_to_workflow; b0 = VisualBox(name='b0', geometry=BoxGeometry(x=10, y=10, width=50, height=20), sequence_index=0); b1 = VisualBox(name='b1', geometry=BoxGeometry(x=10, y=50, width=50, height=20), sequence_index=1); b2 = VisualBox(name='b2', geometry=BoxGeometry(x=10, y=90, width=50, height=20), sequence_index=2); layout = VisualFormLayout(name='Test', canvas=CanvasDimensions(width=800, height=600), target_application=TargetApplicationSpec(window_title_pattern='App'), boxes=[b0, b1, b2]); wf = compile_visual_layout_to_workflow(layout); print([s.label for s in wf.steps if 'Click' in s.label])"
  ```
  *Output*: `['Click [b1]', 'Click [b2]', 'Click [b0]']`.
  `b0` is executed **last**, at the tail of the workflow, directly inverting author intent!
- **`docs/SPECIFICATION.md` references**:
  - Line 1212 (Section 7.2 Visual Form Designer JSON Schema):
    `"sequence_index": { "type": "integer", "minimum": 1 },`
  - Line 1362 (Section 8.2 Unified Action Workflow JSON Schema):
    `"sequence_index": { "type": "integer", "minimum": 1 },`
  - Line 1537 (Section 8.4 Pass 2 Pseudocode):
    `has_explicit_indices = all(b.get("sequence_index", 0) > 0 for b in validated_boxes)`
  - Line 184 (Enterprise Edge Case E12):
    `"Designer applies automatic sequence normalization: sorts all boxes by requested index... and re-assigns clean, contiguous integer ranks [1, 2, 3, ...]"`
  - Line 45, 1129 (Visual Designer UI Badges): Sequence badges are displayed as `[#1]`, `[#2]`, etc.
- **`src/kutomoto/engine/schema.py` line 189**:
  ```python
  sequence_index: int = Field(..., ge=1, description="Contiguous 1-based order")
  ```
  The workflow engine strictly rejects any step with `sequence_index < 1`.

### 1.2 `force_click=True` Propagation Flaw (Reviewer Finding 1)
- In `compiler.py` lines 448–478, for `TYPE_TEXT`, `force_click` sets:
  1. `label = f"... [force_click]"`
  2. `variable_name = "__force_click__"`
  3. `setattr(click_step, "_force_click", force_click)`
- In `compiler.py` lines 552–569, for `CLICK`, `CHECKBOX`, `SELECT`:
  `force_click` is **never passed or referenced**. None of the 3 markers are set.
- Consequently, in Pass 5 (`compiler.py` lines 136–140), `is_force_click` evaluates to `False`. If the action box follows a `tab` step, its click is eliminated.
  Reproduction via shell:
  ```powershell
  python -c "import sys; sys.path.insert(0, 'src'); from kutomoto.designer.schema import *; from kutomoto.designer.compiler import compile_visual_layout_to_workflow; from kutomoto.engine.schema import ActionType; b1 = VisualBox(name='text1', geometry=BoxGeometry(x=10, y=10, width=50, height=20), action_type=DesignerActionType.TYPE_TEXT, navigation=NavigationAction.TAB); b2 = VisualBox(name='click1', geometry=BoxGeometry(x=10, y=50, width=50, height=20), action_type=DesignerActionType.CLICK, force_click=True); layout = VisualFormLayout(name='Test', canvas=CanvasDimensions(width=800, height=600), target_application=TargetApplicationSpec(window_title_pattern='App'), optimization=PeepholeOptimizationConfig(click_to_tab=True), boxes=[b1, b2]); wf = compile_visual_layout_to_workflow(layout); clicks = [s.label for s in wf.steps if s.action_type == ActionType.CLICK]; print('Clicks:', clicks)"
  ```
  *Output*: `Clicks: ['Click [text1]']` (The button click for `click1` is completely eliminated).

### 1.3 Standalone Action Boxes Pruned by `click_to_tab` (Reviewer Finding 1)
- For `DesignerActionType.CLICK`, `CHECKBOX`, and `SELECT`, the mouse click is the actual operational payload (toggling a checkbox, opening a select dropdown, or clicking a button).
- However, when following a `tab` step, Pass 5 treats ANY subsequent `ActionType.CLICK` without `force_click` as a redundant focus anchor and eliminates it (`compiler.py:147–152`).
- As a result, standard checkboxes or buttons following a text input with `nav=TAB` are completely omitted from the generated workflow.

### 1.4 `KEY_PRESS` Delay Parameter Inheritance (Reviewer Finding 2)
- In `compiler.py` lines 624–636:
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
- Neither `pre_delay_ms` nor `post_delay_ms` is supplied to `WorkflowStep`.
- Reproduction via shell:
  ```powershell
  python -c "import sys; sys.path.insert(0, 'src'); from kutomoto.designer.schema import *; from kutomoto.designer.compiler import compile_visual_layout_to_workflow; from kutomoto.engine.schema import ActionType; b1 = VisualBox(name='kp1', geometry=BoxGeometry(x=10, y=10, width=50, height=20), action_type=DesignerActionType.KEY_PRESS, value='enter', timing=BoxTiming(pre_delay_ms=250, post_delay_ms=350)); layout = VisualFormLayout(name='Test', canvas=CanvasDimensions(width=800, height=600), target_application=TargetApplicationSpec(window_title_pattern='App'), boxes=[b1]); wf = compile_visual_layout_to_workflow(layout); kp = next(s for s in wf.steps if s.action_type == ActionType.KEY_PRESS); print('pre_delay:', kp.pre_delay_ms, 'post_delay:', kp.post_delay_ms)"
  ```
  *Output*: `pre_delay: 0 post_delay: 0` (ignoring `pre_delay_ms=250` and `post_delay_ms=350`).

### 1.5 Dropped `pre_delay_ms` Under `click_to_tab` (Challenger Finding F2)
- In `compiler.py` lines 460–507:
  - `click_step` has `pre_delay_ms = pre_delay` (line 467).
  - `clear_step` has hardcoded `pre_delay_ms = 0` (line 490).
  - `type_step` has hardcoded `pre_delay_ms = 0` (line 506).
- When `opt.click_to_tab = True`, Pass 5 discards the redundant `click_step` for field 2 (`compiler.py:152: continue`).
- Crucially, `click_step.pre_delay_ms` is discarded with it. The subsequent `clear_step` and `type_step` execute with 0ms pre-delay.
  Reproduction via shell:
  ```powershell
  python -c "import sys; sys.path.insert(0, 'src'); from kutomoto.designer.schema import *; from kutomoto.designer.compiler import compile_visual_layout_to_workflow; from kutomoto.engine.schema import ActionType; b1 = VisualBox(name='b1', geometry=BoxGeometry(x=10, y=10, width=50, height=20), navigation=NavigationAction.TAB); b2 = VisualBox(name='b2', geometry=BoxGeometry(x=10, y=50, width=50, height=20), timing=BoxTiming(pre_delay_ms=500)); layout = VisualFormLayout(name='Test', canvas=CanvasDimensions(width=800, height=600), target_application=TargetApplicationSpec(window_title_pattern='App'), optimization=PeepholeOptimizationConfig(click_to_tab=True), boxes=[b1, b2]); wf = compile_visual_layout_to_workflow(layout); b2_steps = [s for s in wf.steps if 'b2' in (s.label or '')]; print([(s.label, s.pre_delay_ms) for s in b2_steps])"
  ```
  *Output*: `[('Clear [b2]', 0), ('Type into [b2]', 0)]`. The 500ms settling delay was completely lost.

---

## 2. Logic Chain

1. **Root Cause Analysis for Finding F1 (Sequence Index 0 Semantics)**:
   - In `SPECIFICATION.md` lines 1212 and 1362, `sequence_index` is defined as `integer, minimum: 1`.
   - In `SPECIFICATION.md` line 1537, the reference pseudocode uses `b.get("sequence_index", 0) > 0`, where `0` was simply the fallback default for an omitted field in a raw dictionary.
   - When transcribing to Pydantic in `src/kutomoto/designer/schema.py`, `sequence_index` defaulted to `None`, but `ge=0` was erroneously written instead of `ge=1`.
   - In `compiler.py:370`, the compiler implemented `b.sequence_index > 0`, treating `0` as not indexed.
   - Therefore, a box with `sequence_index=0` bypassed schema validation but failed the compiler's explicit index filter, causing it to be relegated to the unindexed tail.

2. **Harmonization Evaluation (Option A vs Option B)**:
   - **Option A (Strict 1-Based: `ge=1` in `schema.py`)**:
     * Changes `schema.py:156` from `ge=0` to `ge=1`.
     * Docstring remains `"Explicit execution sequence rank (1-based, or None for spatial ordering)"`.
     * `compiler.py:370` checks `b.sequence_index is not None and b.sequence_index >= 1`.
     * *Consistency*: 100% aligned with `SPECIFICATION.md` (`minimum: 1`), `WorkflowStep.sequence_index` (`ge=1`), UI sequence badges (`[#1], [#2]`), and enterprise domain conventions.
     * *Fail-fast*: If a caller passes `0`, Pydantic immediately raises `ValidationError: Input should be greater than or equal to 1`, preventing silent behavioral surprises.
   - **Option B (0-Based Tolerant: `ge=0` and compiler recognizes `>= 0`)**:
     * Modifies `compiler.py:370-374` so `explicit_boxes` filters `b.sequence_index is not None and b.sequence_index >= 0`, and `unindexed_boxes` filters `b.sequence_index is None`.
     * *Pros*: Accepts 0-indexed sequences `[0, 1, 2]` without error.
     * *Cons*: Directly conflicts with `SPECIFICATION.md` lines 1212 and 1362 (`minimum: 1`), contradicts the schema docstring, and conflicts with `WorkflowStep.sequence_index: ge=1`.
   - **Deduction**: **Option A is the definitively superior, architecturally correct choice.** The kutomoto platform is strictly 1-based across UI badges, specifications, and execution steps. Defensive coding in the compiler should ensure `b.sequence_index is not None and b.sequence_index >= 1`.

3. **Logic Chain for Reviewer Finding 1 & Standalone Non-Text Actions**:
   - `VisualBox.force_click` was created specifically to force physical clicks when `click_to_tab=True`.
   - In Pass 4, `CLICK`, `CHECKBOX`, and `SELECT` branches must propagate `force_click` markers (`_force_click = True`, `[force_click]` in label, and `variable_name = "__force_click__"`).
   - Furthermore, standalone action boxes (`CLICK`, `CHECKBOX`, `SELECT`) represent explicit interactions rather than redundant cursor placement anchors.
   - Therefore, in Pass 5, `click_to_tab` must NEVER prune standalone action clicks, even when `force_click=False`. Only focus clicks immediately preceding text entry or clearing (`TYPE_TEXT` / `CLEAR_FIELD`) should be candidate focus clicks for pruning.

4. **Logic Chain for Reviewer Finding 2 (`KEY_PRESS` Timing)**:
   - For `TYPE_TEXT`, `CLICK`, and `SUBMIT`, `pre_delay` and `post_delay` are computed from `box.timing` with fallback to `execution_settings` and `box.post_delay_ms`.
   - `KEY_PRESS` was an omission in Pass 4, omitting `pre_delay_ms` and `post_delay_ms`.
   - Supplying `pre_delay_ms=pre_delay` and `post_delay_ms=post_delay` restores uniform timing semantics across all action types.

5. **Logic Chain for Challenger Finding F2 (Settling Delay Loss under `click_to_tab`)**:
   - When a focus click is pruned under `click_to_tab`, its purpose was focusing the element, but its `pre_delay_ms` represents the required settling time before interacting with that control.
   - If that click is pruned, discarding `pre_delay_ms` violates timing guarantees.
   - When Pass 5 eliminates a click step with `pre_delay_ms > 0`:
     * The `pre_delay_ms` must be transferred to the immediate next step in the box's step sequence (e.g. `clear_field` or `type_text`).
     * `next_step.pre_delay_ms = (next_step.pre_delay_ms or 0) + s.pre_delay_ms`.
     * If there is no next step, a standalone `ActionType.DELAY` step must be synthesized with `duration_ms = s.pre_delay_ms`.
   - This ensures 100% preservation of user-configured settling delays.

---

## 3. Caveats

1. **External Schemas**: If third-party integrations generate JSON layouts with 0-based indices, changing `schema.py` to `ge=1` will cause `ValidationError`. However, this is intended and desirable: kutomoto's enterprise specification explicitly mandates 1-based indexing (`minimum: 1`), and the documentation will clearly instruct users that sequence ranks start at 1.
2. **Read-Only Constraint**: As an explorer agent, no code or test files were directly edited during this investigation. All changes, exact code proposals, and test additions are provided in this handoff for the implementation worker.
3. **Delay Coalescing Interaction**: When transferring `pre_delay_ms` or emitting a `DELAY` step, Pass 5's subsequent delay coalescing pass (`opt.collapse_delays`) will naturally coalesce any adjacent delays without creating fragmented steps.

---

## 4. Conclusion & Recommended Fix Proposals

### 4.1 Harmonization Recommendation for Finding F1
- **File**: `src/kutomoto/designer/schema.py` line 156
  ```python
  # BEFORE:
  sequence_index: Optional[int] = Field(
      default=None,
      ge=0,
      description="Explicit execution sequence rank (1-based, or None for spatial ordering)",
  )

  # AFTER:
  sequence_index: Optional[int] = Field(
      default=None,
      ge=1,
      description="Explicit execution sequence rank (1-based, or None for spatial ordering)",
  )
  ```
- **File**: `src/kutomoto/designer/compiler.py` lines 368–374
  ```python
  # BEFORE:
  boxes_list = list(layout_model.boxes)
  explicit_boxes = [
      b for b in boxes_list if b.sequence_index is not None and b.sequence_index > 0
  ]
  unindexed_boxes = [
      b for b in boxes_list if b.sequence_index is None or b.sequence_index <= 0
  ]

  # AFTER:
  boxes_list = list(layout_model.boxes)
  explicit_boxes = [
      b for b in boxes_list if b.sequence_index is not None and b.sequence_index >= 1
  ]
  unindexed_boxes = [
      b for b in boxes_list if b.sequence_index is None
  ]
  ```

### 4.2 Fix Proposal for Reviewer Finding 1 & Standalone Action Preservation
- **File**: `src/kutomoto/designer/compiler.py` lines 552–569
  ```python
  # AFTER:
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
  ```
- **File**: `src/kutomoto/designer/compiler.py` lines 130–156 (`_pass5_optimize_peephole`)
  ```python
  # AFTER:
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
              is_action_click = getattr(s, "_is_action_click", False)
              is_after_tab = (
                  tab_optimized
                  and tab_optimized[-1].action_type == ActionType.KEY_PRESS
                  and (tab_optimized[-1].parameters.key or "").lower() == "tab"
              )
              # Initial field click is ALWAYS preserved.
              # Standalone action clicks (CLICK, CHECKBOX, SELECT) must NOT be pruned.
              # Redundant focus clicks for TYPE_TEXT without force_click are pruned.
              if (
                  field_click_count > 1
                  and is_after_tab
                  and not is_force_click
                  and not is_action_click
              ):
                  logger.debug(
                      "Peephole Optimizer: Pruned redundant click step: '%s'",
                      s.label,
                  )
                  # Finding F2 Fix: Transfer settling pre_delay_ms to immediate next step
                  if s.pre_delay_ms and s.pre_delay_ms > 0:
                      if i + 1 < len(pruned_focus):
                          next_step = pruned_focus[i + 1]
                          next_step.pre_delay_ms = (
                              next_step.pre_delay_ms or 0
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
  ```

### 4.3 Fix Proposal for Reviewer Finding 2 (`KEY_PRESS` Timing)
- **File**: `src/kutomoto/designer/compiler.py` lines 624–636
  ```python
  # AFTER:
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

---

## 5. Comprehensive Test Suite Specification for `tests/test_compiler.py`

Below is the complete, self-contained test class `TestCompilerRegressionAndEdgeCases` ready to be appended to `tests/test_compiler.py`. It thoroughly covers all 6 test suite requirements with explicit mock layouts, precise assertions, and end-to-end integration checks.

```python
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
                )
            ],
        )
        wf = compile_visual_layout_to_workflow(layout)
        kp_step = next(s for s in wf.steps if s.action_type == ActionType.KEY_PRESS)
        assert kp_step.pre_delay_ms == 180
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
        kp_step = next(s for s in wf.steps if s.action_type == ActionType.KEY_PRESS and "tab" in (s.parameters.key or ""))
        assert kp_step.pre_delay_ms == 80
        assert kp_step.post_delay_ms == 120

        # 4. Verify async execution against MockWin32Driver
        driver = MockWin32Driver()
        runner = WorkflowRunner(driver=driver)
        run_record = await runner.execute_workflow(wf)
        assert run_record.state == ExecutionState.COMPLETED
        assert run_record.executed_steps_count == len(wf.steps)
        assert len(run_record.step_records) == len(wf.steps)
```

---

## 6. Verification Method

To independently verify the investigation findings and run the test suite:

1. **Verify Baseline Compiler Test Suite**:
   ```powershell
   python -m pytest tests/test_compiler.py -v
   ```
   *Expected Result*: 61 passed in ~4.0s.

2. **Verify Challenger Stress Suite**:
   ```powershell
   python -m pytest tests/test_compiler_empirical_challenge.py -v
   ```
   *Expected Result*: 24 passed in ~0.3s.

3. **Verify Sequence Index 0 vs 1 Behavior**:
   ```powershell
   python -c "import sys; sys.path.insert(0, 'src'); from kutomoto.designer.schema import *; from kutomoto.designer.compiler import compile_visual_layout_to_workflow; b0 = VisualBox(name='b0', geometry=BoxGeometry(x=10, y=10, width=50, height=20), sequence_index=0); b1 = VisualBox(name='b1', geometry=BoxGeometry(x=10, y=50, width=50, height=20), sequence_index=1); layout = VisualFormLayout(name='Test', canvas=CanvasDimensions(width=800, height=600), target_application=TargetApplicationSpec(window_title_pattern='App'), boxes=[b0, b1]); wf = compile_visual_layout_to_workflow(layout); print([s.label for s in wf.steps if 'Click' in s.label])"
   ```
   *Current Result*: Shows `['Click [b1]', 'Click [b0]']`, confirming Finding F1 relegation of sequence 0.
   *After Harmonization (`ge=1`)*: Bypassing or passing 0 will fail with `ValidationError`.

4. **Verify Full Project Regression Suite**:
   ```powershell
   python -m pytest tests/ -v
   ```
   *Expected Result*: 217 passed in ~8-9s.
