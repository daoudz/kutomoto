## 2026-11-05T09:06:10Z
You are m5_worker_1.
Your working directory: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m5_worker_1\
Write ownership: You exclusively own `samples/web/`, `samples/desktop/`, `src/kutomoto/automation/win32_window.py`, `src/kutomoto/automation/win32_driver.py`, and `tests/test_e2e_automation.py`.

Mandatory inputs:
- ORIGINAL_REQUEST.md: c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md
- PROJECT.md: c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md
- Explorer 1 handoff: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m5_explorer_1\handoff.md
- Explorer 2 handoff: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m5_explorer_2\handoff.md
- Explorer 3 handoff: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m5_explorer_3\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your task:
Implement Milestone 5 (Sample Target Forms & E2E Automated Verification):
1. `samples/web/`: Implement `samples/web/index.html`, `samples/web/form.js`, and `samples/web/styles.css` per `m5_explorer_1/handoff.md`. Include all 7 fields (Full Name, National ID/SSN, Account Type, Annual Income, Risk Rating, Email, Terms Checkbox), Submit and Reset buttons, sequential tabindex 1-9, dynamic submission confirmation banner `#submission_banner`, and 90Studio attribution branding ("Banking KYC Onboarding — kutomoto Automation Target — Copyrights reserved to 90Studio").
2. `samples/desktop/`: Implement `samples/desktop/sample_desktop_form.py` per `m5_explorer_2/handoff.md`. Standalone Tkinter GUI with window title "Telecom SIM Provisioning System — 90Studio", all 5 fields (MSISDN, SIM ICCID, Plan Type Combobox, KYC Status Combobox, IMSI) and action buttons ("Provision SIM", "Clear Form"), sequential Tab focus, visual status confirmation banner, programmatic inspection API, and CLI flags (--headless, --state-file, --geometry).
3. Driver Adapter Bugfixes: Apply the 2 adapter fixes identified in `m5_explorer_2/handoff.md`:
   - In `src/kutomoto/automation/win32_window.py` / `win32_driver.py`: fix `ProductionDriverAdapter.find_window` returning WindowInfo instead of HWND integer (`window_info.hwnd if window_info else None`), and ensure `get_foreground_window` safely handles None without raising TypeError.
4. `tests/test_e2e_automation.py`: Implement the 18 E2E test cases per `m5_explorer_3/handoff.md`:
   - Scenario 1: Automated form filling on Banking KYC Web Form using both visual designer compiled workflow and manual 21-step action workflow, verifying sequential filling and submission banner.
   - Scenario 2: Automated form filling on Telecom SIM Desktop Form using window targeting, focus switching, sequential coordinate/tab entry, and "Provision SIM" button activation with status verification.
   - Scenario 3: Adversarial and edge case tests (Loss-of-Focus Guardian pause/resume, Escape key abort, Corner Slam failsafe, parameter boundaries, error policies, audit logging stamped with "Copyrights reserved to 90Studio").
   - Dual CI/Live execution support via VirtualTkinterDriver / MockWin32Driver for 100% deterministic passes in CI and live Win32 execution.
5. Verification:
   - Run `python -m pytest tests/test_e2e_automation.py -v` (18/18 passed).
   - Run `python -m pytest tests/` (all 390+ tests passed).
   - Run `python -m ruff check src/ tests/ samples/` (All checks passed!).
   - Confirm 0 bare `pass` statements.
6. Write handoff.md in your working directory with sections Observation, Logic Chain, Caveats, Conclusion, Verification Method.
7. Use send_message to report completion back to the orchestrator.
