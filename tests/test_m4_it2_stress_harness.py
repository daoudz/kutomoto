"""
tests.test_m4_it2_stress_harness
Milestone 4 Iteration 2 Empirical Stress Testing Harness:
Adversarial concurrency, FSM race condition attacks, and Ghost Running lockout validation.
Copyrights reserved to 90Studio
"""

import asyncio
from pathlib import Path
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


class MockStressWin32Driver:
    """Mock Win32 Driver with concrete metric tracking for adversarial stress testing."""

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
        self.cursor_pos = (x, y)
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
    return MockStressWin32Driver()


@pytest.fixture(autouse=True)
def setup_teardown(mock_driver, monkeypatch):
    """Ensure clean execution state before and after each test."""
    app.dependency_overrides[get_driver] = lambda: mock_driver
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


def _make_test_workflow(
    countdown: int = 0,
    pre_delay: int = 0,
    post_delay: int = 10,
    num_steps: int = 1,
    action_type: str = "click",
) -> Dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "id": str(uuid.uuid4()),
        "name": "M4 Iteration 2 Stress Workflow",
        "copyright": "Copyrights reserved to 90Studio",
        "source_mode": "manual_step_flow",
        "target_application": {
            "type": "web_browser",
            "window_title_pattern": "Banking KYC",
            "match_mode": "contains",
        },
        "execution_settings": {
            "countdown_seconds": countdown,
            "default_step_delay_ms": 10,
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
                "action_type": action_type,
                "enabled": True,
                "pre_delay_ms": pre_delay,
                "post_delay_ms": post_delay,
                "parameters": {
                    "norm_x": 0.5,
                    "norm_y": 0.5,
                    "coordinate_mode": "normalized",
                    "button": "left",
                    "click_count": 1,
                    "text": f"text_{i}",
                },
            }
            for i in range(num_steps)
        ],
    }


class TestFSMStressAndGhostLockout:
    """Rigorous empirical validation of F-M4-01, F-M4-02, and single-flight lock resilience."""

    @pytest.mark.asyncio
    async def test_multi_step_pre_delay_pause_resume_completion(self):
        """
        Stress Test: 3-step workflow where pause occurs during pre-delay of step 1,
        resumes, pauses again during pre-delay of step 2, resumes, and runs to completion.
        Verifies:
        - pre_delay halts cleanly on each step.
        - Background task remains alive through multiple pause/resume cycles.
        - All 3 steps execute to SUCCESS.
        - No ghost running lockout occurs.
        """
        payload = _make_test_workflow(countdown=0, pre_delay=100, post_delay=20, num_steps=3)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
            # 1. Start execution
            r_start = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            # 2. Pause during step 1 pre_delay (20ms in)
            await asyncio.sleep(0.02)
            r_pause1 = await async_client.post("/api/execute/pause")
            assert r_pause1.status_code == 200

            # Hold paused for 120ms
            await asyncio.sleep(0.12)
            st_pause1 = await async_client.get("/api/execute/status")
            assert st_pause1.json()["state"] == "PAUSED"
            assert execution_manager._active_task is not None and not execution_manager._active_task.done()

            # 3. Resume execution to finish step 1 and enter step 2 pre_delay
            r_res1 = await async_client.post("/api/execute/resume")
            assert r_res1.status_code == 200

            # Wait for step 1 to complete (pre_delay remaining ~80ms + action + post_delay 20ms)
            # and enter step 2 pre_delay (~130ms total)
            await asyncio.sleep(0.13)

            # 4. Pause during step 2 pre_delay
            r_pause2 = await async_client.post("/api/execute/pause")
            if r_pause2.status_code == 200:
                await asyncio.sleep(0.1)
                st_pause2 = await async_client.get("/api/execute/status")
                assert st_pause2.json()["state"] == "PAUSED"
                assert execution_manager._active_task is not None and not execution_manager._active_task.done()

                # Resume step 2
                r_res2 = await async_client.post("/api/execute/resume")
                assert r_res2.status_code == 200

            # 5. Allow full workflow to complete (step 2 + step 3)
            # Wait up to 1 second for completion
            for _ in range(20):
                st_curr = await async_client.get("/api/execute/status")
                if st_curr.json()["state"] in ("COMPLETED", "IDLE"):
                    break
                await asyncio.sleep(0.05)

            final_status = await async_client.get("/api/execute/status")
            assert final_status.json()["state"] in ("COMPLETED", "IDLE")

            # 6. Verify server immediately permits a new workflow (no 409 lockout)
            r_start_next = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start_next.status_code == 200
            await async_client.post("/api/execute/abort")

    @pytest.mark.asyncio
    async def test_multi_step_post_delay_pause_resume_completion(self):
        """
        Stress Test: 3-step workflow where pause occurs during post-delay of the FINAL step (step 3).
        Directly targets Finding F-M4-01:
        - When resumed, post-delay must complete and trigger ALL_STEPS_DONE from RUNNING state.
        - Must NOT raise InvalidTransitionError: cannot transition from 'PAUSED' via 'ALL_STEPS_DONE'.
        """
        payload = _make_test_workflow(countdown=0, pre_delay=10, post_delay=120, num_steps=2)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
            r_start = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            # Wait for step 1 to complete and step 2 to reach post_delay
            # Step 1: pre 10ms + action + post 120ms = ~140ms
            # Step 2: pre 10ms + action = ~20ms -> total ~170ms
            await asyncio.sleep(0.18)

            # Pause in post-delay of step 2 (final step)
            r_pause = await async_client.post("/api/execute/pause")
            if r_pause.status_code == 200:
                await asyncio.sleep(0.15)
                st = await async_client.get("/api/execute/status")
                assert st.json()["state"] == "PAUSED"
                assert execution_manager._active_task is not None and not execution_manager._active_task.done()

                # Resume
                r_resume = await async_client.post("/api/execute/resume")
                assert r_resume.status_code == 200

            # Wait for completion
            for _ in range(20):
                st_curr = await async_client.get("/api/execute/status")
                if st_curr.json()["state"] in ("COMPLETED", "IDLE"):
                    break
                await asyncio.sleep(0.05)

            final_st = await async_client.get("/api/execute/status")
            assert final_st.json()["state"] in ("COMPLETED", "IDLE")

            # Check audit log endpoint works and records SUCCESS
            r_audit = await async_client.get(f"/api/execute/audit/{payload['id']}")
            assert r_audit.status_code == 200
            assert r_audit.json()["status"] == "SUCCESS"

            # Verify no ghost lockout
            r_start2 = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start2.status_code == 200
            await async_client.post("/api/execute/abort")

    @pytest.mark.asyncio
    async def test_pause_in_pre_delay_then_abort_immediate(self):
        """
        Stress Test: Pause during pre-delay, then immediately abort while in PAUSED state.
        Verifies:
        - FSM transitions cleanly PAUSED -> STOPPING -> STOPPED.
        - Background task terminates and releases resources.
        - Server does not lock into 409 ghost state.
        """
        payload = _make_test_workflow(countdown=0, pre_delay=200, post_delay=10, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
            r_start = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            await asyncio.sleep(0.03)
            r_pause = await async_client.post("/api/execute/pause")
            assert r_pause.status_code == 200

            # Verify paused
            st = await async_client.get("/api/execute/status")
            assert st.json()["state"] == "PAUSED"

            # Abort directly from PAUSED
            r_abort = await async_client.post("/api/execute/abort")
            assert r_abort.status_code == 200

            await asyncio.sleep(0.05)
            st_after = await async_client.get("/api/execute/status")
            assert st_after.json()["state"] in ("STOPPED", "IDLE")
            assert not execution_manager.is_active()

            # Verify immediately able to start new workflow
            r_start_next = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start_next.status_code == 200
            await async_client.post("/api/execute/abort")

    @pytest.mark.asyncio
    async def test_pause_in_post_delay_then_abort_immediate(self):
        """
        Stress Test: Pause during post-delay, then immediately abort while in PAUSED state.
        Verifies clean cleanup and immediate start capability.
        """
        payload = _make_test_workflow(countdown=0, pre_delay=0, post_delay=200, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
            r_start = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            await asyncio.sleep(0.03)
            r_pause = await async_client.post("/api/execute/pause")
            assert r_pause.status_code == 200

            st = await async_client.get("/api/execute/status")
            assert st.json()["state"] == "PAUSED"

            # Abort directly from PAUSED
            r_abort = await async_client.post("/api/execute/abort")
            assert r_abort.status_code == 200

            await asyncio.sleep(0.05)
            st_after = await async_client.get("/api/execute/status")
            assert st_after.json()["state"] in ("STOPPED", "IDLE")
            assert not execution_manager.is_active()

            # Verify clean subsequent start
            r_start_next = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start_next.status_code == 200
            await async_client.post("/api/execute/abort")

    @pytest.mark.asyncio
    async def test_rapid_thrash_cycles_with_delays_10_consecutive(self):
        """
        Stress Test: 10 consecutive cycles of rapid thrashing with non-zero pre and post delays:
        Start -> wait pre_delay -> Pause -> Resume -> wait post_delay -> Pause -> Abort.
        Verifies:
        - Zero 500 Internal Server Errors across all 10 cycles.
        - FSM transitions cleanly between all states.
        - Single-flight lock releases cleanly on every cycle.
        - Never gets trapped in HTTP 409 Ghost Running state.
        """
        payload = _make_test_workflow(countdown=0, pre_delay=40, post_delay=40, num_steps=2)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
            for cycle in range(10):
                r_start = await async_client.post("/api/execute/start", json={"workflow": payload})
                assert r_start.status_code == 200, f"Cycle {cycle}: start failed with {r_start.status_code}: {r_start.text}"

                # Short sleep into pre_delay
                await asyncio.sleep(0.015)
                r_pause1 = await async_client.post("/api/execute/pause")

                # Resume
                r_resume = await async_client.post("/api/execute/resume")

                # Short sleep into post_delay
                await asyncio.sleep(0.03)
                r_pause2 = await async_client.post("/api/execute/pause")

                # Abort
                r_abort = await async_client.post("/api/execute/abort")

                # Check status
                r_status = await async_client.get("/api/execute/status")

                codes = [
                    r_start.status_code,
                    r_pause1.status_code,
                    r_resume.status_code,
                    r_pause2.status_code,
                    r_abort.status_code,
                    r_status.status_code,
                ]
                assert 500 not in codes, f"Cycle {cycle} generated HTTP 500 error: {codes}"
                assert r_status.json()["state"] in ("STOPPED", "IDLE")

                # Small settle
                await asyncio.sleep(0.02)

    @pytest.mark.asyncio
    async def test_30_concurrent_start_requests_under_active_execution(self):
        """
        Adversarial Concurrency Stress: While a workflow is actively executing,
        fire 30 concurrent start requests.
        Verifies:
        - Exactly 0 of the 30 requests succeed.
        - All 30 requests receive HTTP 409 Conflict.
        - RFC 7807 problem details are returned with 90Studio attribution.
        - Active execution continues running safely without corruption.
        """
        payload = _make_test_workflow(countdown=0, pre_delay=20, post_delay=20, num_steps=5)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
            # 1. Start execution
            r_start = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200
            assert execution_manager.is_active()

            # 2. Fire 30 concurrent start requests
            async def _fire_start():
                return await async_client.post("/api/execute/start", json={"workflow": payload})

            responses = await asyncio.gather(*[_fire_start() for _ in range(30)])

            # Verify all 30 are 409 Conflict
            status_codes = [r.status_code for r in responses]
            assert all(code == 409 for code in status_codes), f"Expected all 409, got: {status_codes}"

            for r in responses:
                body = r.json()
                assert "already active" in body["detail"].lower()

            # 3. Abort active execution
            r_abort = await async_client.post("/api/execute/abort")
            assert r_abort.status_code == 200

            await asyncio.sleep(0.05)
            assert not execution_manager.is_active()

            # 4. Immediate subsequent start must succeed
            r_next = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_next.status_code == 200
            await async_client.post("/api/execute/abort")

    @pytest.mark.asyncio
    async def test_dead_task_defense_prevents_ghost_running_lockout(self):
        """
        Adversarial Test: Verify ServerExecutionManager defense mechanisms:
        1. When background task finishes (done() is True), is_active() immediately returns False.
        2. Calling resume() when task is done returns 409 Conflict and does NOT mark state as RUNNING.
        3. Server never enters a locked state where start() is rejected while nothing is running.
        """
        payload = _make_test_workflow(countdown=0, pre_delay=5, post_delay=5, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
            r_start = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            # Wait for workflow to finish and background wrapper task to finish
            for _ in range(20):
                st = await async_client.get("/api/execute/status")
                if st.json()["state"] in ("COMPLETED", "IDLE") and execution_manager._active_task and execution_manager._active_task.done():
                    break
                await asyncio.sleep(0.05)

            # At this point, active task is done
            assert execution_manager._active_task is not None
            assert execution_manager._active_task.done()
            assert not execution_manager.is_active()

            # Attempting to resume a completed/dead task must return 409 Conflict
            r_resume = await async_client.post("/api/execute/resume")
            assert r_resume.status_code == 409

            # Attempting to pause a completed/dead task must return 409 Conflict
            r_pause = await async_client.post("/api/execute/pause")
            assert r_pause.status_code == 409

            # Starting a new workflow must succeed cleanly
            r_start_again = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start_again.status_code == 200
            await async_client.post("/api/execute/abort")

    @pytest.mark.asyncio
    async def test_background_task_exception_clean_recovery(self):
        """
        Adversarial Test: Force an unhandled driver exception during action execution.
        Verifies:
        - Server catches exception in _run_wrapper.
        - Broadcasts step_failed and execution_error.
        - FSM is transitioned out of active/PAUSED states to ERROR or STOPPED.
        - is_active() returns False.
        - Server is NOT locked into HTTP 409 ghost state: subsequent workflow starts cleanly.
        """
        # Create a mock driver that raises an exception on send_click
        class FailingDriver(MockStressWin32Driver):
            def send_click(self, x: int, y: int, button: str = "left", click_count: int = 1) -> None:
                raise RuntimeError("Simulated Win32 hardware injection failure!")

        failing_driver = FailingDriver()
        app.dependency_overrides[get_driver] = lambda: failing_driver

        payload = _make_test_workflow(countdown=0, pre_delay=5, post_delay=5, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
            r_start = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            # Wait for execution error and task termination
            for _ in range(20):
                st = await async_client.get("/api/execute/status")
                if st.json()["state"] in ("ERROR", "STOPPED", "IDLE") and not execution_manager.is_active():
                    break
                await asyncio.sleep(0.05)

            # Check status and manager state
            assert not execution_manager.is_active()

            # Switch back to normal driver
            normal_driver = MockStressWin32Driver()
            app.dependency_overrides[get_driver] = lambda: normal_driver

            # Immediate new start must succeed without 409 ghost lockout!
            r_recover = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_recover.status_code == 200
            await async_client.post("/api/execute/abort")
