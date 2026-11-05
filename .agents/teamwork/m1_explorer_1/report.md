# Enterprise Specification Exploration & Blueprint Report

**System Name**: kutomoto — Professional Forms Filling Automation System for Windows OS  
**Copyright**: Copyrights reserved to 90Studio  
**Author**: m1_explorer_1 (Specification Miner)  
**Date**: 2026-11-04  
**Target Output**: Blueprint and Authoring Guidelines for `docs/SPECIFICATION.md` (Milestone M1)  
**Status**: Ready for Document Authoring  

---

## 1. Executive Summary & Purpose

The purpose of this exploration is to formulate the complete, production-grade specification blueprint for **kutomoto**, an enterprise-grade automated forms filling and repetitive action system engineered specifically for Microsoft Windows OS (Windows 10/11 64-bit).

kutomoto addresses a critical productivity bottleneck in regulated enterprise environments: the tedious, error-prone manual re-keying of operational data into legacy Windows desktop software and web browser portals. The system solves this through two complementary, unified paradigms:
1. **Visual Form Designer (VFD)**: A graphical, coordinate-aware design canvas enabling non-programmers to visually draw bounding boxes over application screenshot underlays or form canvases, assign field types, sequence indices, and values, and automatically compile them into deterministic action workflows.
2. **Step-by-Step Action Workflow Engine (AWE)**: A granular, sequential execution engine that deterministically simulates human and burst input events (focus activation, coordinate clicking, Unicode text injection, Tab/Enter navigation chords, configurable delays, and form submissions) across open web browser pages and native Windows desktop applications.

This report establishes the authoritative content, tabular inventories, and Gherkin acceptance criteria to be compiled into `docs/SPECIFICATION.md` by the Milestone 1 authoring worker.

---

## 2. Mandatory 90Studio Branding & System Identity

In accordance with strict corporate directives from 90Studio, all documentation, source code artifacts, user interfaces, logs, and compiled deliverables must adhere to the following branding standards:

| Branding Element | Specification & Exact Text | Placement / Verification |
|------------------|----------------------------|--------------------------|
| **Product Name** | `kutomoto` (lowercase preferred in prose/code; stylized title casing allowed in UI headers) | Window Title bar, README, Package name (`kutomoto`), CLI banner |
| **Copyright Notice** | `Copyrights reserved to 90Studio` | Main window status bar footer, About dialogue, CLI `--version`, File headers, Audit logs |
| **Corporate Entity** | `90Studio` | All architectural diagrams, license metadata, JSON schema `$id` URLs |
| **UI Aesthetic** | Enterprise Slate / Deep Navy / High-Contrast Crisp Theme | Single-Page Application Shell (Edge App Mode), modern typography, clean borders |
| **Audit Watermark** | `"copyright": "Copyrights reserved to 90Studio"` | Injected into every serialized JSON workflow and JSON execution log file |

---

## 3. Authoritative 23 Feature Catalog (F01 – F23)

The following table provides the exhaustive, authoritative catalog of all 23 system features defined across `ORIGINAL_REQUEST.md` (R1–R4, AC) and `PROJECT.md`. Every feature is enumerated with its inputs, outputs, error handling behaviors, target milestone, and verification source.

| # | ID | Category | Feature Name | Description | Inputs | Outputs | Error Handling / Behavior | Milestone | Source |
|---|----|----------|--------------|-------------|--------|---------|---------------------------|-----------|--------|
| 1 | **F01** | Specification | Specification Document | Comprehensive enterprise specification covering architecture, 23 features, 15 edge cases, 9 use cases, 8 epics, and JSON schemas. | System requirements from ORIGINAL_REQUEST.md & survey findings | `docs/SPECIFICATION.md` (authoritative markdown document) | Validated by automated regex and structural pytest suite (`test_specification.py`) | M1 | R1 / survey |
| 2 | **F02** | Enterprise Blueprint | Banking Domain Specs | Formal operational workflows, field catalogs, and validation criteria for Commercial Loan Origination, Retail KYC Account Opening, and SWIFT MT103 Wire Transfer. | Banking industry data schemas, transaction structures | Detailed use case specifications and reference fill flows | Flags missing required regulatory fields; validates IBAN/BIC formats | M1 | R1 / survey |
| 3 | **F03** | Enterprise Blueprint | Telecom Domain Specs | Operational specifications for Prepaid/Postpaid SIM Registration, Fiber Broadband Subscriber Provisioning, and Corporate Fleet Plan Migration. | BSS/CRM form layouts, ICCID/MSISDN formatting rules | Telecom automation use cases and workflow definitions | Detects invalid 19-digit ICCID check digits; handles multi-tab provisioning | M1 | R1 / survey |
| 4 | **F04** | Enterprise Blueprint | Business Domain Specs | Operational workflows for Accounts Payable Invoice Processing, Vendor Master Data Onboarding, and Travel & Expense Reimbursement. | ERP invoice fields, W-9/tax structures, expense line items | Business automation specifications and workflow definitions | Enforces debit/credit balancing, invoice duplicate detection logic | M1 | R1 / survey |
| 5 | **F05** | Win32 Core | Win32 DPI Input Core | Pure Python ctypes driver configuring Per-Monitor V2 DPI awareness context and wrapping Windows `SendInput` for mouse moves, clicks, and coordinates. | Screen/Client coordinates (X, Y), mouse button (left, right, middle), click count | Synthesized Win32 `INPUT` events injected into OS hardware message queue | Clamps coordinates to virtual desktop bounds; fails safely if cursor locked | M2 | R3 / survey |
| 6 | **F06** | Win32 Core | Unicode & Key Typing | Text typing engine utilizing `SendInput` with `KEYEVENTF_UNICODE` for full international character set typing without layout corruption, plus virtual key codes (Tab, Enter, Backspace). | String payload, virtual key codes (VK_TAB, VK_RETURN, VK_BACK), per-key delay (ms) | Dispatched sequence of `KEYBDINPUT` down/up events | Handles UTF-16 surrogate pairs; gracefully recovers if buffer overflows | M2 | R3 / survey |
| 7 | **F07** | Win32 Core | Focus Activation Core | Multi-stage window focus activation combining `AttachThreadInput`, `ShowWindow(SW_RESTORE)`, and `SetForegroundWindow` to overcome Windows focus-stealing locks. | Target Window Handle (`HWND`) or window title | Window restored, unminimized, and brought to foreground with active input focus | Retries 3 times with 150ms backoff; raises `WindowFocusFailureException` on failure | M2 | R3 / survey |
| 8 | **F08** | Win32 Core | Window Enumeration | Discovery module using `EnumWindows`, `GetWindowTextW`, and `GetWindowThreadProcessId` to match open desktop windows and browser tabs by regex or title substring. | Title regex pattern, process name substring, case-sensitivity flag | List of matching window records (`hwnd`, `title`, `rect`, `pid`) | Returns empty list if no match found; suppresses phantom/zero-size tooltips | M2 | R3 / survey |
| 9 | **F09** | Workflow Engine | 10 Atomic Actions | Standardized handlers for the 10 atomic actions: `focus_window`, `click`, `type_text`, `key_press`, `hotkey`, `clear_field`, `delay`, `submit`, `scroll`, and `prompt_user_input`. | Action type enum, action parameter dictionary | Executed physical action, telemetry status event, duration timestamp | Validates parameters against action schema; raises `ActionExecutionError` on failure | M2 | R3 / survey |
| 10 | **F10** | Workflow Engine | Execution Engine FSM | Asynchronous non-blocking finite state machine managing 7 lifecycle states: `IDLE`, `ARMED_COUNTDOWN`, `RUNNING`, `PAUSED`, `ABORTED`, `FAILED`, `COMPLETED`. | State transition triggers (start, pause, resume, abort, complete, fail) | State transition events streamed over WebSocket to UI | Blocks invalid state transitions (e.g. `COMPLETED` -> `RUNNING`); logs state changes | M2 | R3 / survey |
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

## 4. Discovered Operational Edge Cases (E01 – E15)

In automated forms filling on Windows OS, environmental variables, display scaling, application responsiveness, and security boundaries introduce failure modes that must be strictly addressed. The following table catalogs the 15 authoritative edge cases, their triggers, and the system's required behavior.

| # | Edge Case ID | Trigger Condition / Environmental Input | Observed / Required System Behavior | Architectural Defense Mechanism |
|---|--------------|-----------------------------------------|--------------------------------------|----------------------------------|
| 1 | **E01** | **Target Window Minimized or Occluded**: Target application is minimized to taskbar or occluded by modal dialog. | Engine detects window state via `IsIconic()`; invokes `ShowWindow(hwnd, SW_RESTORE)` followed by `BringWindowToTop(hwnd)` and `SetForegroundWindow(hwnd)`. Retries 3 times with 150ms pauses before raising `WindowFocusFailureException`. | Multi-tier Win32 window restoration pipeline with exponential backoff. |
| 2 | **E02** | **Dynamic or Mutating Window Titles**: Window titles change dynamically during operation (e.g. `Google Chrome - [New Tab]` -> `Google Chrome - [KYC Portal]`). | Engine compiles title search string as Python regex (`re.compile(pattern, re.IGNORECASE)`). If regex matches multiple windows, engine filters by process name or selects the most recently active top-level window. | Flexible regex matching and secondary process executable filtering. |
| 3 | **E03** | **Multi-Monitor Display Scaling Mismatch**: Form designer runs on 100% DPI monitor, but target app resides on 150% scaling display. | Engine initializes process as Per-Monitor V2 DPI Aware (`SetProcessDpiAwarenessContext(-4)`). Normalized coordinates ($0.0 \le x, y \le 1.0$) are multiplied by the target window's actual physical client dimensions (`GetClientRect`). | Dual-coordinate normalization and native OS DPI awareness context. |
| 4 | **E04** | **Stale or Default Pre-Filled Values**: Input field contains existing default text (e.g. `"0.00"`, `"Enter Name"`), resulting in concatenated corrupt strings. | When `clear_first` is enabled (default for text boxes), engine emits `Ctrl+A` chord followed by `Backspace` (or multiple `Delete` key events) before dispatching the typed payload. | Pre-typing text selection and clearing chord (`Ctrl+A` -> `VK_BACK`). |
| 5 | **E05** | **Rapid Typing Keystroke Loss**: Target application runs over high-latency Remote Desktop/Citrix or has heavy JavaScript input masks, dropping fast keystrokes. | Engine supports configurable `keystroke_delay_ms` (default 25ms, configurable up to 200ms). For ultra-long text blocks, engine supports optional high-speed clipboard paste (`Ctrl+V` via `OpenClipboard`). | Configurable inter-key delay and clipboard injection fallback. |
| 6 | **E06** | **Unicode & International Characters**: Payloads contain accented characters (e.g., `é`, `ü`), Arabic/Cyrillic scripts, or currency symbols (`€`, `£`, `¥`). | Keystroke simulation utilizes `SendInput` with `KEYEVENTF_UNICODE` (`wScan` contains UTF-16 code unit, `wVk = 0`). This bypasses the active Windows keyboard layout and dead-key states. | Hardware-level Unicode scan code injection via `KEYEVENTF_UNICODE`. |
| 7 | **E07** | **Modal Confirmation Prompts**: Target form displays a modal dialogue upon submission (e.g. `"Confirm Wire Transfer? [Yes/No]"`). | Visual compiler and workflow engine support chained multi-step confirmation sequences: configurable post-submit settling delay followed by a secondary `key_press` (`Enter` or `Y`) or modal coordinate click. | Chained post-submit confirmation action steps and settling pauses. |
| 8 | **E08** | **Accidental Operator Mouse Movement**: Operator bumps physical mouse during active execution, potentially shifting focus. | Engine tracks cursor position. If mouse moves more than 100 physical pixels while engine is in `RUNNING` state, the engine triggers the Loss-of-Focus Guardian, pauses execution, and prompts the operator. | Threshold-based mouse disturbance detection and automatic pausing. |
| 9 | **E09** | **Asynchronous / Lagging DOM Elements**: Slow AJAX network response delays the rendering of subsequent form fields. | Workflow engine supports configurable `inter_step_delay_ms` and per-step explicit `delay` actions. Workflows can configure polling retries before declaring a field unreachable. | Adaptive inter-step delay rules and configurable action timeouts. |
| 10 | **E10** | **Virtual Coordinate Space Across Multi-Monitors**: Target window is positioned on a secondary display with negative coordinate space (left or above primary display). | System computes screen coordinates using virtual desktop metrics (`SM_XVIRTUALSCREEN`, `SM_YVIRTUALSCREEN`). `ClientToScreen` Win32 API correctly resolves negative virtual coordinates. | Full virtual desktop coordinate calculation supporting negative offsets. |
| 11 | **E11** | **Degenerate Sub-Threshold Visual Boxes**: User clicks canvas without dragging, creating accidental 0-width or 1-pixel boxes. | Visual designer canvas enforces a minimum bounding box threshold: boxes smaller than 10x10 pixels are automatically rejected and discarded with a subtle UI toast notice. | Geometry threshold validator on canvas pointer release (`mouseup`). |
| 12 | **E12** | **Duplicate or Non-Contiguous Sequence Indices**: User manually edits sequence indices causing duplicates (e.g. two boxes labeled `#2`). | Designer applies automatic sequence normalization: sorts all boxes by requested index (secondary sort by Y then X coordinates) and re-assigns clean, contiguous integer ranks `[1, 2, 3, ...]`. | Automatic sequence gap repair and duplicate disambiguation algorithm. |
| 13 | **E13** | **Active Browser Tab Switching**: Operator switches active browser tab during automated execution. | Loss-of-Focus Guardian polls `GetForegroundWindow()` immediately before every atomic action. If the active window handle deviates from the target `hwnd`, execution instantly transitions to `PAUSED`. | Active foreground window verification hook before every atomic action. |
| 14 | **E14** | **Empty or Blank String Payloads**: Workflow step contains an empty text value `""` (e.g. optional middle name or note field). | Engine detects empty string: executes field focus (click or Tab navigation) to ensure cursor position advances properly, but skips character typing loop. | Navigation-preserving empty payload bypass logic. |
| 15 | **E15** | **UAC Administrator Elevation Mismatch (UIPI)**: Target application is running as Administrator (`High Integrity`), while kutomoto runs as standard user (`Medium Integrity`). | Windows User Interface Privilege Isolation blocks synthetic inputs. kutomoto checks process token elevation; if mismatch is detected upon failure, logs an explicit diagnostic: `"Target runs elevated. Relaunch kutomoto as Administrator"`. | Process integrity level diagnostic check and actionable user remediation guidance. |

---

## 5. Enterprise Domain Blueprints & Use Cases

The specification must thoroughly detail 9 operational enterprise use cases across Banking, Telecommunications, and Business Operations. Each use case defines the operational problem, field inventory, automation sequence, and business outcomes.

```
+-----------------------------------------------------------------------------------------+
|                                9 ENTERPRISE USE CASES                                   |
+---------------------------+-----------------------------+-------------------------------+
|      BANKING SECTOR       |    TELECOMMUNICATIONS       |       GENERAL BUSINESS        |
+---------------------------+-----------------------------+-------------------------------+
| BK-01: Commercial Loan    | TC-01: SIM Card KYC         | GB-01: AP Vendor Invoice      |
| Underwriting (Desktop)    | Registration (Web)          | Processing (SAP GUI / ERP)    |
|                           |                             |                               |
| BK-02: Retail KYC Account | TC-02: Fiber Provisioning   | GB-02: Vendor Master Data     |
| Opening (Web SPA)         | & ONT Activation (Hybrid)   | Onboarding (Web Portal)       |
|                           |                             |                               |
| BK-03: SWIFT MT103 Wire   | TC-03: Corporate Fleet Plan | GB-03: Employee Travel &      |
| Transfer (Terminal)       | Migration & Swap (Batch)    | Expense Reimbursement (HR)    |
+---------------------------+-----------------------------+-------------------------------+
```

### 5.1 Banking & Financial Services Blueprints

#### 5.1.1 Use Case BK-01: Commercial Loan Application & Credit Underwriting
- **Sector**: Corporate & Commercial Banking
- **Target Application**: Native Windows Desktop Underwriting Client (WinForms / .NET core banking terminal)
- **Target Window Title Pattern**: `.*Commercial Underwriting Client - 90Studio Bank.*`
- **Business Problem**: Commercial credit analysts must ingest complex loan origination data from underwriting dossiers into core banking software. Manual data entry takes 25 minutes per application, with high error rates on tax IDs, revenue figures, and collateral appraisals.
- **Detailed Field Catalog (12 Fields)**:
  1. `borrower_legal_name` (Text, Center X: 320, Y: 180): Full corporate entity name
  2. `tax_id_ein` (Text, Center X: 320, Y: 220): Federal Employer Identification Number (XX-XXXXXXX)
  3. `business_address` (Text, Center X: 320, Y: 260): Registered corporate headquarters address
  4. `annual_gross_revenue` (Currency, Center X: 320, Y: 300): Audited annual revenue in USD
  5. `facility_amount` (Currency, Center X: 320, Y: 340): Requested credit facility amount ($50,000 – $10,000,000)
  6. `loan_term_months` (Number, Center X: 320, Y: 380): Loan duration in months (12 to 120)
  7. `collateral_description` (Text, Center X: 320, Y: 420): Description of pledged collateral assets
  8. `collateral_valuation` (Currency, Center X: 320, Y: 460): Certified appraised asset valuation ($)
  9. `loan_officer_id` (Text, Center X: 320, Y: 500): Officer registration ID (`LO-90S-4412`)
  10. `risk_category` (Dropdown, Center X: 320, Y: 540): Underwriting risk tier (`Tier-1 Low Risk`)
  11. `compliance_attestation` (Checkbox, Center X: 180, Y: 580): AML/BSA statutory declaration
  12. `submit_underwriting` (Button, Center X: 320, Y: 630): Final submission button
- **Workflow Execution Sequence**:
  - `focus_window` -> target underwriting application
  - Countdown HUD 3 seconds
  - `click` box 1 -> `clear_field` -> `type_text` -> `key_press: Tab`
  - Sequential population through fields 2–10 with 30ms keystroke pacing and 80ms settling delay
  - `key_press: Space` on box 11 to toggle compliance checkbox
  - `click` box 12 (`submit_underwriting`)
- **Expected Outcome**: Processing time reduced from 25 minutes to 7.8 seconds; 100% data entry accuracy; complete compliance audit trail.

#### 5.1.2 Use Case BK-02: Retail KYC (Know Your Customer) Account Opening
- **Sector**: Retail Banking & Wealth Management
- **Target Application**: Open Web Browser Page (Google Chrome / Microsoft Edge running customer onboarding portal)
- **Target Window Title Pattern**: `.*Retail Account Opening - Core Banking.*`
- **Business Problem**: Branch officers onboard retail banking customers into an internal Angular/React single-page application. Rigid client-side validation triggers errors if fields lose focus prematurely or receive inputs out of order.
- **Detailed Field Catalog (9 Fields)**:
  1. `customer_full_name` (Text, Client X: 380, Y: 210): Legal individual customer name
  2. `date_of_birth` (Date, Client X: 380, Y: 260): Format `DD/MM/YYYY`
  3. `national_id_ssn` (Text, Client X: 380, Y: 310): Government identification number
  4. `residential_address` (Text, Client X: 380, Y: 360): Physical street address
  5. `postal_code` (Text, Client X: 380, Y: 410): Postal ZIP code
  6. `mobile_number` (Phone, Client X: 380, Y: 460): E.164 formatted telephone number
  7. `email_address` (Email, Client X: 380, Y: 510): Customer contact email
  8. `initial_deposit_amount` (Currency, Client X: 380, Y: 560): Opening balance amount
  9. `account_type_checking` (Radio/Click, Client X: 380, Y: 610): Selected account product tier
- **Workflow Execution Sequence**:
  - `focus_window` -> browser tab
  - `click` on field 1 to anchor DOM focus
  - Sequence through fields using `type_text` and `key_press: Tab`
  - Final `key_press: Enter` on submit trigger
- **Expected Outcome**: Eliminates customer wait times at branches; ensures error-free account origination.

#### 5.1.3 Use Case BK-03: High-Value Cross-Border Wire Transfer (SWIFT MT103 / ISO 20022)
- **Sector**: Treasury & Institutional Banking Operations
- **Target Application**: Windows Desktop SWIFT Terminal Emulator (Win32 / Java terminal)
- **Target Window Title Pattern**: `.*SWIFT Alliance Access - MT103 Entry.*`
- **Business Problem**: High-value corporate payments require re-keying 15 precision fields. A single typo in an IBAN or SWIFT BIC code routes millions of dollars to invalid accounts or triggers international sanction rejection penalties.
- **Detailed Field Catalog (15 Fields)**:
  - Sender Account Number, Ordering Customer Name, Beneficiary Name, Beneficiary IBAN/Account, SWIFT BIC Code (8/11 chars), Intermediary Bank Routing Code, Currency Code (USD/EUR/GBP), Transfer Amount, Value Date (`YYYYMMDD`), Remittance Information (Field 70), Charge Code (`OUR`/`BEN`/`SHA`), Compliance Screening Flag, Dual-Auth PIN, Review Comments, Dispatch Wire Button.
- **Special Operational Requirements**:
  - Enforce `keystroke_delay_ms: 50` to prevent buffer overflow on legacy terminal message loops.
  - Implement two-stage submission verification: primary submit click followed by a modal confirmation dialog handler.

---

### 5.2 Telecommunications Blueprints

#### 5.2.1 Use Case TC-01: Prepaid & Postpaid SIM Card Registration & KYC
- **Sector**: Mobile Network Operator (MNO) Dealer & Retail Operations
- **Target Application**: Open Web Browser Page (Edge/Chrome BSS/CRM Portal)
- **Target Window Title Pattern**: `.*MNO Telecom BSS - Subscriber Registration.*`
- **Business Problem**: Retail agents register hundreds of SIM cards daily under strict national telecommunications authority regulations. Hand-typing 19-digit ICCID SIM card numbers produces an 8.2% error rate, resulting in dealer penalties and delayed subscriber activation.
- **Detailed Field Catalog (8 Fields)**:
  1. `subscriber_full_name` (Text): Customer legal identity
  2. `national_id_passport` (Text): National ID / Passport number
  3. `id_expiry_date` (Date): Identity document expiration date
  4. `sim_iccid_number` (Text): 19-digit SIM card identifier (`8901410321111851072`)
  5. `msisdn_phone_number` (Phone): Assigned 10-digit mobile phone number
  6. `plan_package_code` (Dropdown/Text): Tariff plan code (`PRE-UNL-5G`)
  7. `alternate_contact` (Phone): Secondary emergency contact
  8. `activate_provision_btn` (Button): Submit and network provisioning trigger
- **Workflow Execution Sequence**:
  - Target browser activation -> anchor click on field 1 -> sequential typing and Tab traversal -> activation button click -> capture provisioning confirmation ID.
- **Expected Outcome**: Cycle time reduced from 4 minutes to under 12 seconds per subscriber; 0% ICCID transcription errors.

#### 5.2.2 Use Case TC-02: Fiber Broadband Subscriber Provisioning & ONT Activation
- **Sector**: Fixed-Line Broadband & Network Operations Center (NOC)
- **Target Application**: Hybrid: Native Desktop OLT Element Manager (Win32) + Web Provisioning Dashboard
- **Target Window Title Pattern**: `.*FTTH Network Element Manager - GPON.*`
- **Business Problem**: Provisioning Gigabit fiber requires entering optical parameters (OLT Frame/Slot/Port, ONT Serial Number, VLAN ID, PPPoE credentials, QoS profile) into an on-premises desktop client and copying the generated circuit ID to an intranet web ticket portal.
- **Detailed Field Catalog (10 Fields)**:
  - OLT Frame-Slot-Port, ONT Serial (`ALCLB0921A`), Subscriber Circuit ID, VLAN ID (`102`), PPPoE Username, PPPoE Password (`is_secret: true`), Downstream Profile (`1000M`), Upstream Profile (`500M`), Static IPv4 (`/29`), Commit Provisioning Button.
- **Workflow Execution Sequence**:
  - Win32 desktop target activation -> parameter input -> commit button -> wait 1000ms -> clipboard copy of circuit ID -> focus web browser ticket -> paste circuit ID -> submit ticket.

#### 5.2.3 Use Case TC-03: Corporate Fleet Account Plan Migration & SIM Swap
- **Sector**: B2B Enterprise Telecom Services
- **Target Application**: Web Enterprise Account Portal
- **Target Window Title Pattern**: `.*Corporate Fleet Manager - Telecom Enterprise.*`
- **Business Problem**: Account managers frequently migrate hundreds of corporate lines during annual contract renewals. The portal requires tedious repetitive form entries for each line item.
- **Detailed Field Catalog (8 Fields)**:
  - Corporate Account Number, Line MSISDN, Current Plan Code, New Plan Code, Effective Migration Date, Roaming Add-on Checkbox, Authorization Officer ID, Submit Migration Button.
- **Workflow Execution Sequence**:
  - Iterative execution loop processing corporate fleet spreadsheets, automating form filling per line with modal confirmation handling.

---

### 5.3 General Business Operations Blueprints

#### 5.3.1 Use Case GB-01: Accounts Payable Vendor Invoice Processing
- **Sector**: Corporate Accounting & Finance Shared Services
- **Target Application**: Native Windows Desktop ERP (SAP GUI / Microsoft Dynamics NAV Win32 Client)
- **Target Window Title Pattern**: `.*SAP GUI - Enter Incoming Invoice.*`
- **Business Problem**: AP clerks transcribe paper/PDF supplier invoices into enterprise ERP systems. High invoice volumes during month-end close cause cognitive fatigue and typing errors in invoice amounts, tax breakdowns, and cost center codes.
- **Detailed Field Catalog (10 Fields)**:
  1. `vendor_number` (Text): ERP supplier master ID (`VEND-90S-1048`)
  2. `invoice_number` (Text): Supplier's printed invoice reference (`INV-2026-8841`)
  3. `invoice_date` (Date): Invoice issuance date (`YYYYMMDD`)
  4. `posting_date` (Date): General Ledger posting date
  5. `gross_amount` (Currency): Total payable amount
  6. `tax_code_amount` (Currency): Calculated VAT/Sales tax amount
  7. `currency_code` (Text): ISO currency code (`USD`)
  8. `payment_terms` (Text): Agreed settlement term (`Net 30`)
  9. `purchase_order_ref` (Text): Matching PO number (`PO-44021`)
  10. `cost_center_code` (Text): Departmental cost center (`CC-FIN-770`)
- **Workflow Execution Sequence**:
  - Focus SAP GUI client -> clear pre-existing fields -> sequential typing and tab traversal -> hotkey `Ctrl+S` (Save/Post) -> capture SAP document number from status bar.
- **Expected Outcome**: Processing speed increased by 400%; invoice transcription errors eliminated.

#### 5.3.2 Use Case GB-02: New Vendor Master Data Onboarding
- **Sector**: Corporate Procurement & Supply Chain
- **Target Application**: Web Procurement System (Coupa/SAP Ariba Web Portal)
- **Target Window Title Pattern**: `.*Procurement Portal - New Supplier Registration.*`
- **Business Problem**: Onboarding new global suppliers requires inputting 12 multi-field regulatory, banking, and tax data points across multi-step wizard web pages.
- **Detailed Field Catalog (12 Fields)**:
  - Legal Entity Name, DBA Trading Name, Tax ID / W-9 / VAT Number, Country of Incorporation, Registered Street Address, City, Postal Code, Bank Name, SWIFT/Routing Code, Bank Account Number, Accounts Receivable Contact Email, Payment Method (ACH/Wire).

#### 5.3.3 Use Case GB-03: Employee Travel & Expense Reimbursement Entry
- **Sector**: Human Resources & Corporate Payroll
- **Target Application**: Native Windows Desktop HR / Payroll Client
- **Target Window Title Pattern**: `.*Enterprise Expense Manager - Claim Entry.*`
- **Business Problem**: Re-keying recurring monthly travel expenses, lodging, per diems, and client entertainment line items into legacy desktop payroll systems.
- **Detailed Field Catalog (8 Fields)**:
  - Employee Badge ID, Expense Incurred Date, Expense Category (Travel/Meals/Lodging), Vendor/Merchant Name, Total Amount Incurred, Tax Element, Project Billing Code, Justification / Business Purpose.

---

## 6. Comprehensive User Story Epics & Gherkin Acceptance Criteria

The system specification is governed by 8 user story epics covering every functional and operational aspect of kutomoto. Each epic includes detailed Gherkin acceptance criteria (Given-When-Then).

```
+-----------------------------------------------------------------------------------------+
|                                  8 USER STORY EPICS                                     |
+------------------------------------+----------------------------------------------------+
| Epic 1: Visual Form Designer (VFD) | Epic 5: Focus Management & Fail-Safe Controls      |
| Epic 2: Step-by-Step Flow Creation | Epic 6: Error Handling & Submission Verification   |
| Epic 3: Visual-to-Workflow Compile | Epic 7: Enterprise UI & 90Studio Attribution       |
| Epic 4: Target Execution (Web/Desk)| Epic 8: Verification & Sample Test Scenarios       |
+------------------------------------+----------------------------------------------------+
```

### 6.1 Epic 1: Visual Form Designer (VFD)

#### User Story US-VFD-01: Interactive Canvas Bounding Box Creation
- **Role**: Business Operations Analyst
- **Goal**: Visually draw rectangular bounding boxes on a 2D canvas representing form inputs.
- **Benefit**: Rapidly map complex form layouts without writing coordinate scripts.
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

### 6.2 Epic 2: Step-by-Step Action Workflow Creation (AWE)

#### User Story US-AWE-01: Manual Step Construction in Action Grid
- **Role**: Automation Engineer
- **Goal**: Manually construct and edit an action workflow using a structured step-by-step editor.
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
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Reordering steps in the flow editor
    Given a workflow containing steps [Step 1: focus_window, Step 2: click, Step 3: type_text]
    When I select Step 3 and click "Move Up"
    Then the step order updates to [Step 1: focus_window, Step 2: type_text, Step 3: click]
    And all step indices are re-numbered sequentially
  ```

---

### 6.3 Epic 3: Visual-to-Workflow Translation Semantics

#### User Story US-TRANS-01: Auto-Compiling Visual Boxes into Action Workflow
- **Role**: Non-Technical Business User
- **Goal**: Click "Compile Workflow" from a visual form layout to generate an executable action flow.
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
      | 1    | click       | Center of Box 1 (X=200, Y=118)                 |
      | 2    | hotkey      | Ctrl+A (Clear pre-existing text)               |
      | 3    | key_press   | Backspace                                      |
      | 4    | type_text   | Text="admin_corp", Delay=25ms                  |
      | 5    | key_press   | Tab                                            |
      | 6    | delay       | 80ms                                           |
      | 7    | hotkey      | Ctrl+A                                         |
      | 8    | key_press   | Backspace                                      |
      | 9    | type_text   | Text="P@ssword123!", Delay=25ms                |
      | 10   | key_press   | Tab                                            |
      | 11   | delay       | 80ms                                           |
      | 12   | click       | Center of Box 3 (X=160, Y=230) (Submit trigger)|
    And the generated workflow passes all schema validations
  ```

---

### 6.4 Epic 4: Workflow Execution & Targeting (Desktop & Web)

#### User Story US-EXEC-01: Executing Automation against Open Web Browser Pages
- **Role**: Operations Specialist
- **Goal**: Execute an automated fill flow against an open web browser tab (Edge, Chrome, Firefox).
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

### 6.5 Epic 5: Focus Management, Countdown & Hotkey Interruption

#### User Story US-FOC-01: Pre-Execution Arming Countdown & Window Focus
- **Role**: Enterprise Operator
- **Goal**: Experience a visual 3-second countdown before execution begins, ensuring target readiness.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: 3-second countdown and automatic window activation
    Given I click "Execute Workflow" in the kutomoto interface
    Then the engine enters "ARMED_COUNTDOWN" state
    And a countdown HUD displays "3... 2... 1..." with a visual progress indicator
    And the target window is activated and brought to the foreground via Win32 SetForegroundWindow
    When the countdown timer reaches 0
    Then the engine transitions to "RUNNING" state and dispatches Step 1 immediately
  ```

#### User Story US-FOC-02: Global Emergency Abort Hotkey (Escape / F10)
- **Role**: Compliance & Safety Officer
- **Goal**: Instantly halt automation at any millisecond by pressing the `Escape` key.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Instant abort of running workflow via Escape key
    Given a workflow is currently in "RUNNING" state at Step 5 of 12
    When the operator presses the "Escape" key
    Then all input simulation ceases immediately within 50 milliseconds
    And no subsequent steps are dispatched
    And the engine state transitions to "ABORTED"
    And an emergency abort audit record is written to the execution log
  ```

---

### 6.6 Epic 6: Error Handling, Timeouts & Submission Verification

#### User Story US-ERR-01: Target Window Resolution Failure Handling
- **Role**: System Operator
- **Goal**: Receive an immediate, clear error message when the target application window cannot be found.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Handling missing target window
    Given a workflow configured for target title "Core Banking - Finacle"
    And no open desktop window matches "Core Banking - Finacle"
    When I attempt to execute the workflow
    Then the engine aborts before dispatching any inputs
    And transitions to "FAILED" state
    And displays: "Target Window Not Found: Unable to locate window matching 'Core Banking - Finacle'. Please open the target application."
  ```

#### User Story US-ERR-02: Immutable Audit Logging & Submission Verification
- **Role**: Compliance Auditor
- **Goal**: Review a complete, tamper-evident audit log of every executed action step.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Capturing structured audit log with 90Studio attribution
    Given a workflow completes execution
    Then the audit log file contains:
      - Workflow ID, Name, and Execution UUID
      - Start timestamp, end timestamp, and total duration in milliseconds
      - Array of all executed steps with individual latency and status
      - Legal watermark: "Copyrights reserved to 90Studio"
      - Final outcome status: "COMPLETED"
    And sensitive password fields are masked as "********"
  ```

---

### 6.7 Epic 7: Enterprise UI & 90Studio Branding

#### User Story US-UI-01: Professional Desktop Presentation
- **Role**: Corporate User
- **Goal**: Interact with a polished, high-contrast desktop user interface suitable for financial institutions.
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
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Verifying mandatory 90Studio branding across application views
    Given the kutomoto application is active
    Then the window title bar contains "kutomoto"
    And the status bar footer permanently displays "Copyrights reserved to 90Studio"
    And the About modal dialog displays "kutomoto" and "Copyrights reserved to 90Studio"
  ```

---

### 6.8 Epic 8: Verification & Sample Test Scenarios

#### User Story US-TST-01: End-to-End Automated Banking KYC Web Form Verification
- **Role**: Quality Assurance Engineer
- **Goal**: Validate end-to-end automated filling and submission of the provided Banking KYC Web Form.
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

## 7. Concrete Outline and Content Blueprint for `docs/SPECIFICATION.md`

The M1 Authoring Worker must structure `docs/SPECIFICATION.md` into 10 cohesive sections following this authoritative blueprint:

```
docs/SPECIFICATION.md
├── 1. Executive Summary, System Purpose & 90Studio Branding
├── 2. System Architecture & Native Hybrid Operating Model
├── 3. Complete 23 Feature Catalog (F01 – F23)
├── 4. Operational Edge Cases & Failure Recovery (E01 – E15)
├── 5. Enterprise Domain Blueprints (Banking, Telecom, Business - 9 Use Cases)
├── 6. User Story Epics & Gherkin Acceptance Criteria (8 Epics, US-VFD to US-TST)
├── 7. Workflow Engine Rules, Finite State Machine & JSON Schemas
├── 8. Win32 Automation Core, DPI Subsystem & Cross-App Targeting
├── 9. Verification Targets & Test Scenarios Specification
└── 10. Requirements Traceability Matrix & Compliance Baseline
```

### 7.1 Section-by-Section Authoring Instructions

1. **Title & Preamble**:
   - Title: `# kutomoto — Enterprise Specification & System Architecture`
   - Metadata block: System Name, Version (1.0.0), Document Reference (`KTM-SPEC-2026-M1`), Author (`90Studio Architectural Council`), Copyright Notice (`Copyrights reserved to 90Studio`).
2. **Section 1: Executive Summary & Branding**:
   - Vision statement, operational paradigms (Visual Designer vs Step Flow), target regulated industries.
   - Exact branding rules table (Section 2 of this report).
3. **Section 2: System Architecture**:
   - ASCII architecture diagram from `PROJECT.md`.
   - Technology stack rationale: Python 3.14 + FastAPI backend, pure ctypes Win32 automation core, HTML5 Canvas SPA frontend launched in Microsoft Edge App Mode (`msedge.exe --app=...`).
4. **Section 3: Feature Catalog (F01 – F23)**:
   - Full 23-feature table with columns: `#`, `ID`, `Category`, `Name`, `Description`, `Inputs`, `Outputs`, `Error Behavior`, `Milestone`, `Source`.
   - Embed complete descriptions and inputs/outputs verbatim as specified in Section 3 of this report.
5. **Section 4: Edge Cases (E01 – E15)**:
   - Full 15-edge-case table with columns: `#`, `ID`, `Condition / Trigger`, `Observed / Required Behavior`, `Architectural Defense`.
   - Provide concrete technical explanations for DPI normalization, UIPI elevation, modal dialogs, and focus loss.
6. **Section 5: Enterprise Domain Blueprints**:
   - Detail the 9 use cases (BK-01..03, TC-01..03, GB-01..03) with field inventories, target application types, sequence diagrams, and business outcomes.
7. **Section 6: User Story Epics & Acceptance Criteria**:
   - Group the 8 epics with all Given-When-Then Gherkin scenarios defined in Section 6 of this report.
8. **Section 7: Workflow Engine Rules & Schemas**:
   - Synthesize contributions from `m1_explorer_3`:
     - Embed full `VisualFormLayout` and `ActionWorkflow` JSON schemas (Draft 2020-12).
     - 10 atomic actions catalog.
     - 5-pass compilation algorithm pipeline.
     - 7-state FSM ASCII state transition diagram.
     - 90Studio audit log schema.
9. **Section 8: Win32 Automation Core & Cross-App Targeting**:
   - Synthesize contributions from `m1_explorer_2`:
     - Per-Monitor V2 DPI Awareness (`SetProcessDpiAwarenessContext(-4)`).
     - 64-bit 40-byte `INPUT` ctypes struct definitions.
     - `KEYEVENTF_UNICODE` typing mechanics and virtual key codes.
     - Window enumeration, regex matching, and thread attachment (`AttachThreadInput` + `SetForegroundWindow`).
     - Web browser targeting vs desktop application targeting.
     - Safety guardrails (Escape abort, corner slam, Loss-of-Focus Guardian).
10. **Section 9: Verification Targets**:
    - Complete specifications for `samples/web/index.html` (Banking KYC Web Form) and `samples/desktop/sample_desktop_form.py` (Telecom SIM Provisioning Desktop Form).
11. **Section 10: Traceability Matrix**:
    - Comprehensive mapping from R1–R4 and Acceptance Criteria items to the 23 features, use cases, and verification methods.

---

## 8. Concrete Guidance for the M1 Authoring Worker

To ensure that `docs/SPECIFICATION.md` achieves maximum completeness, clarity, and maintainability:

1. **Unify Explorer Findings Seamlessly**:
   - Incorporate the complete functional domain specifications from this report (`m1_explorer_1`).
   - Incorporate the Win32 ctypes structures and OS targeting rules from `m1_explorer_2`.
   - Incorporate the JSON schemas, 5-pass compilation algorithm, and 7-state FSM from `m1_explorer_3`.
2. **Ensure Absolute Completeness**:
   - Do NOT omit any of the 23 features or 15 edge cases.
   - Do NOT use shorthand like "etc." or "remaining fields omitted for brevity". Every single field of all 9 enterprise use cases must be explicitly named and typed.
3. **Rigorous Compliance with Automated Tests**:
   - In Milestone M5, `tests/test_specification.py` will parse `docs/SPECIFICATION.md` to programmatically assert the presence of all feature IDs (`F01` through `F23`), all edge case IDs (`E01` through `E15`), all 9 use cases (`BK-01`..`03`, `TC-01`..`03`, `GB-01`..`03`), all 8 epics (`Epic 1` through `Epic 8`), and the branding phrase `"Copyrights reserved to 90Studio"`.
   - Following this blueprint guarantees 100% test pass rate on specification verification.
4. **Single Source of Truth**:
   - Once authored, `docs/SPECIFICATION.md` will serve as the immutable blueprint for Milestones M2 (Win32 Core & Engine), M3 (Compiler & Box Model), M4 (FastAPI Server & Canvas UI), and M5 (Sample Targets & Test Suite).

---
*Report formulated and delivered by m1_explorer_1.*  
*Copyrights reserved to 90Studio.*
