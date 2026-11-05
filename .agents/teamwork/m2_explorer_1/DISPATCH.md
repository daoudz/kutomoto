# Dispatch for m2_explorer_1

## Objective
Explore and provide the precise implementation blueprint for the Win32 ctypes automation driver (`src/kutomoto/automation/`) in Milestone 2.

## Inputs
- ORIGINAL_REQUEST: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md`
- Master Architecture: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md`
- Master Specification: `c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md` (specifically Section 6)

## Instructions
1. Inspect `docs/SPECIFICATION.md` Section 6 (Win32 Automation Core & Platform Primitives).
2. Formulate the exact implementation structure for:
   - `src/kutomoto/automation/win32_core.py`: Per-Monitor V2 DPI awareness initialization (`SetProcessDpiAwarenessContext(-4)`), 64-bit 40-byte `INPUT` struct hierarchy (`MOUSEINPUT`, `KEYBDINPUT`, `HARDWAREINPUT`, `_INPUT_UNION`, `INPUT`), Windows virtual key constants (`VK_TAB`, `VK_RETURN`, `VK_ESCAPE`, `VK_BACK`, `VK_CONTROL`, `VK_SHIFT`, etc.), and input type constants (`INPUT_MOUSE=0`, `INPUT_KEYBOARD=1`, `INPUT_HARDWARE=2`).
   - `src/kutomoto/automation/win32_input.py`: `send_click(x, y, button, count)`, `send_mouse_move(x, y)`, `send_text(text, delay_ms, use_clipboard_threshold)` with `KEYEVENTF_UNICODE=0x0004` and surrogate pair support for non-BMP characters, `send_key_press(vk_code_or_name)`, `send_hotkey(modifiers, key)`, `clear_field()` (Ctrl+A -> Backspace), and Unicode clipboard fallback (`OpenClipboard`, `CF_UNICODETEXT`).
   - `src/kutomoto/automation/win32_window.py`: Window enumeration (`EnumWindows`), regex title matching, process executable name matching, client-to-screen coordinate translation (`ClientToScreen`), and focus activation (`AttachThreadInput` + `ShowWindow(SW_RESTORE)` + `BringWindowToTop` + `SetForegroundWindow`).
3. Detail unit testing strategies for ctypes structs, DPI setting, and mocked input calls.
4. Write your report to `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_explorer_1\report.md` and deliver `handoff.md`.


## 2026-11-04T22:58:36Z
[Message] sender=ce2dd708-d288-4e8f-9834-dfdb673a5856
You are m2_explorer_1.
Your working directory is: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_explorer_1
Your task instructions are in: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_explorer_1\DISPATCH.md
Read c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md, c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md, c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md, and your DISPATCH.md.
Formulate the exact implementation blueprint for src/kutomoto/automation/ (win32_core.py, win32_input.py, win32_window.py).
Write your report to c:\Users\daoud\projects\kutomoto\.agents\teamwork\m2_explorer_1\report.md and deliver handoff.md. Report back via send_message when done.
