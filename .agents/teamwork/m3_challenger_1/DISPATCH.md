# Milestone 3 Challenger 1: Compiler Empirical Stress Verifier
Scope: Stress-test compiler.py and schema.py with adversarial layouts
Verify: Write test generators, extreme grid shapes, zero/negative coordinates, non-Western reading orders, large forms (100+ fields), benchmark execution speed.
Output: handoff.md with verdict (PASS / FAIL).

## 2026-11-05T00:33:25Z
From: ce2dd708-d288-4e8f-9834-dfdb673a5856
Priority: MESSAGE_PRIORITY_HIGH

You are m3_challenger_1 (Role: Milestone 3 Compiler Stress Challenger).
Your working directory is: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_challenger_1
Your parent conversation ID is: ce2dd708-d288-4e8f-9834-dfdb673a5856

MANDATORY INPUT - Read this file first:
c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md

MISSION:
Adversarially challenge and stress-test `src/kutomoto/designer/compiler.py` and `src/kutomoto/designer/schema.py`.

CHALLENGE VECTORS:
1. Spatial Band Sorting Stress:
   - What happens with complex multi-column forms with sub-pixel or 1px vertical offsets?
   - What happens with zigzag or spiraling coordinates?
   - Does explicit `sequence_index` strictly override spatial sorting even when explicit indices are out of spatial order?
2. Extreme Geometries:
   - Can any box have `x + width > canvas.width` or `y + height > canvas.height` slip past validation?
   - What happens with 1x1 pixel boxes? Canvas of 1x1?
   - What happens with negative coordinates or negative dimensions?
3. Large Layout Scalability:
   - Generate a 100-field and 200-field form layout. Does compilation complete in < 100ms?
4. Write your own empirical stress test script in your working directory and run it via `python`.

VERIFICATION:
Run full project tests:
`python -m pytest tests/ -v`

DELIVERABLE:
Write your structured report in `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_challenger_1\handoff.md` with an explicit verdict: **PASS** or **FAIL**.
Send a completion message via `send_message` to parent `ce2dd708-d288-4e8f-9834-dfdb673a5856`.

