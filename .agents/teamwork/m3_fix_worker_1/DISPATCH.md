## 2026-11-05T03:15:00Z
You are m3_fix_worker_1, an implementation worker.
Working directory: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_fix_worker_1\

MANDATORY INPUTS (read before starting):
- ORIGINAL_REQUEST.md: c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md
- PROJECT.md: c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md
- Explorer 1 Report: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_fix_explorer_1\handoff.md
- Explorer 2 Report: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_fix_explorer_2\handoff.md
- Explorer 3 Report: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_fix_explorer_3\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

EXCLUSIVE FILE WRITE OWNERSHIP:
You exclusively own and may edit:
- c:\Users\daoud\projects\kutomoto\src\kutomoto\designer\compiler.py
- c:\Users\daoud\projects\kutomoto\src\kutomoto\designer\schema.py
- c:\Users\daoud\projects\kutomoto\tests\test_compiler.py

MISSION:
Implement the verified fixes and comprehensive regression tests for Milestone 3 based on the 3 explorer reports:
1. `src/kutomoto/designer/compiler.py`:
   - Pass 4: In lines 552-569 (CLICK / CHECKBOX / SELECT branch):
     Propagate force_click markers:
     - append " [force_click]" to label if force_click is true
     - set parameters.variable_name="__force_click__" if force_click is true
     - set setattr(click_step, "_force_click", force_click)
     - set setattr(click_step, "_is_action_click", True)
   - Pass 4: In lines 463-478 (TYPE_TEXT branch):
     - set setattr(click_step, "_is_focus_anchor", True)
   - Pass 4: In lines 624-636 (KEY_PRESS branch):
     - pass pre_delay_ms=pre_delay, post_delay_ms=post_delay to WorkflowStep
   - Pass 2: In lines 370-374:
     - check `b.sequence_index is not None and b.sequence_index >= 1`
   - Pass 5: In lines 130-156 (`_pass5_optimize_peephole`):
     - Ensure standalone action clicks (CLICK, CHECKBOX, SELECT) are NEVER pruned by click_to_tab, even following a Tab.
     - Prune ONLY auxiliary focus anchor clicks preceding clear_field/type_text where field_click_count > 1, is_after_tab, not is_force_click, not is_action_click, and is_focus_anchor.
     - When an auxiliary focus click IS pruned: if s.pre_delay_ms > 0, preserve that settling delay! Transfer s.pre_delay_ms to the next step (`pruned_focus[i + 1].pre_delay_ms += s.pre_delay_ms`), or append a standalone ActionType.DELAY step if no next step exists (Strategy 1 from explorer 2).
2. `src/kutomoto/designer/schema.py`:
   - In lines 154-158: update sequence_index field definition to `ge=1` (1-based index) with clear validation message.
3. `tests/test_compiler.py`:
   - Implement the comprehensive test suite from m3_fix_explorer_3 and explorer 1 & 2 covering:
     - force_click=True preserves clicks under click_to_tab=True for TYPE_TEXT
     - force_click=True preserves clicks under click_to_tab=True for CLICK, CHECKBOX, SELECT
     - Standalone CLICK, CHECKBOX, SELECT following Tab are preserved even with force_click=False
     - KEY_PRESS timing delay inheritance (pre_delay_ms and post_delay_ms)
     - Pre-delay settling time preserved when focus click is pruned under click_to_tab
     - sequence_index ge=1 validation and ordering
4. VERIFICATION:
   - Run `python -m pytest tests/test_compiler.py -v`
   - Run `python -m pytest tests/ -v`
   - Run `python -m ruff check src/ tests/`
   - Verify 100% test pass rate and 0 lint errors.

DELIVERABLE:
Write your complete handoff report to c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_fix_worker_1\handoff.md documenting all code changes, test outputs, and verification results.
Notify parent via send_message when done.
