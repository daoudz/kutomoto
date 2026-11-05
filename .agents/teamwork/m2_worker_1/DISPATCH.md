# Dispatch for m2_worker_1 (Milestone 2)

## Objective
Implement the complete Win32 Automation Core (`src/kutomoto/automation/`) and Workflow Execution Engine (`src/kutomoto/engine/`) for kutomoto, along with comprehensive test suites in `tests/test_win32_driver.py` and `tests/test_engine.py`.

## Exclusive Write Ownership
You exclusively own and may write to:
- `src/kutomoto/__init__.py`
- `src/kutomoto/__main__.py`
- `src/kutomoto/automation/*`
- `src/kutomoto/engine/*`
- `tests/test_win32_driver.py`
- `tests/test_engine.py`
- Files within your own directory `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_worker_1\`

DO NOT touch `docs/SPECIFICATION.md` or any files in `src/kutomoto/designer/` or `src/kutomoto/server/`.

## Inputs
- ORIGINAL_REQUEST: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md`
- Master Architecture: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md`
- Master Specification: `c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md` (Sections 6, 7.3, 9, 10)
- M2_1 Automation Blueprint: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_explorer_1\report.md`
- M2_2 Engine Blueprint: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_explorer_2\report.md`
- M2_3 Safety & Test Blueprint: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_explorer_3\report.md`

## Instructions
1. Review the three explorer blueprints thoroughly.
2. Implement the Win32 Automation Core:
   - `src/kutomoto/__init__.py`: Package metadata, version `"1.0.0"`, and branding attribution `__copyright__ = "Copyrights reserved to 90Studio"`.
   - `src/kutomoto/automation/win32_core.py`: Per-Monitor V2 DPI awareness ladder (`SetProcessDpiAwarenessContext(-4)`), 40-byte 64-bit ABI `INPUT` struct hierarchy, explicit 64-bit `argtypes`/`restype`, Virtual Key constants and mapping.
   - `src/kutomoto/automation/win32_input.py`: `send_click`, `send_mouse_move`, `send_text` (with `KEYEVENTF_UNICODE` and UTF-16 surrogate pairs for emojis/non-BMP chars), `send_key_press`, `send_hotkey`, `clear_field`, `release_all_modifiers`, and Unicode clipboard fallback.
   - `src/kutomoto/automation/win32_window.py`: `enumerate_windows`, `find_window` (regex & process name matching), `activate_target_window` (`AttachThreadInput` + `ShowWindow` + `SetForegroundWindow`), normalized client coordinate mapping.
3. Implement the Workflow Execution Engine:
   - `src/kutomoto/engine/schema.py`: Pydantic V2 models for 10 atomic actions (`focus_window`, `click`, `type_text`, `key_press`, `hotkey`, `clear_field`, `delay`, `submit`, `scroll`, `prompt_user_input`), target application config, step definitions, recovery policies, root `KutomotoWorkflow` model with 90Studio copyright default.
   - `src/kutomoto/engine/fsm.py`: 7-State FSM (`IDLE`, `VALIDATING`, `COUNTDOWN`, `RUNNING`, `PAUSED`, `STOPPING`, `COMPLETED`, `ERROR`) implementing transitions T01–T18.
   - `src/kutomoto/engine/safety.py`: Screen-corner failsafe, emergency Escape abort hotkey, Loss-of-Focus Guardian (E13), accidental mouse disturbance detector (E08), and `MockWin32Driver`.
   - `src/kutomoto/engine/audit.py`: Structured 90Studio compliance audit logger with credential masking.
   - `src/kutomoto/engine/runner.py`: Asynchronous `WorkflowRunner` loop coordinating step execution, delays, telemetry callbacks, event streaming, variable interpolation, and error recovery policies.
4. Implement Test Suites:
   - `tests/test_win32_driver.py`: Verify struct sizes (INPUT=40B, etc.), DPI awareness, input generation, surrogate pairs, and mock window enumeration.
   - `tests/test_engine.py`: Verify all 10 action handlers, all 18 FSM transitions, safety triggers, audit logging with secret masking, and recovery policies.
5. Verification:
   - Run `python -m pytest tests/ -v`
   - Assert all tests pass! Document passing test results with command and output in your handoff report.
6. Write your handoff report to `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_worker_1\handoff.md`.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.


## 2026-11-04T23:06:53Z
[Message] timestamp=2026-11-04T23:06:53Z sender=ce2dd708-d288-4e8f-9834-dfdb673a5856 priority=MESSAGE_PRIORITY_HIGH content=You are m2_worker_1.
Your working directory is: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_worker_1
Your task instructions are in: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_worker_1\DISPATCH.md
Read c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md, c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md, c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md, and your DISPATCH.md.
