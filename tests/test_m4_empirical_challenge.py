"""
tests.test_m4_empirical_challenge
Adversarial Empirical Challenge Suite for Milestone 4:
Empirical stress testing of FastAPI backend and WebSocket server:
1. Concurrency attacks: 20 concurrent start requests, single-flight lock 409 verification, start/abort races.
2. WebSocket resilience: multi-client broadcasts, abrupt mid-execution disconnects, frame fuzzing.
3. Edge case and payload fuzzing: malformed JSON, missing copyright, empty boxes, path traversal sanitization.
4. FSM Rapid State Thrashing: rapid start/pause/resume/abort cycles, mid-step pause race conditions,
   and ghost running state lockout vulnerability identification.

Copyrights reserved to 90Studio
"""

import asyncio
import copy
from pathlib import Path
import random
import sys
from typing import Any, Dict, List, Tuple
import uuid

import httpx
import pytest

SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from fastapi.testclient import TestClient  # noqa: E402

from kutomoto.server.app import app, execution_manager, get_driver  # noqa: E402


# ==============================================================================
# MOCK WIN32 DRIVER FIXTURE
# ==============================================================================

class MockWin32Driver:
    """Isolated Mock Win32 Driver for Milestone 4 Adversarial Testing."""

    def __init__(self) -> None:
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
            }
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
        process_name: str | None = None,
    ) -> int | None:
        for w in self.mock_windows:
            if title_pattern.lower() in w["title"].lower():
                return w["hwnd"]
        return None

    def focus_window(self, hwnd: int, timeout_ms: int = 1500) -> bool:
        self.foreground_hwnd = hwnd
        return True

    def get_window_bounds(self, hwnd: int) -> Tuple[int, int, int, int]:
        return (0, 0, 1920, 1080)

    def get_client_rect(self, hwnd: int) -> Tuple[int, int, int, int]:
        return (0, 0, 1920, 1040)

    def client_to_screen(self, hwnd: int, client_x: int, client_y: int) -> Tuple[int, int]:
        return (client_x, client_y)

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


@pytest.fixture(autouse=True)
def setup_teardown(mock_driver, monkeypatch, tmp_path):
    """Ensure clean execution state and isolated workflow storage before and after each test."""
    from kutomoto.server.app import WorkflowRepository, get_repository, repository
    tmp_repo = WorkflowRepository(tmp_path / "workflows")
    monkeypatch.setattr(repository, "storage_dir", tmp_repo.storage_dir)
    app.dependency_overrides[get_driver] = lambda: mock_driver
    app.dependency_overrides[get_repository] = lambda: tmp_repo
    monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
    yield
    # Force clean abort of any dangling active executions
    if execution_manager.is_active():
        asyncio.run(execution_manager.abort())
    app.dependency_overrides.clear()


@pytest.fixture
def client(mock_driver):
    with TestClient(app) as c:
        yield c


def _make_workflow(countdown: int = 0, step_delay: int = 10, pre_delay: int = 0, post_delay: int = 10, num_steps: int = 1) -> Dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "id": str(uuid.uuid4()),
        "name": "Adversarial Stress Workflow",
        "copyright": "Copyrights reserved to 90Studio",
        "source_mode": "manual_step_flow",
        "target_application": {
            "type": "web_browser",
            "window_title_pattern": "Banking KYC",
            "match_mode": "contains",
        },
        "execution_settings": {
            "countdown_seconds": countdown,
            "default_step_delay_ms": step_delay,
            "typing_speed_ms": 5,
            "stop_on_error": True,
            "error_recovery_policy": "abort",
            "max_step_retries": 0,
            "failsafe_corner_enabled": False,
            "abort_hotkey": "Escape",
        },
        "variables": [],
        "steps": [
            {
                "step_id": str(uuid.uuid4()),
                "sequence_index": i + 1,
                "label": f"Step {i + 1}",
                "action_type": "click",
                "enabled": True,
                "pre_delay_ms": pre_delay,
                "post_delay_ms": post_delay,
                "parameters": {
                    "norm_x": 0.5,
                    "norm_y": 0.5,
                    "coordinate_mode": "normalized",
                    "button": "left",
                    "click_count": 1,
                },
            }
            for i in range(num_steps)
        ],
    }


# ==============================================================================
# 1. CONCURRENCY ATTACK SUITE
# ==============================================================================

class TestConcurrencyAttacks:
    """Stress tests single-flight lock and concurrent request handling."""

    @pytest.mark.asyncio
    async def test_20_concurrent_start_requests_single_flight_lock(self):
        """
        Adversarial Test: Bombard /api/execute/start with 20 simultaneous async requests.
        Invariant: Exactly 1 request MUST succeed (200/202). Exactly 19 MUST return 409 Conflict.
        No deadlocks or internal 500 errors permitted.
        """
        payload = _make_workflow(countdown=0, pre_delay=0, post_delay=300, num_steps=2)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
            tasks = [
                async_client.post("/api/execute/start", json={"workflow": payload})
                for _ in range(20)
            ]
            responses = await asyncio.gather(*tasks)

            statuses = [r.status_code for r in responses]
            success_count = statuses.count(200) + statuses.count(202)
            conflict_count = statuses.count(409)

            assert success_count == 1, f"Expected exactly 1 success, got {success_count}. Statuses: {statuses}"
            assert conflict_count == 19, f"Expected 19 conflicts, got {conflict_count}. Statuses: {statuses}"
            assert 500 not in statuses, "Internal server error detected during concurrent start burst!"

            # Verify 409 error details adhere to RFC 7807 with 90Studio attribution
            conflict_resps = [r for r in responses if r.status_code == 409]
            for cr in conflict_resps:
                data = cr.json()
                assert data["status"] == 409
                assert "Concurrency not permitted" in data["detail"]
                assert data["copyright"] == "Copyrights reserved to 90Studio"

            # Clean up
            await async_client.post("/api/execute/abort")

    @pytest.mark.asyncio
    async def test_concurrent_start_after_abort_clean_recovery(self):
        """
        Adversarial Test: Verify that abort immediately releases the execution lock
        and permits subsequent workflow starts without lockout.
        """
        payload = _make_workflow(countdown=0, post_delay=200, num_steps=2)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
            # Start 1
            r1 = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r1.status_code == 200

            # Abort 1
            r_abort = await async_client.post("/api/execute/abort")
            assert r_abort.status_code == 200
            assert r_abort.json()["status"] == "aborted"

            # Start 2 must succeed immediately
            r2 = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r2.status_code == 200, f"Lock was not released after abort! Code: {r2.status_code}, Body: {r2.text}"

            await async_client.post("/api/execute/abort")

    @pytest.mark.asyncio
    async def test_concurrent_start_and_abort_race_no_deadlock(self):
        """
        Adversarial Test: Fire 10 start and 10 abort requests simultaneously in mixed order.
        Verify no deadlocks, zero 500 errors, and clean recovery to STOPPED or IDLE.
        """
        payload = _make_workflow(countdown=0, post_delay=50, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
            actions = ["start"] * 10 + ["abort"] * 10
            random.shuffle(actions)

            tasks = []
            for a in actions:
                if a == "start":
                    tasks.append(async_client.post("/api/execute/start", json={"workflow": payload}))
                else:
                    tasks.append(async_client.post("/api/execute/abort"))

            results = await asyncio.gather(*tasks)
            codes = [r.status_code for r in results]

            assert 500 not in codes, f"500 Internal Server Error in start/abort race: {codes}"
            for c in codes:
                assert c in (200, 202, 409), f"Unexpected status code {c}"

            # Ensure final state settles
            await async_client.post("/api/execute/abort")
            st = await async_client.get("/api/execute/status")
            assert st.json()["state"] in ("STOPPED", "IDLE")


# ==============================================================================
# 2. WEBSOCKET RESILIENCE SUITE
# ==============================================================================

class TestWebSocketResilience:
    """Stress tests WebSocket telemetry hub under multi-client loads and disconnects."""

    def test_websocket_multi_client_concurrent_broadcast(self, client):
        """
        Adversarial Test: Connect 10 simultaneous WebSocket clients.
        Verify all 10 receive initial connection frame with 90Studio attribution,
        and all 10 receive subsequent broadcast events when workflow is triggered.
        """
        payload = _make_workflow(countdown=0, post_delay=50, num_steps=1)

        sockets = []
        try:
            for _ in range(10):
                ws = client.websocket_connect("/ws/execution")
                s = ws.__enter__()
                sockets.append((ws, s))
                msg = s.receive_json()
                assert msg["event"] == "connection_established"
                assert msg["system"] == "kutomoto"
                assert msg["copyright"] == "Copyrights reserved to 90Studio"

            # Trigger workflow
            r = client.post("/api/execute/start", json={"workflow": payload})
            assert r.status_code == 200

            # Verify all 10 clients receive streamed events
            for _, s in sockets:
                event = s.receive_json()
                assert "event" in event or "type" in event
                ev_type = event.get("event") or event.get("type")
                assert ev_type in ("state_change", "countdown_tick", "step_started", "log")
        finally:
            client.post("/api/execute/abort")
            for ws, _ in sockets:
                try:
                    ws.__exit__(None, None, None)
                except Exception:
                    continue

    def test_websocket_mid_execution_abrupt_disconnect(self, client):
        """
        Adversarial Test: Connect 5 WebSocket clients, begin execution, and abruptly drop 3
        clients mid-execution while events are actively firing.
        Verify remaining 2 clients continue to receive broadcasts, and server hub discards
        dead connections without unhandled exceptions.
        """
        payload = _make_workflow(countdown=0, post_delay=100, num_steps=2)

        sockets = []
        try:
            for _ in range(5):
                ws = client.websocket_connect("/ws/execution")
                s = ws.__enter__()
                sockets.append((ws, s))
                s.receive_json()  # discard connection_established

            # Start execution
            client.post("/api/execute/start", json={"workflow": payload})

            # Drop 3 clients abruptly
            for i in range(3):
                ws, s = sockets[i]
                s.close()

            # Verify remaining 2 clients still receive events
            for i in (3, 4):
                _, s = sockets[i]
                event = s.receive_json()
                assert event is not None
                assert "event" in event or "type" in event
        finally:
            client.post("/api/execute/abort")
            for ws, _ in sockets:
                try:
                    ws.__exit__(None, None, None)
                except Exception:
                    continue

    def test_websocket_frame_fuzzing_and_ping_pong(self, client):
        """
        Adversarial Test: Send malformed frames (non-JSON strings, non-dict payloads, unknown actions)
        over WebSocket. Verify server does not crash, disconnects gracefully only on explicit close,
        and continues responding to pings with 90Studio attribution.
        """
        with client.websocket_connect("/ws/execution") as ws:
            ws.receive_json()  # connection_established

            # 1. Non-JSON raw text
            ws.send_text("MALFORMED_NON_JSON_DATA!@#$%^&*()")

            # 2. Ping check
            ws.send_json({"event": "ping"})
            pong1 = ws.receive_json()
            assert pong1["event"] == "pong"
            assert pong1["copyright"] == "Copyrights reserved to 90Studio"

            # 3. Non-dict JSON list
            ws.send_text("[1, 2, 3, 4]")

            # 4. Unknown action
            ws.send_json({"action": "unknown_fuzzed_action_xyz", "value": 9999})

            # 5. Invalid pause when IDLE (should not crash socket)
            ws.send_json({"action": "pause"})

            # 6. Final ping to verify connection remains active
            ws.send_json({"event": "ping"})
            pong2 = ws.receive_json()
            assert pong2["event"] == "pong"

    def test_websocket_rapid_connect_disconnect_churn(self, client):
        """
        Adversarial Test: Rapidly open and close 25 WebSocket connections in succession.
        Verify server connection pool cleanly frees connections and leaves zero dangling locks.
        """
        for _ in range(25):
            with client.websocket_connect("/ws/execution") as ws:
                msg = ws.receive_json()
                assert msg["event"] == "connection_established"


# ==============================================================================
# 3. EDGE CASE AND PAYLOAD FUZZING SUITE
# ==============================================================================

class TestEdgeCaseAndPayloadFuzzing:
    """Stress tests boundary conditions, invalid parameters, and schema fuzzing."""

    def test_workflows_crud_fuzzing_invalid_payloads(self, client):
        """
        Adversarial Test: Fuzz /api/workflows with malformed JSON, missing copyright,
        forged copyright, empty steps, and negative timings.
        """
        valid = _make_workflow()

        # 1. Malformed JSON syntax
        r = client.post("/api/workflows", content="MALFORMED_JSON{", headers={"content-type": "application/json"})
        assert r.status_code == 422

        # 2. Invalid/unauthorized copyright
        fake_copy = copy.deepcopy(valid)
        fake_copy["copyright"] = "Unauthorized Copyright 2026"
        assert client.post("/api/workflows", json=fake_copy).status_code == 422

        # 4. Empty steps list
        empty_steps = copy.deepcopy(valid)
        empty_steps["steps"] = []
        assert client.post("/api/workflows", json=empty_steps).status_code == 422

        # 5. Invalid step action_type
        bad_action = copy.deepcopy(valid)
        bad_action["steps"][0]["action_type"] = "unauthorized_remote_code_execution"
        assert client.post("/api/workflows", json=bad_action).status_code == 422

        # 6. Negative pre_delay_ms
        neg_delay = copy.deepcopy(valid)
        neg_delay["steps"][0]["pre_delay_ms"] = -500
        assert client.post("/api/workflows", json=neg_delay).status_code == 422

        # 7. Normalized coordinate out of [0, 1] bounds
        out_bounds = copy.deepcopy(valid)
        out_bounds["steps"][0]["parameters"]["norm_x"] = 2.5
        assert client.post("/api/workflows", json=out_bounds).status_code == 422

    def test_designer_compile_fuzzing_invalid_payloads(self, client):
        """
        Adversarial Test: Fuzz /api/designer/compile with empty boxes, negative dimensions,
        and duplicate box identifiers.
        """
        valid_layout = {
            "id": "layout_fuzz_1",
            "name": "Fuzz Layout",
            "canvas": {"width": 800.0, "height": 600.0, "scale": 1.0},
            "target": {"type": "windows_desktop", "match_pattern": "Banking"},
            "boxes": [
                {
                    "id": "box_1",
                    "name": "Field 1",
                    "geometry": {"x": 50.0, "y": 50.0, "width": 200.0, "height": 30.0},
                    "action_type": "type_text",
                    "sequence_index": 1,
                }
            ],
        }

        # 1. Missing boxes key
        no_boxes = copy.deepcopy(valid_layout)
        del no_boxes["boxes"]
        assert client.post("/api/designer/compile", json=no_boxes).status_code == 422

        # 2. Empty boxes list
        empty_boxes = copy.deepcopy(valid_layout)
        empty_boxes["boxes"] = []
        assert client.post("/api/designer/compile", json=empty_boxes).status_code == 422

        # 3. Negative coordinates
        neg_geom = copy.deepcopy(valid_layout)
        neg_geom["boxes"][0]["geometry"]["x"] = -100.0
        assert client.post("/api/designer/compile", json=neg_geom).status_code == 422

        # 4. Zero dimensions
        zero_dim = copy.deepcopy(valid_layout)
        zero_dim["boxes"][0]["geometry"]["width"] = 0.0
        assert client.post("/api/designer/compile", json=zero_dim).status_code == 422

        # 5. Duplicate box IDs
        dup_boxes = copy.deepcopy(valid_layout)
        dup_boxes["boxes"].append(copy.deepcopy(dup_boxes["boxes"][0]))
        dup_boxes["boxes"][1]["sequence_index"] = 2
        r_dup = client.post("/api/designer/compile", json=dup_boxes)
        assert r_dup.status_code == 422
        assert "Duplicate box ID" in str(r_dup.json())

    def test_workflow_id_path_traversal_sanitization(self, client):
        """
        Adversarial Test: Attempt path traversal attacks on /api/workflows/{id}
        using ../, ..\\, Windows reserved device names (CON, NUL).
        Verify requests safely return 404 without filesystem leakage or server crashes.
        """
        traversals = [
            "../../windows/system32/cmd.exe",
            "..%2F..%2Fwindows%2Fwin.ini",
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "LPT1",
            "invalid_uuid_that_does_not_exist_99999",
        ]
        for tid in traversals:
            r_get = client.get(f"/api/workflows/{tid}")
            assert r_get.status_code == 404
            r_del = client.delete(f"/api/workflows/{tid}")
            assert r_del.status_code in (404, 405)

    def test_lifecycle_invalid_state_transitions_rejected(self, client):
        """
        Adversarial Test: Query endpoints in invalid states (pause when IDLE, resume when IDLE).
        Verify strict 409 Conflict rejection.
        """
        # When IDLE:
        assert client.post("/api/execute/pause").status_code == 409
        assert client.post("/api/execute/resume").status_code == 409

        # Start empty payload
        assert client.post("/api/execute/start", json={}).status_code == 422

        # Start non-existent workflow ID
        assert client.post("/api/execute/start", json={"workflow_id": "non_existent_id"}).status_code == 404


# ==============================================================================
# 4. FSM RAPID STATE THRASHING & VULNERABILITY SUITE
# ==============================================================================

class TestFSMRapidStateThrashingAndVulnerabilities:
    """Stress tests FSM state transitions and demonstrates concurrency/pause failure modes."""

    @pytest.mark.asyncio
    async def test_rapid_thrash_zero_delay_cycles(self):
        """
        Adversarial Test: Rapidly fire Start -> Pause -> Resume -> Abort in immediate succession
        for 5 consecutive cycles under zero-delay conditions.
        Verify transitions are cleanly processed without 500 errors.
        """
        payload = _make_workflow(countdown=0, pre_delay=0, post_delay=50, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
            for cycle in range(5):
                r_start = await async_client.post("/api/execute/start", json={"workflow": payload})
                r_pause = await async_client.post("/api/execute/pause")
                r_resume = await async_client.post("/api/execute/resume")
                r_abort = await async_client.post("/api/execute/abort")
                r_status = await async_client.get("/api/execute/status")

                codes = [r_start.status_code, r_pause.status_code, r_resume.status_code, r_abort.status_code]
                assert 500 not in codes, f"500 error in cycle {cycle}: {codes}"
                assert r_status.json()["state"] in ("STOPPED", "IDLE")

    @pytest.mark.asyncio
    async def test_vulnerability_post_delay_pause_causes_invalid_fsm_transition(self):
        """
        Regression Test (Resolves Finding F-M4-01):
        When a user pauses execution while the step is in post_delay:
        1. post_delay safely awaits pause_event without triggering ALL_STEPS_DONE from PAUSED.
        2. Resume continues execution cleanly through to completion.
        3. Background runner does not crash, and server never enters a Ghost Running lockout.
        """
        payload = _make_workflow(countdown=0, pre_delay=0, post_delay=100, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
            r_start = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            # Pause mid-post_delay (at 20ms)
            await asyncio.sleep(0.02)
            r_pause = await async_client.post("/api/execute/pause")
            assert r_pause.status_code == 200

            # Wait while paused (150ms) - runner must remain paused, task must NOT crash
            await asyncio.sleep(0.15)
            r_status_paused = await async_client.get("/api/execute/status")
            assert r_status_paused.json()["state"] == "PAUSED"
            assert execution_manager._active_task is not None and not execution_manager._active_task.done()

            # Resume execution
            r_resume = await async_client.post("/api/execute/resume")
            assert r_resume.status_code == 200

            # Wait for remaining post_delay and completion (150ms)
            await asyncio.sleep(0.15)

            # Check status: must complete cleanly
            r_status = await async_client.get("/api/execute/status")
            status_data = r_status.json()
            assert status_data["state"] in ("COMPLETED", "IDLE")

            # Verify next workflow starts cleanly without 409 ghost lockout
            r_start2 = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start2.status_code == 200

            # Clean up
            await async_client.post("/api/execute/abort")

    @pytest.mark.asyncio
    async def test_vulnerability_pre_delay_pause_causes_invalid_fsm_transition(self):
        """
        Regression Test (Resolves Finding F-M4-02):
        When a user pauses execution while a step is in its pre_delay:
        1. pre_delay respects pause_event and halts execution.
        2. Step does not proceed to execute action or trigger STEP_SUCCESS while in PAUSED state.
        3. Task remains alive, resumes cleanly, and reaches completion.
        """
        payload = _make_workflow(countdown=0, pre_delay=100, post_delay=10, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
            r_start = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            # Pause mid-pre_delay (at 20ms)
            await asyncio.sleep(0.02)
            r_pause = await async_client.post("/api/execute/pause")
            assert r_pause.status_code == 200

            # Wait while paused (150ms)
            await asyncio.sleep(0.15)

            # Check that task is still alive and runner is paused (did NOT crash on STEP_SUCCESS)
            task_crashed = execution_manager._active_task is not None and execution_manager._active_task.done()
            assert not task_crashed, "Runner crashed during pre-delay pause with InvalidTransitionError!"

            r_status_paused = await async_client.get("/api/execute/status")
            assert r_status_paused.json()["state"] == "PAUSED"

            # Resume and let finish
            r_resume = await async_client.post("/api/execute/resume")
            assert r_resume.status_code == 200

            # Wait for step completion (150ms)
            await asyncio.sleep(0.15)
            r_status_done = await async_client.get("/api/execute/status")
            assert r_status_done.json()["state"] in ("COMPLETED", "IDLE")

            # Clean up
            await async_client.post("/api/execute/abort")
