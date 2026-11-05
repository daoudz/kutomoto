# BRIEFING — 2026-11-04T22:30:00Z

## Mission
Formulate comprehensive Win32 automation, DPI awareness, SendInput, focus management, and cross-application targeting technical rules and specifications for docs/SPECIFICATION.md.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigator, synthesizer
- Working directory: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_explorer_2
- Original parent: ce2dd708-d288-4e8f-9834-dfdb673a5856
- Milestone: M1 (Specification & Domain Blueprints)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement source code
- Focus on Win32 automation, Per-Monitor V2 DPI awareness, SendInput ctypes mechanics, focus stealing recovery, cross-application targeting, and safety guardrails
- Write report to c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_explorer_2\report.md and deliver handoff.md
- Report back via send_message to orchestrator

## Current Parent
- Conversation ID: ce2dd708-d288-4e8f-9834-dfdb673a5856
- Updated: 2026-11-04T22:30:00Z

## Investigation State
- **Explored paths**:
  - `c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md`
  - `c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md`
  - `c:\Users\daoud\projects\kutomoto\.agents\teamwork\explorer_survey_2\tech_survey_report.md`
  - `c:\Users\daoud\projects\kutomoto\.agents\teamwork\explorer_survey_3\engine_survey_report.md`
  - Windows 11 host environment via Python 3.14 ctypes diagnostic commands.
- **Key findings**:
  - Python 3.14 64-bit on Windows 11 requires exact 40-byte `INPUT` struct with 8-byte union alignment. Empirically tested and verified `sizeof(INPUT) == 40`.
  - `SetProcessDpiAwarenessContext(c_void_p(-4))` succeeds immediately on Windows 11, ensuring 1:1 physical pixel coordinate mapping.
  - Focus activation requires `AttachThreadInput` + `ShowWindow(SW_RESTORE)` + simulated Alt tap to bypass `LockSetForegroundWindow`.
  - Web browser tab targeting requires 4-way hybrid approach (Regex, Process match, 3s Countdown HUD, In-place Global Hotkey).
  - Safety guardrails include: (0,0) corner slam, Escape abort hotkey with modifier release, and pre-flight loss-of-focus guardian.
  - UIPI privilege isolation noted: if target app runs elevated, Kutomoto must also run elevated.
- **Unexplored areas**:
  - None within the scope of Win32 automation and targeting specification.

## Key Decisions Made
- Authored a comprehensive technical specification in `report.md` structured specifically for direct incorporation into `docs/SPECIFICATION.md` by the M1 worker.
- Provided normative Python ctypes data models, API interface contract `IWin32AutomationDriver`, and mathematical coordinate translation formulas.

## Artifact Index
- `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_explorer_2\BRIEFING.md` — Persistent agent memory
- `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_explorer_2\progress.md` — Liveness heartbeat
- `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_explorer_2\report.md` — Primary technical specifications report
- `c:\Users\daoud\projects\kutomoto\.agents\teamwork\m1_explorer_2\handoff.md` — 5-component handoff report
