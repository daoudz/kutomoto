# Handoff Report: Milestone 3 Designer Schema Architecture & Design

```
====================================================================================================
Agent Name         : m3_explorer_1 (Milestone 3 Designer Schema Explorer)
Parent Conversation: ce2dd708-d288-4e8f-9834-dfdb673a5856
Target Artifact    : src/kutomoto/designer/schema.py
Deliverable Files  : analysis.md, test_prototype.py, handoff.md
Date               : 2026-11-05
Status             : COMPLETE (Hard Handoff)
====================================================================================================
```

---

## 1. Observation

### 1.1 Specification & Project Directives
1. **`docs/SPECIFICATION.md` Section 7.2 & 7.3 (Lines 1136–1422)**:
   - Section 7.2 defines `VisualFormLayout` with required fields `schema_version`, `id`, `name`, `target`, `canvas`, `boxes`, and `"copyright": "Copyrights reserved to 90Studio"`.
   - Section 7.3 defines `KutomotoWorkflow` with required fields `schema_version`, `id`, `name`, `target_application`, `execution_settings`, `steps`, and `"copyright": "Copyrights reserved to 90Studio"`.
2. **`docs/SPECIFICATION.md` Section 8.2 (Lines 1764–1800)**:
   - Hardening Directive 1 mandates coordinate boundary clamping:
     ```python
     norm_x = max(0.0, min(1.0, round(x / canvas_w, 4)))
     norm_y = max(0.0, min(1.0, round(y / canvas_h, 4)))
     norm_w = max(0.0, min(1.0 - norm_x, round(w / canvas_w, 4)))
     norm_h = max(0.0, min(1.0 - norm_y, round(h / canvas_h, 4)))
     ```
   - Hardening Directive 2 mandates strict non-zero canvas validation: `canvas_w > 0 and canvas_h > 0`.
   - Hardening Directive 3 mandates schema flexibility for optional box elements: `norm_bounds: Optional[NormBounds] = None`, `value_config: Optional[ValueConfig] = None`.
3. **`src/kutomoto/engine/schema.py` (Lines 187–264)**:
   - Models `TargetApplication`, `ExecutionSettings`, `DesignerMetadata`, `WorkflowStep`, `StepParameters`, and `KutomotoWorkflow` are defined in Pydantic V2 with strict copyright validation:
     ```python
     copyright: Literal["Copyrights reserved to 90Studio"] = Field(
         default="Copyrights reserved to 90Studio",
         description="Mandatory 90Studio copyright watermark",
     )
     ```
4. **Existing Test Suite Baseline**:
   - `python -m pytest` executes 132 tests in 4.59s with 100% pass rate (`tests/test_specification.py`, `tests/test_spec_empirical_challenge.py`, `tests/test_engine.py`, `tests/test_win32_driver.py`).
5. **Empirical Verification Prototype**:
   - In `.agents/teamwork/m3_explorer_1/test_prototype.py`, the complete proposed Pydantic V2 schema was instantiated and verified against Python 3.14.0 + Pydantic 2.12.
   - Command: `python -m pytest .agents/teamwork/m3_explorer_1/test_prototype.py`
   - Output: `5 passed in 0.07s` (full test suite with workflow synthesis: 6 passed in 0.08s).

---

## 2. Logic Chain

1. **Model Requirement Derivation (From Observations 1.1, 1.2, 1.3)**:
   - To support the Visual Form Designer UI and compiler without schema impedance, we require:
     - `CanvasDimensions`: Encapsulates `width`, `height`, `scale`, and `background_image_path`. Enforces `width > 0` and `height > 0` via `Field(..., gt=0)`, directly resolving Observation 1.2 Hardening Directive 2 and preventing division-by-zero during normalization.
     - `BoxGeometry`: Encapsulates `x`, `y`, `width`, `height` with `x, y >= 0` and `width, height > 0`. Provides computed properties `right`, `bottom`, `center_x`, and `center_y`.
     - `VisualBox`: Encapsulates `id`, `name`, `label`, `geometry` (aliased to `rect`), `sequence_index`, `action_type`, `value`, `navigation`, `clear_before`, `post_delay_ms`, and `metadata`. Provides backward compatibility with Section 7.2 attributes (`field_type`, `value_config`, `timing`) via a `@model_validator(mode="before")` pre-processor.
     - `TargetApplicationSpec`: Inherits directly from `src.kutomoto.engine.schema.TargetApplication` while introducing `validation_alias=AliasChoices("window_title_pattern", "match_pattern")`.
     - `ExecutionSettingsSpec`: Inherits directly from `src.kutomoto.engine.schema.ExecutionSettings` while introducing `validation_alias=AliasChoices("default_step_delay_ms", "post_delay_ms")`.
     - `PeepholeOptimizationConfig`: Manages compiler optimization flags (`enabled`, `band_tolerance_px`, `click_to_tab`, `collapse_delays`).
     - `VisualFormLayout`: The root document binding canvas, target app, execution settings, optimizations, boxes, and variables.
2. **Validator Construction (From Observations 1.1, 1.2, 1.3)**:
   - Boundary checks cannot be verified on `VisualBox` or `BoxGeometry` in isolation because they lack canvas dimensions. Therefore, `VisualFormLayout` implements `@model_validator(mode="after")` to verify:
     $$\text{geom.right} \le \text{canvas.width} + 10^{-4} \quad \text{and} \quad \text{geom.bottom} \le \text{canvas.height} + 10^{-4}$$
   - Unique box IDs across the layout are validated within the same post-root validator: `len(box_ids) == len(set(box_ids))`.
   - 90Studio copyright watermark is enforced via `Literal["Copyrights reserved to 90Studio"]` combined with `@field_validator("copyright")`, maintaining exact behavioral consistency with `KutomotoWorkflow`.
3. **Interfacing with Engine Schema (From Observations 1.3, 1.5)**:
   - `VisualFormLayout` generates normalized box coordinates clamped to $[0.0, 1.0]$ via `get_normalized_box()`.
   - `TargetApplicationSpec` and `ExecutionSettingsSpec` are direct subclasses of the engine's `TargetApplication` and `ExecutionSettings`, enabling zero-conversion assignment into `KutomotoWorkflow`.
   - `KutomotoWorkflow.designer_metadata` is populated directly from `layout.canvas` and `layout.boxes`.

---

## 3. Caveats

1. **Read-Only Explorer Scope**: In accordance with explorer integrity constraints, no changes were committed to `src/kutomoto/designer/schema.py` or `tests/`. The implementation must be executed by the designated implementer agent (`m3_implementer_1`).
2. **Tolerance Epsilon**: Boundary containment uses an epsilon of $10^{-4}$ (`cw + 1e-4`) to prevent false-positive rejection of valid boxes positioned flush against canvas edges due to IEEE-754 floating point precision.
3. **Draft Canvas with Zero Boxes**: `VisualFormLayout.boxes` defaults to an empty list (`default_factory=list`) to allow operators to save blank canvas drafts before placing fields. The compiler (`src/kutomoto/designer/compiler.py`) enforces `len(boxes) >= 1` at compile time.

---

## 4. Conclusion

The complete Pydantic V2 schema architecture for `src/kutomoto/designer/schema.py` is fully designed, tested, and empirically validated. It satisfies all 3 key questions from the mission dispatch:
1. Exact Pydantic V2 models defined with optimal inheritance and properties.
2. Complete field validators and root validators defined (boundary containment, positive dimensions, unique IDs, 90Studio copyright, and alias compatibility).
3. Clean, typed 1:1 interfacing with `KutomotoWorkflow` in `src/kutomoto/engine/schema.py`.

The reference design code in `.agents/teamwork/m3_explorer_1/analysis.md` and verification harness in `.agents/teamwork/m3_explorer_1/test_prototype.py` provide a drop-in specification for the implementer agent.

---

## 5. Verification Method

To independently verify the schema design and test assertions:

1. **Execute Standalone Prototype Suite**:
   ```powershell
   python .agents/teamwork/m3_explorer_1/test_prototype.py
   ```
   *Expected Outcome*:
   - `test_full_roundtrip passed!`
   - `test_boundary_violations passed!`
   - `test_duplicate_box_ids passed!`
   - `test_copyright_validation passed!`
   - `test_section_7_2_compatibility passed!`
   - `test_interface_with_kutomoto_workflow passed!`
   - `ALL VERIFICATION PROTOCOL TESTS PASSED SUCCESSFULLY!`

2. **Execute via Pytest**:
   ```powershell
   python -m pytest .agents/teamwork/m3_explorer_1/test_prototype.py
   ```
   *Expected Outcome*: `6 passed in 0.08s` with exit code 0.

3. **Verify Baseline Non-Regression**:
   ```powershell
   python -m pytest tests/
   ```
   *Expected Outcome*: All 132 existing unit, engine, and specification tests pass without warnings or failures.

4. **Invalidation Conditions**:
   - Any box allowed with $x + \text{width} > \text{canvas.width}$ without raising a `ValidationError`.
   - Canvas allowed with non-positive dimensions (`width <= 0`).
   - Any layout serialized without `"copyright": "Copyrights reserved to 90Studio"`.
   - Failure of `VisualFormLayout` to produce valid inputs for `KutomotoWorkflow`.
