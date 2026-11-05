# Dispatch for m2_explorer_2

## Objective
Explore and provide the precise implementation blueprint for the Workflow Execution Engine (`src/kutomoto/engine/`) in Milestone 2.

## Inputs
- ORIGINAL_REQUEST: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md`
- Master Architecture: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md`
- Master Specification: `c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md` (specifically Sections 7.3, 9, 10)

## Instructions
1. Inspect `docs/SPECIFICATION.md` Section 7.3 (KutomotoWorkflow Unified Action Schema), Section 9 (Execution Engine Runtime & 7-State FSM), and Section 10 (90Studio Compliance Audit Trail).
2. Formulate the exact implementation structure for:
   - `src/kutomoto/engine/schema.py`: Pydantic V2 models for all 10 atomic actions (`focus_window`, `click`, `type_text`, `key_press`, `hotkey`, `clear_field`, `delay`, `submit`, `scroll`, `prompt_user_input`), target application configuration, step definitions, recovery policies (`ABORT`, `RETRY`, `PROMPT`, `SKIP`), and the root `KutomotoWorkflow` model with 90Studio copyright default.
   - `src/kutomoto/engine/fsm.py`: 7-State FSM (`IDLE`, `VALIDATING`, `COUNTDOWN`, `RUNNING`, `PAUSED`, `STOPPING`, `COMPLETED`, `ERROR`) implementing the 18 state transitions (T01–T18).
   - `src/kutomoto/engine/runner.py`: Asynchronous workflow executor (`WorkflowRunner`) coordinating step execution, inter-step delays, step telemetry callbacks, event streaming, and error handling.
   - `src/kutomoto/engine/audit.py`: 90Studio compliance audit logger emitting structured JSON events with credential masking (`is_secret`).
3. Detail unit and integration test strategies for FSM transitions and workflow execution.
4. Write your report to `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_explorer_2\report.md` and deliver `handoff.md`.

## 2026-11-04T22:58:36Z
Message from ce2dd708-d288-4e8f-9834-dfdb673a5856:
Formulate the exact implementation blueprint for src/kutomoto/engine/ (schema.py with 10 actions, fsm.py with 18 transitions, runner.py, audit.py).
Write your report to c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_explorer_2\report.md and deliver handoff.md. Report back via send_message when done.
