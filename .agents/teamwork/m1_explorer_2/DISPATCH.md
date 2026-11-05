# Dispatch for m1_explorer_2

## Objective
Explore and provide the precise technical rules for Win32 automation, DPI scaling, and cross-application targeting to be specified in `docs/SPECIFICATION.md`.

## Inputs
- ORIGINAL_REQUEST path: c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md
- PROJECT.md path: c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md
- Survey tech report: c:\Users\daoud\projects\kutomoto\.agents\teamwork\explorer_survey_2\tech_survey_report.md

## Instructions
1. Read ORIGINAL_REQUEST.md and PROJECT.md.
2. Review the survey technical findings in `tech_survey_report.md`.
3. Formulate the technical specification sections for `docs/SPECIFICATION.md` detailing:
   - Win32 DPI Per-Monitor V2 context mechanics
   - Win32 `SendInput` keyboard & mouse injection specifications (64-bit 40-byte INPUT structs, KEYEVENTF_UNICODE, virtual keys)
   - Window attachment & focus stealing recovery (`AttachThreadInput`, `ShowWindow(SW_RESTORE)`, `SetForegroundWindow`)
   - Cross-application targeting against open web browser tabs (Edge, Chrome, Firefox) and native Windows desktop apps (WinForms, WPF, Tkinter, SAP GUI)
   - Safety guardrails (Escape emergency abort, corner slam failsafe, loss-of-focus guardian)
4. Recommend concrete guidance for the Worker who will author `docs/SPECIFICATION.md`.
5. Write your report to `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_explorer_2\report.md` and deliver `handoff.md`.


## 2026-11-04T22:18:42Z
Sender: ce2dd708-d288-4e8f-9834-dfdb673a5856
Priority: MESSAGE_PRIORITY_HIGH
Content:
You are m1_explorer_2.
Your working directory is: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_explorer_2
Your task instructions are in: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_explorer_2\DISPATCH.md
Read c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md, c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md, and your DISPATCH.md.
Formulate the technical rules and specifications for Win32 automation, DPI awareness, SendInput, focus management, and cross-application targeting for docs/SPECIFICATION.md.
Write your report to c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_explorer_2\report.md and deliver handoff.md. Report back via send_message when done.
