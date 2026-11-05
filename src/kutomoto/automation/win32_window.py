"""
kutomoto.automation.win32_window
Win32 desktop window enumeration, geometry translation, and focus activation.
Copyrights reserved to 90Studio
"""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import logging
from pathlib import Path
import re
import time
from typing import List, Optional, Tuple

from kutomoto.automation.win32_core import (
    POINT,
    RECT,
    SW_RESTORE,
)

logger = logging.getLogger("kutomoto.automation.win32_window")

try:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
except (AttributeError, OSError):
    user32 = None  # type: ignore
    kernel32 = None  # type: ignore

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


# ==============================================================================
# 1. WINDOW DATA MODEL
# ==============================================================================

@dataclass
class WindowInfo:
    hwnd: int
    title: str
    class_name: str
    pid: int
    executable_name: str
    executable_path: str
    is_visible: bool
    is_iconic: bool
    rect: Tuple[int, int, int, int]        # left, top, right, bottom (screen px)
    client_rect: Tuple[int, int, int, int] # left, top, width, height (screen px)

    @property
    def width(self) -> int:
        return self.rect[2] - self.rect[0]

    @property
    def height(self) -> int:
        return self.rect[3] - self.rect[1]

    @property
    def client_width(self) -> int:
        return self.client_rect[2]

    @property
    def client_height(self) -> int:
        return self.client_rect[3]


# ==============================================================================
# 2. WINDOW ENUMERATION & INSPECTION
# ==============================================================================

def get_executable_info(pid: int) -> Tuple[str, str]:
    """
    Retrieves the full executable path and filename for a given PID.
    Uses PROCESS_QUERY_LIMITED_INFORMATION (0x1000) for unprivileged query.
    """
    if kernel32 is None or pid <= 0:
        return "", ""

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h_proc:
        return "", ""

    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size)):
            exe_path = buf.value
            return Path(exe_path).name, exe_path
        return "", ""
    finally:
        kernel32.CloseHandle(h_proc)


def get_window_info(hwnd: int) -> Optional[WindowInfo]:
    """
    Extracts comprehensive metadata for a specific HWND.
    Returns None if HWND is invalid.
    """
    if user32 is None or not user32.IsWindow(hwnd):
        return None

    # Title
    length = user32.GetWindowTextLengthW(hwnd)
    title = ""
    if length > 0:
        t_buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, t_buf, length + 1)
        title = t_buf.value

    # Class Name
    c_buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, c_buf, 256)
    class_name = c_buf.value

    # PID & Executable
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    exe_name, exe_path = get_executable_info(pid.value)

    # State & Geometry
    is_visible = bool(user32.IsWindowVisible(hwnd))
    is_iconic = bool(user32.IsIconic(hwnd))

    rc = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rc))
    rect = (rc.left, rc.top, rc.right, rc.bottom)

    # Client rect on screen
    crc = RECT()
    user32.GetClientRect(hwnd, ctypes.byref(crc))
    pt = POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    client_rect = (pt.x, pt.y, crc.right - crc.left, crc.bottom - crc.top)

    return WindowInfo(
        hwnd=int(hwnd),
        title=title,
        class_name=class_name,
        pid=int(pid.value),
        executable_name=exe_name,
        executable_path=exe_path,
        is_visible=is_visible,
        is_iconic=is_iconic,
        rect=rect,
        client_rect=client_rect,
    )


def enumerate_windows(visible_only: bool = True, non_empty_title_only: bool = True) -> List[WindowInfo]:
    """
    Enumerates all top-level windows on the current desktop.
    """
    if user32 is None:
        return []

    results: List[WindowInfo] = []

    def enum_cb(hwnd, lparam):
        if visible_only and not user32.IsWindowVisible(hwnd):
            return True
        info = get_window_info(hwnd)
        if info:
            if non_empty_title_only and not info.title.strip():
                return True
            results.append(info)
        return True

    cb = WNDENUMPROC(enum_cb)
    user32.EnumWindows(cb, 0)
    return results


_BROWSER_EXECUTABLES = {"msedge.exe", "chrome.exe", "firefox.exe", "brave.exe", "iexplore.exe"}
_PYTHON_DESKTOP_EXECUTABLES = {"python.exe", "pythonw.exe", "sample_desktop_form.exe"}
_last_focused_hwnd: int = 0


def _matches_executable(actual_exe: str, expected_exe: str, case_sensitive: bool = False) -> bool:
    if not expected_exe:
        return True
    if case_sensitive and actual_exe == expected_exe:
        return True
    actual_low = (actual_exe or "").lower()
    expected_low = expected_exe.lower()
    if actual_low == expected_low:
        return True
    if expected_low in _PYTHON_DESKTOP_EXECUTABLES and actual_low in _PYTHON_DESKTOP_EXECUTABLES:
        return True
    return False


def _matches_title(
    actual_title: str,
    title_pattern: str,
    match_mode: str = "regex",
    case_sensitive: bool = False,
) -> bool:
    if not title_pattern:
        return True
    flags = 0 if case_sensitive else re.IGNORECASE
    target_title = actual_title if case_sensitive else actual_title.lower()
    pattern = title_pattern if case_sensitive else title_pattern.lower()

    if match_mode == "exact":
        return target_title == pattern
    if match_mode == "startswith":
        return target_title.startswith(pattern)
    if match_mode == "contains":
        if pattern in target_title:
            return True
        try:
            return bool(re.search(title_pattern, actual_title, flags))
        except re.error:
            return False
    # Default: 'regex'
    try:
        return bool(re.search(title_pattern, actual_title, flags))
    except re.error:
        return pattern in target_title


def _is_kutomoto_studio_window(title: str) -> bool:
    t = (title or "").lower()
    return "kutomoto" in t and "enterprise form automation" in t


def find_window(
    title_pattern: Optional[str] = None,
    exe_name: Optional[str] = None,
    match_mode: str = "regex",
    case_sensitive: bool = False,
    visible_only: bool = True,
) -> Optional[WindowInfo]:
    """
    Finds the first window matching title pattern and/or executable name.
    match_mode: 'regex', 'contains', 'exact', or 'startswith'.
    """
    all_matches = find_all_windows(
        title_pattern=title_pattern,
        exe_name=exe_name,
        match_mode=match_mode,
        case_sensitive=case_sensitive,
        visible_only=visible_only,
    )
    if not all_matches:
        return None

    # When using a generic wildcard pattern (e.g. ".*"), prefer non-empty non-Studio windows first
    if title_pattern and title_pattern.strip() in (".*", ".+", "^.*$"):
        non_studio = [
            w for w in all_matches
            if w.title.strip() and not _is_kutomoto_studio_window(w.title)
        ]
        if non_studio:
            return non_studio[0]
        non_empty = [w for w in all_matches if w.title.strip()]
        if non_empty:
            return non_empty[0]

    return all_matches[0]


def find_all_windows(
    title_pattern: Optional[str] = None,
    exe_name: Optional[str] = None,
    match_mode: str = "regex",
    case_sensitive: bool = False,
    visible_only: bool = True,
) -> List[WindowInfo]:
    """
    Finds all windows matching title pattern and/or executable name.
    """
    windows = enumerate_windows(visible_only=visible_only, non_empty_title_only=False)
    matches: List[WindowInfo] = []

    for win in windows:
        if exe_name and not _matches_executable(win.executable_name, exe_name, case_sensitive):
            continue
        if title_pattern and not _matches_title(win.title, title_pattern, match_mode, case_sensitive):
            continue
        matches.append(win)

    # Fallback: if a specific title_pattern was requested along with a browser exe_name (e.g. msedge.exe),
    # but the user opened the target web page in another browser (e.g. chrome.exe or firefox.exe),
    # allow matching across browser executables.
    if not matches and exe_name and title_pattern and exe_name.lower() in _BROWSER_EXECUTABLES:
        for win in windows:
            if (win.executable_name or "").lower() in _BROWSER_EXECUTABLES:
                if _matches_title(win.title, title_pattern, match_mode, case_sensitive):
                    matches.append(win)

    return matches


# ==============================================================================
# 3. FOCUS MANAGEMENT & THREAD INPUT ATTACHMENT
# ==============================================================================

def activate_target_window(hwnd: int, timeout_ms: int = 1500) -> bool:
    """
    Brings target HWND to the foreground on Windows 10/11 using thread-input queue
    attachment, iconic state restoration, and simulated Alt tap DWM unlock.
    """
    global _last_focused_hwnd
    if user32 is None or kernel32 is None:
        return False

    if not hwnd or hwnd <= 0 or not user32.IsWindow(hwnd):
        logger.error("Invalid window handle: %s", hwnd)
        return False

    if user32.GetForegroundWindow() == hwnd:
        _last_focused_hwnd = int(hwnd)
        return True

    # 1. Un-minimize if iconic
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.06)

    foreground_hwnd = user32.GetForegroundWindow()
    current_thread_id = kernel32.GetCurrentThreadId()
    foreground_thread_id = (
        user32.GetWindowThreadProcessId(foreground_hwnd, None) if foreground_hwnd else 0
    )
    target_thread_id = user32.GetWindowThreadProcessId(hwnd, None)

    attached_fg = False
    attached_target = False
    if foreground_thread_id != 0 and foreground_thread_id != current_thread_id:
        attached_fg = bool(user32.AttachThreadInput(current_thread_id, foreground_thread_id, True))
    if (
        target_thread_id != 0
        and target_thread_id != current_thread_id
        and target_thread_id != foreground_thread_id
    ):
        attached_target = bool(user32.AttachThreadInput(current_thread_id, target_thread_id, True))

    try:
        # Simulated Alt-key tap to unstick DWM foreground lock
        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 0x0002, 0)

        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        if hasattr(user32, "SwitchToThisWindow"):
            user32.SwitchToThisWindow(hwnd, True)
        user32.SetActiveWindow(hwnd)
        if hasattr(user32, "SetFocus"):
            user32.SetFocus(hwnd)
    finally:
        if attached_target:
            user32.AttachThreadInput(current_thread_id, target_thread_id, False)
        if attached_fg:
            user32.AttachThreadInput(current_thread_id, foreground_thread_id, False)

    # Verification polling loop
    poll_ms = min(timeout_ms, 250)
    deadline = time.time() + (poll_ms / 1000.0)
    while time.time() < deadline:
        fg = user32.GetForegroundWindow()
        if fg == hwnd:
            _last_focused_hwnd = int(hwnd)
            time.sleep(0.02)
            return True
        time.sleep(0.02)

    fg = user32.GetForegroundWindow()
    if fg == hwnd or (user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd)):
        _last_focused_hwnd = int(hwnd)
        return True
    return False


def focus_window(hwnd: int, timeout_ms: int = 1500) -> bool:
    """
    Alias for activate_target_window adhering to Interface Contract 2.
    """
    return activate_target_window(hwnd, timeout_ms=timeout_ms)


def get_foreground_window() -> int:
    """Returns HWND of the currently active foreground window."""
    if user32 is None:
        return 0
    fg = user32.GetForegroundWindow()
    if _last_focused_hwnd and user32.IsWindow(_last_focused_hwnd) and user32.IsWindowVisible(_last_focused_hwnd):
        if fg == 0 or fg != _last_focused_hwnd:
            return _last_focused_hwnd
    if fg:
        return int(fg)
    return 0


def is_window_foreground(hwnd: int) -> bool:
    """Checks whether the specified HWND currently possesses foreground focus."""
    if user32 is None:
        return False
    fg = get_foreground_window()
    return bool(fg and int(fg) == int(hwnd))


def is_window_valid(hwnd: int) -> bool:
    """Verifies whether an HWND represents an existing window."""
    if user32 is None:
        return False
    return bool(user32.IsWindow(hwnd))


# ==============================================================================
# 4. COORDINATE GEOMETRY & CLIENT TRANSLATION
# ==============================================================================

def get_window_bounds(hwnd: int) -> Tuple[int, int, int, int]:
    """
    Returns (left, top, right, bottom) outer screen bounds of window.
    """
    if user32 is None:
        return (0, 0, 0, 0)
    rc = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rc))
    return (rc.left, rc.top, rc.right, rc.bottom)


def get_client_bounds(hwnd: int) -> Tuple[int, int, int, int]:
    """
    Returns (screen_left, screen_top, width, height) of the window client area.
    """
    if user32 is None:
        return (0, 0, 0, 0)
    crc = RECT()
    user32.GetClientRect(hwnd, ctypes.byref(crc))
    pt = POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return (pt.x, pt.y, crc.right - crc.left, crc.bottom - crc.top)


def client_to_screen_coords(hwnd: int, client_x: int, client_y: int) -> Tuple[int, int]:
    """
    Translates relative client coordinates (client_x, client_y) to absolute
    physical screen coordinates (screen_x, screen_y).
    """
    if user32 is None:
        return (client_x, client_y)
    pt = POINT(int(client_x), int(client_y))
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return (pt.x, pt.y)


def normalized_to_screen_coords(hwnd: int, norm_u: float, norm_v: float) -> Tuple[int, int]:
    """
    Translates normalized coordinates (0.0 <= norm_u, norm_v <= 1.0) of the client
    area into absolute physical desktop screen coordinates.
    """
    if user32 is None:
        return (0, 0)
    crc = RECT()
    user32.GetClientRect(hwnd, ctypes.byref(crc))
    width = crc.right - crc.left
    height = crc.bottom - crc.top

    cx = int(round(norm_u * width))
    cy = int(round(norm_v * height))
    return client_to_screen_coords(hwnd, cx, cy)


# Provide aliases for engine interface harmonization
get_client_rect = get_client_bounds
client_to_screen = client_to_screen_coords

