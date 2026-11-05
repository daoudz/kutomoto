## 2026-11-05T03:52:00Z
You are m4_worker_1, an implementation worker.
Working directory: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_worker_1\

MANDATORY INPUTS (read before starting):
- ORIGINAL_REQUEST.md: c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md
- PROJECT.md: c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md
- Explorer 1 Report (API Server & WebSockets): c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_explorer_1\handoff.md
- Explorer 2 Report (Canvas Designer & Enterprise UI): c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_explorer_2\handoff.md
- Explorer 3 Report (Flow Builder, HUD, Launcher & API Tests): c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_explorer_3\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

EXCLUSIVE FILE WRITE OWNERSHIP:
You exclusively own and may create/edit:
- c:\Users\daoud\projects\kutomoto\src\kutomoto\server\ (all files)
- c:\Users\daoud\projects\kutomoto\src\kutomoto\ui\ (all files)
- c:\Users\daoud\projects\kutomoto\src\kutomoto\__main__.py
- c:\Users\daoud\projects\kutomoto\run_kutomoto.bat
- c:\Users\daoud\projects\kutomoto\tests\test_api.py

MISSION:
Implement Milestone 4: Enterprise UI Application & 90Studio Branding (R4) based on the comprehensive blueprints provided by the 3 explorers:
1. `src/kutomoto/server/`:
   - Implement `__init__.py` and `app.py`:
     - FastAPI application with CORS middleware, lifespan events, and static file mount for `src/kutomoto/ui/` at `/`.
     - Data storage: `data/workflows/` JSON storage.
     - Endpoints:
       - `GET /api/health`: returns `{"status": "ok", "app": "kutomoto", "version": "1.0.0", "copyright": "Copyrights reserved to 90Studio"}`
       - `GET /api/workflows`: list all saved workflows
       - `POST /api/workflows`: validate and save `KutomotoWorkflow` JSON
       - `GET /api/workflows/{workflow_id}`: get workflow by id
       - `DELETE /api/workflows/{workflow_id}`: delete workflow
       - `POST /api/designer/compile`: accept `VisualFormLayout` JSON, compile via `compile_visual_layout_to_workflow()`, return generated `KutomotoWorkflow`
       - `GET /api/windows`: list active desktop windows using `kutomoto.automation.win32_window` (handle, title, rect, process)
       - `POST /api/execute/start`: start execution of workflow (by id or payload) asynchronously using `WorkflowRunner`
       - `POST /api/execute/pause`: pause runner
       - `POST /api/execute/resume`: resume runner
       - `POST /api/execute/abort`: emergency abort runner
       - `GET /api/execute/status`: current runner state and active step
     - WebSocket `/ws/execution`:
       - Real-time broadcast channel streaming state changes, step start/complete events, and audit logs.
2. `src/kutomoto/ui/`:
   - `index.html`: Enterprise Single Page Application layout, kutomoto branding, "Copyrights reserved to 90Studio" header watermark and footer, tab navigation (Visual Designer, Step Flow Builder, Live Console, Target Windows, Settings).
   - `css/kutomoto.css`: Professional corporate dark slate/navy theme (`#0d1117`, `#161b22`, `#1f6feb`, `#8957e5`), responsive layout, 8 resize handles, magnetic snap guides, badges, countdown overlay modal, execution console styling.
   - `js/app.js`: Master UI coordinator, tab manager, toast notifications, WebSocket client connecting to `/ws/execution`.
   - `js/designer.js`: HTML5 Canvas visual form designer:
     - Drag to draw boxes (discarding jitter < 10px)
     - Select, move, snap to 8px/16px grid
     - 8 directional resize handles
     - Sequence badges rendered on boxes: `[#1]`, `[#2]` showing execution order
     - Box property editor sidebar: Name, Label, Action Type (Text, Click, Checkbox, KeyPress, Submit), Value, Navigation, Force Click toggle, Timing (pre/post delay)
     - Import/Export layout JSON matching `VisualFormLayout`
     - "Compile to Workflow" button calling `/api/designer/compile`
   - `js/runner.js`:
     - Step-by-Step Flow Builder: sequential step table/cards, add/edit/delete/reorder steps, parameter editor.
     - Target window selector dropdown populated via `/api/windows`.
     - 3-second Countdown HUD modal ("Switching to Target Window in 3... 2... 1... Press Escape to cancel"), triggering execution via `/api/execute/start`.
     - Live Execution Console: step progress bar, current step highlighter, live log viewer with 90Studio audit watermark, Pause/Resume/Abort controls.
3. Windows Launcher & CLI Entry Point:
   - `src/kutomoto/__main__.py`: CLI arguments (`--host`, `--port`, `--no-browser`, `--mock`), launches Uvicorn server, and opens Microsoft Edge in App Mode (`msedge.exe --app=http://127.0.0.1:8765`) or default browser.
   - `run_kutomoto.bat`: Batch script to launch on Windows.
4. Test Suite (`tests/test_api.py`):
   - Implement the comprehensive FastAPI `TestClient` tests designed by explorer 3 covering:
     - Health check endpoint & 90Studio branding verification
     - Workflow CRUD endpoints
     - Designer compile endpoint
     - Windows enumeration endpoint
     - Execution lifecycle (start, pause, resume, abort, status)
     - WebSocket streaming events
5. Verification:
   - Run `python -m pytest tests/test_api.py -v`
   - Run `python -m pytest tests/ -v`
   - Run `python -m ruff check src/ tests/`
   - Verify 100% test pass rate and 0 lint errors.

DELIVERABLE:
Write your complete handoff report to `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_worker_1\handoff.md` documenting all files created, test outputs, and verification results.
Notify parent via send_message when done.
