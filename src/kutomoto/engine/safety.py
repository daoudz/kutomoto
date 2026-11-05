"""
kutomoto.engine.safety
Safety Guardrails, Failsafe Triggers, Loss-of-Focus Guardian, and Mock Driver.
Copyrights reserved to 90Studio
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("kutomoto.safety")

# Virtual key codes for cleanup and abort detection
VK_ESCAPE = 0x1B
MODIFIER_VKS = [
    0x11,  # VK_CONTROL
    0xA2,  # VK_LCONTROL
    0xA3,  # VK_RCONTROL
    0x10,  # VK_SHIFT
    0xA0,  # VK_LSHIFT
    0xA1,  # VK_RSHIFT
    0x12,  # VK_MENU (Alt)
    0xA4,  # VK_LMENU
    0xA5,  # VK_RMENU
    0x5B,  # VK_LWIN
    0x5C,  # VK_RWIN
]


# ==============================================================================
# 1. SAFETY EXCEPTIONS
# ==============================================================================

class SafetyException(Exception):
    """Base exception for all safety guardrail trips."""
    pass


class EscapeAbortTriggered(SafetyException):
    """Raised when emergency Escape key abort is activated by operator."""
    pass


class CornerFailsafeTriggered(SafetyException):
    """Raised when mouse hits screen corner failsafe coordinates (0, 0)."""
    pass


class FocusLostError(SafetyException):
    """Raised when target window loses focus and cannot be restored."""
    pass


class MouseDisturbanceDetected(SafetyException):
    """Raised when operator accidentally bumps mouse > 100px during execution."""
    pass


# ==============================================================================
# 2. CONFIGURATION
# ==============================================================================

@dataclass
class SafetyConfig:
    """Configurable thresholds for safety guardrails."""
    corner_failsafe_enabled: bool = True
    corner_threshold_px: int = 2
    escape_abort_enabled: bool = True
    focus_guardian_enabled: bool = True
    auto_pause_on_focus_loss: bool = True
    auto_restore_focus_attempts: int = 3
    auto_restore_delay_ms: int = 150
    mouse_disturbance_detector_enabled: bool = True
    mouse_disturbance_threshold_px: float = 100.0


# ==============================================================================
# 3. SAFETY GUARDIAN CORE
# ==============================================================================

class SafetyGuard:
    """
    Multi-layer safety guardian enforcing corner failsafe, Escape abort,
    loss-of-focus detection, and accidental mouse movement defense.
    """

    def __init__(self, driver: Any, config: Optional[SafetyConfig] = None) -> None:
        self.driver = driver
        self.config = config or SafetyConfig()
        self._last_cursor_pos: Optional[Tuple[int, int]] = None
        self._abort_requested: bool = False
        self._watcher_task: Optional[asyncio.Task] = None
        self._active_target_hwnd: Optional[int] = None

    def set_target_hwnd(self, hwnd: Optional[int]) -> None:
        """Sets the currently active target window handle."""
        self._active_target_hwnd = hwnd

    def register_intentional_mouse_move(self, x: int, y: int) -> None:
        """
        Informs the disturbance detector of an intentional mouse movement
        originating from an automation click or move action.
        """
        self._last_cursor_pos = (int(x), int(y))

    def check_corner_failsafe(self) -> None:
        """
        Verifies that mouse is not at screen corner failsafe position.
        Throws CornerFailsafeTriggered if within corner threshold.
        """
        if not self.config.corner_failsafe_enabled:
            return

        cur_x, cur_y = self.driver.get_cursor_pos()
        thresh = self.config.corner_threshold_px

        # Check Top-Left (0, 0)
        if cur_x <= thresh and cur_y <= thresh:
            logger.critical("Safety Failsafe: Top-Left screen corner hit at (%d, %d)", cur_x, cur_y)
            raise CornerFailsafeTriggered(f"Screen corner failsafe hit at ({cur_x}, {cur_y})")

        # Check Top-Right (max_x, 0)
        screen_w, _ = self.driver.get_screen_dimensions()
        if cur_x >= (screen_w - thresh) and cur_y <= thresh:
            logger.critical("Safety Failsafe: Top-Right screen corner hit at (%d, %d)", cur_x, cur_y)
            raise CornerFailsafeTriggered(f"Screen corner failsafe hit at ({cur_x}, {cur_y})")

    def check_escape_abort(self) -> None:
        """
        Verifies if Escape key abort has been triggered by operator.
        """
        if not self.config.escape_abort_enabled:
            return

        if self._abort_requested or self.driver.is_key_pressed("escape") or self.driver.is_key_pressed(VK_ESCAPE):
            self._abort_requested = True
            logger.warning("Emergency Escape abort detected from keyboard input")
            raise EscapeAbortTriggered("Operator triggered emergency Escape abort")

    def check_mouse_disturbance(self) -> None:
        """
        Detects unintended physical mouse movements exceeding threshold (E08).
        """
        if not self.config.mouse_disturbance_detector_enabled:
            return

        cur_x, cur_y = self.driver.get_cursor_pos()
        if self._last_cursor_pos is None:
            self._last_cursor_pos = (cur_x, cur_y)
            return

        ref_x, ref_y = self._last_cursor_pos
        dx = cur_x - ref_x
        dy = cur_y - ref_y
        dist = math.hypot(dx, dy)

        if dist > self.config.mouse_disturbance_threshold_px:
            logger.warning(
                "Accidental mouse disturbance detected (E08): displacement %.1fpx exceeds threshold %.1fpx",
                dist,
                self.config.mouse_disturbance_threshold_px,
            )
            # Update position so operator can pause/resume without immediate repeat trip
            self._last_cursor_pos = (cur_x, cur_y)
            raise MouseDisturbanceDetected(
                f"Operator mouse disturbance detected: {dist:.1f}px displacement"
            )

        # Minor drift update
        self._last_cursor_pos = (cur_x, cur_y)

    def check_focus_guardian(self, target_hwnd: Optional[int] = None) -> None:
        """
        Verifies active foreground window matches target application (E13).
        """
        if not self.config.focus_guardian_enabled:
            return

        hwnd = target_hwnd or self._active_target_hwnd
        if not hwnd:
            return

        active_hwnd = self.driver.get_foreground_window()
        if active_hwnd == hwnd:
            return

        logger.warning(
            "Loss-of-Focus Guardian (E13): Active HWND %s != Target HWND %s",
            active_hwnd,
            hwnd,
        )

        # Attempt auto-restoration if configured
        if self.config.auto_restore_focus_attempts > 0:
            for attempt in range(1, self.config.auto_restore_focus_attempts + 1):
                logger.info("Attempting to restore focus to target HWND %s (attempt %d)", hwnd, attempt)
                if self.driver.focus_window(hwnd):
                    if self.driver.get_foreground_window() == hwnd:
                        logger.info("Successfully re-acquired focus for HWND %s", hwnd)
                        return

        raise FocusLostError(
            f"Foreground focus lost: active window {active_hwnd} != target window {hwnd}"
        )

    def pre_step_check(self, target_hwnd: Optional[int] = None) -> None:
        """
        Master gatekeeper called immediately prior to EVERY atomic action execution.
        """
        self.check_escape_abort()
        self.check_corner_failsafe()
        self.check_mouse_disturbance()
        self.check_focus_guardian(target_hwnd)

    def emergency_cleanup(self) -> None:
        """
        Purges stuck modifier keys and releases mouse buttons.
        Guaranteed execution upon abort, exception, or cancellation.
        """
        logger.info("Executing safety emergency cleanup: releasing all modifier keys and mouse buttons")
        for vk in MODIFIER_VKS:
            try:
                self.driver.send_key_up(vk)
            except Exception as e:
                logger.debug("Suppressed error releasing vk %s: %s", vk, e)

        try:
            self.driver.release_all_modifiers()
        except Exception:
            pass

        # Reset state
        self._abort_requested = False
        self._last_cursor_pos = None

    async def start_background_watcher(self, check_interval_sec: float = 0.02) -> None:
        """
        Starts an asynchronous background watcher loop checking Escape abort.
        """
        async def _watcher_loop():
            try:
                while True:
                    if self.driver.is_key_pressed("escape") or self.driver.is_key_pressed(VK_ESCAPE):
                        self._abort_requested = True
                        break
                    await asyncio.sleep(check_interval_sec)
            except asyncio.CancelledError:
                pass

        self._abort_requested = False
        self._watcher_task = asyncio.create_task(_watcher_loop())

    def stop_background_watcher(self) -> None:
        """Cancels background Escape watcher task."""
        if self._watcher_task and not self._watcher_task.done():
            self._watcher_task.cancel()
            self._watcher_task = None

    def reset(self) -> None:
        """Resets internal safety state before or after a workflow run."""
        self.stop_background_watcher()
        self._abort_requested = False
        self._last_cursor_pos = None
        self._active_target_hwnd = None


# ==============================================================================
# 4. MOCK WIN32 DRIVER (ZERO-DEPENDENCY CI/CD & TESTING COMPONENT)
# ==============================================================================

class MockWin32Driver:
    """
    Full-fidelity mock Win32 driver recording all physical actions
    and providing controllable desktop state simulation for testing.
    """

    def __init__(self) -> None:
        self.dpi_aware: bool = False
        self.screen_width: int = 1920
        self.screen_height: int = 1080
        self.cursor_pos: Tuple[int, int] = (500, 500)
        self.foreground_hwnd: int = 1001
        self.clipboard_content: str = ""
        self.pressed_keys: Set[Union[int, str]] = set()

        # Window Database: hwnd -> metadata dict
        self.windows: Dict[int, Dict[str, Any]] = {
            1001: {
                "title": "Banking KYC Customer Onboarding - 90Studio",
                "process_name": "msedge.exe",
                "pid": 4200,
                "rect": (100, 100, 1200, 800),  # x, y, width, height
                "is_iconic": False,
                "is_window": True,
            },
            1002: {
                "title": "Commercial Loan Origination - 90Studio Bank",
                "process_name": "loan_app.exe",
                "pid": 5300,
                "rect": (150, 150, 1024, 768),
                "is_iconic": False,
                "is_window": True,
            },
        }

        # Telemetry & Call Logs
        self.calls: List[Dict[str, Any]] = []
        self.clicks: List[Dict[str, Any]] = []
        self.mouse_moves: List[Tuple[int, int]] = []
        self.typed_text: List[str] = []
        self.key_presses: List[Dict[str, Any]] = []
        self.hotkeys: List[Dict[str, Any]] = []
        self.cleared_fields: List[str] = []
        self.scrolls: List[Tuple[int, int]] = []
        self.active_modifiers: Set[str] = set()
        self.focus_history: List[int] = []

        # Fault Injection Flags
        self.fail_focus: bool = False
        self.fail_window_find: bool = False

    def reset(self) -> None:
        """Clears all recorded telemetry and resets default state."""
        self.calls.clear()
        self.clicks.clear()
        self.mouse_moves.clear()
        self.typed_text.clear()
        self.key_presses.clear()
        self.hotkeys.clear()
        self.cleared_fields.clear()
        self.scrolls.clear()
        self.active_modifiers.clear()
        self.focus_history.clear()
        self.pressed_keys.clear()
        self.cursor_pos = (500, 500)
        self.foreground_hwnd = 1001
        self.fail_focus = False
        self.fail_window_find = False

    # --------------------------------------------------------------------------
    # Simulation & Test Helpers
    # --------------------------------------------------------------------------

    def add_mock_window(
        self,
        hwnd: int,
        title: str,
        process_name: str = "app.exe",
        rect: Tuple[int, int, int, int] = (100, 100, 800, 600),
        is_iconic: bool = False,
    ) -> None:
        """Registers a mock window in the driver."""
        self.windows[hwnd] = {
            "title": title,
            "process_name": process_name,
            "pid": hwnd * 2,
            "rect": rect,
            "is_iconic": is_iconic,
            "is_window": True,
        }

    def simulate_escape_press(self) -> None:
        """Simulates operator pressing Escape key."""
        self.pressed_keys.add("escape")
        self.pressed_keys.add(0x1B)

    def simulate_escape_release(self) -> None:
        """Simulates operator releasing Escape key."""
        self.pressed_keys.discard("escape")
        self.pressed_keys.discard(0x1B)

    def simulate_focus_loss(self, new_hwnd: int = 9999) -> None:
        """Simulates another application stealing foreground focus (E13)."""
        self.foreground_hwnd = new_hwnd
        if new_hwnd not in self.windows:
            self.add_mock_window(new_hwnd, "External Popup / Notification", "unknown.exe")

    def simulate_corner_failsafe(self, x: int = 0, y: int = 0) -> None:
        """Positions cursor at screen corner failsafe coordinates."""
        self.cursor_pos = (x, y)

    def simulate_mouse_disturbance(self, dx: int = 150, dy: int = 150) -> None:
        """Simulates accidental operator mouse bump (E08)."""
        cur_x, cur_y = self.cursor_pos
        self.cursor_pos = (cur_x + dx, cur_y + dy)

    # --------------------------------------------------------------------------
    # Driver Core Interface Implementation
    # --------------------------------------------------------------------------

    def set_dpi_awareness(self) -> bool:
        self.dpi_aware = True
        self.calls.append({"method": "set_dpi_awareness", "success": True})
        return True

    def get_screen_dimensions(self) -> Tuple[int, int]:
        return (self.screen_width, self.screen_height)

    def get_cursor_pos(self) -> Tuple[int, int]:
        return self.cursor_pos

    def set_cursor_pos(self, x: int, y: int) -> None:
        self.cursor_pos = (int(x), int(y))
        self.mouse_moves.append(self.cursor_pos)
        self.calls.append({"method": "set_cursor_pos", "x": x, "y": y})

    def get_foreground_window(self) -> int:
        return self.foreground_hwnd

    def find_window(
        self,
        title_pattern: str,
        match_mode: str = "regex",
        process_name: Optional[str] = None,
    ) -> Optional[int]:
        self.calls.append({
            "method": "find_window",
            "title_pattern": title_pattern,
            "match_mode": match_mode,
            "process_name": process_name,
        })
        if self.fail_window_find:
            return None

        pattern = re.compile(title_pattern, re.IGNORECASE)
        for hwnd, win in self.windows.items():
            if pattern.search(win["title"]):
                if process_name:
                    if win["process_name"].lower() == process_name.lower():
                        return hwnd
                else:
                    return hwnd
        return None

    def focus_window(self, hwnd: int, timeout_ms: int = 1500) -> bool:
        self.calls.append({"method": "focus_window", "hwnd": hwnd, "timeout_ms": timeout_ms})
        if self.fail_focus or hwnd not in self.windows:
            return False

        win = self.windows[hwnd]
        if win.get("is_iconic", False):
            win["is_iconic"] = False  # Restored from taskbar

        self.foreground_hwnd = hwnd
        self.focus_history.append(hwnd)
        return True

    def get_window_bounds(self, hwnd: int) -> Tuple[int, int, int, int]:
        self.calls.append({"method": "get_window_bounds", "hwnd": hwnd})
        if hwnd in self.windows:
            return self.windows[hwnd]["rect"]
        return (0, 0, 800, 600)

    def get_client_rect(self, hwnd: int) -> Tuple[int, int, int, int]:
        bounds = self.get_window_bounds(hwnd)
        # Standardized return: (screen_left, screen_top, width, height)
        return (bounds[0], bounds[1], bounds[2], bounds[3])

    def get_client_bounds(self, hwnd: int) -> Tuple[int, int, int, int]:
        return self.get_client_rect(hwnd)

    def client_to_screen(self, hwnd: int, client_x: int, client_y: int) -> Tuple[int, int]:
        self.calls.append({"method": "client_to_screen", "hwnd": hwnd, "x": client_x, "y": client_y})
        win_x, win_y, _, _ = self.get_window_bounds(hwnd)
        return (win_x + int(client_x), win_y + int(client_y))

    def client_to_screen_coords(self, hwnd: int, client_x: int, client_y: int) -> Tuple[int, int]:
        return self.client_to_screen(hwnd, client_x, client_y)

    def send_click(
        self,
        x: int,
        y: int,
        button: str = "left",
        click_count: int = 1,
    ) -> None:
        self.cursor_pos = (int(x), int(y))
        entry = {"x": int(x), "y": int(y), "button": button, "click_count": click_count}
        self.clicks.append(entry)
        self.calls.append({"method": "send_click", **entry})

    def send_mouse_move(self, x: int, y: int, smooth: bool = False, steps: int = 10, delay_ms: float = 5.0) -> None:
        self.cursor_pos = (int(x), int(y))
        self.mouse_moves.append(self.cursor_pos)
        self.calls.append({"method": "send_mouse_move", "x": x, "y": y})

    def send_text(
        self,
        text: str,
        delay_between_keys_ms: int = 20,
        use_clipboard_threshold: int = 40,
    ) -> None:
        self.typed_text.append(text)
        self.calls.append({"method": "send_text", "text": text, "delay": delay_between_keys_ms})

    def send_key_press(self, key_name: str, repeat_count: int = 1) -> None:
        entry = {"key": str(key_name).lower(), "repeat_count": repeat_count}
        self.key_presses.append(entry)
        self.calls.append({"method": "send_key_press", **entry})

    def send_hotkey(self, modifiers: List[str], key: str) -> None:
        mods = [str(m).lower() for m in modifiers]
        entry = {"modifiers": mods, "key": str(key).lower()}
        self.hotkeys.append(entry)
        self.calls.append({"method": "send_hotkey", **entry})

    def send_key_down(self, vk_name: Union[int, str]) -> None:
        key_str = str(vk_name).lower()
        self.active_modifiers.add(key_str)
        self.pressed_keys.add(key_str)
        self.calls.append({"method": "send_key_down", "key": key_str})

    def send_key_up(self, vk_name: Union[int, str]) -> None:
        key_str = str(vk_name).lower()
        self.active_modifiers.discard(key_str)
        self.pressed_keys.discard(key_str)
        self.calls.append({"method": "send_key_up", "key": key_str})

    def release_all_modifiers(self) -> None:
        self.active_modifiers.clear()
        for vk in MODIFIER_VKS:
            self.pressed_keys.discard(str(vk).lower())
            self.pressed_keys.discard(vk)
        self.calls.append({"method": "release_all_modifiers"})

    def send_scroll(self, delta_x: int, delta_y: int) -> None:
        self.scrolls.append((int(delta_x), int(delta_y)))
        self.calls.append({"method": "send_scroll", "delta_x": delta_x, "delta_y": delta_y})

    def clear_field(self, strategy: str = "select_all_backspace") -> None:
        self.cleared_fields.append(strategy)
        self.calls.append({"method": "clear_field", "strategy": strategy})

    def get_clipboard_text(self) -> str:
        return self.clipboard_content

    def set_clipboard_text(self, text: str) -> None:
        self.clipboard_content = text
        self.calls.append({"method": "set_clipboard_text", "text": text})

    def is_key_pressed(self, vk_code_or_name: Union[int, str]) -> bool:
        if isinstance(vk_code_or_name, str):
            return vk_code_or_name.lower() in self.pressed_keys
        return vk_code_or_name in self.pressed_keys
