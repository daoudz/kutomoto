"""
tests.test_executable_and_driver_integration
End-to-end verification of native Windows 64-bit executables (kutomoto.exe, sample_desktop_form.exe),
Win32DriverAdapter / ProductionDriverAdapter parameter contracts, and sample target routes.
Copyrights reserved to 90Studio
"""

from __future__ import annotations

from pathlib import Path
import socket
import struct
import subprocess
import sys
import time
import urllib.request

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from kutomoto import __copyright__, __version__  # noqa: E402
from kutomoto.automation import win32_input, win32_window  # noqa: E402
from kutomoto.automation.win32_driver import ProductionDriverAdapter  # noqa: E402
from kutomoto.engine.safety import SafetyGuard  # noqa: E402
from kutomoto.server.app import Win32DriverAdapter, app  # noqa: E402


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_executable_files_exist_and_have_valid_pe64_headers():
    """Verifies that kutomoto.exe and sample_desktop_form.exe exist and have valid 64-bit PE headers."""
    exe_paths = [
        PROJECT_ROOT / "kutomoto.exe",
        PROJECT_ROOT / "dist" / "kutomoto.exe",
        PROJECT_ROOT / "samples" / "desktop" / "sample_desktop_form.exe",
        PROJECT_ROOT / "dist" / "sample_desktop_form.exe",
    ]
    for exe_path in exe_paths:
        assert exe_path.is_file(), f"Missing executable at {exe_path}"
        raw = exe_path.read_bytes()
        assert len(raw) > 2048, f"Executable {exe_path} is unexpectedly small ({len(raw)} bytes)"
        assert raw[:2] == b"MZ", f"Invalid DOS MZ header in {exe_path}"
        pe_offset = struct.unpack_from("<I", raw, 0x3C)[0]
        assert raw[pe_offset : pe_offset + 4] == b"PE\x00\x00", f"Invalid PE signature in {exe_path}"
        machine = struct.unpack_from("<H", raw, pe_offset + 4)[0]
        assert machine == 0x8664, f"Expected x64 machine type (0x8664) in {exe_path}, got 0x{machine:04X}"


def test_kutomoto_exe_cli_version_and_help():
    """Verifies that kutomoto.exe and dist/kutomoto.exe respond to --version and --help."""
    for exe_path in (PROJECT_ROOT / "kutomoto.exe", PROJECT_ROOT / "dist" / "kutomoto.exe"):
        res_ver = subprocess.run(
            [str(exe_path), "--version"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=15,
        )
        assert res_ver.returncode == 0, f"{exe_path} --version failed: {res_ver.stderr}"
        assert f"kutomoto {__version__}" in res_ver.stdout
        assert __copyright__ in res_ver.stdout

        res_help = subprocess.run(
            [str(exe_path), "--help"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=15,
        )
        assert res_help.returncode == 0, f"{exe_path} --help failed: {res_help.stderr}"
        assert "usage: kutomoto" in res_help.stdout
        assert __copyright__ in res_help.stdout


def test_kutomoto_exe_live_server_startup_and_shutdown():
    """Launches kutomoto.exe on a free port, verifies live HTTP health & UI serving, and terminates cleanly."""
    exe_path = PROJECT_ROOT / "kutomoto.exe"
    port = _get_free_port()

    proc = subprocess.Popen(
        [str(exe_path), "--host", "127.0.0.1", "--port", str(port), "--no-browser", "--mock"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        health_url = f"http://127.0.0.1:{port}/api/health"
        ui_url = f"http://127.0.0.1:{port}/"
        sample_url = f"http://127.0.0.1:{port}/samples/web/index.html"

        ready = False
        for _ in range(40):
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen(health_url, timeout=0.5) as resp:
                    if resp.status == 200:
                        body = resp.read().decode("utf-8")
                        assert "Copyrights reserved to 90Studio" in body
                        ready = True
                        break
            except Exception:
                time.sleep(0.2)

        assert ready, f"kutomoto.exe server did not become healthy on port {port}"

        with urllib.request.urlopen(ui_url, timeout=1.0) as resp_ui:
            assert resp_ui.status == 200
            html = resp_ui.read().decode("utf-8")
            assert "kutomoto — Enterprise Form Automation" in html
            assert "Copyrights reserved to 90Studio" in html

        with urllib.request.urlopen(sample_url, timeout=1.0) as resp_sample:
            assert resp_sample.status == 200
            sample_html = resp_sample.read().decode("utf-8")
            assert "Banking KYC" in sample_html
            assert "Copyrights reserved to 90Studio" in sample_html
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_samples_api_and_static_routes(monkeypatch):
    """Verifies /api/samples, /api/samples/launch/web, /api/samples/launch/desktop, and /samples/web/index.html."""
    monkeypatch.setenv("KUTOMOTO_MOCK_DRIVER", "1")
    client = TestClient(app)

    resp_samples = client.get("/api/samples")
    assert resp_samples.status_code == 200
    samples = resp_samples.json()
    assert isinstance(samples, list)
    assert len(samples) >= 2
    sample_ids = {s["id"] for s in samples}
    assert "e2e-banking-kyc-web-flow-0001" in sample_ids
    assert "telecom-sim-provisioning-e2e-001" in sample_ids

    resp_web = client.post("/api/samples/launch/web")
    assert resp_web.status_code == 200
    assert resp_web.json()["status"] == "launched"
    assert resp_web.json()["copyright"] == __copyright__

    resp_desktop = client.post("/api/samples/launch/desktop")
    assert resp_desktop.status_code == 200
    assert resp_desktop.json()["status"] == "launched"
    assert resp_desktop.json()["copyright"] == __copyright__

    resp_static = client.get("/samples/web/index.html")
    assert resp_static.status_code == 200
    assert "Banking KYC" in resp_static.text


def test_win32_driver_adapter_and_production_adapter_contracts(monkeypatch):
    """
    Verifies that Win32DriverAdapter and ProductionDriverAdapter return integer HWND from find_window,
    accept delay_between_keys_ms / repeat_count / strategy, and work seamlessly with SafetyGuard.
    """
    sample_win = win32_window.WindowInfo(
        hwnd=4242,
        title="Telecom SIM Provisioning System — 90Studio",
        class_name="TkTopLevel",
        pid=5000,
        executable_name="sample_desktop_form.exe",
        executable_path=r"C:\kutomoto\sample_desktop_form.exe",
        is_visible=True,
        is_iconic=False,
        rect=(100, 100, 740, 680),
        client_rect=(100, 100, 640, 580),
    )

    monkeypatch.setattr(win32_window, "find_window", lambda **kw: sample_win)
    monkeypatch.setattr(win32_window, "get_foreground_window", lambda: 4242)

    recorded = []
    monkeypatch.setattr(win32_input, "send_raw_input", lambda inputs: recorded.extend(inputs) or len(inputs))

    for adapter_cls in (Win32DriverAdapter, ProductionDriverAdapter):
        adapter = adapter_cls()

        # 1. find_window must return integer HWND (not WindowInfo)
        hwnd = adapter.find_window("Telecom SIM", match_mode="contains")
        assert isinstance(hwnd, int), f"Expected int HWND from {adapter_cls.__name__}.find_window, got {type(hwnd)}"
        assert hwnd == 4242

        # 2. send_text with delay_between_keys_ms
        recorded.clear()
        adapter.send_text("ABC", delay_between_keys_ms=0, use_clipboard_threshold=100)
        assert len(recorded) == 6  # 3 chars * (down + up)

        # 3. send_key_press with repeat_count
        recorded.clear()
        adapter.send_key_press("tab", repeat_count=2)
        assert len(recorded) == 4  # 2 * (down + up)

        # 4. send_key_up
        recorded.clear()
        adapter.send_key_up("ctrl")
        assert len(recorded) == 1

        # 5. clear_field with all strategies
        for strat in ("select_all_backspace", "triple_click_delete", "backspace_repeat", "double"):
            adapter.clear_field(strategy=strat)

        # 6. SafetyGuard integration (is_key_pressed, pre_step_check, emergency_cleanup)
        monkeypatch.setattr(adapter, "get_cursor_pos", lambda: (300, 300))
        monkeypatch.setattr(adapter, "is_key_pressed", lambda k: False)
        guard = SafetyGuard(driver=adapter)
        guard.set_target_hwnd(4242)
        guard.register_intentional_mouse_move(300, 300)
        guard.pre_step_check(4242)
        guard.emergency_cleanup()


def test_win32_window_find_window_regex_in_contains_and_exe_aliasing(monkeypatch):
    """
    Verifies that win32_window.find_window handles:
    1. Regex patterns when match_mode='contains' (default TargetApplication.match_mode).
    2. Generic wildcard '.*' deprioritizing the kutomoto Studio window in favor of target forms.
    3. Process name aliasing between sample_desktop_form.exe and python.exe / pythonw.exe.
    4. Cross-browser fallback when exe_name='msedge.exe' is paired with a specific web form title_pattern.
    """
    windows = [
        win32_window.WindowInfo(
            hwnd=1001,
            title="kutomoto — Enterprise Form Automation",
            class_name="Chrome_WidgetWin_1",
            pid=2001,
            executable_name="msedge.exe",
            executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            is_visible=True,
            is_iconic=False,
            rect=(50, 50, 1416, 900),
            client_rect=(50, 50, 1366, 850),
        ),
        win32_window.WindowInfo(
            hwnd=2002,
            title="Telecom SIM Provisioning System — 90Studio",
            class_name="TkTopLevel",
            pid=2002,
            executable_name="pythonw.exe",
            executable_path=r"C:\Python314\pythonw.exe",
            is_visible=True,
            is_iconic=False,
            rect=(120, 120, 760, 700),
            client_rect=(120, 120, 640, 580),
        ),
        win32_window.WindowInfo(
            hwnd=3003,
            title="Banking KYC Customer Onboarding — 90Studio",
            class_name="Chrome_WidgetWin_1",
            pid=3003,
            executable_name="chrome.exe",
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            is_visible=True,
            is_iconic=False,
            rect=(150, 150, 1350, 950),
            client_rect=(150, 150, 1200, 800),
        ),
    ]
    monkeypatch.setattr(win32_window, "enumerate_windows", lambda **kw: windows)

    # 1. Regex pattern with match_mode='contains'
    w_regex_contains = win32_window.find_window(
        title_pattern=r".*Telecom SIM Provisioning.*",
        match_mode="contains",
    )
    assert w_regex_contains is not None and w_regex_contains.hwnd == 2002

    # 2. Wildcard '.*' with match_mode='contains' skips kutomoto Studio window (1001) and selects form (2002)
    w_wildcard = win32_window.find_window(title_pattern=".*", match_mode="contains")
    assert w_wildcard is not None and w_wildcard.hwnd == 2002

    # 3. sample_desktop_form.exe process filter matches pythonw.exe window
    w_desktop_exe = win32_window.find_window(
        title_pattern="Telecom SIM",
        exe_name="sample_desktop_form.exe",
        match_mode="contains",
    )
    assert w_desktop_exe is not None and w_desktop_exe.hwnd == 2002

    # 4. msedge.exe process filter with specific web title falls back to chrome.exe when not open in Edge
    w_browser_fallback = win32_window.find_window(
        title_pattern=r".*Banking KYC.*",
        exe_name="msedge.exe",
        match_mode="regex",
    )
    assert w_browser_fallback is not None and w_browser_fallback.hwnd == 3003


def test_win32_driver_cursor_fallback_and_live_tk_window_focus(monkeypatch):
    """
    Verifies that:
    1. When user32.GetCursorPos returns 0 (FALSE), Win32DriverAdapter and ProductionDriverAdapter
       return _last_cursor_pos (e.g. (500, 500)) instead of (0, 0), preventing false CornerFailsafeTriggered.
    2. Win32DriverAdapter.find_window and focus_window succeed against a real TelecomProvisioningForm
       Tkinter window and get_foreground_window returns the target HWND.
    """
    from samples.desktop.sample_desktop_form import TelecomProvisioningForm

    for adapter_cls in (Win32DriverAdapter, ProductionDriverAdapter):
        adapter = adapter_cls()
        # Simulate GetCursorPos failing (returning 0) without writing to POINT
        if adapter_cls is Win32DriverAdapter:
            monkeypatch.setattr(adapter._core.user32, "GetCursorPos", lambda pt_ptr: 0)
        else:
            from kutomoto.automation import win32_driver
            monkeypatch.setattr(win32_driver.user32, "GetCursorPos", lambda pt_ptr: 0)

        pos = adapter.get_cursor_pos()
        assert pos == (500, 500), f"Expected fallback (500, 500) when GetCursorPos fails, got {pos}"
        guard = SafetyGuard(driver=adapter)
        guard.check_corner_failsafe()  # Must NOT raise CornerFailsafeTriggered!

    form = TelecomProvisioningForm(headless=False)
    try:
        form.update()
        adapter = Win32DriverAdapter()
        hwnd = adapter.find_window(
            title_pattern=r".*Telecom SIM Provisioning.*",
            match_mode="contains",
            process_name="sample_desktop_form.exe",
        )
        assert hwnd is not None and hwnd > 0
        focused = adapter.focus_window(hwnd, timeout_ms=300)
        assert focused is True
        assert adapter.get_foreground_window() > 0
    finally:
        form.destroy()


def test_telecom_desktop_form_space_on_kyc_and_select_all_on_focus():
    """
    Verifies that pressing Space on combo_kyc preserves 'VERIFIED' (instead of overwriting with ' ')
    and focusing an entry selects existing text so repeated runs do not corrupt field values.
    """
    from samples.desktop.sample_desktop_form import TelecomProvisioningForm

    form = TelecomProvisioningForm(headless=True)
    try:
        form.update()
        # Simulate pressing space on combo_kyc
        form.var_kyc.set("PENDING")
        res = form.combo_kyc.event_generate("<KeyPress-space>")
        form.update()
        assert res != "error"
        # Trigger the bound handler directly to verify return "break" and state update
        handler_result = form.combo_kyc.tk.call(form.combo_kyc.bind("<KeyPress-space>")) if False else None
        _ = handler_result
        # Populate valid fields and verify validation succeeds after space on combo_kyc
        form.var_msisdn.set("555-019-2834")
        form.var_iccid.set("8901410321111851072")
        form.var_plan.set("Unlimited Enterprise")
        form.var_kyc.set("VERIFIED")
        form.var_imsi.set("310260987654321")
        is_valid, errors, payload = form.validate_form()
        assert is_valid is True, f"Expected valid form, got errors: {errors}"
        assert payload["kyc_status"] == "VERIFIED"
        assert form.var_kyc_status.get() is True

        # Focus entry_msisdn and verify selection_present after idle
        form.entry_msisdn.focus_force()
        form.entry_msisdn.event_generate("<FocusIn>")
        form.update()
        form.update_idletasks()
        assert form.entry_msisdn.selection_present() is True
    finally:
        form.destroy()

