# Project: kutomoto

**Product**: kutomoto — Professional Forms Filling Automation System for Windows OS  
**Copyright**: Copyrights reserved to 90Studio  
**Target Environments**: Enterprise (Banking, Telecom, General Business)  

---

## Architecture

kutomoto is designed as a **Native Hybrid Enterprise Automation System** optimized for Windows OS:

```
+---------------------------------------------------------------------------------------+
|                                    kutomoto Shell                                    |
|                      (Microsoft Edge App Mode / Native Window)                       |
+---------------------------------------------------------------------------------------+
|  Presentation Layer (HTML5 / Modern CSS / Vanilla JS - No Heavy Bundler Required)     |
|  - Visual Form Designer Canvas (8-handle box drawing, magnetic snap, sequence badges) |
|  - Step-by-Step Flow Builder (Sequential action step editor, drag-and-drop reorder)   |
|  - Target App Selector & Countdown HUD (3s focus switch, window matcher)              |
|  - Real-time Execution Console & 90Studio Audit Log Viewer                            |
+-------------------------------------------+-------------------------------------------+
                                            | REST API & WebSocket (ws://127.0.0.1:8765)
                                            v
+---------------------------------------------------------------------------------------+
|                        Backend Service (Python 3.14 + FastAPI)                        |
|  - REST Endpoints (/api/workflows, /api/designer, /api/execute, /api/windows)         |
|  - Real-time WebSocket Streaming (/ws/execution)                                      |
|  - Flow Persistence (JSON Storage in user profile / workspace)                        |
+-------------------------------------------+-------------------------------------------+
                                            |
        +-----------------------------------+-----------------------------------+
        |                                                                       |
        v                                                                       v
+-----------------------------------------------+   +-----------------------------------+
|      Visual-to-Workflow Compiler Module       |   |     Workflow Execution Engine     |
| - 2D Spatial & Sequence Ordering              |   | - 7-State FSM (Idle, Run, Pause..) |
| - Dual-Coordinate Mapping (Norm 0..1 to Pix)  |   | - 10 Atomic Action Handlers       |
| - Peephole Navigation Optimizer (Click->Tab)  |   | - 4-Way Target Attachment         |
| - Schema Validation & Dynamic Injection       |   | - Safety Guardrails (Esc, Failsafe|
+-----------------------------------------------+   +-----------------+-----------------+
                                                                      |
                                                                      v
+---------------------------------------------------------------------------------------+
|                        Win32 Automation Core (Pure Python ctypes)                     |
|  - DPI Awareness Context (Per-Monitor V2: SetProcessDpiAwarenessContext(-4))          |
|  - Input Injection: SendInput (Mouse clicks, moves, KEYEVENTF_UNICODE typing, Keys)   |
|  - Focus Management: AttachThreadInput + ShowWindow(SW_RESTORE) + SetForegroundWindow |
|  - Window Enumeration & Geometry: EnumWindows, GetWindowTextW, GetWindowRect          |
|  - Clipboard Injection Fallback: OpenClipboard, SetClipboardData(CF_UNICODETEXT)      |
+-------------------------------------------+-------------------------------------------+
                                            |
                    +-----------------------+-----------------------+
                    |                                               |
                    v                                               v
+---------------------------------------+   +-------------------------------------------+
|    Target 1: Open Web Browser Forms   |   |   Target 2: Windows Desktop Applications  |
|  (Chrome, Edge, Firefox, Brave, etc.) |   |   (WinForms, WPF, Tkinter, SAP, Win32)   |
+---------------------------------------+   +-------------------------------------------+
```

---

## Feature Inventory

Every requirement and discovered feature from the Survey phase is enumerated and assigned to a milestone:

| # | Feature ID | Name | Description | Milestone | Source |
|---|------------|------|-------------|-----------|--------|
| 1 | F01 | Specification Document | Enterprise requirements, 9 use cases, 8 epics, schemas | M1 | R1 / survey |
| 2 | F02 | Banking Domain Specs | Commercial loan, KYC onboarding, SWIFT wire transfer specs | M1 | R1 / survey |
| 3 | F03 | Telecom Domain Specs | SIM registration, fiber provisioning, fleet migration specs | M1 | R1 / survey |
| 4 | F04 | Business Domain Specs | AP invoice entry, vendor onboarding, expense claim specs | M1 | R1 / survey |
| 5 | F05 | Win32 DPI Input Core | ctypes SendInput, Per-Monitor V2 DPI awareness | M2 | R3 / survey |
| 6 | F06 | Unicode & Key Typing | KEYEVENTF_UNICODE typing, Tab, Enter, Backspace, Hotkeys | M2 | R3 / survey |
| 7 | F07 | Focus Activation Core | AttachThreadInput + ShowWindow + SetForegroundWindow | M2 | R3 / survey |
| 8 | F08 | Window Enumeration | EnumWindows, regex title matching, process filtering | M2 | R3 / survey |
| 9 | F09 | 10 Atomic Actions | focus, click, type_text, key_press, hotkey, clear, delay, submit, scroll, prompt | M2 | R3 / survey |
| 10 | F10 | Execution Engine FSM | 7-state asynchronous execution engine with pause/resume | M2 | R3 / survey |
| 11 | F11 | Safety Guardrails | Emergency Escape abort, corner failsafe, focus check | M2 | R3 / survey |
| 12 | F12 | Audit Logger | Structured execution log stamped "Copyrights reserved to 90Studio" | M2 | R4 / survey |
| 13 | F13 | Visual Form Box Model | VisualBox data model, geometry, properties, sequence index | M3 | R2 / survey |
| 14 | F14 | Visual-to-Workflow Compiler | 5-pass compilation algorithm from visual boxes to workflow | M3 | R2 / survey |
| 15 | F15 | Coordinate Normalization | Dual-coordinate translation (normalized 0..1 to physical px) | M3 | R2 / survey |
| 16 | F16 | Backend API Server | FastAPI REST API & WebSocket event streaming | M4 | R4 / survey |
| 17 | F17 | Enterprise UI Layout | Modern responsive enterprise dashboard with 90Studio branding | M4 | R4 / survey |
| 18 | F18 | Visual Designer Canvas UI | Interactive HTML5 canvas with 8 handles, snap guides, badges | M4 | R2 / survey |
| 19 | F19 | Step-by-Step Flow Editor | Manual sequential flow builder with action configuration | M4 | R3 / survey |
| 20 | F20 | Countdown HUD & Runner | Interactive 3-second countdown HUD for target window switch | M4 | R3 / survey |
| 21 | F21 | Sample Web Form Target | Banking KYC Web Form with visual submission verification | M5 | AC / survey |
| 22 | F22 | Sample Desktop Form Target | Telecom SIM Provisioning Tkinter Form with submission verification | M5 | AC / survey |
| 23 | F23 | Automated E2E Test Suite | Comprehensive tests covering unit, compiler, engine, web/desktop | M5 | AC / survey |

*Cross-check verification*: All 23 features assigned. No unassigned features.

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Specification & Domain Blueprints | `docs/SPECIFICATION.md` with enterprise scenarios, user stories, engine rules, JSON schemas | none | DONE |
| M2 | Win32 Automation Core & Workflow Engine | `src/kutomoto/automation/` (Win32 ctypes, DPI, SendInput, focus) and `src/kutomoto/engine/` (10 actions, FSM, safety) | none | DONE |
| M3 | Visual Form Designer Compiler & Schemas | `src/kutomoto/designer/` (VisualBox schema, normalization, 5-pass compilation algorithm, validation) | M2 | DONE |
| M4 | Enterprise Application UI & 90Studio Branding | `src/kutomoto/server/` (FastAPI + WebSocket) and `src/kutomoto/ui/` (Canvas designer, flow editor, HUD, branding) | M2, M3 | DONE |
| M5 | Sample Target Applications & E2E Verification | `samples/web/`, `samples/desktop/`, and `tests/` verifying automated form filling and submission on web & desktop | M1, M2, M3, M4 | DONE |

---

## Interface Contracts

### 1. Visual Designer ↔ Workflow Compiler
- **Input**: `VisualFormLayout`
  ```json
  {
    "id": "string",
    "name": "string",
    "target": { "type": "window_title", "match_pattern": "string" },
    "canvas": { "width": 800, "height": 600 },
    "boxes": [
      {
        "id": "box_1",
        "name": "field_name",
        "rect": { "x": 100, "y": 150, "width": 200, "height": 36 },
        "sequence_index": 1,
        "action_type": "type_text" | "click" | "submit",
        "value": "text to enter",
        "navigation": "tab" | "enter" | "none",
        "clear_before": true
      }
    ]
  }
  ```
- **Output**: `ActionWorkflow` (Unified Action Schema Draft 2020-12)
- **Function**: `compile_visual_boxes_to_workflow(layout: VisualFormLayout) -> ActionWorkflow`

### 2. Workflow Engine ↔ Win32 Automation Driver
- **Functions in `automation.win32_driver`**:
  - `set_dpi_awareness() -> bool`
  - `find_window(title_regex: str) -> Optional[int]`
  - `focus_window(hwnd: int) -> bool`
  - `get_window_bounds(hwnd: int) -> Tuple[int, int, int, int]`
  - `send_click(x: int, y: int, button: str = "left", click_count: int = 1) -> None`
  - `send_text(text: str, delay_between_keys: float = 0.01) -> None`
  - `send_key_press(vk_name: str) -> None`
  - `send_hotkey(modifiers: List[str], key: str) -> None`
  - `clear_field() -> None` (Ctrl+A -> Backspace)

### 3. Backend REST/WebSocket API ↔ Frontend UI
- `GET /api/workflows` -> List saved workflows
- `POST /api/workflows` -> Create/save workflow
- `POST /api/designer/compile` -> Convert `VisualFormLayout` to `ActionWorkflow`
- `POST /api/execute/start` -> Start executing workflow by ID or payload
- `POST /api/execute/abort` -> Emergency abort
- `GET /api/windows` -> List currently open desktop windows & browser tabs
- `WebSocket /ws/execution` -> Real-time stream: `{ "event": "step_started" | "step_completed" | "log" | "state_change" }`

---

## Code Layout

```
c:\Users\daoud\projects\kutomoto\
├── docs\
│   └── SPECIFICATION.md          # Comprehensive Enterprise Specification (R1)
├── src\
│   └── kutomoto\
│       ├── __init__.py           # Package version & 90Studio attribution
│       ├── __main__.py           # CLI entry point (`python -m kutomoto`)
│       ├── automation\           # Win32 Native Driver (ctypes)
│       │   ├── __init__.py
│       │   ├── win32_core.py     # INPUT structs, constants, DPI awareness
│       │   ├── win32_input.py    # SendInput wrapper for mouse & keyboard
│       │   └── win32_window.py   # EnumWindows, AttachThreadInput, focus
│       ├── engine\               # Workflow Execution Engine
│       │   ├── __init__.py
│       │   ├── schema.py         # Pydantic models for Unified Action Schema
│       │   ├── fsm.py            # 7-State Execution Finite State Machine
│       │   ├── runner.py         # Async workflow executor loop & handlers
│       │   └── safety.py         # Esc abort, corner failsafe, focus guardian
│       ├── designer\             # Visual Form Designer Compiler
│       │   ├── __init__.py
│       │   ├── schema.py         # VisualFormLayout & VisualBox schemas
│       │   └── compiler.py       # 5-pass translation algorithm
│       ├── server\               # Local API & WebSocket Service
│       │   ├── __init__.py
│       │   └── app.py            # FastAPI endpoints & WebSocket hub
│       └── ui\                   # Enterprise UI Static Assets
│           ├── index.html        # Single Page App shell
│           ├── css\
│           │   └── kutomoto.css  # Enterprise theme (blue/gray/dark slate)
│           └── js\
│               ├── app.js        # UI controller & WebSocket client
│               ├── designer.js   # HTML5 Canvas visual form designer
│               └── runner.js     # Sequential flow builder & countdown HUD
├── samples\                      # Verification Target Applications
│   ├── web\
│   │   ├── index.html            # Banking KYC Web Form
│   │   └── form.js               # Form validation & visual confirmation banner
│   └── desktop\
│       └── sample_desktop_form.py# Telecom SIM Provisioning Tkinter Win32 Form
├── tests\                        # Comprehensive Automated Test Suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_specification.py     # Specification completeness validation
│   ├── test_win32_driver.py      # Win32 driver unit & struct tests
│   ├── test_compiler.py          # Visual-to-workflow compilation tests
│   ├── test_engine.py            # Workflow execution & FSM tests
│   ├── test_api.py               # REST API & WebSocket endpoint tests
│   └── test_e2e_automation.py    # E2E automated form filling on web & desktop
├── run_kutomoto.bat              # Windows batch launcher (Edge App Mode)
└── README.md                     # Documentation & Quickstart
```
