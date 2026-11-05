# Final Project Handoff Report: kutomoto

**Project**: kutomoto — Professional Forms Filling Automation System for Windows OS  
**Attribution**: Copyrights reserved to 90Studio  
**Orchestrator**: Teamwork Orchestrator (`7675637a-9a1e-40c3-a3cd-063a24f49a5c`)  
**Parent Agent**: Sentinel (`ff077c76-e5b2-4e48-af06-c0812d5d76c6`)  
**Date**: 2026-11-05T13:36:00Z  
**Status**: 100% COMPLETE — All 5 Milestones Approved & Gate PASS  

---

## 1. Executive Summary

**kutomoto** is an enterprise-grade forms filling automation system engineered specifically for Windows desktop environments and open web browser pages. Designed for high-compliance enterprise sectors (banking, telecommunications, corporate operations), kutomoto bridges visual form design and low-level hardware automation without relying on brittle browser extensions or inaccessible DOM trees.

All 5 core project milestones have been designed, implemented, reviewed, challenged, and forensically audited with **Gate PASS** across all gates:
- **Milestone 1 (R1 Specification)**: Enterprise specifications, user stories, engine rules, and JSON schemas (`docs/SPECIFICATION.md`).
- **Milestone 2 (R3 Automation Core & Engine)**: Win32 ctypes hardware `SendInput` driver, 7-state FSM, 10 atomic actions, focus guardian, Escape key emergency abort, and structured audit logger (`src/kutomoto/automation/`, `src/kutomoto/engine/`).
- **Milestone 3 (R2 Visual Form Designer Compiler & Schemas)**: 8-handle canvas box designer schema, 2D reading-order spatial sequencing, 5-pass compilation into executable action workflows (`src/kutomoto/designer/`).
- **Milestone 4 (R4 Enterprise UI Application & 90Studio Branding)**: FastAPI backend with WebSocket streaming, single-flight execution lock, Single Page App UI shell (`src/kutomoto/server/`, `src/kutomoto/ui/`), Windows batch launcher (`run_kutomoto.bat`), CLI launcher (`src/kutomoto/__main__.py`), RFC 7807 problem details with 90Studio copyright.
- **Milestone 5 (R5 Sample Targets & E2E Automated Verification)**: Banking KYC Web Form (`samples/web/`), Telecom SIM Provisioning Desktop Tkinter Form (`samples/desktop/`), on-disk workflow deliverables, safety state isolation, and comprehensive E2E test suites (`tests/test_e2e_automation.py`).

**Quality Metrics**:
- **452 / 452** synchronous tests passing across the entire repository.
- **0** linter errors (`ruff check src/ tests/ samples/`).
- **0** bare `pass` statements or stub implementations.
- **100%** compliance with `"Copyrights reserved to 90Studio"` across UI headers/footers, HTML `<title>`, API error responses, CLI banners, batch files, and sample applications.

---

## 2. Milestone State & Verification Summary

| # | Milestone | Scope | Deliverables | Gate Verdict |
|---|---|---|---|---|
| M1 | Specification & Domain Blueprints (R1) | Enterprise specifications, user stories, engine rules, JSON schemas | `docs/SPECIFICATION.md`, `tests/test_specification.py` | **PASS** (Iteration 2) |
| M2 | Automation Engine & Action Workflows (R3) | Win32 ctypes driver, 7-state FSM, 10 actions, safety guards, audit logging | `src/kutomoto/automation/`, `src/kutomoto/engine/`, `tests/test_automation.py`, `tests/test_engine.py` | **PASS** (Iteration 3) |
| M3 | Visual Form Designer Compiler & Schemas (R2) | VisualBox schema, 8-handle geometry, 5-pass compiler, spatial sorting, tab navigation | `src/kutomoto/designer/`, `tests/test_designer.py` | **PASS** (Iteration 2) |
| M4 | Enterprise UI Application & Branding (R4) | FastAPI REST API, WebSocket stream, Canvas UI, countdown HUD, launchers, RFC 7807 | `src/kutomoto/server/`, `src/kutomoto/ui/`, `run_kutomoto.bat`, `src/kutomoto/__main__.py`, `tests/test_api.py` | **PASS** (Iteration 4) |
| M5 | Sample Target Applications & E2E Verification (R5) | Banking KYC web form, Telecom SIM provisioning desktop form, on-disk workflow validation, E2E test suite | `samples/web/`, `samples/desktop/`, `tests/test_e2e_automation.py`, `tests/test_m5_adversarial_*.py` | **PASS** (Iteration 2) |

---

## 3. System Architecture & Component Inventory

### 3.1 Win32 Automation Core (`src/kutomoto/automation/`)
- `win32_driver.py`: High-precision Win32 hardware input driver leveraging `ctypes.windll.user32.SendInput`. Provides sub-millisecond mouse clicks, key events, Unicode character injections (`KEYEVENTF_UNICODE`), hotkey combos, field clearing (`Ctrl+A -> Backspace`), and Per-Monitor V2 DPI awareness.
- `win32_window.py`: Window discovery (`FindWindowExW`, `EnumWindows`), regex title matching, focus forcing (`SetForegroundWindow`, `AttachThreadInput`, `BringWindowToTop`), and coordinate translation (client vs screen space).

### 3.2 Workflow Engine & Safety Guardian (`src/kutomoto/engine/`)
- `fsm.py`: Strict 7-state finite state machine (`IDLE`, `ARMED`, `COUNTDOWN`, `RUNNING`, `PAUSED`, `ABORTED`, `COMPLETED`) with validated transition guards.
- `runner.py`: Workflow execution engine supporting 10 atomic actions (`click`, `double_click`, `type_text`, `send_key`, `hotkey`, `clear_field`, `wait_delay`, `assert_window`, `scroll`, `drag_and_drop`). Slices delays into 50ms chunks to ensure responsive sub-100ms pauses and emergency aborts. Supports variable interpolation with whitespace tolerance (`{{ variable_name }}`).
- `safety.py`: Hardware-level operator safety guardian:
  - Global `VK_ESCAPE` (Escape key) polling for instant emergency abort.
  - Operator mouse disturbance detection (>100px cursor movement triggers abort). Reinitializes cleanly across runs via `SafetyGuard.reset()`.
  - Focus loss guard: aborts or pauses if target window loses focus during active execution.
- `audit.py`: ISO 8601 structured audit logger generating tamper-evident execution logs with step timings, targets, status codes, and 90Studio attribution. Strictly isolated per run via `AuditLogger.reset()`.

### 3.3 Visual Form Designer Compiler (`src/kutomoto/designer/`)
- `schema.py`: Pydantic V2 schema models enforcing box coordinates, resize handles, action mappings, variable bindings, and navigation rules.
- `compiler.py`: Deterministic 5-pass compilation engine:
  1. *Pass 1 (Validation)*: Schema constraints, coordinate boundaries, target application definitions.
  2. *Pass 2 (Spatial Sequencing)*: 2D reading-order sorting (top-to-bottom, left-to-right with tolerance bands).
  3. *Pass 3 (Action Generation)*: Translates spatial boxes into atomic actions (click field, clear field, type text, tab/enter navigation).
  4. *Pass 4 (Optimization)*: `click_to_tab` coalescing, redundant click pruning while strictly preserving non-text clicks and settling pre-delays.
  5. *Pass 5 (Finalization)*: Emits valid JSON Draft 2020-12 `ActionWorkflow` ready for execution.

### 3.4 Enterprise Application & UI Shell (`src/kutomoto/server/`, `src/kutomoto/ui/`)
- `app.py`: FastAPI server with single-flight execution lock (`WorkflowExecutionManager`), REST endpoints (`/api/workflows`, `/api/execute`, `/api/execute/{id}/pause`, `/api/execute/{id}/resume`, `/api/execute/{id}/abort`, `/api/execute/audit/{id:path}`).
- `websocket.py`: Real-time WebSocket event stream (`/ws/execution`) publishing state transitions, step progress, and HUD events.
- `src/kutomoto/ui/`: Single Page Application with HTML5 Canvas 8-handle visual box designer, form flow editor, execution controls, interactive 3-second countdown HUD, and persistent 90Studio attribution.
- Launchers: `run_kutomoto.bat` (Windows batch script) and `python -m kutomoto` (CLI entry point).

### 3.5 Sample Target Applications (`samples/`)
- `samples/web/`: Enterprise Banking KYC Customer Onboarding portal with full DOM validation, step-by-step fields (Full Name, Date of Birth, National ID, Email, Phone, Account Type, Initial Deposit, Declaration, Submit), inspection hooks (`window.__KYC_SUBMISSION__`), and on-disk workflow definition (`banking_kyc_workflow.json`).
- `samples/desktop/`: Telecom SIM Card Provisioning standalone Tkinter desktop application with authentic Windows control geometry, MSISDN/IMSI/SIM Type/Plan/Customer ID inputs, verification badge, and on-disk workflow definition (`telecom_sim_provisioning_workflow.json`).

---

## 4. Verification Evidence & Quality Assurance

### 4.1 Test Suite Breakdown (452 Tests Synchronously Passing)
- `tests/test_specification.py`: 28 tests (Schema validation, specification completeness, requirements inventory).
- `tests/test_automation.py`: 48 tests (Win32 ctypes, DPI awareness, coordinate transforms, window discovery).
- `tests/test_engine.py`: 84 tests (FSM transitions, 10 atomic actions, safety guards, delay slicing, reusability).
- `tests/test_designer.py`: 111 tests (Pydantic models, 8-handle geometry, 5-pass compiler, spatial sorting, optimization).
- `tests/test_api.py`: 103 tests (FastAPI endpoints, single-flight lock, WebSocket streaming, RFC 7807 Problem Details, path sanitization).
- `tests/test_e2e_automation.py`: 18 tests (End-to-end automation of Banking KYC web form and Telecom SIM desktop form with on-disk workflow validation).
- `tests/test_m5_adversarial_challenge.py`: 30 tests (Adversarial FSM stress, 20-cycle pause/resume flapping, multi-run cursor jumps up to 1802px, modifier key releases).
- `tests/test_m5_adversarial_empirical.py`: 30 tests (15 consecutive form fills with 100% fidelity, 50-run audit isolation, memory leak & latency profiling).

### 4.2 Linter & Forensic Integrity
- `ruff check src/ tests/ samples/`: **0 errors**.
- Forensic Integrity Audit (`teamwork_auditor`): **CLEAN** across all 5 milestones.
  - Zero mock stubs, dummy facades, or bare `pass` statements in production or test drivers.
  - Authentic Win32 ctypes hardware `SendInput` implementation.
  - 100% verified `"Copyrights reserved to 90Studio"` attribution across all user-facing and machine-readable surfaces.

---

## 5. Deployment & Execution Instructions

### 5.1 Quickstart
To launch the kutomoto Enterprise Application:
```cmd
run_kutomoto.bat
```
Or via Python CLI:
```cmd
python -m kutomoto --host 127.0.0.1 --port 8000
```
This automatically boots the FastAPI backend and launches the Single Page Application UI in Microsoft Edge app mode (or the default browser) at `http://127.0.0.1:8000`.

### 5.2 Running the Sample Target Applications
1. **Banking KYC Web Portal**:
   Open `samples/web/index.html` in Chrome/Edge or serve via any static web server.
2. **Telecom SIM Provisioning Desktop App**:
   ```cmd
   python samples/desktop/sample_desktop_form.py
   ```

### 5.3 Running the Test Suite
```cmd
pytest -q
```
Expected output:
```text
452 passed in ~58s
```

---

## 6. Conclusion
The **kutomoto** system is complete, robust, rigorously tested, and fully aligned with all architectural and enterprise compliance requirements. All deliverables are documented and verified.
