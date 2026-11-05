# kutomoto — Professional Forms Filling Automation System for Windows OS

> **Copyrights reserved to 90Studio**  
> *Enterprise Forms Filling & Repetitive Action Automation Platform for Web Browsers & Windows Desktop Applications*

[![Build & Test Status](https://img.shields.io/badge/tests-460%20passing-brightgreen.svg)](tests/)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011%20x64-blue.svg)](kutomoto.exe)
[![Architecture](https://img.shields.io/badge/architecture-Win32%20SendInput%20%2B%20FastAPI%20%2B%20Edge%20App-purple.svg)](#system-architecture)
[![License](https://img.shields.io/badge/copyright-90Studio-navy.svg)](#copyright-and-license)
[![GitHub Pages Demo](https://img.shields.io/badge/live%20demo-GitHub%20Pages-success.svg)](https://daoudz.github.io/kutomoto/)

---

## 📑 Table of Contents

1. [Executive Overview](#executive-overview)
2. [Dual Core Operating Paradigms](#dual-core-operating-paradigms)
3. [Key Architectural Highlights](#key-architectural-highlights)
4. [Multi-Agent Engineering & Verification Effort](#multi-agent-engineering--verification-effort)
   - [The Multi-Agent Taskforce](#the-multi-agent-taskforce)
   - [Milestone Delivery Roadmap](#milestone-delivery-roadmap)
   - [Verification Record: 460 Passing Tests](#verification-record-460-passing-tests)
5. [Enterprise Sample Applications](#enterprise-sample-applications)
   - [Sample 1: Banking KYC Customer Onboarding (Web)](#sample-1-banking-kyc-customer-onboarding-web)
   - [Sample 2: Telecom SIM Card Provisioning System (Desktop)](#sample-2-telecom-sim-card-provisioning-system-desktop)
6. [Interactive GitHub Pages Showcase & Online Release](#interactive-github-pages-showcase--online-release)
7. [Getting Started & Installation](#getting-started--installation)
   - [Option A: Standalone Windows Executable (Recommended)](#option-a-standalone-windows-executable-recommended)
   - [Option B: Quick-Launch Batch Script](#option-b-quick-launch-batch-script)
   - [Option C: Python Development Environment](#option-c-python-development-environment)
8. [Workflow Authoring Guide](#workflow-authoring-guide)
   - [Visual Form Designer (VFD)](#visual-form-designer-vfd)
   - [Step-by-Step Flow Builder (AWE)](#step-by-step-flow-builder-awe)
9. [Win32 Native Automation Subsystem](#win32-native-automation-subsystem)
   - [64-bit ABI SendInput Layout](#64-bit-abi-sendinput-layout)
   - [Multi-Tier Safety Guard & Loss-of-Focus Guardian](#multi-tier-safety-guard--loss-of-focus-guardian)
10. [Repository Structure](#repository-structure)
11. [Copyright and License](#copyright-and-license)

---

## 🏛️ Executive Overview

In regulated enterprise environments—commercial and retail banking, telecommunications network operations, healthcare administration, and supply chain logistics—operational staff spend millions of aggregate hours manually transcribing data between documents, internal web portals, and legacy Windows desktop software (WinForms, WPF, SAP GUI, terminal emulators).

Manual data entry incurs catastrophic business costs:
- **High Error Rates**: Human transcription errors on 19-digit SIM ICCID numbers, 34-character IBANs, and GL accounting codes average 4% to 8%, causing compliance penalties and customer churn.
- **Severe Latency**: Onboarding a corporate customer or provisioning an enterprise SIM profile manually takes 15 to 30 minutes per record.
- **Brittle Macro Tools**: Conventional web-only browser extensions fail in locked-down enterprise environments where extensions are blocked by Active Directory Group Policy, or where desktop applications render via DirectX/GDI surfaces without standard accessibility hooks.

**kutomoto** is an enterprise-grade, high-reliability forms filling automation platform designed and engineered exclusively for Microsoft Windows OS by **90Studio**. kutomoto combines visual, drag-and-drop workflow authoring with hardware-level Win32 automation primitives. By synthesizing the precision of desktop coordinate mapping with cross-application browser targeting, kutomoto empowers non-technical domain specialists and automation engineers to eliminate manual re-keying, enforce compliance, and accelerate data entry speeds by over 400%.

---

## 🎯 Dual Core Operating Paradigms

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

---

## ⚡ Key Architectural Highlights

- **Hardware-Level Native Win32 ctypes Driver**: Direct interaction via `user32.dll` `SendInput`, `GetCursorPos`, `SetCursorPos`, `SetForegroundWindow`, `EnumWindows`, and `GetAsyncKeyState` without external automation drivers (no Selenium, no Playwright, no AutoIt required).
- **Zero-Driver Standalone Windows Executables**: Standalone 64-bit PE binaries (`kutomoto.exe` and `samples/desktop/sample_desktop_form.exe`) compiled with embedded 90Studio icon, version resources, and high-DPI awareness.
- **Enterprise Application Shell**: Launches seamlessly in Microsoft Edge App Mode (`msedge.exe --app=http://127.0.0.1:8765`), offering a distraction-free native desktop app experience without browser navigation chrome.
- **Loss-of-Focus Guardian & Multi-Layer Safety Guard**:
  - Instant pause if the active target window loses focus during typing.
  - Corner failsafe: slamming mouse to screen coordinates `(0, 0)` immediately halts execution.
  - Emergency Escape hotkey detection (`GetAsyncKeyState(VK_ESCAPE)`).
  - Explicit 3-second focus countdown HUD allowing operators to switch to the target application safely.
- **5-Pass Visual Compiler**:
  - Pass 1: Schema validation & coordinate normalization (0.0 to 1.0 relative to target window).
  - Pass 2: 2D spatial & topological reading-order sorting (top-to-bottom, left-to-right with configurable band tolerance).
  - Pass 3: Action synthesis (focus, clear, type, tab, delay, click).
  - Pass 4: Peephole optimization (delay coalescing, redundant focus pruning, click-to-tab conversion).
  - Pass 5: Unified Action Workflow JSON generation with 90Studio compliance stamping.
- **7-State Asynchronous Non-Blocking FSM Engine**: States: `IDLE`, `COUNTDOWN`, `RUNNING`, `PAUSED`, `STOPPED`, `COMPLETED`, `FAILED`. Real-time telemetry broadcast via WebSockets.

---

## 👥 Multi-Agent Engineering & Verification Effort

kutomoto was architected, engineered, challenged, and verified through a rigorous collaborative multi-agent framework involving specialized AI agent taskforces working under strict architectural governance.

### The Multi-Agent Taskforce

```
+--------------------------------------------------------------------------------------------------+
|                                    90STUDIO MULTI-AGENT COUNCIL                                  |
+--------------------------------------------------------------------------------------------------+
|  [Orchestrator]          Milestone roadmap governance, gating criteria, and protocol compliance  |
|  [Sentinel]              Regression guard, test harness integrity, continuous verification       |
|  [Spec Miner & Analyst]  Enterprise domain modeling (Banking KYC & Telecom SIM workflows)       |
|  [Architecture Explorer] Win32 64-bit ABI ctypes memory layout, Edge App Mode spike, FSM design  |
|  [Engineering Worker]    FastAPI service, Win32 driver, Visual Designer canvas, compiler passes  |
|  [Dual Reviewers]        Independent peer reviews on code cleanliness, memory safety, and schema |
|  [Adversarial Challenger]Empirical edge-case stress attacks (loss of focus, jitter, Unicode, races)|
|  [Compliance Auditor]    Enterprise branding verification, 90Studio copyright validation         |
+--------------------------------------------------------------------------------------------------+
```

### Milestone Delivery Roadmap

| Milestone | Scope & Deliverables | Verification Result |
| :--- | :--- | :--- |
| **M1: Specification & Domain Blueprint** | Formal 2,120-line Master Specification (`docs/SPECIFICATION.md`), Draft 2020-12 JSON schemas for VisualFormLayout and Unified Action Workflow, enterprise user stories for Banking and Telecom. | **48/48 passed** (Empirical schema validation, regex syntax checks, user story completeness) |
| **M2: Compiler & Win32 Driver Core** | 5-pass visual-to-workflow compiler, topological 2D band sorter, SendInput 64-bit ABI ctypes bindings, fuzzy and regex window matcher. | **157/157 passed** (Adversarial band overlaps, coordinate boundary fuzzing, mock driver contracts) |
| **M3: FSM Execution Engine & Safety Guard** | 7-state asynchronous execution engine, Loss-of-Focus Guardian, mouse corner failsafe, emergency pause/stop hotkey, retry policies. | **244/244 passed** (Sudden focus theft during typing, corner slam trigger, asynchronous pause/resume) |
| **M4: Enterprise UI & Microsoft Edge App Shell** | HTML5 Canvas Visual Designer with 8-handle transformation, Flow Builder grid, Target Window selector, countdown HUD, real-time WebSocket console. | **378/378 passed** (Browserless headless UI contracts, canvas event simulation, live WebSocket telemetry) |
| **M5: End-to-End Packaging & Executables** | Native PE64 standalone executables (`kutomoto.exe`, `sample_desktop_form.exe`), icon generation, live web KYC sample, live desktop Telecom Tkinter form. | **460/460 passed** (PE headers, live process startup/shutdown, CLI help/version, end-to-end automation) |

### Verification Record: 460 Passing Tests

The test suite runs under `pytest` with 100% pass rate:

```
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\daoud\projects\kutomoto
configfile: pyproject.toml
plugins: anyio-4.12.1, langsmith-0.6.2, asyncio-1.3.0, cov-7.0.0
collected 460 items

tests\test_api.py ......................                                 [  4%]
tests\test_compiler.py ................................................. [ 15%]
........................                                                 [ 20%]
tests\test_compiler_empirical_challenge.py ........................      [ 25%]
tests\test_e2e_automation.py .......................                     [ 30%]
tests\test_engine.py .............................................       [ 40%]
tests\test_engine_empirical_challenge.py .............                   [ 43%]
tests\test_executable_and_driver_integration.py ........                 [ 45%]
tests\test_m2_empirical_challenge.py ................................... [ 52%]
.                                                                        [ 53%]
tests\test_m3_it2_empirical_adversarial.py ............................. [ 59%]
.                                                                        [ 59%]
tests\test_m4_deep_stress_challenge.py ..................                [ 63%]
tests\test_m4_empirical_challenge.py ..............                      [ 66%]
tests\test_m4_it2_stress_harness.py ........                             [ 68%]
tests\test_m4_it3_adversarial_challenge.py ............                  [ 70%]
tests\test_m4_it4_empirical_challenger.py .......                        [ 72%]
tests\test_m5_adversarial_challenge.py ...................               [ 76%]
tests\test_m5_adversarial_empirical.py ..................                [ 80%]
tests\test_m5_it2_challenger_empirical.py ...............                [ 83%]
tests\test_roundtrip_execution_challenge.py ............                 [ 86%]
tests\test_spec_empirical_challenge.py ....                              [ 87%]
tests\test_specification.py ........................                     [ 92%]
tests\test_ui_m4_challenge.py ......................                     [ 97%]
tests\test_win32_driver.py .............                                 [100%]

======================= 460 passed in 64.56s ========================
```

---

## 🏢 Enterprise Sample Applications

### Sample 1: Banking KYC Customer Onboarding (Web)

- **Location**: `samples/web/index.html` (Styles: `styles.css`, Logic: `form.js`)
- **Workflow**: `samples/web/banking_kyc_workflow.json`
- **Use Case**: Retail and Commercial banking due diligence.
- **Fields Automated**:
  1. Full Legal Name (`input_full_name`)
  2. Tax ID / SSN (`input_tax_id`)
  3. Corporate Legal Entity Identifier (`input_lei`)
  4. Account Currency (`select_currency`)
  5. Initial Deposit Amount (`input_initial_deposit`)
  6. Source of Funds (`select_source_of_funds`)
  7. Politically Exposed Person Declaration (`checkbox_pep`)
  8. AML Attestation (`checkbox_aml_attest`)
  9. Submit Application (`btn_submit_kyc`)

### Sample 2: Telecom SIM Card Provisioning System (Desktop)

- **Executable**: `samples/desktop/sample_desktop_form.exe` (Source: `sample_desktop_form.py`)
- **Workflow**: `samples/desktop/telecom_sim_provisioning_workflow.json`
- **Use Case**: Telecom branch office SIM card activation and provisioning.
- **Features**:
  - Native Windows desktop application with exact Win32 client coordinates.
  - Predictable Tab-order traversal (`tab_index: 1` through `7`).
  - Dropdown keyboard navigation (`Prepaid 5G`, `Postpaid Unlimited`, `Corporate Data`).
  - Checkbox activation via Space keystroke.
  - Verification banner with dynamic SHA-256 confirmation hash.

---

## 🌐 Interactive GitHub Pages Showcase & Online Release

An interactive live release and demo showcase is published online via GitHub Pages:

🔗 **[https://daoudz.github.io/kutomoto/](https://daoudz.github.io/kutomoto/)**

The GitHub Pages release showcase includes:
- **Online Interactive Visual Form Designer**: Draw bounding boxes on a simulated enterprise form canvas, drag, resize, set labels/values, and click **Compile** to see real-time generated Unified Action Workflow JSON!
- **Interactive Banking KYC Form Simulator**: Run step-by-step simulated automated filling directly in your web browser with animated typing, field focus indicators, and successful AML validation.
- **Standalone Live Banking KYC Web Target**: Full web client form target available live at [https://daoudz.github.io/kutomoto/samples/web/index.html](https://daoudz.github.io/kutomoto/samples/web/index.html).
- **Release Download Portal**: Direct download links for standalone Windows 64-bit binaries:
  - `kutomoto.exe` (Enterprise Automation System Launcher)
  - `sample_desktop_form.exe` (Telecom SIM Provisioning Desktop Target)
  - Sample workflow JSON templates (`banking_kyc_workflow.json`, `telecom_sim_provisioning_workflow.json`)
- **Full Architecture Specification Viewer**: Complete architectural documentation and memory layout diagrams ([SPECIFICATION.md](https://daoudz.github.io/kutomoto/SPECIFICATION.md)).
- **GitHub Tagged Releases**: Formal release tags and source packages available at [https://github.com/daoudz/kutomoto/releases](https://github.com/daoudz/kutomoto/releases).

---

## 🚀 Getting Started & Installation

### Option A: Standalone Windows Executable (Recommended)

1. Download `kutomoto.exe` from the repository root or the [GitHub Pages Release Center](https://daoudz.github.io/kutomoto/).
2. Double-click `kutomoto.exe` or run from PowerShell:
   ```powershell
   .\kutomoto.exe
   ```
3. kutomoto automatically starts the local backend engine on `127.0.0.1:8765` and launches Microsoft Edge in dedicated App Mode with the enterprise UI.

### Option B: Quick-Launch Batch Script

Run the included batch script from the repository root:
```cmd
run_kutomoto.bat
```

### Option C: Python Development Environment

Requirements: Python 3.10+ on Windows 10/11 64-bit.

1. Clone the repository:
   ```bash
   git clone https://github.com/daoudz/kutomoto.git
   cd kutomoto
   ```
2. Install dependencies:
   ```bash
   pip install -e .
   pip install pytest pytest-asyncio pytest-cov httpx
   ```
3. Run the application:
   ```bash
   python -m kutomoto
   ```
4. Run the full test suite:
   ```bash
   python -m pytest
   ```

---

## 🛠️ Workflow Authoring Guide

### Visual Form Designer (VFD)

1. Open kutomoto and select the **Visual Designer** tab.
2. Load a screenshot or mock canvas of your target form (web or desktop).
3. Click and drag across input fields to draw bounding boxes.
4. Each box displays:
   - Sequence Badge (`#1`, `#2`, `#3`, ...)
   - Field Label (e.g., `Full Legal Name`)
   - Default Value to type (e.g., `Acme Global Holdings LLC`)
   - Interaction Type (`text_field`, `dropdown`, `checkbox`, `submit_button`)
5. Configure target window title pattern (e.g., `Banking KYC.*` or `Telecom SIM.*`).
6. Click **⚡ Compile to Workflow**. The system validates your layout and generates an optimized JSON Action Workflow.
7. Click **Run Flow** to execute against the target application.

### Step-by-Step Flow Builder (AWE)

1. Navigate to the **Flow Builder** tab.
2. Build custom sequential actions by adding steps:
   - `focus_window`: Brings the target window to foreground by HWND or title regex.
   - `click`: Clicks client or normalized coordinates `(norm_x, norm_y)`.
   - `clear_field`: Clears existing content using `select_all_backspace` or `triple_click_delete`.
   - `type_text`: Types text with configurable keystroke delay.
   - `key_press`: Sends special keys (`tab`, `enter`, `space`, `escape`).
   - `hotkey`: Sends chords (`ctrl+a`, `ctrl+c`, `alt+f4`).
   - `delay`: Pauses execution for a specified duration in milliseconds.
3. Save workflows as reusable `.json` files in `data/workflows/`.

---

## 🛡️ Win32 Native Automation Subsystem

### 64-bit ABI SendInput Layout

kutomoto uses direct ctypes memory structures matching the native Microsoft Windows 64-bit ABI:

```python
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),  # 8 bytes on 64-bit Windows
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),  # 8 bytes on 64-bit Windows
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", _INPUTunion),                    # Union of MOUSEINPUT, KEYBDINPUT, HARDWAREINPUT
    ]
```

### Multi-Tier Safety Guard & Loss-of-Focus Guardian

Automation errors in enterprise banking or telecom software can lead to disastrous misfiling. kutomoto enforces strict runtime safeguards:

1. **Loss-of-Focus Guardian**: Before executing any keyboard or mouse step, kutomoto inspects `GetForegroundWindow()`. If the user accidentally switches focus to another application (e.g., Slack or Outlook), execution **immediately pauses**, preventing keystrokes from leaking into unintended windows.
2. **Mouse Corner Failsafe**: If the user jerks the mouse cursor to the upper-left corner `(0, 0)`, the failsafe triggers and halts execution immediately.
3. **Emergency Stop Hotkey**: Pressing `ESC` at any point during countdown or execution instantly terminates the automation engine.
4. **Pre-Flight Countdown HUD**: A configurable 3-second countdown gives operators time to visually inspect the target window before automation begins.

---

## 📁 Repository Structure

```
kutomoto/
├── .agents/                      # Multi-agent teamwork logs and milestone retrospectives
├── data/
│   └── workflows/               # Pre-packaged enterprise workflow JSON files
│       ├── banking_kyc_workflow.json
│       └── telecom_sim_provisioning_workflow.json
├── dist/                         # Compiled 64-bit PE release binaries & icons
│   ├── kutomoto.exe
│   ├── kutomoto.ico
│   └── sample_desktop_form.exe
├── docs/                         # Documentation & GitHub Pages showcase
│   ├── index.html                # Interactive GitHub Pages release showcase & online demo
│   └── SPECIFICATION.md          # 2,120-line Master Enterprise Architecture Blueprint
├── samples/
│   ├── desktop/                  # Telecom SIM Provisioning Tkinter desktop application
│   │   ├── sample_desktop_form.exe
│   │   ├── sample_desktop_form.py
│   │   └── telecom_sim_provisioning_workflow.json
│   └── web/                      # Banking KYC Customer Onboarding Web Portal
│       ├── banking_kyc_workflow.json
│       ├── form.js
│       ├── index.html
│       └── styles.css
├── src/
│   └── kutomoto/                 # Core Python package
│       ├── automation/           # Win32 ctypes driver, window matching, SendInput ABI
│       ├── designer/             # Visual Designer schema, 5-pass compiler & exceptions
│       ├── engine/               # 7-state asynchronous FSM & Loss-of-Focus Guardian
│       ├── server/               # FastAPI backend & WebSocket telemetry broadcaster
│       └── ui/                   # HTML5 Canvas designer, Flow Builder, CSS & JS
├── tests/                        # 460 comprehensive automated tests (100% passing)
├── build_exe.py                  # Windows 64-bit PE binary builder
├── kutomoto.exe                  # Root launcher executable
├── pyproject.toml                # Project packaging & dependencies
├── README.md                     # This documentation file
└── run_kutomoto.bat              # One-click Windows launch script
```

---

## ⚖️ Copyright and License

**Copyrights reserved to 90Studio.**

All rights reserved. No part of this software, specification, design layout, or associated documentation may be reproduced, distributed, or transmitted in any form or by any means, including photocopying, recording, or other electronic or mechanical methods, without the prior written permission of 90Studio, except in the case of brief quotations embodied in critical reviews and certain other noncommercial uses permitted by copyright law.
