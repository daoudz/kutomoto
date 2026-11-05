# Execution Plan: kutomoto

**Product**: kutomoto — Professional Forms Filling Automation System for Windows OS  
**Copyright**: Copyrights reserved to 90Studio  
**Orchestration Pattern**: Project (Explorer -> Worker -> Reviewer -> Challenger -> Auditor -> Gate)

---

## Milestone Execution Strategy

Each milestone executes via the Project Pattern iteration loop:
1. **Explorer**: Technical investigation, failure analysis (if retrying), strategy formulation.
2. **Worker**: Genuine implementation, executing build and test commands, providing verification evidence.
3. **Reviewers (2x)**: Independent verification of code quality, requirements fulfillment, interface conformance, and edge case handling.
4. **Challengers (2x)**: Empirical stress testing, boundary fuzzing, adversarial execution.
5. **Forensic Auditor (teamwork_auditor)**: Binary veto verification ensuring NO cheating, NO hardcoding, NO dummy facades, and genuine logic.
6. **Gate Evaluation**: Strict consensus requirement (All pass, clean audit, both reviewers approve, challenger passes).

---

## Sequential Milestones Roadmap

### Milestone 1: Specification & Domain Blueprints (R1)
- **Goal**: Authoritative `docs/SPECIFICATION.md` detailing 23 features, 15 edge cases, 9 enterprise scenarios (Banking, Telecom, Business), 8 user story epics (Gherkin), JSON schemas, Win32 input mechanics, and 90Studio branding.
- **Assigned Features**: F01, F02, F03, F04.

### Milestone 2: Win32 Automation Core & Workflow Engine (R3)
- **Goal**: Implement `src/kutomoto/automation/` and `src/kutomoto/engine/`. Pure Python ctypes Win32 driver (DPI Per-Monitor V2 awareness, 40-byte INPUT structs, SendInput mouse/keyboard/unicode, focus management via AttachThreadInput + SetForegroundWindow), 10 atomic actions, 7-state FSM runner, emergency Escape abort hotkey, and structured 90Studio audit logger.
- **Assigned Features**: F05, F06, F07, F08, F09, F10, F11, F12.

### Milestone 3: Visual Form Designer Compiler & Schemas (R2)
- **Goal**: Implement `src/kutomoto/designer/`. VisualBox schema, 5-pass compilation algorithm (`compile_visual_boxes_to_workflow`), 2D spatial sorting, dual-coordinate normalization (0.0 to 1.0), peephole navigation optimization, and reverse visual mapping.
- **Assigned Features**: F13, F14, F15.

### Milestone 4: Enterprise Application UI & 90Studio Branding (R4)
- **Goal**: Implement `src/kutomoto/server/` and `src/kutomoto/ui/`. FastAPI REST & WebSocket server, modern enterprise SPA with HTML5 Canvas Visual Form Designer (8 resize handles, magnetic snap, sequence badges), Step-by-Step Flow Builder, 3-second Countdown HUD, and Windows launcher (`run_kutomoto.bat`).
- **Assigned Features**: F16, F17, F18, F19, F20.

### Milestone 5: Sample Target Applications & E2E Verification (R1-R4 Acceptance Criteria)
- **Goal**: Implement sample targets (`samples/web/index.html` Banking KYC form, `samples/desktop/sample_desktop_form.py` Telecom SIM form) and comprehensive automated test suite (`tests/`). Verify end-to-end automated form filling, field ordering, and submission confirmation on both web and desktop forms.
- **Assigned Features**: F21, F22, F23.
