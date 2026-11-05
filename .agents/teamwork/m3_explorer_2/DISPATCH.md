## 2026-11-05T00:13:15Z
You are m3_explorer_2 (Role: Milestone 3 Compiler Algorithm Explorer).
Your working directory is: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_explorer_2
Your parent conversation ID is: ce2dd708-d288-4e8f-9834-dfdb673a5856

MANDATORY INPUTS - Read these files first:
1. c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md (Section 6: Visual-to-Workflow Compilation & Section 5: Box Model)
3. c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md
4. c:\Users\daoud\projects\kutomoto\src\kutomoto\engine\schema.py

MISSION:
Investigate and design the 5-pass visual-to-workflow compilation algorithm in `src/kutomoto/designer/compiler.py`.

KEY QUESTIONS TO RESOLVE:
1. What is the exact function signature?
   `compile_visual_layout_to_workflow(layout: VisualFormLayout) -> KutomotoWorkflow`
2. How does each pass operate step-by-step?
   - Pass 1: Structural & Geometry Validation:
     - Verify layout has at least 1 box.
     - Verify every box fits within canvas (`x >= 0`, `y >= 0`, `x + width <= canvas.width`, `y + height <= canvas.height`).
     - Detect box overlapping / collision warnings if applicable.
   - Pass 2: Spatial Band Sorting & Sequence Ordering:
     - If all boxes have distinct explicit `sequence_index`, respect explicit order.
     - For boxes without explicit `sequence_index` (or `sequence_index == 0` / None), apply 2D spatial band sorting:
       - Sort into horizontal bands based on `box.y` and a configurable `band_tolerance_px` (default 24px or 50% of average box height).
       - Within each horizontal band (top-to-bottom), sort boxes left-to-right (`box.x`).
     - Support hybrid layouts: explicit indices first or sequence override.
   - Pass 3: Dual-Coordinate Normalization:
     - Compute normalized center coordinates:
       `norm_x = (box.geometry.x + box.geometry.width / 2.0) / float(layout.canvas.width)`
       `norm_y = (box.geometry.y + box.geometry.height / 2.0) / float(layout.canvas.height)`
     - Clamp to `[0.0, 1.0]`. Round to 4 decimal places for clean serialization.
   - Pass 4: Action Step Synthesis:
     - Step 0 (Header): `FOCUS_WINDOW` action targeting `layout.target_application.window_title_pattern` or default.
     - For each ordered box:
       - If `clear_before` is True: `CLEAR_FIELD` action or `CLICK_COORDINATES` + `CLEAR_FIELD`.
       - If action is `TYPE_TEXT`:
         - If click required: `CLICK_COORDINATES` at `(norm_x, norm_y)`
         - If `clear_before`: `CLEAR_FIELD`
         - `TYPE_TEXT` with `box.value`
         - Navigation step if specified: `KEY_PRESS` with `key="tab"` or `key="enter"`.
       - If action is `CLICK`:
         - `CLICK_COORDINATES` at `(norm_x, norm_y)`.
       - If action is `SUBMIT`:
         - `SUBMIT_FORM` (or Enter / Click submit button).
     - Assign sequential `sequence_index = 1, 2, 3...` to all generated workflow steps.
   - Pass 5: Peephole Navigation Optimizer:
     - How to replace sequential Click with Tab? (See Explorer 3 collaboration).
     - How to collapse consecutive delays?
3. What error types must be raised on invalid layouts? (`CompilationError`, `GeometryError`, `EmptyLayoutError`).

STRICT CONSTRAINTS:
- You are read-only. Do NOT write or modify source code in `src/` or `tests/`.
- Document your detailed technical analysis in `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_explorer_2\analysis.md`.
- Produce your final structured handoff report in `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_explorer_2\handoff.md`.
- Send a completion message via `send_message` to parent `ce2dd708-d288-4e8f-9834-dfdb673a5856` when done.
