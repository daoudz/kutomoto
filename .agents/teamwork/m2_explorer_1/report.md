# Implementation Blueprint: Win32 Automation Core (`src/kutomoto/automation/`)

**Product**: kutomoto — Professional Forms Filling Automation System for Windows OS  
**Copyright**: Copyrights reserved to 90Studio  
**Milestone**: Milestone 2 (Win32 Automation Core & Workflow Engine)  
**Author**: m2_explorer_1  
**Target Architecture**: Microsoft Windows 10 (Build 1703+) / Windows 11 64-bit (x86_64 / AMD64)  
**Document Revision**: 1.0.0 (Production Blueprint)

---

## 1. Executive Summary & Architectural Overview

The Win32 Automation Core (`src/kutomoto/automation/`) forms the foundation of kutomoto's native execution pipeline. Operating in user space via Python's standard `ctypes` library, it interfaces directly with `user32.dll`, `kernel32.dll`, and `shcore.dll`. It provides hardware-level input injection and precise desktop window management without requiring third-party C compilers, Node.js runtimes, or invasive native drivers.

### 1.1 Architecture & Component Boundaries

```
+--------------------------------------------------------------------------------------------------+
|                                    WORKFLOW EXECUTION ENGINE                                     |
|              (runner.py, fsm.py, safety.py - 10 Atomic Handlers & Safety Guardrails)              |
+-------------------------------------------------+------------------------------------------------+
                                                  | Interface Contract 2
                                                  v
+--------------------------------------------------------------------------------------------------+
|                                 kutomoto.automation (__init__.py)                                |
|        Public Facade: send_click, send_text, send_key_press, send_hotkey, clear_field,           |
|                       find_window, focus_window, get_client_bounds, set_process_dpi_awareness     |
+----------------------------------------+---------------------------------------------------------+
                                         |
     +-----------------------------------+-----------------------------------+
     |                                   |                                   |
     v                                   v                                   v
+-----------------------+   +-----------------------+   +------------------------------------------+
|     win32_core.py     |   |    win32_input.py     |   |             win32_window.py              |
+-----------------------+   +-----------------------+   +------------------------------------------+
| - Per-Monitor V2 DPI  |   | - SendInput Injection |   | - EnumWindows & Process Metadata Query   |
| - 40-Byte INPUT ABI   |   | - UTF-16 Surrogates   |   | - Regex Title & Process Executable Match |
| - 64-bit Structs      |   | - VK Navigation Keys  |   | - ClientToScreen & Coordinate Mapping    |
| - Virtual Key Maps    |   | - Safe Hotkey Chords  |   | - AttachThreadInput + SW_RESTORE Focus   |
| - Strict Win32 Types  |   | - Clipboard Fallback  |   | - Window Geometry & Rect Calculations    |
+-----------------------+   +-----------------------+   +------------------------------------------+
```

### 1.2 Core Design Principles
1. **Zero External Binary Dependencies**: Relies exclusively on Python 3.14 standard library (`ctypes`, `wintypes`, `struct`, `re`, `logging`, `time`, `typing`).
2. **Strict 64-bit ABI Compliance**: Explicit 40-byte alignment for `INPUT`, 32-byte for `MOUSEINPUT`, and 24-byte for `KEYBDINPUT`. All Win32 function signatures explicitly declare `argtypes` and `restype` to prevent 64-bit pointer truncation.
3. **Unicode & Layout Immunity**: All character typing utilizes `KEYEVENTF_UNICODE` with UTF-16 surrogate pair decomposition, rendering typing immune to active keyboard layout (QWERTY, AZERTY, Arabic, etc.).
4. **Non-Stuck Key Safety**: Hotkey execution and input operations employ strict `try...finally` blocks with an emergency `release_all_modifiers()` routine to guarantee modifier keys (Ctrl, Shift, Alt, Win) are never left latched.
5. **DPI-Aware 1:1 Physical Coordinate Translation**: Automatically initializes Per-Monitor V2 DPI awareness on startup, preventing DWM bitmap virtualization and ensuring dual-coordinate mappings (normalized $[0.0, 1.0]$ to physical pixels) land with pixel perfection.

---

## 2. Module Blueprint: `src/kutomoto/automation/win32_core.py`

### 2.1 Responsibilities
- Initialize Per-Monitor V2 High-DPI scaling context with fallback ladder.
- Define normative 64-bit Win32 data structures (`INPUT`, `_INPUT_UNION`, `MOUSEINPUT`, `KEYBDINPUT`, `HARDWAREINPUT`, `POINT`, `RECT`).
- Define all Windows virtual key constants (`VK_*`), mouse event flags (`MOUSEEVENTF_*`), and keyboard flags (`KEYEVENTF_*`).
- Expose canonical dictionary `VK_MAP` and resolver function `resolve_virtual_key()`.
- Explicitly declare `argtypes` and `restype` for all Win32 API functions.

### 2.2 Complete Code Blueprint

```python
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
    user32 = ctypes.windll.user32

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
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

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
```

---

## 3. Module Blueprint: `src/kutomoto/automation/win32_input.py`

### 3.1 Responsibilities
- Inject mouse clicks (`send_click`), moves (`send_mouse_move`), and scrolling (`send_mouse_wheel`).
- Inject text via `KEYEVENTF_UNICODE` with UTF-16 surrogate pair decomposition for non-BMP Unicode characters (`send_text`).
- Dispatch navigation and action keys (`send_key_press`).
- Dispatch modifier key combinations safely (`send_hotkey`).
- Clear input fields (`clear_field`).
- Provide an emergency modifier reset (`release_all_modifiers`).
- Provide high-speed clipboard injection fallback for long text blocks (`set_clipboard_text`, `send_text_clipboard`).

### 3.2 Complete Code Blueprint

```python
"""
kutomoto.automation.win32_input
Win32 input injection driver utilizing ctypes SendInput and clipboard fallback.
Copyrights reserved to 90Studio
"""

import ctypes
from ctypes import wintypes
import logging
import struct
import time
from typing import Optional, Sequence, Union

from kutomoto.automation.win32_core import (
    CF_UNICODETEXT,
    GMEM_MOVEABLE,
    INPUT,
    INPUT_KEYBOARD,
    INPUT_MOUSE,
    KEYBDINPUT,
    KEYEVENTF_EXTENDEDKEY,
    KEYEVENTF_KEYUP,
    KEYEVENTF_UNICODE,
    MOUSEEVENTF_LEFTDOWN,
    MOUSEEVENTF_LEFTUP,
    MOUSEEVENTF_MIDDLEDOWN,
    MOUSEEVENTF_MIDDLEUP,
    MOUSEEVENTF_RIGHTDOWN,
    MOUSEEVENTF_RIGHTUP,
    MOUSEEVENTF_WHEEL,
    MOUSEINPUT,
    POINT,
    VK_CONTROL,
    VK_LWIN,
    VK_MENU,
    VK_SHIFT,
    _INPUT_UNION,
    resolve_virtual_key,
)

logger = logging.getLogger("kutomoto.automation.win32_input")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


# ==============================================================================
# 1. CORE LOW-LEVEL INJECTION HELPERS
# ==============================================================================

def send_raw_input(inputs: Sequence[INPUT]) -> int:
    """
    Submits a sequence of INPUT structs to user32.SendInput.
    Returns the count of successfully inserted events.
    """
    if not inputs:
        return 0
    c_inputs = len(inputs)
    arr_type = INPUT * c_inputs
    input_array = arr_type(*inputs)
    sent = user32.SendInput(c_inputs, input_array, ctypes.sizeof(INPUT))
    if sent != c_inputs:
        err = ctypes.GetLastError()
        logger.warning("SendInput partial failure: submitted %d, inserted %d, error=%d", c_inputs, sent, err)
    return sent


# ==============================================================================
# 2. MOUSE INJECTION
# ==============================================================================

def send_mouse_move(x: int, y: int, smooth: bool = False, steps: int = 10, delay_ms: float = 5.0) -> None:
    """
    Moves the cursor to screen coordinates (x, y).
    Supports instant relocation or smooth linear interpolation.
    """
    if not smooth:
        user32.SetCursorPos(int(x), int(y))
        return

    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    start_x, start_y = pt.x, pt.y

    steps = max(1, steps)
    step_delay = max(0.001, delay_ms / 1000.0)

    for i in range(1, steps + 1):
        frac = i / float(steps)
        cur_x = int(round(start_x + (x - start_x) * frac))
        cur_y = int(round(start_y + (y - start_y) * frac))
        user32.SetCursorPos(cur_x, cur_y)
        time.sleep(step_delay)

    user32.SetCursorPos(int(x), int(y))


def send_click(
    x: Optional[int] = None,
    y: Optional[int] = None,
    button: str = "left",
    click_count: int = 1,
    interval_ms: float = 50.0,
    press_duration_ms: float = 15.0,
) -> None:
    """
    Injects mouse click(s) at designated or current cursor position.
    button: 'left', 'right', or 'middle'.
    click_count: 1 (single), 2 (double), 3 (triple).
    """
    if x is not None and y is not None:
        user32.SetCursorPos(int(x), int(y))
        time.sleep(0.01)

    btn = button.strip().lower()
    if btn == "left":
        down_flag, up_flag = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
    elif btn == "right":
        down_flag, up_flag = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
    elif btn == "middle":
        down_flag, up_flag = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
    else:
        raise ValueError(f"Unsupported mouse button: {button}")

    press_sleep = max(0.002, press_duration_ms / 1000.0)
    inter_sleep = max(0.01, interval_ms / 1000.0)

    for i in range(click_count):
        down_input = INPUT(
            type=INPUT_MOUSE,
            union=_INPUT_UNION(mi=MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=down_flag, time=0, dwExtraInfo=0)),
        )
        send_raw_input([down_input])
        time.sleep(press_sleep)

        up_input = INPUT(
            type=INPUT_MOUSE,
            union=_INPUT_UNION(mi=MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=up_flag, time=0, dwExtraInfo=0)),
        )
        send_raw_input([up_input])

        if i < click_count - 1:
            time.sleep(inter_sleep)


def send_mouse_wheel(delta: int, x: Optional[int] = None, y: Optional[int] = None) -> None:
    """
    Injects mouse wheel vertical scroll.
    delta > 0: scroll up, delta < 0: scroll down. Standard notch is 120 units.
    """
    if x is not None and y is not None:
        user32.SetCursorPos(int(x), int(y))
        time.sleep(0.01)

    wheel_input = INPUT(
        type=INPUT_MOUSE,
        union=_INPUT_UNION(
            mi=MOUSEINPUT(dx=0, dy=0, mouseData=int(delta * 120), dwFlags=MOUSEEVENTF_WHEEL, time=0, dwExtraInfo=0)
        ),
    )
    send_raw_input([wheel_input])


# ==============================================================================
# 3. KEYBOARD INJECTION & UNICODE HANDLING
# ==============================================================================

def send_key_press(
    vk_code_or_name: Union[int, str],
    repeat: int = 1,
    delay_ms: float = 20.0,
    press_duration_ms: float = 15.0,
) -> None:
    """
    Injects a physical/virtual key press (down + up) repeated N times.
    """
    vk = resolve_virtual_key(vk_code_or_name)
    press_sleep = max(0.002, press_duration_ms / 1000.0)
    delay_sleep = max(0.002, delay_ms / 1000.0)

    # Determine extended key flag for navigation keys
    extended = vk in (0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E)
    flags_down = KEYEVENTF_EXTENDEDKEY if extended else 0
    flags_up = (KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP) if extended else KEYEVENTF_KEYUP

    for i in range(repeat):
        down = INPUT(
            type=INPUT_KEYBOARD,
            union=_INPUT_UNION(ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags_down, time=0, dwExtraInfo=0)),
        )
        send_raw_input([down])
        time.sleep(press_sleep)

        up = INPUT(
            type=INPUT_KEYBOARD,
            union=_INPUT_UNION(ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags_up, time=0, dwExtraInfo=0)),
        )
        send_raw_input([up])

        if i < repeat - 1:
            time.sleep(delay_sleep)


def send_hotkey(
    modifiers: Sequence[Union[int, str]],
    key: Union[int, str],
    press_duration_ms: float = 20.0,
    settle_delay_ms: float = 20.0,
) -> None:
    """
    Injects a modifier key combination (e.g. ['ctrl', 'shift'], 't').
    Presses modifiers in sequence, taps key, and releases modifiers in reverse.
    Guarantees modifier release via try...finally block.
    """
    mod_vks = [resolve_virtual_key(m) for m in modifiers]
    target_vk = resolve_virtual_key(key)
    press_sleep = max(0.005, press_duration_ms / 1000.0)
    settle_sleep = max(0.005, settle_delay_ms / 1000.0)

    pressed_mods = []
    try:
        # Press all modifiers in order
        for mvk in mod_vks:
            down = INPUT(
                type=INPUT_KEYBOARD,
                union=_INPUT_UNION(ki=KEYBDINPUT(wVk=mvk, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)),
            )
            send_raw_input([down])
            pressed_mods.append(mvk)
            time.sleep(0.005)

        # Tap target key
        key_down = INPUT(
            type=INPUT_KEYBOARD,
            union=_INPUT_UNION(ki=KEYBDINPUT(wVk=target_vk, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)),
        )
        send_raw_input([key_down])
        time.sleep(press_sleep)

        key_up = INPUT(
            type=INPUT_KEYBOARD,
            union=_INPUT_UNION(ki=KEYBDINPUT(wVk=target_vk, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)),
        )
        send_raw_input([key_up])
        time.sleep(0.005)
    finally:
        # Release pressed modifiers in reverse order
        for mvk in reversed(pressed_mods):
            up = INPUT(
                type=INPUT_KEYBOARD,
                union=_INPUT_UNION(ki=KEYBDINPUT(wVk=mvk, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)),
            )
            send_raw_input([up])
            time.sleep(0.005)

    time.sleep(settle_sleep)


def release_all_modifiers() -> None:
    """
    Emergency release of all modifier keys (Ctrl, Shift, Alt, Windows).
    Called by safety abort handlers and exception handlers to prevent stuck keys.
    """
    for vk in (VK_CONTROL, VK_SHIFT, VK_MENU, VK_LWIN):
        up = INPUT(
            type=INPUT_KEYBOARD,
            union=_INPUT_UNION(ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)),
        )
        send_raw_input([up])


def send_text(text: str, delay_ms: float = 25.0, use_clipboard_threshold: int = 0) -> None:
    """
    Types arbitrary Unicode text using KEYEVENTF_UNICODE.
    Decomposes strings into UTF-16 code units (supporting non-BMP surrogate pairs).
    If use_clipboard_threshold > 0 and len(text) >= threshold, delegates to clipboard driver.
    """
    if not text:
        return

    if use_clipboard_threshold > 0 and len(text) >= use_clipboard_threshold:
        if send_text_clipboard(text):
            return
        logger.warning("Clipboard injection fallback failed; falling back to keystroke typing")

    # Encode to UTF-16 Little Endian and extract 16-bit code units
    encoded_bytes = text.encode("utf-16-le")
    num_units = len(encoded_bytes) // 2
    code_units = struct.unpack(f"<{num_units}H", encoded_bytes)

    inter_char_delay = max(0.0, delay_ms / 1000.0)

    for unit in code_units:
        down = INPUT(
            type=INPUT_KEYBOARD,
            union=_INPUT_UNION(ki=KEYBDINPUT(wVk=0, wScan=unit, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=0)),
        )
        up = INPUT(
            type=INPUT_KEYBOARD,
            union=_INPUT_UNION(
                ki=KEYBDINPUT(wVk=0, wScan=unit, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)
            ),
        )
        send_raw_input([down, up])

        if inter_char_delay > 0:
            time.sleep(inter_char_delay)


def clear_field(method: str = "ctrl_a_backspace", delay_ms: float = 30.0) -> None:
    """
    Clears the content of the currently focused input field.
    Default method: Ctrl+A followed by Backspace.
    """
    send_hotkey(["ctrl"], "a")
    time.sleep(max(0.01, delay_ms / 1000.0))
    send_key_press("backspace")

    if method == "double":
        time.sleep(0.01)
        send_key_press("delete")


# ==============================================================================
# 4. UNICODE CLIPBOARD DRIVER & FALLBACK
# ==============================================================================

def set_clipboard_text(text: str, max_retries: int = 5, retry_delay_ms: float = 20.0) -> bool:
    """
    Copies Unicode text to the Windows OS clipboard via pure ctypes Win32 API.
    Handles transient clipboard locks with exponential retry.
    """
    retry_delay = max(0.005, retry_delay_ms / 1000.0)
    opened = False

    for attempt in range(max_retries):
        if user32.OpenClipboard(None):
            opened = True
            break
        time.sleep(retry_delay * (attempt + 1))

    if not opened:
        logger.error("Failed to open Windows clipboard after %d attempts", max_retries)
        return False

    try:
        user32.EmptyClipboard()
        # UTF-16 null-terminated buffer
        raw_data = (text + "\0").encode("utf-16-le")
        data_len = len(raw_data)

        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, data_len)
        if not h_mem:
            logger.error("GlobalAlloc failed for clipboard data (%d bytes)", data_len)
            return False

        ptr = kernel32.GlobalLock(h_mem)
        if not ptr:
            kernel32.GlobalFree(h_mem)
            logger.error("GlobalLock failed for clipboard memory handle")
            return False

        ctypes.memmove(ptr, raw_data, data_len)
        kernel32.GlobalUnlock(h_mem)

        res = user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        if not res:
            kernel32.GlobalFree(h_mem)
            logger.error("SetClipboardData failed: Win32 Error %d", ctypes.GetLastError())
            return False

        return True
    finally:
        user32.CloseClipboard()


def get_clipboard_text() -> Optional[str]:
    """
    Reads the current Unicode text from the Windows OS clipboard.
    """
    if not user32.OpenClipboard(None):
        return None
    try:
        h_mem = user32.GetClipboardData(CF_UNICODETEXT)
        if not h_mem:
            return None
        ptr = kernel32.GlobalLock(h_mem)
        if not ptr:
            return None
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(h_mem)
    finally:
        user32.CloseClipboard()


def send_text_clipboard(text: str, paste_delay_ms: float = 50.0) -> bool:
    """
    Injects text by placing it onto the clipboard and triggering Ctrl+V paste.
    """
    if not set_clipboard_text(text):
        return False
    time.sleep(0.01)
    send_hotkey(["ctrl"], "v")
    time.sleep(max(0.01, paste_delay_ms / 1000.0))
    return True
```

---

## 4. Module Blueprint: `src/kutomoto/automation/win32_window.py`

### 4.1 Responsibilities
- Enumerate open top-level desktop windows (`enumerate_windows`).
- Resolve window properties: HWND, title, class name, PID, executable name, iconic state, visibility, and bounds.
- Find windows using regex pattern matching or exact executable matching (`find_window`, `find_all_windows`).
- Bring target window reliably to foreground using thread-input queue attachment, iconic state restoration, and simulated Alt-key DWM unlock (`activate_target_window`, `focus_window`).
- Translate client coordinates and normalized coordinates $[0.0, 1.0]$ to screen pixels (`client_to_screen_coords`, `normalized_to_screen_coords`).

### 4.2 Complete Code Blueprint

```python
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

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

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
    if not user32.IsWindow(hwnd):
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
    windows = enumerate_windows(visible_only=visible_only, non_empty_title_only=False)
    flags = 0 if case_sensitive else re.IGNORECASE

    for win in windows:
        # Check executable name filter
        if exe_name:
            if case_sensitive:
                if win.executable_name != exe_name:
                    continue
            else:
                if win.executable_name.lower() != exe_name.lower():
                    continue

        # Check title filter
        if title_pattern:
            target_title = win.title if case_sensitive else win.title.lower()
            pattern = title_pattern if case_sensitive else title_pattern.lower()

            if match_mode == "exact":
                if target_title != pattern:
                    continue
            elif match_mode == "contains":
                if pattern not in target_title:
                    continue
            elif match_mode == "startswith":
                if not target_title.startswith(pattern):
                    continue
            else:  # 'regex'
                if not re.search(title_pattern, win.title, flags):
                    continue

        return win

    return None


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
    flags = 0 if case_sensitive else re.IGNORECASE

    for win in windows:
        if exe_name:
            if case_sensitive:
                if win.executable_name != exe_name:
                    continue
            else:
                if win.executable_name.lower() != exe_name.lower():
                    continue

        if title_pattern:
            target_title = win.title if case_sensitive else win.title.lower()
            pattern = title_pattern if case_sensitive else title_pattern.lower()

            if match_mode == "exact":
                if target_title != pattern:
                    continue
            elif match_mode == "contains":
                if pattern not in target_title:
                    continue
            elif match_mode == "startswith":
                if not target_title.startswith(pattern):
                    continue
            else:  # 'regex'
                if not re.search(title_pattern, win.title, flags):
                    continue

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
    if not hwnd or not user32.IsWindow(hwnd):
        logger.error("Invalid window handle: %s", hwnd)
        return False

    if user32.GetForegroundWindow() == hwnd:
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

    attached = False
    if foreground_thread_id != 0 and foreground_thread_id != current_thread_id:
        attached = bool(user32.AttachThreadInput(current_thread_id, foreground_thread_id, True))

    try:
        # Simulated Alt-key tap to unstick DWM foreground lock
        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 0x0002, 0)

        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetActiveWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(current_thread_id, foreground_thread_id, False)

    # Verification polling loop
    deadline = time.time() + (timeout_ms / 1000.0)
    while time.time() < deadline:
        if user32.GetForegroundWindow() == hwnd:
            time.sleep(0.04)
            return True
        time.sleep(0.03)

    return user32.GetForegroundWindow() == hwnd


def focus_window(hwnd: int, timeout_ms: int = 1500) -> bool:
    """
    Alias for activate_target_window adhering to Interface Contract 2.
    """
    return activate_target_window(hwnd, timeout_ms=timeout_ms)


def get_foreground_window() -> int:
    """Returns HWND of the currently active foreground window."""
    return int(user32.GetForegroundWindow())


def is_window_foreground(hwnd: int) -> bool:
    """Checks whether the specified HWND currently possesses foreground focus."""
    return user32.GetForegroundWindow() == hwnd


def is_window_valid(hwnd: int) -> bool:
    """Verifies whether an HWND represents an existing window."""
    return bool(user32.IsWindow(hwnd))


# ==============================================================================
# 4. COORDINATE GEOMETRY & CLIENT TRANSLATION
# ==============================================================================

def get_window_bounds(hwnd: int) -> Tuple[int, int, int, int]:
    """
    Returns (left, top, right, bottom) outer screen bounds of window.
    """
    rc = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rc))
    return (rc.left, rc.top, rc.right, rc.bottom)


def get_client_bounds(hwnd: int) -> Tuple[int, int, int, int]:
    """
    Returns (screen_left, screen_top, width, height) of the window client area.
    """
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
    pt = POINT(int(client_x), int(client_y))
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return (pt.x, pt.y)


def normalized_to_screen_coords(hwnd: int, norm_u: float, norm_v: float) -> Tuple[int, int]:
    """
    Translates normalized coordinates (0.0 <= norm_u, norm_v <= 1.0) of the client
    area into absolute physical desktop screen coordinates.
    """
    crc = RECT()
    user32.GetClientRect(hwnd, ctypes.byref(crc))
    width = crc.right - crc.left
    height = crc.bottom - crc.top

    cx = int(round(norm_u * width))
    cy = int(round(norm_v * height))
    return client_to_screen_coords(hwnd, cx, cy)
```

---

## 5. Unified Package Facade: `src/kutomoto/automation/__init__.py`

```python
"""
kutomoto.automation
Win32 native automation driver for Windows OS.
Copyrights reserved to 90Studio
"""

from kutomoto.automation.win32_core import (
    INPUT,
    MOUSEINPUT,
    KEYBDINPUT,
    HARDWAREINPUT,
    VK_MAP,
    resolve_virtual_key,
    set_process_dpi_awareness,
)
from kutomoto.automation.win32_input import (
    clear_field,
    get_clipboard_text,
    release_all_modifiers,
    send_click,
    send_hotkey,
    send_key_press,
    send_mouse_move,
    send_mouse_wheel,
    send_text,
    send_text_clipboard,
    set_clipboard_text,
)
from kutomoto.automation.win32_window import (
    WindowInfo,
    activate_target_window,
    client_to_screen_coords,
    enumerate_windows,
    find_all_windows,
    find_window,
    focus_window,
    get_client_bounds,
    get_foreground_window,
    get_window_bounds,
    get_window_info,
    is_window_foreground,
    is_window_valid,
    normalized_to_screen_coords,
)

__all__ = [
    # win32_core
    "INPUT",
    "MOUSEINPUT",
    "KEYBDINPUT",
    "HARDWAREINPUT",
    "VK_MAP",
    "resolve_virtual_key",
    "set_process_dpi_awareness",
    # win32_input
    "send_click",
    "send_mouse_move",
    "send_mouse_wheel",
    "send_text",
    "send_key_press",
    "send_hotkey",
    "clear_field",
    "release_all_modifiers",
    "set_clipboard_text",
    "get_clipboard_text",
    "send_text_clipboard",
    # win32_window
    "WindowInfo",
    "enumerate_windows",
    "find_window",
    "find_all_windows",
    "get_window_info",
    "focus_window",
    "activate_target_window",
    "get_foreground_window",
    "is_window_foreground",
    "is_window_valid",
    "get_window_bounds",
    "get_client_bounds",
    "client_to_screen_coords",
    "normalized_to_screen_coords",
]
```

---

## 6. Unit Testing Strategy (`tests/test_win32_driver.py`)

A rigorous testing strategy requires dual-track validation:
1. **Deterministic Mock Unit Tests**: Validates structs, alignment, offsets, fallback ladders, input ordering, Unicode decomposition, and focus attachment logic in any environment (including non-interactive CI/CD).
2. **Empirical Windows OS Live Integration Tests**: Validates real `user32.dll` and `kernel32.dll` execution against a live Tkinter test window on the Windows workstation.

### 6.1 Test Matrix

| Test ID | Test Category | Target Component | Verification Objective |
|---------|---------------|------------------|------------------------|
| **UT-ABI-01** | Struct Layout | `INPUT`, `_INPUT_UNION` | Verify `sizeof(INPUT) == 40`, `union.offset == 8` |
| **UT-ABI-02** | Struct Layout | `MOUSEINPUT` | Verify `sizeof(MOUSEINPUT) == 32`, `dwFlags.offset == 12` |
| **UT-ABI-03** | Struct Layout | `KEYBDINPUT` | Verify `sizeof(KEYBDINPUT) == 24`, `wScan.offset == 2` |
| **UT-DPI-01** | DPI Initialization | `set_process_dpi_awareness` | Returns valid mode on live Windows OS |
| **UT-DPI-02** | DPI Fallback Ladder | `set_process_dpi_awareness` | Falls back to V1 -> shcore -> SetProcessDPIAware -> UNAWARE when mocked |
| **UT-INP-01** | Mouse Injection | `send_click` | Dispatches correct button down/up flags and honors click counts |
| **UT-INP-02** | Mouse Move | `send_mouse_move` | Direct and smooth coordinate interpolation |
| **UT-INP-03** | Key Press | `send_key_press` | Maps string aliases (`"tab"`, `"enter"`) to VK codes and dispatches down/up |
| **UT-INP-04** | Hotkey Ordering | `send_hotkey` | Down order: `[ctrl, shift, a]`; Up order: `[a, shift, ctrl]` |
| **UT-INP-05** | Hotkey Safety | `send_hotkey` | Releases modifiers in `finally` even if key press raises exception |
| **UT-INP-06** | Unicode BMP | `send_text` | Injects UTF-16 code units with `KEYEVENTF_UNICODE` |
| **UT-INP-07** | Unicode Non-BMP | `send_text` | Decomposes emoji `\U0001F600` into surrogate pair `0xD83D, 0xDE00` |
| **UT-INP-08** | Field Clearing | `clear_field` | Dispatches `Ctrl+A` followed by `Backspace` |
| **UT-INP-09** | Clipboard Fallback | `set_clipboard_text` | Writes UTF-16 to clipboard; reads back identical string |
| **UT-WIN-01** | Window Enum Mock | `enumerate_windows` | Correctly filters by title regex, executable name, visibility |
| **UT-WIN-02** | Coordinate Math | `normalized_to_screen_coords` | Translates $(u, v)$ client ratio to physical screen pixels |
| **UT-WIN-03** | Focus Protocol | `activate_target_window` | Simulates iconic restore, Alt tap, `AttachThreadInput`, `SetForegroundWindow` |
| **IT-LIVE-01** | Live Integration | Tkinter Window | Enumerate, focus, and query geometry against live Tkinter window on Windows |

### 6.2 Key Test Code Implementation Outline

```python
"""
tests/test_win32_driver.py
Unit and integration tests for Win32 automation core.
Copyrights reserved to 90Studio
"""

import ctypes
import unittest
from unittest.mock import MagicMock, patch
import pytest

from kutomoto.automation.win32_core import (
    INPUT,
    MOUSEINPUT,
    KEYBDINPUT,
    HARDWAREINPUT,
    _INPUT_UNION,
    VK_MAP,
    resolve_virtual_key,
    set_process_dpi_awareness,
    KEYEVENTF_UNICODE,
    KEYEVENTF_KEYUP,
)
from kutomoto.automation.win32_input import (
    send_click,
    send_text,
    send_key_press,
    send_hotkey,
    clear_field,
    release_all_modifiers,
    set_clipboard_text,
    get_clipboard_text,
)
from kutomoto.automation.win32_window import (
    WindowInfo,
    find_window,
    normalized_to_screen_coords,
    activate_target_window,
)


# --- 1. ABI & STRUCT ALIGNMENT TESTS ---

def test_win32_input_struct_alignment():
    assert ctypes.sizeof(INPUT) == 40
    assert ctypes.sizeof(MOUSEINPUT) == 32
    assert ctypes.sizeof(KEYBDINPUT) == 24
    assert ctypes.sizeof(HARDWAREINPUT) == 8
    assert ctypes.sizeof(_INPUT_UNION) == 32
    assert INPUT.type.offset == 0
    assert INPUT.union.offset == 8


# --- 2. DPI FALLBACK LADDER TEST ---

def test_dpi_awareness_fallback_cascade():
    with patch("ctypes.windll.user32.SetProcessDpiAwarenessContext", side_effect=OSError), \
         patch("ctypes.windll.shcore.SetProcessDpiAwareness", return_value=0):
        mode = set_process_dpi_awareness()
        assert mode == "SHCORE_PER_MONITOR"


# --- 3. INPUT INJECTION & UNICODE SURROGATE TESTS ---

def test_unicode_surrogate_pair_decomposition():
    captured = []

    def mock_send_input(c_inputs, p_inputs, cb_size):
        assert cb_size == 40
        for i in range(c_inputs):
            ki = p_inputs[i].union.ki
            captured.append((ki.wScan, ki.dwFlags))
        return c_inputs

    with patch("ctypes.windll.user32.SendInput", side_effect=mock_send_input):
        # Injects emoji 😀 (U+1F600) -> UTF-16 surrogates: 0xD83D, 0xDE00
        send_text("😀", delay_ms=0)

    assert len(captured) == 4  # (high down, high up, low down, low up)
    assert captured[0] == (0xD83D, KEYEVENTF_UNICODE)
    assert captured[1] == (0xD83D, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)
    assert captured[2] == (0xDE00, KEYEVENTF_UNICODE)
    assert captured[3] == (0xDE00, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)


def test_hotkey_ordering_and_reverse_release():
    events = []

    def mock_send_input(c_inputs, p_inputs, cb_size):
        for i in range(c_inputs):
            ki = p_inputs[i].union.ki
            events.append((ki.wVk, ki.dwFlags))
        return c_inputs

    with patch("ctypes.windll.user32.SendInput", side_effect=mock_send_input):
        send_hotkey(["ctrl", "shift"], "a", press_duration_ms=0, settle_delay_ms=0)

    # Sequence: Ctrl down, Shift down, A down, A up, Shift up, Ctrl up
    expected_vks = [
        (VK_MAP["ctrl"], 0),
        (VK_MAP["shift"], 0),
        (VK_MAP["a"], 0),
        (VK_MAP["a"], KEYEVENTF_KEYUP),
        (VK_MAP["shift"], KEYEVENTF_KEYUP),
        (VK_MAP["ctrl"], KEYEVENTF_KEYUP),
    ]
    assert events == expected_vks


# --- 4. LIVE TKINTER INTEGRATION TEST ---

def test_live_tkinter_window_automation():
    import tkinter as tk

    root = tk.Tk()
    root.title("KutomotoTestLiveWindow")
    root.geometry("400x300+100+100")
    root.update()

    try:
        win = find_window("KutomotoTestLiveWindow")
        assert win is not None
        assert "KutomotoTestLiveWindow" in win.title
        assert win.hwnd != 0

        # Verify client coordinate translation
        sx, sy = normalized_to_screen_coords(win.hwnd, 0.5, 0.5)
        assert sx > 100
        assert sy > 100

        # Verify focus
        focused = activate_target_window(win.hwnd, timeout_ms=500)
        assert focused is True
    finally:
        root.destroy()
```

---

## 7. Traceability Matrix & Compliance Baseline

| Feature / Edge Case | Requirement Reference | Implementation Component | Verification Method |
|---|---|---|---|
| **F05** (Win32 DPI Input Core) | SPEC §6.1, §6.2 | `win32_core.set_process_dpi_awareness`, `INPUT` 40-byte alignment | `test_win32_input_struct_alignment`, `test_dpi_awareness_fallback_cascade` |
| **F06** (Unicode & Key Typing) | SPEC §6.3 | `win32_input.send_text` (`KEYEVENTF_UNICODE`, UTF-16 surrogates), `send_key_press` | `test_unicode_surrogate_pair_decomposition` |
| **F07** (Focus Activation Core) | SPEC §6.4 | `win32_window.activate_target_window` (`AttachThreadInput`, Alt tap, `ShowWindow`) | `test_live_tkinter_window_automation` |
| **F08** (Window Enumeration) | SPEC §6.5 | `win32_window.enumerate_windows`, `find_window` (regex & executable) | `test_live_tkinter_window_automation` |
| **E05** (Keystroke Loss / Clipboard) | SPEC §3 (E05) | `win32_input.set_clipboard_text`, `send_text_clipboard` (`CF_UNICODETEXT`) | Clipboard read/write roundtrip test |
| **E08** (Multi-Monitor Coordinate Drift)| SPEC §3 (E08) | `win32_window.normalized_to_screen_coords`, `ClientToScreen` | Coordinate calculation test |
| **E10** (DWM Focus Lock) | SPEC §3 (E10) | `win32_window.activate_target_window` (Alt tap + `AttachThreadInput`) | Simulated foreground lock test |
| **90Studio Branding** | SPEC §1.4 | Module docstrings: `"Copyrights reserved to 90Studio"` | Header assertion in test suite |

---

## 8. Implementation Readiness Checklist for Milestone 2

1. **`src/kutomoto/automation/win32_core.py`**:
   - [x] Defined all structures (`INPUT`, `_INPUT_UNION`, `MOUSEINPUT`, `KEYBDINPUT`, `HARDWAREINPUT`, `POINT`, `RECT`).
   - [x] Asserted strict 40-byte 64-bit alignment and union offset.
   - [x] Implemented Per-Monitor V2 DPI fallback ladder.
   - [x] Declared explicit `argtypes` and `restype` for all Win32 API functions.
   - [x] Populated complete `VK_MAP` and `resolve_virtual_key()`.

2. **`src/kutomoto/automation/win32_input.py`**:
   - [x] Implemented `send_click` with single/double/triple clicks and left/right/middle buttons.
   - [x] Implemented `send_mouse_move` (instant and smooth interpolation) and `send_mouse_wheel`.
   - [x] Implemented `send_text` with UTF-16 surrogate pairs for non-BMP characters and clipboard threshold.
   - [x] Implemented `send_key_press` and `send_hotkey` with reverse modifier release in `finally`.
   - [x] Implemented `clear_field` (Ctrl+A -> Backspace).
   - [x] Implemented `release_all_modifiers()` for safety emergency aborts.
   - [x] Implemented pure ctypes clipboard driver (`CF_UNICODETEXT`).

3. **`src/kutomoto/automation/win32_window.py`**:
   - [x] Implemented `enumerate_windows` collecting `WindowInfo` (HWND, title, PID, exe, geometry).
   - [x] Implemented unprivileged process inspection via `QueryFullProcessImageNameW`.
   - [x] Implemented `find_window` and `find_all_windows` with regex and executable filtering.
   - [x] Implemented `activate_target_window` / `focus_window` with thread attachment and Alt tap.
   - [x] Implemented `client_to_screen_coords` and `normalized_to_screen_coords`.

4. **`src/kutomoto/automation/__init__.py`**:
   - [x] Re-exported all interface contract functions.

5. **`tests/test_win32_driver.py`**:
   - [x] Designed struct size & alignment tests.
   - [x] Designed DPI fallback tests.
   - [x] Designed mock input injection tests (Unicode, surrogate pairs, hotkeys, modifier safety).
   - [x] Designed live Tkinter window integration test.
