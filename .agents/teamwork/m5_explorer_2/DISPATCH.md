## 2026-11-05T08:52:54Z
You are m5_explorer_2.
Your working directory: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m5_explorer_2\
Mandatory inputs:
- ORIGINAL_REQUEST.md: c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md
- PROJECT.md: c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md
- docs/SPECIFICATION.md: c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md

Your task:
Investigate and design the technical blueprint for the Sample Windows Desktop Form target in Milestone 5 (`samples/desktop/`):
1. Design `samples/desktop/sample_desktop_form.py` as a standalone Tkinter GUI application representing an enterprise Telecom SIM Card Provisioning / Activation System.
2. The desktop form must include:
   - Window Title: "Telecom SIM Provisioning System — 90Studio" (enabling Win32 title regex matching).
   - Form Fields: Subscriber MSISDN, SIM ICCID (19 digits), Plan Type (Postpaid/Prepaid/Corporate), KYC Verification Status, IMSI, and Action Buttons ("Provision SIM", "Clear Form").
   - Status & Result Display: Visual status label and payload confirmation banner upon successful submission.
   - Distinct, predictable Windows control coordinates and sequential Tab key focus traversal.
   - Headless / programmatic inspection support (e.g., exposing state or automated driver compatibility) for test harnesses.
   - 90Studio branding displayed prominently.
3. Analyze how kutomoto's Win32 ctypes driver (`focus_window`, `get_window_bounds`, `send_click`, `send_text`, `send_key_press`) targets this window.
4. Formulate the exact implementation blueprint for the worker agent.
5. Write your report in handoff.md in your working directory with sections Observation, Logic Chain, Caveats, Conclusion, Verification Method. Report completion to orchestrator via send_message. You must NOT write or modify source code.
