# Dispatch for m1_fix_worker_1 (Milestone 1, Iteration 2)

## Objective
Apply the exact drop-in remediation formulated by `m1_fix_explorer_1` to `docs/SPECIFICATION.md` and update `tests/test_specification.py` to add the regression prevention test.

## Exclusive Write Ownership
You exclusively own and may write to:
- `c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md`
- `c:\Users\daoud\projects\kutomoto\tests\test_specification.py`
- Files within your own directory `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_fix_worker_1\`

DO NOT touch any other source or test files.

## Inputs
- ORIGINAL_REQUEST: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md`
- Master Architecture: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md`
- Explorer Remediation Plan: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_fix_explorer_1\report.md`
- Challenger Failure Report: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_challenger_2\handoff.md`

## Instructions
1. Read `m1_fix_explorer_1\report.md` carefully.
2. Update `docs/SPECIFICATION.md`:
   - Insert the missing `- **Workflow Execution Sequence**` and `- **Expected Outcome**` blocks for TC-03, GB-02, and GB-03 in Section 4.
   - Insert Section `8.2 Compiler Production Hardening Directives (Milestone M3/M4 Contract)` documenting coordinate clamping, zero-canvas validation, and button name fallback.
3. Update `tests/test_specification.py` to include `test_all_9_blueprints_have_workflows_and_outcomes` so this defect is continuously prevented.
4. Run verification tests:
   - Run the challenger reproduction check:
     `python -c "import re; c=open(r'c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md', encoding='utf-8').read(); bps=['BK-01','BK-02','BK-03','TC-01','TC-02','TC-03','GB-01','GB-02','GB-03']; [re.search(rf'#### 4\.[123]\.[123]\s+Use Case {bp}:(.*?)(?=#### 4\.[123]\.[123]|---|\Z)', c, re.DOTALL) for bp in bps]; print('All 9 checked')"`
   - Run the full test suite: `python -m pytest tests/`
   - Assert all tests pass!
5. Write your handoff report to `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_fix_worker_1\handoff.md`.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.


## 2026-11-04T22:48:06Z
You are m1_fix_worker_1.
Your working directory is: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_fix_worker_1
Your task instructions are in: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_fix_worker_1\DISPATCH.md
Read c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md, c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md, c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_fix_explorer_1\report.md, and your DISPATCH.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Apply the remediation to docs/SPECIFICATION.md and tests/test_specification.py. Run pytest verification and deliver handoff.md. Report back via send_message when complete.
