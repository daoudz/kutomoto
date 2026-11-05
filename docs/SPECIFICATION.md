# kutomoto — Enterprise Specification & System Architecture Blueprint

```
====================================================================================================
Product Name       : kutomoto
Subtitle           : Professional Forms Filling Automation System for Windows OS
Copyright Notice   : Copyrights reserved to 90Studio
Document Reference : KTM-SPEC-2026-M1
Document Revision  : 1.0.0 (Master Production Specification)
Author             : 90Studio Architecture Council & Engineering Taskforce
Classification     : Enterprise Confidential / Architectural Baseline
Target Environment : Microsoft Windows 10 (Build 1703+) / Windows 11 64-bit
====================================================================================================
```

---

## 1. Executive Summary, Product Vision & 90Studio Branding

### 1.1 Executive Summary & Mission Statement

In modern regulated enterprise environments—encompassing commercial and retail banking, telecommunications network operations, supply chain logistics, and corporate shared services—operational staff spend millions of aggregate hours manually re-keying structured data. These workflows involve transcribing information from physical paperwork, PDF dossiers, spreadsheets, and internal ticketing systems into legacy Windows desktop software (WinForms, WPF, SAP GUI, terminal emulators) and internal web browser portals.

Manual data entry incurs catastrophic friction:
- **Severe Latency**: Onboarding a commercial borrower or provisioning a telecom fiber circuit manually consumes 15 to 30 minutes per record.
- **High Error Frequencies**: Human typing error rates on complex 19-digit SIM card ICCID numbers, 34-character International Bank Account Numbers (IBAN), and multi-digit general ledger accounting codes average 4% to 8%, precipitating regulatory fines, transaction rejections, and customer churn.
- **Brittle Automation Tools**: Conventional macro recorders and web-only browser extensions fail in locked-down enterprise environments where Chrome/Edge extensions are prohibited by Active Directory Group Policy, or where desktop applications render via DirectX/GDI surfaces without standard accessibility hooks.

**kutomoto** is an enterprise-grade, high-reliability forms filling automation platform designed and engineered exclusively for Microsoft Windows OS by **90Studio**. kutomoto combines visual, drag-and-drop workflow authoring with hardware-level Win32 automation primitives. By synthesizing the precision of desktop coordinate mapping with cross-application browser targeting, kutomoto empowers non-technical domain specialists and automation engineers to eliminate manual re-keying, enforce compliance, and accelerate data entry speeds by over 400%.

### 1.2 Dual Core Operating Paradigms

kutomoto addresses enterprise automation through two complementary, unified operational paradigms:

```
+--------------------------------------------------------------------------------------------------+
|                                    KUTOMOTO OPERATING PARADIGMS                                  |
+--------------------------------------------------+-----------------------------------------------+
|      PARADIGM 1: VISUAL FORM DESIGNER (VFD)      | PARADIGM 2: STEP-BY-STEP ACTION WORKFLOW (AWE)|
+--------------------------------------------------+-----------------------------------------------+
| - Designed for business analysts & branch staff  | - Designed for automation engineers & DevOps  |
| - Interactive HTML5 Canvas with screenshot under | - Granular step-by-step action sequence grid  |
| - Visual bounding box drawing over form controls | - Precise parameter tuning for timing & logic |
| - Automatic 8-handle resizing & magnetic snap    | - Explicit hotkeys, delays, chords & loops    |
| - Automatic sequence ordering badges ([#1], [#2])| - Direct coordinate targeting & mouse paths   |
| - Automatically compiles into unified workflows  | - Native JSON workflow editing and persistence|
+--------------------------------------------------+-----------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------------------------------------------------------+
|                                  UNIFIED ACTION WORKFLOW MODEL                                   |
|             (Draft 2020-12 JSON Schema, Stamped "Copyrights reserved to 90Studio")              |
+--------------------------------------------------------------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------------------------------------------------------+
|                                    WORKFLOW EXECUTION ENGINE                                     |
|             (7-State Asynchronous FSM, Loss-of-Focus Guardian, Win32 ctypes Core)                |
+--------------------------------------------------------------------------------------------------+
```

1. **Visual Form Designer (VFD)**: Non-programmers take a screenshot of any target form (web page or desktop GUI), load it as a canvas underlay, visually draw bounding boxes over input fields, assign sequence badges and field values, and click "Compile". kutomoto's 5-pass compilation engine automatically derives an optimized, executable action flow.
2. **Step-by-Step Action Workflow Engine (AWE)**: Advanced operators configure granular sequential action pipelines (`focus_window`, `click`, `type_text`, `key_press`, `hotkey`, `clear_field`, `delay`, `submit`, `scroll`, `prompt_user_input`). Each action step exposes precision timing parameters, retry policies, and field-clearing strategies.

Both authoring paradigms compile into the identical, canonical **Unified Action Workflow Schema**, allowing seamless round-trip editing, serialization, and team collaboration.

### 1.3 Native Hybrid Architecture & Runtime Strategy

To ensure zero-friction deployment on enterprise corporate workstations without requiring local C/C++ compilers (`cl.exe`, `gcc`), administrative Node.js installations, or complex heavy runtime dependencies, kutomoto implements a **Native Hybrid Enterprise Architecture**:

```
+--------------------------------------------------------------------------------------------------+
|                                        KUTOMOTO SHELL                                            |
|                  Microsoft Edge App Mode Window (`msedge.exe --app=http://127.0.0.1:8765`)       |
+--------------------------------------------------------------------------------------------------+
|  Presentation Layer (Vanilla HTML5 / Modern CSS Grid / ES2022 JavaScript - No Bundler Required)  |
|  - Visual Form Designer Canvas (8-handle box drawing, magnetic snap guides, sequence badges)     |
|  - Step-by-Step Flow Builder (Sequential action step editor, drag-and-drop reorder, cloning)     |
|  - Target App Selector & Countdown HUD (3s focus switch, window matcher, running monitor)        |
|  - Real-Time Execution Console & 90Studio Compliance Audit Log Viewer                            |
+--------------------------------------------------+-----------------------------------------------+
                                                   | REST API (HTTP) & Real-time WebSockets (ws://)
                                                   v
+--------------------------------------------------------------------------------------------------+
|                          Backend Service Layer (Python 3.14 + FastAPI + Uvicorn)                 |
|  - REST Endpoints (/api/workflows, /api/designer, /api/execute, /api/windows)                    |
|  - Real-Time WebSocket Telemetry Channel (/ws/execution)                                         |
|  - Flow Persistence & Audit Trail Storage (JSON documents stamped with 90Studio copyright)      |
+--------------------------------------------------+-----------------------------------------------+
                                                   |
                         +-------------------------+-------------------------+
                         |                                                   |
                         v                                                   v
+--------------------------------------------------+   +-------------------------------------------+
|        Visual-to-Workflow Compiler Module        |   |         Workflow Execution Engine         |
|  - 2D Spatial & Topological Reading Order Sort   |   |  - 7-State Non-Blocking Asynchronous FSM  |
|  - Dual-Coordinate Normalization (0.0 to 1.0)    |   |  - 10 Atomic Win32 Action Handlers        |
|  - Peephole Optimization & Delay Coalescing      |   |  - Pre-Step Loss-of-Focus Guardian        |
|  - Dynamic Schema Validation & Variable Binder   |   |  - Multi-Layer Safety (Esc, Corner Slam)  |
+--------------------------------------------------+   +---------------------+---------------------+
                                                                             |
                                                                             v
+--------------------------------------------------------------------------------------------------+
|                             Win32 Automation Core (Pure Python ctypes)                           |
|  - DPI Awareness Context: Per-Monitor V2 (`SetProcessDpiAwarenessContext(-4)`)                   |
|  - Input Injection: `SendInput` (64-bit 40-byte `INPUT` structs, `KEYEVENTF_UNICODE`, mouse)     |
|  - Focus Management: `AttachThreadInput` + `ShowWindow(SW_RESTORE)` + `SetForegroundWindow`      |
|  - Window Discovery: `EnumWindows`, `GetWindowTextW`, `GetClientRect`, `ClientToScreen`          |
|  - High-Speed Clipboard Driver: `OpenClipboard`, `GlobalAlloc`, `SetClipboardData(CF_UNICODETEXT)`|
+--------------------------------------------------+-----------------------------------------------+
                                                   |
                         +-------------------------+-------------------------+
                         |                                                   |
                         v                                                   v
+--------------------------------------------------+   +-------------------------------------------+
|         Target 1: Open Web Browser Forms         |   |    Target 2: Windows Desktop Applications |
|      (Microsoft Edge, Chrome, Firefox, Brave)    |   |      (WinForms, WPF, Tkinter, SAP GUI)    |
+--------------------------------------------------+   +-------------------------------------------+
```

### 1.4 Mandatory 90Studio Branding & Identity Standard

In strict compliance with 90Studio corporate governance, all source code, user interface components, documentation, telemetry streams, and serialized artifacts must embody the following identity standards:

| Branding Attribute | Normative Specification | System Placement & Implementation |
|:---|:---|:---|
| **Product Name** | `kutomoto` | UI Title bar, CLI launcher (`python -m kutomoto`), batch launcher (`run_kutomoto.bat`), schema titles. |
| **Corporate Attribution** | `Copyrights reserved to 90Studio` | Window status bar footer, About modal dialog, CLI `--version`, audit log footers, JSON schema metadata. |
| **System Identifier** | `90Studio` | System identifier in JSON schemas (`$id: "https://90studio.com/schemas/..."`), logging namespaces. |
| **Visual Aesthetic** | Enterprise High-Contrast Slate / Deep Navy | Modern corporate design: `#0f172a` (Slate 900), `#1e293b` (Slate 800), `#0284c7` (Sky Blue accent), `#22c55e` (Emerald success). |
| **Tamper-Evident Stamping** | `"copyright": "Copyrights reserved to 90Studio"` | Injected into every serialized `VisualFormLayout`, `ActionWorkflow`, and compliance audit log JSON record. |

---

## 2. Comprehensive 23-Feature Catalog (F01 – F23)

The following catalog provides the exhaustive, binding specification of all 23 functional features of kutomoto. Every feature is mapped to its architectural component, input contracts, output guarantees, error behaviors, milestone delivery, and traceability source.

| # | ID | Category | Feature Name | Description | Inputs | Outputs | Error Handling / Behavior | Milestone | Source |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **F01** | Specification | Enterprise Specification Document | Comprehensive master enterprise specification covering architecture, 23 features, 15 edge cases, 9 use cases, 8 epics, and JSON schemas. | System requirements from ORIGINAL_REQUEST.md & survey findings | `docs/SPECIFICATION.md` (authoritative markdown document) | Validated by automated structural pytest suite (`test_specification.py`) | M1 | R1 / survey |
| 2 | **F02** | Enterprise Blueprint | Banking Domain Specs | Formal operational workflows, field catalogs, and validation criteria for Commercial Loan Origination, Retail KYC Account Opening, and SWIFT MT103 Wire Transfer. | Banking industry data schemas, transaction structures | Detailed use case specifications and reference fill flows | Flags missing required regulatory fields; validates IBAN/BIC formats | M1 | R1 / survey |
| 3 | **F03** | Enterprise Blueprint | Telecom Domain Specs | Operational specifications for Prepaid/Postpaid SIM Registration, Fiber Broadband Subscriber Provisioning, and Corporate Fleet Plan Migration. | BSS/CRM form layouts, ICCID/MSISDN formatting rules | Telecom automation use cases and workflow definitions | Detects invalid 19-digit ICCID check digits; handles multi-tab provisioning | M1 | R1 / survey |
| 4 | **F04** | Enterprise Blueprint | Business Domain Specs | Operational workflows for Accounts Payable Invoice Processing, Vendor Master Data Onboarding, and Travel & Expense Reimbursement. | ERP invoice fields, W-9/tax structures, expense line items | Business automation specifications and workflow definitions | Enforces debit/credit balancing, invoice duplicate detection logic | M1 | R1 / survey |
| 5 | **F05** | Win32 Core | Win32 DPI Input Core | Pure Python ctypes driver configuring Per-Monitor V2 DPI awareness context and wrapping Windows `SendInput` for mouse moves, clicks, and coordinates. | Screen/Client coordinates (X, Y), mouse button (left, right, middle), click count | Synthesized Win32 `INPUT` events injected into OS hardware message queue | Clamps coordinates to virtual desktop bounds; fails safely if cursor locked | M2 | R3 / survey |
| 6 | **F06** | Win32 Core | Unicode & Key Typing | Text typing engine utilizing `SendInput` with `KEYEVENTF_UNICODE` for full international character set typing without layout corruption, plus virtual key codes (Tab, Enter, Backspace). | String payload, virtual key codes (VK_TAB, VK_RETURN, VK_BACK), per-key delay (ms) | Dispatched sequence of `KEYBDINPUT` down/up events | Handles UTF-16 surrogate pairs; gracefully recovers if buffer overflows | M2 | R3 / survey |
| 7 | **F07** | Win32 Core | Focus Activation Core | Multi-stage window focus activation combining `AttachThreadInput`, `ShowWindow(SW_RESTORE)`, and `SetForegroundWindow` to overcome Windows focus-stealing locks. | Target Window Handle (`HWND`) or window title | Window restored, unminimized, and brought to foreground with active input focus | Retries 3 times with 150ms backoff; raises `WindowFocusFailureException` on failure | M2 | R3 / survey |
| 8 | **F08** | Win32 Core | Window Enumeration | Discovery module using `EnumWindows`, `GetWindowTextW`, and `GetWindowThreadProcessId` to match open desktop windows and browser tabs by regex or title substring. | Title regex pattern, process name substring, case-sensitivity flag | List of matching window records (`hwnd`, `title`, `rect`, `pid`) | Returns empty list if no match found; suppresses phantom/zero-size tooltips | M2 | R3 / survey |
| 9 | **F09** | Workflow Engine | 10 Atomic Actions | Standardized handlers for the 10 atomic actions: `focus_window`, `click`, `type_text`, `key_press`, `hotkey`, `clear_field`, `delay`, `submit`, `scroll`, and `prompt_user_input`. | Action type enum, action parameter dictionary | Executed physical action, telemetry status event, duration timestamp | Validates parameters against action schema; raises `ActionExecutionError` on failure | M2 | R3 / survey |
| 10 | **F10** | Workflow Engine | Execution Engine FSM | Asynchronous non-blocking finite state machine managing 7 lifecycle states: `IDLE`, `VALIDATING`, `COUNTDOWN`, `RUNNING`, `PAUSED`, `STOPPING`, `COMPLETED`/`ERROR`. | State transition triggers (start, pause, resume, abort, complete, fail) | State transition events streamed over WebSocket to UI | Blocks invalid state transitions (e.g. `COMPLETED` -> `RUNNING`); logs state changes | M2 | R3 / survey |
| 11 | **F11** | Workflow Engine | Safety Guardrails | Multi-layer fail-safe system including global Emergency Escape abort hotkey, screen corner slam (0,0), and pre-step Loss-of-Focus Guardian. | Keyboard hooks (Esc, F9), physical mouse position, active foreground HWND | Immediate engine halt, input queue purge, emergency state transition | Catches unintended target window switches; halts execution within 50ms | M2 | R3 / survey |
| 12 | **F12** | Workflow Engine | Audit Logger | Tamper-evident structured execution logger emitting JSON audit trails stamped with timestamps, step metrics, error traces, and "Copyrights reserved to 90Studio". | Execution events, step telemetry, user parameters | Formatted audit log entries written to disk and streamed to UI | Masks sensitive passwords/fields (`is_secret: true`); guarantees immutable records | M2 | R4 / survey |
| 13 | **F13** | Visual Designer | Visual Form Box Model | Pydantic data model and JSON schema representing visual form input boxes with geometric rect, sequence rank, field type, value, and navigation rules. | Box geometry (X, Y, W, H), sequence index, label, field type, value, postAction | Validated `VisualFormLayout` and `VisualBox` instances | Rejects non-positive dimensions; auto-corrects sequence index gaps | M3 | R2 / survey |
| 14 | **F14** | Visual Designer | Visual-to-Workflow Compiler | Deterministic 5-pass compilation algorithm converting visual box layouts into optimized sequential action workflows (`ActionWorkflow`). | `VisualFormLayout` object, ordering strategy (manual rank or spatial band) | Compiled, executable `ActionWorkflow` JSON object | Validates connectivity and coordinates; warns on empty values or unreachable boxes | M3 | R2 / survey |
| 15 | **F15** | Visual Designer | Coordinate Normalization | Dual-coordinate translation system mapping normalized canvas coordinates ($0.0 \le x, y \le 1.0$) to absolute target window client pixels based on live window geometry. | Normalized box coordinates, target window client rectangle (`RECT`) | Physical target screen coordinates $(x_{screen}, y_{screen})$ | Accounts for DPI scaling factors (100%–200%) and window title/border offsets | M3 | R2 / survey |
| 16 | **F16** | Server & API | Backend API Server | High-performance FastAPI server running on `127.0.0.1:8765` providing REST endpoints for workflow CRUD, compilation, execution, and WebSocket telemetry streaming. | HTTP requests (`/api/workflows`, `/api/execute`, `/api/windows`), WS connections | JSON responses, real-time WebSocket event frames (`step_started`, `log`, etc.) | Returns RFC 7807 Problem Details on HTTP errors; handles disconnected WS clients | M4 | R4 / survey |
| 17 | **F17** | UI & Branding | Enterprise UI Layout | Modern, responsive desktop Single Page Application with split-pane layout, dark/light theme, ergonomic toolbars, and persistent 90Studio attribution. | Operator mouse clicks, keyboard shortcuts, window resize events | Rendered responsive UI shell running in Microsoft Edge App Mode | Graceful responsive scaling from 1280x720 up to 3840x2160 4K displays | M4 | R4 / survey |
| 18 | **F18** | UI & Branding | Visual Designer Canvas UI | Interactive HTML5 2D canvas supporting click-and-drag box drawing, 8 resize handles, magnetic snap guides, sequence badges, and image underlay loading. | Mouse drag events, image upload files, keyboard nudge arrows | Rendered canvas elements, updated box position coordinates | Clamps boxes within canvas bounds; enforces minimum 10x10 px box size | M4 | R2 / survey |
| 19 | **F19** | UI & Branding | Step-by-Step Flow Editor | Structured table and list builder allowing manual creation, inspection, reordering, editing, cloning, and deletion of atomic action steps. | User step additions, drag-and-drop reorder events, parameter changes | Updated in-memory and persisted `ActionWorkflow` model | Validates action parameter formats; highlights missing required parameters | M4 | R3 / survey |
| 20 | **F20** | UI & Branding | Countdown HUD & Runner | High-visibility 3-second arming countdown overlay allowing operators to inspect target application state, accompanied by run/pause/abort controls. | Execution start trigger, countdown timer ticks, abort hotkey | Visual countdown HUD (3..2..1), audio/visual ready cues, live progress bar | Instant cancellation if Escape is pressed during countdown without target changes | M4 | R3 / survey |
| 21 | **F21** | Sample Targets | Sample Web Form Target | Standalone enterprise Banking KYC customer onboarding web application (`samples/web/index.html`) with client validation and visual submission banner. | User/automated input keystrokes, button clicks | Visual success notification banner displaying submitted payload JSON | Shows field-level error banners if submitted with empty or invalid fields | M5 | AC / survey |
| 22 | **F22** | Sample Targets | Sample Desktop Form Target | Standalone native Windows desktop application (`samples/desktop/sample_desktop_form.py`) built with Tkinter demonstrating telecom SIM provisioning. | Synthetic Win32 mouse clicks, keystrokes, and form submission | Updated GUI status label: `"Status: SIM PROVISIONED SUCCESSFULLY"` | Displays validation alert dialog if mandatory fields are missing | M5 | AC / survey |
| 23 | **F23** | Test Suite | Automated E2E Test Suite | Comprehensive pytest test suite validating Win32 input structs, compiler 5-pass algorithm, FSM transitions, REST/WS APIs, and end-to-end form filling. | Pytest test runner execution (`pytest -v tests/`) | Test execution reports, code coverage metrics, assertion results | Reports granular failures with diffs; validates zero regressions across all modules | M5 | AC / survey |

---

## 3. Discovered Operational Edge Cases & Failure Recovery (E01 – E15)

In automated forms filling on Windows OS, display scaling, environmental concurrency, application latency, and operating system security mechanisms introduce failure modes that must be handled deterministically. The following table catalogs the 15 authoritative edge cases, their triggers, and the architectural defense mechanisms built into kutomoto:

| # | ID | Trigger Condition / Environmental Input | Observed / Required System Behavior | Architectural Defense Mechanism |
|---|:---|:---|:---|:---|
| 1 | **E01** | **Target Window Minimized or Occluded**: Target application is minimized to taskbar or occluded by modal dialog. | Engine detects window state via `IsIconic()`; invokes `ShowWindow(hwnd, SW_RESTORE)` followed by `BringWindowToTop(hwnd)` and `SetForegroundWindow(hwnd)`. Retries 3 times with 150ms pauses before raising `WindowFocusFailureException`. | Multi-tier Win32 window restoration pipeline with exponential backoff and Iconic verification. |
| 2 | **E02** | **Dynamic or Mutating Window Titles**: Window titles change dynamically during operation (e.g. `Google Chrome - [New Tab]` -> `Google Chrome - [KYC Portal]`). | Engine compiles title search string as Python regex (`re.compile(pattern, re.IGNORECASE)`). If regex matches multiple windows, engine filters by process name or selects the most recently active top-level window. | Flexible regex matching and secondary process executable filtering (`process_name`). |
| 3 | **E03** | **Multi-Monitor Display Scaling Mismatch**: Form designer runs on 100% DPI monitor, but target app resides on 150% scaling display. | Engine initializes process as Per-Monitor V2 DPI Aware (`SetProcessDpiAwarenessContext(-4)`). Normalized coordinates ($0.0 \le x, y \le 1.0$) are multiplied by the target window's actual physical client dimensions (`GetClientRect`). | Dual-coordinate normalization and native OS DPI awareness context. |
| 4 | **E04** | **Stale or Default Pre-Filled Values**: Input field contains existing default text (e.g. `"0.00"`, `"Enter Name"`), resulting in concatenated corrupt strings. | When `clear_before_type` is enabled (default for text boxes), engine emits `Ctrl+A` chord followed by `Backspace` (or triple-click for URLs) before dispatching the typed payload. | Pre-typing text selection and clearing chord (`Ctrl+A` -> `VK_BACK`). |
| 5 | **E05** | **Rapid Typing Keystroke Loss**: Target application runs over high-latency Remote Desktop/Citrix or has heavy JavaScript input masks, dropping fast keystrokes. | Engine supports configurable `keystroke_delay_ms` (default 25ms, configurable up to 200ms). For ultra-long text blocks (> 40 chars), engine supports optional high-speed clipboard paste (`Ctrl+V` via `OpenClipboard`). | Configurable inter-key delay and clipboard injection fallback. |
| 6 | **E06** | **Unicode & International Characters**: Payloads contain accented characters (e.g., `é`, `ü`), Arabic/Cyrillic scripts, or currency symbols (`€`, `£`, `¥`). | Keystroke simulation utilizes `SendInput` with `KEYEVENTF_UNICODE` (`wScan` contains UTF-16 code unit, `wVk = 0`). This bypasses the active Windows keyboard layout and dead-key states. | Hardware-level Unicode scan code injection via `KEYEVENTF_UNICODE`. |
| 7 | **E07** | **Modal Confirmation Prompts**: Target form displays a modal dialogue upon submission (e.g. `"Confirm Wire Transfer? [Yes/No]"`). | Visual compiler and workflow engine support chained multi-step confirmation sequences: configurable post-submit settling delay followed by a secondary `key_press` (`Enter` or `Y`) or modal coordinate click. | Chained post-submit confirmation action steps and settling pauses. |
| 8 | **E08** | **Accidental Operator Mouse Movement**: Operator bumps physical mouse during active execution, potentially shifting focus. | Engine tracks cursor position. If mouse moves more than 100 physical pixels while engine is in `RUNNING` state, the engine triggers the Loss-of-Focus Guardian, pauses execution, and prompts the operator. | Threshold-based mouse disturbance detection and automatic pausing. |
| 9 | **E09** | **Asynchronous / Lagging DOM Elements**: Slow AJAX network response delays the rendering of subsequent form fields. | Workflow engine supports configurable `inter_step_delay_ms` and per-step explicit `delay` actions. Workflows can configure polling retries before declaring a field unreachable. | Adaptive inter-step delay rules and configurable action timeouts. |
| 10 | **E10** | **Virtual Coordinate Space Across Multi-Monitors**: Target window is positioned on a secondary display with negative coordinate space (left or above primary display). | System computes screen coordinates using virtual desktop metrics (`SM_XVIRTUALSCREEN`, `SM_YVIRTUALSCREEN`). `ClientToScreen` Win32 API correctly resolves negative virtual coordinates. | Full virtual desktop coordinate calculation supporting negative offsets. |
| 11 | **E11** | **Degenerate Sub-Threshold Visual Boxes**: User clicks canvas without dragging, creating accidental 0-width or 1-pixel boxes. | Visual designer canvas enforces a minimum bounding box threshold: boxes smaller than 10x10 pixels (or 24x16 px) are automatically rejected and discarded with a subtle UI toast notice. | Geometry threshold validator on canvas pointer release (`mouseup`). |
| 12 | **E12** | **Duplicate or Non-Contiguous Sequence Indices**: User manually edits sequence indices causing duplicates (e.g. two boxes labeled `#2`). | Designer applies automatic sequence normalization: sorts all boxes by requested index (secondary sort by Y then X coordinates) and re-assigns clean, contiguous integer ranks `[1, 2, 3, ...]`. | Automatic sequence gap repair and duplicate disambiguation algorithm. |
| 13 | **E13** | **Active Browser Tab Switching**: Operator switches active browser tab during automated execution. | Loss-of-Focus Guardian polls `GetForegroundWindow()` immediately before every atomic action. If the active window handle deviates from the target `hwnd`, execution instantly transitions to `PAUSED`. | Active foreground window verification hook before every atomic action. |
| 14 | **E14** | **Empty or Blank String Payloads**: Workflow step contains an empty text value `""` (e.g. optional middle name or note field). | Engine detects empty string: executes field focus (click or Tab navigation) to ensure cursor position advances properly, but skips character typing loop. | Navigation-preserving empty payload bypass logic. |
| 15 | **E15** | **UAC Administrator Elevation Mismatch (UIPI)**: Target application is running as Administrator (`High Integrity`), while kutomoto runs as standard user (`Medium Integrity`). | Windows User Interface Privilege Isolation blocks synthetic inputs. kutomoto checks process token elevation; if mismatch is detected upon failure, logs an explicit diagnostic: `"Target runs elevated. Relaunch kutomoto as Administrator"`. | Process integrity level diagnostic check and actionable user remediation guidance. |

---

## 4. Enterprise Domain Blueprints & Field Catalogs

kutomoto is architected specifically for high-compliance enterprise sectors: **Banking**, **Telecommunications**, and **Corporate Business Operations**. The following blueprints document 9 production use cases complete with operational problem statements, target window profiles, exhaustive field catalogs, execution sequences, and business outcomes.

```
+---------------------------------------------------------------------------------------------------+
|                                      9 ENTERPRISE USE CASES                                       |
+------------------------------+-------------------------------+------------------------------------+
|        BANKING SECTOR        |      TELECOMMUNICATIONS       |          GENERAL BUSINESS          |
+------------------------------+-------------------------------+------------------------------------+
| BK-01: Commercial Loan       | TC-01: SIM Card KYC           | GB-01: AP Vendor Invoice           |
| Origination (Desktop)        | Registration (Web)            | Processing (SAP GUI / ERP)         |
|                              |                               |                                    |
| BK-02: Retail KYC Customer   | TC-02: Fiber Provisioning     | GB-02: Vendor Master Data          |
| Onboarding (Web SPA)         | & ONT Activation (Hybrid)     | Onboarding (Web Portal)            |
|                              |                               |                                    |
| BK-03: SWIFT MT103 Wire      | TC-03: Corporate Fleet Plan   | GB-03: Employee Travel &           |
| Transfer (Terminal)          | Migration & Swap (Batch)      | Expense Reimbursement (HR)         |
+------------------------------+-------------------------------+------------------------------------+
```

### 4.1 Banking & Financial Services Blueprints

#### 4.1.1 Use Case BK-01: Commercial Loan Application & Credit Underwriting
- **Sector**: Corporate & Commercial Banking
- **Target Application**: Native Windows Desktop Underwriting Client (WinForms / .NET core banking terminal)
- **Target Window Title Pattern**: `.*Commercial Underwriting Client - 90Studio Bank.*`
- **Business Problem**: Commercial credit analysts must ingest complex loan origination data from underwriting dossiers into core banking software. Manual data entry takes 25 minutes per application, with high error rates on tax IDs, revenue figures, and collateral appraisals.
- **Detailed Field Catalog (12 Fields)**:
  1. `borrower_legal_name` (Text, Center X: 320, Y: 180): Full registered corporate entity name (e.g., `"Acme Industrial Supplies LLC"`).
  2. `tax_id_ein` (Text, Center X: 320, Y: 220): Federal Employer Identification Number format `XX-XXXXXXX` (e.g., `"12-3456789"`).
  3. `business_address` (Text, Center X: 320, Y: 260): Registered corporate headquarters address (e.g., `"100 Corporate Parkway, Suite 400"`).
  4. `annual_gross_revenue` (Currency, Center X: 320, Y: 300): Audited annual revenue in USD (e.g., `"4500000.00"`).
  5. `facility_amount` (Currency, Center X: 320, Y: 340): Requested credit facility amount ($50,000 – $10,000,000) (e.g., `"1250000.00"`).
  6. `loan_term_months` (Number, Center X: 320, Y: 380): Loan duration in months (12 to 120) (e.g., `"60"`).
  7. `collateral_description` (Text, Center X: 320, Y: 420): Description of pledged collateral assets (e.g., `"First Commercial Real Estate Lien"`).
  8. `collateral_valuation` (Currency, Center X: 320, Y: 460): Certified appraised asset valuation ($) (e.g., `"1800000.00"`).
  9. `loan_officer_id` (Text, Center X: 320, Y: 500): Officer registration ID (e.g., `"LO-90S-4412"`).
  10. `risk_category` (Dropdown/Text, Center X: 320, Y: 540): Underwriting risk tier (e.g., `"Tier-1 Low Risk"`).
  11. `compliance_attestation` (Checkbox, Center X: 180, Y: 580): AML/BSA statutory declaration (value: `"Space"` key press).
  12. `submit_underwriting` (Button, Center X: 320, Y: 630): Final submission button trigger.
- **Workflow Execution Sequence**:
  - `focus_window` -> target underwriting application window.
  - Interactive Countdown HUD: 3-second visual count.
  - `click` box 1 (`borrower_legal_name`) -> `clear_field` (`select_all_backspace`) -> `type_text` -> `key_press: Tab`.
  - Sequential progression through fields 2–10 with 25ms keystroke pacing and 80ms settling delay.
  - `key_press: Space` on box 11 to toggle compliance checkbox.
  - `click` box 12 (`submit_underwriting`).
- **Expected Outcome**: Processing time reduced from 25 minutes to 7.8 seconds; 100% data entry accuracy; complete compliance audit trail.

#### 4.1.2 Use Case BK-02: Retail KYC (Know Your Customer) Account Opening
- **Sector**: Retail Banking & Wealth Management
- **Target Application**: Open Web Browser Page (Google Chrome / Microsoft Edge running customer onboarding portal)
- **Target Window Title Pattern**: `.*Retail Account Opening - Core Banking.*`
- **Business Problem**: Branch officers onboard retail banking customers into an internal Angular/React single-page application. Rigid client-side validation triggers errors if fields lose focus prematurely or receive inputs out of order.
- **Detailed Field Catalog (9 Fields)**:
  1. `customer_full_name` (Text, Client X: 380, Y: 210): Legal individual customer name (e.g., `"Eleanor Vance"`).
  2. `date_of_birth` (Date, Client X: 380, Y: 260): Date of birth format `DD/MM/YYYY` (e.g., `"14/08/1988"`).
  3. `national_id_ssn` (Text, Client X: 380, Y: 310): Government identification number (e.g., `"987-65-4321"`).
  4. `residential_address` (Text, Client X: 380, Y: 360): Physical street address (e.g., `"742 Evergreen Terrace"`).
  5. `postal_code` (Text, Client X: 380, Y: 410): Postal ZIP code (e.g., `"97201"`).
  6. `mobile_number` (Phone, Client X: 380, Y: 460): E.164 formatted telephone number (e.g., `"+1-503-555-0199"`).
  7. `email_address` (Email, Client X: 380, Y: 510): Customer contact email (e.g., `"e.vance@example.com"`).
  8. `initial_deposit_amount` (Currency, Client X: 380, Y: 560): Opening balance amount (e.g., `"2500.00"`).
  9. `account_type_checking` (Radio/Click, Client X: 380, Y: 610): Selected account product tier (Checking).
- **Workflow Execution Sequence**:
  - `focus_window` -> browser window.
  - `click` on field 1 to anchor DOM focus.
  - Sequence through fields using `type_text` and `key_press: Tab`.
  - Final `key_press: Enter` on submit trigger.
- **Expected Outcome**: Eliminates customer wait times at branches; ensures error-free account origination.

#### 4.1.3 Use Case BK-03: High-Value Cross-Border Wire Transfer (SWIFT MT103 / ISO 20022)
- **Sector**: Treasury & Institutional Banking Operations
- **Target Application**: Windows Desktop SWIFT Terminal Emulator (Win32 / Java terminal)
- **Target Window Title Pattern**: `.*SWIFT Alliance Access - MT103 Entry.*`
- **Business Problem**: High-value corporate payments require re-keying 15 precision fields. A single typo in an IBAN or SWIFT BIC code routes millions of dollars to invalid accounts or triggers international sanction rejection penalties.
- **Detailed Field Catalog (15 Fields)**:
  1. `sender_account_number` (Text): Debit account number (`ACCT-00918274`).
  2. `ordering_customer_name` (Text): Corporate remitter name (`Meridian Global Trading`).
  3. `beneficiary_name` (Text): Payee legal entity (`Zurich Precision Engineering AG`).
  4. `beneficiary_iban` (Text): Target IBAN (`CH9300762011623852957`).
  5. `swift_bic_code` (Text): Receiving bank 8 or 11 character BIC (`UBSWCHZH80A`).
  6. `intermediary_bank_code` (Text): Clearing institution routing code (`CHASUS33XXX`).
  7. `currency_code` (Text): ISO currency code (`USD`).
  8. `transfer_amount` (Currency): Transaction principal (`2450000.00`).
  9. `value_date` (Date): Settlement date format `YYYYMMDD` (`20261105`).
  10. `remittance_info` (Text): MT103 Field 70 details (`INV-2026-CH-9941 / CAPITAL EQUIPMENT`).
  11. `charge_code` (Dropdown/Text): Fee distribution code (`OUR`).
  12. `compliance_screening_flag` (Checkbox): OFAC/Sanctions pre-clearance toggle.
  13. `dual_auth_officer_pin` (Secret): Supervisor secondary authorization PIN (`is_secret: true`).
  14. `review_comments` (Text): Treasury operator clearance notes.
  15. `dispatch_wire_button` (Button): Final transmission trigger.
- **Special Operational Requirements**:
  - Enforce `keystroke_delay_ms: 50` to prevent buffer overflow on legacy terminal message loops.
  - Implement two-stage submission verification: primary submit click followed by a modal confirmation dialog handler.
- **Workflow Execution Sequence**:
  - `focus_window` -> target SWIFT desktop terminal emulator matching `.*SWIFT Alliance Access - MT103 Entry.*`.
  - Sequential progression through 15 payment and routing fields with 50ms keystroke delay pacing.
  - Toggle OFAC compliance screening checkbox -> inject supervisor authorization PIN.
  - Two-stage submission verification: click `dispatch_wire_button` followed by automated confirmation dialog acknowledgement.
- **Expected Outcome**: 100% elimination of payment routing typos; transmission time reduced from 10 minutes to 18 seconds; dual-authorization audit compliance.

---

### 4.2 Telecommunications Blueprints

#### 4.2.1 Use Case TC-01: Prepaid & Postpaid SIM Card Registration & KYC
- **Sector**: Mobile Network Operator (MNO) Dealer & Retail Operations
- **Target Application**: Open Web Browser Page (Edge/Chrome BSS/CRM Portal)
- **Target Window Title Pattern**: `.*MNO Telecom BSS - Subscriber Registration.*`
- **Business Problem**: Retail agents register hundreds of SIM cards daily under strict national telecommunications authority regulations. Hand-typing 19-digit ICCID SIM card numbers produces an 8.2% error rate, resulting in dealer penalties and delayed subscriber activation.
- **Detailed Field Catalog (8 Fields)**:
  1. `subscriber_full_name` (Text): Customer legal identity (e.g., `"Tariq Al-Mansoor"`).
  2. `national_id_passport` (Text): National ID / Passport number (e.g., `"A90812458"`).
  3. `id_expiry_date` (Date): Identity document expiration date (e.g., `"12/10/2030"`).
  4. `sim_iccid_number` (Text): 19-digit SIM card identifier (e.g., `"8901410321111851072"`).
  5. `msisdn_phone_number` (Phone): Assigned 10-digit mobile phone number (e.g., `"555-014-9922"`).
  6. `plan_package_code` (Dropdown/Text): Tariff plan code (e.g., `"PRE-UNL-5G"`).
  7. `alternate_contact` (Phone): Secondary emergency contact (e.g., `"555-014-9920"`).
  8. `activate_provision_btn` (Button): Submit and network provisioning trigger.
- **Workflow Execution Sequence**:
  - Target browser activation -> anchor click on field 1 -> sequential typing and Tab traversal -> activation button click -> capture provisioning confirmation ID.
- **Expected Outcome**: Cycle time reduced from 4 minutes to under 12 seconds per subscriber; 0% ICCID transcription errors.

#### 4.2.2 Use Case TC-02: Fiber Broadband Subscriber Provisioning & ONT Activation
- **Sector**: Fixed-Line Broadband & Network Operations Center (NOC)
- **Target Application**: Hybrid: Native Desktop OLT Element Manager (Win32) + Web Provisioning Dashboard
- **Target Window Title Pattern**: `.*FTTH Network Element Manager - GPON.*`
- **Business Problem**: Provisioning Gigabit fiber requires entering optical parameters into an on-premises desktop client and copying the generated circuit ID to an intranet web ticket portal.
- **Detailed Field Catalog (10 Fields)**:
  1. `olt_frame_slot_port` (Text): Hardware optical interface (`1/1/4`).
  2. `ont_serial_number` (Text): Optical Network Terminal hardware serial (`ALCLB0921A44`).
  3. `subscriber_circuit_id` (Text): Enterprise circuit reference (`CKT-FTTH-2026-8810`).
  4. `vlan_id` (Number): Customer traffic VLAN tag (`102`).
  5. `pppoe_username` (Text): Network authentication user (`sub_8810@fastfiber.net`).
  6. `pppoe_password` (Secret): Subscriber credential (`is_secret: true`, value: `P@ssw0rd99!`).
  7. `downstream_profile` (Text): Bandwidth QoS profile (`1000M_UNLIMITED`).
  8. `upstream_profile` (Text): Bandwidth QoS profile (`500M_UNLIMITED`).
  9. `static_ipv4_block` (Text): Assigned static routing subnet (`198.51.100.32/29`).
  10. `commit_provisioning_button` (Button): Hardware configuration commit trigger.
- **Workflow Execution Sequence**:
  - Win32 desktop target activation -> parameter input -> commit button -> wait 1000ms -> clipboard copy of circuit ID -> focus web browser ticket -> paste circuit ID -> submit ticket.
- **Expected Outcome**: Fiber provisioning cycle compressed from 15 minutes to 45 seconds; eliminates manual copy-paste errors across desktop OLT terminals and web ticketing portals.

#### 4.2.3 Use Case TC-03: Corporate Fleet Account Plan Migration & SIM Swap
- **Sector**: B2B Enterprise Telecom Services
- **Target Application**: Web Enterprise Account Portal
- **Target Window Title Pattern**: `.*Corporate Fleet Manager - Telecom Enterprise.*`
- **Business Problem**: Account managers frequently migrate hundreds of corporate lines during annual contract renewals. The portal requires tedious repetitive form entries for each line item.
- **Detailed Field Catalog (8 Fields)**:
  1. `corporate_account_number` (Text): Enterprise master account (`CORP-TEL-77490`).
  2. `line_msisdn` (Phone): Line phone number to migrate (`555-019-3381`).
  3. `current_plan_code` (Text): Existing tariff tier (`LEGACY-CORP-4G`).
  4. `new_plan_code` (Text): Target upgraded tier (`ENTERPRISE-5G-MAX`).
  5. `effective_migration_date` (Date): Activation scheduling date (`20261201`).
  6. `roaming_addon_flag` (Checkbox): International roaming bundle toggle.
  7. `authorization_officer_id` (Text): B2B account director badge (`DIR-90S-552`).
  8. `submit_migration_button` (Button): Batch commitment action.
- **Workflow Execution Sequence**:
  - `focus_window` -> target web browser window matching `.*Corporate Fleet Manager - Telecom Enterprise.*`.
  - Countdown HUD: 3-second visual count for operator supervision.
  - `click` box 1 (`corporate_account_number`) to establish DOM focus -> `clear_field` (`select_all_backspace`) -> `type_text`.
  - Sequential progression through fields 2–5 (`line_msisdn`, `current_plan_code`, `new_plan_code`, `effective_migration_date`) using `type_text` and `key_press: Tab` (25ms keystroke pacing, 60ms settling pause).
  - `key_press: Space` on box 6 (`roaming_addon_flag`) to toggle international roaming bundle checkbox.
  - `key_press: Tab` to box 7 (`authorization_officer_id`) -> `type_text` director credential.
  - `click` box 8 (`submit_migration_button`) -> wait 500ms -> handle asynchronous batch commitment confirmation modal via `key_press: Enter`.
- **Expected Outcome**: Batch plan migrations completed in under 15 seconds per account (85% reduction vs manual entry); 0% plan code and MSISDN transcription errors across high-volume corporate fleets; full 90Studio audit log emission.

---

### 4.3 General Business Operations Blueprints

#### 4.3.1 Use Case GB-01: Accounts Payable Vendor Invoice Processing
- **Sector**: Corporate Accounting & Finance Shared Services
- **Target Application**: Native Windows Desktop ERP (SAP GUI / Microsoft Dynamics NAV Win32 Client)
- **Target Window Title Pattern**: `.*SAP GUI - Enter Incoming Invoice.*`
- **Business Problem**: AP clerks transcribe paper/PDF supplier invoices into enterprise ERP systems. High invoice volumes during month-end close cause cognitive fatigue and typing errors in invoice amounts, tax breakdowns, and cost center codes.
- **Detailed Field Catalog (10 Fields)**:
  1. `vendor_number` (Text): ERP supplier master ID (e.g., `"VEND-90S-1048"`).
  2. `invoice_number` (Text): Supplier's printed invoice reference (e.g., `"INV-2026-8841"`).
  3. `invoice_date` (Date): Invoice issuance date format `YYYYMMDD` (e.g., `"20261102"`).
  4. `posting_date` (Date): General Ledger posting date (e.g., `"20261104"`).
  5. `gross_amount` (Currency): Total payable amount (e.g., `"14850.00"`).
  6. `tax_code_amount` (Currency): Calculated VAT/Sales tax amount (e.g., `"1350.00"`).
  7. `currency_code` (Text): ISO currency code (e.g., `"USD"`).
  8. `payment_terms` (Text): Agreed settlement term (e.g., `"Net 30"`).
  9. `purchase_order_ref` (Text): Matching PO number (e.g., `"PO-44021"`).
  10. `cost_center_code` (Text): Departmental cost center (e.g., `"CC-FIN-770"`).
- **Workflow Execution Sequence**:
  - Focus SAP GUI client -> clear pre-existing fields -> sequential typing and tab traversal -> hotkey `Ctrl+S` (Save/Post) -> capture SAP document number from status bar.
- **Expected Outcome**: Processing speed increased by 400%; invoice transcription errors eliminated.

#### 4.3.2 Use Case GB-02: New Vendor Master Data Onboarding
- **Sector**: Corporate Procurement & Supply Chain
- **Target Application**: Web Procurement System (Coupa / SAP Ariba Web Portal)
- **Target Window Title Pattern**: `.*Procurement Portal - New Supplier Registration.*`
- **Business Problem**: Onboarding new global suppliers requires inputting 12 multi-field regulatory, banking, and tax data points across multi-step wizard web pages.
- **Detailed Field Catalog (12 Fields)**:
  1. `legal_entity_name` (Text): Full corporate registered name.
  2. `dba_trading_name` (Text): Doing-business-as trade brand.
  3. `tax_id_vat_number` (Text): W-9 / VAT registration code.
  4. `country_incorporation` (Dropdown/Text): Registered jurisdiction.
  5. `registered_street_address` (Text): Primary physical headquarters.
  6. `city_locality` (Text): City of operation.
  7. `postal_code` (Text): Postal ZIP code.
  8. `remittance_bank_name` (Text): Supplier's designated bank.
  9. `swift_routing_code` (Text): Bank routing / BIC code.
  10. `bank_account_number` (Text): Depository account number.
  11. `accounts_receivable_email` (Email): Vendor billing contact email.
  12. `payment_method_code` (Dropdown/Text): ACH, Wire, or Corporate Check.
- **Workflow Execution Sequence**:
  - `focus_window` -> target web browser window matching `.*Procurement Portal - New Supplier Registration.*`.
  - Countdown HUD: 3-second visual count for operator handoff.
  - `click` box 1 (`legal_entity_name`) to establish DOM focus -> `clear_field` (`select_all_backspace`) -> `type_text`.
  - Sequential `type_text` and `key_press: Tab` navigation across corporate identity and physical address fields 2–7.
  - Traversal into remittance & banking section (fields 8–10) with sensitive masking (`is_secret: false` / secure audit masking) and 35ms keystroke pacing for legacy web portals.
  - `type_text` for box 11 (`accounts_receivable_email`) -> `key_press: Tab` -> select payment method code on box 12 (`payment_method_code`).
  - Final trigger: `key_press: Enter` or `click` on wizard step submission trigger -> verify post-submission confirmation banner.
- **Expected Outcome**: Global vendor onboarding cycle reduced from 20 minutes to under 30 seconds; 100% tax ID, SWIFT BIC, and depository account data accuracy; automated vendor master validation.

#### 4.3.3 Use Case GB-03: Employee Travel & Expense Reimbursement Entry
- **Sector**: Human Resources & Corporate Payroll
- **Target Application**: Native Windows Desktop HR / Payroll Client
- **Target Window Title Pattern**: `.*Enterprise Expense Manager - Claim Entry.*`
- **Business Problem**: Re-keying recurring monthly travel expenses, lodging, per diems, and client entertainment line items into legacy desktop payroll systems.
- **Detailed Field Catalog (8 Fields)**:
  1. `employee_badge_id` (Text): Internal staff identity (`EMP-90S-2081`).
  2. `expense_incurred_date` (Date): Transaction date (`20261028`).
  3. `expense_category` (Dropdown/Text): Claim type (`Lodging & Travel`).
  4. `vendor_merchant_name` (Text): Hotel / Airline merchant (`Grand Hyatt Hotels`).
  5. `total_amount_incurred` (Currency): Claimed amount (`485.60`).
  6. `tax_element` (Currency): Deductible VAT/GST (`44.15`).
  7. `project_billing_code` (Text): Client billable cost center (`PRJ-ALPHA-CORP`).
  8. `business_justification` (Text): Operational justification note (`Quarterly Client Technical Review`).
- **Workflow Execution Sequence**:
  - `focus_window` -> target Win32 desktop client matching `.*Enterprise Expense Manager - Claim Entry.*`.
  - Countdown HUD: 3-second visual count for operator window handoff.
  - `click` box 1 (`employee_badge_id`) -> `clear_field` (`select_all_backspace`) -> `type_text`.
  - Sequential progression through date, category dropdown, merchant, and numerical currency fields 2–6 via `type_text` and `key_press: Tab` (25ms keystroke pacing, 80ms settling delay).
  - Traversal to box 7 (`project_billing_code`) and multiline text input for box 8 (`business_justification`).
  - Final claim commitment: hotkey `Ctrl+Enter` or `click` on "Submit Claim" button -> verify desktop status bar confirmation message.
- **Expected Outcome**: Expense entry cycle time reduced by 85% (from 12 minutes to under 10 seconds per claim); eliminates recurring month-end manual transcription backlogs; guaranteed format compliance on billing codes and tax elements.


---

## 5. Comprehensive User Story Epics & Gherkin Acceptance Criteria

The kutomoto system specification is governed by 8 user story epics spanning the complete functional lifecycle: Visual Form Designing, Step-by-Step Flow Construction, Compilation Semantics, Web and Desktop Target Execution, Focus and Interruption Controls, Error Boundaries and Audit Trails, Enterprise UI Presentation, and Verification Test Scenarios.

```
+---------------------------------------------------------------------------------------------------+
|                                        8 USER STORY EPICS                                         |
+------------------------------------+--------------------------------------------------------------+
| Epic 1: Visual Form Designer (VFD) | Epic 5: Focus Management, Countdown & Emergency Abort (FOC)  |
| Epic 2: Step-by-Step Flows (AWE)   | Epic 6: Error Handling, Timeouts & Audit Trails (ERR)        |
| Epic 3: Visual Translation (TRANS) | Epic 7: Enterprise UI & 90Studio Branding (UI)               |
| Epic 4: Target Execution (EXEC)    | Epic 8: Verification & Sample Test Scenarios (TST)           |
+------------------------------------+--------------------------------------------------------------+
```

### 5.1 Epic 1: Visual Form Designer (US-VFD)

#### User Story US-VFD-01: Interactive Canvas Bounding Box Creation
- **Role**: Business Operations Analyst
- **Goal**: Visually draw rectangular bounding boxes on a 2D canvas representing form inputs.
- **Benefit**: Rapidly map complex form layouts without writing coordinate scripts or measuring pixels.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Successfully drawing a visual input box on canvas
    Given the kutomoto Visual Form Designer canvas is open and ready
    When I press the left mouse button at canvas coordinate (150, 200)
    And I drag the mouse pointer to canvas coordinate (450, 245)
    And I release the left mouse button
    Then a new rectangular bounding box is rendered at X=150, Y=200 with width=300 and height=45
    And the box displays an active selection border and 8 resize handles
    And the box is assigned the next sequential index badge (e.g. #1)
    And the Field Property Inspector updates immediately to display this box's parameters

  Scenario: Discarding sub-threshold accidental clicks
    Given the Visual Form Designer canvas is open
    When I click at coordinate (300, 300) without dragging (width < 10px or height < 10px)
    Then no bounding box is created
    And the canvas maintains its previous state without error
  ```

#### User Story US-VFD-02: Visual Box Sequencing & Manual Reordering
- **Role**: Banking Workflow Author
- **Goal**: Easily inspect and reorder the execution sequence of visual form boxes.
- **Benefit**: Ensure fields are populated in the exact logical order required by the target form.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Re-indexing execution order via property inspector
    Given the canvas contains three boxes with indices [1: "First Name", 2: "Last Name", 3: "Tax ID"]
    When I select box #3 ("Tax ID")
    And I change its sequence index in the Property Inspector to 1
    Then the system automatically updates all sequence ranks:
      | Box Name   | New Index |
      | Tax ID     | 1         |
      | First Name | 2         |
      | Last Name  | 3         |
    And the visual number badges on the canvas immediately reflect [1, 2, 3]
  ```

#### User Story US-VFD-03: Field Property Inspector & Navigation Rules
- **Role**: Telecom Workflow Specialist
- **Goal**: Configure label, field type, static or dynamic input text, and post-entry navigation action for each box.
- **Benefit**: Eliminate ambiguities regarding whether Tab or Enter moves focus to the subsequent control.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Configuring field properties and Tab navigation
    Given a visual bounding box is selected on the canvas
    When I enter "SIM Card ICCID" as Field Label
    And I select Field Type "Text Input"
    And I enter "8901410321111851072" as Value
    And I set Post-Action to "Tab"
    And I enable "Clear Before Typing"
    Then the box model stores these attributes
    And the visual box renders the label and an icon indicating Tab navigation
  ```

#### User Story US-VFD-04: Canvas Screenshot Background Underlay
- **Role**: Enterprise Automation Designer
- **Goal**: Load a screenshot of the target web or desktop form as a canvas background.
- **Benefit**: Visually align input boxes directly over original UI elements with pixel precision.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Loading an application form screenshot underlay
    Given the Visual Form Designer is open
    When I select "Load Form Image" and choose a valid PNG or JPEG screenshot file
    Then the canvas dimensions update to match the image resolution
    And the image is rendered as a stationary background layer
    And user-drawn bounding boxes overlay transparently with high contrast
  ```

---

### 5.2 Epic 2: Step-by-Step Action Workflow Creation (US-AWE)

#### User Story US-AWE-01: Manual Step Construction in Action Grid
- **Role**: Automation Engineer
- **Goal**: Manually construct and edit an action workflow using a structured step-by-step editor.
- **Benefit**: Create complex, highly customized automation sequences without canvas interactions.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Adding a granular text entry action step
    Given the Step-by-Step Flow Builder is open
    When I click "Add Action Step"
    And I choose Action Type "type_text"
    And I enter Payload "INV-2026-9081"
    And I set Keystroke Delay to 30 ms
    Then the step is appended to the workflow sequence
    And the step table displays: [Index: N, Action: type_text, Target: Active Focus, Delay: 30ms]
  ```

#### User Story US-AWE-02: Keyboard Navigation Primitives & Chords
- **Role**: ERP Data Entry Operator
- **Goal**: Add specific keyboard actions including Tab, Enter, Backspace, and key chords (`Ctrl+A`, `Ctrl+S`).
- **Benefit**: Accurately simulate complex keyboard shortcuts and rapid desktop navigation.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Adding Tab and Enter steps for form progression and submission
    Given an open Action Workflow in the Flow Builder
    When I append a step with Action Type "key_press" and Key "Tab"
    And I append a final step with Action Type "key_press" and Key "Enter"
    Then the workflow records the navigation step followed by the submission step
    And serializes them as valid action primitives in the JSON workflow model
  ```

#### User Story US-AWE-03: Coordinate-Based Mouse Clicks
- **Role**: System Operator
- **Goal**: Configure mouse click actions specifying precise screen or client coordinates and mouse buttons.
- **Benefit**: Click exact visual targets such as buttons, checkboxes, or canvas elements.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Adding a coordinate click action
    When I add a step with Action Type "click"
    And I specify Client Coordinates X=420, Y=350, Button="Left", ClickCount=1
    Then the workflow records the click step
    And during execution the engine repositions the cursor and dispatches mouse down and up events
  ```

#### User Story US-AWE-04: Step Reordering, Duplication, and Deletion
- **Role**: Workflow Maintainer
- **Goal**: Rapidly reorder, duplicate, or delete action steps in the workflow list.
- **Benefit**: Maintain and refactor automated fill flows with minimal friction.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Reordering steps in the flow editor
    Given a workflow containing steps [Step 1: focus_window, Step 2: click, Step 3: type_text]
    When I select Step 3 and click "Move Up"
    Then the step order updates to [Step 1: focus_window, Step 2: type_text, Step 3: click]
    And all step indices are re-numbered sequentially
  ```

---

### 5.3 Epic 3: Visual-to-Workflow Translation Semantics (US-TRANS)

#### User Story US-TRANS-01: Auto-Compiling Visual Boxes into Action Workflow
- **Role**: Non-Technical Business User
- **Goal**: Click "Compile Workflow" from a visual form layout to generate an executable action flow.
- **Benefit**: Instant, error-free translation of visual layouts into executable machine actions.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Compiling visual boxes into sequential action steps
    Given a Visual Form Layout with 2 text boxes and 1 submit button:
      | Box ID | Label       | Coords (X,Y,W,H)   | Value           | PostAction | ClearFirst |
      | b1     | Username    | (100, 100, 200, 36)| "admin_corp"    | tab        | true       |
      | b2     | Password    | (100, 150, 200, 36)| "P@ssword123!"  | tab        | true       |
      | b3     | Submit Btn  | (100, 210, 120, 40)| ""              | click      | false      |
    When I trigger the compiler function `compile_visual_boxes_to_workflow`
    Then the compiler generates an `ActionWorkflow` with the following sequence:
      | Step | Action Type | Details                                        |
      | 1    | focus_window| Focus configured target window                 |
      | 2    | click       | Center of Box 1 (X=200, Y=118)                 |
      | 3    | clear_field | select_all_backspace                           |
      | 4    | type_text   | Text="admin_corp", Delay=20ms                  |
      | 5    | key_press   | Tab                                            |
      | 6    | delay       | 120ms                                          |
      | 7    | clear_field | select_all_backspace                           |
      | 8    | type_text   | Text="P@ssword123!", Delay=20ms, is_secret=true|
      | 9    | key_press   | Tab                                            |
      | 10   | delay       | 120ms                                          |
      | 11   | submit      | Button click at Center of Box 3 (X=160, Y=230) |
    And the generated workflow passes all schema validations
  ```

---

### 5.4 Epic 4: Workflow Execution & Targeting Across Web and Desktop (US-EXEC)

#### User Story US-EXEC-01: Executing Automation against Open Web Browser Pages
- **Role**: Operations Specialist
- **Goal**: Execute an automated fill flow against an open web browser tab (Edge, Chrome, Firefox).
- **Benefit**: Streamline high-volume web portal forms entry without browser driver installations.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Automated filling and submission of an open web browser form
    Given a target web browser window is open displaying an enterprise form
    And an executable kutomoto workflow matching the browser window title
    When I trigger execution
    Then kutomoto brings the browser window to the foreground
    And sequentially navigates, clears, and inputs all field values into the web controls
    And clicks the form submit button
    And the web page processes and displays the submission confirmation
    And kutomoto reports execution status as "COMPLETED"
  ```

#### User Story US-EXEC-02: Executing Automation against Windows Desktop Applications
- **Role**: Core Banking Analyst
- **Goal**: Execute an automated fill flow against a native Windows desktop form (WinForms, WPF, Tkinter, SAP GUI).
- **Benefit**: Seamlessly automate legacy desktop systems that do not provide modern APIs.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Automated filling and submission of a native desktop application form
    Given a native Windows desktop form application is open and visible
    And a verified kutomoto workflow configured with the desktop window title regex
    When execution is triggered
    Then kutomoto activates the desktop application window
    And populates all text entries, combo boxes, and checkboxes in sequence
    And executes the submit button click or Enter keystroke
    And the desktop application acknowledges successful submission
  ```

---

### 5.5 Epic 5: Focus Management, Countdown & Emergency Abort (US-FOC)

#### User Story US-FOC-01: Pre-Execution Arming Countdown & Window Focus
- **Role**: Enterprise Operator
- **Goal**: Experience a visual 3-second countdown before execution begins, ensuring target readiness.
- **Benefit**: Verify that the correct target window and form tab are active before inputs fire.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: 3-second countdown and automatic window activation
    Given I click "Execute Workflow" in the kutomoto interface
    Then the engine enters "COUNTDOWN" state
    And a countdown HUD displays "Switching in 3... 2... 1..." with a visual progress indicator
    And the target window is activated and brought to the foreground via Win32 SetForegroundWindow
    When the countdown timer reaches 0
    Then the engine transitions to "RUNNING" state and dispatches Step 1 immediately
  ```

#### User Story US-FOC-02: Global Emergency Abort Hotkey (Escape / F10)
- **Role**: Compliance & Safety Officer
- **Goal**: Instantly halt automation at any millisecond by pressing the `Escape` key.
- **Benefit**: Prevent unintended inputs if an unexpected modal dialog or system alert appears.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Instant abort of running workflow via Escape key
    Given a workflow is currently in "RUNNING" state at Step 5 of 12
    When the operator presses the "Escape" key
    Then all input simulation ceases immediately within 50 milliseconds
    And no subsequent steps are dispatched
    And the engine state transitions to "STOPPING" then "STOPPED"
    And an emergency abort audit record is written to the execution log
  ```

---

### 5.6 Epic 6: Error Handling, Timeouts & Submission Verification (US-ERR)

#### User Story US-ERR-01: Target Window Resolution Failure Handling
- **Role**: System Operator
- **Goal**: Receive an immediate, clear error message when the target application window cannot be found.
- **Benefit**: Understand exactly why execution could not proceed without silent failures.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Handling missing target window
    Given a workflow configured for target title "Core Banking - Finacle"
    And no open desktop window matches "Core Banking - Finacle"
    When I attempt to execute the workflow
    Then the engine aborts before dispatching any inputs
    And transitions to "ERROR" state
    And displays: "Target Window Not Found: Unable to locate window matching 'Core Banking - Finacle'. Please open the target application."
  ```

#### User Story US-ERR-02: Immutable Audit Logging & Submission Verification
- **Role**: Compliance Auditor
- **Goal**: Review a complete, tamper-evident audit log of every executed action step.
- **Benefit**: Guarantee regulatory compliance in banking and telecom operations.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Capturing structured audit log with 90Studio attribution
    Given a workflow completes execution
    Then the audit log file contains:
      - Workflow ID, Name, and Execution UUID
      - Start timestamp, end timestamp, and total duration in milliseconds
      - Array of all executed steps with individual latency and status
      - Legal watermark: "Copyrights reserved to 90Studio"
      - Final outcome status: "SUCCESS"
    And sensitive password fields are masked as "********"
  ```

---

### 5.7 Epic 7: Enterprise UI & 90Studio Branding (US-UI)

#### User Story US-UI-01: Professional Desktop Presentation
- **Role**: Corporate User
- **Goal**: Interact with a polished, high-contrast desktop user interface suitable for financial institutions.
- **Benefit**: Minimize eye strain and cognitive load during intensive data operations.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Enterprise theme and responsive layout
    Given kutomoto is launched in Microsoft Edge App Mode
    Then the UI renders with deep navy/slate styling, clean typography, and zero browser toolbars
    And the interface scales crisply across 100%, 125%, 150%, and 200% display DPI settings
    And provides intuitive split panes for visual design, flow editing, and real-time execution logs
  ```

#### User Story US-UI-02: 90Studio Legal Attribution & Compliance
- **Role**: Legal & Compliance Officer
- **Goal**: Verify that all user-visible views contain the required intellectual property notice.
- **Benefit**: Ensure strict compliance with corporate branding and legal ownership mandates.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Verifying mandatory 90Studio branding across application views
    Given the kutomoto application is active
    Then the window title bar contains "kutomoto"
    And the status bar footer permanently displays "Copyrights reserved to 90Studio"
    And the About modal dialog displays "kutomoto" and "Copyrights reserved to 90Studio"
  ```

---

### 5.8 Epic 8: Verification & Sample Test Scenarios (US-TST)

#### User Story US-TST-01: End-to-End Automated Banking KYC Web Form Verification
- **Role**: Quality Assurance Engineer
- **Goal**: Validate end-to-end automated filling and submission of the provided Banking KYC Web Form.
- **Benefit**: Ensure regression-free automated browser form filling across updates.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: End-to-end web verification test
    Given the sample web form (`samples/web/index.html`) is open in a web browser
    And the pre-configured Banking KYC workflow is loaded in kutomoto
    When I execute the workflow
    Then kutomoto focuses the browser, fills all 6 fields in sequence, and clicks Submit
    And the web page displays a green confirmation panel: "Submission Succeeded: All 6 Fields Verified"
    And the submitted data payload matches the workflow values exactly
  ```

#### User Story US-TST-02: End-to-End Automated Telecom SIM Desktop Form Verification
- **Role**: Quality Assurance Engineer
- **Goal**: Validate end-to-end automated filling and submission of the provided Telecom SIM Desktop Form.
- **Benefit**: Ensure regression-free automated desktop form filling across updates.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: End-to-end desktop verification test
    Given the sample desktop form (`samples/desktop/sample_desktop_form.py`) is running
    And the pre-configured Telecom SIM Provisioning workflow is loaded in kutomoto
    When I execute the workflow
    Then kutomoto activates the desktop window, populates all fields, and triggers Submit
    And the desktop application status label updates to "Status: SIM PROVISIONED SUCCESSFULLY"
  ```

---

## 6. Win32 Automation Core, High-DPI Scaling & Platform Primitives

### 6.1 Win32 Per-Monitor V2 High-DPI Scaling Specification

Modern Windows 10 and 11 workstations operate with high-resolution displays (e.g. 4K, Surface displays) where the OS applies scaling factors (125%, 150%, 175%, 200%). When an automation process is DPI-unaware, Windows engages **DPI Virtualization (Bitmap Stretching)**:
- Window geometry returned by `GetWindowRect` or `GetClientRect` is virtualized to an artificial 96 DPI coordinate space.
- Mouse clicks injected via Win32 `SendInput` or `SetCursorPos` land at shifted, erroneous pixel coordinates.

To guarantee true 1:1 pixel accuracy, kutomoto enforces **Per-Monitor V2 DPI Awareness**:

```
+--------------------------------------------------------------------------------------------------+
| Context Value | Mode Name                   | Behavior & OS Handling                             |
+---------------+-----------------------------+----------------------------------------------------+
| -1            | UNAWARE                     | Virtualized coordinates; blurry DWM bitmap scaling |
| -2            | SYSTEM_AWARE                | Scaled once at logon; drifts across mixed monitors |
| -3            | PER_MONITOR_AWARE (V1)      | Window gets WM_DPICHANGED; non-client unscaled    |
| -4            | PER_MONITOR_AWARE_V2        | FULL OS NATIVE 1:1 PHYSICAL DEVICE PIXELS          |
+--------------------------------------------------------------------------------------------------+
```

kutomoto executes the following robust 3-stage fallback initialization ladder upon backend startup:

```python
"""
kutomoto.automation.win32_core.dpi
DPI Awareness Context Initializer for Windows OS
Copyrights reserved to 90Studio
"""
import ctypes
from ctypes import wintypes
import logging

logger = logging.getLogger("kutomoto.dpi")

DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE    = ctypes.c_void_p(-3)
PROCESS_PER_MONITOR_DPI_AWARE             = 2

def set_process_dpi_awareness() -> str:
    """
    Enforces Per-Monitor V2 DPI awareness on the running Kutomoto process.
    Returns the successfully applied awareness mode string.
    """
    user32 = ctypes.windll.user32
    
    # 1. Primary: Windows 10 Creators Update (Build 1703+) & Windows 11
    try:
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
        if user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2):
            logger.info("DPI Awareness set: Per-Monitor V2 (-4)")
            return "PER_MONITOR_V2"
        elif user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE):
            logger.info("DPI Awareness set: Per-Monitor V1 (-3)")
            return "PER_MONITOR_V1"
    except (AttributeError, OSError) as ex:
        logger.debug("SetProcessDpiAwarenessContext unavailable: %s", ex)

    # 2. Secondary: Windows 8.1 / Windows 10 pre-1703 via shcore.dll
    try:
        shcore = ctypes.windll.shcore
        shcore.SetProcessDpiAwareness.argtypes = [ctypes.c_int]
        shcore.SetProcessDpiAwareness.restype = ctypes.HRESULT
        if shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE) == 0:
            logger.info("DPI Awareness set: shcore PROCESS_PER_MONITOR_DPI_AWARE")
            return "SHCORE_PER_MONITOR"
    except (AttributeError, OSError) as ex:
        logger.debug("shcore.SetProcessDpiAwareness unavailable: %s", ex)

    # 3. Tertiary: Legacy Windows Vista / 7
    try:
        user32.SetProcessDPIAware.argtypes = []
        user32.SetProcessDPIAware.restype = wintypes.BOOL
        if user32.SetProcessDPIAware():
            logger.info("DPI Awareness set: user32 SetProcessDPIAware")
            return "SYSTEM_AWARE"
    except Exception as ex:
        logger.error("Failed to set any DPI awareness mode: %s", ex)

    return "UNAWARE"
```

### 6.2 64-bit ABI Memory Layout & 40-Byte Struct Alignment

On 64-bit Windows architectures (x86_64 / AMD64), C compilers enforce 8-byte pointer alignment boundaries. An incorrect `ctypes` definition causes `sizeof(INPUT)` to evaluate to 32, 36, or 48 bytes, resulting in `SendInput` failing immediately with `ERROR_INVALID_PARAMETER` (Win32 Error 87).

```
+---------------------------------------------------------------------------------+
| Offset (Bytes) | Field Name       | Type              | Size   | Alignment      |
+----------------+------------------+-------------------+--------+----------------+
| 0 .. 3         | type             | DWORD (wintypes)  | 4 B    | 4-byte         |
| 4 .. 7         | [PADDED BY COMP] | Explicit Pad      | 4 B    | Required for   |
|                |                  |                   |        | 8-byte union   |
| 8 .. 39        | union            | _INPUT_UNION      | 32 B   | 8-byte aligned |
+---------------------------------------------------------------------------------+
Total Size = 40 Bytes (sizeof(INPUT) == 40)
```

Normative 64-bit Python ctypes definitions:

```python
"""
kutomoto.automation.win32_core.input_structs
Normative 64-bit SendInput Structures for Windows OS
Copyrights reserved to 90Studio
"""
import ctypes
from ctypes import wintypes

INPUT_MOUSE    = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

# Mouse flags
MOUSEEVENTF_MOVE        = 0x0001
MOUSEEVENTF_LEFTDOWN    = 0x0002
MOUSEEVENTF_LEFTUP      = 0x0004
MOUSEEVENTF_RIGHTDOWN   = 0x0008
MOUSEEVENTF_RIGHTUP     = 0x0010
MOUSEEVENTF_MIDDLEDOWN  = 0x0020
MOUSEEVENTF_MIDDLEUP    = 0x0040
MOUSEEVENTF_WHEEL       = 0x0800
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_ABSOLUTE    = 0x8000

# Keyboard flags
KEYEVENTF_EXTENDEDKEY   = 0x0001
KEYEVENTF_KEYUP         = 0x0002
KEYEVENTF_UNICODE       = 0x0004
KEYEVENTF_SCANCODE      = 0x0008

ULONG_PTR = ctypes.c_size_t

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]

# Assertion verifying exact 64-bit alignment:
assert ctypes.sizeof(INPUT) == 40, f"Critical: INPUT struct must be 40 bytes, got {ctypes.sizeof(INPUT)}"
```

### 6.3 Keyboard Injection: KEYEVENTF_UNICODE vs Virtual Keys

kutomoto standardizes on a bifurcated keyboard injection architecture:
1. **Semantic Text Input (`KEYEVENTF_UNICODE = 0x0004`)**:
   - `wScan = ord(character)` UTF-16 code unit, `wVk = 0`.
   - Injected directly into the window message queue as `WM_CHAR` / `WM_UNICHAR`.
   - **Guaranteed Layout Immunity**: Text types identically whether the workstation has US QWERTY, French AZERTY, German QWERTZ, or Arabic keyboards active.
2. **Navigation & Functional Keys (Virtual Key Codes)**:
   - Dispatched using standard Win32 Virtual Key codes (`VK_TAB = 0x09`, `VK_RETURN = 0x0D`, `VK_BACK = 0x08`, `VK_ESCAPE = 0x1B`, `VK_SPACE = 0x20`).

Standard Virtual Key mapping table:
```python
VK_MAP = {
    "tab": 0x09, "enter": 0x0D, "return": 0x0D, "escape": 0x1B,
    "backspace": 0x08, "delete": 0x2E, "space": 0x20,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "ctrl": 0x11, "control": 0x11, "shift": 0x10, "alt": 0x12, "win": 0x5B,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
    "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "a": 0x41, "c": 0x43, "v": 0x56, "x": 0x58, "z": 0x5A
}
```

### 6.4 Window Attachment & Focus Stealing Protection (`AttachThreadInput`)

Beginning with Windows 98/2000 and reinforced in Windows 10 and 11, the OS prevents background processes from disrupting the operator by calling `SetForegroundWindow`. If called without active interaction, Windows flashes the taskbar button orange and preserves current foreground focus.

kutomoto bypasses this restriction using canonical **Thread Input Attachment**:

```python
"""
kutomoto.automation.win32_window.focus
Canonical Win32 Window Focus and Activation Core
Copyrights reserved to 90Studio
"""
import ctypes
from ctypes import wintypes
import time
import logging

logger = logging.getLogger("kutomoto.focus")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SW_RESTORE = 9

def activate_target_window(hwnd: int, timeout_ms: int = 1500) -> bool:
    """
    Guarantees bringing target HWND to the foreground on Windows 10/11
    using thread-input queue attachment and iconic state restoration.
    """
    if not hwnd or not user32.IsWindow(hwnd):
        logger.error("Invalid window handle: %s", hwnd)
        return False

    if user32.GetForegroundWindow() == hwnd:
        return True

    # 1. Un-minimize if iconic
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.06)

    foreground_hwnd = user32.GetForegroundWindow()
    current_thread_id = kernel32.GetCurrentThreadId()
    foreground_thread_id = user32.GetWindowThreadProcessId(foreground_hwnd, None) if foreground_hwnd else 0

    attached = False
    if foreground_thread_id != 0 and foreground_thread_id != current_thread_id:
        attached = bool(user32.AttachThreadInput(current_thread_id, foreground_thread_id, True))

    try:
        # Simulated Alt-key tap to unstick DWM foreground lock
        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 0x0002, 0)

        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetActiveWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(current_thread_id, foreground_thread_id, False)

    # Verification polling loop
    deadline = time.time() + (timeout_ms / 1000.0)
    while time.time() < deadline:
        if user32.GetForegroundWindow() == hwnd:
            time.sleep(0.04)
            return True
        time.sleep(0.03)

    return user32.GetForegroundWindow() == hwnd
```

### 6.5 Cross-Application Targeting: Browser Tabs vs Desktop Applications

kutomoto automates both open web browser pages and native Windows desktop applications using a unified targeting strategy:

```
+--------------------------------------------------------------------------------------------------+
| Mode 1: Window Title Regex Matching                                                             |
| - Matches top-level window titles (e.g. `.*Banking KYC.*`, `.*SAP GUI.*`).                     |
| Mode 2: Process Executable Filtering                                                             |
| - Restricts search to specific binaries (`msedge.exe`, `chrome.exe`, `saplogon.exe`).           |
| Mode 3: Interactive 3-Second Countdown HUD (Zero-Switching Friction)                             |
| - Shows a floating HUD allowing the user to click the desired window before filling starts.     |
| Mode 4: In-Place Global Hotkey (Ctrl+F9)                                                         |
| - Automates the currently active foreground window without window switching.                     |
+--------------------------------------------------------------------------------------------------+
```

Across desktop application frameworks (WPF, WinForms, Qt, Tkinter, SAP GUI), kutomoto's use of **Normalized Client Coordinates** ($0.0 \le u, v \le 1.0$) guarantees 100% targeting compatibility regardless of whether individual controls expose child `HWND` handles or render as direct raster surfaces.


---

## 7. Visual Form Designer Architecture, Box Model & JSON Schemas

### 7.1 Visual Form Designer Canvas & Box Model

The kutomoto Visual Form Designer provides an intuitive, high-precision visual canvas designed for both non-technical business operators and automation engineers.

```
+--------------------------------------------------------------------------------------------------+
|                                  VISUAL FORM DESIGNER CANVAS                                     |
+--------------------------------------------------------------------------------------------------+
| [Upload Screenshot Backdrop] [Grid Snap: 8px] [Auto-Align: 4px] [Clear Canvas] [Compile Flow]   |
+--------------------------------------------------------------------------------------------------+
| +----------------------------------------------------------------------------------------------+ |
| | (Form Screenshot Underlay Layer - 100% 1:1 Aspect Ratio)                                     | |
| |                                                                                              | |
| |   [#1] Borrower Legal Name                                                                   | |
| |   +-------------------------------------------------------------+                            | |
| |   | [NW]                       [N]                         [NE] |                            | |
| |   | [W]     Acme Industrial Supplies LLC                    [E] |                            | |
| |   | [SW]                       [S]                         [SE] |                            | |
| |   +-------------------------------------------------------------+                            | |
| |                                                                                              | |
| |   [#2] Tax ID / EIN                                                                          | |
| |   +-------------------------------+                                                          | |
| |   | 12-3456789                    |                                                          | |
| |   +-------------------------------+                                                          | |
| |                                                                                              | |
| |   [#3] Submit Application Button                                                             | |
| |   +-----------------------+                                                                  | |
| |   | [ Submit Loan Dossier]|                                                                  | |
| |   +-----------------------+                                                                  | |
| +----------------------------------------------------------------------------------------------+ |
+--------------------------------------------------------------------------------------------------+
| Field Property Inspector:                                                                        |
| Field Name: borrower_legal_name  | Type: Text  | Nav: Tab  | Clear Before: True  | Secret: False    |
+--------------------------------------------------------------------------------------------------+
```

Key visual designer capabilities:
1. **Interactive Canvas Bounding Box Creation**: Operators click and drag directly on top of form elements. Accidental clicks below 10x10 px are automatically rejected.
2. **8 Resize Handles & Clamping**: Placed boxes feature handles ($N, S, E, W, NW, NE, SW, SE$) with constraints ensuring width $\ge 24\text{px}$ and height $\ge 16\text{px}$.
3. **Magnetic Snap Guides**: Horizontal and vertical alignment guides appear when edges align within $\pm 4\text{px}$ of neighboring controls.
4. **Sequence Badges**: High-contrast badges (`[#1]`, `[#2]`) display execution order. Reordering boxes dynamically re-indexes sequence ranks without numbering gaps.
5. **Dual-Coordinate Resolution Independence**: Box coordinates $(x, y, w, h)$ on canvas $(W_c, H_c)$ normalize to:
   $$\text{norm\_x} = \frac{x}{W_c}, \quad \text{norm\_y} = \frac{y}{H_c}, \quad \text{norm\_w} = \frac{w}{W_c}, \quad \text{norm\_h} = \frac{h}{H_c}$$
   At runtime, physical screen coordinates adapt dynamically to the target application's live client bounds:
   $$\text{ScreenX} = X_{\text{client}} + \text{round}\left(\left(\text{norm\_x} + \frac{\text{norm\_w}}{2}\right) \times W_{\text{client}}\right)$$
   $$\text{ScreenY} = Y_{\text{client}} + \text{round}\left(\left(\text{norm\_y} + \frac{\text{norm\_h}}{2}\right) \times H_{\text{client}}\right)$$

### 7.2 VisualFormLayout Formal JSON Schema (Draft 2020-12)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://90studio.com/schemas/kutomoto/visual-layout.v1.json",
  "title": "VisualFormLayout",
  "description": "Visual Form Designer Layout Schema for kutomoto. Copyrights reserved to 90Studio.",
  "type": "object",
  "required": [
    "schema_version",
    "id",
    "name",
    "target",
    "canvas",
    "boxes",
    "copyright"
  ],
  "properties": {
    "schema_version": { "type": "string", "enum": ["1.0.0"] },
    "id": { "type": "string", "format": "uuid" },
    "name": { "type": "string", "minLength": 1, "maxLength": 128 },
    "description": { "type": "string", "maxLength": 1024 },
    "copyright": { "type": "string", "const": "Copyrights reserved to 90Studio" },
    "target": {
      "type": "object",
      "required": ["type", "window_title_pattern"],
      "properties": {
        "type": { "type": "string", "enum": ["web_browser", "windows_desktop", "any"] },
        "window_title_pattern": { "type": "string", "minLength": 1 },
        "process_name": { "type": "string" },
        "match_mode": { "type": "string", "enum": ["exact", "contains", "regex"], "default": "contains" }
      }
    },
    "canvas": {
      "type": "object",
      "required": ["width", "height"],
      "properties": {
        "width": { "type": "number", "minimum": 320 },
        "height": { "type": "number", "minimum": 240 },
        "scale": { "type": "number", "default": 1.0 },
        "background_image_path": { "type": "string" }
      }
    },
    "global_timing": {
      "type": "object",
      "properties": {
        "pre_delay_ms": { "type": "integer", "minimum": 0, "default": 100 },
        "typing_speed_ms": { "type": "integer", "minimum": 1, "maximum": 500, "default": 20 },
        "post_delay_ms": { "type": "integer", "minimum": 0, "default": 120 }
      }
    },
    "boxes": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": [
          "id",
          "name",
          "label",
          "field_type",
          "sequence_index",
          "rect",
          "norm_bounds",
          "value_config",
          "navigation"
        ],
        "properties": {
          "id": { "type": "string", "format": "uuid" },
          "name": { "type": "string", "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*$" },
          "label": { "type": "string", "minLength": 1, "maxLength": 64 },
          "field_type": {
            "type": "string",
            "enum": ["text", "number", "date", "select", "checkbox", "radio", "textarea", "submit_button"]
          },
          "sequence_index": { "type": "integer", "minimum": 1 },
          "rect": {
            "type": "object",
            "required": ["x", "y", "width", "height"],
            "properties": {
              "x": { "type": "number", "minimum": 0 },
              "y": { "type": "number", "minimum": 0 },
              "width": { "type": "number", "minimum": 24 },
              "height": { "type": "number", "minimum": 16 }
            }
          },
          "norm_bounds": {
            "type": "object",
            "required": ["norm_x", "norm_y", "norm_w", "norm_h"],
            "properties": {
              "norm_x": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
              "norm_y": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
              "norm_w": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
              "norm_h": { "type": "number", "minimum": 0.0, "maximum": 1.0 }
            }
          },
          "value_config": {
            "type": "object",
            "required": ["source_type", "is_secret", "clear_before_type"],
            "properties": {
              "source_type": {
                "type": "string",
                "enum": ["static", "variable", "generated", "runtime_prompt"]
              },
              "static_value": { "type": "string" },
              "variable_name": { "type": "string" },
              "generator_pattern": {
                "type": "string",
                "enum": ["timestamp_iso", "timestamp_compact", "uuid4", "counter_increment"]
              },
              "is_secret": { "type": "boolean", "default": false },
              "clear_before_type": { "type": "boolean", "default": true }
            }
          },
          "navigation": {
            "type": "string",
            "enum": ["tab", "enter", "click_next", "none"],
            "default": "tab"
          },
          "timing": {
            "type": "object",
            "properties": {
              "pre_delay_ms": { "type": "integer", "minimum": 0 },
              "typing_speed_ms": { "type": "integer", "minimum": 1, "maximum": 500 },
              "post_delay_ms": { "type": "integer", "minimum": 0 }
            }
          }
        }
      }
    }
  }
}
```

### 7.3 Unified Action Workflow Formal JSON Schema (Draft 2020-12)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://90studio.com/schemas/kutomoto/workflow.v1.json",
  "title": "KutomotoWorkflow",
  "description": "Unified Action Workflow Schema for kutomoto forms filling automation. Copyrights reserved to 90Studio.",
  "type": "object",
  "required": [
    "schema_version",
    "id",
    "name",
    "target_application",
    "execution_settings",
    "steps",
    "copyright"
  ],
  "properties": {
    "schema_version": { "type": "string", "enum": ["1.0.0"] },
    "id": { "type": "string", "format": "uuid" },
    "name": { "type": "string", "minLength": 1, "maxLength": 128 },
    "description": { "type": "string", "maxLength": 1024 },
    "author": { "type": "string" },
    "created_at": { "type": "string", "format": "date-time" },
    "updated_at": { "type": "string", "format": "date-time" },
    "copyright": { "type": "string", "const": "Copyrights reserved to 90Studio" },
    "source_mode": {
      "type": "string",
      "enum": ["visual_designer_generated", "manual_step_flow", "hybrid"]
    },
    "target_application": {
      "type": "object",
      "required": ["type", "window_title_pattern"],
      "properties": {
        "type": { "type": "string", "enum": ["web_browser", "windows_desktop", "any"] },
        "window_title_pattern": { "type": "string", "minLength": 1 },
        "process_name": { "type": "string" },
        "browser_url_pattern": { "type": "string" },
        "match_mode": { "type": "string", "enum": ["exact", "contains", "regex"], "default": "contains" }
      }
    },
    "execution_settings": {
      "type": "object",
      "required": ["default_step_delay_ms", "typing_speed_ms", "stop_on_error"],
      "properties": {
        "countdown_seconds": { "type": "integer", "minimum": 0, "maximum": 30, "default": 3 },
        "default_step_delay_ms": { "type": "integer", "minimum": 10, "maximum": 10000, "default": 120 },
        "typing_speed_ms": { "type": "integer", "minimum": 1, "maximum": 500, "default": 20 },
        "stop_on_error": { "type": "boolean", "default": true },
        "error_recovery_policy": {
          "type": "string",
          "enum": ["abort", "retry_step", "prompt_user", "skip_step"],
          "default": "abort"
        },
        "max_step_retries": { "type": "integer", "minimum": 0, "maximum": 5, "default": 2 },
        "failsafe_corner_enabled": { "type": "boolean", "default": true },
        "abort_hotkey": { "type": "string", "default": "Escape" }
      }
    },
    "variables": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "default_value"],
        "properties": {
          "name": { "type": "string", "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*$" },
          "description": { "type": "string" },
          "default_value": { "type": "string" },
          "type": { "type": "string", "enum": ["string", "number", "date", "secret"], "default": "string" },
          "required": { "type": "boolean", "default": false }
        }
      }
    },
    "designer_metadata": {
      "type": "object",
      "properties": {
        "canvas_width": { "type": "number" },
        "canvas_height": { "type": "number" },
        "background_image_path": { "type": "string" },
        "box_count": { "type": "integer" }
      }
    },
    "steps": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["step_id", "sequence_index", "action_type", "enabled"],
        "properties": {
          "step_id": { "type": "string", "format": "uuid" },
          "sequence_index": { "type": "integer", "minimum": 1 },
          "label": { "type": "string" },
          "action_type": {
            "type": "string",
            "enum": [
              "focus_window",
              "click",
              "type_text",
              "key_press",
              "hotkey",
              "clear_field",
              "delay",
              "submit",
              "scroll",
              "prompt_user_input"
            ]
          },
          "enabled": { "type": "boolean", "default": true },
          "pre_delay_ms": { "type": "integer", "minimum": 0, "default": 0 },
          "post_delay_ms": { "type": "integer", "minimum": 0, "default": 0 },
          "parameters": {
            "type": "object",
            "properties": {
              "window_title_pattern": { "type": "string" },
              "process_name": { "type": "string" },
              "x": { "type": "number" },
              "y": { "type": "number" },
              "norm_x": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
              "norm_y": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
              "coordinate_mode": {
                "type": "string",
                "enum": ["screen", "window_client", "normalized"],
                "default": "normalized"
              },
              "button": { "type": "string", "enum": ["left", "right", "middle"], "default": "left" },
              "click_count": { "type": "integer", "enum": [1, 2, 3], "default": 1 },
              "text": { "type": "string" },
              "is_secret": { "type": "boolean", "default": false },
              "keystroke_delay_ms": { "type": "integer", "minimum": 0, "default": 20 },
              "key": { "type": "string" },
              "repeat_count": { "type": "integer", "minimum": 1, "default": 1 },
              "keys": { "type": "array", "items": { "type": "string" } },
              "clear_strategy": {
                "type": "string",
                "enum": ["select_all_backspace", "triple_click_delete", "backspace_repeat"],
                "default": "select_all_backspace"
              },
              "duration_ms": { "type": "integer", "minimum": 0 },
              "submit_method": { "type": "string", "enum": ["enter_key", "button_click"], "default": "enter_key" },
              "delta_x": { "type": "integer", "default": 0 },
              "delta_y": { "type": "integer", "default": 0 },
              "variable_name": { "type": "string" },
              "prompt_message": { "type": "string" }
            }
          }
        }
      }
    }
  }
}
```

---

## 8. Visual-to-Workflow Compilation Pipeline (5-Pass Algorithm)

The compiler translates 2D visual layouts into optimized, linear sequences of Win32 automation primitives through a rigorous 5-pass deterministic pipeline:

```
[VisualFormLayout Input]
          |
          v
+--------------------------------------------------------------------------------------------------+
| PASS 1: Integrity Validation & Geometry Normalization                                            |
| - Verify non-zero box dimensions (width >= 24px, height >= 16px)                                 |
| - Validate unique IDs, field names, and variable tokens                                          |
| - Compute exact normalized center points (norm_x + norm_w/2, norm_y + norm_h/2)                  |
+--------------------------------------------------------------------------------------------------+
          |
          v
+--------------------------------------------------------------------------------------------------+
| PASS 2: Sequence Ordering & Spatial Topological Sorting                                          |
| - If sequence_index defined on all boxes: sort strictly by sequence_index                        |
| - If sequence_index missing/ambiguous: 2D Spatial Band Sort (Reading Order: Top-to-Bottom, L-to-R)|
+--------------------------------------------------------------------------------------------------+
          |
          v
+--------------------------------------------------------------------------------------------------+
| PASS 3: Traversal Strategy Selection                                                             |
| - 'coordinate_targeted': click center of every field (highest reliability)                       |
| - 'tab_chained': click initial field, navigate subsequent fields via Tab key                     |
| - 'hybrid': click controls/combos/buttons, Tab through adjacent text inputs                      |
+--------------------------------------------------------------------------------------------------+
          |
          v
+--------------------------------------------------------------------------------------------------+
| PASS 4: Atomic Step Generation & Parameter Synthesis                                             |
| - Inject initial window focus activation step                                                    |
| - Synthesize field actions: Click -> Clear -> Prompt/Type -> Navigation                          |
| - Inject form submission step (Enter key or button coordinate click)                             |
+--------------------------------------------------------------------------------------------------+
          |
          v
+--------------------------------------------------------------------------------------------------+
| PASS 5: Peephole Optimization & Safety Post-Processing                                           |
| - Consolidate consecutive delay steps (sum duration_ms)                                          |
| - Remove redundant focus/clear sequences                                                         |
| - Re-index step sequence integers sequentially (1..N)                                            |
| - Embed 90Studio legal copyright notice and canvas metadata                                      |
+--------------------------------------------------------------------------------------------------+
          |
          v
[Compiled ActionWorkflow Output]
```

### 8.1 Reference Compilation Implementation

```python
"""
kutomoto.designer.compiler
Visual-to-Workflow Compiler (5-Pass Pipeline)
Copyrights reserved to 90Studio
"""
import uuid
from typing import List, Dict, Any

def compile_visual_boxes_to_workflow(
    layout: Dict[str, Any],
    traversal_mode: str = "coordinate_targeted"
) -> Dict[str, Any]:
    """
    Translates a VisualFormLayout document into a fully executable ActionWorkflow.
    """
    boxes = layout.get("boxes", [])
    if not boxes:
        raise ValueError("Compilation error: layout contains no visual boxes.")

    # PASS 1: Integrity Validation & Geometry Normalization
    canvas_w = float(layout.get("canvas", {}).get("width", 1024))
    canvas_h = float(layout.get("canvas", {}).get("height", 768))
    validated_boxes = []

    for idx, b in enumerate(boxes):
        rect = b.get("rect", {})
        w, h = float(rect.get("width", 0)), float(rect.get("height", 0))
        x, y = float(rect.get("x", 0)), float(rect.get("y", 0))

        if w <= 0 or h <= 0:
            raise ValueError(f"Box '{b.get('name', idx)}' has invalid zero or negative dimensions.")

        norm_bounds = b.get("norm_bounds")
        if not norm_bounds:
            norm_x, norm_y = round(x / canvas_w, 4), round(y / canvas_h, 4)
            norm_w, norm_h = round(w / canvas_w, 4), round(h / canvas_h, 4)
        else:
            norm_x = float(norm_bounds.get("norm_x", 0.0))
            norm_y = float(norm_bounds.get("norm_y", 0.0))
            norm_w = float(norm_bounds.get("norm_w", 0.0))
            norm_h = float(norm_bounds.get("norm_h", 0.0))

        center_norm_x = round(norm_x + (norm_w / 2.0), 4)
        center_norm_y = round(norm_y + (norm_h / 2.0), 4)

        validated_boxes.append({
            **b,
            "id": b.get("id") or str(uuid.uuid4()),
            "center_norm_x": center_norm_x,
            "center_norm_y": center_norm_y,
            "norm_x": norm_x,
            "norm_y": norm_y,
            "norm_w": norm_w,
            "norm_h": norm_h
        })

    # PASS 2: Sequence Ordering & Spatial Topological Sorting
    has_explicit_indices = all(b.get("sequence_index", 0) > 0 for b in validated_boxes)
    if has_explicit_indices:
        ordered_boxes = sorted(validated_boxes, key=lambda b: b["sequence_index"])
    else:
        # Spatial 2D reading-order band sort
        heights = sorted([b["norm_h"] for b in validated_boxes])
        median_h = heights[len(heights) // 2] if heights else 0.05
        band_threshold = median_h * 0.75
        sorted_by_y = sorted(validated_boxes, key=lambda b: b["norm_y"])
        bands: List[List[Dict[str, Any]]] = []
        current_band = [sorted_by_y[0]]

        for b in sorted_by_y[1:]:
            if abs(b["norm_y"] - current_band[-1]["norm_y"]) <= band_threshold:
                current_band.append(b)
            else:
                bands.append(current_band)
                current_band = [b]
        bands.append(current_band)

        ordered_boxes = []
        for band in bands:
            ordered_boxes.extend(sorted(band, key=lambda b: b["norm_x"]))

    # PASS 3 & 4: Traversal Strategy Selection & Step Generation
    target_info = layout.get("target", {})
    global_timing = layout.get("global_timing", {})
    default_pre_delay = global_timing.get("pre_delay_ms", 100)
    default_typing_speed = global_timing.get("typing_speed_ms", 20)
    default_post_delay = global_timing.get("post_delay_ms", 120)

    steps: List[Dict[str, Any]] = []

    # Window focus step
    steps.append({
        "step_id": str(uuid.uuid4()),
        "sequence_index": 1,
        "label": f"Focus Window: {target_info.get('window_title_pattern', 'Target Window')}",
        "action_type": "focus_window",
        "enabled": True,
        "pre_delay_ms": 0,
        "post_delay_ms": 250,
        "parameters": {
            "window_title_pattern": target_info.get("window_title_pattern", ""),
            "process_name": target_info.get("process_name", ""),
            "match_mode": target_info.get("match_mode", "contains")
        }
    })

    for idx, box in enumerate(ordered_boxes):
        field_type = box.get("field_type", "text")
        val_cfg = box.get("value_config", {})
        nav_action = box.get("navigation", "tab")
        timing = box.get("timing", {})
        pre_delay = timing.get("pre_delay_ms", default_pre_delay)
        post_delay = timing.get("post_delay_ms", default_post_delay)
        typing_speed = timing.get("typing_speed_ms", default_typing_speed)

        requires_click = True
        if traversal_mode == "tab_chained" and idx > 0 and field_type in ("text", "number", "date", "textarea"):
            requires_click = False

        if requires_click:
            steps.append({
                "step_id": str(uuid.uuid4()),
                "sequence_index": len(steps) + 1,
                "label": f"Click [{box.get('label', box.get('name'))}]",
                "action_type": "click",
                "enabled": True,
                "pre_delay_ms": pre_delay,
                "post_delay_ms": 60,
                "parameters": {
                    "norm_x": box["center_norm_x"],
                    "norm_y": box["center_norm_y"],
                    "coordinate_mode": "normalized",
                    "button": "left",
                    "click_count": 1
                }
            })

        if field_type in ("text", "number", "date", "textarea") and val_cfg.get("clear_before_type", True):
            steps.append({
                "step_id": str(uuid.uuid4()),
                "sequence_index": len(steps) + 1,
                "label": f"Clear Field [{box.get('name')}]",
                "action_type": "clear_field",
                "enabled": True,
                "pre_delay_ms": 0,
                "post_delay_ms": 40,
                "parameters": { "clear_strategy": "select_all_backspace" }
            })

        if field_type in ("text", "number", "date", "textarea"):
            src_type = val_cfg.get("source_type", "static")
            if src_type == "variable":
                text_payload = f"{{{{{val_cfg.get('variable_name', box.get('name'))}}}}}"
            elif src_type == "runtime_prompt":
                var_name = val_cfg.get("variable_name", box.get("name"))
                steps.append({
                    "step_id": str(uuid.uuid4()),
                    "sequence_index": len(steps) + 1,
                    "label": f"Prompt Operator for [{box.get('label')}]",
                    "action_type": "prompt_user_input",
                    "enabled": True,
                    "pre_delay_ms": 0,
                    "post_delay_ms": 50,
                    "parameters": {
                        "variable_name": var_name,
                        "prompt_message": f"Please enter value for {box.get('label')}:",
                        "is_password": val_cfg.get("is_secret", False)
                    }
                })
                text_payload = f"{{{{{var_name}}}}}"
            elif src_type == "generated":
                text_payload = f"{{{{${val_cfg.get('generator_pattern', 'timestamp_iso')}}}}}"
            else:
                text_payload = val_cfg.get("static_value", "")

            steps.append({
                "step_id": str(uuid.uuid4()),
                "sequence_index": len(steps) + 1,
                "label": f"Type into [{box.get('name')}]",
                "action_type": "type_text",
                "enabled": True,
                "pre_delay_ms": 0,
                "post_delay_ms": post_delay,
                "parameters": {
                    "text": text_payload,
                    "keystroke_delay_ms": typing_speed,
                    "is_secret": val_cfg.get("is_secret", False)
                }
            })

        elif field_type == "checkbox":
            steps.append({
                "step_id": str(uuid.uuid4()),
                "sequence_index": len(steps) + 1,
                "label": f"Toggle Checkbox [{box.get('name')}]",
                "action_type": "key_press",
                "enabled": True,
                "pre_delay_ms": 0,
                "post_delay_ms": post_delay,
                "parameters": { "key": "space", "repeat_count": 1 }
            })

        elif field_type == "submit_button":
            steps.append({
                "step_id": str(uuid.uuid4()),
                "sequence_index": len(steps) + 1,
                "label": f"Submit Form via [{box.get('label', 'Submit')}]",
                "action_type": "submit",
                "enabled": True,
                "pre_delay_ms": pre_delay,
                "post_delay_ms": 1000,
                "parameters": {
                    "submit_method": "button_click" if requires_click else "enter_key",
                    "norm_x": box["center_norm_x"],
                    "norm_y": box["center_norm_y"]
                }
            })
            continue

        if nav_action == "tab":
            steps.append({
                "step_id": str(uuid.uuid4()),
                "sequence_index": len(steps) + 1,
                "label": f"Navigate (Tab) from [{box.get('name')}]",
                "action_type": "key_press",
                "enabled": True,
                "pre_delay_ms": 0,
                "post_delay_ms": 100,
                "parameters": { "key": "tab", "repeat_count": 1 }
            })
        elif nav_action == "enter":
            steps.append({
                "step_id": str(uuid.uuid4()),
                "sequence_index": len(steps) + 1,
                "label": f"Navigate (Enter) from [{box.get('name')}]",
                "action_type": "key_press",
                "enabled": True,
                "pre_delay_ms": 0,
                "post_delay_ms": 200,
                "parameters": { "key": "enter", "repeat_count": 1 }
            })

    # PASS 5: Peephole Optimization & Safety Post-Processing
    optimized_steps: List[Dict[str, Any]] = []
    for s in steps:
        if optimized_steps and optimized_steps[-1]["action_type"] == "delay" and s["action_type"] == "delay":
            optimized_steps[-1]["parameters"]["duration_ms"] += s["parameters"]["duration_ms"]
        else:
            optimized_steps.append(s)

    for seq, s in enumerate(optimized_steps, start=1):
        s["sequence_index"] = seq

    return {
        "schema_version": "1.0.0",
        "id": str(uuid.uuid4()),
        "name": layout.get("name", "Compiled Form Workflow"),
        "description": layout.get("description", "Compiled from Visual Form Layout"),
        "author": "kutomoto Visual Form Compiler",
        "created_at": "2026-11-04T22:30:00Z",
        "updated_at": "2026-11-04T22:30:00Z",
        "copyright": "Copyrights reserved to 90Studio",
        "source_mode": "visual_designer_generated",
        "target_application": target_info,
        "execution_settings": {
            "countdown_seconds": 3,
            "default_step_delay_ms": default_post_delay,
            "typing_speed_ms": default_typing_speed,
            "stop_on_error": True,
            "error_recovery_policy": "abort",
            "max_step_retries": 2,
            "failsafe_corner_enabled": True,
            "abort_hotkey": "Escape"
        },
        "variables": layout.get("variables", []),
        "designer_metadata": {
            "canvas_width": canvas_w,
            "canvas_height": canvas_h,
            "box_count": len(ordered_boxes)
        },
        "steps": optimized_steps
    }
```

### 8.2 Compiler Production Hardening Directives (Milestone M3/M4 Contract)

While Section 8.1 provides the baseline reference compilation algorithm, production implementation in `src/kutomoto/designer/compiler.py` (Milestone M3) must enforce the following four hardening directives established by empirical verification:

1. **Normalized Coordinate Boundary Clamping (Pass 1)**:
   Boxes placed or dragged outside the visual canvas area (yielding negative coordinates or values exceeding canvas boundaries) must have their normalized coordinates clamped to the interval `[0.0, 1.0]`:
   ```python
   norm_x = max(0.0, min(1.0, round(x / canvas_w, 4)))
   norm_y = max(0.0, min(1.0, round(y / canvas_h, 4)))
   norm_w = max(0.0, min(1.0 - norm_x, round(w / canvas_w, 4)))
   norm_h = max(0.0, min(1.0 - norm_y, round(h / canvas_h, 4)))
   ```
   This guarantees that generated action workflows strictly conform to the `minimum: 0.0, maximum: 1.0` constraints of the `KutomotoWorkflow` formal JSON schema.

2. **Strict Non-Zero Canvas Validation (Pass 1)**:
   Pass 1 must validate canvas dimensions prior to performing division:
   ```python
   if canvas_w <= 0 or canvas_h <= 0:
       raise ValueError(f"Compilation error: Canvas dimensions must be strictly positive, got {canvas_w}x{canvas_h}.")
   ```

3. **Pydantic Model Schema Flexibility for Optional Box Elements**:
   In Milestone M3 Pydantic models (`src/kutomoto/designer/schema.py`), `norm_bounds` and `value_config` must be declared with default factories:
   ```python
   norm_bounds: Optional[NormBounds] = None
   value_config: Optional[ValueConfig] = None
   ```
   This avoids contract friction when importing designer drafts or compiling non-input elements (e.g., submit buttons and static headers).

4. **Submit Button Telemetry Identifier Fallback (Pass 3 & 4)**:
   When synthesizing step labels for submit button actions, the compiler must fall back to the box name if an explicit label is omitted:
   ```python
   button_label = box.get("label") or box.get("name", "Submit")
   label = f"Submit Form via [{button_label}]"
   ```

---

## 9. Workflow Execution Engine & Finite State Machine (FSM)

### 9.1 7-State FSM Architecture

The kutomoto execution runtime operates as a non-blocking asynchronous state machine managing 7 discrete states:

```
                  +----------------------------------------------+
                  |                     IDLE                     |
                  +----------------------------------------------+
                                         |
                                 (EXECUTE_START)
                                         v
                  +----------------------------------------------+
                  |                  VALIDATING                  |
                  +----------------------------------------------+
                         |                              |
                 (VALIDATION_OK)               (VALIDATION_FAILED)
                         v                              v
        +--------------------------------+      +----------------+
        |           COUNTDOWN            |      |     ERROR      |
        +--------------------------------+      +----------------+
            |                       |                   ^
      (USER_ABORT)          (COUNTDOWN_DONE)            |
            v                       v                   |
     +--------------+     +--------------------+        |
     |   STOPPED    |     |      RUNNING       |        |
     +--------------+     +--------------------+        |
                            |   ^            |          |
               (USER_PAUSE) |   |            |          |
                            v   |            |          |
                        +-----------+        |          |
                        |  PAUSED   |        |          |
                        +-----------+        |          |
                            |                |          |
                       (USER_ABORT)          |          |
                            v                |          |
                        [ STOPPED ]          |          |
                                             |          |
                                      (STEP_FAILURE)    |
                                             v          |
                                    +-----------------+ |
                                    | ERROR_RECOVERY  |-+
                                    +-----------------+ (ABORT_FATAL)
                                      |             |
                                (RETRY_STEP)   (SKIP_STEP)
                                      |             |
                                      +------+------+
                                             |
                                             v
                                        [ RUNNING ]
                                             |
                                      (ALL_STEPS_DONE)
                                             v
                                    +-----------------+
                                    |    COMPLETED    |
                                    +-----------------+
```

### 9.2 Formal State Transition Matrix (T01 – T18)

| # | Current State | Trigger Event | Next State | Guard / Condition | Actions / Side Effects |
|---|:---|:---|:---|:---|:---|
| T01 | `IDLE` | `EXECUTE_START` | `VALIDATING` | Workflow payload present | Initialize execution timer; load runtime variable bindings |
| T02 | `VALIDATING` | `VALIDATION_OK` | `COUNTDOWN` | Schema valid & variables resolved | Spawn Countdown HUD overlay; begin 3-second tick timer |
| T03 | `VALIDATING` | `VALIDATION_FAILED` | `ERROR` | Missing variables or bad schema | Emit validation error log; alert UI console |
| T04 | `COUNTDOWN` | `COUNTDOWN_TICK` | `COUNTDOWN` | Timer remaining $> 0$ | Decrement counter HUD (3 -> 2 -> 1) |
| T05 | `COUNTDOWN` | `COUNTDOWN_DONE` | `RUNNING` | Timer reached 0 | Close HUD; force focus to target `hWnd`; start step loop at index 0 |
| T06 | `COUNTDOWN` | `ABORT_TRIGGERED` | `STOPPED` | User pressed `Escape` or clicked cancel | Dismiss HUD; log abort event; return to `IDLE` |
| T07 | `RUNNING` | `STEP_SUCCESS` | `RUNNING` | More steps remaining | Increment `step_index += 1`; wait `post_delay_ms` |
| T08 | `RUNNING` | `ALL_STEPS_DONE` | `COMPLETED` | `step_index == total_steps` | Flush audit log; trigger completion notification chime |
| T09 | `RUNNING` | `USER_PAUSE` | `PAUSED` | User clicked Pause or hotkey | Suspend async sleep event; render floating "PAUSED" HUD |
| T10 | `RUNNING` | `FOCUS_LOST` | `PAUSED` | `GetForegroundWindow() != target_hwnd` | Auto-pause to prevent blind typing into wrong app |
| T11 | `RUNNING` | `ABORT_TRIGGERED` | `STOPPING` | `Escape` pressed or failsafe corner $(0,0)$ hit | Purge key injection queue; release modifier keys |
| T12 | `RUNNING` | `STEP_EXCEPTION` | `ERROR_RECOVERY` | Step execution threw Win32 or timeout error | Check `execution_settings.error_recovery_policy` |
| T13 | `PAUSED` | `USER_RESUME` | `RUNNING` | Target window re-focused | Clear pause event; resume step loop at current index |
| T14 | `PAUSED` | `ABORT_TRIGGERED` | `STOPPED` | User clicked Abort | Cancel remaining steps; flush partial audit log |
| T15 | `ERROR_RECOVERY`| `POLICY_RETRY` | `RUNNING` | `retry_count < max_step_retries` | Increment retry counter; wait exponential backoff; re-dispatch |
| T16 | `ERROR_RECOVERY`| `POLICY_SKIP` | `RUNNING` | `error_recovery_policy == 'skip_step'` | Log warning entry; increment `step_index += 1` |
| T17 | `ERROR_RECOVERY`| `POLICY_ABORT` | `ERROR` | `error_recovery_policy == 'abort'` or retries exhausted | Record step failure in audit log; abort workflow |
| T18 | `STOPPING` | `CLEANUP_DONE` | `STOPPED` | Modifiers released | Reset Win32 input state; return focus to kutomoto |

### 9.3 Safety Architecture & Loss-of-Focus Guardian

1. **Screen Corner Slam Failsafe `(0, 0)`**: Polled before every action. If cursor coordinates satisfy $X \le 2$ and $Y \le 2$, automation halts within 5ms.
2. **Global Escape Abort**: Monitored via asynchronous keyboard polling. Immediately purges input queues and releases all modifier keys (`VK_CONTROL`, `VK_SHIFT`, `VK_MENU`, `VK_LWIN`).
3. **Loss-of-Focus Guardian**: Prior to each typing or click action, verifies:
   $$\text{user32.GetForegroundWindow()} == \text{target\_hwnd}$$
   If focus was shifted by user activity or background popups, execution pauses instantly to prevent input leakage.

---

## 10. Enterprise Audit Logging & Compliance (90Studio Standard)

### 10.1 Structured Audit Log JSON Schema (Draft 2020-12)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://90studio.com/schemas/kutomoto/audit-log.v1.json",
  "title": "KutomotoAuditLog",
  "description": "Enterprise Compliance Audit Log Schema for kutomoto. Copyrights reserved to 90Studio.",
  "type": "object",
  "required": [
    "audit_version",
    "system",
    "copyright",
    "execution_id",
    "workflow_id",
    "workflow_name",
    "timestamp_utc",
    "operator_username",
    "host_machine",
    "target_application",
    "execution_summary",
    "step_events"
  ],
  "properties": {
    "audit_version": { "type": "string", "enum": ["1.0.0"] },
    "system": { "type": "string", "const": "kutomoto" },
    "copyright": { "type": "string", "const": "Copyrights reserved to 90Studio" },
    "execution_id": { "type": "string", "format": "uuid" },
    "workflow_id": { "type": "string", "format": "uuid" },
    "workflow_name": { "type": "string" },
    "source_mode": { "type": "string", "enum": ["visual_designer_generated", "manual_step_flow", "hybrid"] },
    "timestamp_utc": { "type": "string", "format": "date-time" },
    "operator_username": { "type": "string" },
    "host_machine": { "type": "string" },
    "os_version": { "type": "string" },
    "target_application": {
      "type": "object",
      "required": ["title", "hwnd", "process_name"],
      "properties": {
        "title": { "type": "string" },
        "hwnd": { "type": "integer" },
        "process_name": { "type": "string" },
        "pid": { "type": "integer" }
      }
    },
    "execution_summary": {
      "type": "object",
      "required": ["total_steps", "successful_steps", "failed_steps", "retried_steps", "duration_seconds", "final_status"],
      "properties": {
        "total_steps": { "type": "integer", "minimum": 0 },
        "successful_steps": { "type": "integer", "minimum": 0 },
        "failed_steps": { "type": "integer", "minimum": 0 },
        "retried_steps": { "type": "integer", "minimum": 0 },
        "duration_seconds": { "type": "number", "minimum": 0 },
        "final_status": { "type": "string", "enum": ["SUCCESS", "FAILED", "ABORTED"] }
      }
    },
    "step_events": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["step_index", "action_type", "timestamp_offset_ms", "parameters_summary", "latency_ms", "status"],
        "properties": {
          "step_index": { "type": "integer", "minimum": 1 },
          "action_type": { "type": "string" },
          "label": { "type": "string" },
          "timestamp_offset_ms": { "type": "integer", "minimum": 0 },
          "parameters_summary": { "type": "string" },
          "latency_ms": { "type": "number", "minimum": 0 },
          "status": { "type": "string", "enum": ["SUCCESS", "ERROR", "SKIPPED", "RETRIED"] },
          "error_details": { "type": "string" }
        }
      }
    }
  }
}
```

### 10.2 Production Audit Record Example

```json
{
  "audit_version": "1.0.0",
  "system": "kutomoto",
  "copyright": "Copyrights reserved to 90Studio",
  "execution_id": "e81d4a92-91f3-42e1-884d-61e892cfa712",
  "workflow_id": "7b8e19d2-3140-4968-a40e-7d6f5c88102a",
  "workflow_name": "Retail KYC Customer Onboarding Flow",
  "source_mode": "visual_designer_generated",
  "timestamp_utc": "2026-11-04T22:35:10.125Z",
  "operator_username": "enterprise_teller_04",
  "host_machine": "CORP-W11-B042",
  "os_version": "Microsoft Windows 11 Enterprise (10.0.22631)",
  "target_application": {
    "title": "Retail Account Opening - Core Banking",
    "hwnd": 196840,
    "process_name": "msedge.exe",
    "pid": 14220
  },
  "execution_summary": {
    "total_steps": 6,
    "successful_steps": 6,
    "failed_steps": 0,
    "retried_steps": 0,
    "duration_seconds": 2.74,
    "final_status": "SUCCESS"
  },
  "step_events": [
    {
      "step_index": 1,
      "action_type": "focus_window",
      "label": "Focus Retail Account Opening Window",
      "timestamp_offset_ms": 10,
      "parameters_summary": "pattern='Retail Account Opening', hwnd=0x000300E8",
      "latency_ms": 250.0,
      "status": "SUCCESS"
    },
    {
      "step_index": 2,
      "action_type": "click",
      "label": "Click [Full Name]",
      "timestamp_offset_ms": 265,
      "parameters_summary": "norm_coords=(0.3800, 0.2100), button=left",
      "latency_ms": 60.5,
      "status": "SUCCESS"
    },
    {
      "step_index": 3,
      "action_type": "clear_field",
      "label": "Clear Field [customer_full_name]",
      "timestamp_offset_ms": 330,
      "parameters_summary": "strategy=select_all_backspace",
      "latency_ms": 40.0,
      "status": "SUCCESS"
    },
    {
      "step_index": 4,
      "action_type": "type_text",
      "label": "Type Customer Name",
      "timestamp_offset_ms": 375,
      "parameters_summary": "text='Eleanor Vance' (13 chars, 20ms pacing)",
      "latency_ms": 260.0,
      "status": "SUCCESS"
    },
    {
      "step_index": 5,
      "action_type": "key_press",
      "label": "Navigate (Tab)",
      "timestamp_offset_ms": 640,
      "parameters_summary": "key=VK_TAB, count=1",
      "latency_ms": 100.0,
      "status": "SUCCESS"
    },
    {
      "step_index": 6,
      "action_type": "submit",
      "label": "Submit Account Opening Form",
      "timestamp_offset_ms": 745,
      "parameters_summary": "method=enter_key, post_wait_ms=1000",
      "latency_ms": 1002.0,
      "status": "SUCCESS"
    }
  ]
}
```

---

## 11. Verification Targets & Test Scenarios Specification

To guarantee end-to-end verification of kutomoto's automation capabilities across both open web browser pages and native Windows desktop applications, the repository provides two dedicated sample target applications:

### 11.1 Sample Web Form Target (`samples/web/index.html`)

- **Domain**: Banking KYC Customer Onboarding
- **Window Title**: `Banking KYC Portal - 90Studio Enterprise`
- **Fields (6 Input Fields + Submit)**:
  1. `Customer Full Name` (`#cust_name`): Text input
  2. `National Identity Number` (`#national_id`): Text input format `ID-XXXXXX`
  3. `Date of Birth` (`#dob`): Date format `YYYY-MM-DD`
  4. `Account Type` (`#account_type`): Select dropdown (`Checking`, `Savings`, `Corporate Treasury`)
  5. `Initial Deposit Amount` (`#initial_deposit`): Number input
  6. `Statutory Attestation` (`#attestation`): Checkbox toggle
  7. `Submit Onboarding` (`#btn_submit`): Primary submission button
- **Verification Logic**:
  Upon clicking Submit, client-side JavaScript validates all fields. If valid, an animated green confirmation panel renders displaying:
  `"Submission Succeeded: All 6 Fields Verified"` along with the JSON serialization of submitted data.

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

---

## 12. Requirements Traceability Matrix & Compliance Baseline

| Requirement ID | Description | Features Covered | Blueprints | User Story Epics | Verification Test Target |
|:---|:---|:---|:---|:---|:---|
| **R1. Specification** | Feature list and user stories for business, banking, telecom, engine rules, and visual designer interactions. | F01, F02, F03, F04 | BK-01..03, TC-01..03, GB-01..03 | US-VFD-01..04, US-AWE-01..04, US-TRANS-01 | `tests/test_specification.py` validates presence of all 23 features, 15 edge cases, 9 use cases, 8 epics, and 90Studio attribution. |
| **R2. Visual Form Designer** | Canvas for drawing boxes, sequence badges, input text, and auto-compilation to workflow. | F13, F14, F15, F18 | BK-01, TC-01, GB-01 | US-VFD-01..04, US-TRANS-01 | `tests/test_compiler.py` validates 5-pass compilation algorithm, geometry normalization, and schema output. |
| **R3. Action Flow Creation & Execution** | Step-by-step flow builder and execution engine across open browser pages and desktop apps. | F05, F06, F07, F08, F09, F10, F11, F12, F19, F20 | BK-02, TC-02, GB-02 | US-AWE-01..04, US-EXEC-01..02, US-FOC-01..02, US-ERR-01..02 | `tests/test_win32_driver.py` & `tests/test_engine.py` validate SendInput structs, FSM transitions, and safety aborts. |
| **R4. Enterprise UI & Branding** | Professional Windows UI stack branded as kutomoto with copyrights reserved to 90Studio. | F16, F17, F21, F22, F23 | BK-03, TC-03, GB-03 | US-UI-01..02, US-TST-01..02 | `tests/test_e2e_automation.py` executes end-to-end form filling and submission verification on web and desktop. |

---

```
====================================================================================================
                            END OF MASTER SPECIFICATION DOCUMENT
               kutomoto Forms Filling Automation System for Windows OS
                        Copyrights reserved to 90Studio
====================================================================================================
```
