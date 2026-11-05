## 2026-11-05T03:29:56Z
You are m3_it2_challenger_1, an empirical challenger and verifier.
Working directory: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_it2_challenger_1\

MANDATORY INPUTS (read before starting):
- ORIGINAL_REQUEST.md: c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md
- PROJECT.md: c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md
- Worker Handoff: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_fix_worker_1\handoff.md
- Target files:
  - c:\Users\daoud\projects\kutomoto\src\kutomoto\designer\compiler.py
  - c:\Users\daoud\projects\kutomoto\src\kutomoto\designer\schema.py
  - c:\Users\daoud\projects\kutomoto\tests\test_compiler.py

MISSION:
Perform empirical adversarial testing and stress-testing on the updated compiler and schema:
1. Spatial Band Sorting Stress:
   - Dynamic band clustering across jittered coordinates, zigzags, sub-pixel offsets, and explicit sequence indices.
   - Verify `sequence_index: ge=1` rejection on 0 or negative values in Pydantic schema validation.
2. Boundary and Extreme Geometries:
   - 1x1 canvas, 4K canvas, sub-pixel dimensions, extreme edge coordinates.
3. Large Layout Compilation Performance:
   - Benchmark compilation speed on 100-field, 200-field, and 500-field layouts. Target: < 100ms.
4. Peephole Optimizations Stress:
   - Delay coalescing, 0ms delay pruning, settling delay transfer, and duplicate focus window pruning.
5. Provide your explicit verdict: PASS or FAIL.

DELIVERABLE:
Write your empirical challenge harness script and full report to c:\Users\daoud\projects\kutomoto\.agents\teamwork\m3_it2_challenger_1\handoff.md.
Notify parent via send_message when done.
