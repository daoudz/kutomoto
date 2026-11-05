# Handoff Report: Sample Windows Desktop Form Target Blueprint (`samples/desktop/sample_desktop_form.py`)

- **Author**: `m5_explorer_2`
- **Working Directory**: `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m5_explorer_2\`
- **Target Component**: `samples/desktop/sample_desktop_form.py` & associated test harnesses
- **Date**: 2026-11-05
- **Attribution**: Copyrights reserved to 90Studio

---

## 1. Observation

### 1.1 Specification & Requirement Baselines
1. **ORIGINAL_REQUEST.md**:
   - Section *Verification & Test Scenarios* (lines 39–41):
     ```markdown
     ### Verification & Test Scenarios
     - [ ] The team provides sample web forms and Windows desktop forms demonstrating end-to-end automated form filling.
     - [ ] Automated execution correctly fills all fields in order and triggers form submission on both sample web and desktop forms.
     ```
   - Section *UI & Branding* (lines 43–45):
     ```markdown
     ### UI & Branding
     - [ ] Application presents a clean, professional user interface suitable for enterprise environments.
     - [ ] The application displays the name "kutomoto" and the attribution "Copyrights reserved to 90Studio".
     ```

2. **PROJECT.md**:
   - Feature Inventory (line 92):
     ```markdown
     | 22 | F22 | Sample Desktop Form Target | Telecom SIM Provisioning Tkinter Form with submission verification | M5 | AC / survey |
     ```
   - Code Layout (lines 201–202):
     ```markdown
     │   └── desktop\
     │       └── sample_desktop_form.py# Telecom SIM Provisioning Tkinter Win32 Form
     ```

3. **docs/SPECIFICATION.md**:
   - Section 11.2 (lines 2084–2099):
     ```markdown
     ### 11.2 Sample Desktop Form Target (`samples/desktop/sample_desktop_form.py`)
     
     - **Domain**: Telecom SIM Provisioning Terminal
     - **Framework**: Python `tkinter` (Native Win32 desktop application window)
     - **Window Title**: `Telecom SIM Provisioning - 90Studio Network Ops`
     - **Fields (6 Controls + Submit)**:
       1. `Subscriber Name`: Entry field
       2. `MSISDN`: Entry field format `555-XXX-XXXX`
       3. `ICCID`: Entry field (19 digits)
       4. `Plan Code`: Combobox (`PREPAID_5G`, `POSTPAID_UNLIMITED`, `CORP_DATA`)
       5. `Active Roaming`: Checkbutton
       6. `Commit Provisioning`: Button
     - **Verification Logic**:
       Upon button click or Enter key, validates field formats. On success, updates GUI status label to:
       `"Status: SIM PROVISIONED SUCCESSFULLY"` and records the transaction to an in-memory verification log.
     ```
   - Dispatch Mission requirement harmonizes and refines the field list:
     - Title: `"Telecom SIM Provisioning System — 90Studio"`
     - Fields: `Subscriber MSISDN`, `SIM ICCID (19 digits)`, `Plan Type (Postpaid/Prepaid/Corporate)`, `KYC Verification Status`, `IMSI`, and Action Buttons (`"Provision SIM"`, `"Clear Form"`).
     - Visual status label and payload confirmation banner upon successful submission.
     - Sequential Tab traversal and predictable coordinates.

### 1.2 Host Environment & Python Runtime Verification
Direct command execution verified the runtime dependencies on the target Windows system:
1. **Tkinter Availability**:
   - Tool Command: `python -c "import tkinter; root = tkinter.Tk(); root.withdraw(); print('Tkinter version:', tkinter.TkVersion); root.destroy()"`
   - Result: `Tkinter version: 8.6` (exit code 0). Standard library Tkinter is fully available.
2. **TTK Themes**:
   - Result: `('winnative', 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative')`.
3. **Per-Monitor V2 High-DPI Awareness**:
   - Tool Command: `cmd /c "set PYTHONPATH=src && python -c ""from kutomoto.automation.win32_core import set_process_dpi_awareness; print('DPI mode:', set_process_dpi_awareness())"""`
   - Result: `DPI mode: PER_MONITOR_V2` (exit code 0). Tkinter windows render 1:1 in physical device pixels when initialized after DPI context configuration.

### 1.3 Critical Win32 Driver Adapter Bugs Observed
During investigation of the Win32 driver interaction with desktop windows, two latent bugs in the codebase were identified that will block real desktop window automation if unaddressed:

#### Bug 1: `ProductionDriverAdapter.find_window` Return Type Mismatch
- **Location**: `src/kutomoto/server/app.py` lines 82–92:
  ```python
  def find_window(
      self,
      title_pattern: str,
      match_mode: str = "contains",
      process_name: Optional[str] = None,
  ) -> Optional[int]:
      return self._window.find_window(
          title_pattern=title_pattern,
          match_mode=match_mode,
          exe_name=process_name,
      )
  ```
- **Observed Behavior**: `self._window.find_window` returns `Optional[WindowInfo]` (a dataclass), NOT an integer `HWND`.
- **Downstream Failure**: When `WorkflowRunner._execute_focus_window` in `src/kutomoto/engine/runner.py` executes:
  ```python
  hwnd = self._driver.find_window(pattern, match_mode=mode_str, process_name=proc)
  ctx.target_hwnd = hwnd
  success = self._driver.focus_window(hwnd)
  ```
  Passing `hwnd` (which is a `WindowInfo` instance) to `user32.IsWindow(hwnd)` causes:
  `ctypes.ArgumentError: argument 1: TypeError: 'WindowInfo' object cannot be interpreted as ctypes.c_void_p`.
- **Verified via Terminal**:
  ```
  ctypes.ArgumentError: argument 1: TypeError: 'WindowInfo' object cannot be interpreted as ctypes.c_void_p
  ```
- **Required Fix**: `ProductionDriverAdapter.find_window` must return `win_info.hwnd if win_info else None`.

#### Bug 2: `get_foreground_window` Unhandled `None` Type Error
- **Location**: `src/kutomoto/automation/win32_window.py` line 335:
  ```python
  def get_foreground_window() -> int:
      """Returns HWND of the currently active foreground window."""
      if user32 is None:
          return 0
      return int(user32.GetForegroundWindow())
  ```
- **Observed Behavior**: `user32.GetForegroundWindow.restype = wintypes.HWND` (defined in `win32_core.py` line 383). When Windows has no foreground window or during desktop locks, `GetForegroundWindow()` returns NULL (`c_void_p(0)`), which ctypes unmarshals to Python `None`.
- **Downstream Failure**: `int(None)` raises:
  `TypeError: int() argument must be a string, a bytes-like object or a real number, not 'NoneType'`.
- **Verified via Terminal**: Observed when running `win32_window.get_foreground_window()` without an active GUI window.
- **Required Fix**:
  ```python
  fg = user32.GetForegroundWindow()
  return int(fg) if fg else 0
  ```

---

## 2. Logic Chain

### 2.1 Domain & Requirements Derivation
1. The target application is an enterprise **Telecom SIM Card Provisioning / Activation Terminal**.
2. To allow kutomoto's automation core to find the window via regex or contains matching, the window title must be:
   `"Telecom SIM Provisioning System — 90Studio"`.
   Regex pattern: `r".*Telecom SIM Provisioning.*"`.
3. To represent realistic enterprise telecom workflows, 5 key data attributes and 2 primary actions are required:
   - `Subscriber MSISDN`: Standard E.164 phone number format (e.g., `+1-555-0199` or `555-019-2834`).
   - `SIM ICCID`: 19 or 20 numeric digits conforming to ITU-T E.118 (e.g., `8901410321111851072`).
   - `Plan Type`: Combobox selection (`Postpaid Unlimited`, `Prepaid 5G`, `Corporate Data`).
   - `KYC Verification Status`: Combobox selection (`VERIFIED`, `PENDING_REVIEW`, `CORPORATE_EXEMPT`).
   - `IMSI`: 14 or 15 numeric digits conforming to ITU-T E.212 (e.g., `310410123456789`).
   - Action Buttons: `"Provision SIM"` (Primary submission) and `"Clear Form"` (Reset).
4. Validation & Feedback:
   - Success condition: All 5 fields valid. Status updates to `"Status: SIM PROVISIONED SUCCESSFULLY"` (green), and a result banner opens displaying the committed transaction payload JSON with timestamp and transaction ID.
   - Failure condition: Validation error displayed in red, e.g. `"Status: Validation Error - ICCID must be 19-20 numeric digits"`.
   - Clear condition: Resets all fields, sets status to `"Status: Form Cleared — Ready for input"`.

### 2.2 Predictable Coordinate Geometry Design
1. In GUI automation, coordinate drift occurs when windows are freely resizable or layouts use fluid wrapping.
2. By fixing the client area dimensions to $640 \times 580$ pixels (`geometry("640x580")` and `resizable(False, False)`), widget positions relative to the client area remain 100% constant across all Windows machines.
3. Using Tkinter's `place()` geometry manager guarantees pixel-accurate coordinate positioning down to a single pixel:

| Control Index | Widget Name | Control Type | Client Rect $(x, y, w, h)$ | Center Client $(cx, cy)$ | Center Normalized $(u, v)$ |
|:---:|:---|:---|:---:|:---:|:---:|
| 1 | `entry_msisdn` | `ttk.Entry` | $(220, 90, 360, 28)$ | $(400, 104)$ | $(0.625, 0.179)$ |
| 2 | `entry_iccid` | `ttk.Entry` | $(220, 135, 360, 28)$ | $(400, 149)$ | $(0.625, 0.257)$ |
| 3 | `combo_plan` | `ttk.Combobox` | $(220, 180, 360, 28)$ | $(400, 194)$ | $(0.625, 0.334)$ |
| 4 | `combo_kyc` | `ttk.Combobox` | $(220, 225, 360, 28)$ | $(400, 239)$ | $(0.625, 0.412)$ |
| 5 | `entry_imsi` | `ttk.Entry` | $(220, 270, 360, 28)$ | $(400, 284)$ | $(0.625, 0.490)$ |
| 6 | `btn_provision`| `ttk.Button` | $(220, 315, 175, 34)$ | $(307, 332)$ | $(0.480, 0.572)$ |
| 7 | `btn_clear` | `ttk.Button` | $(405, 315, 175, 34)$ | $(492, 332)$ | $(0.769, 0.572)$ |

### 2.3 Deterministic Sequential Tab Traversal
1. In Tkinter, the internal focus traversal (`tk::TabToWindow` / `tk_focusNext()`) strictly follows the widget instantiation order in the parent container.
2. By creating widgets in the exact sequence:
   `entry_msisdn` $\to$ `entry_iccid` $\to$ `combo_plan` $\to$ `combo_kyc` $\to$ `entry_imsi` $\to$ `btn_provision` $\to$ `btn_clear`,
   and setting `takefocus=0` on all descriptive labels, headers, and frames, pressing Tab sequentially navigates from Field 1 through Field 7 without any focus traps.
3. On application startup, `entry_msisdn.focus_set()` is invoked. When kutomoto activates the window, keyboard focus is immediately positioned inside Field 1.
4. Binding `<Return>` to `self._on_submit` ensures Enter-key form submission (`SubmitMethod.ENTER_KEY`) is fully supported.

### 2.4 Programmatic & Headless Inspection for Test Harnesses
1. Tests running in CI or automated pytest suites need to verify state changes without depending exclusively on screen scraping.
2. The application class `TelecomProvisioningForm` provides:
   - `get_state() -> Dict[str, Any]`: Exposes `msisdn`, `iccid`, `plan_type`, `kyc_status`, `imsi`, `status_text`, `is_submitted`, `submission_count`, `last_payload`, and `errors`.
   - `set_field(field_name, value)`: Programmatic field setter.
   - `get_control_coordinates() -> Dict[str, Dict[str, Any]]`: Returns bounding rects and normalized coordinates for test verification.
   - `submit() -> bool` & `clear() -> None`: Programmatic triggers.
3. CLI Options for Subprocess / Remote Harnesses:
   - `--state-file <path>`: Whenever the application initializes or changes state (submit, clear), it dumps its full state to `<path>` as atomic JSON. Subprocess test runners can poll or inspect this file without IPC complications.
   - `--headless`: Calls `root.withdraw()` so the window exists offscreen for headless environments.
   - `--geometry <geometry>`: Overrides launch position/size.

### 2.5 Win32 Automation Call Chain Interaction
kutomoto's automation engine interacts with this window via the following verified sequence:
1. `find_window`: `EnumWindows` finds window where `re.search(r".*Telecom SIM Provisioning.*", title)` matches.
2. `focus_window`: `AttachThreadInput` + `ShowWindow(SW_RESTORE)` + simulated Alt tap + `SetForegroundWindow` brings window to foreground and verifies foreground focus.
3. `normalized_to_screen_coords`: Translates $(u, v)$ normalized coordinates to physical screen coordinates $(x_{screen}, y_{screen})$ using `ClientToScreen` and `GetClientRect`.
4. `send_click`: `SetCursorPos` + `SendInput(MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_LEFTUP)` clicks entry or button.
5. `send_text`: Decomposes text to UTF-16 code units and injects via `KEYEVENTF_UNICODE`.
6. `send_key_press`: Injects virtual key codes for Tab (`0x09`) and Enter (`0x0D`).
7. `clear_field`: Injects `Ctrl+A` followed by `Backspace`.

---

## 3. Caveats

1. **Driver Bug Remediation Required**:
   The worker agent implementing Milestone 5 must apply the 2 one-line fixes identified in Section 1.3:
   - In `src/kutomoto/server/app.py`: `ProductionDriverAdapter.find_window` must return `win.hwnd if win else None`.
   - In `src/kutomoto/automation/win32_window.py`: `get_foreground_window` must guard `int(fg) if fg else 0`.
   Without these fixes, `WorkflowRunner` will fail when executing against real Win32 windows using the production adapter.
2. **Interactive vs Headless CI Execution**:
   Win32 `SendInput` requires an active Windows interactive desktop session (Winlogon Session 1+). If run in a headless Windows Server container (Session 0) without a GUI session, `SendInput` events are dropped by the OS security subsystem. Therefore, `tests/test_e2e_automation.py` must support both live hardware Win32 execution (when interactive) and programmatic/headless execution via the form's inspection API.
3. **Tkinter Combobox Keyboard Behavior**:
   In Tkinter, typing directly into a `ttk.Combobox` replaces its string value, which is fully compatible with `send_text`. Alternatively, down-arrow key navigation or coordinate clicking can be used.

---

## 4. Conclusion & Technical Implementation Blueprint

### 4.1 Target File Placement
- `samples/desktop/sample_desktop_form.py`
- Accompanying package init files: `samples/__init__.py`, `samples/desktop/__init__.py`.

### 4.2 Complete Source Code Blueprint for `samples/desktop/sample_desktop_form.py`

The worker agent should implement `samples/desktop/sample_desktop_form.py` adhering to the following complete, production-ready specification:

```python
"""
samples.desktop.sample_desktop_form
Standalone Tkinter GUI application representing an enterprise Telecom SIM Card
Provisioning & Activation System. Designed as a verification target for kutomoto
Windows automation workflows.

Copyrights reserved to 90Studio
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
import sys
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("sample_desktop_form")

# Window Title enables Win32 title regex / contains matching
WINDOW_TITLE = "Telecom SIM Provisioning System — 90Studio"
DEFAULT_GEOMETRY = "640x580+100+100"
CANVAS_WIDTH = 640
CANVAS_HEIGHT = 580

PLAN_OPTIONS = ["Prepaid 5G", "Postpaid Unlimited", "Corporate Data"]
KYC_OPTIONS = ["VERIFIED", "PENDING_REVIEW", "CORPORATE_EXEMPT"]

# Exact Predictable Coordinate Layout (Client Coordinates)
CONTROL_GEOMETRY: Dict[str, Dict[str, Any]] = {
    "entry_msisdn": {
        "label": "Subscriber MSISDN",
        "rect": (220, 90, 360, 28),
        "center_client": (400, 104),
        "center_normalized": (400 / 640, 104 / 580),
        "tab_index": 1,
    },
    "entry_iccid": {
        "label": "SIM ICCID (19 digits)",
        "rect": (220, 135, 360, 28),
        "center_client": (400, 149),
        "center_normalized": (400 / 640, 149 / 580),
        "tab_index": 2,
    },
    "combo_plan": {
        "label": "Plan Type",
        "rect": (220, 180, 360, 28),
        "center_client": (400, 194),
        "center_normalized": (400 / 640, 194 / 580),
        "tab_index": 3,
    },
    "combo_kyc": {
        "label": "KYC Verification Status",
        "rect": (220, 225, 360, 28),
        "center_client": (400, 239),
        "center_normalized": (400 / 640, 239 / 580),
        "tab_index": 4,
    },
    "entry_imsi": {
        "label": "IMSI (15 digits)",
        "rect": (220, 270, 360, 28),
        "center_client": (400, 284),
        "center_normalized": (400 / 640, 284 / 580),
        "tab_index": 5,
    },
    "btn_provision": {
        "label": "Provision SIM",
        "rect": (220, 315, 175, 34),
        "center_client": (307, 332),
        "center_normalized": (307 / 640, 332 / 580),
        "tab_index": 6,
    },
    "btn_clear": {
        "label": "Clear Form",
        "rect": (405, 315, 175, 34),
        "center_client": (492, 332),
        "center_normalized": (492 / 640, 332 / 580),
        "tab_index": 7,
    },
}


class TelecomProvisioningForm(tk.Tk):
    """
    Enterprise Telecom SIM Card Provisioning Form GUI.
    Provides visual status display, confirmation banner, predictable coordinates,
    sequential Tab traversal, and full programmatic inspection support.
    """

    def __init__(
        self,
        state_file: Optional[Path | str] = None,
        headless: bool = False,
        geometry: Optional[str] = None,
    ) -> None:
        super().__init__()

        self.title(WINDOW_TITLE)
        self.geometry(geometry or DEFAULT_GEOMETRY)
        self.resizable(False, False)
        self.configure(bg="#f8fafc")

        self.state_file: Optional[Path] = Path(state_file) if state_file else None
        self.headless: bool = headless

        # Form Variables
        self.var_msisdn = tk.StringVar(value="")
        self.var_iccid = tk.StringVar(value="")
        self.var_plan = tk.StringVar(value="Prepaid 5G")
        self.var_kyc = tk.StringVar(value="VERIFIED")
        self.var_imsi = tk.StringVar(value="")
        self.var_status = tk.StringVar(value="Status: Ready for input")

        # Internal State Tracking
        self._is_submitted: bool = False
        self._submission_count: int = 0
        self._last_payload: Optional[Dict[str, Any]] = None
        self._last_errors: List[str] = []

        self._build_ui()
        self._setup_bindings()

        if self.headless:
            self.withdraw()
            self.update_idletasks()

        self._export_state()

    def _build_ui(self) -> None:
        # Style configuration
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#1e3a8a", background="#f8fafc")
        style.configure("SubHeader.TLabel", font=("Segoe UI", 9), foreground="#475569", background="#f8fafc")
        style.configure("FieldLabel.TLabel", font=("Segoe UI", 10), foreground="#1e293b", background="#f8fafc")
        style.configure("Status.TLabel", font=("Segoe UI", 10, "bold"), background="#f8fafc")
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Secondary.TButton", font=("Segoe UI", 10))

        # 1. Header Frame (y = 0..75)
        lbl_title = ttk.Label(self, text="Telecom SIM Provisioning System", style="Header.TLabel", takefocus=0)
        lbl_title.place(x=30, y=14)

        lbl_subtitle = ttk.Label(
            self,
            text="90Studio Enterprise Network Operations — Terminal v1.0",
            style="SubHeader.TLabel",
            takefocus=0,
        )
        lbl_subtitle.place(x=30, y=42)

        sep = ttk.Separator(self, orient="horizontal")
        sep.place(x=30, y=72, width=580)

        # 2. Form Labels (takefocus=0)
        ttk.Label(self, text="Subscriber MSISDN:", style="FieldLabel.TLabel", takefocus=0).place(x=30, y=94)
        ttk.Label(self, text="SIM ICCID (19 digits):", style="FieldLabel.TLabel", takefocus=0).place(x=30, y=139)
        ttk.Label(self, text="Plan Type:", style="FieldLabel.TLabel", takefocus=0).place(x=30, y=184)
        ttk.Label(self, text="KYC Verification Status:", style="FieldLabel.TLabel", takefocus=0).place(x=30, y=229)
        ttk.Label(self, text="IMSI (15 digits):", style="FieldLabel.TLabel", takefocus=0).place(x=30, y=274)

        # 3. Form Input Controls — Created STRICTLY in sequential Tab order (1..7)
        # Control 1: MSISDN Entry
        self.entry_msisdn = ttk.Entry(self, textvariable=self.var_msisdn, font=("Segoe UI", 10))
        self.entry_msisdn.place(x=220, y=90, width=360, height=28)

        # Control 2: ICCID Entry
        self.entry_iccid = ttk.Entry(self, textvariable=self.var_iccid, font=("Segoe UI", 10))
        self.entry_iccid.place(x=220, y=135, width=360, height=28)

        # Control 3: Plan Type Combobox
        self.combo_plan = ttk.Combobox(
            self,
            textvariable=self.var_plan,
            values=PLAN_OPTIONS,
            font=("Segoe UI", 10),
        )
        self.combo_plan.place(x=220, y=180, width=360, height=28)

        # Control 4: KYC Status Combobox
        self.combo_kyc = ttk.Combobox(
            self,
            textvariable=self.var_kyc,
            values=KYC_OPTIONS,
            font=("Segoe UI", 10),
        )
        self.combo_kyc.place(x=220, y=225, width=360, height=28)

        # Control 5: IMSI Entry
        self.entry_imsi = ttk.Entry(self, textvariable=self.var_imsi, font=("Segoe UI", 10))
        self.entry_imsi.place(x=220, y=270, width=360, height=28)

        # Control 6: Provision SIM Button (Primary)
        self.btn_provision = ttk.Button(
            self,
            text="Provision SIM",
            command=self._on_submit,
            style="Primary.TButton",
        )
        self.btn_provision.place(x=220, y=315, width=175, height=34)

        # Control 7: Clear Form Button (Secondary)
        self.btn_clear = ttk.Button(
            self,
            text="Clear Form",
            command=self._on_clear,
            style="Secondary.TButton",
        )
        self.btn_clear.place(x=405, y=315, width=175, height=34)

        # 4. Status Indicator Label (y = 360)
        self.lbl_status = tk.Label(
            self,
            textvariable=self.var_status,
            font=("Segoe UI", 10, "bold"),
            fg="#2563eb",
            bg="#f8fafc",
            anchor="w",
            takefocus=0,
        )
        self.lbl_status.place(x=30, y=360, width=580, height=24)

        # 5. Payload Confirmation Banner / Result Card (y = 390..535)
        self.banner_frame = tk.Frame(self, bg="#ffffff", highlightthickness=1, highlightbackground="#cbd5e1")
        self.banner_frame.place(x=30, y=390, width=580, height=140)

        self.lbl_banner_title = tk.Label(
            self.banner_frame,
            text="Awaiting SIM provisioning submission...",
            font=("Segoe UI", 10, "bold"),
            fg="#64748b",
            bg="#ffffff",
            anchor="w",
            takefocus=0,
        )
        self.lbl_banner_title.place(x=12, y=8, width=550)

        self.txt_payload = tk.Text(
            self.banner_frame,
            font=("Consolas", 8),
            bg="#f8fafc",
            fg="#334155",
            relief="flat",
            takefocus=0,
            wrap="none",
        )
        self.txt_payload.place(x=12, y=32, width=554, height=96)
        self.txt_payload.insert("1.0", "No active transaction payload recorded.")
        self.txt_payload.configure(state="disabled")

        # 6. Footer Attribution (y = 550)
        lbl_footer = tk.Label(
            self,
            text="kutomoto Automation Target — Copyrights reserved to 90Studio",
            font=("Segoe UI", 8, "italic"),
            fg="#94a3b8",
            bg="#f8fafc",
            takefocus=0,
        )
        lbl_footer.place(x=30, y=550, width=580)

        # Initial Focus Set on Field 1
        self.entry_msisdn.focus_set()

    def _setup_bindings(self) -> None:
        self.bind("<Return>", self._on_submit)

    def validate_form(self) -> Tuple[bool, List[str], Dict[str, Any]]:
        errors: List[str] = []
        msisdn = self.var_msisdn.get().strip()
        iccid = self.var_iccid.get().strip()
        plan = self.var_plan.get().strip()
        kyc = self.var_kyc.get().strip()
        imsi = self.var_imsi.get().strip()

        # MSISDN: 7-15 digits
        digits_msisdn = re.sub(r"\D", "", msisdn)
        if not digits_msisdn or len(digits_msisdn) < 7 or len(digits_msisdn) > 15:
            errors.append("MSISDN must contain 7-15 digits (e.g. 555-019-2834)")

        # ICCID: Exactly 19 or 20 digits
        if not re.match(r"^\d{19,20}$", iccid):
            errors.append("SIM ICCID must be 19 or 20 numeric digits")

        # Plan Type: Valid option
        if not plan:
            errors.append("Plan Type must be selected")

        # KYC: Valid option
        if not kyc:
            errors.append("KYC Verification Status must be selected")

        # IMSI: 14-15 digits
        if not re.match(r"^\d{14,15}$", imsi):
            errors.append("IMSI must be 14 or 15 numeric digits")

        payload = {
            "msisdn": msisdn,
            "iccid": iccid,
            "plan_type": plan,
            "kyc_status": kyc,
            "imsi": imsi,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "ACTIVE" if not errors else "REJECTED",
            "transaction_id": f"SIM-TX-{abs(hash(iccid + msisdn)) % 100000000:08d}",
        }

        return len(errors) == 0, errors, payload

    def _on_submit(self, event: Optional[Any] = None) -> None:
        is_valid, errors, payload = self.validate_form()
        self._last_errors = errors

        if is_valid:
            self._is_submitted = True
            self._submission_count += 1
            self._last_payload = payload

            self.var_status.set("Status: SIM PROVISIONED SUCCESSFULLY")
            self.lbl_status.configure(fg="#16a34a")

            self.banner_frame.configure(highlightbackground="#86efac", bg="#f0fdf4")
            self.lbl_banner_title.configure(
                text=f"✓ Provisioning Confirmed — Transaction #{payload['transaction_id']}",
                fg="#15803d",
                bg="#f0fdf4",
            )

            self.txt_payload.configure(state="normal", bg="#ffffff", fg="#0f172a")
            self.txt_payload.delete("1.0", "end")
            self.txt_payload.insert("1.0", json.dumps(payload, indent=2))
            self.txt_payload.configure(state="disabled")
        else:
            self._is_submitted = False
            first_err = errors[0] if errors else "Invalid form data"
            self.var_status.set(f"Status: Validation Error - {first_err}")
            self.lbl_status.configure(fg="#dc2626")

            self.banner_frame.configure(highlightbackground="#fca5a5", bg="#fef2f2")
            self.lbl_banner_title.configure(
                text="✗ Provisioning Failed — Corrections Required",
                fg="#b91c1c",
                bg="#fef2f2",
            )
            self.txt_payload.configure(state="normal", bg="#ffffff", fg="#991b1b")
            self.txt_payload.delete("1.0", "end")
            self.txt_payload.insert("1.0", "\n".join(f"• {e}" for e in errors))
            self.txt_payload.configure(state="disabled")

        self._export_state()

    def _on_clear(self, event: Optional[Any] = None) -> None:
        self.var_msisdn.set("")
        self.var_iccid.set("")
        self.var_plan.set("Prepaid 5G")
        self.var_kyc.set("VERIFIED")
        self.var_imsi.set("")
        self.var_status.set("Status: Form Cleared — Ready for input")
        self.lbl_status.configure(fg="#2563eb")

        self._is_submitted = False
        self._last_payload = None
        self._last_errors = []

        self.banner_frame.configure(highlightbackground="#cbd5e1", bg="#ffffff")
        self.lbl_banner_title.configure(
            text="Awaiting SIM provisioning submission...",
            fg="#64748b",
            bg="#ffffff",
        )
        self.txt_payload.configure(state="normal", bg="#f8fafc", fg="#334155")
        self.txt_payload.delete("1.0", "end")
        self.txt_payload.insert("1.0", "No active transaction payload recorded.")
        self.txt_payload.configure(state="disabled")

        self.entry_msisdn.focus_set()
        self._export_state()

    def _export_state(self) -> None:
        if not self.state_file:
            return
        state = self.get_state()
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to export form state to %s: %s", self.state_file, e)

    # --------------------------------------------------------------------------
    # Programmatic Inspection & Test Harness Interface
    # --------------------------------------------------------------------------

    def get_state(self) -> Dict[str, Any]:
        return {
            "window_title": self.title(),
            "msisdn": self.var_msisdn.get(),
            "iccid": self.var_iccid.get(),
            "plan_type": self.var_plan.get(),
            "kyc_status": self.var_kyc.get(),
            "imsi": self.var_imsi.get(),
            "status_text": self.var_status.get(),
            "is_submitted": self._is_submitted,
            "submission_count": self._submission_count,
            "last_payload": self._last_payload,
            "errors": self._last_errors,
        }

    def set_field(self, field_name: str, value: Any) -> None:
        val = str(value)
        if field_name == "msisdn":
            self.var_msisdn.set(val)
        elif field_name == "iccid":
            self.var_iccid.set(val)
        elif field_name == "plan_type":
            self.var_plan.set(val)
        elif field_name == "kyc_status":
            self.var_kyc.set(val)
        elif field_name == "imsi":
            self.var_imsi.set(val)
        else:
            raise KeyError(f"Unknown field name: {field_name}")
        self._export_state()

    def submit(self) -> bool:
        self._on_submit()
        return self._is_submitted

    def clear(self) -> None:
        self._on_clear()

    @staticmethod
    def get_control_coordinates() -> Dict[str, Dict[str, Any]]:
        return dict(CONTROL_GEOMETRY)


def create_app(
    state_file: Optional[Path | str] = None,
    headless: bool = False,
    geometry: Optional[str] = None,
) -> TelecomProvisioningForm:
    """Factory function for test fixture instantiation."""
    return TelecomProvisioningForm(state_file=state_file, headless=headless, geometry=geometry)


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Telecom SIM Provisioning Desktop Form — 90Studio")
    parser.add_argument("--state-file", type=str, default=None, help="Path to dump JSON state file")
    parser.add_argument("--headless", action="store_true", help="Launch without visible display window")
    parser.add_argument("--geometry", type=str, default=None, help="Window geometry WxH+X+Y")
    args = parser.parse_args(argv)

    app = create_app(state_file=args.state_file, headless=args.headless, geometry=args.geometry)
    app.mainloop()


if __name__ == "__main__":
    main()
```

### 4.3 Pre-configured Automation Workflow Payload
To allow immediate end-to-end execution, the worker agent should also save `data/workflows/telecom_sim_provisioning_workflow.json` (or include it in `test_e2e_automation.py`):

```json
{
  "schema_version": "1.0.0",
  "id": "telecom-sim-provisioning-e2e-001",
  "name": "Telecom SIM Provisioning Flow",
  "description": "Automated provisioning of 5G SIM card into Telecom Provisioning Terminal",
  "author": "90Studio QA Engineer",
  "copyright": "Copyrights reserved to 90Studio",
  "source_mode": "manual_step_flow",
  "target_application": {
    "type": "desktop_window",
    "window_title_pattern": "Telecom SIM Provisioning System — 90Studio",
    "process_name": "python.exe",
    "match_mode": "contains"
  },
  "execution_settings": {
    "countdown_seconds": 0,
    "default_step_delay_ms": 10,
    "typing_speed_ms": 5,
    "stop_on_error": true,
    "error_recovery_policy": "abort",
    "failsafe_corner_enabled": true,
    "abort_hotkey": "Escape"
  },
  "variables": [],
  "steps": [
    {
      "step_id": "step-focus",
      "sequence_index": 1,
      "label": "Focus Telecom Terminal Window",
      "action_type": "focus_window",
      "enabled": true,
      "parameters": {
        "window_title_pattern": "Telecom SIM Provisioning System — 90Studio",
        "match_mode": "contains"
      }
    },
    {
      "step_id": "step-click-msisdn",
      "sequence_index": 2,
      "label": "Click MSISDN Field",
      "action_type": "click",
      "enabled": true,
      "parameters": {
        "coordinate_mode": "normalized",
        "norm_x": 0.625,
        "norm_y": 0.179
      }
    },
    {
      "step_id": "step-type-msisdn",
      "sequence_index": 3,
      "label": "Enter MSISDN",
      "action_type": "type_text",
      "enabled": true,
      "parameters": { "text": "555-019-2834" }
    },
    {
      "step_id": "step-tab-1",
      "sequence_index": 4,
      "label": "Tab to ICCID",
      "action_type": "key_press",
      "enabled": true,
      "parameters": { "key": "tab" }
    },
    {
      "step_id": "step-type-iccid",
      "sequence_index": 5,
      "label": "Enter SIM ICCID",
      "action_type": "type_text",
      "enabled": true,
      "parameters": { "text": "8901410321111851072" }
    },
    {
      "step_id": "step-tab-2",
      "sequence_index": 6,
      "label": "Tab to Plan Type",
      "action_type": "key_press",
      "enabled": true,
      "parameters": { "key": "tab" }
    },
    {
      "step_id": "step-type-plan",
      "sequence_index": 7,
      "label": "Select Plan Type",
      "action_type": "type_text",
      "enabled": true,
      "parameters": { "text": "Postpaid Unlimited" }
    },
    {
      "step_id": "step-tab-3",
      "sequence_index": 8,
      "label": "Tab to KYC Status",
      "action_type": "key_press",
      "enabled": true,
      "parameters": { "key": "tab" }
    },
    {
      "step_id": "step-type-kyc",
      "sequence_index": 9,
      "label": "Confirm KYC Status",
      "action_type": "type_text",
      "enabled": true,
      "parameters": { "text": "VERIFIED" }
    },
    {
      "step_id": "step-tab-4",
      "sequence_index": 10,
      "label": "Tab to IMSI",
      "action_type": "key_press",
      "enabled": true,
      "parameters": { "key": "tab" }
    },
    {
      "step_id": "step-type-imsi",
      "sequence_index": 11,
      "label": "Enter IMSI",
      "action_type": "type_text",
      "enabled": true,
      "parameters": { "text": "310410123456789" }
    },
    {
      "step_id": "step-tab-5",
      "sequence_index": 12,
      "label": "Tab to Provision Button",
      "action_type": "key_press",
      "enabled": true,
      "parameters": { "key": "tab" }
    },
    {
      "step_id": "step-submit",
      "sequence_index": 13,
      "label": "Trigger Provision SIM",
      "action_type": "key_press",
      "enabled": true,
      "parameters": { "key": "enter" }
    }
  ]
}
```

---

## 5. Verification Method

To independently verify the implementation after the worker writes the code:

### 5.1 Verification Commands
1. **Module Import & Headless State Check**:
   ```powershell
   python -c "from samples.desktop.sample_desktop_form import TelecomProvisioningForm; app = TelecomProvisioningForm(headless=True); app.set_field('msisdn', '555-019-2834'); app.set_field('iccid', '8901410321111851072'); app.set_field('imsi', '310410123456789'); assert app.submit() is True; assert app.get_state()['status_text'] == 'Status: SIM PROVISIONED SUCCESSFULLY'; print('Verification passed'); app.destroy()"
   ```
2. **Tab Traversal Determinism Check**:
   ```powershell
   python -c "from samples.desktop.sample_desktop_form import TelecomProvisioningForm; app = TelecomProvisioningForm(headless=True); cur = app.entry_msisdn; seq = [cur]; [seq.append(seq[-1].tk_focusNext()) for _ in range(6)]; expected = [app.entry_msisdn, app.entry_iccid, app.combo_plan, app.combo_kyc, app.entry_imsi, app.btn_provision, app.btn_clear]; assert seq == expected, 'Tab traversal order mismatch'; print('Tab traversal verified'); app.destroy()"
   ```
3. **Control Coordinate Verification**:
   ```powershell
   python -c "from samples.desktop.sample_desktop_form import TelecomProvisioningForm; app = TelecomProvisioningForm(headless=True); coords = app.get_control_coordinates(); assert 'entry_msisdn' in coords and 'btn_provision' in coords; print('Coordinates verified:', coords['btn_provision']['center_normalized']); app.destroy()"
   ```
4. **Comprehensive Pytest Suite Execution**:
   ```powershell
   pytest tests/test_e2e_automation.py -v
   pytest tests/test_win32_driver.py -v
   ```

### 5.2 Invalidation Conditions
The blueprint is invalidated if:
1. Tkinter is replaced by an external dependency not present in standard Python on Windows.
2. The window title changes in a way that breaks regex matching `r".*Telecom SIM Provisioning.*"`.
3. Widget creation order is altered such that sequential Tab traversal deviates from Field 1 through Field 7.
4. Dynamic window resizing alters control normalized coordinates without maintaining fixed client bounds.
