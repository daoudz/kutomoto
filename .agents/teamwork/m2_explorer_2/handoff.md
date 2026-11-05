# Handoff Report: Workflow Execution Engine Architecture Blueprint

**Agent**: `m2_explorer_2`  
**Working Directory**: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_explorer_2`  
**Recipient**: `ce2dd708-d288-4e8f-9834-dfdb673a5856` (Parent Orchestrator)  
**Date**: 2026-11-04  
**Status**: Hard Handoff (Investigation & Blueprint Formulation Complete)  

---

## 1. Observation

1. **Task Dispatch & Objectives**:
   - `DISPATCH.md` lines 12–19 instruct:
     > "1. Inspect docs/SPECIFICATION.md Section 7.3 (KutomotoWorkflow Unified Action Schema), Section 9 (Execution Engine Runtime & 7-State FSM), and Section 10 (90Studio Compliance Audit Trail).
     > 2. Formulate the exact implementation structure for:
     >    - src/kutomoto/engine/schema.py: Pydantic V2 models for all 10 atomic actions (focus_window, click, type_text, key_press, hotkey, clear_field, delay, submit, scroll, prompt_user_input), target application configuration, step definitions, recovery policies (ABORT, RETRY, PROMPT, SKIP), and the root KutomotoWorkflow model with 90Studio copyright default.
     >    - src/kutomoto/engine/fsm.py: 7-State FSM (IDLE, VALIDATING, COUNTDOWN, RUNNING, PAUSED, STOPPING, COMPLETED, ERROR) implementing the 18 state transitions (T01–T18).
     >    - src/kutomoto/engine/runner.py: Asynchronous workflow executor (WorkflowRunner) coordinating step execution, inter-step delays, step telemetry callbacks, event streaming, and error handling.
     >    - src/kutomoto/engine/audit.py: 90Studio compliance audit logger emitting structured JSON events with credential masking (is_secret).
     > 3. Detail unit and integration test strategies for FSM transitions and workflow execution.
     > 4. Write your report to c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_explorer_2\report.md and deliver handoff.md."

2. **Unified Action Workflow Schema (Section 7.3)**:
   - `docs/SPECIFICATION.md` lines 1271–1422 establish the Draft 2020-12 JSON Schema for `KutomotoWorkflow`.
   - Required root properties: `"schema_version"`, `"id"`, `"name"`, `"target_application"`, `"execution_settings"`, `"steps"`, `"copyright"`.
   - Copyright constraint: `"copyright": { "type": "string", "const": "Copyrights reserved to 90Studio" }`.
   - Step actions: 10 atomic actions (`focus_window`, `click`, `type_text`, `key_press`, `hotkey`, `clear_field`, `delay`, `submit`, `scroll`, `prompt_user_input`).
   - Parameters include `norm_x`, `norm_y` (normalized [0..1]), `coordinate_mode` (`screen`, `window_client`, `normalized`), `is_secret`, `keystroke_delay_ms`, `clear_strategy`, `submit_method`.

3. **7-State FSM & 18 Transition Matrix (Section 9.1 & 9.2)**:
   - `docs/SPECIFICATION.md` lines 1804–1882 define the FSM lifecycle and formal state transition matrix:
     - T01: `IDLE` + `EXECUTE_START` -> `VALIDATING`
     - T02: `VALIDATING` + `VALIDATION_OK` -> `COUNTDOWN`
     - T03: `VALIDATING` + `VALIDATION_FAILED` -> `ERROR`
     - T04: `COUNTDOWN` + `COUNTDOWN_TICK` -> `COUNTDOWN`
     - T05: `COUNTDOWN` + `COUNTDOWN_DONE` -> `RUNNING`
     - T06: `COUNTDOWN` + `ABORT_TRIGGERED` -> `STOPPED`
     - T07: `RUNNING` + `STEP_SUCCESS` -> `RUNNING`
     - T08: `RUNNING` + `ALL_STEPS_DONE` -> `COMPLETED`
     - T09: `RUNNING` + `USER_PAUSE` -> `PAUSED`
     - T10: `RUNNING` + `FOCUS_LOST` -> `PAUSED`
     - T11: `RUNNING` + `ABORT_TRIGGERED` -> `STOPPING`
     - T12: `RUNNING` + `STEP_EXCEPTION` -> `ERROR_RECOVERY`
     - T13: `PAUSED` + `USER_RESUME` -> `RUNNING`
     - T14: `PAUSED` + `ABORT_TRIGGERED` -> `STOPPED`
     - T15: `ERROR_RECOVERY` + `POLICY_RETRY` -> `RUNNING`
     - T16: `ERROR_RECOVERY` + `POLICY_SKIP` -> `RUNNING`
     - T17: `ERROR_RECOVERY` + `POLICY_ABORT` -> `ERROR`
     - T18: `STOPPING` + `CLEANUP_DONE` -> `STOPPED`

4. **Structured Audit Log Schema (Section 10.1 & 10.2)**:
   - `docs/SPECIFICATION.md` lines 1896–1972 establish the schema for `KutomotoAuditLog`.
   - Requires `"system": "kutomoto"`, `"copyright": "Copyrights reserved to 90Studio"`.
   - Requires `execution_id`, `workflow_id`, `workflow_name`, `timestamp_utc`, `operator_username`, `host_machine`, `target_application`, `execution_summary`, and `step_events`.
   - Each step event records `step_index`, `action_type`, `timestamp_offset_ms`, `parameters_summary`, `latency_ms`, `status` (`SUCCESS`, `ERROR`, `SKIPPED`, `RETRIED`).
   - Line 724 / US-ERR-02: Sensitive password fields (`is_secret=True`) must be masked as `"********"`.

5. **Runtime Environment & Python Dependencies**:
   - Environment check confirmed Python 3.14 (`C:\Python314\python.exe`), `pydantic` 2.12.5, `fastapi` 0.128.0, `uvicorn` 0.40.0, and `pytest` 9.0.2 with `pytest-asyncio` 1.3.0.
   - Existing 28 tests in `tests/test_specification.py` and `tests/test_spec_empirical_challenge.py` pass cleanly.

---

## 2. Logic Chain

1. **Derivation of `src/kutomoto/engine/schema.py`**:
   - From Observation 2, `KutomotoWorkflow` must adhere to Draft 2020-12 schema rules.
   - Pydantic V2 models provide runtime validation, automatic casting, JSON schema export, and serialization.
   - Defining `ActionType`, `ErrorRecoveryPolicy`, `TargetAppType`, `MatchMode`, `CoordinateMode`, and `ClearStrategy` as `str, Enum` preserves JSON serializability.
   - Creating individual parameter models (`FocusWindowParameters`, `ClickParameters`, etc.) alongside a consolidated `StepParameters` model provides both granular typing and schema compliance.
   - Field validators on `copyright` guarantee that any workflow without `"Copyrights reserved to 90Studio"` fails validation.

2. **Derivation of `src/kutomoto/engine/fsm.py`**:
   - From Observation 3, the runtime lifecycle encompasses 18 distinct transitions (T01–T18).
   - An immutable transition table mapping `(CurrentState, TriggerEvent) -> NextState` guarantees deterministic state progression.
   - Any attempt to trigger an unmapped transition raises `InvalidTransitionError`, satisfying the requirement to block illegal operations (e.g. `COMPLETED` -> `RUNNING`).
   - Adding `RESET` transitions from terminal states (`COMPLETED`, `STOPPED`, `ERROR`) back to `IDLE` allows the engine to be cleanly re-armed.
   - Supporting both sync and async listener hooks ensures real-time event streaming over WebSockets without blocking the main event loop.

3. **Derivation of `src/kutomoto/engine/runner.py`**:
   - From Observation 2, 3, and 5, `WorkflowRunner` must execute sequentially in an asynchronous loop (`asyncio`).
   - Pre-step checks verify the Loss-of-Focus Guardian: `GetForegroundWindow() == target_hwnd`. When focus is stolen (Edge case E13), it triggers `FOCUS_LOST` (T10), pausing execution to avoid blind typing.
   - Each of the 10 atomic actions has a dedicated handler method mapping step parameters to `IWin32Driver` primitives (`send_click`, `send_text`, `send_key_press`, `send_hotkey`, `clear_field`, `send_scroll`, etc.).
   - Dynamic parameter interpolation allows resolving `{{variable_name}}` templates against runtime context variables.
   - Sleep intervals for delays and countdowns are partitioned into non-blocking slices to allow immediate abort response (< 50ms) upon `ABORT_TRIGGERED` (T11).

4. **Derivation of `src/kutomoto/engine/audit.py`**:
   - From Observation 4, structured audit records must match Section 10.1 schema.
   - `CredentialMasker` redacts strings for actions where `is_secret=True`, substituting `"********"` in `parameters_summary`.
   - `AuditLogger` records monotonic offsets (`timestamp_offset_ms`) and per-step latencies, writing formatted JSON files stamped with 90Studio copyright upon completion or abort.

5. **Derivation of Test Strategy**:
   - `tests/test_fsm.py` tests all 18 transitions individually, verifying valid transitions and rejecting illegal transitions.
   - `tests/test_runner.py` utilizes a `MockWin32Driver` to verify all 10 actions, timing delays, variable binding, pause/resume, and retry/skip policies without requiring real OS window interaction.
   - `tests/test_audit.py` validates output records against the Section 10.1 schema and verifies secret masking.

---

## 3. Caveats

1. **Safety Module Boundary**:
   - Screen-corner failsafe detection (`(0, 0)` coordinates) and global hotkey polling (`VK_ESCAPE`) are assigned to `m2_explorer_3` in `src/kutomoto/engine/safety.py`. `WorkflowRunner` integrates via `ctx.abort_requested` and safety callbacks.
2. **Win32 Implementation Boundary**:
   - `src/kutomoto/automation/` implementation details (ctypes memory layout, Per-Monitor DPI initialization, `KEYEVENTF_UNICODE` buffers) are assigned to `m2_explorer_1`. The engine interfaces strictly via the `IWin32Driver` contract.
3. **Prompt User Input UI Interaction**:
   - In automated test and headless environments, `prompt_user_input` resolves via a mock resolver. When integrated with FastAPI/WebSockets in Milestone 4, it will await an incoming WebSocket message from the frontend.

---

## 4. Conclusion

The blueprint in `report.md` provides complete, unambiguous, and production-ready architectures for:
- `src/kutomoto/engine/schema.py`: Pydantic V2 models for all 10 atomic actions, target configuration, recovery policies, and `KutomotoWorkflow` with mandatory 90Studio copyright watermark.
- `src/kutomoto/engine/fsm.py`: Complete FSM encoding all 18 transitions (T01–T18) with transition validation and lifecycle listener callbacks.
- `src/kutomoto/engine/runner.py`: Asynchronous `WorkflowRunner` coordinating all 10 action handlers, pre-step focus verification, variable substitution, inter-step delays, and retry/skip error handling.
- `src/kutomoto/engine/audit.py`: Tamper-evident 90Studio compliance audit logger with credential masking (`is_secret`) and JSON file export.
- Test suites covering all transitions, actions, error recoveries, and schema invariants.

This directly unblocks Milestone 2 implementation workers to write clean, fully tested code without ambiguities.

---

## 5. Verification Method

To independently verify the blueprint and its baseline:
1. **Inspect Blueprint**:
   - Read `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_explorer_2\report.md`.
2. **Verify Schema Alignment**:
   - Compare `report.md` Section 2 with `docs/SPECIFICATION.md` Section 7.3.
3. **Verify FSM Transition Completeness**:
   - Cross-check the 18 transitions in `report.md` Section 3 against `docs/SPECIFICATION.md` Section 9.2 (T01 through T18).
4. **Verify Existing Spec Test Suite**:
   ```powershell
   python -m pytest tests/ -v
   ```
   Must pass all 28 tests without regression.
5. **Invalidation Conditions**:
   - If Section 7.3 or 9.2 in `SPECIFICATION.md` changes the action schema or state transitions, `report.md` must be updated accordingly.
