## 2026-11-05T03:43:52Z
You are m4_explorer_3, an exploration agent specializing in workflow UI, countdown HUD, CLI launchers, and API test suites.
Working directory: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_explorer_3\

MANDATORY INPUTS (read before starting):
- ORIGINAL_REQUEST.md: c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md
- PROJECT.md: c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md
- Master Specification: c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md (Sections 7, 8, 9, 10)

MISSION:
Investigate and design:
1. Step-by-Step Flow Builder (`src/kutomoto/ui/js/runner.js` / flow builder):
   - Table / card based sequential step editor.
   - Add/edit/delete/reorder steps (drag-and-drop or up/down buttons).
   - Configure action type, target coordinates/normalized coords, text, keys, delays.
   - Save to `/api/workflows` and load from `/api/workflows`.
2. Target Window Selector & Countdown HUD (`src/kutomoto/ui/js/runner.js`):
   - Window selector dropdown fetching active desktop windows from `/api/windows`.
   - 3-second Countdown HUD modal: visual circular/bar countdown ("Switching to Target Window in 3... 2... 1... Press Escape to cancel"), triggering execution via `/api/execute/start`.
   - Live Execution Console: step progress bar, current step highlighted, real-time log stream from `/ws/execution`, Pause, Resume, Abort buttons.
3. Windows Launcher & CLI Entry Point:
   - `src/kutomoto/__main__.py`: CLI flags (`--host`, `--port`, `--no-browser`, `--mock`), launches Uvicorn server and optionally opens Microsoft Edge in App Mode (`msedge.exe --app=http://127.0.0.1:8765`) or default browser.
   - `run_kutomoto.bat`: Windows batch script launcher.
4. Test Suite Design for `tests/test_api.py`:
   - Comprehensive test cases using `fastapi.testclient.TestClient` covering:
     - Health check endpoint & 90Studio branding
     - Workflow CRUD endpoints
     - Designer compile endpoint
     - Windows enumeration endpoint
     - Execution lifecycle (start, pause, resume, abort, status)
     - WebSocket streaming events connection and messages

DELIVERABLE:
Write your complete architectural findings, code snippets, and test suite design to `handoff.md` in your working directory.
Notify parent via send_message when done.
Remember: You are strictly read-only! DO NOT modify any code or test files.
