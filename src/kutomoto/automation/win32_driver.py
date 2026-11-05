"""
kutomoto.automation.win32_driver
Production Win32 driver adapter implementing IWin32Driver Protocol.
Copyrights reserved to 90Studio
"""

from __future__ import annotations

import ctypes
import logging
from typing import Any, List, Optional, Tuple

from kutomoto import __copyright__
from kutomoto.automation import win32_core, win32_input, win32_window

logger = logging.getLogger("kutomoto.automation.driver")

try:
    user32 = ctypes.windll.user32
except (AttributeError, OSError):
    user32 = None


class ProductionDriverAdapter:
    """
    Production driver adapter implementing the IWin32Driver Protocol
    by delegating to kutomoto.automation native ctypes implementations.
    """

    def __init__(self) -> None:
        self._core = win32_core
        self._input = win32_input
        self._window = win32_window
        self._last_cursor_pos: Tuple[int, int] = (500, 500)

    def set_dpi_awareness(self) -> bool:
        """Enables Per-Monitor V2 DPI awareness."""
        return self._core.set_process_dpi_awareness()

    def get_screen_dimensions(self) -> Tuple[int, int]:
        """Returns virtual screen width and height in pixels."""
        if user32:
            w = int(user32.GetSystemMetrics(0))
            h = int(user32.GetSystemMetrics(1))
            if w > 0 and h > 0:
                return (w, h)
        return (1920, 1080)

    def get_cursor_pos(self) -> Tuple[int, int]:
        """Returns current mouse cursor position (x, y) in screen coordinates."""
        if user32:
            pt = self._core.POINT()
            if user32.GetCursorPos(ctypes.byref(pt)):
                self._last_cursor_pos = (int(pt.x), int(pt.y))
                return self._last_cursor_pos
        return self._last_cursor_pos

    def set_cursor_pos(self, x: int, y: int) -> None:
        """Sets mouse cursor position to screen coordinates (x, y)."""
        self._last_cursor_pos = (int(x), int(y))
        self._input.send_mouse_move(x, y)

    def get_foreground_window(self) -> int:
        """Returns integer HWND of the current foreground window."""
        return self._window.get_foreground_window()

    def find_window(
        self,
        title_pattern: str,
        match_mode: str = "contains",
        process_name: Optional[str] = None,
    ) -> Optional[int]:
        """
        Finds matching window and returns its integer HWND handle, or None if not found.
        """
        window_info = self._window.find_window(
            title_pattern=title_pattern,
            match_mode=match_mode,
            exe_name=process_name,
        )
        return window_info.hwnd if window_info is not None else None

    def focus_window(self, hwnd: int, timeout_ms: int = 1500) -> bool:
        """Activates and brings target HWND to foreground."""
        return self._window.activate_target_window(hwnd, timeout_ms=timeout_ms)

    def get_window_bounds(self, hwnd: int) -> Tuple[int, int, int, int]:
        """Returns bounding rectangle (x, y, w, h) of target window."""
        return self._window.get_window_bounds(hwnd)

    def get_client_rect(self, hwnd: int) -> Tuple[int, int, int, int]:
        """Returns client viewport bounds (x, y, w, h) of target window."""
        return self._window.get_client_rect(hwnd)

    def client_to_screen(self, hwnd: int, client_x: int, client_y: int) -> Tuple[int, int]:
        """Translates client coordinates to absolute screen coordinates."""
        return self._window.client_to_screen_coords(hwnd, client_x, client_y)

    def send_click(
        self,
        x: int,
        y: int,
        button: str = "left",
        click_count: int = 1,
    ) -> None:
        """Injects hardware mouse click at specified screen coordinates."""
        self._last_cursor_pos = (int(x), int(y))
        self._input.send_click(x, y, button=button, click_count=click_count)

    def send_mouse_move(self, x: int, y: int) -> None:
        """Moves cursor to screen coordinates."""
        self._last_cursor_pos = (int(x), int(y))
        self._input.send_mouse_move(x, y)

    def send_text(
        self,
        text: str,
        delay_between_keys_ms: int = 20,
        use_clipboard_threshold: int = 40,
    ) -> None:
        """Injects text keystrokes or pastes via clipboard if exceeding threshold."""
        self._input.send_text(
            text,
            delay_between_keys_ms=delay_between_keys_ms,
            use_clipboard_threshold=use_clipboard_threshold,
        )

    def send_key_press(self, key_name: str, repeat_count: int = 1) -> None:
        """Injects single virtual key press."""
        self._input.send_key_press(key_name, repeat_count=repeat_count)

    def send_key_up(self, key_or_vk: Any) -> None:
        """Releases a virtual key."""
        self._input.send_key_up(key_or_vk)

    def send_hotkey(self, modifiers: List[str], key: str) -> None:
        """Injects keyboard chord with modifier keys."""
        self._input.send_hotkey(modifiers, key)

    def clear_field(self, strategy: str = "select_all_backspace") -> None:
        """Clears current active text field."""
        self._input.clear_field(strategy=strategy)

    def send_scroll(self, delta_x: int, delta_y: int) -> None:
        """Injects mouse wheel scroll."""
        self._input.send_mouse_wheel(delta=delta_y)

    def release_all_modifiers(self) -> None:
        """Releases stuck modifier keys."""
        self._input.release_all_modifiers()

    def is_key_pressed(self, key: Any) -> bool:
        """Checks if a key is currently pressed via GetAsyncKeyState."""
        if not user32:
            return False
        try:
            vk = self._core.resolve_virtual_key(key)
            state = user32.GetAsyncKeyState(int(vk))
            return bool(state & 0x8000)
        except Exception:
            return False


# Backward-compatibility alias
Win32DriverAdapter = ProductionDriverAdapter

__all__ = [
    "ProductionDriverAdapter",
    "Win32DriverAdapter",
    "__copyright__",
]
