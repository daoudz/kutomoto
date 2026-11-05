"""
kutomoto.automation.win32_input
Win32 input injection driver utilizing ctypes SendInput and clipboard fallback.
Copyrights reserved to 90Studio
"""

import ctypes
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

try:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
except (AttributeError, OSError):
    user32 = None  # type: ignore
    kernel32 = None  # type: ignore


# ==============================================================================
# 1. CORE LOW-LEVEL INJECTION HELPERS
# ==============================================================================

def send_raw_input(inputs: Sequence[INPUT]) -> int:
    """
    Submits a sequence of INPUT structs to user32.SendInput.
    Returns the count of successfully inserted events.
    """
    if not inputs or user32 is None:
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
    if user32 is None:
        return

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
    if user32 is None:
        return

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
    if user32 is None:
        return

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
    repeat_count: Optional[int] = None,
) -> None:
    """
    Injects a physical/virtual key press (down + up) repeated N times.
    """
    if repeat_count is not None:
        repeat = int(repeat_count)
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


def send_key_up(vk_code_or_name: Union[int, str]) -> None:
    """
    Injects a key release (KEYEVENTF_KEYUP) for a given virtual key code or name.
    """
    vk = resolve_virtual_key(vk_code_or_name)
    extended = vk in (0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E)
    flags_up = (KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP) if extended else KEYEVENTF_KEYUP
    up = INPUT(
        type=INPUT_KEYBOARD,
        union=_INPUT_UNION(ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags_up, time=0, dwExtraInfo=0)),
    )
    send_raw_input([up])



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


def send_text(
    text: str,
    delay_ms: float = 25.0,
    use_clipboard_threshold: int = 0,
    delay_between_keys_ms: Optional[float] = None,
) -> None:
    """
    Types arbitrary Unicode text using KEYEVENTF_UNICODE.
    Decomposes strings into UTF-16 code units (supporting non-BMP surrogate pairs).
    If use_clipboard_threshold > 0 and len(text) >= use_clipboard_threshold, delegates to clipboard driver.
    """
    if delay_between_keys_ms is not None:
        delay_ms = float(delay_between_keys_ms)
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


def clear_field(
    method: str = "ctrl_a_backspace",
    delay_ms: float = 30.0,
    strategy: Optional[str] = None,
) -> None:
    """
    Clears the content of the currently focused input field.
    Default method: Ctrl+A followed by Backspace.
    """
    active_method = strategy if strategy is not None else method
    if active_method == "triple_click_delete":
        send_click(click_count=3)
        time.sleep(max(0.01, delay_ms / 1000.0))
        send_key_press("delete")
        return
    if active_method == "backspace_repeat":
        send_key_press("backspace", repeat=50)
        return

    send_hotkey(["ctrl"], "a")
    time.sleep(max(0.01, delay_ms / 1000.0))
    send_key_press("backspace")

    if active_method == "double":
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
    if user32 is None or kernel32 is None:
        return False

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
    if user32 is None or kernel32 is None:
        return None

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
