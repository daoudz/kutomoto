# Dispatch for m2_explorer_3

## Objective
Explore safety guardrails, failure recovery, and mock testing infrastructure for the automation core and workflow engine in Milestone 2.

## Inputs
- ORIGINAL_REQUEST: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md`
- Master Architecture: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md`
- Master Specification: `c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md` (specifically Section 3 edge cases, Section 6.5 safety, Section 9.3 focus guardian)

## Instructions
1. Formulate the implementation of `src/kutomoto/engine/safety.py`:
   - Screen-corner failsafe: monitor mouse cursor; if positioned at (0,0) or (max_x, 0), immediately trigger safety stop.
   - Emergency Escape abort hotkey: background listener for `VK_ESCAPE` to transition FSM to `STOPPING` -> `ERROR`.
   - Loss-of-Focus Guardian: pre-step check verifying `GetForegroundWindow() == target_hwnd`; trigger auto-pause or target re-activation if focus was stolen (Edge case E13).
   - Accidental mouse movement disturbance detector: Euclidean distance check during execution (Edge case E08).
2. Design the mock driver & test harness:
   - Provide a clean `MockWin32Driver` that records all clicks, typed text, key presses, and window activations.
   - Design comprehensive unit test suites: `tests/test_win32_driver.py` and `tests/test_engine.py` verifying all 10 action handlers, all 18 FSM transitions, safety triggers, and audit logging.
3. Write your report to `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_explorer_3\report.md` and deliver `handoff.md`.


## 2026-11-04T22:58:36Z
[Message] sender=ce2dd708-d288-4e8f-9834-dfdb673a5856
You are m2_explorer_3.
Your working directory is: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_explorer_3
Your task instructions are in: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_explorer_3\DISPATCH.md
Read c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md, c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md, c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md, and your DISPATCH.md.
Formulate the safety guardrails (safety.py: Escape abort, corner failsafe, focus guardian) and test harness design (MockWin32Driver, tests/test_win32_driver.py, tests/test_engine.py).
Write your report to c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_explorer_3\report.md and deliver handoff.md. Report back via send_message when done.
