"""
kutomoto.automation
Win32 native automation driver for Windows OS.
Copyrights reserved to 90Studio
"""

from kutomoto.automation.win32_core import (
    HARDWAREINPUT,
    INPUT,
    KEYBDINPUT,
    MOUSEINPUT,
    POINT,
    RECT,
    VK_MAP,
    _INPUT_UNION,
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
    client_to_screen,
    client_to_screen_coords,
    enumerate_windows,
    find_all_windows,
    find_window,
    focus_window,
    get_client_bounds,
    get_client_rect,
    get_foreground_window,
    get_window_bounds,
    get_window_info,
    is_window_foreground,
    is_window_valid,
    normalized_to_screen_coords,
)

__copyright__ = "Copyrights reserved to 90Studio"

__all__ = [
    # win32_core
    "INPUT",
    "MOUSEINPUT",
    "KEYBDINPUT",
    "HARDWAREINPUT",
    "_INPUT_UNION",
    "POINT",
    "RECT",
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
    "activate_target_window",
    "focus_window",
    "get_foreground_window",
    "is_window_foreground",
    "is_window_valid",
    "get_window_bounds",
    "get_client_bounds",
    "get_client_rect",
    "client_to_screen_coords",
    "client_to_screen",
    "normalized_to_screen_coords",
    "get_window_info",
    "__copyright__",
]
