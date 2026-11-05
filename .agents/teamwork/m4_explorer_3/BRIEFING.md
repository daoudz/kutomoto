# BRIEFING — 2026-11-05T03:50:00Z

## Mission
Investigate and design:
1. Step-by-Step Flow Builder (`src/kutomoto/ui/js/runner.js`)
2. Target Window Selector & Countdown HUD (`src/kutomoto/ui/js/runner.js`)
3. Windows Launcher & CLI Entry Point (`src/kutomoto/__main__.py`, `run_kutomoto.bat`)
4. Test Suite Design for `tests/test_api.py`

## 🔒 My Identity
- Archetype: explorer
- Roles: workflow UI, countdown HUD, CLI launchers, and API test suites
- Working directory: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_explorer_3\
- Original parent: 59700fc9-320d-4ed3-b1db-2fc709fed831
- Milestone: M4

## 🔒 Key Constraints
- Read-only investigation — do NOT implement in src/ or tests/
- Write only to c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_explorer_3\
- Synthesize all findings and proposals in handoff.md

## Current Parent
- Conversation ID: 59700fc9-320d-4ed3-b1db-2fc709fed831
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `docs/SPECIFICATION.md` (Sections 7.2, 7.3, 8.1, 9.1-9.3, 10.1-10.2)
  - `src/kutomoto/engine/schema.py` (KutomotoWorkflow, WorkflowStep, StepParameters, ActionType, ExecutionSettings)
  - `src/kutomoto/engine/runner.py` (WorkflowRunner, ExecutionContext, FSM transitions, countdown telemetry)
  - `src/kutomoto/automation/win32_window.py` (WindowInfo, enumerate_windows, find_window)
  - `src/kutomoto/designer/compiler.py` (compile_visual_layout_to_workflow)
  - `src/kutomoto/__main__.py` (CLI skeleton)
  - `tests/conftest.py` & existing test suite
- **Key findings**:
  - Complete schema compatibility established across Pydantic models and frontend data representations.
  - Edge App Mode integration parameters mapped (`--app=http://...`, `--window-size`, `--window-position`).
  - WebSocket telemetry protocol formalized with `WorkflowRunner._emit_telemetry` hooks.
  - Comprehensive TestClient test matrix formulated for `tests/test_api.py`.
- **Unexplored areas**: None within M4-Explorer-3 scope.

## Key Decisions Made
- `runner.js` will encapsulate the Step Flow Builder, Window Selector, 3-second Countdown HUD, and Execution Console into unified, modular JavaScript components.
- `__main__.py` includes background health polling thread before invoking Edge in App Mode (`msedge.exe --app=...`) with seamless fallback to `webbrowser.open()`.
- `run_kutomoto.bat` incorporates 90Studio banner, Python environment verification, UTF-8 codepage switch, and error-pause guardrails.
- `tests/test_api.py` includes isolated mock driver testing covering all REST routes, WebSocket streaming, and 90Studio branding enforcement.

## Artifact Index
- c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_explorer_3\DISPATCH.md — Dispatch log
- c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_explorer_3\BRIEFING.md — Working memory index
- c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_explorer_3\progress.md — Liveness heartbeat
- c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_explorer_3\handoff.md — Complete architectural handoff report
