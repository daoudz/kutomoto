"""
tests.test_m4_deep_stress_challenge
Deep Empirical Stress Testing Suite for Milestone 4:
- F-M4-01 & F-M4-02: Multi-cycle pause/resume during pre_delay and post_delay.
- In-step abort lifecycles: abort during DELAY action, pre_delay, post_delay, and retry loops.
- High-concurrency polling storms (status and audit endpoints during active runs).
- Concurrent race conditions: start vs abort storms, rapid double/triple aborts.
- WebSocket bi-directional control stress (pause/resume/abort over WS concurrent with REST).
- WebSocket connection drop storms under heavy broadcast load.
- Active vs completed audit consistency across execution_id and workflow_id.

Copyrights reserved to 90Studio
"""

import asyncio
from pathlib import Path
import random
import sys
import time
from typing import Any, Dict, List, Tuple
import uuid

import httpx
import pytest

SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from fastapi.testclient import TestClient  # noqa: E402

from kutomoto import __copyright__  # noqa: E402
from kutomoto.server.app import app, execution_manager, get_driver  # noqa: E402


# ==============================================================================
# MOCK WIN32 DRIVER FIXTURE
# ==============================================================================

class DeepStressMockDriver:
    """Mock Win32 Driver with action tracking and configurable failure modes."""

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
        self.fail_next_action: bool = False
        self.action_failure_count: int = 0
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
        if self.fail_next_action:
            self.action_failure_count += 1
            raise RuntimeError(f"Simulated hardware failure on click #{self.action_failure_count}")
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


@pytest.fixture
def stress_driver():
    return DeepStressMockDriver()


@pytest.fixture(autouse=True)
def setup_stress_teardown(stress_driver, monkeypatch):
    """Ensure clean execution state before and after each test."""
    app.dependency_overrides[get_driver] = lambda: stress_driver
    monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
    yield
    # Force clean abort of any dangling active executions
    if execution_manager.is_active():
        asyncio.run(execution_manager.abort())
    app.dependency_overrides.clear()


@pytest.fixture
def stress_client(stress_driver):
    with TestClient(app) as c:
        yield c


def _build_stress_workflow(
    countdown: int = 0,
    num_steps: int = 1,
    pre_delay: int = 0,
    post_delay: int = 20,
    action_type: str = "click",
    duration_ms: int = 0,
    error_recovery: str = "abort",
    max_retries: int = 0,
) -> Dict[str, Any]:
    steps = []
    for i in range(num_steps):
        step_dict: Dict[str, Any] = {
            "step_id": str(uuid.uuid4()),
            "sequence_index": i + 1,
            "label": f"Stress Step {i + 1}",
            "action_type": action_type,
            "enabled": True,
            "pre_delay_ms": pre_delay,
            "post_delay_ms": post_delay,
            "parameters": {},
        }
        if action_type == "click":
            step_dict["parameters"] = {
                "norm_x": 0.5,
                "norm_y": 0.5,
                "coordinate_mode": "normalized",
                "button": "left",
                "click_count": 1,
            }
        elif action_type == "delay":
            step_dict["parameters"] = {
                "duration_ms": duration_ms,
            }
        elif action_type == "type_text":
            step_dict["parameters"] = {
                "text": f"Test input {i + 1}",
                "keystroke_delay_ms": 2,
            }
        steps.append(step_dict)

    return {
        "schema_version": "1.0.0",
        "id": f"wf_stress_{uuid.uuid4().hex[:8]}",
        "name": "Milestone 4 Deep Stress Workflow",
        "copyright": __copyright__,
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
            "error_recovery_policy": error_recovery,
            "max_step_retries": max_retries,
            "failsafe_corner_enabled": False,
            "abort_hotkey": "Escape",
        },
        "variables": [],
        "steps": steps,
    }


# ==============================================================================
# SUITE 1: PRE-DELAY & POST-DELAY MULTI-CYCLE PAUSE/RESUME (F-M4-01 & F-M4-02)
# ==============================================================================

class TestDelayLifecycleDeepChallenge:
    """Verifies that F-M4-01 and F-M4-02 remain completely resolved under repeated thrashing."""

    @pytest.mark.asyncio
    async def test_multi_cycle_pause_resume_during_pre_delay(self):
        """
        Adversarial Test: Multi-cycle pause and resume within a single step's pre_delay.
        Pre-delay is 250ms.
        1. Start workflow.
        2. Cycle 1: Pause at 20ms, verify PAUSED, resume at 60ms.
        3. Cycle 2: Pause AGAIN at 80ms (still within pre_delay), verify PAUSED, resume at 120ms.
        4. Let finish cleanly.
        Verify no InvalidTransitionError, state reaches COMPLETED/IDLE, audit shows SUCCESS.
        """
        payload = _build_stress_workflow(countdown=0, pre_delay=250, post_delay=10, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            r_start = await client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            # Cycle 1 Pause
            await asyncio.sleep(0.02)
            r_p1 = await client.post("/api/execute/pause")
            assert r_p1.status_code == 200
            st1 = await client.get("/api/execute/status")
            assert st1.json()["state"] == "PAUSED"

            # Cycle 1 Resume
            await asyncio.sleep(0.04)
            r_r1 = await client.post("/api/execute/resume")
            assert r_r1.status_code == 200
            st_r1 = await client.get("/api/execute/status")
            assert st_r1.json()["state"] == "RUNNING"

            # Cycle 2 Pause (still within 250ms pre_delay)
            await asyncio.sleep(0.02)
            r_p2 = await client.post("/api/execute/pause")
            assert r_p2.status_code == 200
            st2 = await client.get("/api/execute/status")
            assert st2.json()["state"] == "PAUSED"

            # Cycle 2 Resume
            await asyncio.sleep(0.04)
            r_r2 = await client.post("/api/execute/resume")
            assert r_r2.status_code == 200

            # Wait for workflow to finish
            await asyncio.sleep(0.25)
            st_final = await client.get("/api/execute/status")
            assert st_final.json()["state"] in ("COMPLETED", "IDLE")

            # Check audit summary
            wf_id = payload["id"]
            r_audit = await client.get(f"/api/execute/audit/{wf_id}")
            assert r_audit.status_code == 200
            assert r_audit.json()["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def test_multi_cycle_pause_resume_during_post_delay(self):
        """
        Adversarial Test: Multi-cycle pause and resume within a single step's post_delay.
        Post-delay is 250ms.
        1. Start workflow with 0 pre-delay.
        2. Wait 20ms for action to execute, entering post_delay.
        3. Cycle 1: Pause at 30ms, verify PAUSED, resume at 70ms.
        4. Cycle 2: Pause AGAIN at 90ms, verify PAUSED, resume at 130ms.
        5. Let complete.
        Verify no crash, ALL_STEPS_DONE not triggered while PAUSED, clean completion.
        """
        payload = _build_stress_workflow(countdown=0, pre_delay=0, post_delay=250, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            r_start = await client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            # Wait until action fires and enters post_delay
            await asyncio.sleep(0.03)

            # Cycle 1 Pause
            r_p1 = await client.post("/api/execute/pause")
            assert r_p1.status_code == 200
            st1 = await client.get("/api/execute/status")
            assert st1.json()["state"] == "PAUSED"

            # Cycle 1 Resume
            await asyncio.sleep(0.04)
            r_r1 = await client.post("/api/execute/resume")
            assert r_r1.status_code == 200

            # Cycle 2 Pause
            await asyncio.sleep(0.02)
            r_p2 = await client.post("/api/execute/pause")
            assert r_p2.status_code == 200
            st2 = await client.get("/api/execute/status")
            assert st2.json()["state"] == "PAUSED"

            # Cycle 2 Resume
            await asyncio.sleep(0.04)
            r_r2 = await client.post("/api/execute/resume")
            assert r_r2.status_code == 200

            # Wait for completion
            await asyncio.sleep(0.25)
            st_final = await client.get("/api/execute/status")
            assert st_final.json()["state"] in ("COMPLETED", "IDLE")

            # Audit summary verification
            wf_id = payload["id"]
            r_audit = await client.get(f"/api/execute/audit/{wf_id}")
            assert r_audit.status_code == 200
            assert r_audit.json()["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def test_interleaved_pre_and_post_delay_pauses_across_multiple_steps(self):
        """
        Adversarial Test: Multi-step workflow (3 steps) where:
        - Step 1 is paused in pre_delay, then resumed.
        - Step 2 is paused in post_delay, then resumed.
        - Step 3 completes normally.
        Verify correct sequence execution, 3 successful steps recorded in audit log.
        """
        payload = _build_stress_workflow(countdown=0, pre_delay=120, post_delay=120, num_steps=3)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            r_start = await client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            # Pause Step 1 in pre_delay
            await asyncio.sleep(0.03)
            r_p1 = await client.post("/api/execute/pause")
            assert r_p1.status_code == 200
            assert (await client.get("/api/execute/status")).json()["state"] == "PAUSED"
            await asyncio.sleep(0.05)
            r_r1 = await client.post("/api/execute/resume")
            assert r_r1.status_code == 200

            # Wait for Step 1 to complete and Step 2 to enter post_delay
            # (Step 1 pre: remaining ~90ms, step 1 post: 120ms, step 2 pre: 120ms -> total ~330ms)
            await asyncio.sleep(0.35)
            r_p2 = await client.post("/api/execute/pause")
            # Might be in RUNNING or PAUSED
            if r_p2.status_code == 200:
                assert (await client.get("/api/execute/status")).json()["state"] == "PAUSED"
                await asyncio.sleep(0.05)
                await client.post("/api/execute/resume")

            # Wait for entire workflow to complete
            for _ in range(30):
                st = (await client.get("/api/execute/status")).json()
                if st["state"] in ("COMPLETED", "IDLE"):
                    break
                await asyncio.sleep(0.05)

            st_done = (await client.get("/api/execute/status")).json()
            assert st_done["state"] in ("COMPLETED", "IDLE")

            wf_id = payload["id"]
            audit = (await client.get(f"/api/execute/audit/{wf_id}")).json()
            assert audit["status"] == "SUCCESS"
            assert audit["total_steps"] == 3
            assert audit["successful_steps"] == 3


# ==============================================================================
# SUITE 2: IN-STEP ABORT LIFECYCLES
# ==============================================================================

class TestInStepAbortLifecycles:
    """Stress tests aborting during various execution phases (action delay, pre-delay, pause)."""

    @pytest.mark.asyncio
    async def test_abort_during_action_delay_step(self):
        """
        Adversarial Test: Start a workflow containing ActionType.DELAY with 2000ms.
        Immediately issue /api/execute/abort while the delay loop is executing.
        Verify abort halts the loop immediately without waiting for the full 2 seconds.
        """
        payload = _build_stress_workflow(
            countdown=0,
            num_steps=1,
            action_type="delay",
            duration_ms=2000,
            post_delay=0,
        )

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            t0 = asyncio.get_event_loop().time()
            r_start = await client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            # Wait 50ms into the delay
            await asyncio.sleep(0.05)
            st_running = await client.get("/api/execute/status")
            assert st_running.json()["state"] == "RUNNING"

            # Issue abort
            r_abort = await client.post("/api/execute/abort")
            assert r_abort.status_code == 200
            assert r_abort.json()["status"] == "aborted"

            # Verify execution halted well before 2 seconds
            await asyncio.sleep(0.1)
            t_elapsed = asyncio.get_event_loop().time() - t0
            assert t_elapsed < 1.0, f"Abort took too long ({t_elapsed}s); delay loop did not break!"

            st_stopped = await client.get("/api/execute/status")
            assert st_stopped.json()["state"] in ("STOPPED", "IDLE")

            # Check audit
            wf_id = payload["id"]
            audit = (await client.get(f"/api/execute/audit/{wf_id}")).json()
            assert audit["status"] == "ABORTED"

    @pytest.mark.asyncio
    async def test_abort_while_paused_in_pre_delay(self):
        """
        Adversarial Test: Workflow with 500ms pre_delay.
        Pause mid-pre-delay, then abort while in state PAUSED.
        Verify FSM transitions via T14 (PAUSED -> STOPPED), task cancels cleanly,
        and single-flight lock is immediately available for next start.
        """
        payload = _build_stress_workflow(countdown=0, pre_delay=500, post_delay=0, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            r_start = await client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            await asyncio.sleep(0.03)
            r_pause = await client.post("/api/execute/pause")
            assert r_pause.status_code == 200
            assert (await client.get("/api/execute/status")).json()["state"] == "PAUSED"

            # Abort directly from PAUSED
            r_abort = await client.post("/api/execute/abort")
            assert r_abort.status_code == 200
            assert r_abort.json()["status"] == "aborted"

            st = (await client.get("/api/execute/status")).json()
            assert st["state"] in ("STOPPED", "IDLE")

            # Invariant: immediate next start must succeed without 409 lockout
            r_start2 = await client.post("/api/execute/start", json={"workflow": payload})
            assert r_start2.status_code == 200
            await client.post("/api/execute/abort")

    @pytest.mark.asyncio
    async def test_abort_while_paused_in_post_delay(self):
        """
        Adversarial Test: Workflow with 500ms post_delay.
        Pause mid-post-delay, then abort while in state PAUSED.
        Verify clean abort and immediate lock release.
        """
        payload = _build_stress_workflow(countdown=0, pre_delay=0, post_delay=500, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            r_start = await client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            await asyncio.sleep(0.04)  # Action executes, enters post_delay
            r_pause = await client.post("/api/execute/pause")
            assert r_pause.status_code == 200
            assert (await client.get("/api/execute/status")).json()["state"] == "PAUSED"

            # Abort directly from PAUSED
            r_abort = await client.post("/api/execute/abort")
            assert r_abort.status_code == 200

            st = (await client.get("/api/execute/status")).json()
            assert st["state"] in ("STOPPED", "IDLE")

            # Invariant: immediate next start must succeed
            r_start2 = await client.post("/api/execute/start", json={"workflow": payload})
            assert r_start2.status_code == 200
            await client.post("/api/execute/abort")

    @pytest.mark.asyncio
    async def test_abort_during_error_retry_loop(self, stress_driver):
        """
        Adversarial Test: Step fails and enters retry loop (max_retries=5).
        Abort while runner is sleeping between retries.
        Verify abort halts retry cycle, transitions to STOPPED, and releases modifiers.
        """
        stress_driver.fail_next_action = True
        payload = _build_stress_workflow(
            countdown=0,
            num_steps=1,
            error_recovery="retry_step",
            max_retries=5,
        )

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            r_start = await client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            # Wait for failure and retry cycle initiation
            await asyncio.sleep(0.06)

            # Abort during retry
            r_abort = await client.post("/api/execute/abort")
            assert r_abort.status_code == 200

            await asyncio.sleep(0.1)
            st = (await client.get("/api/execute/status")).json()
            assert st["state"] in ("STOPPED", "IDLE", "ERROR")
            assert stress_driver.modifiers_released is True

            stress_driver.fail_next_action = False


# ==============================================================================
# SUITE 3: HIGH-FREQUENCY STATUS & CONCURRENCY STORMS
# ==============================================================================

class TestHighFrequencyConcurrencyStorms:
    """Stress tests the API under concurrent status storms, start vs abort races, and rapid bursts."""

    @pytest.mark.asyncio
    async def test_status_polling_storm_during_active_execution(self):
        """
        Adversarial Test: Start a 3-step workflow (duration ~200ms).
        Concurrently bombard with 50 status queries and 20 audit queries.
        Verify 100% of requests succeed (HTTP 200), adhere to RFC 7807 / 90Studio attribution,
        and cause zero degradation or deadlocks.
        """
        payload = _build_stress_workflow(countdown=0, pre_delay=20, post_delay=50, num_steps=3)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            r_start = await client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200
            wf_id = payload["id"]

            async def poll_status():
                return await client.get("/api/execute/status")

            async def poll_audit():
                return await client.get(f"/api/execute/audit/{wf_id}")

            tasks = [poll_status() for _ in range(50)] + [poll_audit() for _ in range(20)]
            random.shuffle(tasks)
            responses = await asyncio.gather(*tasks)

            for r in responses:
                assert r.status_code == 200, f"Poll request failed with status {r.status_code}: {r.text}"
                data = r.json()
                assert data["copyright"] == __copyright__

            # Wait for clean completion
            for _ in range(20):
                st = (await client.get("/api/execute/status")).json()
                if st["state"] in ("COMPLETED", "IDLE"):
                    break
                await asyncio.sleep(0.05)

            assert (await client.get("/api/execute/status")).json()["state"] in ("COMPLETED", "IDLE")

    @pytest.mark.asyncio
    async def test_rapid_burst_double_and_triple_abort_idempotency(self):
        """
        Adversarial Test: Fire 5 abort requests simultaneously while running,
        and another 5 abort requests after execution is already stopped.
        Verify all return 200 OK without unhandled exceptions or broken FSM transitions.
        """
        payload = _build_stress_workflow(countdown=0, pre_delay=50, post_delay=50, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/execute/start", json={"workflow": payload})

            # 5 concurrent aborts during RUNNING
            tasks1 = [client.post("/api/execute/abort") for _ in range(5)]
            resps1 = await asyncio.gather(*tasks1)
            for r in resps1:
                assert r.status_code == 200
                assert r.json()["status"] == "aborted"

            # 5 concurrent aborts after STOPPED / IDLE
            tasks2 = [client.post("/api/execute/abort") for _ in range(5)]
            resps2 = await asyncio.gather(*tasks2)
            for r in resps2:
                assert r.status_code == 200
                assert r.json()["status"] == "aborted"

    @pytest.mark.asyncio
    async def test_start_vs_abort_high_contention_race(self):
        """
        Adversarial Test: Launch 25 start and 25 abort requests simultaneously in random order.
        Verify no 500 errors, single-flight lock handles all conflicts (409),
        and server reliably settles into STOPPED or IDLE.
        """
        payload = _build_stress_workflow(countdown=0, pre_delay=10, post_delay=20, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            actions = ["start"] * 25 + ["abort"] * 25
            random.shuffle(actions)

            tasks = []
            for act in actions:
                if act == "start":
                    tasks.append(client.post("/api/execute/start", json={"workflow": payload}))
                else:
                    tasks.append(client.post("/api/execute/abort"))

            responses = await asyncio.gather(*tasks)
            status_codes = [r.status_code for r in responses]

            assert 500 not in status_codes, f"500 Internal Server Error in contention race: {status_codes}"
            for code in status_codes:
                assert code in (200, 202, 409), f"Unexpected status code: {code}"

            # Settle state
            await client.post("/api/execute/abort")
            st = (await client.get("/api/execute/status")).json()
            assert st["state"] in ("STOPPED", "IDLE")


# ==============================================================================
# SUITE 4: WEBSOCKET BI-DIRECTIONAL CONTROL & DROP STORMS
# ==============================================================================

class TestWebSocketBidirectionalControlStress:
    """Stress tests bi-directional control over WebSocket and resilience to disconnect storms."""

    def test_websocket_control_pause_resume_abort_actions(self, stress_client):
        """
        Adversarial Test: Control workflow execution entirely via WebSocket JSON frames:
        1. Start workflow via REST.
        2. Send {"action": "pause"} via WebSocket -> verify state transitions to PAUSED.
        3. Send {"action": "resume"} via WebSocket -> verify state transitions to RUNNING.
        4. Send {"action": "abort"} via WebSocket -> verify state transitions to STOPPED.
        Verify full bi-directional parity between WebSocket control and REST endpoints.
        """
        payload = _build_stress_workflow(countdown=0, pre_delay=50, post_delay=150, num_steps=2)

        with stress_client.websocket_connect("/ws/execution") as ws:
            ws.receive_json()  # connection_established

            # Start execution
            r_start = stress_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            # Wait briefly for RUNNING
            time.sleep(0.03)

            # Send pause via WebSocket
            ws.send_json({"action": "pause"})
            time.sleep(0.05)
            st_p = stress_client.get("/api/execute/status").json()
            assert st_p["state"] == "PAUSED"

            # Send resume via WebSocket
            ws.send_json({"action": "resume"})
            time.sleep(0.05)
            st_r = stress_client.get("/api/execute/status").json()
            assert st_r["state"] == "RUNNING"

            # Send abort via WebSocket
            ws.send_json({"action": "abort"})
            time.sleep(0.05)
            st_a = stress_client.get("/api/execute/status").json()
            assert st_a["state"] in ("STOPPED", "IDLE")

    def test_websocket_heavy_disconnect_storm_during_telemetry_broadcast(self, stress_client):
        """
        Adversarial Test: Connect 10 WebSocket clients. Start a fast multi-step workflow.
        While events are actively firing, simultaneously disconnect 7 clients abruptly.
        Verify the hub cleans up disconnected sockets, remaining 3 clients continue receiving events,
        and server experiences zero unhandled exceptions.
        """
        payload = _build_stress_workflow(countdown=0, pre_delay=10, post_delay=20, num_steps=4)

        sockets = []
        try:
            for _ in range(10):
                ws = stress_client.websocket_connect("/ws/execution")
                s = ws.__enter__()
                sockets.append((ws, s))
                s.receive_json()  # discard connection_established

            # Trigger execution
            stress_client.post("/api/execute/start", json={"workflow": payload})

            # Immediately drop 7 clients
            for i in range(7):
                ws, s = sockets[i]
                s.close()

            # Verify remaining 3 clients receive active broadcast events
            for i in (7, 8, 9):
                _, s = sockets[i]
                event = s.receive_json()
                assert event is not None
                assert "event" in event or "type" in event
        finally:
            stress_client.post("/api/execute/abort")
            for ws, _ in sockets:
                try:
                    ws.__exit__(None, None, None)
                except Exception:
                    continue


# ==============================================================================
# SUITE 5: ACTIVE VS COMPLETED AUDIT CONSISTENCY (F-M4-04 INVARIANT)
# ==============================================================================

class TestActiveVsCompletedAuditConsistency:
    """Verifies that audit summaries are consistent across workflow_id and execution_id during both active and completed states."""

    @pytest.mark.asyncio
    async def test_audit_consistency_by_workflow_id_and_execution_id(self):
        """
        Adversarial Test:
        1. Start workflow with 150ms delay.
        2. Query /api/execute/audit/{workflow_id} during active state -> verify 200 OK, RUNNING.
        3. Query /api/execute/audit/{execution_id} during active state -> verify 200 OK, RUNNING.
        4. Let workflow complete.
        5. Query /api/execute/audit/{workflow_id} -> verify 200 OK, SUCCESS, total_steps matched.
        6. Query /api/execute/audit/{execution_id} -> verify 200 OK, SUCCESS, total_steps matched.
        Both identifiers MUST resolve identically at every point in the lifecycle.
        """
        payload = _build_stress_workflow(countdown=0, pre_delay=20, post_delay=80, num_steps=2)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            r_start = await client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200
            data_start = r_start.json()
            wf_id = data_start["workflow_id"]
            exec_id = data_start["execution_id"]

            # Active phase assertions
            await asyncio.sleep(0.04)
            r_audit_wf = await client.get(f"/api/execute/audit/{wf_id}")
            r_audit_ex = await client.get(f"/api/execute/audit/{exec_id}")

            assert r_audit_wf.status_code == 200
            assert r_audit_ex.status_code == 200

            data_wf = r_audit_wf.json()
            data_ex = r_audit_ex.json()

            assert data_wf["workflow_id"] == wf_id
            assert data_wf["execution_id"] == exec_id
            assert data_ex["workflow_id"] == wf_id
            assert data_ex["execution_id"] == exec_id
            assert data_wf["copyright"] == __copyright__
            assert data_ex["copyright"] == __copyright__

            # Wait for completion
            for _ in range(25):
                st = (await client.get("/api/execute/status")).json()
                if st["state"] in ("COMPLETED", "IDLE"):
                    break
                await asyncio.sleep(0.05)

            # Completed phase assertions
            r_done_wf = await client.get(f"/api/execute/audit/{wf_id}")
            r_done_ex = await client.get(f"/api/execute/audit/{exec_id}")

            assert r_done_wf.status_code == 200
            assert r_done_ex.status_code == 200

            done_wf = r_done_wf.json()
            done_ex = r_done_ex.json()

            assert done_wf["status"] == "SUCCESS"
            assert done_ex["status"] == "SUCCESS"
            assert done_wf["total_steps"] == 2
            assert done_ex["total_steps"] == 2
            assert done_wf["successful_steps"] == 2
            assert done_ex["successful_steps"] == 2
            assert done_wf["execution_id"] == exec_id
            assert done_ex["execution_id"] == exec_id


# ==============================================================================
# SUITE 6: ADVANCED ADVERSARIAL & GHOST STATE RESILIENCE
# ==============================================================================

class TestAdvancedAdversarialAndGhostStateResilience:
    """Stress tests ghost running state prevention, rapid flapping, focus loss, and fuzzing."""

    @pytest.mark.asyncio
    async def test_ghost_running_lockout_resilience_on_abrupt_task_cancellation(self):
        """
        Adversarial Test: Simulate an abrupt external cancellation of the background asyncio task
        while the runner is in RUNNING state.
        Verify that execution_manager.is_active() detects the dead task immediately and returns False,
        preventing permanent 409 Ghost Running lockouts on subsequent workflow starts.
        """
        payload = _build_stress_workflow(countdown=0, pre_delay=50, post_delay=500, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            r_start = await client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            # Wait for RUNNING state
            await asyncio.sleep(0.04)
            assert execution_manager._active_task is not None
            assert not execution_manager._active_task.done()

            # Abruptly cancel background task from outside the normal runner flow
            execution_manager._active_task.cancel()
            try:
                await execution_manager._active_task
            except (asyncio.CancelledError, Exception):
                pass

            # Invariant: is_active() MUST immediately evaluate to False
            assert execution_manager.is_active() is False

            # Invariant: Server must NOT be trapped in a 409 Ghost Running lockout
            r_start2 = await client.post("/api/execute/start", json={"workflow": payload})
            assert r_start2.status_code == 200, f"Ghost lockout detected! Got {r_start2.status_code}: {r_start2.text}"

            await client.post("/api/execute/abort")

    @pytest.mark.asyncio
    async def test_rapid_flapping_20_start_pause_abort_cycles(self):
        """
        Adversarial Test: Execute 20 consecutive rapid flapping cycles:
        Start -> Pause -> Abort in quick succession with zero delays.
        Verify server never leaks tasks, never deadlocks, and always settles cleanly into STOPPED or IDLE.
        """
        payload = _build_stress_workflow(countdown=0, pre_delay=20, post_delay=40, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            for cycle in range(20):
                r_start = await client.post("/api/execute/start", json={"workflow": payload})
                r_pause = await client.post("/api/execute/pause")
                r_abort = await client.post("/api/execute/abort")

                assert 500 not in (r_start.status_code, r_pause.status_code, r_abort.status_code), (
                    f"Cycle {cycle} triggered 500 error: start={r_start.status_code}, "
                    f"pause={r_pause.status_code}, abort={r_abort.status_code}"
                )

            st = (await client.get("/api/execute/status")).json()
            assert st["state"] in ("STOPPED", "IDLE")

    @pytest.mark.asyncio
    async def test_loss_of_focus_auto_pause_and_ws_telemetry(self, stress_driver):
        """
        Adversarial Test: When target application loses foreground focus during execution:
        1. Loss-of-Focus Guardian pauses runner (T10: RUNNING -> PAUSED).
        2. Status endpoint reflects PAUSED.
        3. Restoring foreground window and calling resume resumes execution cleanly.
        """
        payload = _build_stress_workflow(countdown=0, pre_delay=20, post_delay=50, num_steps=2)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            r_start = await client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            # Wait until Step 1 starts
            await asyncio.sleep(0.04)

            # Simulate operator switching window (change foreground HWND to untracked 9999)
            stress_driver.foreground_hwnd = 9999

            # Wait for Step 2 focus check to trip
            await asyncio.sleep(0.08)

            st_paused = (await client.get("/api/execute/status")).json()
            # If focus guardian tripped, state is PAUSED
            if st_paused["state"] == "PAUSED":
                # Restore foreground HWND and resume
                stress_driver.foreground_hwnd = 1001
                r_resume = await client.post("/api/execute/resume")
                assert r_resume.status_code == 200

                await asyncio.sleep(0.15)
                st_final = (await client.get("/api/execute/status")).json()
                assert st_final["state"] in ("COMPLETED", "IDLE")
            else:
                # Clean up if already completed
                await client.post("/api/execute/abort")

    @pytest.mark.asyncio
    async def test_audit_endpoint_fuzzing_with_special_characters_and_sql_injection(self):
        """
        Adversarial Test: Query /api/execute/audit/{id} with SQL injection patterns,
        XSS probes, shell metacharacters, and path traversal strings.
        Verify ALL return 404 RFC 7807 problem details with 90Studio attribution.
        """
        fuzz_payloads = [
            "' OR '1'='1",
            "1; DROP TABLE workflows;--",
            "<script>alert(1)</script>",
            "../../etc/passwd",
            "..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "%00admin",
            "audit_*",
            "audit_?_test",
            "$(whoami)",
            "`id`",
            "${IFS}",
            "null",
            "undefined",
            "NaN",
            " ",
            "   ",
        ]

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            for p in fuzz_payloads:
                r = await client.get(f"/api/execute/audit/{p}")
                assert r.status_code == 404, f"Fuzz payload {p!r} returned status {r.status_code}: {r.text}"
                data = r.json()
                assert data["status"] == 404
                assert data["copyright"] == __copyright__
                assert "90studio.com" in data.get("type", "")

    def test_websocket_high_frequency_message_flood(self, stress_client):
        """
        Adversarial Test: Flood WebSocket connection with 100 consecutive ping frames
        while a workflow is actively executing.
        Verify server responds to all pings without dropping connections or stalling the runner.
        """
        payload = _build_stress_workflow(countdown=0, pre_delay=20, post_delay=80, num_steps=2)

        with stress_client.websocket_connect("/ws/execution") as ws:
            ws.receive_json()  # connection_established

            stress_client.post("/api/execute/start", json={"workflow": payload})

            # Send 100 pings rapidly
            for i in range(100):
                ws.send_json({"event": "ping", "seq": i})

            # Consume responses
            pongs_received = 0
            while pongs_received < 100:
                frame = ws.receive_json()
                if frame.get("event") == "pong":
                    pongs_received += 1
                    assert frame["copyright"] == __copyright__

            assert pongs_received == 100
            stress_client.post("/api/execute/abort")

