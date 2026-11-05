"""
kutomoto.server.app
FastAPI backend service and WebSocket telemetry hub for kutomoto.
Copyrights reserved to 90Studio
"""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import platform
import re
import tempfile
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from kutomoto import __copyright__, __version__
from kutomoto.designer.compiler import compile_visual_layout_to_workflow
from kutomoto.designer.exceptions import DuplicateBoxIdError, EmptyLayoutError, GeometryError
from kutomoto.engine.audit import AuditLogger
from kutomoto.engine.fsm import ExecutionState, FSMEvent
from kutomoto.engine.runner import WorkflowRunner
from kutomoto.engine.safety import MockWin32Driver

logger = logging.getLogger("kutomoto.server")

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_DATA_DIR = BASE_DIR / "data" / "workflows"
UI_DIR = Path(__file__).resolve().parent.parent / "ui"


# ==============================================================================
# 1. WIN32 DRIVER ADAPTER
# ==============================================================================

class Win32DriverAdapter:
    """
    Production driver adapter implementing the IWin32Driver Protocol
    by delegating to kutomoto.automation native ctypes implementations.
    """

    def __init__(self) -> None:
        from kutomoto.automation import win32_core, win32_input, win32_window
        self._core = win32_core
        self._input = win32_input
        self._window = win32_window
        self._last_cursor_pos: Tuple[int, int] = (500, 500)

    def set_dpi_awareness(self) -> bool:
        return self._core.set_process_dpi_awareness()

    def get_screen_dimensions(self) -> Tuple[int, int]:
        if self._core.user32:
            w = int(self._core.user32.GetSystemMetrics(0))
            h = int(self._core.user32.GetSystemMetrics(1))
            if w > 0 and h > 0:
                return (w, h)
        return (1920, 1080)

    def get_cursor_pos(self) -> Tuple[int, int]:
        if self._core.user32:
            pt = self._core.POINT()
            if self._core.user32.GetCursorPos(self._core.byref(pt)):
                self._last_cursor_pos = (int(pt.x), int(pt.y))
                return self._last_cursor_pos
        return self._last_cursor_pos

    def set_cursor_pos(self, x: int, y: int) -> None:
        self._last_cursor_pos = (int(x), int(y))
        self._input.send_mouse_move(x, y)

    def get_foreground_window(self) -> int:
        return self._window.get_foreground_window()

    def find_window(
        self,
        title_pattern: str,
        match_mode: str = "contains",
        process_name: Optional[str] = None,
    ) -> Optional[int]:
        res = self._window.find_window(
            title_pattern=title_pattern,
            match_mode=match_mode,
            exe_name=process_name,
        )
        if res is None:
            return None
        return res.hwnd if hasattr(res, "hwnd") else int(res)

    def focus_window(self, hwnd: int, timeout_ms: int = 1500) -> bool:
        return self._window.activate_target_window(hwnd, timeout_ms=timeout_ms)

    def get_window_bounds(self, hwnd: int) -> Tuple[int, int, int, int]:
        return self._window.get_window_bounds(hwnd)

    def get_client_rect(self, hwnd: int) -> Tuple[int, int, int, int]:
        return self._window.get_client_rect(hwnd)

    def client_to_screen(self, hwnd: int, client_x: int, client_y: int) -> Tuple[int, int]:
        return self._window.client_to_screen_coords(hwnd, client_x, client_y)

    def send_click(
        self,
        x: int,
        y: int,
        button: str = "left",
        click_count: int = 1,
    ) -> None:
        self._last_cursor_pos = (int(x), int(y))
        self._input.send_click(x, y, button=button, click_count=click_count)

    def send_mouse_move(self, x: int, y: int) -> None:
        self._last_cursor_pos = (int(x), int(y))
        self._input.send_mouse_move(x, y)

    def send_text(
        self,
        text: str,
        delay_between_keys_ms: int = 20,
        use_clipboard_threshold: int = 40,
    ) -> None:
        self._input.send_text(
            text,
            delay_between_keys_ms=delay_between_keys_ms,
            use_clipboard_threshold=use_clipboard_threshold,
        )

    def send_key_press(self, key_name: str, repeat_count: int = 1) -> None:
        self._input.send_key_press(key_name, repeat_count=repeat_count)

    def send_key_up(self, key_or_vk: Any) -> None:
        self._input.send_key_up(key_or_vk)

    def send_hotkey(self, modifiers: List[str], key: str) -> None:
        self._input.send_hotkey(modifiers, key)

    def clear_field(self, strategy: str = "select_all_backspace") -> None:
        self._input.clear_field(strategy=strategy)

    def send_scroll(self, delta_x: int, delta_y: int) -> None:
        self._input.send_mouse_wheel(delta=delta_y)

    def release_all_modifiers(self) -> None:
        self._input.release_all_modifiers()

    def is_key_pressed(self, key: Any) -> bool:
        if not self._core.user32:
            return False
        try:
            vk = self._core.resolve_virtual_key(key)
            state = self._core.user32.GetAsyncKeyState(int(vk))
            return bool(state & 0x8000)
        except Exception:
            return False


# ==============================================================================
# 2. WORKFLOW REPOSITORY (JSON PERSISTENCE)
# ==============================================================================

class WorkflowRepository:
    """Filesystem repository for saving, loading, and listing KutomotoWorkflow documents."""

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self.storage_dir = Path(storage_dir or DEFAULT_DATA_DIR)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, workflow_id: str) -> Path:
        safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", workflow_id)
        return self.storage_dir / f"{safe_id}.json"

    def list_all(self) -> List[Dict[str, Any]]:
        workflows: List[Dict[str, Any]] = []
        for file_path in sorted(self.storage_dir.glob("*.json")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    workflows.append(data)
            except Exception as ex:
                logger.warning("Failed to load workflow file %s: %s", file_path, ex)
        return workflows

    def get(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        file_path = self._get_path(workflow_id)
        if not file_path.is_file():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as ex:
            logger.error("Failed to read workflow %s: %s", workflow_id, ex)
            return None

    def save(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        workflow_id = workflow_data.get("id") or str(uuid.uuid4())
        workflow_data["id"] = workflow_id
        workflow_data["copyright"] = __copyright__
        now_iso = datetime.now(timezone.utc).isoformat()
        workflow_data.setdefault("created_at", now_iso)
        workflow_data["updated_at"] = now_iso

        file_path = self._get_path(workflow_id)
        # Atomic file write using temporary file
        temp_fd, temp_path = tempfile.mkstemp(dir=str(self.storage_dir), prefix="wf_", suffix=".tmp")
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(workflow_data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, str(file_path))
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

        return workflow_data

    def delete(self, workflow_id: str) -> bool:
        file_path = self._get_path(workflow_id)
        if file_path.is_file():
            try:
                file_path.unlink()
                return True
            except Exception as ex:
                logger.error("Failed to delete workflow %s: %s", workflow_id, ex)
                return False
        return False


# ==============================================================================
# 3. WEBSOCKET TELEMETRY HUB
# ==============================================================================

class WebSocketHub:
    """Manages active WebSocket connections and broadcasts real-time telemetry."""

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.debug("WebSocket client connected. Active connections: %d", len(self._connections))
        try:
            await websocket.send_json({
                "event": "connection_established",
                "type": "connection_established",
                "system": "kutomoto",
                "version": __version__,
                "copyright": __copyright__,
                "state": "IDLE",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            pass

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)
        logger.debug("WebSocket client disconnected. Active connections: %d", len(self._connections))

    async def broadcast(self, event_name: str, data: Dict[str, Any]) -> None:
        message = {
            "event": event_name,
            "type": event_name,
            "payload": data,
            "data": data,
            **data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "copyright": __copyright__,
        }
        async with self._lock:
            subscribers = list(self._connections)

        dead_connections: List[WebSocket] = []
        for ws in subscribers:
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.append(ws)

        if dead_connections:
            async with self._lock:
                for ws in dead_connections:
                    self._connections.discard(ws)


# ==============================================================================
# 4. SERVER EXECUTION CONTROLLER
# ==============================================================================

class ServerExecutionManager:
    """Coordinates asynchronous single-flight workflow execution, FSM, and telemetry."""

    def __init__(self, hub: WebSocketHub) -> None:
        self.hub = hub
        self._runner: Optional[WorkflowRunner] = None
        self._active_task: Optional[asyncio.Task] = None
        self._execution_id: Optional[str] = None
        self._workflow_id: Optional[str] = None
        self._workflow_name: Optional[str] = None
        self._current_step_index: int = 0
        self._total_steps: int = 0
        self._start_time: float = 0.0
        self._last_audit_summary: Optional[Dict[str, Any]] = None
        self._audit_summaries: Dict[str, Dict[str, Any]] = {}
        self._audit_logs: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    def is_active(self) -> bool:
        if self._active_task is not None and self._active_task.done():
            return False
        if self._runner is not None and self._runner.fsm.is_active:
            return True
        if self._active_task is not None and not self._active_task.done():
            return True
        return False

    def get_state(self) -> str:
        if self._runner is not None:
            return self._runner.state.value
        return "IDLE"

    async def start(
        self,
        workflow: Any,
        variables: Optional[Dict[str, Any]],
        driver: Any,
    ) -> Dict[str, Any]:
        async with self._lock:
            if self.is_active():
                raise HTTPException(
                    status_code=409,
                    detail="A workflow execution is already active. Concurrency not permitted.",
                )

            self._execution_id = str(uuid.uuid4())
            self._workflow_id = getattr(workflow, "id", None) or str(uuid.uuid4())
            self._workflow_name = getattr(workflow, "name", "Workflow")
            self._current_step_index = 0
            self._total_steps = len(getattr(workflow, "steps", []))
            self._start_time = time.perf_counter()

            audit_logger = AuditLogger(execution_id=self._execution_id, workflow=workflow)
            runner = WorkflowRunner(
                driver=driver,
                audit_logger=audit_logger,
                telemetry_callback=self._on_runner_telemetry,
            )
            runner.fsm.add_listener(self._on_fsm_transition)
            self._runner = runner

            # Launch runner loop in background
            self._active_task = asyncio.create_task(
                self._run_wrapper(runner, workflow, variables)
            )

            return {
                "status": "started",
                "execution_id": self._execution_id,
                "workflow_id": self._workflow_id,
                "workflow_name": self._workflow_name,
                "initial_state": "COUNTDOWN",
                "message": "Workflow execution started successfully",
            }

    async def _run_wrapper(
        self,
        runner: WorkflowRunner,
        workflow: Any,
        variables: Optional[Dict[str, Any]],
    ) -> None:
        try:
            audit = await runner.execute(workflow, runtime_variables=variables)
            status = "SUCCESS"
            if audit and hasattr(audit, "execution_summary"):
                status = audit.execution_summary.final_status
            elif audit and hasattr(audit, "final_status"):
                status = getattr(audit, "final_status")

            summary = {
                "workflow_id": self._workflow_id,
                "execution_id": self._execution_id,
                "workflow_name": self._workflow_name,
                "status": status,
                "duration_seconds": round(time.perf_counter() - self._start_time, 2),
                "total_steps": self._total_steps,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "copyright": __copyright__,
            }
            if audit and hasattr(audit, "execution_summary"):
                summary["successful_steps"] = audit.execution_summary.successful_steps
                summary["failed_steps"] = audit.execution_summary.failed_steps
                summary["retried_steps"] = audit.execution_summary.retried_steps
            if audit and hasattr(audit, "step_events"):
                summary["events_count"] = len(audit.step_events)

            self._last_audit_summary = summary
            if self._workflow_id:
                self._audit_summaries[self._workflow_id] = summary
            if self._execution_id:
                self._audit_summaries[self._execution_id] = summary
            if audit:
                if self._workflow_id:
                    self._audit_logs[self._workflow_id] = audit
                if self._execution_id:
                    self._audit_logs[self._execution_id] = audit

            await self.hub.broadcast("audit_log", summary)
            await self.hub.broadcast("execution_completed", summary)
        except Exception as ex:
            logger.error("Workflow execution error: %s", ex, exc_info=True)
            err_data = {
                "execution_id": self._execution_id,
                "workflow_id": self._workflow_id,
                "workflow_name": self._workflow_name,
                "error": str(ex),
                "status": "ERROR",
                "duration_seconds": round(time.perf_counter() - self._start_time, 2),
                "total_steps": self._total_steps,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "copyright": __copyright__,
            }
            self._last_audit_summary = err_data
            if self._workflow_id:
                self._audit_summaries[self._workflow_id] = err_data
            if self._execution_id:
                self._audit_summaries[self._execution_id] = err_data
            await self.hub.broadcast("step_failed", err_data)
            await self.hub.broadcast("execution_error", err_data)
            # Ensure runner is never trapped in PAUSED or non-terminal active state
            if runner and not runner.fsm.is_terminal:
                try:
                    if runner.fsm.can_trigger(FSMEvent.ABORT_TRIGGERED):
                        await runner.fsm.trigger(FSMEvent.ABORT_TRIGGERED)
                    elif runner.fsm.can_trigger(FSMEvent.POLICY_ABORT):
                        await runner.fsm.trigger(FSMEvent.POLICY_ABORT)
                    if runner.fsm.can_trigger(FSMEvent.CLEANUP_DONE):
                        await runner.fsm.trigger(FSMEvent.CLEANUP_DONE)
                except Exception as abort_err:
                    logger.warning("FSM terminal transition failed during error handler: %s", abort_err)
                if not runner.fsm.is_terminal:
                    runner.fsm._state = ExecutionState.ERROR

    async def _on_runner_telemetry(self, event_name: str, payload: Dict[str, Any]) -> None:
        if event_name == "step_started":
            self._current_step_index = payload.get("step_index", self._current_step_index)
        payload["execution_id"] = self._execution_id
        await self.hub.broadcast(event_name, payload)

    async def _on_fsm_transition(
        self,
        old_state: ExecutionState,
        new_state: ExecutionState,
        event: FSMEvent,
    ) -> None:
        logger.debug("FSM transition: %s -> %s via %s", old_state.value, new_state.value, event.value)
        await self.hub.broadcast("state_change", {
            "execution_id": self._execution_id,
            "old_state": old_state.value,
            "new_state": new_state.value,
            "fsm_event": event.value,
        })

    async def pause(self) -> Dict[str, Any]:
        if not self._runner or not self.is_active():
            raise HTTPException(status_code=409, detail="No active execution to pause.")

        # If currently in COUNTDOWN or VALIDATING, allow a short wait for RUNNING
        for _ in range(30):
            if self._runner.state == ExecutionState.RUNNING:
                break
            if not self.is_active():
                break
            await asyncio.sleep(0.05)

        if self._runner.state != ExecutionState.RUNNING:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot pause runner in state '{self._runner.state.value}'. Only RUNNING may be paused.",
            )

        await self._runner.pause()
        return {"status": "paused", "runner_state": "PAUSED"}

    async def resume(self) -> Dict[str, Any]:
        if not self._runner or self._runner.state != ExecutionState.PAUSED:
            current = self._runner.state.value if self._runner else "IDLE"
            raise HTTPException(
                status_code=409,
                detail=f"Cannot resume runner in state '{current}'. Only PAUSED may be resumed.",
            )
        # Verify the background execution task is alive and active before transitioning state
        if self._active_task is None or self._active_task.done():
            if not self._runner.fsm.is_terminal:
                if self._runner.fsm.can_trigger(FSMEvent.ABORT_TRIGGERED):
                    await self._runner.fsm.trigger(FSMEvent.ABORT_TRIGGERED)
                else:
                    self._runner.fsm._state = ExecutionState.ERROR
            raise HTTPException(
                status_code=409,
                detail="Cannot resume workflow: background execution task is no longer active.",
            )
        await self._runner.resume()
        return {"status": "resumed", "runner_state": "RUNNING"}

    async def abort(self) -> Dict[str, Any]:
        if self._runner:
            await self._runner.abort()
        if self._active_task and not self._active_task.done():
            self._active_task.cancel()
            try:
                await self._active_task
            except (asyncio.CancelledError, Exception):
                pass
        aborted_summary = {
            "workflow_id": self._workflow_id,
            "execution_id": self._execution_id,
            "workflow_name": self._workflow_name,
            "status": "ABORTED",
            "duration_seconds": round(time.perf_counter() - self._start_time, 2) if self._start_time else 0.0,
            "total_steps": self._total_steps,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "copyright": __copyright__,
        }
        self._last_audit_summary = aborted_summary
        if self._workflow_id:
            self._audit_summaries[self._workflow_id] = aborted_summary
        if self._execution_id:
            self._audit_summaries[self._execution_id] = aborted_summary
        return {"status": "aborted", "runner_state": "STOPPED"}

    def get_status(self) -> Dict[str, Any]:
        state = self.get_state()
        if self._runner and getattr(self._runner, "_ctx", None) and self._runner._ctx.abort_requested:
            state = "STOPPED"
        elapsed = round(time.perf_counter() - self._start_time, 2) if self.is_active() else 0.0
        return {
            "state": state,
            "execution_id": self._execution_id,
            "workflow_id": self._workflow_id,
            "workflow_name": self._workflow_name,
            "current_step_index": self._current_step_index,
            "total_steps": self._total_steps,
            "is_paused": state == "PAUSED",
            "elapsed_seconds": elapsed,
            "last_audit_summary": self._last_audit_summary,
            "copyright": __copyright__,
        }

    def get_audit_summary(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve audit log summary for a workflow ID or execution ID."""
        if not workflow_id or not isinstance(workflow_id, str):
            return None

        # Guard against path length overflow or DoS
        if len(workflow_id) > 256:
            return None

        # Early rejection of wildcards (F-M4-03)
        if any(c in workflow_id for c in ("*", "?", "[", "]", "{", "}")):
            return None

        # Strict alphanumeric/slug sanitization
        safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "", workflow_id)
        if not safe_id or safe_id != workflow_id:
            return None

        # Evaluate active execution first (F-M4-04)
        if (self._workflow_id == safe_id or self._execution_id == safe_id) and self.is_active():
            return {
                "workflow_id": self._workflow_id,
                "execution_id": self._execution_id,
                "workflow_name": self._workflow_name,
                "status": self.get_state(),
                "duration_seconds": round(time.perf_counter() - self._start_time, 2),
                "total_steps": self._total_steps,
                "current_step_index": self._current_step_index,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "copyright": __copyright__,
            }

        # Check in-memory summaries
        if safe_id in self._audit_summaries:
            return self._audit_summaries[safe_id]

        # Check _last_audit_summary
        if (self._workflow_id == safe_id or self._execution_id == safe_id) and self._last_audit_summary:
            return self._last_audit_summary

        # On-disk fallback across audit_dirs
        audit_dirs = [Path.home() / ".kutomoto" / "audit", BASE_DIR / "data" / "audit", BASE_DIR / "logs" / "audit"]
        for audit_dir in audit_dirs:
            if audit_dir.is_dir():
                candidates = sorted(audit_dir.glob(f"audit_{safe_id}_*.json"), reverse=True)
                if not candidates:
                    candidates = sorted(audit_dir.glob(f"audit_*_{safe_id}_*.json"), reverse=True)
                for p in candidates:
                    try:
                        data = json.loads(p.read_text(encoding="utf-8"))
                        if data.get("workflow_id") == safe_id or data.get("execution_id") == safe_id:
                            summary = data.get("execution_summary", {})
                            return {
                                "workflow_id": data.get("workflow_id", safe_id),
                                "execution_id": data.get("execution_id", ""),
                                "workflow_name": data.get("workflow_name", ""),
                                "status": summary.get("final_status", "UNKNOWN"),
                                "duration_seconds": summary.get("duration_seconds", 0.0),
                                "total_steps": summary.get("total_steps", 0),
                                "successful_steps": summary.get("successful_steps", 0),
                                "failed_steps": summary.get("failed_steps", 0),
                                "retried_steps": summary.get("retried_steps", 0),
                                "timestamp_utc": data.get("timestamp_utc", ""),
                                "copyright": data.get("copyright", __copyright__),
                            }
                    except Exception:
                        pass
        return None

    def get_audit(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Alias for get_audit_summary."""
        return self.get_audit_summary(identifier)


# ==============================================================================
# 5. DEPENDENCY INJECTION & FACTORY
# ==============================================================================

repository = WorkflowRepository()
hub = WebSocketHub()
execution_manager = ServerExecutionManager(hub=hub)


def get_driver() -> Any:
    """Dependency provider returning production or mock Win32 driver."""
    if os.environ.get("KUTOMOTO_MOCK_DRIVER") == "1" or platform.system() != "Windows":
        return MockWin32Driver()
    try:
        from kutomoto.automation import win32_core
        if win32_core.user32 is None:
            return MockWin32Driver()
        return Win32DriverAdapter()
    except Exception:
        return MockWin32Driver()


def get_runner() -> ServerExecutionManager:
    """Dependency provider returning active execution manager."""
    return execution_manager


def get_repository() -> WorkflowRepository:
    """Dependency provider returning workflow repository."""
    return repository


# ==============================================================================
# 6. LIFESPAN & FASTAPI APPLICATION
# ==============================================================================

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # Startup: Set DPI awareness on Windows
    logger.info("kutomoto server starting — %s", __copyright__)
    try:
        driver = get_driver()
        if hasattr(driver, "set_dpi_awareness"):
            driver.set_dpi_awareness()
    except Exception as ex:
        logger.debug("DPI awareness initialization note: %s", ex)

    # Ensure UI directory exists
    UI_DIR.mkdir(parents=True, exist_ok=True)
    yield

    # Shutdown: Cleanly abort any ongoing automation and release modifiers
    if execution_manager.is_active():
        logger.info("Aborting active execution on server shutdown...")
        await execution_manager.abort()


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app_instance = FastAPI(
        title="kutomoto Automation Studio",
        description=f"Professional Forms Filling Automation System for Windows OS\n{__copyright__}",
        version=__version__,
        lifespan=lifespan,
    )

    # CORS configuration
    app_instance.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global RFC 7807 Problem Details Handlers
    @app_instance.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": f"https://90studio.com/errors/{exc.status_code}",
                "title": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
                "status": exc.status_code,
                "detail": exc.detail,
                "instance": str(request.url.path),
                "copyright": __copyright__,
            },
        )

    @app_instance.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": f"https://90studio.com/errors/{exc.status_code}",
                "title": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
                "status": exc.status_code,
                "detail": exc.detail,
                "instance": str(request.url.path),
                "copyright": __copyright__,
            },
        )

    # --------------------------------------------------------------------------
    # REST API ENDPOINTS
    # --------------------------------------------------------------------------

    @app_instance.get("/api/health")
    async def health_check():
        """Health check probe verifying server status and 90Studio attribution."""
        return {
            "status": "ok",
            "app": "kutomoto",
            "system": "kutomoto",
            "version": __version__,
            "copyright": __copyright__,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "runner_state": execution_manager.get_state(),
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "dpi_aware": True,
            },
        }

    @app_instance.get("/api/workflows")
    async def list_workflows(repo: WorkflowRepository = Depends(get_repository)):
        """List all saved workflows."""
        return repo.list_all()

    @app_instance.post("/api/workflows", status_code=201)
    async def save_workflow(
        payload: Dict[str, Any],
        repo: WorkflowRepository = Depends(get_repository),
    ):
        """Validate and persist a KutomotoWorkflow document."""
        from kutomoto.engine.schema import KutomotoWorkflow
        try:
            workflow = KutomotoWorkflow.model_validate(payload)
        except ValidationError as ex:
            raise HTTPException(status_code=422, detail=ex.errors())

        saved = repo.save(workflow.model_dump())
        return saved

    @app_instance.get("/api/workflows/{workflow_id}")
    async def get_workflow(
        workflow_id: str,
        repo: WorkflowRepository = Depends(get_repository),
    ):
        """Get a single workflow by ID."""
        wf = repo.get(workflow_id)
        if wf is None:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")
        return wf

    @app_instance.delete("/api/workflows/{workflow_id}")
    async def delete_workflow(
        workflow_id: str,
        repo: WorkflowRepository = Depends(get_repository),
    ):
        """Delete a saved workflow by ID."""
        deleted = repo.delete(workflow_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")
        return {"success": True, "id": workflow_id, "message": "Workflow deleted successfully."}

    @app_instance.post("/api/designer/compile")
    async def compile_designer_layout(payload: Dict[str, Any]):
        """Compile a VisualFormLayout into an executable KutomotoWorkflow."""
        boxes = payload.get("boxes")
        if not boxes or not isinstance(boxes, list) or len(boxes) == 0:
            raise HTTPException(
                status_code=422,
                detail="Layout must contain at least one visual box.",
            )

        try:
            workflow = compile_visual_layout_to_workflow(payload)
            return workflow.model_dump()
        except (EmptyLayoutError, GeometryError, DuplicateBoxIdError, ValueError) as ex:
            raise HTTPException(status_code=422, detail=str(ex))
        except ValidationError as ex:
            raise HTTPException(status_code=422, detail=ex.errors())

    @app_instance.get("/api/windows")
    async def list_desktop_windows(
        visible_only: bool = True,
        driver: Any = Depends(get_driver),
    ):
        """Enumerate active desktop windows."""
        # 1. Injected Mock driver with mock_windows
        if hasattr(driver, "mock_windows") and isinstance(driver.mock_windows, list):
            results = []
            for w in driver.mock_windows:
                if not visible_only or w.get("is_visible", True):
                    results.append(w)
            return results

        # 2. Mock driver with windows dict (from safety.py)
        if hasattr(driver, "windows") and isinstance(driver.windows, dict):
            results = []
            for hwnd, info in driver.windows.items():
                rect = info.get("rect", (0, 0, 800, 600))
                item = {
                    "hwnd": hwnd,
                    "title": info.get("title", ""),
                    "class_name": info.get("class_name", "DesktopWindow"),
                    "pid": info.get("pid", 1000),
                    "executable_name": info.get("process_name", "app.exe"),
                    "executable_path": rf"C:\Windows\System32\{info.get('process_name', 'app.exe')}",
                    "is_visible": not info.get("is_iconic", False),
                    "is_iconic": info.get("is_iconic", False),
                    "rect": rect,
                    "client_rect": rect,
                }
                if not visible_only or item["is_visible"]:
                    results.append(item)
            return results

        # 3. Real Win32 window enumeration
        try:
            from kutomoto.automation.win32_window import enumerate_windows
            windows = enumerate_windows(visible_only=visible_only, non_empty_title_only=True)
            results = []
            for win in windows:
                if is_dataclass(win):
                    d = asdict(win)
                elif hasattr(win, "__dict__"):
                    d = dict(win.__dict__)
                else:
                    d = dict(win)
                results.append(d)
            return results
        except Exception as ex:
            logger.warning("Desktop window enumeration notice: %s", ex)
            return []

    @app_instance.post("/api/execute/start")
    async def start_execution(
        payload: Dict[str, Any],
        driver: Any = Depends(get_driver),
        repo: WorkflowRepository = Depends(get_repository),
    ):
        """Asynchronously launch workflow execution."""
        from kutomoto.engine.schema import KutomotoWorkflow

        wf_payload = payload.get("workflow")
        wf_id = payload.get("workflow_id")
        variables = payload.get("variables") or payload.get("runtime_variables") or {}

        if wf_payload:
            try:
                workflow = KutomotoWorkflow.model_validate(wf_payload)
            except ValidationError as ex:
                raise HTTPException(status_code=422, detail=ex.errors())
        elif wf_id:
            raw = repo.get(wf_id)
            if not raw:
                raise HTTPException(status_code=404, detail=f"Workflow '{wf_id}' not found.")
            workflow = KutomotoWorkflow.model_validate(raw)
        else:
            raise HTTPException(
                status_code=422,
                detail="Execution request must provide either 'workflow' object or 'workflow_id'.",
            )

        return await execution_manager.start(workflow=workflow, variables=variables, driver=driver)

    @app_instance.post("/api/execute/pause")
    async def pause_execution():
        """Pause running workflow."""
        return await execution_manager.pause()

    @app_instance.post("/api/execute/resume")
    async def resume_execution():
        """Resume paused workflow."""
        return await execution_manager.resume()

    @app_instance.post("/api/execute/abort")
    async def abort_execution():
        """Emergency execution abort."""
        return await execution_manager.abort()

    @app_instance.get("/api/execute/status")
    async def execution_status():
        """Get live execution state and progress."""
        return execution_manager.get_status()

    @app_instance.get("/api/execute/audit/{workflow_id:path}")
    async def get_execution_audit(
        workflow_id: str,
        runner_mgr: ServerExecutionManager = Depends(get_runner),
    ):
        """Retrieve audit log summary for a workflow execution."""
        summary = runner_mgr.get_audit_summary(workflow_id)
        if summary is None:
            raise HTTPException(
                status_code=404,
                detail=f"Audit log summary for workflow '{workflow_id}' not found.",
            )
        return summary

    @app_instance.get("/api/samples")
    async def list_sample_workflows():
        """List built-in enterprise sample workflows (Banking KYC Web & Telecom SIM Desktop)."""
        samples_list = []
        sample_files = [
            BASE_DIR / "samples" / "web" / "banking_kyc_workflow.json",
            BASE_DIR / "samples" / "desktop" / "telecom_sim_provisioning_workflow.json",
        ]
        for sf in sample_files:
            if sf.is_file():
                try:
                    data = json.loads(sf.read_text(encoding="utf-8"))
                    samples_list.append(data)
                except Exception as ex:
                    logger.warning("Failed to read sample workflow %s: %s", sf, ex)
        return samples_list

    @app_instance.post("/api/samples/launch/web")
    async def launch_sample_web(request: Request):
        """Launch the Sample Banking KYC Web Form in browser window."""
        import subprocess
        import webbrowser

        base_url = str(request.base_url).rstrip("/")
        sample_url = f"{base_url}/samples/web/index.html"

        if os.environ.get("KUTOMOTO_MOCK_DRIVER") == "1":
            return {
                "status": "launched",
                "target": "web",
                "url": sample_url,
                "copyright": __copyright__,
            }

        try:
            from kutomoto.__main__ import find_edge_executable
            edge_exe = find_edge_executable()
            if edge_exe:
                subprocess.Popen(
                    [
                        edge_exe,
                        f"--app={sample_url}",
                        "--window-size=1100,820",
                        "--window-position=120,80",
                        "--no-first-run",
                        "--no-default-browser-check",
                    ],
                    close_fds=(platform.system() != "Windows"),
                )
            else:
                webbrowser.open(sample_url)
        except Exception:
            webbrowser.open(sample_url)

        return {
            "status": "launched",
            "target": "web",
            "url": sample_url,
            "copyright": __copyright__,
        }

    @app_instance.post("/api/samples/launch/desktop")
    async def launch_sample_desktop():
        """Launch the Sample Telecom SIM Provisioning native Windows desktop form."""
        import subprocess
        import sys

        desktop_exe = BASE_DIR / "samples" / "desktop" / "sample_desktop_form.exe"
        desktop_py = BASE_DIR / "samples" / "desktop" / "sample_desktop_form.py"

        if os.environ.get("KUTOMOTO_MOCK_DRIVER") == "1":
            return {
                "status": "launched",
                "target": "desktop",
                "executable": str(desktop_exe if desktop_exe.is_file() else desktop_py),
                "copyright": __copyright__,
            }

        if desktop_exe.is_file():
            subprocess.Popen([str(desktop_exe)], cwd=str(BASE_DIR))
            launched_path = str(desktop_exe)
        elif desktop_py.is_file():
            subprocess.Popen([sys.executable, str(desktop_py)], cwd=str(BASE_DIR))
            launched_path = str(desktop_py)
        else:
            raise HTTPException(status_code=404, detail="Sample desktop form executable/script not found.")

        return {
            "status": "launched",
            "target": "desktop",
            "executable": launched_path,
            "copyright": __copyright__,
        }

    # --------------------------------------------------------------------------
    # WEBSOCKET STREAMING
    # --------------------------------------------------------------------------

    @app_instance.websocket("/ws/execution")
    async def execution_websocket(websocket: WebSocket):
        """Real-time bi-directional telemetry and control WebSocket."""
        await hub.connect(websocket)
        try:
            while True:
                msg_text = await websocket.receive_text()
                try:
                    data = json.loads(msg_text)
                    action = data.get("action")
                    if action == "pause":
                        await execution_manager.pause()
                    elif action == "resume":
                        await execution_manager.resume()
                    elif action == "abort":
                        await execution_manager.abort()
                    elif data.get("event") == "ping":
                        await websocket.send_json({"event": "pong", "copyright": __copyright__})
                except Exception:
                    pass
        except WebSocketDisconnect:
            await hub.disconnect(websocket)
        except Exception:
            await hub.disconnect(websocket)

    # --------------------------------------------------------------------------
    # STATIC ASSET ROUTING (SERVED AT ROOT & /samples)
    # --------------------------------------------------------------------------

    samples_dir = BASE_DIR / "samples"
    if samples_dir.exists():
        app_instance.mount("/samples", StaticFiles(directory=str(samples_dir), html=True), name="samples")

    @app_instance.get("/")
    async def root_index():
        """Serve index.html at root path."""
        index_file = UI_DIR / "index.html"
        if index_file.is_file():
            return FileResponse(index_file, media_type="text/html")
        return HTMLResponse(
            f"<!DOCTYPE html><html><body><h1>kutomoto</h1><p>{__copyright__}</p></body></html>",
            media_type="text/html",
        )

    # Mount UI directory for /css, /js, etc. (registered after API routes)
    if UI_DIR.exists():
        app_instance.mount("/", StaticFiles(directory=str(UI_DIR), html=True), name="ui")

    return app_instance


app = create_app()


def run_server(host: str = "127.0.0.1", port: int = 8765, reload: bool = False) -> None:
    """Entry point for launching the server using uvicorn."""
    import uvicorn
    uvicorn.run("kutomoto.server.app:app", host=host, port=port, reload=reload)
