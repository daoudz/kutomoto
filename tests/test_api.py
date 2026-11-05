"""
tests.test_api
Comprehensive automated REST API & WebSocket test suite for kutomoto server.
Copyrights reserved to 90Studio
"""

import copy
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

import pytest

SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from fastapi.testclient import TestClient  # noqa: E402

from kutomoto import __version__  # noqa: E402
from kutomoto.server.app import BASE_DIR, app, execution_manager, get_driver  # noqa: E402


# ==============================================================================
# 1. TEST FIXTURES & MOCK DRIVER
# ==============================================================================

class MockWin32Driver:
    """Mock Win32 Driver simulating desktop window and input interactions."""

    def __init__(self):
        self.dpi_set = False
        self.cursor_pos = (500, 400)
        self.foreground_hwnd = 1001
        self.clicks: List[Tuple[int, int, str, int]] = []
        self.typed_text: List[str] = []
        self.pressed_keys: List[Tuple[str, int]] = []
        self.modifiers_released = False
        self.cleared_fields: List[str] = []
        self.scrolls: List[Tuple[int, int]] = []
        self.held_keys: List[Any] = []
        self.released_keys: List[Any] = []
        self.mouse_buttons_down: List[str] = []
        self.mouse_buttons_up: List[str] = []
        self.mock_windows = [
            {
                "hwnd": 1001,
                "title": "Banking KYC Customer Onboarding - Microsoft Edge",
                "class_name": "Chrome_WidgetWin_1",
                "pid": 1420,
                "executable_name": "msedge.exe",
                "executable_path": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                "is_visible": True,
                "is_iconic": False,
                "rect": (0, 0, 1920, 1080),
                "client_rect": (0, 0, 1920, 1040),
            },
            {
                "hwnd": 1002,
                "title": "Telecom SIM Provisioning Terminal (Win32)",
                "class_name": "TkTopLevel",
                "pid": 2840,
                "executable_name": "python.exe",
                "executable_path": r"C:\Python314\python.exe",
                "is_visible": True,
                "is_iconic": False,
                "rect": (100, 100, 800, 600),
                "client_rect": (100, 100, 800, 560),
            },
        ]

    def set_dpi_awareness(self) -> bool:
        self.dpi_set = True
        return True

    def get_screen_dimensions(self) -> Tuple[int, int]:
        return (1920, 1080)

    def get_cursor_pos(self) -> Tuple[int, int]:
        return self.cursor_pos

    def set_cursor_pos(self, x: int, y: int) -> None:
        self.cursor_pos = (x, y)

    def get_foreground_window(self) -> int:
        return self.foreground_hwnd

    def find_window(
        self,
        title_pattern: str,
        match_mode: str = "contains",
        process_name: Optional[str] = None,
    ) -> Optional[int]:
        for w in self.mock_windows:
            if title_pattern.lower() in w["title"].lower():
                return w["hwnd"]
        return None

    def focus_window(self, hwnd: int, timeout_ms: int = 1500) -> bool:
        self.foreground_hwnd = hwnd
        return True

    def get_window_bounds(self, hwnd: int) -> Tuple[int, int, int, int]:
        for w in self.mock_windows:
            if w["hwnd"] == hwnd:
                return w["rect"]
        return (0, 0, 1920, 1080)

    def get_client_rect(self, hwnd: int) -> Tuple[int, int, int, int]:
        for w in self.mock_windows:
            if w["hwnd"] == hwnd:
                return w["client_rect"]
        return (0, 0, 1920, 1040)

    def client_to_screen(self, hwnd: int, client_x: int, client_y: int) -> Tuple[int, int]:
        bounds = self.get_window_bounds(hwnd)
        return (bounds[0] + client_x, bounds[1] + client_y)

    def send_click(self, x: int, y: int, button: str = "left", click_count: int = 1) -> None:
        self.clicks.append((x, y, button, click_count))

    def send_mouse_move(self, x: int, y: int) -> None:
        self.cursor_pos = (x, y)

    def send_text(self, text: str, delay_between_keys_ms: int = 20, use_clipboard_threshold: int = 40) -> None:
        self.typed_text.append(text)

    def send_key_press(self, key_name: str, repeat_count: int = 1) -> None:
        self.pressed_keys.append((key_name, repeat_count))

    def send_hotkey(self, modifiers: List[str], key: str) -> None:
        self.pressed_keys.append(("+".join(modifiers) + "+" + key, 1))

    def clear_field(self, strategy: str = "select_all_backspace") -> None:
        self.cleared_fields.append(strategy)

    def send_scroll(self, delta_x: int, delta_y: int) -> None:
        self.scrolls.append((delta_x, delta_y))

    def release_all_modifiers(self) -> None:
        self.modifiers_released = True

    def is_key_pressed(self, vk_code_or_name: Any) -> bool:
        return False

    def send_key_down(self, vk_name: Any) -> None:
        self.held_keys.append(vk_name)

    def send_key_up(self, vk_name: Any) -> None:
        self.released_keys.append(vk_name)

    def send_mouse_down(self, button: str = "left") -> None:
        self.mouse_buttons_down.append(button)

    def send_mouse_up(self, button: str = "left") -> None:
        self.mouse_buttons_up.append(button)


@pytest.fixture
def mock_driver():
    return MockWin32Driver()


@pytest.fixture
def client(mock_driver, monkeypatch, tmp_path):
    """TestClient fixture overriding automation driver with MockWin32Driver and isolated workflow storage."""
    from kutomoto.server.app import WorkflowRepository, get_repository, repository
    tmp_repo = WorkflowRepository(tmp_path / "workflows")
    monkeypatch.setattr(repository, "storage_dir", tmp_repo.storage_dir)
    app.dependency_overrides[get_driver] = lambda: mock_driver
    app.dependency_overrides[get_repository] = lambda: tmp_repo
    monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def valid_workflow_payload() -> Dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "id": str(uuid.uuid4()),
        "name": "KYC Automated Onboarding Flow",
        "description": "Enterprise automated KYC workflow",
        "author": "90Studio QA Engineer",
        "copyright": "Copyrights reserved to 90Studio",
        "source_mode": "manual_step_flow",
        "target_application": {
            "type": "web_browser",
            "window_title_pattern": "Banking KYC Customer Onboarding",
            "process_name": "msedge.exe",
            "match_mode": "contains",
        },
        "execution_settings": {
            "countdown_seconds": 1,
            "default_step_delay_ms": 10,
            "typing_speed_ms": 5,
            "stop_on_error": True,
            "error_recovery_policy": "abort",
            "max_step_retries": 1,
            "failsafe_corner_enabled": True,
            "abort_hotkey": "Escape",
        },
        "variables": [
            {
                "name": "customer_name",
                "default_value": "Daoud Enterprise",
                "type": "string",
                "required": True,
            }
        ],
        "steps": [
            {
                "step_id": str(uuid.uuid4()),
                "sequence_index": 1,
                "label": "Focus KYC Portal Window",
                "action_type": "focus_window",
                "enabled": True,
                "pre_delay_ms": 0,
                "post_delay_ms": 10,
                "parameters": {
                    "window_title_pattern": "Banking KYC Customer Onboarding",
                    "match_mode": "contains",
                },
            },
            {
                "step_id": str(uuid.uuid4()),
                "sequence_index": 2,
                "label": "Click Full Name Input Box",
                "action_type": "click",
                "enabled": True,
                "pre_delay_ms": 0,
                "post_delay_ms": 10,
                "parameters": {
                    "norm_x": 0.25,
                    "norm_y": 0.35,
                    "coordinate_mode": "normalized",
                    "button": "left",
                    "click_count": 1,
                },
            },
            {
                "step_id": str(uuid.uuid4()),
                "sequence_index": 3,
                "label": "Type Customer Full Name",
                "action_type": "type_text",
                "enabled": True,
                "pre_delay_ms": 0,
                "post_delay_ms": 10,
                "parameters": {
                    "text": "{{customer_name}}",
                    "is_secret": False,
                    "keystroke_delay_ms": 5,
                },
            },
        ],
    }


@pytest.fixture
def valid_designer_layout_payload() -> Dict[str, Any]:
    return {
        "id": "layout_kyc_001",
        "name": "Visual Form Layout Banking",
        "target": {
            "type": "windows_desktop",
            "match_pattern": "Banking KYC Customer Onboarding",
        },
        "canvas": {
            "width": 1280.0,
            "height": 800.0,
            "scale": 1.0,
        },
        "boxes": [
            {
                "id": "box_first_name",
                "name": "First Name",
                "geometry": {"x": 100.0, "y": 150.0, "width": 250.0, "height": 36.0},
                "sequence_index": 1,
                "action_type": "type_text",
                "value": "Daoud",
                "navigation": "tab",
                "clear_before": True,
            },
            {
                "id": "box_submit",
                "name": "Submit Button",
                "geometry": {"x": 100.0, "y": 250.0, "width": 120.0, "height": 40.0},
                "sequence_index": 2,
                "action_type": "submit",
                "value": "",
                "navigation": "none",
                "clear_before": False,
            },
        ],
    }


# ==============================================================================
# 2. HEALTH & BRANDING TEST SUITE
# ==============================================================================

class TestHealthAndBranding:
    """Verifies health check endpoints and 90Studio copyright requirements."""

    def test_health_check_status_code_and_version(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == __version__
        assert data["system"] == "kutomoto"

    def test_health_check_90studio_branding_enforcement(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["copyright"] == "Copyrights reserved to 90Studio"

    def test_root_endpoint_serves_spa_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        assert "kutomoto" in resp.text
        assert "90Studio" in resp.text
        assert (
            "<title>kutomoto — Enterprise Form Automation — Copyrights reserved to 90Studio</title>"
            in resp.text
        )


# ==============================================================================
# 3. WORKFLOW CRUD TEST SUITE
# ==============================================================================

class TestWorkflowCrud:
    """Verifies complete CRUD operations for KutomotoWorkflow persistence."""

    def test_list_workflows_returns_200(self, client):
        resp = client.get("/api/workflows")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_workflow_valid_payload(self, client, valid_workflow_payload):
        resp = client.post("/api/workflows", json=valid_workflow_payload)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["id"] == valid_workflow_payload["id"]
        assert data["name"] == valid_workflow_payload["name"]
        assert data["copyright"] == "Copyrights reserved to 90Studio"
        assert len(data["steps"]) == 3

    def test_create_workflow_rejects_missing_copyright(self, client, valid_workflow_payload):
        bad_payload = copy.deepcopy(valid_workflow_payload)
        bad_payload["copyright"] = "Unauthorized Copyright 2026"
        resp = client.post("/api/workflows", json=bad_payload)
        assert resp.status_code == 422

    def test_create_workflow_rejects_empty_steps(self, client, valid_workflow_payload):
        bad_payload = copy.deepcopy(valid_workflow_payload)
        bad_payload["steps"] = []
        resp = client.post("/api/workflows", json=bad_payload)
        assert resp.status_code == 422

    def test_get_workflow_by_id_success(self, client, valid_workflow_payload):
        # Save first
        client.post("/api/workflows", json=valid_workflow_payload)
        wf_id = valid_workflow_payload["id"]
        resp = client.get(f"/api/workflows/{wf_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == wf_id

    def test_get_workflow_by_id_not_found(self, client):
        missing_id = str(uuid.uuid4())
        resp = client.get(f"/api/workflows/{missing_id}")
        assert resp.status_code == 404

    def test_delete_workflow_success(self, client, valid_workflow_payload):
        wf_id = valid_workflow_payload["id"]
        client.post("/api/workflows", json=valid_workflow_payload)
        del_resp = client.delete(f"/api/workflows/{wf_id}")
        assert del_resp.status_code in (200, 204)

        # Subsequent GET should return 404
        get_resp = client.get(f"/api/workflows/{wf_id}")
        assert get_resp.status_code == 404


# ==============================================================================
# 4. DESIGNER COMPILER ENDPOINT TEST SUITE
# ==============================================================================

class TestDesignerCompileEndpoint:
    """Verifies compilation of VisualFormLayout into KutomotoWorkflow via API."""

    def test_designer_compile_success(self, client, valid_designer_layout_payload):
        resp = client.post("/api/designer/compile", json=valid_designer_layout_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["copyright"] == "Copyrights reserved to 90Studio"
        assert data["source_mode"] == "visual_designer_generated"
        assert len(data["steps"]) >= 2
        # First step focuses target window
        assert data["steps"][0]["action_type"] == "focus_window"

    def test_designer_compile_empty_boxes_error(self, client, valid_designer_layout_payload):
        bad_layout = copy.deepcopy(valid_designer_layout_payload)
        bad_layout["boxes"] = []
        resp = client.post("/api/designer/compile", json=bad_layout)
        assert resp.status_code in (400, 422)


# ==============================================================================
# 5. WINDOWS ENUMERATION TEST SUITE
# ==============================================================================

class TestWindowsEnumeration:
    """Verifies GET /api/windows endpoint enumeration against automation core."""

    def test_get_windows_returns_list(self, client):
        resp = client.get("/api/windows")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if len(data) > 0:
            win = data[0]
            assert "hwnd" in win
            assert "title" in win
            assert "executable_name" in win

    def test_get_windows_visible_only_filter(self, client):
        resp = client.get("/api/windows?visible_only=true")
        assert resp.status_code == 200
        for win in resp.json():
            assert win.get("is_visible") is True


# ==============================================================================
# 6. EXECUTION LIFECYCLE TEST SUITE
# ==============================================================================

class TestExecutionLifecycle:
    """Verifies starting, pausing, resuming, aborting, and querying execution status."""

    def test_execution_initial_status_idle(self, client):
        resp = client.get("/api/execute/status")
        assert resp.status_code == 200
        assert resp.json()["state"] == "IDLE"

    def test_execution_start_pause_resume_abort(self, client, valid_workflow_payload):
        # 1. Start execution
        start_resp = client.post("/api/execute/start", json={"workflow": valid_workflow_payload})
        assert start_resp.status_code in (200, 202)
        exec_id = start_resp.json()["execution_id"]
        assert exec_id is not None

        # 2. Pause execution
        pause_resp = client.post("/api/execute/pause")
        assert pause_resp.status_code == 200

        # 3. Resume execution
        resume_resp = client.post("/api/execute/resume")
        assert resume_resp.status_code == 200

        # 4. Abort execution
        abort_resp = client.post("/api/execute/abort")
        assert abort_resp.status_code == 200

        # Verify final state is STOPPED or IDLE
        status_resp = client.get("/api/execute/status")
        assert status_resp.json()["state"] in ("STOPPED", "IDLE", "COMPLETED")


# ==============================================================================
# 7. WEBSOCKET STREAMING TEST SUITE
# ==============================================================================

class TestWebSocketExecution:
    """Verifies real-time event broadcasting over /ws/execution."""

    def test_websocket_connects_and_receives_events(self, client, valid_workflow_payload):
        with client.websocket_connect("/ws/execution") as ws:
            # Trigger execution in background
            client.post("/api/execute/start", json={"workflow": valid_workflow_payload})

            # Read first event from stream
            msg = ws.receive_json()
            assert "event" in msg or "type" in msg
            event_type = msg.get("event") or msg.get("type")
            assert event_type in ("state_change", "countdown_tick", "step_started", "log", "connection_established")


# ==============================================================================
# 8. AUDIT LOG ENDPOINT TEST SUITE
# ==============================================================================

class TestAuditLogEndpoint:
    """Verifies GET /api/execute/audit/{workflow_id} compliance and 90Studio audit trails."""

    def test_get_audit_non_existent_workflow_returns_404(self, client):
        """Verify 404 Not Found when workflow has not been executed or does not exist."""
        non_existent_id = str(uuid.uuid4())
        resp = client.get(f"/api/execute/audit/{non_existent_id}")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        assert non_existent_id in data["detail"]
        assert data.get("copyright") == "Copyrights reserved to 90Studio"

    def test_get_audit_completed_workflow_returns_200_with_watermark(self, client, valid_workflow_payload):
        """Verify 200 OK returning structured audit log with 90Studio watermark upon completion."""
        wf_id = valid_workflow_payload["id"]
        # Fast execution with 0 delay
        fast_payload = copy.deepcopy(valid_workflow_payload)
        for s in fast_payload["steps"]:
            s["pre_delay_ms"] = 0
            s["post_delay_ms"] = 0

        # Start execution
        start_resp = client.post("/api/execute/start", json={"workflow": fast_payload})
        assert start_resp.status_code in (200, 202)
        exec_id = start_resp.json()["execution_id"]

        # Wait briefly for execution completion
        for _ in range(30):
            st = client.get("/api/execute/status").json()
            if st["state"] in ("IDLE", "COMPLETED", "SUCCESS"):
                break
            time.sleep(0.05)

        # Query audit endpoint
        audit_resp = client.get(f"/api/execute/audit/{wf_id}")
        assert audit_resp.status_code == 200
        audit = audit_resp.json()

        assert audit["workflow_id"] == wf_id
        assert audit["execution_id"] == exec_id
        assert audit["copyright"] == "Copyrights reserved to 90Studio"
        assert audit["status"] in ("SUCCESS", "COMPLETED")
        assert audit["total_steps"] == len(fast_payload["steps"])
        assert "duration_seconds" in audit

    def test_get_audit_aborted_workflow_returns_200_with_aborted_status(self, client, valid_workflow_payload):
        """Verify 200 OK returning ABORTED audit record with 90Studio watermark when aborted."""
        wf_id = valid_workflow_payload["id"]
        long_payload = copy.deepcopy(valid_workflow_payload)
        for s in long_payload["steps"]:
            s["pre_delay_ms"] = 500

        # Start execution
        start_resp = client.post("/api/execute/start", json={"workflow": long_payload})
        assert start_resp.status_code in (200, 202)

        # Abort execution immediately
        abort_resp = client.post("/api/execute/abort")
        assert abort_resp.status_code == 200

        # Query audit endpoint
        audit_resp = client.get(f"/api/execute/audit/{wf_id}")
        assert audit_resp.status_code == 200
        audit = audit_resp.json()

        assert audit["workflow_id"] == wf_id
        assert audit["copyright"] == "Copyrights reserved to 90Studio"
        assert audit["status"] in ("ABORTED", "STOPPED")

    def test_get_audit_wildcard_and_path_traversal_sanitization_rejects_404(self, client):
        """
        Regression test for Finding F-M4-03 (Glob Pattern Injection & Information Disclosure).
        Ensures wildcard patterns (*, *sensitive*) and path traversal attempts (..%2F..%2Fwin.ini)
        are neutralized, returning HTTP 404 Problem Details with 90Studio copyright attribution
        and strictly preventing disclosure of stored on-disk audit records.
        """
        audit_dir = BASE_DIR / "data" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        confidential_wf_name = "TOP_SECRET_BANKING_WIRE_COMPLIANCE_90STUDIO"
        confidential_wf_id = f"sensitive_payroll_{uuid.uuid4().hex[:8]}"
        confidential_file = audit_dir / f"audit_{confidential_wf_id}_exec99_20261105.json"

        confidential_file.write_text(
            json.dumps({
                "workflow_id": confidential_wf_id,
                "execution_id": "exec-confidential-99",
                "workflow_name": confidential_wf_name,
                "timestamp_utc": "2026-11-05T00:00:00Z",
                "copyright": "Copyrights reserved to 90Studio",
                "execution_summary": {
                    "total_steps": 3,
                    "successful_steps": 3,
                    "failed_steps": 0,
                    "retried_steps": 0,
                    "duration_seconds": 1.5,
                    "final_status": "SUCCESS",
                },
            }),
            encoding="utf-8",
        )

        try:
            # Clear in-memory caches to guarantee disk query resolution is evaluated
            execution_manager._audit_summaries.clear()
            execution_manager._last_audit_summary = None

            adversarial_queries = [
                "*",
                "*sensitive*",
                "..%2F..%2Fwin.ini",
                "C%3A%2F",
                "C:/",
                "D%3A%2F",
            ]

            for query in adversarial_queries:
                resp = client.get(f"/api/execute/audit/{query}")
                assert resp.status_code == 404, f"Query '{query}' expected HTTP 404, got {resp.status_code}: {resp.text}"
                data = resp.json()

                # Verify RFC 7807 Problem Details and 90Studio attribution
                assert data.get("copyright") == "Copyrights reserved to 90Studio"
                assert data.get("status") == 404
                assert "404" in str(data.get("type", ""))

                # Verify strict non-disclosure of confidential execution history
                assert confidential_wf_name not in resp.text
                assert confidential_wf_id not in resp.text
                assert "exec-confidential-99" not in resp.text
        finally:
            if confidential_file.exists():
                confidential_file.unlink()

    def test_get_audit_active_execution_and_disk_fallback_by_execution_id(self, client, valid_workflow_payload):
        """
        Regression test for Finding F-M4-04 (Asymmetric Identifier Handling in Active Polling & Disk Fallback).
        1. Launches a workflow with non-zero step delay.
        2. Queries /api/execute/audit/{execution_id} while active: asserts HTTP 200 OK, status 'RUNNING',
           and 90Studio attribution watermark.
        3. Cleans up execution via emergency abort.
        4. Writes an on-disk audit log with pattern audit_{wf_id}_{exec_id}_{timestamp}.json.
        5. Clears in-memory caches to force disk lookup fallback.
        6. Queries /api/execute/audit/{execution_id}: asserts HTTP 200 OK matching execution_id, workflow_id,
           and 90Studio attribution watermark.
        """
        active_payload = copy.deepcopy(valid_workflow_payload)
        active_payload["execution_settings"]["countdown_seconds"] = 0
        for s in active_payload["steps"]:
            s["pre_delay_ms"] = 1000
            s["post_delay_ms"] = 1000

        # 1. Start execution
        start_resp = client.post("/api/execute/start", json={"workflow": active_payload})
        assert start_resp.status_code in (200, 202)
        start_data = start_resp.json()
        exec_id = start_data["execution_id"]
        wf_id = active_payload["id"]

        audit_dir = BASE_DIR / "data" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        disk_file = audit_dir / f"audit_{wf_id}_{exec_id}_20261105_120000.json"

        try:
            # Wait briefly for runner to enter active RUNNING state
            for _ in range(20):
                st = client.get("/api/execute/status").json()
                if st.get("state") == "RUNNING":
                    break
                time.sleep(0.02)

            # 2. Query while actively running using execution_id
            active_resp = client.get(f"/api/execute/audit/{exec_id}")
            assert active_resp.status_code == 200, f"Active query by execution_id failed: {active_resp.text}"
            active_data = active_resp.json()
            assert active_data["execution_id"] == exec_id
            assert active_data["workflow_id"] == wf_id
            assert active_data["status"] == "RUNNING"
            assert active_data.get("copyright") == "Copyrights reserved to 90Studio"

            # 3. Cleanly abort execution
            abort_resp = client.post("/api/execute/abort")
            assert abort_resp.status_code == 200

            # 4. Create on-disk audit record matching engine format
            disk_content = {
                "workflow_id": wf_id,
                "execution_id": exec_id,
                "workflow_name": active_payload["name"],
                "timestamp_utc": "2026-11-05T12:00:00Z",
                "copyright": "Copyrights reserved to 90Studio",
                "execution_summary": {
                    "total_steps": len(active_payload["steps"]),
                    "successful_steps": 0,
                    "failed_steps": 0,
                    "retried_steps": 0,
                    "duration_seconds": 0.25,
                    "final_status": "ABORTED",
                },
            }
            disk_file.write_text(json.dumps(disk_content), encoding="utf-8")

            # 5. Clear in-memory caches to force disk fallback
            execution_manager._audit_summaries.clear()
            execution_manager._last_audit_summary = None

            # 6. Query by execution_id on disk fallback
            disk_resp = client.get(f"/api/execute/audit/{exec_id}")
            assert disk_resp.status_code == 200, f"Disk fallback by execution_id failed: {disk_resp.text}"
            disk_data = disk_resp.json()
            assert disk_data["execution_id"] == exec_id
            assert disk_data["workflow_id"] == wf_id
            assert disk_data["status"] == "ABORTED"
            assert disk_data.get("copyright") == "Copyrights reserved to 90Studio"

        finally:
            if disk_file.exists():
                disk_file.unlink()
            if execution_manager.is_active():
                client.post("/api/execute/abort")
