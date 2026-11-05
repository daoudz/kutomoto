"""
tests.test_m4_it3_adversarial_challenge
Milestone 4 Iteration 3 Adversarial Challenge Suite:
Empirically verifies:
1. F-M4-03: Glob and traversal attack vectors against GET /api/execute/audit/{id}.
   Wildcards ('*', '?', '[]', '{}'), path traversals ('../', '..%2F', '..\\'), null bytes,
   and shell/regex metacharacters.
   Verifies all return 404 Problem Details stamped with 90Studio copyright without leaking stored files.
2. F-M4-04: Query symmetry between workflow_id and execution_id during active execution
   and on disk fallback after cache eviction.

Copyrights reserved to 90Studio
"""

import asyncio
import json
from pathlib import Path
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
from kutomoto.server.app import BASE_DIR, app, execution_manager, get_driver  # noqa: E402


class MockAdversarialDriver:
    """Mock Win32 Driver for adversarial challenge execution."""

    def __init__(self) -> None:
        self.dpi_set = False
        self.cursor_pos = (500, 400)
        self.foreground_hwnd = 1001
        self.clicks: List[Tuple[int, int, str, int]] = []
        self.typed_text: List[str] = []
        self.pressed_keys: List[Tuple[str, int]] = []
        self.cleared_fields: List[str] = []
        self.scrolls: List[Tuple[int, int]] = []
        self.modifiers_released: bool = False
        self.held_keys: List[Any] = []
        self.released_keys: List[Any] = []
        self.mouse_buttons_down: List[str] = []
        self.mouse_buttons_up: List[str] = []
        self.mock_windows = [
            {
                "hwnd": 1001,
                "title": "Adversarial Target - Microsoft Edge",
                "class_name": "Chrome_WidgetWin_1",
                "pid": 2048,
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
    return MockAdversarialDriver()


@pytest.fixture(autouse=True)
def setup_teardown(mock_driver, monkeypatch):
    """Ensure clean execution state before and after each test."""
    app.dependency_overrides[get_driver] = lambda: mock_driver
    monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
    yield
    if execution_manager.is_active():
        asyncio.run(execution_manager.abort())
    execution_manager._audit_summaries.clear()
    execution_manager._last_audit_summary = None
    app.dependency_overrides.clear()


@pytest.fixture
def client(mock_driver):
    with TestClient(app) as c:
        yield c


def _sample_workflow_payload(wf_id: str = "wf_adversarial_test", step_delay_ms: int = 1000) -> Dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "id": wf_id,
        "name": "Adversarial Challenge Workflow",
        "description": "Enterprise automated KYC workflow",
        "author": "90Studio QA Challenger",
        "copyright": "Copyrights reserved to 90Studio",
        "source_mode": "manual_step_flow",
        "target_application": {
            "type": "web_browser",
            "window_title_pattern": "Adversarial Target",
            "process_name": "msedge.exe",
            "match_mode": "contains",
        },
        "execution_settings": {
            "countdown_seconds": 0,
            "default_step_delay_ms": 10,
            "typing_speed_ms": 5,
            "stop_on_error": True,
            "error_recovery_policy": "abort",
            "max_step_retries": 1,
            "failsafe_corner_enabled": True,
            "abort_hotkey": "Escape",
        },
        "variables": [],
        "steps": [
            {
                "step_id": str(uuid.uuid4()),
                "sequence_index": 1,
                "label": "Focus Target Window",
                "action_type": "focus_window",
                "enabled": True,
                "pre_delay_ms": step_delay_ms,
                "post_delay_ms": step_delay_ms,
                "parameters": {
                    "window_title_pattern": "Adversarial Target",
                    "match_mode": "contains",
                },
            },
            {
                "step_id": str(uuid.uuid4()),
                "sequence_index": 2,
                "label": "Send Key",
                "action_type": "key_press",
                "enabled": True,
                "pre_delay_ms": step_delay_ms,
                "post_delay_ms": step_delay_ms,
                "parameters": {
                    "key_name": "Tab",
                    "repeat_count": 1,
                },
            },
        ],
    }


# ==============================================================================
# SUITE 1: F-M4-03 ADVERSARIAL ATTACK VECTORS (GLOB, TRAVERSAL, NULL, METACHARD)
# ==============================================================================

class TestFM403AdversarialAttackVectors:
    """
    Adversarially challenges GET /api/execute/audit/{id} against:
    - Glob wildcards ('*', '?', '[]', '{}')
    - Path traversals ('../', '..%2F', '..\\', '..%5C', etc.)
    - Null bytes ('%00', '\\x00')
    - Shell / regex / command metacharacters (';', '|', '&', '$', '`', '<', '>', '^', '+', etc.)
    - Asserts HTTP 404 Problem Details with 90Studio copyright
    - Asserts ZERO disclosure of stored confidential files.
    """

    @pytest.fixture(autouse=True)
    def setup_confidential_files(self):
        """Place high-sensitivity audit records in audit directory."""
        audit_dir = BASE_DIR / "data" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)

        self.confidential_wf_name = "TOP_SECRET_ENTERPRISE_SWIFT_TRANSFER_CONFIDENTIAL_90STUDIO"
        self.confidential_wf_id = f"secret_vault_{uuid.uuid4().hex[:12]}"
        self.confidential_exec_id = f"exec_classified_{uuid.uuid4().hex[:12]}"
        self.secret_token = "CONFIDENTIAL_API_BEARER_TOKEN_90STUDIO_998877"

        self.confidential_file = audit_dir / f"audit_{self.confidential_wf_id}_{self.confidential_exec_id}_20261105.json"
        self.confidential_file.write_text(
            json.dumps({
                "workflow_id": self.confidential_wf_id,
                "execution_id": self.confidential_exec_id,
                "workflow_name": self.confidential_wf_name,
                "secret_token": self.secret_token,
                "timestamp_utc": "2026-11-05T00:00:00Z",
                "copyright": __copyright__,
                "execution_summary": {
                    "total_steps": 5,
                    "successful_steps": 5,
                    "failed_steps": 0,
                    "retried_steps": 0,
                    "duration_seconds": 3.14,
                    "final_status": "SUCCESS",
                },
            }),
            encoding="utf-8",
        )

        yield

        if self.confidential_file.exists():
            self.confidential_file.unlink()

    def _assert_secure_404_response(self, resp, vector_desc: str, query_contained_wf_id: bool = False):
        """Verify RFC 7807 problem details, 90Studio attribution, and zero confidential data leakage."""
        assert resp.status_code == 404, (
            f"Vector '{vector_desc}' failed security check: expected HTTP 404, got {resp.status_code}."
        )
        try:
            data = resp.json()
        except Exception as ex:
            pytest.fail(f"Vector '{vector_desc}' did not return valid JSON Problem Details: {ex} (body: {resp.text})")

        # RFC 7807 and 90Studio copyright requirements
        assert data.get("copyright") == "Copyrights reserved to 90Studio", (
            f"Vector '{vector_desc}' missing 90Studio copyright attribution in Problem Details."
        )
        assert data.get("status") == 404
        assert "type" in data
        assert "404" in str(data.get("type", ""))

        # Confidential data non-disclosure assertion
        resp_content = resp.text
        assert self.confidential_wf_name not in resp_content, f"Vector '{vector_desc}' LEAKED workflow name!"
        assert self.confidential_exec_id not in resp_content, f"Vector '{vector_desc}' LEAKED execution_id!"
        assert self.secret_token not in resp_content, f"Vector '{vector_desc}' LEAKED secret token!"
        if not query_contained_wf_id:
            assert self.confidential_wf_id not in resp_content, f"Vector '{vector_desc}' LEAKED workflow_id!"
        assert self.confidential_exec_id not in resp_content, f"Vector '{vector_desc}' LEAKED execution_id!"
        assert self.secret_token not in resp_content, f"Vector '{vector_desc}' LEAKED secret token!"

    def test_wildcard_vectors_rejected(self, client):
        """Test glob wildcards: *, **, *.*, *.json, *secret*, ?, ???, [], [a-z], {}, {a,b}."""
        vectors = [
            "*",
            "**",
            "*.*",
            "*.json",
            "*secret*",
            "secret*",
            "*vault*",
            "?",
            "%3F",
            "???",
            "%3F%3F%3F",
            "[]",
            "[a-z]",
            "%5Ba-z%5D",
            "[0-9]",
            "%5B0-9%5D",
            "[*]",
            "[!a]",
            "{}",
            "{a,b}",
            "%7Ba,b%7D",
            "{1..5}",
            "%7B1..5%7D",
            f"*{self.confidential_wf_id[:6]}*",
            f"[{self.confidential_wf_id[:4]}]",
        ]

        for vec in vectors:
            resp = client.get(f"/api/execute/audit/{vec}")
            self._assert_secure_404_response(
                resp,
                f"Wildcard vector: {vec}",
                query_contained_wf_id=(self.confidential_wf_id in str(vec)),
            )

    def test_path_traversal_vectors_rejected(self, client):
        """Test path traversal vectors: ../, ..%2F, ..\\, ..%5C, nested traversals, win.ini, passwd."""
        vectors = [
            "..",
            "../",
            "../..",
            "..%2F",
            "..%2f",
            "..%2F..%2F",
            "..\\",
            "..%5C",
            "..%5c",
            "..%5C..%5C",
            "../../../../etc/passwd",
            "..%2F..%2F..%2F..%2Fetc%2Fpasswd",
            r"..\..\..\..\windows\win.ini",
            "..%5C..%5C..%5C..%5Cwindows%5Cwin.ini",
            "..%252F..%252F",
            "....//....//",
            ".%2e/",
            "../data/audit",
            f"..%2Fdata%2Faudit%2Faudit_{self.confidential_wf_id}.json",
            r"..\data\audit",
            f"..%5Cdata%5Caudit%5Caudit_{self.confidential_wf_id}.json",
            "subdir/../test",
            "subdir%2F..%2Ftest",
        ]

        for vec in vectors:
            resp = client.get(f"/api/execute/audit/{vec}")
            self._assert_secure_404_response(
                resp,
                f"Traversal vector: {vec}",
                query_contained_wf_id=(self.confidential_wf_id in str(vec)),
            )

    def test_null_byte_vectors_rejected(self, client):
        """Test null byte injection: %00, suffix termination, mid-string null bytes."""
        vectors = [
            "%00",
            f"{self.confidential_wf_id}%00",
            f"{self.confidential_wf_id}%00.json",
            "audit%00",
            "valid_id%00_suffix",
            "%00admin",
        ]

        for vec in vectors:
            resp = client.get(f"/api/execute/audit/{vec}")
            self._assert_secure_404_response(
                resp,
                f"Null byte vector: {vec}",
                query_contained_wf_id=(self.confidential_wf_id in str(vec)),
            )

    def test_shell_and_regex_metacharacters_rejected(self, client):
        """Test shell, regex, SQL, and command injection metacharacters."""
        vectors = [
            ";",
            "%3B",
            "wf;ls",
            "wf%3Bls",
            "|",
            "%7C",
            "wf|cat",
            "wf%7Ccat",
            "&",
            "%26",
            "wf&dir",
            "wf%26dir",
            "$",
            "%24",
            "$HOME",
            "%24HOME",
            "$(whoami)",
            "%24%28whoami%29",
            "`",
            "%60",
            "`id`",
            "%60id%60",
            "(",
            ")",
            "%28",
            "%29",
            ">",
            "<",
            "%3E",
            "%3C",
            "^",
            "%5E",
            "^audit.*",
            "%5Eaudit.*",
            "+",
            "%2B",
            "wf+1",
            "wf%2B1",
            "\\",
            "%5C",
            ".",
            "%2E",
            "audit.json",
            "wf.json",
            f"{self.confidential_wf_id}.json",
            "..;id",
            '"',
            "'",
            "%22",
            "%27",
            "!",
            "%21",
            "~",
            "%7E",
            "@",
            "%40",
            "#",
            "%23",
            "%",
            "%25",
            "%0A",
            "%0D",
            "%09",
            "%20",
            "wf 1",
            "wf%201",
        ]

        for vec in vectors:
            resp = client.get(f"/api/execute/audit/{vec}")
            self._assert_secure_404_response(
                resp,
                f"Metacharacter vector: {vec}",
                query_contained_wf_id=(self.confidential_wf_id in str(vec)),
            )

    def test_advanced_fuzzing_and_unicode_homoglyphs(self, client):
        """
        Adversarial test with unicode homoglyphs, zero-width chars, and overlong encodings:
        - Fullwidth solidus (%EF%BC%8F)
        - Fullwidth asterisk (%EF%BC%8A)
        - Fullwidth question mark (%EF%BC%9F)
        - Zero-width space (%E2%80%8B)
        - Non-breaking space (%C2%A0)
        - Right-to-left override (%E2%80%AE)
        - Double URL encoding (%252e%252e%252f)
        - Windows device names (CON, PRN, AUX, NUL, COM1, LPT1)
        - Windows drive letters (C:, C%3A, C%3A%2F)
        - Buffer overflow length string ('A' * 4096)
        """
        advanced_vectors = [
            "%252e%252e%252f",
            "%EF%BC%8F",
            "%EF%BC%8A",
            "%EF%BC%9F",
            "%E2%80%8B",
            "%C2%A0",
            "%E2%80%AE",
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "LPT1",
            "C:",
            "C%3A",
            "C:%5C",
            "C%3A%5C",
            "C%3A%2F",
            "A" * 2048,
        ]

        for vec in advanced_vectors:
            resp = client.get(f"/api/execute/audit/{vec}")
            self._assert_secure_404_response(
                resp,
                f"Advanced/Unicode vector: {vec[:20]}...",
                query_contained_wf_id=False,
            )



# ==============================================================================
# SUITE 2: F-M4-04 QUERY SYMMETRY (ACTIVE EXECUTION & DISK FALLBACK)
# ==============================================================================

class TestFM404QuerySymmetry:
    """
    Adversarially tests query symmetry between workflow_id and execution_id:
    1. During active RUNNING and PAUSED execution.
    2. On disk fallback after cache eviction for single execution.
    3. On disk fallback after cache eviction for multiple executions (temporal precedence).
    4. Negative boundary testing (substrings, prefixes, non-existent IDs).
    """

    def test_active_execution_symmetry_running_and_paused(self, client):
        """
        Verify that during active RUNNING and PAUSED states:
        - Query by workflow_id returns HTTP 200 with active status.
        - Query by execution_id returns HTTP 200 with active status.
        - Payloads are completely symmetric and stamped with 90Studio copyright.
        """
        wf_id = f"wf_active_sym_{uuid.uuid4().hex[:8]}"
        payload = _sample_workflow_payload(wf_id=wf_id, step_delay_ms=1000)

        # 1. Start execution
        start_resp = client.post("/api/execute/start", json={"workflow": payload})
        assert start_resp.status_code in (200, 202)
        exec_id = start_resp.json()["execution_id"]
        assert exec_id is not None

        try:
            # Wait for runner to enter active RUNNING state
            for _ in range(25):
                st = client.get("/api/execute/status").json()
                if st.get("state") == "RUNNING":
                    break
                time.sleep(0.02)

            # --- RUNNING STATE SYMMETRY ---
            resp_by_wf = client.get(f"/api/execute/audit/{wf_id}")
            resp_by_ex = client.get(f"/api/execute/audit/{exec_id}")

            assert resp_by_wf.status_code == 200
            assert resp_by_ex.status_code == 200

            data_wf = resp_by_wf.json()
            data_ex = resp_by_ex.json()

            assert data_wf["workflow_id"] == wf_id
            assert data_wf["execution_id"] == exec_id
            assert data_ex["workflow_id"] == wf_id
            assert data_ex["execution_id"] == exec_id
            assert data_wf["status"] == "RUNNING"
            assert data_ex["status"] == "RUNNING"
            assert data_wf["total_steps"] == len(payload["steps"])
            assert data_ex["total_steps"] == len(payload["steps"])
            assert data_wf["copyright"] == "Copyrights reserved to 90Studio"
            assert data_ex["copyright"] == "Copyrights reserved to 90Studio"

            # --- PAUSED STATE SYMMETRY ---
            pause_resp = client.post("/api/execute/pause")
            assert pause_resp.status_code == 200

            time.sleep(0.05)
            paused_by_wf = client.get(f"/api/execute/audit/{wf_id}").json()
            paused_by_ex = client.get(f"/api/execute/audit/{exec_id}").json()

            assert paused_by_wf["status"] == "PAUSED"
            assert paused_by_ex["status"] == "PAUSED"
            assert paused_by_wf["workflow_id"] == wf_id
            assert paused_by_ex["workflow_id"] == wf_id
            assert paused_by_wf["execution_id"] == exec_id
            assert paused_by_ex["execution_id"] == exec_id

            # Resume
            resume_resp = client.post("/api/execute/resume")
            assert resume_resp.status_code == 200

        finally:
            client.post("/api/execute/abort")

    def test_disk_fallback_symmetry_single_execution_after_cache_eviction(self, client):
        """
        Verify that on disk fallback after cache eviction:
        - Query by workflow_id returns HTTP 200.
        - Query by execution_id returns HTTP 200.
        - The returned objects are 100% field-for-field identical.
        """
        audit_dir = BASE_DIR / "data" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)

        wf_id = f"wf_disk_single_{uuid.uuid4().hex[:8]}"
        exec_id = f"exec_disk_single_{uuid.uuid4().hex[:8]}"
        disk_file = audit_dir / f"audit_{wf_id}_{exec_id}_20261105_150000.json"

        stored_record = {
            "workflow_id": wf_id,
            "execution_id": exec_id,
            "workflow_name": "Single Disk Fallback Workflow",
            "timestamp_utc": "2026-11-05T15:00:00Z",
            "copyright": "Copyrights reserved to 90Studio",
            "execution_summary": {
                "total_steps": 4,
                "successful_steps": 4,
                "failed_steps": 0,
                "retried_steps": 0,
                "duration_seconds": 2.45,
                "final_status": "SUCCESS",
            },
        }
        disk_file.write_text(json.dumps(stored_record), encoding="utf-8")

        try:
            # Force cache eviction
            execution_manager._audit_summaries.clear()
            execution_manager._last_audit_summary = None

            resp_wf = client.get(f"/api/execute/audit/{wf_id}")
            resp_ex = client.get(f"/api/execute/audit/{exec_id}")

            assert resp_wf.status_code == 200
            assert resp_ex.status_code == 200

            data_wf = resp_wf.json()
            data_ex = resp_ex.json()

            # Field-for-field exact equality check
            assert data_wf == data_ex, f"Query asymmetry detected:\nBy wf: {data_wf}\nBy ex: {data_ex}"

            assert data_wf["workflow_id"] == wf_id
            assert data_wf["execution_id"] == exec_id
            assert data_wf["workflow_name"] == "Single Disk Fallback Workflow"
            assert data_wf["status"] == "SUCCESS"
            assert data_wf["total_steps"] == 4
            assert data_wf["successful_steps"] == 4
            assert data_wf["failed_steps"] == 0
            assert data_wf["retried_steps"] == 0
            assert data_wf["duration_seconds"] == 2.45
            assert data_wf["timestamp_utc"] == "2026-11-05T15:00:00Z"
            assert data_wf["copyright"] == "Copyrights reserved to 90Studio"

        finally:
            if disk_file.exists():
                disk_file.unlink()

    def test_disk_fallback_multiple_executions_temporal_symmetry(self, client):
        """
        Verify behavior when multiple executions exist on disk for the same workflow:
        - Query by workflow_id returns the LATEST execution (temporal sort order).
        - Query by the latest execution_id returns that exact same latest execution.
        - Query by older execution_ids returns their respective historical executions.
        """
        audit_dir = BASE_DIR / "data" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)

        wf_id = f"wf_temporal_sym_{uuid.uuid4().hex[:8]}"
        exec_1 = f"exec_run1_{uuid.uuid4().hex[:8]}"
        exec_2 = f"exec_run2_{uuid.uuid4().hex[:8]}"
        exec_3 = f"exec_run3_{uuid.uuid4().hex[:8]}"

        file_1 = audit_dir / f"audit_{wf_id}_{exec_1}_20261105_080000.json"
        file_2 = audit_dir / f"audit_{wf_id}_{exec_2}_20261105_100000.json"
        file_3 = audit_dir / f"audit_{wf_id}_{exec_3}_20261105_120000.json"

        record_1 = {
            "workflow_id": wf_id,
            "execution_id": exec_1,
            "workflow_name": "Temporal Test",
            "timestamp_utc": "2026-11-05T08:00:00Z",
            "copyright": "Copyrights reserved to 90Studio",
            "execution_summary": {
                "total_steps": 2,
                "successful_steps": 2,
                "failed_steps": 0,
                "retried_steps": 0,
                "duration_seconds": 1.0,
                "final_status": "SUCCESS",
            },
        }
        record_2 = {
            "workflow_id": wf_id,
            "execution_id": exec_2,
            "workflow_name": "Temporal Test",
            "timestamp_utc": "2026-11-05T10:00:00Z",
            "copyright": "Copyrights reserved to 90Studio",
            "execution_summary": {
                "total_steps": 3,
                "successful_steps": 1,
                "failed_steps": 1,
                "retried_steps": 1,
                "duration_seconds": 2.5,
                "final_status": "FAILED",
            },
        }
        record_3 = {
            "workflow_id": wf_id,
            "execution_id": exec_3,
            "workflow_name": "Temporal Test",
            "timestamp_utc": "2026-11-05T12:00:00Z",
            "copyright": "Copyrights reserved to 90Studio",
            "execution_summary": {
                "total_steps": 5,
                "successful_steps": 5,
                "failed_steps": 0,
                "retried_steps": 0,
                "duration_seconds": 4.2,
                "final_status": "SUCCESS",
            },
        }

        file_1.write_text(json.dumps(record_1), encoding="utf-8")
        file_2.write_text(json.dumps(record_2), encoding="utf-8")
        file_3.write_text(json.dumps(record_3), encoding="utf-8")

        try:
            # Force cache eviction
            execution_manager._audit_summaries.clear()
            execution_manager._last_audit_summary = None

            # 1. Query by workflow_id: must return latest (Run 3)
            resp_wf = client.get(f"/api/execute/audit/{wf_id}")
            assert resp_wf.status_code == 200
            data_wf = resp_wf.json()
            assert data_wf["execution_id"] == exec_3
            assert data_wf["total_steps"] == 5

            # 2. Query by latest execution_id: must return Run 3 identically
            resp_ex3 = client.get(f"/api/execute/audit/{exec_3}")
            assert resp_ex3.status_code == 200
            data_ex3 = resp_ex3.json()
            assert data_wf == data_ex3

            # 3. Query historical executions: must return respective records
            resp_ex1 = client.get(f"/api/execute/audit/{exec_1}")
            assert resp_ex1.status_code == 200
            data_ex1 = resp_ex1.json()
            assert data_ex1["execution_id"] == exec_1
            assert data_ex1["total_steps"] == 2
            assert data_ex1["status"] == "SUCCESS"

            resp_ex2 = client.get(f"/api/execute/audit/{exec_2}")
            assert resp_ex2.status_code == 200
            data_ex2 = resp_ex2.json()
            assert data_ex2["execution_id"] == exec_2
            assert data_ex2["total_steps"] == 3
            assert data_ex2["status"] == "FAILED"

        finally:
            for f in (file_1, file_2, file_3):
                if f.exists():
                    f.unlink()

    def test_disk_fallback_negative_and_partial_identifier_matching(self, client):
        """
        Verify strict whole-string matching on disk fallback:
        - Partial workflow_id (prefix/suffix) does NOT match.
        - Partial execution_id (prefix/suffix) does NOT match.
        - Non-existent workflow_id and execution_id return 404 Problem Details.
        """
        audit_dir = BASE_DIR / "data" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)

        wf_id = f"wf_prefix_test_{uuid.uuid4().hex[:8]}"
        exec_id = f"exec_suffix_test_{uuid.uuid4().hex[:8]}"
        disk_file = audit_dir / f"audit_{wf_id}_{exec_id}_20261105_160000.json"

        stored_record = {
            "workflow_id": wf_id,
            "execution_id": exec_id,
            "workflow_name": "Prefix Test",
            "timestamp_utc": "2026-11-05T16:00:00Z",
            "copyright": "Copyrights reserved to 90Studio",
            "execution_summary": {
                "total_steps": 1,
                "successful_steps": 1,
                "failed_steps": 0,
                "retried_steps": 0,
                "duration_seconds": 0.5,
                "final_status": "SUCCESS",
            },
        }
        disk_file.write_text(json.dumps(stored_record), encoding="utf-8")

        try:
            # Force cache eviction
            execution_manager._audit_summaries.clear()
            execution_manager._last_audit_summary = None

            # Substrings / prefixes
            partial_queries = [
                wf_id[:6],             # prefix of workflow_id
                wf_id[3:],             # suffix of workflow_id
                exec_id[:6],           # prefix of execution_id
                exec_id[4:],           # suffix of execution_id
                "wf_prefix_test",      # common root
                "exec_suffix_test",    # common root
                str(uuid.uuid4()),     # non-existent
            ]

            for q in partial_queries:
                resp = client.get(f"/api/execute/audit/{q}")
                assert resp.status_code == 404, f"Partial/non-existent query '{q}' should return 404, got {resp.status_code}"
                data = resp.json()
                assert data.get("copyright") == "Copyrights reserved to 90Studio"
                assert data.get("status") == 404

        finally:
            if disk_file.exists():
                disk_file.unlink()

    def test_identifiers_with_hyphens_and_underscores_symmetric_resolution(self, client):
        """
        Verify valid complex identifier slugs with hyphens and underscores:
        e.g. 'wf-enterprise-banking_kyc-v2' and 'exec-run_4f2a-9c1e'
        Both must resolve symmetrically and correctly.
        """
        audit_dir = BASE_DIR / "data" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)

        wf_id = f"wf-banking_kyc-v2_{uuid.uuid4().hex[:6]}"
        exec_id = f"exec-run_99-prod_{uuid.uuid4().hex[:6]}"
        disk_file = audit_dir / f"audit_{wf_id}_{exec_id}_20261105_170000.json"

        stored_record = {
            "workflow_id": wf_id,
            "execution_id": exec_id,
            "workflow_name": "Hyphen Underscore Workflow",
            "timestamp_utc": "2026-11-05T17:00:00Z",
            "copyright": "Copyrights reserved to 90Studio",
            "execution_summary": {
                "total_steps": 2,
                "successful_steps": 2,
                "failed_steps": 0,
                "retried_steps": 0,
                "duration_seconds": 1.2,
                "final_status": "SUCCESS",
            },
        }
        disk_file.write_text(json.dumps(stored_record), encoding="utf-8")

        try:
            # Force cache eviction
            execution_manager._audit_summaries.clear()
            execution_manager._last_audit_summary = None

            resp_wf = client.get(f"/api/execute/audit/{wf_id}")
            resp_ex = client.get(f"/api/execute/audit/{exec_id}")

            assert resp_wf.status_code == 200
            assert resp_ex.status_code == 200

            data_wf = resp_wf.json()
            data_ex = resp_ex.json()

            assert data_wf == data_ex
            assert data_wf["workflow_id"] == wf_id
            assert data_wf["execution_id"] == exec_id
            assert data_wf["copyright"] == "Copyrights reserved to 90Studio"

        finally:
            if disk_file.exists():
                disk_file.unlink()

    def test_tampered_disk_record_mismatch_defense_in_depth(self, client):
        """
        Adversarial Test:
        If a file exists on disk named audit_{wf_id}_{exec_id}_{timestamp}.json, but the JSON payload
        inside contains a mismatching workflow_id and execution_id (e.g. spoofed or corrupted),
        the endpoint must reject it and return 404 Problem Details rather than trusting the filename.
        """
        audit_dir = BASE_DIR / "data" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)

        wf_id = f"wf_spoof_target_{uuid.uuid4().hex[:8]}"
        exec_id = f"exec_spoof_target_{uuid.uuid4().hex[:8]}"
        tampered_file = audit_dir / f"audit_{wf_id}_{exec_id}_20261105_180000.json"

        # File contents contain completely different IDs
        tampered_record = {
            "workflow_id": "different_wf_id_completely",
            "execution_id": "different_exec_id_completely",
            "workflow_name": "Spoofed Tampered File",
            "timestamp_utc": "2026-11-05T18:00:00Z",
            "copyright": "Copyrights reserved to 90Studio",
            "execution_summary": {
                "total_steps": 1,
                "final_status": "SUCCESS",
            },
        }
        tampered_file.write_text(json.dumps(tampered_record), encoding="utf-8")

        try:
            # Force cache eviction
            execution_manager._audit_summaries.clear()
            execution_manager._last_audit_summary = None

            resp_wf = client.get(f"/api/execute/audit/{wf_id}")
            resp_ex = client.get(f"/api/execute/audit/{exec_id}")

            assert resp_wf.status_code == 404, f"Tampered record should not be returned by wf_id: {resp_wf.text}"
            assert resp_ex.status_code == 404, f"Tampered record should not be returned by exec_id: {resp_ex.text}"
            assert resp_wf.json().get("copyright") == "Copyrights reserved to 90Studio"
            assert resp_ex.json().get("copyright") == "Copyrights reserved to 90Studio"

        finally:
            if tampered_file.exists():
                tampered_file.unlink()

    @pytest.mark.asyncio
    async def test_concurrent_audit_polling_symmetry(self):
        """
        Adversarial Test:
        While a workflow is actively running, issue 20 concurrent requests interleaved
        between workflow_id and execution_id queries.
        Assert that all 20 return HTTP 200 with RUNNING state, zero race conditions,
        zero 500 errors, and consistent 90Studio copyright attribution.
        """
        wf_id = f"wf_concurrent_sym_{uuid.uuid4().hex[:8]}"
        payload = _sample_workflow_payload(wf_id=wf_id, step_delay_ms=2000)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
            r_start = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200
            exec_id = r_start.json()["execution_id"]

            try:
                # Wait for RUNNING state
                for _ in range(25):
                    st = (await async_client.get("/api/execute/status")).json()
                    if st.get("state") == "RUNNING":
                        break
                    await asyncio.sleep(0.02)

                # Prepare 20 interleaved tasks
                tasks = []
                for i in range(20):
                    target_id = wf_id if i % 2 == 0 else exec_id
                    tasks.append(async_client.get(f"/api/execute/audit/{target_id}"))

                responses = await asyncio.gather(*tasks)

                for idx, r in enumerate(responses):
                    assert r.status_code == 200, f"Concurrent request {idx} failed with {r.status_code}: {r.text}"
                    data = r.json()
                    assert data["workflow_id"] == wf_id
                    assert data["execution_id"] == exec_id
                    assert data["status"] == "RUNNING"
                    assert data.get("copyright") == "Copyrights reserved to 90Studio"

            finally:
                await async_client.post("/api/execute/abort")

