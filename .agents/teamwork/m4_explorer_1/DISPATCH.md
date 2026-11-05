## 2026-11-05T03:43:36Z
You are m4_explorer_1, an exploration and specification mining agent.
Working directory: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_explorer_1\

MANDATORY INPUTS (read before starting):
- ORIGINAL_REQUEST.md: c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md
- PROJECT.md: c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md
- Master Specification: c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md (Sections 8, 9, 10)
- Existing code:
  - c:\Users\daoud\projects\kutomoto\src\kutomoto\engine\
  - c:\Users\daoud\projects\kutomoto\src\kutomoto\designer\
  - c:\Users\daoud\projects\kutomoto\src\kutomoto\automation\

MISSION:
Investigate and design the Backend REST & WebSocket Server (`src/kutomoto/server/app.py`):
1. Review requirements for F16 (Backend API Server):
   - FastAPI application setup, CORS middleware, lifespan event handlers.
   - REST endpoints:
     - `GET /api/health`: system health, version, branding "Copyrights reserved to 90Studio"
     - `GET /api/workflows`: list saved workflows
     - `POST /api/workflows`: save workflow payload (validated by KutomotoWorkflow)
     - `GET /api/workflows/{id}`: retrieve workflow
     - `DELETE /api/workflows/{id}`: delete workflow
     - `POST /api/designer/compile`: compile VisualFormLayout into KutomotoWorkflow
     - `GET /api/windows`: list active desktop windows using `kutomoto.automation.win32_window` (handle, title, process, rect)
     - `POST /api/execute/start`: start execution asynchronously with WorkflowRunner
     - `POST /api/execute/pause`, `POST /api/execute/resume`, `POST /api/execute/abort`: execution control
     - `GET /api/execute/status`: current runner state and active step
   - WebSocket `/ws/execution`:
     - Real-time event subscription broadcasting state transitions, step starts/finishes, countdown ticks, and audit logs.
   - Static files: mount `src/kutomoto/ui/` at `/` to serve the web interface.
2. Formulate concrete code structure, dependencies (FastAPI, Uvicorn, WebSockets), error handling, and concurrency architecture.

DELIVERABLE:
Write your complete architectural findings and concrete code recommendations to `handoff.md` in your working directory.
Notify parent via send_message when done.
Remember: You are strictly read-only! DO NOT modify any code or test files.
