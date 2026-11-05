"""
kutomoto.automation.win32_core
Win32 ctypes core constants, data structures, and DPI awareness context.
Copyrights reserved to 90Studio
"""

import ctypes
from ctypes import wintypes
import logging
from typing import Dict, Union

logger = logging.getLogger("kutomoto.automation.win32_core")

byref = ctypes.byref
try:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
except (AttributeError, OSError):
    user32 = None  # type: ignore
    kernel32 = None  # type: ignore

# ==============================================================================
# 1. 64-BIT ABI TYPE DEFINITIONS & STRUCTURES
# ==============================================================================

ULONG_PTR = ctypes.c_size_t

# Win32 INPUT Type Identifiers
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

# Win32 Mouse Event Flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000
MOUSEEVENTF_MOVE_NOCOALESCE = 0x2000
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_ABSOLUTE = 0x8000

# Win32 Keyboard Event Flags
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

# Win32 Window Display State Constants
SW_HIDE = 0
SW_NORMAL = 1
SW_SHOWMINIMIZED = 2
SW_MAXIMIZE = 3
SW_SHOWNOACTIVATE = 4
SW_SHOW = 5
SW_MINIMIZE = 6
SW_SHOWMINNOACTIVE = 7
SW_SHOWNA = 8
SW_RESTORE = 9

# Win32 Clipboard Formats & Memory Flags
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    ]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]


# Validate 64-bit ABI memory alignment at module import time
assert ctypes.sizeof(MOUSEINPUT) == 32, f"MOUSEINPUT alignment failure: expected 32, got {ctypes.sizeof(MOUSEINPUT)}"
assert ctypes.sizeof(KEYBDINPUT) == 24, f"KEYBDINPUT alignment failure: expected 24, got {ctypes.sizeof(KEYBDINPUT)}"
assert ctypes.sizeof(HARDWAREINPUT) == 8, f"HARDWAREINPUT alignment failure: expected 8, got {ctypes.sizeof(HARDWAREINPUT)}"
assert ctypes.sizeof(_INPUT_UNION) == 32, f"_INPUT_UNION alignment failure: expected 32, got {ctypes.sizeof(_INPUT_UNION)}"
assert ctypes.sizeof(INPUT) == 40, f"Critical 64-bit ABI failure: INPUT struct must be 40 bytes, got {ctypes.sizeof(INPUT)}"
assert INPUT.union.offset == 8, f"INPUT union offset must be 8, got {INPUT.union.offset}"


# ==============================================================================
# 2. VIRTUAL KEY CONSTANTS & NORMALIZATION MAP
# ==============================================================================

VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_CANCEL = 0x03
VK_MBUTTON = 0x04
VK_BACK = 0x08
VK_TAB = 0x09
VK_CLEAR = 0x0C
VK_RETURN = 0x0D
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_PAUSE = 0x13
VK_CAPITAL = 0x14
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_PRIOR = 0x21  # Page Up
VK_NEXT = 0x22  # Page Down
VK_END = 0x23
VK_HOME = 0x24
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_SELECT = 0x29
VK_PRINT = 0x2A
VK_EXECUTE = 0x2B
VK_SNAPSHOT = 0x2C  # PrintScreen
VK_INSERT = 0x2D
VK_DELETE = 0x2E
VK_HELP = 0x2F

VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_APPS = 0x5D

VK_NUMPAD0 = 0x60
VK_NUMPAD1 = 0x61
VK_NUMPAD2 = 0x62
VK_NUMPAD3 = 0x63
VK_NUMPAD4 = 0x64
VK_NUMPAD5 = 0x65
VK_NUMPAD6 = 0x66
VK_NUMPAD7 = 0x67
VK_NUMPAD8 = 0x68
VK_NUMPAD9 = 0x69
VK_MULTIPLY = 0x6A
VK_ADD = 0x6B
VK_SEPARATOR = 0x6C
VK_SUBTRACT = 0x6D
VK_DECIMAL = 0x6E
VK_DIVIDE = 0x6F

VK_F1 = 0x70
VK_F2 = 0x71
VK_F3 = 0x72
VK_F4 = 0x73
VK_F5 = 0x74
VK_F6 = 0x75
VK_F7 = 0x76
VK_F8 = 0x77
VK_F9 = 0x78
VK_F10 = 0x79
VK_F11 = 0x7A
VK_F12 = 0x7B

VK_NUMLOCK = 0x90
VK_SCROLL = 0x91

VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LMENU = 0xA4
VK_RMENU = 0xA5

VK_MAP: Dict[str, int] = {
    # Navigation & control
    "tab": VK_TAB,
    "enter": VK_RETURN,
    "return": VK_RETURN,
    "esc": VK_ESCAPE,
    "escape": VK_ESCAPE,
    "backspace": VK_BACK,
    "back": VK_BACK,
    "delete": VK_DELETE,
    "del": VK_DELETE,
    "space": VK_SPACE,
    "spacebar": VK_SPACE,
    "insert": VK_INSERT,
    "home": VK_HOME,
    "end": VK_END,
    "pageup": VK_PRIOR,
    "pgup": VK_PRIOR,
    "pagedown": VK_NEXT,
    "pgdn": VK_NEXT,
    "up": VK_UP,
    "down": VK_DOWN,
    "left": VK_LEFT,
    "right": VK_RIGHT,
    # Modifiers
    "ctrl": VK_CONTROL,
    "control": VK_CONTROL,
    "shift": VK_SHIFT,
    "alt": VK_MENU,
    "menu": VK_MENU,
    "win": VK_LWIN,
    "windows": VK_LWIN,
    "lwin": VK_LWIN,
    "rwin": VK_RWIN,
    # Function keys
    "f1": VK_F1, "f2": VK_F2, "f3": VK_F3, "f4": VK_F4,
    "f5": VK_F5, "f6": VK_F6, "f7": VK_F7, "f8": VK_F8,
    "f9": VK_F9, "f10": VK_F10, "f11": VK_F11, "f12": VK_F12,
    # Numpad
    "numpad0": VK_NUMPAD0, "numpad1": VK_NUMPAD1, "numpad2": VK_NUMPAD2,
    "numpad3": VK_NUMPAD3, "numpad4": VK_NUMPAD4, "numpad5": VK_NUMPAD5,
    "numpad6": VK_NUMPAD6, "numpad7": VK_NUMPAD7, "numpad8": VK_NUMPAD8,
    "numpad9": VK_NUMPAD9,
    "add": VK_ADD, "subtract": VK_SUBTRACT, "multiply": VK_MULTIPLY, "divide": VK_DIVIDE,
}

# Add standard letters a-z to VK_MAP
for _ch in range(ord("a"), ord("z") + 1):
    VK_MAP[chr(_ch)] = ord(chr(_ch).upper())

# Add numbers 0-9 to VK_MAP
for _d in range(ord("0"), ord("9") + 1):
    VK_MAP[chr(_d)] = _d


def resolve_virtual_key(key: Union[int, str]) -> int:
    """
    Normalizes and resolves a virtual key name or integer code to a Win32 VK code.
    Raises ValueError if key cannot be resolved.
    """
    if isinstance(key, int):
        return key

    key_clean = str(key).strip().lower()
    if key_clean in VK_MAP:
        return VK_MAP[key_clean]

    if len(key_clean) == 1:
        return ord(key_clean.upper())

    raise ValueError(f"Unrecognized virtual key identifier: {key}")


# ==============================================================================
# 3. HIGH-DPI SCALING LADDER
# ==============================================================================

DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE = ctypes.c_void_p(-3)
PROCESS_PER_MONITOR_DPI_AWARE = 2


def set_process_dpi_awareness() -> str:
    """
    Enforces Per-Monitor V2 DPI awareness on the running Kutomoto process.
    Returns the successfully applied awareness mode string:
    'PER_MONITOR_V2', 'PER_MONITOR_V1', 'SHCORE_PER_MONITOR', 'SYSTEM_AWARE', or 'UNAWARE'.
    """
    try:
        user32 = ctypes.windll.user32
    except (AttributeError, OSError):
        return "UNAWARE"

    # 1. Primary: Windows 10 Creators Update (Build 1703+) & Windows 11
    try:
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
        if user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2):
            logger.info("DPI Awareness set: Per-Monitor V2 (-4)")
            return "PER_MONITOR_V2"
        elif user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE):
            logger.info("DPI Awareness set: Per-Monitor V1 (-3)")
            return "PER_MONITOR_V1"
        else:
            err = ctypes.GetLastError()
            # If error is ERROR_ACCESS_DENIED (5), awareness is already fixed for process
            if err == 5:
                logger.info("DPI Awareness was already locked for process")
                return "ALREADY_SET"
    except (AttributeError, OSError) as ex:
        logger.debug("SetProcessDpiAwarenessContext unavailable: %s", ex)

    # 2. Secondary: Windows 8.1 / Windows 10 pre-1703 via shcore.dll
    try:
        shcore = ctypes.windll.shcore
        shcore.SetProcessDpiAwareness.argtypes = [ctypes.c_int]
        shcore.SetProcessDpiAwareness.restype = ctypes.HRESULT
        if shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE) == 0:
            logger.info("DPI Awareness set: shcore PROCESS_PER_MONITOR_DPI_AWARE")
            return "SHCORE_PER_MONITOR"
    except (AttributeError, OSError) as ex:
        logger.debug("shcore.SetProcessDpiAwareness unavailable: %s", ex)

    # 3. Tertiary: Legacy Windows Vista / 7
    try:
        user32.SetProcessDPIAware.argtypes = []
        user32.SetProcessDPIAware.restype = wintypes.BOOL
        if user32.SetProcessDPIAware():
            logger.info("DPI Awareness set: user32 SetProcessDPIAware")
            return "SYSTEM_AWARE"
    except Exception as ex:
        logger.error("Failed to set any DPI awareness mode: %s", ex)

    return "UNAWARE"


# ==============================================================================
# 4. WIN32 API FUNCTION SIGNATURE DECLARATIONS
# ==============================================================================

def init_win32_signatures() -> None:
    """
    Explicitly binds argtypes and restype for all referenced user32 and kernel32
    APIs to eliminate 64-bit pointer truncation and access violations.
    """
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
    except (AttributeError, OSError):
        return

    # SendInput
    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT

    # Cursor & Point
    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user32.SetCursorPos.restype = wintypes.BOOL
    user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
    user32.GetCursorPos.restype = wintypes.BOOL

    # Window Coordinates
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
    user32.ClientToScreen.restype = wintypes.BOOL
    user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
    user32.ScreenToClient.restype = wintypes.BOOL
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
    user32.GetClientRect.restype = wintypes.BOOL
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL

    # Window Management & Focus
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.SetActiveWindow.argtypes = [wintypes.HWND]
    user32.SetActiveWindow.restype = wintypes.HWND
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.BringWindowToTop.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsWindow.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL

    # Thread Attachment
    user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    user32.AttachThreadInput.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    kernel32.GetCurrentThreadId.argtypes = []
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD

    # Window Enumeration & Text
    user32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int

    # Process Inspection
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = wintypes.BOOL

    # Clipboard API
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = ctypes.c_void_p

    # Global Memory
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.restype = ctypes.c_void_p


# Execute signature binding immediately upon module import
init_win32_signatures()
