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
import os
from pathlib import Path
import re
import sys
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("sample_desktop_form")


def _ensure_tcl_tk_env() -> None:
    """Configures TCL_LIBRARY and TK_LIBRARY environment variables if not set."""
    prefix = Path(sys.prefix)
    tcl_dir = prefix / "tcl" / "tcl8.6"
    tk_dir = prefix / "tcl" / "tk8.6"
    if tcl_dir.exists() and ("TCL_LIBRARY" not in os.environ or "\\" in os.environ.get("TCL_LIBRARY", "")):
        os.environ["TCL_LIBRARY"] = tcl_dir.as_posix()
    if tk_dir.exists() and ("TK_LIBRARY" not in os.environ or "\\" in os.environ.get("TK_LIBRARY", "")):
        os.environ["TK_LIBRARY"] = tk_dir.as_posix()

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
        "x": 220,
        "y": 90,
        "width": 360,
        "height": 28,
        "center_client": (400, 104),
        "center_normalized": (400 / 640, 104 / 580),
        "norm_x": 400 / 640,
        "norm_y": 104 / 580,
        "tab_index": 1,
    },
    "entry_iccid": {
        "label": "SIM ICCID (19 digits)",
        "rect": (220, 135, 360, 28),
        "x": 220,
        "y": 135,
        "width": 360,
        "height": 28,
        "center_client": (400, 149),
        "center_normalized": (400 / 640, 149 / 580),
        "norm_x": 400 / 640,
        "norm_y": 149 / 580,
        "tab_index": 2,
    },
    "combo_plan": {
        "label": "Plan Type",
        "rect": (220, 180, 360, 28),
        "x": 220,
        "y": 180,
        "width": 360,
        "height": 28,
        "center_client": (400, 194),
        "center_normalized": (400 / 640, 194 / 580),
        "norm_x": 400 / 640,
        "norm_y": 194 / 580,
        "tab_index": 3,
    },
    "combo_kyc": {
        "label": "KYC Verification Status",
        "rect": (220, 225, 360, 28),
        "x": 220,
        "y": 225,
        "width": 360,
        "height": 28,
        "center_client": (400, 239),
        "center_normalized": (400 / 640, 239 / 580),
        "norm_x": 400 / 640,
        "norm_y": 239 / 580,
        "tab_index": 4,
    },
    "entry_imsi": {
        "label": "IMSI (15 digits)",
        "rect": (220, 270, 360, 28),
        "x": 220,
        "y": 270,
        "width": 360,
        "height": 28,
        "center_client": (400, 284),
        "center_normalized": (400 / 640, 284 / 580),
        "norm_x": 400 / 640,
        "norm_y": 284 / 580,
        "tab_index": 5,
    },
    "btn_provision": {
        "label": "Provision SIM",
        "rect": (220, 315, 175, 34),
        "x": 220,
        "y": 315,
        "width": 175,
        "height": 34,
        "center_client": (307, 332),
        "center_normalized": (307 / 640, 332 / 580),
        "norm_x": 307 / 640,
        "norm_y": 332 / 580,
        "tab_index": 6,
    },
    "btn_clear": {
        "label": "Clear Form",
        "rect": (405, 315, 175, 34),
        "x": 405,
        "y": 315,
        "width": 175,
        "height": 34,
        "center_client": (492, 332),
        "center_normalized": (492 / 640, 332 / 580),
        "norm_x": 492 / 640,
        "norm_y": 332 / 580,
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
        _ensure_tcl_tk_env()
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
        self.var_kyc_status = tk.BooleanVar(value=True)
        self.var_imsi = tk.StringVar(value="")
        self.var_status = tk.StringVar(value="Status: Ready for input")

        # Internal State Tracking
        self._is_submitted: bool = False
        self._submission_count: int = 0
        self._last_payload: Optional[Dict[str, Any]] = None
        self._last_errors: List[str] = []
        self._records: List[Dict[str, Any]] = []

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
        except Exception as exc:
            logger.debug("Failed to set clam theme: %s", exc)

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

        def _select_all_on_focus(event: Any) -> None:
            widget = getattr(event, "widget", None)
            if widget is not None and hasattr(widget, "selection_range"):
                try:
                    self.after_idle(lambda w=widget: w.selection_range(0, tk.END))
                except Exception:
                    pass

        for ctrl in (
            self.entry_msisdn,
            self.entry_iccid,
            self.combo_plan,
            self.combo_kyc,
            self.entry_imsi,
        ):
            ctrl.bind("<FocusIn>", _select_all_on_focus, add="+")
            ctrl.bind("<ButtonRelease-1>", _select_all_on_focus, add="+")

        def _on_kyc_space(event: Any) -> str:
            self.var_kyc.set("VERIFIED")
            self.var_kyc_status.set(True)
            return "break"

        self.combo_kyc.bind("<KeyPress-space>", _on_kyc_space)

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
            "copyright": "Copyrights reserved to 90Studio",
        }

        return len(errors) == 0, errors, payload

    def _on_submit(self, event: Optional[Any] = None) -> None:
        is_valid, errors, payload = self.validate_form()
        self._last_errors = errors

        if is_valid:
            self._is_submitted = True
            self._submission_count += 1
            self._last_payload = payload
            self._records.append(payload)

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
        self.var_kyc_status.set(True)
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
        """Returns complete snapshot of form state."""
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

    def get_status(self) -> str:
        """Returns the current status indicator text."""
        return self.var_status.get()

    def get_provisioned_records(self) -> List[Dict[str, Any]]:
        """Returns history of successfully provisioned records."""
        return list(self._records)

    def set_field(self, field_name: str, value: Any) -> None:
        """Programmatic setter for form fields."""
        val = str(value)
        if field_name == "msisdn":
            self.var_msisdn.set(val)
        elif field_name == "iccid":
            self.var_iccid.set(val)
        elif field_name == "plan_type":
            self.var_plan.set(val)
        elif field_name == "kyc_status":
            self.var_kyc.set(val)
            if isinstance(value, bool):
                self.var_kyc_status.set(value)
        elif field_name == "imsi":
            self.var_imsi.set(val)
        else:
            raise KeyError(f"Unknown field name: {field_name}")
        self._export_state()

    def set_field_value(self, field_name: str, value: Any) -> None:
        """Alias for set_field."""
        self.set_field(field_name, value)

    def submit(self) -> bool:
        """Triggers form submission."""
        self._on_submit()
        return self._is_submitted

    def clear(self) -> None:
        """Resets form state."""
        self._on_clear()

    @staticmethod
    def get_control_coordinates() -> Dict[str, Dict[str, Any]]:
        """Returns fixed coordinate geometry dictionary."""
        return dict(CONTROL_GEOMETRY)


# Class aliases for test compatibility
TelecomSimApp = TelecomProvisioningForm
TelecomSimForm = TelecomProvisioningForm


def create_app(
    state_file: Optional[Path | str] = None,
    headless: bool = False,
    geometry: Optional[str] = None,
) -> TelecomProvisioningForm:
    """Factory function for test fixture instantiation."""
    return TelecomProvisioningForm(state_file=state_file, headless=headless, geometry=geometry)


def main(argv: Optional[List[str]] = None) -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Telecom SIM Provisioning Desktop Form — 90Studio")
    parser.add_argument("--state-file", type=str, default=None, help="Path to dump JSON state file")
    parser.add_argument("--headless", action="store_true", help="Launch without visible display window")
    parser.add_argument("--geometry", type=str, default=None, help="Window geometry WxH+X+Y")
    args = parser.parse_args(argv)

    app = create_app(state_file=args.state_file, headless=args.headless, geometry=args.geometry)
    app.mainloop()


if __name__ == "__main__":
    main()
