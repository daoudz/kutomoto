# BRIEFING — 2026-11-05T08:57:00Z

## Mission
Investigate and design the technical blueprint for the Sample Web Form target in Milestone 5 (`samples/web/`): realistic Banking KYC / Customer Onboarding Form with clean styling, DOM structure, validation, submission confirmation, Tab flow, and automation engine / visual form compiler integration.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigator, technical designer, synthesizer
- Working directory: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m5_explorer_1\
- Original parent: 7675637a-9a1e-40c3-a3cd-063a24f49a5c
- Milestone: Milestone 5 (Sample Applications)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code outside working directory
- Deliverables in working directory: handoff.md, progress.md, BRIEFING.md, DISPATCH.md
- Use send_message to report completion to parent

## Current Parent
- Conversation ID: 7675637a-9a1e-40c3-a3cd-063a24f49a5c
- Updated: 2026-11-05T08:57:00Z

## Investigation State
- **Explored paths**:
  - `c:\Users\daoud\projects\kutomoto\.agents\teamwork\ORIGINAL_REQUEST.md` (R1-R4, AC)
  - `c:\Users\daoud\projects\kutomoto\.agents\teamwork\orchestrator\PROJECT.md` (F21, F23, M5 scope)
  - `c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md` (BK-02, US-TST-01, Sec 11.1)
  - `src\kutomoto\engine\schema.py`, `runner.py`, `safety.py` (Atomic actions, FSM, SendInput integration)
  - `src\kutomoto\designer\schema.py`, `compiler.py` (5-pass visual compiler, spatial sorting, peephole optimization)
  - `src\kutomoto\ui\css\kutomoto.css` (Enterprise visual design tokens)
  - `tests\test_compiler.py`, `tests\test_engine.py` (Existing banking KYC test flows)
- **Key findings**:
  - `docs/SPECIFICATION.md` §11.1 and US-TST-01 define standard acceptance criteria for Banking KYC web target.
  - The form requires 7 data controls + Submit + Reset: Full Name, National ID / SSN, Account Type, Annual Income, Risk Rating, Email, Terms Checkbox, Submit Button, Reset Button.
  - Must include exact branding: "Banking KYC Onboarding — kutomoto Automation Target — Copyrights reserved to 90Studio".
  - Window title matching `.*Banking KYC.*` enables seamless Win32 driver attachment.
  - Hybrid targeting strategy: initial `click` anchors DOM focus at Field 1, followed by `type_text` and `key_press: tab`, with `space` for checkbox and `enter` or `click` for submit.
  - Form must expose `window.__LAST_SUBMITTED_PAYLOAD__` and `window.__GET_FIELD_COORDINATES__()` for automated testing.
- **Unexplored areas**: None. Blueprint is fully synthesized.

## Key Decisions Made
- Designed full specifications for `index.html`, `styles.css`, and `form.js`.
- Specified dual-mode coordinate support (DOM bounding client rects and normalized 0..1 coordinates).
- Specified both visual compiler layout and sequential action workflow for E2E automation.

## Artifact Index
- DISPATCH.md — Recorded incoming dispatch message
- BRIEFING.md — Persistent context and state
- progress.md — Liveness heartbeat and activity tracking
- handoff.md — Complete 5-component technical blueprint and handoff report
