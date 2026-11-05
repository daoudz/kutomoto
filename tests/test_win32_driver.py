"""
tests.test_win32_driver
Comprehensive unit tests for Win32 automation core, 64-bit ABI structs, DPI awareness,
virtual key mapping, coordinate normalization, and Unicode typing.
Copyrights reserved to 90Studio
"""

import ctypes
from pathlib import Path
import sys
import pytest

SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from kutomoto.automation.win32_core import (  # noqa: E402
    HARDWAREINPUT,
    INPUT,
    KEYBDINPUT,
    MOUSEINPUT,
    VK_MAP,
    _INPUT_UNION,
    resolve_virtual_key,
    set_process_dpi_awareness,
)
from kutomoto.automation.win32_window import (  # noqa: E402
    WindowInfo,
)


def test_64bit_abi_struct_layout_and_size():
    """
    CRITICAL 64-bit ABI TEST:
    Verifies exact 40-byte 64-bit ABI alignment for SendInput.
    Mismatch results in Win32 Error 87 (ERROR_INVALID_PARAMETER) or heap corruption.
    """
    assert ctypes.sizeof(MOUSEINPUT) == 32, f"MOUSEINPUT must be 32 bytes, got {ctypes.sizeof(MOUSEINPUT)}"
    assert ctypes.sizeof(KEYBDINPUT) == 24, f"KEYBDINPUT must be 24 bytes, got {ctypes.sizeof(KEYBDINPUT)}"
    assert ctypes.sizeof(HARDWAREINPUT) == 8, f"HARDWAREINPUT must be 8 bytes, got {ctypes.sizeof(HARDWAREINPUT)}"
    assert ctypes.sizeof(_INPUT_UNION) == 32, f"_INPUT_UNION must be 32 bytes, got {ctypes.sizeof(_INPUT_UNION)}"
    assert ctypes.sizeof(INPUT) == 40, f"Critical: INPUT must be 40 bytes, got {ctypes.sizeof(INPUT)}"

    # Union offset check (4 bytes type + 4 bytes padding = offset 8)
    assert INPUT.union.offset == 8, f"Union must begin at byte offset 8, got {INPUT.union.offset}"


def test_virtual_key_mappings_and_resolver():
    """Verifies standard Win32 virtual key code mappings and resolve_virtual_key helper."""
    assert VK_MAP["tab"] == 0x09
    assert VK_MAP["enter"] == 0x0D
    assert VK_MAP["return"] == 0x0D
    assert VK_MAP["escape"] == 0x1B
    assert VK_MAP["backspace"] == 0x08
    assert VK_MAP["space"] == 0x20
    assert VK_MAP["ctrl"] == 0x11
    assert VK_MAP["shift"] == 0x10
    assert VK_MAP["alt"] == 0x12
    assert VK_MAP["win"] == 0x5B

    # Letters and numbers
    assert resolve_virtual_key("a") == ord("A")
    assert resolve_virtual_key("Z") == ord("Z")
    assert resolve_virtual_key("5") == ord("5")
    assert resolve_virtual_key("enter") == 0x0D
    assert resolve_virtual_key(0x20) == 0x20

    with pytest.raises(ValueError):
        resolve_virtual_key("nonexistent_virtual_key_identifier_xyz")


def test_set_process_dpi_awareness():
    """Verifies that DPI awareness ladder successfully executes on Windows."""
    mode = set_process_dpi_awareness()
    assert mode in ("PER_MONITOR_V2", "PER_MONITOR_V1", "SHCORE_PER_MONITOR", "SYSTEM_AWARE", "ALREADY_SET", "UNAWARE")


def test_normalized_coordinate_translation(monkeypatch):
    """
    Tests translating normalized [0.0, 1.0] coordinates to physical screen pixels
    by executing kutomoto.automation.win32_window.normalized_to_screen_coords.
    """
    from kutomoto.automation import win32_window

    class MockUser32:
        @staticmethod
        def GetClientRect(hwnd, rect_ptr):
            rect = getattr(rect_ptr, "_obj", getattr(rect_ptr, "contents", rect_ptr))
            rect.left = 0
            rect.top = 0
            rect.right = 1000
            rect.bottom = 600
            return 1

    monkeypatch.setattr(win32_window, "user32", MockUser32())
    monkeypatch.setattr(win32_window, "client_to_screen_coords", lambda hwnd, cx, cy: (200 + cx, 150 + cy))

    screen_x, screen_y = win32_window.normalized_to_screen_coords(101, 0.35, 0.50)
    assert screen_x == 550
    assert screen_y == 450


def test_unicode_utf16_surrogate_splitting(monkeypatch):
    """
    Tests that send_text decomposes non-BMP Unicode characters (e.g. emojis)
    into UTF-16 surrogate pairs and dispatches them via SendInput KEYEVENTF_UNICODE.
    """
    from kutomoto.automation import win32_input
    from kutomoto.automation.win32_core import INPUT_KEYBOARD, KEYEVENTF_KEYUP, KEYEVENTF_UNICODE

    captured_inputs = []

    def mock_send_raw_input(inputs):
        captured_inputs.extend(inputs)
        return len(inputs)

    monkeypatch.setattr(win32_input, "send_raw_input", mock_send_raw_input)

    text = "Kutomoto 🚀 Banking"
    win32_input.send_text(text, delay_ms=0)

    # Extract scanned 16-bit code units for keydown unicode inputs
    scans = [
        inp.union.ki.wScan for inp in captured_inputs
        if inp.type == INPUT_KEYBOARD and (inp.union.ki.dwFlags & KEYEVENTF_UNICODE) and not (inp.union.ki.dwFlags & KEYEVENTF_KEYUP)
    ]

    # Rocket emoji '🚀' is U+1F680, which decomposes into 0xD83D and 0xDE80
    assert 0xD83D in scans
    assert 0xDE80 in scans
    assert len(scans) == len(text) + 1  # 1 extra unit for surrogate pair


def test_window_info_dataclass():
    """Tests WindowInfo geometry properties."""
    info = WindowInfo(
        hwnd=12345,
        title="Test Window",
        class_name="WindowClass",
        pid=9876,
        executable_name="test.exe",
        executable_path=r"C:\test\test.exe",
        is_visible=True,
        is_iconic=False,
        rect=(100, 100, 900, 700),
        client_rect=(108, 131, 784, 561),
    )
    assert info.width == 800
    assert info.height == 600
    assert info.client_width == 784
    assert info.client_height == 561


def test_clear_field_strategy_sequences(monkeypatch):
    """Verifies that clear_field executes correct keyboard/mouse sequences for all strategies."""
    from kutomoto.automation import win32_input

    calls = []
    monkeypatch.setattr(win32_input, "send_hotkey", lambda mods, key, *a, **kw: calls.append(("hotkey", mods, key)))
    monkeypatch.setattr(win32_input, "send_key_press", lambda key, *a, **kw: calls.append(("key_press", key)))

    # Strategy 1: ctrl_a_backspace
    calls.clear()
    win32_input.clear_field("ctrl_a_backspace", delay_ms=0)
    assert calls == [("hotkey", ["ctrl"], "a"), ("key_press", "backspace")]

    # Strategy 2: double
    calls.clear()
    win32_input.clear_field("double", delay_ms=0)
    assert calls == [("hotkey", ["ctrl"], "a"), ("key_press", "backspace"), ("key_press", "delete")]


def test_send_raw_input_empty():
    """Verifies that send_raw_input cleanly returns 0 on empty sequence."""
    from kutomoto.automation.win32_input import send_raw_input
    assert send_raw_input([]) == 0


def test_send_text_empty_string():
    """Verifies send_text cleanly returns without actions on empty string (E14)."""
    from kutomoto.automation.win32_input import send_text
    send_text("")  # Must not raise


def test_activate_target_window_invalid_hwnd():
    """Verifies activate_target_window returns False for non-existent HWND 0."""
    from kutomoto.automation.win32_window import activate_target_window
    assert activate_target_window(0) is False
    assert activate_target_window(-1) is False


def test_get_executable_info_invalid_pid():
    """Verifies get_executable_info returns empty strings for invalid PID."""
    from kutomoto.automation.win32_window import get_executable_info
    exe_name, exe_path = get_executable_info(0)
    assert exe_name == ""
    assert exe_path == ""


def test_get_window_info_invalid_hwnd():
    """Verifies get_window_info returns None for invalid HWND."""
    from kutomoto.automation.win32_window import get_window_info
    assert get_window_info(0) is None


def test_find_window_matching_modes(monkeypatch):
    """Verifies find_window and find_all_windows with regex, contains, exact, startswith."""
    from kutomoto.automation import win32_window

    sample_windows = [
        WindowInfo(
            hwnd=101,
            title="Banking KYC Customer Onboarding - 90Studio",
            class_name="Chrome_WidgetWin_1",
            pid=1100,
            executable_name="msedge.exe",
            executable_path=r"C:\Program Files (x86)\Microsoft\Edge\msedge.exe",
            is_visible=True,
            is_iconic=False,
            rect=(100, 100, 1000, 800),
            client_rect=(100, 100, 900, 700),
        ),
        WindowInfo(
            hwnd=102,
            title="Commercial Loan Origination - 90Studio Bank",
            class_name="HwndWrapper[loan_app]",
            pid=1200,
            executable_name="loan_app.exe",
            executable_path=r"C:\Program Files\90Studio\loan_app.exe",
            is_visible=True,
            is_iconic=False,
            rect=(150, 150, 1024, 768),
            client_rect=(150, 150, 1024, 768),
        ),
        WindowInfo(
            hwnd=103,
            title="Calculator",
            class_name="ApplicationFrameWindow",
            pid=1300,
            executable_name="calc.exe",
            executable_path=r"C:\Windows\calc.exe",
            is_visible=True,
            is_iconic=False,
            rect=(200, 200, 600, 600),
            client_rect=(200, 200, 600, 600),
        ),
    ]

    monkeypatch.setattr(win32_window, "enumerate_windows", lambda **kwargs: sample_windows)

    # 1. Regex mode
    w1 = win32_window.find_window(title_pattern=r".*Banking KYC.*", match_mode="regex")
    assert w1 is not None and w1.hwnd == 101

    # 2. Contains mode
    w2 = win32_window.find_window(title_pattern="Loan Origination", match_mode="contains")
    assert w2 is not None and w2.hwnd == 102

    # 3. Exact mode
    w3 = win32_window.find_window(title_pattern="Calculator", match_mode="exact")
    assert w3 is not None and w3.hwnd == 103

    # 4. Startswith mode
    w4 = win32_window.find_window(title_pattern="Commercial", match_mode="startswith")
    assert w4 is not None and w4.hwnd == 102

    # 5. Process name filter
    w5 = win32_window.find_window(exe_name="msedge.exe")
    assert w5 is not None and w5.hwnd == 101

    # 6. Combined filter
    w6 = win32_window.find_window(title_pattern="Loan", exe_name="loan_app.exe", match_mode="contains")
    assert w6 is not None and w6.hwnd == 102

    # 7. Non-matching filter
    w_none = win32_window.find_window(title_pattern="NonExistentTitle999")
    assert w_none is None

    # 8. Find all windows matching
    all_90studio = win32_window.find_all_windows(title_pattern=r"90Studio", match_mode="regex")
    assert len(all_90studio) == 2
