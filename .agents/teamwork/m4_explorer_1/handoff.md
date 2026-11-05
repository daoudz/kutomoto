# Milestone 4 Exploration & Architectural Specification: Backend REST & WebSocket Server

**Author**: m4_explorer_1 (Specification Miner & Explorer)  
**Date**: 2026-11-05T03:55:00Z  
**Target Milestone**: Milestone 4 (F16 Backend API Server & Web Server)  
**Target Module**: `src/kutomoto/server/app.py`  
**Attribution Requirement**: Mandatory watermark `"Copyrights reserved to 90Studio"`  

---

## 1. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Server Core | FastAPI Application & Lifespan | Async ASGI application instance configured with CORS middleware, lifespan manager for startup DPI initialization and graceful shutdown cleanup. | ASGI lifecycle events | Running HTTP/WS service on `127.0.0.1:8765` | Logs error, unbinds port, cleans up modifier keys on abort | `SPECIFICATION.md` §1.3, §2 (F16), `PROJECT.md` |
| 2 | REST Health | `GET /api/health` | System health probe returning system name, version, timestamp, runner state, DPI awareness, and mandatory 90Studio branding. | None | JSON object with `status: "healthy"`, `system: "kutomoto"`, `version`, `copyright: "Copyrights reserved to 90Studio"` | Returns 500 RFC 7807 if internal health check fails | Dispatch prompt, `SPECIFICATION.md` §2 (F16) |
| 3 | REST Workflows | `GET /api/workflows` | Enumerates all persisted automation workflows from the local file repository (`data/workflows/`). | Query parameters (optional limit/offset) | JSON array of workflow metadata / workflow objects | Returns empty list `[]` if storage empty; 500 on I/O error | Dispatch prompt, `PROJECT.md` §Interface Contracts |
| 4 | REST Workflows | `POST /api/workflows` | Validates and persists a workflow document. Enforces `KutomotoWorkflow` Pydantic schema and assigns UUID if missing. | `KutomotoWorkflow` JSON payload | 201 Created with persisted `KutomotoWorkflow` JSON | 422 Unprocessable Entity (RFC 7807) on schema invalidity | Dispatch prompt, `engine/schema.py` |
| 5 | REST Workflows | `GET /api/workflows/{id}` | Retrieves a single saved workflow document by unique ID. | Path parameter `id` (UUID string) | 200 OK with `KutomotoWorkflow` JSON | 404 Not Found (RFC 7807 Problem Details) if not found | Dispatch prompt, `PROJECT.md` |
| 6 | REST Workflows | `DELETE /api/workflows/{id}` | Permanently removes a saved workflow file by ID. | Path parameter `id` (UUID string) | 200 OK `{"success": true, "id": id, "message": "..."}` | 404 Not Found (RFC 7807 Problem Details) if not found | Dispatch prompt, `PROJECT.md` |
| 7 | REST Designer | `POST /api/designer/compile` | Compiles visual bounding box layout (`VisualFormLayout`) into canonical executable `KutomotoWorkflow` via 5-pass algorithm. | `VisualFormLayout` JSON | 200 OK with compiled `KutomotoWorkflow` JSON | 422 Unprocessable Entity / 400 Bad Request on geometry/syntax violation | Dispatch prompt, `designer/compiler.py`, `SPECIFICATION.md` §8 |
| 8 | REST Desktop | `GET /api/windows` | Enumerates active top-level Windows desktop windows using `kutomoto.automation.win32_window`. | Optional query params: `visible_only=true`, `non_empty_title=true`, `filter=str` | JSON array of `WindowInfo` objects (hwnd, title, class_name, pid, process_name, rect, client_rect) | Gracefully returns empty list `[]` if Win32 APIs unavailable | Dispatch prompt, `automation/win32_window.py` |
| 9 | REST Execution | `POST /api/execute/start` | Initiates asynchronous execution of a workflow (by ID or inline payload) via `WorkflowRunner`. | `{"workflow_id": "...", "workflow": {...}, "runtime_variables": {...}}` | 200 OK / 202 Accepted `{"status": "started", "execution_id": "...", "initial_state": "..."}` | 409 Conflict if already running/countdown; 404 if ID missing; 422 if vars missing | Dispatch prompt, `engine/runner.py`, `SPECIFICATION.md` §9 |
| 10 | REST Execution | `POST /api/execute/pause` | Suspends active execution loop, setting runner state to `PAUSED` and invoking `runner.pause()`. | None | 200 OK `{"status": "paused", "runner_state": "PAUSED"}` | 409 Conflict if runner not in `RUNNING` state | Dispatch prompt, `engine/runner.py` |
| 11 | REST Execution | `POST /api/execute/resume` | Resumes a paused execution loop, bringing target window to focus and invoking `runner.resume()`. | None | 200 OK `{"status": "resumed", "runner_state": "RUNNING"}` | 409 Conflict if runner not in `PAUSED` state | Dispatch prompt, `engine/runner.py` |
| 12 | REST Execution | `POST /api/execute/abort` | Emergency execution abort, immediately triggering `runner.abort()`, releasing modifiers and resetting state. | None | 200 OK `{"status": "aborted", "runner_state": "STOPPED"}` | Idempotent; succeeds even if already idle | Dispatch prompt, `engine/runner.py` |
| 13 | REST Execution | `GET /api/execute/status` | Returns current runner state, active step index, total steps, execution UUID, elapsed time, and last audit summary. | None | 200 OK JSON status object | 200 OK with `state: "IDLE"` when no execution active | Dispatch prompt, `engine/runner.py` |
| 14 | Telemetry WS | `WebSocket /ws/execution` | Bidirectional real-time WebSocket connection broadcasting FSM state transitions, countdown ticks, step start/finish, focus alerts, and receiving operator prompt responses. | WebSocket connection request | Real-time JSON telemetry stream (`connection_established`, `state_change`, `countdown_tick`, `step_started`, etc.) | Disconnect handled cleanly without task cancellation | Dispatch prompt, `SPECIFICATION.md` §1.3, §2, §9 |
| 15 | Static UI | Static File Mounting at `/` | Mounts `src/kutomoto/ui/` directory at root path `/` to serve HTML5 Single Page Application shell. | HTTP GET `/`, `/css/*`, `/js/*` | HTML, CSS, JavaScript static assets | Returns 404 for missing static assets; fallback if UI dir not yet created | Dispatch prompt, `PROJECT.md` §Code Layout |
| 16 | Driver Bridge | `Win32Driver` Adapter | Adapter class implementing `IWin32Driver` Protocol by delegating to `kutomoto.automation` functions for production execution. | Method calls from `WorkflowRunner` | Low-level Win32 hardware inputs, window geometry, focus | Catches ctypes errors and surfaces meaningful diagnostics | `engine/runner.py:33`, `automation/*` |
| 17 | Storage Repo | `WorkflowRepository` | Filesystem-based JSON persistence layer for saving, loading, listing, and deleting workflows with atomic write semantics. | Path to directory, workflow models | Filesystem JSON operations | Handles concurrent reads/writes and missing files gracefully | `SPECIFICATION.md` §1.3, §2 |
| 18 | Error Handling | RFC 7807 Problem Details | Global exception handlers converting HTTP errors, Pydantic `ValidationError`, and compilation errors into standard RFC 7807 JSON. | Unhandled exceptions, validation errors | JSON with `type`, `title`, `status`, `detail`, `instance` | Returns appropriate 4xx/5xx HTTP status codes | `SPECIFICATION.md` §2 (F16) |

---

## 2. Discovered Edge Cases

| # | Feature | Input / Condition | Observed / Required System Behavior | Architectural Defense Mechanism |
|---|---------|-------------------|--------------------------------------|----------------------------------|
| 1 | `POST /api/execute/start` | Rapid double-click / concurrent start requests (E06) | Second request arrives while first is in `COUNTDOWN` or `RUNNING`. Second request must be rejected without interfering with running flow. | Check `runner.fsm.is_active` atomically under an asyncio lock; return HTTP 409 Conflict with RFC 7807 Problem Details. |
| 2 | `WebSocket /ws/execution` | Client disconnects mid-execution (E12) | Browser window closes or network drops while runner is actively typing into a desktop application. | WebSocket connection manager catches `WebSocketDisconnect` cleanly, removes client from active subscriber list, and allows `WorkflowRunner` to continue unaffected. |
| 3 | `POST /api/workflows` | Corrupt or invalid JSON schema payload (E14) | Client posts malformed JSON or payload violating `KutomotoWorkflow` (e.g., negative delay, invalid action type). | Pydantic V2 validation catches errors; custom `RequestValidationError` handler returns HTTP 422 with RFC 7807 Problem Details listing invalid parameters. |
| 4 | `POST /api/designer/compile` | Negative box coordinates or out-of-bounds box (E11) | Visual box has `x < 0` or `x + width > canvas.width`. | Compiler / schema validator raises `GeometryError` or `ValueError`; converted to HTTP 422 Problem Details explaining exact edge violation. |
| 5 | `POST /api/execute/start` | Missing required runtime variable | Workflow requires `{{customer_ssn}}` marked `required=True`, but request omitted it. | `WorkflowRunner.execute` raises `ValueError`; caught by executor and transitioned to `ERROR` state; returns HTTP 422 or reports error over WebSocket. |
| 6 | `GET /api/windows` | Running on non-Windows host or headless test container | `ctypes.windll.user32` is unavailable (`None`). | `win32_window.py` detects `user32 is None` and returns `[]`. Endpoint returns empty list `[]` instead of raising 500 error. In test mode, optional mock window injector supported. |
| 7 | `GET /api/workflows/{id}` | Non-existent workflow ID requested | Operator requests `GET /api/workflows/00000000-0000-0000-0000-000000000000`. | Repository detects file absence and returns HTTP 404 Problem Details with title `"Workflow Not Found"`. |
| 8 | `POST /api/execute/pause` | Pause requested when runner is in `IDLE` or `COUNTDOWN` | Client issues pause command before runner enters `RUNNING`. | Endpoint checks `runner.state`; if not `RUNNING`, returns HTTP 409 Conflict explaining that pause is only valid when `RUNNING`. |
| 9 | `POST /api/execute/resume` | Resume requested when runner is not paused | Client issues resume command when runner is already `RUNNING` or `IDLE`. | Endpoint checks `runner.state`; if not `PAUSED`, returns HTTP 409 Conflict explaining that resume is only valid when `PAUSED`. |
| 10 | `POST /api/execute/abort` | Abort requested during 3-second countdown | Operator aborts during countdown ticks before any inputs are injected. | Runner sets `abort_requested = True`, breaks countdown loop, triggers `ABORT_TRIGGERED`, releases modifiers, transitions to `STOPPED`, and returns HTTP 200. |
| 11 | Static files | Static UI directory `src/kutomoto/ui/` does not exist yet | Server started prior to frontend assets creation. | Server checks `ui_dir.exists()`; if missing, creates directory with fallback `index.html` or mounts only when directory exists, preventing startup crashes. |
| 12 | Lifespan shutdown | Server termination (Ctrl+C / SIGINT) while runner is typing | Uvicorn shutdown initiated while keys or mouse buttons might be held down. | Lifespan handler calls `await runner.abort()` and `driver.release_all_modifiers()`, guaranteeing OS input state is clean upon exit. |

---

## 3. Concrete Architecture Design for `src/kutomoto/server/app.py`

### 3.1 Architectural Overview

```
+-------------------------------------------------------------------------------------------------+
|                                     src/kutomoto/server/app.py                                  |
+-------------------------------------------------------------------------------------------------+
|  FastAPI Application (`app`)                                                                    |
|  - CORS Middleware (Allow all origins for local Edge App / browser access)                     |
|  - Lifespan Context Manager (Startup DPI awareness, shutdown cleanup)                          |
|  - RFC 7807 Problem Details Exception Handlers                                                  |
+-------------------------------------------------------------------------------------------------+
|  Subsystems & Components:                                                                       |
|                                                                                                 |
|  1. WorkflowRepository                                                                          |
|     - Persistent JSON storage under `data/workflows/` (or configurable path)                     |
|     - Methods: list(), get(id), save(workflow), delete(id)                                      |
|                                                                                                 |
|  2. WebSocketHub (ConnectionManager)                                                            |
|     - Manages active client WebSockets                                                          |
|     - broadcast(event_name, payload): async fan-out to all connected clients                    |
|     - Handles disconnects silently without leaking exceptions                                  |
|                                                                                                 |
|  3. ServerExecutionManager                                                                      |
|     - Holds current `WorkflowRunner` instance and active `asyncio.Task`                          |
|     - Enforces state concurrency (blocks concurrent runs with 409 Conflict)                     |
|     - Bridges runner telemetry and FSM transitions to WebSocketHub                              |
|     - Provides pause(), resume(), abort(), get_status()                                         |
|                                                                                                 |
|  4. Win32Driver (Production Driver Adapter)                                                     |
|     - Implements `IWin32Driver` Protocol delegating to `kutomoto.automation`                    |
|     - Fallback / Mock driver support for CI/CD test suites                                      |
+-------------------------------------------------------------------------------------------------+
|  REST Routes:                                                                                   |
|  - `GET  /api/health`              -> System status & "Copyrights reserved to 90Studio"         |
|  - `GET  /api/workflows`           -> List saved workflows                                      |
|  - `POST /api/workflows`           -> Create/save workflow (KutomotoWorkflow validated)         |
|  - `GET  /api/workflows/{id}`      -> Retrieve workflow                                         |
|  - `DELETE /api/workflows/{id}`   -> Delete workflow                                           |
|  - `POST /api/designer/compile`    -> Compile VisualFormLayout into KutomotoWorkflow            |
|  - `GET  /api/windows`             -> Enumerate active desktop windows                          |
|  - `POST /api/execute/start`       -> Asynchronously launch workflow execution                  |
|  - `POST /api/execute/pause`       -> Pause running workflow                                    |
|  - `POST /api/execute/resume`      -> Resume paused workflow                                    |
|  - `POST /api/execute/abort`       -> Emergency abort                                           |
|  - `GET  /api/execute/status`      -> Execution telemetry status                                |
+-------------------------------------------------------------------------------------------------+
|  WebSocket Route:                                                                               |
|  - `WebSocket /ws/execution`       -> Real-time bidirectional telemetry & prompt channel        |
+-------------------------------------------------------------------------------------------------+
|  Static Asset Mount:                                                                            |
|  - `app.mount("/", StaticFiles(directory=..., html=True), name="ui")` (Registered last!)        |
+-------------------------------------------------------------------------------------------------+
```

### 3.2 Concrete Component Specifications

#### Component 1: `WorkflowRepository`
- **Location**: `src/kutomoto/server/app.py`
- **Responsibilities**:
  - Initializes storage folder (`data/workflows` or user profile `~/.kutomoto/workflows`).
  - Reads and writes `KutomotoWorkflow` models as formatted JSON (`indent=2`).
  - Atomically writes files using temporary file rename to prevent partial writes during unexpected termination.
  - Lists workflows returning metadata objects: `id`, `name`, `description`, `step_count`, `source_mode`, `target_title`, `created_at`, `updated_at`, `copyright`.

#### Component 2: `WebSocketHub`
- **Location**: `src/kutomoto/server/app.py`
- **Responsibilities**:
  - Thread-safe / asyncio-safe collection of active `WebSocket` connections (`Set[WebSocket]`).
  - `async connect(websocket: WebSocket)`: Accepts socket, adds to set, sends `connection_established` message.
  - `disconnect(websocket: WebSocket)`: Removes socket from set.
  - `async broadcast(event_type: str, data: Dict[str, Any])`: Iterates through connections, converts message to JSON string with mandatory copyright footer, dispatches via `send_text()`. Automatically removes closed/broken sockets.

#### Component 3: `Win32DriverAdapter`
- **Location**: `src/kutomoto/server/app.py` (or `kutomoto.automation.win32_driver`)
- **Responsibilities**:
  - Conforms strictly to `kutomoto.engine.runner.IWin32Driver` Protocol.
  - Implements:
    - `set_dpi_awareness()` -> calls `win32_core.set_process_dpi_awareness()`
    - `get_screen_dimensions()` -> calls `user32.GetSystemMetrics(0)`, `user32.GetSystemMetrics(1)`
    - `get_cursor_pos()` -> calls `user32.GetCursorPos`
    - `set_cursor_pos(x, y)` -> calls `win32_input.send_mouse_move(x, y)`
    - `get_foreground_window()` -> calls `win32_window.get_foreground_window()`
    - `find_window(pattern, mode, proc)` -> calls `win32_window.find_window(title_pattern=pattern, match_mode=mode, exe_name=proc)`
    - `focus_window(hwnd, timeout_ms)` -> calls `win32_window.activate_target_window(hwnd, timeout_ms)`
    - `get_window_bounds(hwnd)` -> calls `win32_window.get_window_bounds(hwnd)`
    - `get_client_rect(hwnd)` -> calls `win32_window.get_client_rect(hwnd)`
    - `client_to_screen(hwnd, cx, cy)` -> calls `win32_window.client_to_screen_coords(hwnd, cx, cy)`
    - `send_click(x, y, btn, count)` -> calls `win32_input.send_click(x, y, button=btn, click_count=count)`
    - `send_mouse_move(x, y)` -> calls `win32_input.send_mouse_move(x, y)`
    - `send_text(text, delay, thresh)` -> calls `win32_input.send_text(text, delay_between_keys_ms=delay, use_clipboard_threshold=thresh)`
    - `send_key_press(key, count)` -> calls `win32_input.send_key_press(key, repeat_count=count)`
    - `send_hotkey(mods, key)` -> calls `win32_input.send_hotkey(mods, key)`
    - `clear_field(strategy)` -> calls `win32_input.clear_field(strategy=strategy)`
    - `send_scroll(dx, dy)` -> calls `win32_input.send_mouse_wheel(delta=dy)`
    - `release_all_modifiers()` -> calls `win32_input.release_all_modifiers()`
    - `is_key_pressed(vk)` -> calls `user32.GetAsyncKeyState(vk) & 0x8000 != 0`

#### Component 4: `ServerExecutionManager`
- **Location**: `src/kutomoto/server/app.py`
- **Responsibilities**:
  - Manages single-flight execution lifecycle.
  - Maintains `_active_task: Optional[asyncio.Task]`, `_current_runner: Optional[WorkflowRunner]`, `_active_execution_id: Optional[str]`.
  - When `start(workflow, runtime_variables)` is called:
    - Verifies no active task is running (`_current_runner.fsm.is_active`). If active, raises 409 Conflict.
    - Instantiates fresh `WorkflowRunner(driver=self.driver, telemetry_callback=self._on_telemetry)`.
    - Attaches FSM state change listener: `runner.fsm.add_listener(self._on_fsm_transition)`.
    - Launches `_active_task = asyncio.create_task(self._run_wrapper(workflow, runtime_variables))`.
    - Returns execution ID and initial state.
  - In `_run_wrapper`:
    - Executes `runner.execute(workflow, runtime_variables)`.
    - Captures resulting `KutomotoAuditLog`.
    - Broadcasts `execution_completed` over WebSocket.
    - Cleans up reference when done.

#### Component 5: RFC 7807 Problem Details Handler
- **Format**:
  ```json
  {
    "type": "https://90studio.com/errors/validation-error",
    "title": "Validation Error",
    "status": 422,
    "detail": "Field 'name' is required and must not be empty.",
    "instance": "/api/workflows",
    "invalid_params": [
      { "name": "name", "reason": "Field required" }
    ]
  }
  ```
- **Registered Handlers**:
  - `HTTPException` -> Extracts `status_code` and `detail`.
  - `RequestValidationError` -> Maps Pydantic errors to `invalid_params`.
  - `CompilationError` / `GeometryError` -> Status 422, detailed geometric explanation.
  - `InvalidTransitionError` -> Status 409 Conflict.
  - Generic `Exception` -> Status 500 Internal Server Error.

---

## 4. REST Endpoint Contracts and Schemas

### 1. `GET /api/health`
- **Status**: 200 OK
- **Response**:
  ```json
  {
    "status": "healthy",
    "system": "kutomoto",
    "version": "1.0.0",
    "copyright": "Copyrights reserved to 90Studio",
    "timestamp_utc": "2026-11-05T03:55:00Z",
    "runner_state": "IDLE",
    "platform": {
      "system": "Windows",
      "release": "11",
      "dpi_aware": true
    }
  }
  ```

### 2. `GET /api/workflows`
- **Status**: 200 OK
- **Response**:
  ```json
  [
    {
      "id": "c1f72a9e-8c3b-4c5e-8840-79db8b123456",
      "name": "Banking KYC Customer Onboarding",
      "description": "Commercial banking customer KYC intake",
      "copyright": "Copyrights reserved to 90Studio",
      "step_count": 6,
      "source_mode": "visual_designer_generated",
      "target_application": {
        "target_type": "window_title",
        "window_title_pattern": "Banking KYC.*",
        "match_mode": "regex",
        "process_name": "msedge.exe"
      },
      "created_at": "2026-11-05T01:00:00Z",
      "updated_at": "2026-11-05T01:00:00Z"
    }
  ]
  ```

### 3. `POST /api/workflows`
- **Input**: Valid `KutomotoWorkflow` JSON payload.
- **Status**: 201 Created (or 200 OK)
- **Response**: Stored `KutomotoWorkflow` object with guaranteed `id` and `copyright`.
- **Error (422)**: RFC 7807 Problem Details if schema validation fails.

### 4. `GET /api/workflows/{id}`
- **Input**: `id` path parameter (string UUID).
- **Status**: 200 OK
- **Response**: Full `KutomotoWorkflow` JSON object.
- **Error (404)**: RFC 7807 Problem Details with title `"Workflow Not Found"`.

### 5. `DELETE /api/workflows/{id}`
- **Input**: `id` path parameter (string UUID).
- **Status**: 200 OK
- **Response**: `{"success": true, "id": "...", "message": "Workflow deleted successfully"}`
- **Error (404)**: RFC 7807 Problem Details if file not found.

### 6. `POST /api/designer/compile`
- **Input**: `VisualFormLayout` JSON payload.
- **Status**: 200 OK
- **Response**: Compiled `KutomotoWorkflow` JSON.
- **Error (422)**: RFC 7807 Problem Details if layout contains duplicate box IDs, negative geometry, or bounds violation.

### 7. `GET /api/windows`
- **Query Params**: `visible_only: bool = True`, `non_empty_title: bool = True`, `filter: Optional[str] = None`
- **Status**: 200 OK
- **Response**:
  ```json
  [
    {
      "hwnd": 131248,
      "title": "Banking KYC Customer Onboarding - Work - Microsoft Edge",
      "class_name": "Chrome_WidgetWin_1",
      "pid": 14208,
      "executable_name": "msedge.exe",
      "executable_path": "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
      "is_visible": true,
      "is_iconic": false,
      "rect": [100, 100, 1380, 900],
      "client_rect": [108, 131, 1264, 761],
      "width": 1280,
      "height": 800,
      "client_width": 1264,
      "client_height": 761
    }
  ]
  ```

### 8. `POST /api/execute/start`
- **Input**:
  ```json
  {
    "workflow_id": "c1f72a9e-8c3b-4c5e-8840-79db8b123456",
    "runtime_variables": {
      "customer_name": "Alice Smith",
      "id_number": "KYC-998822"
    }
  }
  ```
  *(Alternatively accepts `"workflow": { ... full KutomotoWorkflow ... }`)*
- **Status**: 200 OK or 202 Accepted
- **Response**:
  ```json
  {
    "status": "started",
    "execution_id": "e4a29c12-3b44-4e2a-b788-012938475610",
    "workflow_id": "c1f72a9e-8c3b-4c5e-8840-79db8b123456",
    "workflow_name": "Banking KYC Customer Onboarding",
    "initial_state": "COUNTDOWN",
    "message": "Workflow execution started"
  }
  ```
- **Error (409)**: If execution is already active.

### 9. `POST /api/execute/pause`
- **Status**: 200 OK
- **Response**: `{"status": "paused", "runner_state": "PAUSED"}`
- **Error (409)**: If runner is not in `RUNNING` state.

### 10. `POST /api/execute/resume`
- **Status**: 200 OK
- **Response**: `{"status": "resumed", "runner_state": "RUNNING"}`
- **Error (409)**: If runner is not in `PAUSED` state.

### 11. `POST /api/execute/abort`
- **Status**: 200 OK
- **Response**: `{"status": "aborted", "runner_state": "STOPPED"}`

### 12. `GET /api/execute/status`
- **Status**: 200 OK
- **Response**:
  ```json
  {
    "state": "RUNNING",
    "execution_id": "e4a29c12-3b44-4e2a-b788-012938475610",
    "workflow_id": "c1f72a9e-8c3b-4c5e-8840-79db8b123456",
    "workflow_name": "Banking KYC Customer Onboarding",
    "current_step_index": 3,
    "total_steps": 6,
    "is_paused": false,
    "elapsed_seconds": 4.12,
    "last_audit_summary": null
  }
  ```

---

## 5. WebSocket Telemetry Protocol (`/ws/execution`)

### 5.1 Outbound Broadcast Frames (Server -> UI)

1. **`connection_established`**:
   ```json
   {
     "event": "connection_established",
     "system": "kutomoto",
     "copyright": "Copyrights reserved to 90Studio",
     "current_state": "IDLE",
     "active_execution_id": null
   }
   ```
2. **`state_change`**:
   ```json
   {
     "event": "state_change",
     "execution_id": "e4a29c12-...",
     "old_state": "COUNTDOWN",
     "new_state": "RUNNING",
     "fsm_event": "COUNTDOWN_DONE",
     "timestamp": "2026-11-05T03:55:04.120Z"
   }
   ```
3. **`countdown_tick`**:
   ```json
   {
     "event": "countdown_tick",
     "execution_id": "e4a29c12-...",
     "remaining": 2,
     "timestamp": "2026-11-05T03:55:02.000Z"
   }
   ```
4. **`step_started`**:
   ```json
   {
     "event": "step_started",
     "execution_id": "e4a29c12-...",
     "step_index": 2,
     "total_steps": 6,
     "action_type": "type_text",
     "label": "Enter Customer First Name",
     "timestamp": "2026-11-05T03:55:05.100Z"
   }
   ```
5. **`step_completed`**:
   ```json
   {
     "event": "step_completed",
     "execution_id": "e4a29c12-...",
     "step_index": 2,
     "latency_ms": 14.8,
     "timestamp": "2026-11-05T03:55:05.115Z"
   }
   ```
6. **`focus_lost_warning`**:
   ```json
   {
     "event": "focus_lost_warning",
     "execution_id": "e4a29c12-...",
     "expected_hwnd": 131248,
     "actual_hwnd": 65540,
     "message": "Target application lost active focus. Execution automatically paused.",
     "timestamp": "2026-11-05T03:55:07.000Z"
   }
   ```
7. **`user_prompt_requested`**:
   ```json
   {
     "event": "user_prompt_requested",
     "execution_id": "e4a29c12-...",
     "variable_name": "otp_code",
     "prompt_message": "Enter One-Time Password:",
     "step_index": 4,
     "is_secret": true
   }
   ```
8. **`execution_completed`**:
   ```json
   {
     "event": "execution_completed",
     "execution_id": "e4a29c12-...",
     "workflow_id": "c1f72a9e-...",
     "final_status": "SUCCESS",
     "duration_seconds": 5.43,
     "audit_log": { ... },
     "copyright": "Copyrights reserved to 90Studio"
   }
   ```

### 5.2 Inbound Control Frames (UI -> Server)

1. **`ping`** -> Server responds with `{"event": "pong"}`
2. **`{"action": "pause"}`** -> Triggers `pause()`
3. **`{"action": "resume"}`** -> Triggers `resume()`
4. **`{"action": "abort"}`** -> Triggers `abort()`
5. **`{"action": "prompt_response", "variable_name": "...", "value": "..."}`** -> Resolves awaiting prompt variable

---

## 6. Handoff Report

### 1. Observation
- `src/kutomoto/__main__.py:26-29`: CLI entry point is already wired to invoke `from kutomoto.server.app import run_server; run_server(port=args.port)`.
- `src/kutomoto/engine/runner.py:33`: `IWin32Driver` Protocol defines 17 required methods. `MockWin32Driver` exists in `engine/safety.py:269`, but there is currently no concrete `Win32Driver` class adapter wrapping the module-level functions in `kutomoto.automation`.
- `src/kutomoto/engine/runner.py:72`: `WorkflowRunner` is non-blocking and fully asynchronous, taking `driver`, `audit_logger`, `telemetry_callback`, `safety_guard`, and `prompt_resolver`.
- `src/kutomoto/engine/fsm.py:85-110`: `ExecutionFSM` supports async/sync listeners via `add_listener()`, firing on all state transitions `(old_state, new_state, event)`.
- `src/kutomoto/designer/compiler.py:8`: Exports both `compile_visual_layout_to_workflow` and `compile_visual_boxes_to_workflow`.
- `src/kutomoto/automation/win32_window.py:151`: `enumerate_windows(visible_only=True, non_empty_title_only=True)` returns `List[WindowInfo]` with handles, titles, processes, and bounding rectangles.
- Package dependencies confirmed in Python 3.14.0: `fastapi==0.128.0`, `uvicorn==0.40.0`, `websockets==15.0.1`, `starlette==0.50.0`, `pydantic==2.12.5`, `httpx==0.28.1`.

### 2. Logic Chain
1. `src/kutomoto/__main__.py` expects `kutomoto.server.app.run_server(port=...)` and `app` as an ASGI application.
2. In order to support automated form filling without blocking the HTTP event loop, `WorkflowRunner.execute()` must run inside an `asyncio.Task` managed by a dedicated execution controller (`ServerExecutionManager`).
3. Single-flight execution guarantee is required: if an execution is already active (`COUNTDOWN`, `RUNNING`, `PAUSED`), any subsequent `POST /api/execute/start` must return HTTP 409 Conflict.
4. Telemetry events from `WorkflowRunner._emit_telemetry` and FSM state transitions from `ExecutionFSM.add_listener` must be broadcast through a centralized `WebSocketHub` to all connected clients on `/ws/execution`.
5. Error responses must strictly conform to RFC 7807 Problem Details per specification requirement F16.
6. The `ui` directory at `src/kutomoto/ui/` must be mounted at `/` as static files, but registered strictly AFTER `/api/` and `/ws/` routes so API routing takes precedence.

### 3. Caveats
- `src/kutomoto/ui/` static assets (HTML/CSS/JS) are part of Milestone 4 parallel work (`m4_coder_2`). `app.py` must handle the initial absence of `ui/` gracefully by checking `os.path.exists()` or creating a minimal fallback index.
- On non-Windows development/testing hosts (e.g. CI environments), `ctypes.windll.user32` is unavailable; the server must detect this and fall back to `MockWin32Driver` automatically unless an explicit driver is passed to `create_app()`.

### 4. Conclusion
The architecture for `src/kutomoto/server/app.py` is fully specified and ready for implementation. It requires:
1. `create_app()` factory with dependency injection (storage directory, driver instance) for testability.
2. `WorkflowRepository` for JSON persistence in `data/workflows/`.
3. `WebSocketHub` for multi-client event streaming.
4. `Win32DriverAdapter` bridging `kutomoto.automation` to `IWin32Driver`.
5. `ServerExecutionManager` coordinating async task execution, pause, resume, abort, and status.
6. 11 REST endpoints + 1 WebSocket endpoint + static files mount.
7. RFC 7807 Problem Details exception handlers.
8. `run_server()` function invoked by `__main__.py`.

### 5. Verification Method
- Independent verification command:
  `py -3.14 -m pytest tests/test_api.py -v`
- Inspectable files:
  - `src/kutomoto/server/app.py`
  - `tests/test_api.py`
- Invalidation conditions:
  - Any REST endpoint returning non-Problem-Details JSON on 4xx/5xx errors.
  - Concurrent executions permitted simultaneously without 409 Conflict.
  - WebSocket disconnect crashing or interrupting the background execution task.
  - Failure to include `"Copyrights reserved to 90Studio"` in `/api/health` or audit streams.
