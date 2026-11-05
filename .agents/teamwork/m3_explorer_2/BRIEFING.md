# BRIEFING — 2026-11-05T00:17:30Z

## Mission
Investigate and design the 5-pass visual-to-workflow compilation algorithm in `src/kutomoto/designer/compiler.py` for Milestone 3.

## 🔒 My Identity
- Archetype: explorer
- Roles: Milestone 3 Compiler Algorithm Explorer
- Working directory: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_explorer_2
- Original parent: ce2dd708-d288-4e8f-9834-dfdb673a5856
- Milestone: M3 (Visual Form Designer)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement in src/ or tests/
- Produce structured analysis.md and handoff.md
- Keep within .agents/teamwork/m3_explorer_2

## Current Parent
- Conversation ID: ce2dd708-d288-4e8f-9834-dfdb673a5856
- Updated: 2026-11-05T00:17:30Z

## Investigation State
- **Explored paths**:
  - `c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md`
  - `c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md` (Sections 5, 7, 8)
  - `c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md`
  - `c:\Users\daoud\projects\kutomoto\src\kutomoto\engine\schema.py`
  - `c:\Users\daoud\projects\kutomoto\src\kutomoto\engine\runner.py`
- **Key findings**:
  - Exact signature: `compile_visual_layout_to_workflow(layout: Union[VisualFormLayout, Dict[str, Any]], optimization: Optional[PeepholeOptimizationConfig] = None) -> KutomotoWorkflow`
  - Backward compatible alias: `compile_visual_boxes_to_workflow(layout, traversal_mode="coordinate_targeted", **kwargs) -> KutomotoWorkflow`
  - Pass 1 validates canvas dimensions > 0, box dimensions > 0, non-negative coordinates, boundary containment with epsilon (1e-4), duplicate IDs, and collision diagnostics.
  - Pass 2 resolves sequence order via explicit index or 2D horizontal band sort (with configurable `band_tolerance_px`, default 24px or 50% avg height, sorting top-to-bottom and left-to-right).
  - Pass 3 normalizes center coordinates and dimensions clamped to [0.0, 1.0] and rounded to 4 decimals.
  - Pass 4 synthesizes FOCUS_WINDOW header step followed by CLICK, CLEAR_FIELD, TYPE_TEXT, SUBMIT, and KEY_PRESS navigation steps.
  - Pass 5 implements peephole optimizations (click-to-tab elimination, consecutive delay collapse) and strictly re-indexes all steps 1..N.
  - Exception hierarchy defined: `CompilationError`, `EmptyLayoutError`, `GeometryError`, `DuplicateBoxIdError`, `OptimizationError`.
- **Unexplored areas**: None; design is complete and verified against M2 engine.

## Key Decisions Made
- Primary function is `compile_visual_layout_to_workflow` accepting `VisualFormLayout` or dict; alias `compile_visual_boxes_to_workflow` preserved for SPECIFICATION.md compatibility.
- Collision detection emits warnings and records diagnostics rather than throwing hard errors to support overlapping design elements.
- Coordinates normalized to center point and rounded to 4 decimals for clean serialization.
- Click-to-tab optimizer removes redundant field clicks after Tab keypress in Western reading order.

## Artifact Index
- DISPATCH.md — Initial dispatch instructions
- BRIEFING.md — Persistent context & memory
- progress.md — Liveness heartbeat
- analysis.md — Exhaustive technical analysis of the 5-pass compiler
- handoff.md — Final 5-component handoff report
