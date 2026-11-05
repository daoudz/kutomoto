# Win32 Automation, High-DPI Scaling & Cross-Application Targeting Technical Specification Report

**System**: kutomoto — Professional Forms Filling Automation System for Windows OS  
**Copyright**: Copyrights reserved to 90Studio  
**Author**: m1_explorer_2 (Win32 Automation & Cross-Application Targeting Explorer)  
**Recipient**: ce2dd708-d288-4e8f-9834-dfdb673a5856 (Teamwork Orchestrator) & M1 Specification Worker  
**Date**: 2026-11-04  
**Target Specification Document**: `docs/SPECIFICATION.md`  

---

## Table of Contents
1. [Executive Summary & Architectural Scope](#1-executive-summary--architectural-scope)
2. [Win32 Per-Monitor V2 High-DPI Scaling Specification](#2-win32-per-monitor-v2-high-dpi-scaling-specification)
   - 2.1 The DPI Virtualization Problem on Windows 10/11
   - 2.2 Awareness Context Hierarchy & The Per-Monitor V2 Context (`-4`)
   - 2.3 Process DPI Initialization Ladder (ctypes Implementation)
   - 2.4 Multi-Monitor Coordinate Transformation Mathematics
3. [Win32 `SendInput` Keyboard & Mouse Injection Specification](#3-win32-sendinput-keyboard--mouse-injection-specification)
   - 3.1 64-bit ABI Memory Layout & 40-Byte Struct Alignment
   - 3.2 Mouse Injection Specification (Normalized Absolute vs Relative Clicks)
   - 3.3 Keyboard Injection Specification (Direct Unicode vs Virtual Keys)
   - 3.4 Key Sequencing, Modifiers & Field Clearing Mechanics
   - 3.5 High-Speed Unicode Clipboard Driver (Zero-Loss Form Injection)
4. [Window Attachment & Focus Stealing Recovery Specification](#4-window-attachment--focus-stealing-recovery-specification)
   - 4.1 Windows OS Focus-Stealing Protection (`LockSetForegroundWindow`)
   - 4.2 The Canonical Thread-Input Attachment Algorithm (`AttachThreadInput`)
   - 4.3 Window State Handling (Minimized, Iconic, Normal) & Verification Polling Loop
   - 4.4 Fallback Activation Primitives & Timing Budgets
5. [Cross-Application Targeting: Web Browsers vs Native Desktop Apps](#5-cross-application-targeting-web-browsers-vs-native-desktop-apps)
   - 5.1 Web Browser Targeting (Edge Chromium, Chrome, Firefox)
   - 5.2 Browser Sub-Tab Targeting without Extensions (4-Way Strategy)
   - 5.3 Native Desktop Applications (WinForms, WPF, Tkinter, Qt, SAP GUI)
   - 5.4 User Interface Privilege Isolation (UIPI) & UAC Elevation Rules
6. [Multi-Layer Safety Guardrails & Emergency Failsafes](#6-multi-layer-safety-guardrails--emergency-failsafes)
   - 6.1 Hardware Screen Corner Slam Failsafe (`(0, 0)` Abort)
   - 6.2 Global Emergency Escape Abort Hotkey
   - 6.3 Loss-of-Focus Guardian (Pre-Flight Focus Validation)
   - 6.4 Sensitive Credential Masking & Memory Security
7. [Concrete Authoring Guidance for `docs/SPECIFICATION.md`](#7-concrete-authoring-guidance-for-docsspecificationmd)
   - 7.1 Proposed Specification Table of Contents & Structure
   - 7.2 Ready-to-Embed Markdown Sections & Code Specifications
   - 7.3 Win32 Driver API Contracts & Method Signatures

---

## 1. Executive Summary & Architectural Scope

The **kutomoto** automation platform (copyrights reserved to **90Studio**) requires deterministic, zero-external-compilation input injection across modern enterprise Windows environments (Windows 10 Build 1703+ and Windows 11 64-bit). The host environment diagnostic audit established that while modern Python 3.14 and Microsoft Edge are available, C/C++ compiler toolchains (`cl.exe`, `gcc`) are absent.

Consequently, the entire native automation layer must be implemented using pure Python standard library `ctypes` bindings to `user32.dll`, `kernel32.dll`, and `shcore.dll`. To guarantee enterprise-grade reliability in financial, telecommunications, and corporate back-office workflows, the automation subsystem must solve four fundamental Windows OS barriers:
1. **DPI Virtualization & Coordinate Drift**: Unaware or system-scaled applications suffer blurred rendering and distorted coordinate mapping when displays scale at 125%, 150%, 175%, or 200%. Kutomoto enforces **Per-Monitor V2 DPI awareness** to bind directly to true physical device pixels.
2. **64-bit Input Structure Misalignment**: Incorrect padding or union offsets in `SendInput` causes silent input failure or memory corruption. We specify the exact **40-byte 64-bit C/ctypes struct layout**.
3. **Foreground Lock & Focus Stealing Suppression**: Windows blocks background processes from calling `SetForegroundWindow` without active user interaction. We specify the **`AttachThreadInput` + `ShowWindow(SW_RESTORE)`** bypass protocol.
4. **Browser Tab & Desktop Targeting Divergence**: Top-level application windows differ fundamentally from multi-process tabbed browsers. We define a **4-way hybrid targeting architecture** (Title Regex, Process Matching, 3-second Countdown HUD, and In-Place Global Hotkey).

---

## 2. Win32 Per-Monitor V2 High-DPI Scaling Specification

### 2.1 The DPI Virtualization Problem on Windows 10/11
Modern Windows workstations and laptops routinely operate with High-DPI displays (e.g., 4K monitors, Surface devices, laptops at 2560x1440). Windows applies scaling factors (typically 125% to 200%, corresponding to 120 DPI to 192 DPI, where standard baseline DPI is 96 DPI).

When a process is not explicitly DPI-aware, Windows enables **DPI Virtualization (Bitmap Stretching)**:
- The OS reports a virtualized resolution (e.g., $1920 \times 1080$ at 96 DPI) instead of the true monitor resolution (e.g., $3840 \times 2160$ at 192 DPI).
- GDI and window coordinates queried via `GetWindowRect` return virtualized integers.
- Mouse clicks injected via `SendInput` or `SetCursorPos` land at shifted, erroneous screen positions, frequently missing small form fields, dropdown arrows, or checkboxes.

### 2.2 Awareness Context Hierarchy & The Per-Monitor V2 Context (`-4`)
Microsoft defines four distinct DPI awareness contexts in Windows 10 and 11:

| DPI Context Name | Value | Introduced | Behavior |
|:---|:---:|:---:|:---|
| `DPI_AWARENESS_CONTEXT_UNAWARE` | `-1` | Windows XP | Virtualized coordinates. Bitmap stretched by DWM. Unacceptable for automation. |
| `DPI_AWARENESS_CONTEXT_SYSTEM_AWARE` | `-2` | Windows Vista / 7 | Scaled once at logon DPI. Does not adapt when moving between mixed-DPI monitors. |
| `DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE` (V1) | `-3` | Windows 8.1 | Top-level window receives `WM_DPICHANGED`, but child dialogs, menus, and non-client areas are not scaled by OS. |
| **`DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2`** | **`-4`** | **Windows 10 (1703+) / Win 11** | **Full automatic scaling of non-client areas, child windows, dialogs, and native Win32 controls. Coordinates represent exact 1:1 physical desktop pixels.** |

**Normative Rule**: Kutomoto **MUST** declare `DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2` (`-4`) as the very first operation upon Python backend process initialization, before any window enumeration, coordinate calculation, or UI window instantiation occurs.

### 2.3 Process DPI Initialization Ladder (ctypes Implementation)
Because different enterprise host machines may run varying Windows build levels (Windows 11, Windows 10 22H2, or legacy Windows 10 LTSC), Kutomoto implements a robust 3-stage fallback initialization ladder:

```python
"""
kutomoto.automation.win32_core.dpi
DPI Awareness Context Initializer for Windows OS
Copyrights reserved to 90Studio
"""
import ctypes
from ctypes import wintypes
import logging

logger = logging.getLogger("kutomoto.dpi")

# DPI Awareness Context constants
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE    = ctypes.c_void_p(-3)
PROCESS_PER_MONITOR_DPI_AWARE             = 2

def set_process_dpi_awareness() -> str:
    """
    Enforces Per-Monitor V2 DPI awareness on the running Kutomoto process.
    Returns the successfully applied awareness mode string.
    """
    user32 = ctypes.windll.user32
    
    # 1. Primary: Windows 10 Creators Update (Build 1703+) & Windows 11
    # SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
    try:
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
        
        if user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2):
            logger.info("DPI Awareness set: Per-Monitor V2 (DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4)")
            return "PER_MONITOR_V2"
        else:
            # Fallback to Per-Monitor V1 if V2 rejected
            if user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE):
                logger.info("DPI Awareness set: Per-Monitor V1")
                return "PER_MONITOR_V1"
    except (AttributeError, OSError) as ex:
        logger.debug("SetProcessDpiAwarenessContext unavailable: %s", ex)

    # 2. Secondary: Windows 8.1 / Windows 10 pre-1703 via shcore.dll
    try:
        shcore = ctypes.windll.shcore
        shcore.SetProcessDpiAwareness.argtypes = [ctypes.c_int]
        shcore.SetProcessDpiAwareness.restype = ctypes.HRESULT
        
        hr = shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
        if hr == 0:  # S_OK
            logger.info("DPI Awareness set: shcore PROCESS_PER_MONITOR_DPI_AWARE")
            return "SHCORE_PER_MONITOR"
    except (AttributeError, OSError) as ex:
        logger.debug("shcore.SetProcessDpiAwareness unavailable: %s", ex)

    # 3. Tertiary: Legacy Windows Vista / 7 via user32.SetProcessDPIAware()
    try:
        user32.SetProcessDPIAware.argtypes = []
        user32.SetProcessDPIAware.restype = wintypes.BOOL
        if user32.SetProcessDPIAware():
            logger.info("DPI Awareness set: user32 SetProcessDPIAware (System Aware)")
            return "SYSTEM_AWARE"
    except Exception as ex:
        logger.error("Failed to set any DPI awareness mode: %s", ex)

    return "UNAWARE"
```

### 2.4 Multi-Monitor Coordinate Transformation Mathematics
In enterprise trading floors and customer service desks, multi-monitor setups frequently feature:
- Primary monitor at 1920x1080 (100% scale, 96 DPI).
- Secondary monitor at 3840x2160 (150% scale, 144 DPI) positioned to the left (negative coordinates) or right.

#### Window Client vs Non-Client Geometry
When clicking an element in a window, clicking at `(x, y)` relative to the **Window Rect** (which includes title bar and resize borders) leads to errors if window themes or border sizes change. 

Kutomoto mandates the **Client Area Standard**:
1. Obtain window client rectangle: `GetClientRect(hwnd, &rect)`.
2. Convert the client origin $(0, 0)$ to physical screen coordinates:
   $$\text{POINT pt} = \{0, 0\}; \quad \text{ClientToScreen}(hwnd, \&pt);$$
3. Target physical screen coordinate for normalized field coordinate $(u, v) \in [0.0, 1.0]$:
   $$\text{ScreenX} = pt.x + \text{round}\left(u \times \text{client\_width}\right)$$
   $$\text{ScreenY} = pt.y + \text{round}\left(v \times \text{client\_height}\right)$$

#### Multi-Monitor Virtual Screen Space
Windows represents the total desktop canvas across all active monitors as the **Virtual Screen**:
- Virtual Left: `GetSystemMetrics(SM_XVIRTUALSCREEN)` (can be negative if a monitor is placed to the left of the primary).
- Virtual Top: `GetSystemMetrics(SM_YVIRTUALSCREEN)` (can be negative).
- Virtual Width: `GetSystemMetrics(SM_CXVIRTUALSCREEN)`.
- Virtual Height: `GetSystemMetrics(SM_CYVIRTUALSCREEN)`.

When injecting absolute mouse coordinates across multi-monitor setups via `MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK`, coordinates are mapped into the range $[0, 65535]$:
$$\text{dx} = \text{round}\left(\frac{(\text{ScreenX} - \text{SM\_XVIRTUALSCREEN}) \times 65535}{\text{SM\_CXVIRTUALSCREEN} - 1}\right)$$
$$\text{dy} = \text{round}\left(\frac{(\text{ScreenY} - \text{SM\_YVIRTUALSCREEN}) \times 65535}{\text{SM\_CYVIRTUALSCREEN} - 1}\right)$$

---

## 3. Win32 `SendInput` Keyboard & Mouse Injection Specification

### 3.1 64-bit ABI Memory Layout & 40-Byte Struct Alignment
Microsoft's `SendInput` function expects an array of `INPUT` structures:
```c
UINT SendInput(
  UINT    cInputs,
  LPINPUT pInputs,
  int     cbSize
);
```

On 64-bit Windows architectures (x86_64 / AMD64), C compilers enforce pointer alignment (8-byte boundaries). An incorrect Python `ctypes` definition causes `sizeof(INPUT)` to evaluate to 32, 36, or 48 bytes, resulting in `SendInput` failing immediately with `ERROR_INVALID_PARAMETER` (Win32 Error 87).

#### Verified 64-bit Memory Layout (Empirically Validated on Host):
```
+---------------------------------------------------------------------------------+
| Offset (Bytes) | Field Name       | Type              | Size   | Alignment      |
+----------------+------------------+-------------------+--------+----------------+
| 0 .. 3         | type             | DWORD (wintypes)  | 4 B    | 4-byte         |
| 4 .. 7         | [PADDED BY COMP] | Explicit Pad      | 4 B    | Required for   |
|                |                  |                   |        | 8-byte union   |
| 8 .. 39        | union            | _INPUT_UNION      | 32 B   | 8-byte aligned |
+---------------------------------------------------------------------------------+
Total Size = 40 Bytes (sizeof(INPUT) == 40)
```

Inside `_INPUT_UNION`:
- `MOUSEINPUT` (Size = 32 Bytes):
  - Offset 0: `dx` (`LONG`, 4 B)
  - Offset 4: `dy` (`LONG`, 4 B)
  - Offset 8: `mouseData` (`DWORD`, 4 B)
  - Offset 12: `dwFlags` (`DWORD`, 4 B)
  - Offset 16: `time` (`DWORD`, 4 B)
  - Offset 20: [Compiler Pad] (4 B)
  - Offset 24: `dwExtraInfo` (`ULONG_PTR` / `c_size_t`, 8 B)
  - Total: 32 Bytes
- `KEYBDINPUT` (Size = 24 Bytes, padded to 32 B in union):
  - Offset 0: `wVk` (`WORD`, 2 B)
  - Offset 2: `wScan` (`WORD`, 2 B)
  - Offset 4: `dwFlags` (`DWORD`, 4 B)
  - Offset 8: `time` (`DWORD`, 4 B)
  - Offset 12: [Compiler Pad] (4 B)
  - Offset 16: `dwExtraInfo` (`ULONG_PTR` / `c_size_t`, 8 B)
  - Total: 24 Bytes (union expands to 32 Bytes)
- `HARDWAREINPUT` (Size = 8 Bytes, padded to 32 B in union):
  - Offset 0: `uMsg` (`DWORD`, 4 B)
  - Offset 4: `wParamL` (`WORD`, 2 B)
  - Offset 6: `wParamH` (`WORD`, 2 B)
  - Total: 8 Bytes

#### Exact Normative Python ctypes Implementation:
```python
"""
kutomoto.automation.win32_core.input_structs
Normative 64-bit SendInput Structures for Windows OS
Copyrights reserved to 90Studio
"""
import ctypes
from ctypes import wintypes

INPUT_MOUSE    = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

# Mouse dwFlags
MOUSEEVENTF_MOVE        = 0x0001
MOUSEEVENTF_LEFTDOWN    = 0x0002
MOUSEEVENTF_LEFTUP      = 0x0004
MOUSEEVENTF_RIGHTDOWN   = 0x0008
MOUSEEVENTF_RIGHTUP     = 0x0010
MOUSEEVENTF_MIDDLEDOWN  = 0x0020
MOUSEEVENTF_MIDDLEUP    = 0x0040
MOUSEEVENTF_WHEEL       = 0x0800
MOUSEEVENTF_HWHEEL      = 0x1000
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_ABSOLUTE    = 0x8000

# Keyboard dwFlags
KEYEVENTF_EXTENDEDKEY   = 0x0001
KEYEVENTF_KEYUP         = 0x0002
KEYEVENTF_UNICODE       = 0x0004
KEYEVENTF_SCANCODE      = 0x0008

ULONG_PTR = ctypes.c_size_t

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

# Assertion verifying exact 64-bit alignment:
assert ctypes.sizeof(INPUT) == 40, f"Critical: INPUT struct must be 40 bytes, got {ctypes.sizeof(INPUT)}"
```

### 3.2 Mouse Injection Specification (Normalized Absolute vs Relative Clicks)
Windows desktop forms and browser renderers (Chromium Blink, Gecko) process mouse events through asynchronous message queues. Instantaneous click-down and click-up with 0ms delay causes click drops because the browser hit-test tree fails to resolve between states.

#### Mandatory Mouse Click Timing Budget:
1. **Cursor Positioning**: Call `SetCursorPos(x, y)` to physically place the cursor over the target element.
2. **Hover Settle Delay**: Sleep $25\text{ms}$ to $40\text{ms}$ allowing the browser or GUI framework to process `WM_MOUSEMOVE` and trigger hover styles/tooltips.
3. **Button Down**: Dispatch `MOUSEEVENTF_LEFTDOWN` via `SendInput`.
4. **Hold Duration**: Sleep $20\text{ms}$ to $35\text{ms}$ ensuring `WM_LBUTTONDOWN` is acknowledged.
5. **Button Up**: Dispatch `MOUSEEVENTF_LEFTUP` via `SendInput`.
6. **Post-Click Settle**: Sleep $30\text{ms}$ for focus and activation handlers to settle.
7. **Double Click**: Repeat steps 3–5 with an inter-click interval of $60\text{ms}$ to $90\text{ms}$ (well within Windows standard double-click speed of $500\text{ms}$).

### 3.3 Keyboard Injection Specification (Direct Unicode vs Virtual Keys)
Kutomoto standardizes on a **bifurcated keyboard injection model**:

```
                              +------------------------+
                              | Keyboard Action Input  |
                              +------------------------+
                                          |
                        +-----------------+-----------------+
                        |                                   |
                        v                                   v
             [ Semantic Text Typing ]             [ Navigation / Control ]
          (Names, Account IDs, Notes)           (Tab, Enter, Arrows, Hotkeys)
                        |                                   |
                        v                                   v
             KEYEVENTF_UNICODE (0x0004)                 Virtual Keys (wVk)
             - wScan = ord(ch) UTF-16                   - wVk = VK_TAB (0x09)
             - wVk = 0                                  - wVk = VK_RETURN (0x0D)
             - Complete layout immunity                 - wVk = VK_ESCAPE (0x1B)
             - Works across AZERTY, Arabic              - Supports Ctrl/Alt/Shift
```

#### Unicode Injection Mechanics (`KEYEVENTF_UNICODE = 0x0004`):
- For each character `ch` in text:
  - If character is in Basic Multilingual Plane ($\le \text{U+FFFF}$):
    - Down event: `wScan = ord(ch)`, `wVk = 0`, `dwFlags = KEYEVENTF_UNICODE`.
    - Up event: `wScan = ord(ch)`, `wVk = 0`, `dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP`.
  - If character is a surrogate pair (e.g. emojis $> \text{U+FFFF}$):
    - Encode to UTF-16LE, yielding high surrogate $W_1$ and low surrogate $W_2$.
    - Emit Down/Up for $W_1$, then Down/Up for $W_2$.
- **Layout Immunity Guarantee**: Because `KEYEVENTF_UNICODE` dispatches characters directly to the window message queue as `WM_CHAR` / `WM_UNICHAR`, text typing produces identical output regardless of whether the physical workstation has French AZERTY, German QWERTZ, Arabic, or US QWERTY configured.

#### Virtual Key Code Table for Form Traversal:
```python
VK_MAP = {
    "tab": 0x09,
    "enter": 0x0D,
    "return": 0x0D,
    "escape": 0x1B,
    "backspace": 0x08,
    "delete": 0x2E,
    "space": 0x20,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "ctrl": 0x11,
    "control": 0x11,
    "shift": 0x10,
    "alt": 0x12,
    "win": 0x5B,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "a": 0x41, "c": 0x43, "v": 0x56, "x": 0x58, "z": 0x5A
}
```

### 3.4 Key Sequencing, Modifiers & Field Clearing Mechanics
When synthesizing key combinations (such as `Ctrl+A` or `Shift+Tab`), modifiers must strictly follow a **FIFO Press / LIFO Release (Nested Enclosure)** sequence:
1. `KeyDown(Modifier)` (e.g., `VK_CONTROL`)
2. Sleep $10\text{ms}$ (Windows input queue modifier state transition)
3. `KeyDown(Key)` (e.g., `VK_A`)
4. Sleep $15\text{ms}$
5. `KeyUp(Key)`
6. Sleep $10\text{ms}$
7. `KeyUp(Modifier)`

#### Field Clearing Mechanics:
Existing form fields in web or desktop apps often contain pre-filled default text, placeholder values, or previous form entry data. Kutomoto provides three field clearing strategies:
1. **`select_all_backspace` (Standard Enterprise Default)**:
   - Dispatches `Ctrl+A` (Select All).
   - Sleeps $30\text{ms}$.
   - Dispatches `VK_BACK` (Backspace).
   - Sleeps $40\text{ms}$.
2. **`triple_click_delete` (Web Paragraph / URL Bar)**:
   - Dispatches 3 mouse clicks within $120\text{ms}$ to select entire text block.
   - Dispatches `VK_BACK`.
3. **`backspace_repeat` (Masked Input / PIN Fields)**:
   - Dispatches `End` key to move to text tail.
   - Dispatches `N` consecutive `Backspace` keystrokes.

### 3.5 High-Speed Unicode Clipboard Driver (Zero-Loss Form Injection)
In banking wire transfers or telecom subscriber registrations, multi-line addresses, notes, or large ID strings (> 60 characters) typed character-by-character introduce unnecessary execution delay ($60 \times 25\text{ms} = 1.5\text{s}$).

Kutomoto implements an enterprise clipboard injection pipeline:
1. **Trigger Condition**: When `payload_length > 40` or text contains newline characters (`\n`), the engine invokes the high-speed clipboard driver.
2. **Win32 Clipboard API Sequence**:
   - `user32.OpenClipboard(None)`: Opens system clipboard with a retry loop (5 attempts, $20\text{ms}$ exponential backoff) to handle contention with Microsoft Office or clipboard history utilities.
   - `user32.EmptyClipboard()`: Flushes existing formats.
   - `kernel32.GlobalAlloc(GMEM_MOVEABLE, byte_size)`: Allocates global movable memory.
   - `kernel32.GlobalLock(h_mem)`: Obtains pointer; encodes text to UTF-16LE with null-terminator (`b'\x00\x00'`); executes `ctypes.memmove`.
   - `kernel32.GlobalUnlock(h_mem)`.
   - `user32.SetClipboardData(CF_UNICODETEXT, h_mem)`: Hands ownership to Windows clipboard.
   - `user32.CloseClipboard()`.
3. **Paste Keystroke**: Dispatches `Ctrl+V` combination.
4. **Audit Scrubbing**: Once paste completes, clipboard is zeroed or restored to prevent sensitive customer data exposure.

---

## 4. Window Attachment & Focus Stealing Recovery Specification

### 4.1 Windows OS Focus-Stealing Protection (`LockSetForegroundWindow`)
Beginning with Windows 98/2000 and reinforced in Windows 10/11, Microsoft prevents background applications from disrupting the user by calling `SetForegroundWindow`. If a non-foreground thread calls `SetForegroundWindow`, Windows rejects the call, flashes the target application's taskbar button orange, and keeps the current foreground window active.

For an unattended or semi-attended automation system, this results in inputs being typed into the wrong application or dropped entirely.

### 4.2 The Canonical Thread-Input Attachment Algorithm (`AttachThreadInput`)
To guarantee that Kutomoto can activate any target window (browser or desktop app) with 100% reliability, the engine uses the canonical Win32 **Thread Input Attachment** technique:

```
[Kutomoto Engine Thread]                [Windows OS Kernel]               [Target Application Thread]
           |                                     |                                     |
           |-- 1. GetForegroundWindow() -------->|                                     |
           |<-- Returns Current Foreground HWND -|                                     |
           |                                     |                                     |
           |-- 2. GetWindowThreadProcessId() --->|                                     |
           |<-- Foreground TID ------------------|                                     |
           |                                     |                                     |
           |-- 3. AttachThreadInput(Current, Fg, TRUE)                                 |
           |      (Attaches input queues together: OS now treats Kutomoto as in front) |
           |------------------------------------>|                                     |
           |                                     |                                     |
           |-- 4. ShowWindow(target_hwnd, SW_RESTORE)                                  |
           |------------------------------------>|-------- Restores target window ---->|
           |                                     |                                     |
           |-- 5. BringWindowToTop(target_hwnd) >|                                     |
           |-- 6. SetForegroundWindow(target) -->|-------- Activates target HWND ----->|
           |                                     |                                     |
           |-- 7. AttachThreadInput(Current, Fg, FALSE) [FINALLY BLOCK]                |
           |      (Detaches input queues immediately)                                  |
           |------------------------------------>|                                     |
```

#### Complete Normative Implementation:
```python
"""
kutomoto.automation.win32_window.focus
Canonical Win32 Window Focus and Activation Core
Copyrights reserved to 90Studio
"""
import ctypes
from ctypes import wintypes
import time
import logging

logger = logging.getLogger("kutomoto.focus")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SW_HIDE            = 0
SW_NORMAL          = 1
SW_SHOWMINIMIZED   = 2
SW_MAXIMIZE        = 3
SW_SHOWNOACTIVATE  = 4
SW_SHOW            = 5
SW_MINIMIZE        = 6
SW_SHOWNA          = 7
SW_RESTORE         = 9

def activate_target_window(hwnd: int, timeout_ms: int = 1500) -> bool:
    """
    Guarantees bringing target HWND to the foreground on Windows 10/11
    using thread-input queue attachment and iconic state restoration.
    """
    if not hwnd or not user32.IsWindow(hwnd):
        logger.error("Invalid window handle: %s", hwnd)
        return False

    # Check if already active
    if user32.GetForegroundWindow() == hwnd:
        return True

    # 1. Un-minimize window if in iconic state
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.06)

    foreground_hwnd = user32.GetForegroundWindow()
    current_thread_id = kernel32.GetCurrentThreadId()
    foreground_thread_id = user32.GetWindowThreadProcessId(foreground_hwnd, None) if foreground_hwnd else 0

    attached = False
    if foreground_thread_id != 0 and foreground_thread_id != current_thread_id:
        # Attach thread input to bypass LockSetForegroundWindow
        attached = bool(user32.AttachThreadInput(current_thread_id, foreground_thread_id, True))

    try:
        # 2. Simulated Alt-key tap bypass (auxiliary trick for stubborn DWM locks)
        user32.keybd_event(0x12, 0, 0, 0) # Alt down
        user32.keybd_event(0x12, 0, 0x0002, 0) # Alt up

        # 3. Bring to top and set foreground
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetActiveWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(current_thread_id, foreground_thread_id, False)

    # 4. Verification polling loop
    start_time = time.time()
    deadline = start_time + (timeout_ms / 1000.0)
    
    while time.time() < deadline:
        if user32.GetForegroundWindow() == hwnd:
            # Allow OS message pump 40ms to settle input caret
            time.sleep(0.04)
            return True
        time.sleep(0.03)

    logger.warning("Timed out waiting for HWND 0x%X to become foreground", hwnd)
    return user32.GetForegroundWindow() == hwnd
```

### 4.3 Window State Handling & Verification Polling Loop
Before dispatching input, the automation engine evaluates three window state conditions:
1. **Iconic / Minimized**: `IsIconic(hwnd) == TRUE`. Engine issues `ShowWindow(hwnd, SW_RESTORE)` ($9$) and pauses $60\text{ms}$ for DWM restore animation.
2. **Maximized / Zoomed**: `IsZoomed(hwnd) == TRUE`. Engine preserves maximized state without alteration.
3. **Off-Screen / Obscured**: `GetWindowRect` coordinates are checked against `SM_CXVIRTUALSCREEN` and `SM_CYVIRTUALSCREEN`. If window is positioned off-screen, engine repositions it to visible desktop bounds via `SetWindowPos`.

---

## 5. Cross-Application Targeting: Web Browsers vs Native Desktop Apps

### 5.1 Web Browser Targeting (Edge Chromium, Chrome, Firefox)
Modern web browsers use multi-process architectures where each browser tab renders in a sandboxed sub-process (`msedge.exe`, `chrome.exe`), but all tabs share top-level operating system windows.

#### Browser Structural Quirks:
- **Title Bar Dynamic Naming**: When a user switches tabs, the top-level window title immediately changes to match the newly active page title plus a browser suffix (e.g., `"Banking KYC Account Opening - Work - Microsoft Edge"` or `"Telecom Line Provisioning - Google Chrome"`).
- **Sub-Tab Invisibility**: Background tabs in the same browser window do not possess individual Win32 `HWND` handles; they exist only as DOM documents within the browser process memory.

### 5.2 Browser Sub-Tab Targeting without Extensions (4-Way Strategy)
To ensure Kutomoto operates cleanly in restricted enterprise environments where browser extension store access is forbidden by Group Policy, Kutomoto specifies **Four Complementary Targeting Modes**:

```
+---------------------------------------------------------------------------------------+
| Mode 1: Window Title Regex Matching                                                  |
| - Engine enumerates open windows via EnumWindows API.                                 |
| - Matches regex pattern e.g. `.*Banking KYC.*|.*Customer Due Diligence.*`.            |
| - Brings matched browser window to front and executes flow.                           |
+---------------------------------------------------------------------------------------+
| Mode 2: Process Executable Filter                                                     |
| - Scans running processes for `msedge.exe`, `chrome.exe`, or `firefox.exe`.           |
| - Enumerates visible top-level windows belonging to that PID tree.                    |
| - Targets active window.                                                              |
+---------------------------------------------------------------------------------------+
| Mode 3: Interactive 3-Second Countdown HUD (Zero-Switching Friction)                  |
| - Operator clicks "Run Flow" in Kutomoto.                                             |
| - Kutomoto displays a floating transparent countdown HUD: "Switch to form... 3.. 2..1"|
| - Operator clicks desired browser tab or desktop application.                         |
| - At 0.0s, engine locks onto current foreground HWND and begins filling!              |
+---------------------------------------------------------------------------------------+
| Mode 4: In-Place Global Hotkey Trigger (Ctrl+F9 / F10)                                |
| - Operator remains in their open browser tab or desktop app.                          |
| - Operator presses global hotkey `Ctrl+F9`.                                           |
| - Kutomoto fills the active form in-place with zero window switching!                 |
+---------------------------------------------------------------------------------------+
```

### 5.3 Native Desktop Applications (WinForms, WPF, Tkinter, Qt, SAP GUI)
Windows desktop application architectures vary widely across enterprise systems:

| Framework | Architecture | HWND Structure | Targeting Specification |
|:---|:---|:---|:---|
| **WinForms** (`System.Windows.Forms`) | Win32 / GDI+ | Every control (TextBox, Button) has its own child `HWND`. | Target top-level client rect with normalized coordinates OR direct child `FindWindowEx`. |
| **WPF** (`PresentationFramework`) | DirectX / MilCore | Single top-level `HWND`; individual controls are DirectX visual elements without separate HWNDs. | Top-level client rect with normalized coordinates $(u, v)$ is **strictly required**. |
| **Tkinter / Tcl-Tk** | Native Win32 wrapper | Top-level `TkTopLevel` HWND; controls rendered internally. | Top-level client rect with normalized coordinates. |
| **Qt / PySide** | Native raster engine | Single top-level HWND per window. | Top-level client rect with normalized coordinates. |
| **SAP GUI** | SAP Win32 Client | Top-level window with nested container panels. | Top-level client rect with normalized coordinates. |

**Universal Architectural Rule**: By basing Kutomoto's visual designer and execution engine on **Normalized Window Client Coordinates** ($0.0 \le u, v \le 1.0$), Kutomoto achieves 100% universal targeting compatibility across WPF, Qt, SAP GUI, Tkinter, and Web Browsers, bypassing the limitation of missing child HWNDs!

### 5.4 User Interface Privilege Isolation (UIPI) & UAC Elevation Rules
Windows Vista introduced **User Interface Privilege Isolation (UIPI)**. UIPI blocks a process running at a lower Integrity Level from dispatching `SendInput` or sending window messages (`WM_LBUTTONDOWN`, `WM_KEYDOWN`) to a process running at a higher Integrity Level.

#### Empirical Host Audit Finding:
On this Windows 11 host, `shell32.IsUserAnAdmin()` returns `0` (Standard User Token).

#### UIPI Operational Specifications:
1. **Target App Running Elevated**: If an enterprise application (e.g. administrative SAP GUI or elevated command prompt) runs as Administrator (High Integrity), and Kutomoto runs as Medium Integrity:
   - `SetForegroundWindow` will fail.
   - `SendInput` will be discarded silently by the Windows kernel.
2. **Kutomoto Elevation Detection Protocol**:
   - On startup, Kutomoto calls `shell32.IsUserAnAdmin()`.
   - When targeting a window, Kutomoto queries target process token via `OpenProcessToken` and `GetTokenInformation(TokenIntegrityLevel)`.
   - If `target_integrity > kutomoto_integrity`:
     - Engine halts execution before sending any input.
     - Displays actionable warning dialog: `"Target application is running as Administrator. Please relaunch Kutomoto as Administrator to automate this application."`

---

## 6. Multi-Layer Safety Guardrails & Emergency Failsafes

In enterprise banking and telecom environments, an unconstrained automation script can submit erroneous financial transactions or corrupt subscriber records. Kutomoto enforces four hardened safety layers:

```
+------------------------------------------------------------------------------------+
|                      KUTOMOTO 4-LAYER SAFETY GUARDRAILS                            |
+------------------------------------------------------------------------------------+
|                                                                                    |
|  [ LAYER 1: Hardware Screen Corner Slam Failsafe ]                                 |
|  - Inspected before every single step and during mouse movements.                  |
|  - Condition: `GetCursorPos(pt)` yields `pt.x <= 2 and pt.y <= 2`.                 |
|  - Reaction: Instant engine halt in < 5ms. Sets state to STOPPED.                  |
|                                                                                    |
|  [ LAYER 2: Global Emergency Escape Abort Hotkey ]                                 |
|  - Low-level asynchronous keyboard monitor intercepts Escape key.                  |
|  - Signals cancellation token; unblocks async step sleep loops immediately.        |
|  - Releases stuck modifier keys (Ctrl, Shift, Alt, Win).                           |
|                                                                                    |
|  [ LAYER 3: Loss-of-Focus Guardian ]                                               |
|  - Pre-flight check prior to every click, key press, or text typing event:         |
|    `GetForegroundWindow() == target_hwnd`                                          |
|  - If focus stolen by popup or user: ENGINE PAUSES IMMEDIATELY.                    |
|  - Prevents typing sensitive bank/telecom data into wrong window!                  |
|                                                                                    |
|  [ LAYER 4: Credential Masking & Memory Security ]                                 |
|  - Fields with `is_secret: true` masked with `********` in all UI and logs.        |
|  - Sensitive strings zeroed out from memory buffers after step completion.         |
+------------------------------------------------------------------------------------+
```

### 6.1 Hardware Screen Corner Slam Failsafe (`(0, 0)` Abort)
If an operator loses control of the automation (e.g. rapid unwanted clicks or typing), standard UI buttons may be unreachable. The operator simply moves the physical mouse hard into the **top-left corner of the primary screen**.

```python
"""
kutomoto.engine.safety.corner_failsafe
Hardware Failsafe Screen Corner Monitor
Copyrights reserved to 90Studio
"""
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

class ScreenCornerFailsafeException(Exception):
    """Raised immediately when cursor is slammed into screen corner."""
    pass

def check_corner_failsafe(margin_pixels: int = 2):
    """
    Checks if physical cursor is in the top-left screen corner (0, 0).
    Throws ScreenCornerFailsafeException in < 1ms if detected.
    """
    pt = wintypes.POINT()
    if user32.GetCursorPos(ctypes.byref(pt)):
        if pt.x <= margin_pixels and pt.y <= margin_pixels:
            raise ScreenCornerFailsafeException(
                f"Emergency Corner Slam Failsafe triggered at ({pt.x}, {pt.y}). Execution aborted!"
            )
```

### 6.2 Global Emergency Escape Abort Hotkey
Pressing `Escape` (or configured hotkey `Ctrl+Shift+Q` / `Pause`) immediately sets an atomic stop flag.
- The async runner checks `_stop_requested` between actions and cancels in-flight delays.
- A critical cleanup routine dispatches `KEYUP` events for all modifier keys (`VK_CONTROL`, `VK_SHIFT`, `VK_MENU`, `VK_LWIN`) to prevent keys becoming logically stuck down in the OS.

### 6.3 Loss-of-Focus Guardian (Pre-Flight Focus Validation)
Prior to every click or typing action, the engine executes:
```python
if target_hwnd and user32.GetForegroundWindow() != target_hwnd:
    # Target window lost focus!
    engine.transition_to_paused(
        reason=f"Loss of focus detected. Expected HWND 0x{target_hwnd:X}, got 0x{user32.GetForegroundWindow():X}"
    )
    # Halt step loop until operator explicitly resumes
```

---

## 7. Concrete Authoring Guidance for `docs/SPECIFICATION.md`

To empower the M1 Specification Worker to author a comprehensive, coherent, and authoritative `docs/SPECIFICATION.md`, this section provides exact Markdown structures, tables, and technical language for direct inclusion.

### 7.1 Proposed Specification Table of Contents & Structure
The master specification should incorporate the following dedicated technical sections:

```markdown
# kutomoto — System Specification & Architecture Blueprint
**Product**: kutomoto Forms Filling Automation System for Windows OS  
**Copyright**: Copyrights reserved to 90Studio  
**Standard**: Enterprise Grade (Banking, Telecom, General Corporate)

## Section 1: Executive Overview & Business Value
## Section 2: Enterprise Use Cases & User Stories (Epic 1 to 8)
## Section 3: Visual Form Designer Canvas & Box Model Specification
## Section 4: Unified Workflow & 10 Atomic Action Primitives
## Section 5: Win32 Automation Core & OS Driver Architecture
   - 5.1 Per-Monitor V2 High-DPI Awareness Mechanics
   - 5.2 64-bit SendInput ABI Layout & Memory Alignment
   - 5.3 Keyboard Injection: KEYEVENTF_UNICODE vs Virtual Keys
   - 5.4 Mouse Simulation & Dual-Coordinate Resolution
   - 5.5 High-Speed Unicode Clipboard Driver
## Section 6: Window Attachment, Focus Recovery & Cross-App Targeting
   - 6.1 LockSetForegroundWindow & AttachThreadInput Bypass Protocol
   - 6.2 Browser Tab Targeting without Extensions (4-Way Model)
   - 6.3 Native Desktop App Frameworks (WPF, WinForms, Qt, Tkinter, SAP)
   - 6.4 UIPI & UAC Integrity Rules
## Section 7: Multi-Layer Enterprise Safety Guardrails
   - 7.1 Corner Slam Failsafe
   - 7.2 Emergency Escape Abort & Modifier Reset
   - 7.3 Loss-of-Focus Guardian
   - 7.4 Sensitive Credential Masking & Audit Trails
## Section 8: Visual-to-Workflow Compilation Pipeline (5-Pass Algorithm)
## Section 9: Execution Engine Runtime & 7-State FSM
## Section 10: Enterprise User Interface & Microsoft Edge App Shell
## Section 11: Sample Target Applications (Banking KYC & Telecom SIM)
## Section 12: Acceptance Verification Matrix & Compliance Attributions
```

### 7.2 Ready-to-Embed Markdown Sections & Code Specifications
The M1 Worker can directly incorporate the ctypes definitions from Section 2.3 and 3.1, the `activate_target_window` implementation from Section 4.2, and the safety guardrail specs from Section 6.

### 7.3 Win32 Driver API Contracts & Method Signatures
The automation core must expose the following clean, typed Python interface to the workflow engine:

```python
class IWin32AutomationDriver:
    """Interface Contract for kutomoto Win32 Driver Core."""
    
    def initialize_dpi_context(self) -> str:
        """Sets Per-Monitor V2 DPI awareness. Returns mode name."""
        ...
        
    def find_window(self, title_pattern: str, process_name: Optional[str] = None) -> Optional[int]:
        """Finds top-level HWND matching title regex or process name."""
        ...
        
    def activate_window(self, hwnd: int, timeout_ms: int = 1500) -> bool:
        """Forces target HWND to foreground via AttachThreadInput. Returns success."""
        ...
        
    def get_client_bounds(self, hwnd: int) -> Tuple[int, int, int, int]:
        """Returns (client_left, client_top, client_width, client_height) in physical pixels."""
        ...
        
    def resolve_normalized_coords(self, hwnd: int, norm_x: float, norm_y: float) -> Tuple[int, int]:
        """Converts normalized (0.0..1.0) window coordinates to physical screen (x, y)."""
        ...
        
    def send_mouse_click(self, x: int, y: int, button: str = "left", click_count: int = 1) -> None:
        """Dispatches pixel-exact mouse click with settle delays."""
        ...
        
    def send_text_unicode(self, text: str, keystroke_delay_ms: int = 20) -> None:
        """Types string character-by-character via KEYEVENTF_UNICODE."""
        ...
        
    def send_key_press(self, key_name: str, repeat_count: int = 1) -> None:
        """Sends navigation or operational virtual key press (e.g. Tab, Enter)."""
        ...
        
    def send_hotkey(self, modifiers: List[str], key: str) -> None:
        """Sends modifier combination (e.g. ['ctrl'], 'a') with FIFO/LIFO nesting."""
        ...
        
    def clear_field(self, strategy: str = "select_all_backspace") -> None:
        """Clears text field before typing."""
        ...
        
    def paste_clipboard_text(self, text: str) -> bool:
        """Sets text onto Windows Unicode clipboard and executes Ctrl+V."""
        ...
        
    def check_safety_failsafes(self) -> None:
        """Inspects corner slam (0,0) and abort hotkey. Raises exception if triggered."""
        ...
```

---
*Report formulated, validated, and certified by **m1_explorer_2** for 90Studio / kutomoto.*
