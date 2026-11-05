# kutomoto — Specification Survey & Requirements Definition Report
**Enterprise Forms Filling Automation System for Windows OS**  
**Document Reference**: SPEC-MINER-SURVEY-01  
**Author**: spec_miner_survey_1  
**Date**: 2026-11-04  
**Copyright**: Copyrights reserved to 90Studio  
**Status**: Authoritative Architectural Baseline  

---

## 1. Executive Summary & Product Scope

### 1.1 Product Purpose & Vision
**kutomoto** is an enterprise-grade automated forms filling and repetitive action automation system engineered specifically for the Microsoft Windows desktop environment. The system bridges the gap between manual data entry operators and complex, rigid backend integrations by providing non-programmers and operations specialists with two synchronized workflow paradigms:
1. **A Visual Form Designer (VFD)**: A graphical, coordinate-aware canvas allowing users to visually draw bounding boxes over form representations or screenshot mockups, configure execution sequences, assign values and field metadata, and auto-compile these visual layouts into deterministic action workflows.
2. **A Step-by-Step Action Workflow Engine (AWE)**: An imperative, highly configurable action sequencer allowing users to construct, fine-tune, record, and execute granular atomic steps (e.g., target window activation, coordinate clicks, text typing with human-like or burst cadences, Tab/Enter keystrokes, navigation chords, and inter-step delays).

kutomoto operates seamlessly across both **open web browser pages** (Google Chrome, Microsoft Edge, Mozilla Firefox, Opera) and **native Windows desktop applications** (Win32, WinForms, WPF, Qt, Java Swing, SAP GUI, Electron, terminal emulators). It eliminates human error, reduces repetitive strain, accelerates high-volume data entry, and guarantees strict compliance in mission-critical corporate environments.

### 1.2 Enterprise Target Sectors
kutomoto is tailored for operational deployment in three primary regulated industries:
- **Banking & Financial Services**: KYC/AML account opening, commercial loan processing, SWIFT MT103 wire transfer dispatch, credit card origination, regulatory reporting.
- **Telecommunications**: Prepaid/postpaid subscriber registration, SIM card swap & provisioning, fiber/broadband circuit activation, corporate fleet mobile bundle configuration.
- **General Business Operations**: Accounts payable invoice transcription (ERP/SAP/NetSuite), vendor master data onboarding, employee travel & expense itemization, purchase order creation.

### 1.3 Legal & Branding Attribution
Per mandatory design directives:
- **Application Name**: `kutomoto`
- **Branding Statement**: `Copyrights reserved to 90Studio`
- **UI Guidelines**: Enterprise-grade Windows aesthetic (subtle borders, high contrast, clean typography, unambiguous status badges, professional dark/light palette, ergonomic toolbars).

---

## 2. Features Discovered & Functional Catalog

The following table comprehensively catalogs all discovered functional and non-functional features extracted from `ORIGINAL_REQUEST.md`, architectural enterprise requirements, and Windows automation semantics.

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| F01 | Visual Form Designer | Coordinate Canvas & Bounding Box Drawing | Interactive 2D canvas allowing click-and-drag drawing of rectangular bounding boxes representing form input controls. | Mouse drag coordinates (X1, Y1, X2, Y2), canvas zoom/pan state | Rendered bounding box entity, persistent normalized geometry (X, Y, W, H) | Snaps to grid if enabled; discards boxes smaller than minimum threshold (5x5 px) | R2, Visual Form Designer |
| F02 | Visual Form Designer | Visual Box Sequencing & Reordering | Automatic assignment of execution order (1, 2, 3...) upon creation, with manual drag-and-drop reordering, numeric re-indexing, and visual step badges. | Target box identifier, new sequential rank (index integer) | Recalculated sequence list, updated visual indicator badges on canvas | Rejects duplicate indices; automatically shifts conflicting items | R2, Visual Form Designer |
| F03 | Visual Form Designer | Field Property Inspector | Modal/panel inspector to assign field metadata: label name, field type (text, number, date, dropdown, checkbox, submit button), default/static text value, tab navigation rule, and click offset. | Field entity ID, property key-value pairs (type, default value, action) | Updated Box Schema attributes, dynamic preview label on canvas | Validates input format (e.g., numeric checks for number fields, regex for dates) | R2, Visual Form Designer |
| F04 | Visual Form Designer | Canvas Template Image Underlay | Capability to load an image screenshot of an application window or web form into the canvas background to allow pixel-perfect box alignment. | Image file path (.png, .jpg, .bmp) or clipboard bitmap | Scaled canvas background underlay matching original application dimensions | Displays warning on unreadable image formats; preserves aspect ratio | R2, Visual Form Designer |
| F05 | Visual Form Designer | Automated Workflow Translation | Translation engine that maps the visual bounding box collection into a deterministic sequence of executable actions (`focus_window`, `click`, `type_text`, `key_press`, `delay`). | Visual Box Schema JSON collection, ordering mode (Manual Rank, Top-to-Bottom, Left-to-Right) | Executable Action Workflow JSON matching engine specifications | Flags orphan boxes (missing values/targets); generates validation warning list | R2, Workflow Generation |
| F06 | Action Workflow Builder | Granular Step-by-Step Flow Editor | Structured table/list editor allowing manual creation, insertion, editing, and deletion of atomic action steps without using the visual canvas. | Action type, target coordinates/keys, delay duration, description | Action Workflow List model updated in-memory | Rejects unknown action types; enforces required parameters per action | R3, Action Workflow Creation |
| F07 | Action Workflow Builder | Action Step: Text Input (`type_text`) | Simulates keyboard character input into the currently focused target input control, with configurable typing delay between keystrokes. | String payload, character delay (ms), clear-field-before-typing flag | Synthetic keyboard events sent via Windows OS input subsystem | Handles Unicode characters; escapes special control keys safely | R3, Action Workflow Creation |
| F08 | Action Workflow Builder | Action Step: Navigation & Special Keys (`key_press`) | Simulates single or combined virtual key presses (Tab, Enter, Escape, Backspace, Arrow keys, Shift+Tab, Ctrl+A). | Virtual Key code (VK), key modifier masks (Shift, Ctrl, Alt) | Synthetic KeyDown/KeyUp events dispatched to OS message queue | Validates virtual key code; logs unmapped key codes | R3, Action Workflow Creation |
| F09 | Action Workflow Builder | Action Step: Mouse Click (`click`) | Dispatches left, right, or double mouse clicks at precise absolute screen coordinates or client-relative window coordinates. | Coordinate pair (X, Y), mouse button (Left, Right, Middle), click count (1 or 2) | Cursor repositioning and mouse button Down/Up events at target coordinate | Clamps coordinates to valid virtual screen boundaries; alerts if out of bounds | R3, Action Workflow Creation |
| F10 | Action Workflow Builder | Action Step: Configurable Delay (`delay`) | Suspends workflow execution for a designated duration to allow target application UI rendering, network AJAX calls, or page transitions. | Duration in milliseconds (integer >= 0) | Execution thread sleep without freezing the main application UI | Enforces maximum safety limit (e.g. 60,000 ms) unless overridden | R3, Action Workflow Creation |
| F11 | Action Workflow Builder | Action Step: Target Window Focus (`focus_window`) | Identifies target application by window title (exact or regex) or process name, bringing it to foreground before dispatching inputs. | Window title substring / regex pattern, process name, timeout (ms) | Target window activated (`SetForegroundWindow`), restored if minimized | Raises `WindowNotFoundException` or `FocusTimeoutException` if window missing | R3, Target Application Focus |
| F12 | Action Workflow Builder | Action Step: Form Submission (`submit`) | Dedicated step triggering final form submission via Enter key press or mouse click on identified submit button coordinates. | Submission method (Key: Enter / Mouse: X, Y coords), post-submit wait (ms) | Dispatches submission event; transitions execution state to verification | Flags if submit button coordinate is undefined | R3, Form Submission |
| F13 | Execution Engine | Pre-Execution Countdown & Arming | Displays visual countdown timer (e.g., 3..2..1) before first action, giving operator time to inspect the screen and ready the target window. | Countdown duration in seconds (default: 3s) | Audible beep/visual cue, status change to `COUNTDOWN`, smooth transition to `RUNNING` | Can be cancelled by operator hitting Escape before countdown completes | R3, Workflow Execution |
| F14 | Execution Engine | Emergency Fail-Safe & Global Abort Hotkey | Global keyboard hook or mouse gesture allowing instant termination or suspension of automation (e.g. pressing `Escape` or `F10`). | Global key press event (Esc / F10 / F9) | Immediate halts of input generation; state transitions to `ABORTED` | Thread-safe emergency interrupt flag checked before every atomic action | R3, Error Handling |
| F15 | Execution Engine | Web Browser Automation Support | Executes coordinate clicks and sequential keystrokes against open, active web browser pages (Chrome, Edge, Firefox) without requiring browser plugins. | Browser window handle / title, viewport coordinates | Input simulated into browser window DOM controls via OS input stream | Recovers from minor browser scroll shifts if Tab navigation pattern used | R3, Web Automation |
| F16 | Execution Engine | Windows Desktop Application Automation | Executes inputs against native Windows desktop applications (Win32, WinForms, WPF, Qt, Electron, SAP GUI). | Application window handle / title, client coordinates | Native window activation and OS input injection | Detects UAC privilege barriers; warns if target runs as higher integrity level | R3, Desktop Automation |
| F17 | Execution Engine | Execution State Machine & Lifecycle | Manages deterministic states: `IDLE`, `COUNTDOWN`, `RUNNING`, `PAUSED`, `COMPLETED`, `ABORTED`, `FAILED`. | Lifecycle triggers (Start, Pause, Resume, Stop, Fail) | Observable state events dispatched to UI status bars and logging console | Illegal state transitions rejected with clear log diagnostics | R3, Engine Rules |
| F18 | Execution Engine | Real-Time Execution Log & Audit Trail | Displays live timestamped log stream showing each executed step, target coordinates, text values (with masking option), and execution latency. | Step execution telemetry events | Auto-scrolling enterprise audit log viewer with export capability (CSV/JSON) | Logs errors with stack trace and system context | R1, R4, Audit & Logging |
| F19 | Workflow Persistence | Workflow Export & Import (JSON) | Serializes visual designer canvas schemas and action workflow definitions into standardized, human-readable JSON files. | Workflow data structure / file path (`.ktm.json`) | Validated JSON file saved to disk or imported into workspace | Schema validation against JSON schema; rejects corrupted files | R1, R2, R3, Persistence |
| F20 | Enterprise UI | Enterprise-Grade Windows Interface | Professional, responsive desktop GUI adhering to 90Studio brand identity, featuring split-pane layout, dark/light themes, status bar, and toolbar. | User UI interactions | High-DPI Windows application window with clean typography and layout | Graceful layout reflow across standard 1080p, 1440p, and 4K displays | R4, UI & Branding |
| F21 | Enterprise UI | 90Studio Legal Attribution | Unambiguous visual display of application identity "kutomoto" and intellectual property statement "Copyrights reserved to 90Studio". | Application launch / window draw | Rendered title bar, status bar footer, and About dialog attribution | Immutable branding strings; enforced across all views | R4, Branding Attribution |
| F22 | Verification & Testing | Built-in Verification Web Form | Self-contained, local HTML/JS test form representing enterprise business/banking fields with client-side validation to prove end-to-end web automation. | Browser load trigger (local HTTP or file URL) | Interactive test web form with submission confirmation indicator | Logs submission payload in-browser for automated assertion | AC, Verification Scenarios |
| F23 | Verification & Testing | Built-in Verification Desktop Form | Self-contained native Windows desktop form application representing enterprise form fields with validation to prove end-to-end desktop automation. | Launch desktop target trigger | Interactive desktop window displaying filled data and submission status | Emits verifiable completion event/state upon successful submission | AC, Verification Scenarios |

---

## 3. Discovered Edge Cases & System Constraints

The following table documents critical edge cases discovered through environmental analysis, Windows input simulation constraints, and multi-application focus management.

| # | Feature | Input / Condition | Observed / Required Behavior |
|---|---------|-------------------|------------------------------|
| E01 | Target Window Focus | Target window minimized or covered by another modal window | The engine must invoke Windows `ShowWindow(SW_RESTORE)` followed by `SetForegroundWindow()`. If the window fails to obtain focus after 3 attempts, abort with `WindowFocusFailureException`. |
| E02 | Window Title Matching | Target application has dynamic window title (e.g. "Google Chrome - [New Tab]" vs "Google Chrome - [Invoice Entry]") | The engine must support both substring matching and regular expression matching (e.g. `.*Google Chrome.*` or `.*Loan Origination.*`). |
| E03 | DPI Scaling & Resolution Shifts | Designer configured at 100% DPI (1920x1080), but execution occurs at 125% or 150% Windows display scaling | Screen coordinates must either be normalized relative to the target window client area (`ClientToScreen` / `ScreenToClient`) or the workflow must leverage Tab-based key navigation rather than absolute pixel coordinates. |
| E04 | Text Typing into Pre-Filled Fields | Input field in target application already contains stale text or default placeholder | The engine must support a `clear_first` option: prior to typing text, it executes a select-all key combination (`Ctrl+A`) followed by `Backspace` or `Delete`. |
| E05 | Rapid Typing Keystroke Dropping | Target application (e.g. legacy remote terminal, SAP GUI over Citrix, or heavy web SPA) cannot process fast keystrokes | Keystroke delay must be configurable (default 20ms-50ms per key) to ensure zero character loss in legacy or high-latency input queues. |
| E06 | Non-ASCII and Unicode Text Entry | Workflow contains non-ASCII characters (e.g. accented names, Arabic, Cyrillic, Chinese, currency symbols: €, £, ¥) | Input generator must use Windows `SendInput` with `KEYEVENTF_UNICODE` flag to bypass keyboard layout / dead-key mapping issues. |
| E07 | Target Form Submission Confirmation | Target application displays modal confirmation prompt ("Are you sure you want to submit? [Yes/No]") | Workflow must support chained confirmation steps: a secondary `key_press` (e.g. `Enter` or `Y`) or secondary coordinate `click` after a defined settling delay. |
| E08 | Operator Accidental Mouse Movement | Operator moves physical mouse during automated workflow execution | Global interrupt threshold: if manual mouse move exceeds configurable delta, engine can automatically pause and alert the operator to prevent mis-clicks. |
| E09 | Missing or Disabled Input Field | Target field is temporarily disabled or not yet rendered due to slow web page load | Workflow engine enforces a configurable `step_timeout` with retry interval before declaring step failure. |
| E10 | Multi-Monitor Display Configurations | Target application is positioned on secondary display monitor with negative coordinate space | Coordinate calculation must account for virtual screen geometry (`SM_XVIRTUALSCREEN`, `SM_YVIRTUALSCREEN`, `SM_CXVIRTUALSCREEN`, `SM_CYVIRTUALSCREEN`). |
| E11 | Visual Designer Zero-Size Box | User clicks on canvas without dragging, creating a 0-width / 0-height bounding box | Canvas controller rejects boxes whose width or height is less than 10 pixels; prevents invalid zero-area click targets. |
| E12 | Duplicate Execution Indices in Designer | User manually edits box sequence numbers resulting in two boxes with order = 2 | Designer automatically re-sorts all boxes, preserving relative order and ensuring consecutive, gapless integer ranks (1, 2, 3, 4...). |
| E13 | Browser Tab Swapping During Run | User changes active tab in target browser while automation is running | Engine verifies foreground window handle before every step. If foreground window handle diverges from target handle, execution immediately pauses. |
| E14 | Empty Value in Text Step | Workflow step contains blank string value `""` | Engine treats step as navigation-only: moves focus to field, performs click or tab, but skips keystroke injection. |
| E15 | UAC / Elevated Target Window | Target application is running as Administrator while kutomoto is running as standard user | Windows UIPI (User Interface Privilege Isolation) blocks synthetic input messages. kutomoto must detect elevation mismatch and notify the user to launch with matching privileges. |

---

## 4. Enterprise Use Cases & Operational Scenarios

### 4.1 Banking & Financial Services

#### 4.1.1 Use Case BK-01: Commercial Loan Application & Credit Underwriting
- **Sector**: Corporate & Commercial Banking
- **Operational Challenge**: Commercial credit analysts must ingest business loan requests received via loan origination spreadsheets and re-key complex multi-field borrower data into the bank’s core underwriting Windows desktop client (e.g., Finacle/T24/Custom .NET Win32 client) and a parallel web-based fraud/credit bureau portal. Manual entry takes 25 minutes per application with high error rates on tax IDs, revenue figures, and collateral values.
- **kutomoto Solution**:
  1. The analyst opens the Target Desktop Loan Underwriting Client and the Target Web Compliance Portal.
  2. The analyst loads the pre-configured kutomoto workflow `Commercial_Loan_Underwriting_v2.ktm.json`.
  3. Visual Designer mapping displays the layout of the 12 primary fields:
     - Field 1: Borrower Corporate Entity Name
     - Field 2: Registration / Tax ID (EIN)
     - Field 3: Registered Business Address
     - Field 4: Annual Audited Gross Revenue
     - Field 5: Requested Credit Line Facility Amount
     - Field 6: Loan Term (Months)
     - Field 7: Primary Collateral Description
     - Field 8: Collateral Appraised Valuation ($)
     - Field 9: Loan Officer Representative ID
     - Field 10: Risk Rating Category (Dropdown)
     - Field 11: Compliance Attestation (Checkbox)
     - Field 12: Underwriting Submission (Button)
  4. The operator initiates execution. kutomoto counts down 3 seconds, activates the desktop underwriting client, injects all 12 fields sequentially with automatic Tab/coordinate transitions, clears any stale default values, verifies input integrity, clicks the Submit button, and logs an immutable audit event with timestamp and user ID.
- **Expected Outcome**: Data entry duration reduced from 25 minutes to 8 seconds; zero transcription discrepancies.

#### 4.1.2 Use Case BK-02: Retail KYC (Know Your Customer) Account Opening
- **Sector**: Retail Banking & Wealth Management
- **Operational Challenge**: Branch relationship officers onboard new individual checking/savings accounts. Customer details from identification documents must be entered into an internal browser-based Customer Onboarding Portal (Angular/React SPA) that frequently rejects submissions if focus sequences or required field validations are triggered out of order.
- **kutomoto Solution**:
  - The branch officer creates a visual form layout in kutomoto by loading a screenshot of the account opening web form into the designer canvas.
  - Rectangular boxes are drawn directly over: Customer Full Name, Date of Birth (DD/MM/YYYY), National ID Number, Residential Address, Postal Code, Mobile Number, Email Address, Initial Deposit Amount, Account Type selection.
  - The visual designer auto-generates the step-by-step action flow:
    - Step 1: `focus_window` -> "Retail Account Opening - Core Banking"
    - Step 2: `click` -> First Name Box (X: 340, Y: 220)
    - Step 3: `type_text` -> Customer Name + `key_press` -> Tab
    - Step 4: `type_text` -> DOB + `key_press` -> Tab
    - ...
    - Step 10: `key_press` -> Enter (Triggers form submission)
- **Expected Outcome**: Instantaneous branch account creation, consistent compliance adherence, and elimination of customer wait times.

#### 4.1.3 Use Case BK-03: High-Value Cross-Border Wire Transfer (SWIFT MT103 / ISO 20022)
- **Sector**: Treasury & Institutional Operations
- **Operational Challenge**: Treasury operators execute bulk corporate cross-border wire transfers. Each transaction requires entering 15 precise fields: Sender Account, Beneficiary Name, Beneficiary IBAN, SWIFT BIC Code (8 or 11 characters), Intermediary Bank Routing Code, Transfer Currency, Amount (up to 2 decimal places), Value Date, Remittance Information (Field 70), and Charge Details (OUR/BEN/SHA). A single misplaced character can route millions of dollars to incorrect accounts or cause expensive SWIFT rejection penalties.
- **kutomoto Solution**:
  - A strict workflow template enforces exact character pacing (50ms per keystroke) to avoid buffer overflow on the desktop SWIFT terminal emulator.
  - Clear-field-before-typing ensures previous transaction residue is eliminated.
  - Form submission action is configured with a two-step confirmation step to prevent accidental single-click dispatch.

---

### 4.2 Telecommunications

#### 4.2.1 Use Case TC-01: Prepaid & Postpaid SIM Card Registration & KYC
- **Sector**: Mobile Network Operator (MNO) Retail & Dealer Networks
- **Operational Challenge**: Telecom retail agents register hundreds of SIM cards daily under strict government-mandated biometric and national ID verification regulations. Agents must transcribe information into the telecom web-based BSS/CRM portal: 19-digit SIM ICCID, 10-digit MSISDN (Phone Number), Subscriber ID, ID Expiry Date, PUK Code, Plan Package Code, and Alternate Contact Number. Hand-typing 19-digit ICCID numbers leads to an 8% typo rate and dealer fines.
- **kutomoto Solution**:
  - Agent loads a predefined SIM Registration Fill Flow in kutomoto.
  - kutomoto sequences the fields in exact tab order matching the web portal.
  - Fields automatically populate the ICCID, MSISDN, and package details directly into the active browser page.
  - The workflow automatically dispatches the final "Activate & Provision" button click.
- **Expected Outcome**: SIM registration cycle time drops from 4 minutes per customer to under 15 seconds; zero ICCID transcription errors.

#### 4.2.2 Use Case TC-02: Fiber Broadband Subscriber Provisioning & ONT Activation
- **Sector**: Fixed-Line & Broadband Network Operations
- **Operational Challenge**: Network Operations Center (NOC) dispatchers configure optical line terminal (OLT) subscriber profiles and customer premises equipment (ONT) across a native legacy Windows desktop client (WinForms/C++ network element manager) and an intranet provisioning ticket dashboard.
- **kutomoto Solution**:
  - Dual-target workflow: kutomoto targets the legacy desktop client, inputs VLAN ID, PPPoE credentials, downstream/upstream bandwidth profiles (e.g. 1000Mbps/500Mbps), and static IP allocations.
  - The workflow transitions focus to the web provisioning dashboard, fills the ticket reference, and marks the task as completed.

#### 4.2.3 Use Case TC-03: Corporate Fleet Account Plan Migration & SIM Swap
- **Sector**: B2B Enterprise Telecom Accounts
- **Operational Challenge**: Enterprise account managers frequently migrate hundreds of mobile lines for corporate clients (e.g. upgrading 500 company phones from 4G corporate voice to 5G unlimited enterprise tier). The telecom self-service enterprise portal requires line-by-line form filling with multiple confirmation modals.
- **kutomoto Solution**:
  - kutomoto executes repetitive action loops: selecting the line row, navigating through Tab steps, typing plan code, pressing Enter, waiting for modal pop-up, pressing Enter to confirm, and proceeding to the next record.

---

### 4.3 General Business Operations

#### 4.3.1 Use Case GB-01: Accounts Payable Vendor Invoice Processing
- **Sector**: Corporate Accounting & Finance (Shared Services)
- **Operational Challenge**: Accounts payable clerks manually transcribe supplier PDF invoices into enterprise ERP desktop software (e.g., SAP GUI, Microsoft Dynamics NAV/365 desktop, or NetSuite web interface). Each invoice requires entering Vendor Number, Invoice Number, Invoice Date, Posting Date, Gross Amount, Tax Amount, Currency, Payment Terms, Purchase Order Reference, and Cost Center code.
- **kutomoto Solution**:
  - Operator opens the ERP invoice entry screen.
  - Using kutomoto's Visual Form Designer, the operator visually mapped the input boxes to the SAP/ERP screen layout once.
  - The operator pastes or loads the invoice values into the kutomoto flow, clicks "Execute", and kutomoto completes the entire multi-field entry in 3 seconds, pressing the posting hotkey (e.g., `Ctrl+S` or `Enter`) to submit.

#### 4.3.2 Use Case GB-02: New Vendor Master Data Onboarding
- **Sector**: Procurement & Supply Chain
- **Operational Challenge**: Onboarding new corporate suppliers into the procurement web system requires submitting 18 fields including Company Legal Name, Trade Style (DBA), Tax ID (W-9 / VAT), Bank Name, Routing/SWIFT Number, Bank Account Number, Remittance Email, Payment Terms, and NAICS Industry Code.
- **kutomoto Solution**:
  - An automated action flow executes sequential typing and tab navigation across the procurement form, ensuring strict compliance with required field formats.

#### 4.3.3 Use Case GB-03: Employee Travel & Expense Reimbursement Entry
- **Sector**: Human Resources & Operational Administration
- **Operational Challenge**: End-of-month expense reconciliation requires staff to re-key multi-receipt line items (Date, Merchant, Category, Expense Amount, Tax Breakdown, Project Code, Justification) into legacy HR software.
- **kutomoto Solution**:
  - kutomoto visual flow maps the receipt entry grid, allowing users to rapidly fire automated fill flows for recurring monthly subscriptions and expense entries.

---

## 5. Detailed User Stories & Acceptance Criteria

### 5.1 Epic 1: Visual Form Designer (VFD)

#### US-VFD-01: Visual Bounding Box Creation on Canvas
- **As a**: Business Operations Analyst
- **I want to**: Click and drag on an interactive visual canvas to draw rectangular boxes representing form inputs
- **So that**: I can easily configure form layouts without manually calculating screen coordinates.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Successfully drawing a form field box
    Given the Visual Form Designer canvas is open
    When I press the left mouse button at canvas coordinate (100, 150)
    And I drag the mouse to coordinate (350, 190)
    And I release the left mouse button
    Then a new rectangular bounding box is rendered with top-left (100, 150), width 250, and height 40
    And the box is assigned a distinct visual border and highlight
    And the box is automatically assigned the next sequential execution index (e.g. #1)
    And the Field Property Inspector displays the properties of the newly created box

  Scenario: Discarding sub-threshold accidental clicks
    Given the Visual Form Designer canvas is open
    When I click at coordinate (200, 200) without dragging (width < 10px, height < 10px)
    Then no bounding box is created
    And no error is thrown
  ```

#### US-VFD-02: Field Sequencing and Visual Reordering
- **As a**: Banking Workflow Designer
- **I want to**: Reorder the execution sequence of visual form boxes either via numeric property editing or drag-and-drop
- **So that**: The automated flow fills fields in the exact tab/logical order required by the target banking application.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Re-indexing execution order
    Given the canvas contains three boxes with indices [1: "First Name", 2: "Last Name", 3: "Account #"]
    When I select box 3 ("Account #")
    And I change its sequence index in the Property Inspector to 1
    Then the system re-indexes all boxes such that "Account #" becomes index 1
    And "First Name" shifts to index 2
    And "Last Name" shifts to index 3
    And the visual number badges on the canvas update immediately to reflect [1, 2, 3]
  ```

#### US-VFD-03: Assigning Box Properties & Default Values
- **As a**: Telecom Operations Specialist
- **I want to**: Assign a field label, field type, input text value, and post-entry key action to each visual box
- **So that**: The workflow knows what data to enter and how to navigate away from the field.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Configuring field properties
    Given a visual bounding box is selected on the canvas
    When I set Field Label to "SIM Card Number"
    And I set Field Type to "Text Input"
    And I set Text Value to "8901410321111851072"
    And I set Post-Action to "Press Tab"
    Then the box schema stores these attributes
    And the canvas box displays the label "SIM Card Number" and index badge
  ```

#### US-VFD-04: Loading Form Screenshot Background Underlay
- **As a**: Form Automation Designer
- **I want to**: Load a screenshot or image of the target web or desktop form as a canvas background
- **So that**: I can draw bounding boxes with pixel-perfect alignment over the actual target application fields.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Loading image underlay
    Given the Visual Form Designer is open
    When I click "Load Form Image" and select a valid PNG or JPG file
    Then the canvas background renders the image with 1:1 pixel fidelity
    And existing or newly drawn boxes overlay transparently on top of the image
    And the canvas provides clear/remove image controls
  ```

---

### 5.2 Epic 2: Step-by-Step Action Workflow Creation (AWE)

#### US-AWE-01: Manual Action Step Construction
- **As an**: Automation Engineer
- **I want to**: Build and edit an action flow step-by-step using a structured action grid
- **So that**: I can create complex automation workflows containing custom keystrokes, mouse clicks, delays, and window focus commands.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Adding an atomic action step
    Given the Action Workflow editor is open
    When I click "Add Step"
    And I select Action Type "Type Text"
    And I enter Payload "INV-2026-9081"
    And I set Keystroke Delay to 30 ms
    Then a new step is appended to the workflow list
    And the step table displays: [Index: N, Action: Type Text, Details: "INV-2026-9081 (delay: 30ms)"]
  ```

#### US-AWE-02: Configuring Keyboard Primitives (Tab, Enter, Chords)
- **As an**: ERP Data Entry Operator
- **I want to**: Add specific keyboard actions such as Tab, Enter, Backspace, or Ctrl+A
- **So that**: The workflow can submit forms, navigate between form controls, and select default text.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Adding a Tab navigation step
    Given I am editing an Action Workflow
    When I add a step with Action Type "Key Press" and Key "Tab"
    Then the step is configured to emit a synthetic VK_TAB down and up event during execution

  Scenario: Adding a submission Enter step
    Given I am at the final step of a form flow
    When I add a step with Action Type "Key Press" and Key "Enter"
    Then the step is configured to trigger form submission
  ```

#### US-AWE-03: Configuring Coordinate Mouse Clicks
- **As a**: System Operator
- **I want to**: Configure a mouse click action specifying X and Y screen or client coordinates
- **So that**: The engine can click buttons, checkboxes, or radio controls that cannot be reached via keyboard Tab navigation.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Adding a mouse click step
    When I add a step with Action Type "Mouse Click"
    And I specify X: 840, Y: 620, Button: "Left", Clicks: 1
    Then during execution the mouse cursor moves to (840, 620) and dispatches a left-click event
  ```

#### US-AWE-04: Step Reordering, Cloning, and Deletion
- **As a**: Workflow Author
- **I want to**: Move steps up or down, duplicate existing steps, and delete unwanted steps
- **So that**: I can rapidly iterate and maintain my action flows.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Reordering steps
    Given a workflow with steps [Step 1: Focus Window, Step 2: Click, Step 3: Type Text]
    When I select Step 3 and click "Move Up"
    Then the new order is [Step 1: Focus Window, Step 2: Type Text, Step 3: Click]
    And step numbers are sequentially updated
  ```

---

### 5.3 Epic 3: Visual-to-Workflow Translation Semantics

#### US-TRANS-01: Auto-Generating Action Workflow from Visual Layout
- **As a**: Non-Technical Business User
- **I want to**: Click "Generate Workflow" from my visual form design
- **So that**: The system automatically compiles all my drawn boxes into an executable, sequential action flow.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Compiling visual boxes into action workflow
    Given a visual form design with 3 boxes ordered [1: "Username", 2: "Password", 3: "Login Button"]
    And Box 1 has center coords (200, 100), value "admin", post-action "Tab"
    And Box 2 has center coords (200, 150), value "secret123", post-action "Tab"
    And Box 3 has center coords (200, 200), type "Submit Button", post-action "Click"
    When I trigger "Generate Workflow"
    Then the system produces an executable Action Workflow with the following generated steps:
      | Step | Action Type  | Parameters                                 |
      | 1    | Mouse Click  | Target: (200, 100), Button: Left           |
      | 2    | Type Text    | Text: "admin", Delay: 25ms                 |
      | 3    | Key Press    | Key: Tab                                   |
      | 4    | Delay        | Duration: 100ms                            |
      | 5    | Type Text    | Text: "secret123", Delay: 25ms             |
      | 6    | Key Press    | Key: Tab                                   |
      | 7    | Delay        | Duration: 100ms                            |
      | 8    | Mouse Click  | Target: (200, 200), Button: Left (Submit)  |
    And the generated workflow is immediately inspectable and executable in the Action Workflow view
  ```

---

### 5.4 Epic 4: Workflow Execution & Targeting (Desktop & Web)

#### US-EXEC-01: Executing Automation against Open Web Browser Pages
- **As an**: Operations Agent
- **I want to**: Execute an action workflow against an open web browser page (e.g. Chrome, Edge, Firefox)
- **So that**: Form fields across internal and external web portals are automatically filled and submitted.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Executing workflow against web browser form
    Given an open browser window displaying an enterprise web form
    And a verified kutomoto workflow targeted to the browser window title
    When I start workflow execution
    Then kutomoto brings the browser window to the foreground
    And kutomoto sequentially navigates and types values into each web form input
    And the browser form controls receive and reflect all typed values
    And the form submission action is executed successfully
    And execution status reports "COMPLETED"
  ```

#### US-EXEC-02: Executing Automation against Windows Desktop Applications
- **As a**: Banking Loan Processor
- **I want to**: Execute an action workflow against a native Windows desktop application (Win32, WPF, WinForms)
- **So that**: Legacy core banking desktop forms are populated automatically without human keystroke entry.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Executing workflow against desktop client
    Given a native Windows desktop application form is open
    And a verified kutomoto workflow configured for the desktop application
    When I trigger execution
    Then the desktop application window is activated and brought to foreground
    And all text fields, numeric inputs, and dropdowns are filled in exact sequence
    And the submit button or Enter key is pressed
    And the desktop application acknowledges form submission
  ```

---

### 5.5 Epic 5: Focus Management, Countdown & Hotkey Interruption

#### US-FOC-01: Pre-Execution Countdown & Target Window Focus
- **As an**: Operator
- **I want to**: See a 3-second countdown and have kutomoto automatically bring the target window into focus
- **So that**: I have sufficient time to verify the target window is ready and hands are off the keyboard.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Pre-execution countdown and activation
    Given I click "Execute Workflow"
    Then the system enters "COUNTDOWN" state
    And displays a visible 3-second countdown on the kutomoto UI
    And activates the designated target window using Windows SetForegroundWindow
    When the countdown reaches 0
    Then the state transitions to "RUNNING" and step 1 commences immediately
  ```

#### US-FOC-02: Emergency Fail-Safe Global Abort
- **As an**: Enterprise Compliance Officer
- **I want to**: Press an emergency key (e.g. `Escape` or `F10`) at any instant during execution
- **So that**: Automation halts immediately if an unexpected modal, error, or misalignment occurs.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Aborting execution via emergency hotkey
    Given a workflow is currently in "RUNNING" state at step 4 of 10
    When the user presses the emergency abort key (Escape or F10)
    Then input simulation ceases immediately within 50 milliseconds
    And no further steps are dispatched
    And the execution state transitions to "ABORTED"
    And a high-visibility warning notification is logged in the audit trail
  ```

---

### 5.6 Epic 6: Error Handling, Timeouts & Submission Verification

#### US-ERR-01: Target Window Not Found Handling
- **As an**: Operator
- **I want to**: Receive a clear, actionable error message if the target window cannot be located
- **So that**: I know why the automation could not run and how to resolve it.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Target window missing at execution time
    Given a workflow configured with target window title "Core Banking - Finacle"
    And no open window on the system matches "Core Banking - Finacle"
    When I click "Execute Workflow"
    Then execution does not send blind keystrokes
    And the system transitions to "ERROR" state
    And displays: "Target Window Not Found: Unable to locate window matching 'Core Banking - Finacle'. Please open the target application."
  ```

#### US-ERR-02: Submission Verification & Audit Logging
- **As an**: Audit Officer
- **I want to**: Record a detailed execution report confirming all steps were dispatched with timestamps and outcomes
- **So that**: The enterprise retains a full audit trail of automated actions.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Successful submission verification logging
    Given a workflow finishes all steps including form submission
    Then the system logs an audit entry with:
      - Workflow Name and ID
      - Total Steps Executed (e.g. 12/12)
      - Start and End Timestamps
      - Total Execution Duration (e.g. 3.42s)
      - Final State: "COMPLETED"
    And the operator can view or export this log
  ```

---

### 5.7 Epic 7: Enterprise UI & 90Studio Branding

#### US-UI-01: Professional Enterprise Presentation & Attribution
- **As a**: Corporate User
- **I want to**: Use a polished, modern, distraction-free desktop application with clear 90Studio branding
- **So that**: The software feels trustworthy, professional, and compliant with corporate software standards.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: Branding and attribution compliance
    Given the kutomoto application is launched
    Then the main application window title bar contains "kutomoto"
    And the footer or status bar permanently displays "Copyrights reserved to 90Studio"
    And the About / Info dialog prominently displays:
      - Application: kutomoto
      - Version and Build Info
      - Legal Notice: "Copyrights reserved to 90Studio"
    And the UI theme utilizes clean enterprise styling with clear status iconography
  ```

---

### 5.8 Epic 8: Verification & Sample Test Scenarios

#### US-TST-01: End-to-End Automated Filling of Sample Web Form
- **As a**: Quality Assurance Engineer
- **I want to**: Run kutomoto against a provided sample web form and verify 100% field population and submission
- **So that**: We guarantee functional web automation capability.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: End-to-end web form automated filling
    Given the sample web form is opened in a web browser
    And the corresponding kutomoto web workflow is loaded
    When I execute the workflow
    Then all fields (Name, Account/ID, Email, Amount, Notes, Checkbox) are correctly filled
    And the web form Submit button is triggered
    And the web page displays a green "Form Successfully Submitted!" banner with the exact submitted payload
  ```

#### US-TST-02: End-to-End Automated Filling of Sample Desktop Form
- **As a**: Quality Assurance Engineer
- **I want to**: Run kutomoto against a provided sample Windows desktop form application and verify end-to-end execution
- **So that**: We guarantee functional desktop application automation capability.
- **Acceptance Criteria (Gherkin)**:
  ```gherkin
  Scenario: End-to-end desktop form automated filling
    Given the sample Windows desktop form application is running
    And the corresponding kutomoto desktop workflow is loaded
    When I execute the workflow
    Then kutomoto focuses the desktop window
    And fills all input boxes, selects required options, and clicks the Submit button
    And the desktop application updates its status label to "Submission Received: All Fields Verified"
  ```

---

## 6. Workflow Engine Rules & Data Semantics

### 6.1 Unified Data Models & JSON Schemas

The kutomoto automation system operates on two core interoperable data models:
1. **Visual Form Layout Schema (`VisualFormLayout`)**
2. **Action Workflow Schema (`ActionWorkflow`)**

#### 6.1.1 Visual Form Layout Schema Specification
```json
{
  "$schema": "https://kutomoto.90studio.com/schemas/v1/visual-form-layout.json",
  "version": "1.0.0",
  "name": "Banking_KYC_Account_Opening",
  "description": "Visual field layout for retail customer onboarding",
  "canvas": {
    "width": 1280,
    "height": 720,
    "backgroundImage": null,
    "coordinateSpace": "client_relative"
  },
  "boxes": [
    {
      "id": "box_001",
      "index": 1,
      "label": "Full Name",
      "fieldType": "text",
      "geometry": {
        "x": 240,
        "y": 150,
        "width": 300,
        "height": 38
      },
      "clickTarget": "center",
      "value": "Sarah Jenkins",
      "postAction": "tab",
      "clearFirst": true,
      "delayAfterMs": 100
    },
    {
      "id": "box_002",
      "index": 2,
      "label": "National ID / SSN",
      "fieldType": "text",
      "geometry": {
        "x": 240,
        "y": 210,
        "width": 300,
        "height": 38
      },
      "clickTarget": "center",
      "value": "987-65-4321",
      "postAction": "tab",
      "clearFirst": true,
      "delayAfterMs": 100
    },
    {
      "id": "box_003",
      "index": 3,
      "label": "Account Opening Deposit ($)",
      "fieldType": "number",
      "geometry": {
        "x": 240,
        "y": 270,
        "width": 180,
        "height": 38
      },
      "clickTarget": "center",
      "value": "2500.00",
      "postAction": "tab",
      "clearFirst": true,
      "delayAfterMs": 100
    },
    {
      "id": "box_004",
      "index": 4,
      "label": "Submit Application",
      "fieldType": "submit_button",
      "geometry": {
        "x": 240,
        "y": 340,
        "width": 160,
        "height": 44
      },
      "clickTarget": "center",
      "value": "",
      "postAction": "click",
      "clearFirst": false,
      "delayAfterMs": 500
    }
  ]
}
```

#### 6.1.2 Executable Action Workflow Schema Specification
```json
{
  "$schema": "https://kutomoto.90studio.com/schemas/v1/action-workflow.json",
  "version": "1.0.0",
  "id": "wf_banking_kyc_01",
  "name": "Banking KYC Workflow",
  "metadata": {
    "author": "kutomoto Visual Compiler",
    "copyright": "Copyrights reserved to 90Studio",
    "targetApplication": {
      "type": "web_or_desktop",
      "windowTitlePattern": ".*KYC Account Opening.*",
      "processName": null
    },
    "globalSettings": {
      "preExecutionCountdownSeconds": 3,
      "interStepDelayMs": 80,
      "keystrokeDelayMs": 25,
      "abortHotkey": "Escape",
      "pauseHotkey": "F9"
    }
  },
  "steps": [
    {
      "stepNumber": 1,
      "description": "Focus Target Form Window",
      "action": "focus_window",
      "params": {
        "titlePattern": ".*KYC Account Opening.*",
        "timeoutMs": 5000
      }
    },
    {
      "stepNumber": 2,
      "description": "Click Full Name Input",
      "action": "click",
      "params": {
        "x": 390,
        "y": 169,
        "button": "left",
        "clickCount": 1
      }
    },
    {
      "stepNumber": 3,
      "description": "Clear Existing Text",
      "action": "key_chord",
      "params": {
        "modifier": "Ctrl",
        "key": "A"
      }
    },
    {
      "stepNumber": 4,
      "description": "Type Full Name",
      "action": "type_text",
      "params": {
        "text": "Sarah Jenkins",
        "keystrokeDelayMs": 25
      }
    },
    {
      "stepNumber": 5,
      "description": "Navigate to Next Field",
      "action": "key_press",
      "params": {
        "key": "Tab"
      }
    },
    {
      "stepNumber": 6,
      "description": "Type National ID",
      "action": "type_text",
      "params": {
        "text": "987-65-4321",
        "keystrokeDelayMs": 25
      }
    },
    {
      "stepNumber": 7,
      "description": "Navigate to Next Field",
      "action": "key_press",
      "params": {
        "key": "Tab"
      }
    },
    {
      "stepNumber": 8,
      "description": "Type Deposit Amount",
      "action": "type_text",
      "params": {
        "text": "2500.00",
        "keystrokeDelayMs": 25
      }
    },
    {
      "stepNumber": 9,
      "description": "Submit Form via Click",
      "action": "click",
      "params": {
        "x": 320,
        "y": 362,
        "button": "left",
        "clickCount": 1
      }
    }
  ]
}
```

---

### 6.2 Translation Algorithm: Visual Designer to Action Workflow

The translation engine deterministically compiles visual layout boxes into the sequential action workflow using the following formal transformation pipeline:

```
[ Visual Box Collection ]
           │
           ▼
1. Validation Filter (Ensure width > 0, height > 0, valid index)
           │
           ▼
2. Sequence Sorting (Order by index ASC; if identical, sort Y then X)
           │
           ▼
3. Window Target Preamble (Inject initial 'focus_window' step)
           │
           ▼
4. Box Iteration Loop (For each Box B in sorted list):
   │
   ├─► Calculate Click Coordinates: 
   │     Cx = B.x + (B.width / 2)
   │     Cy = B.y + (B.height / 2)
   │
   ├─► Emit Step: 'click' at (Cx, Cy) [If first box or explicit click specified]
   │
   ├─► If B.clearFirst == True:
   │     Emit Step: 'key_chord' (Ctrl + A)
   │     Emit Step: 'key_press' (Backspace)
   │
   ├─► If B.value is not empty:
   │     Emit Step: 'type_text' (text = B.value, keystrokeDelay = default or box override)
   │
   ├─► Post-Action Processing:
   │     If B.postAction == "tab":
   │       Emit Step: 'key_press' (Key = Tab)
   │     Else If B.postAction == "enter":
   │       Emit Step: 'key_press' (Key = Enter)
   │     Else If B.postAction == "click":
   │       (Target already clicked or will click next target)
   │     Else If B.postAction == "none":
   │       (No navigation emitted)
   │
   └─► Inter-Step Pause:
         Emit Step: 'delay' (duration = B.delayAfterMs)
           │
           ▼
5. Output Executable Action Workflow
```

---

### 6.3 Execution State Machine Specification

The kutomoto Workflow Engine strictly enforces the following finite state machine (FSM):

```
       ┌────────────────────────┐
       │          IDLE          │◄───────────────────────┐
       └───────────┬────────────┘                        │
                   │ Trigger: Start Execution            │
                   ▼                                     │
       ┌────────────────────────┐                        │
       │    ARMED_COUNTDOWN     │                        │
       └───────────┬────────────┘                        │
                   │ Timer Expires (0s)                  │
                   ▼                                     │
       ┌────────────────────────┐    Trigger: Pause      │
  ┌───►│        RUNNING         ├──────────────────┐     │
  │    └─────┬────────────┬─────┘                  ▼     │
  │          │            │               ┌────────┴─────┴──┐
  │          │            │               │     PAUSED      │
  │          │            │               └────────┬────────┘
  │          │            │                        │
  │          │            └────────────────────────┘
  │          │                Trigger: Resume
  │          ▼
  │    Step Completed (More steps remain)
  │
  │          │
  │          ├───────────────────► Trigger: Emergency Abort (Esc/F10)
  │          │                     │
  │          │                     ▼
  │          │             ┌─────────────────┐
  │          │             │     ABORTED     │
  │          │             └─────────────────┘
  │          │
  │          ├───────────────────► Step Exception / Window Focus Failure
  │          │                     │
  │          │                     ▼
  │          │             ┌─────────────────┐
  │          │             │     FAILED      │
  │          │             └─────────────────┘
  │          │
  │          ▼ All Steps Successfully Executed
  │    ┌─────────────────┐
  └───►│    COMPLETED    ├─────────────────────────────────┘
       └─────────────────┘
```

#### State Definitions & Transition Rules:
1. **`IDLE`**: Engine is quiescent. Workflows can be created, edited, saved, or loaded. No input simulation hooks are active.
2. **`ARMED_COUNTDOWN`**: Triggered by user pressing "Execute". A 3-second visual countdown is displayed. Global abort hotkey (`Escape`) is active. If Escape is pressed, transitions back to `IDLE`. At 0 seconds, activates target window and transitions to `RUNNING`.
3. **`RUNNING`**: Engine iterates over the action sequence. Before each atomic action:
   - Check abort flag (transitions to `ABORTED` if set).
   - Check pause flag (transitions to `PAUSED` if set).
   - Verify foreground window still matches target (if not, pause or alert).
   - Execute input action.
   - Wait inter-step delay.
4. **`PAUSED`**: Input injection suspended. Hotkey `F9` or "Resume" button transitions state back to `RUNNING`.
5. **`ABORTED`**: Operator pressed emergency hotkey. Keystrokes and clicks stopped immediately. Execution logs marked with abort timestamp.
6. **`FAILED`**: An unrecoverable error occurred (e.g. target window closed, invalid coordinates, OS exception). Diagnostic details logged.
7. **`COMPLETED`**: All steps finished successfully. Form submission acknowledged. Audit log entry written. Transitions back to `IDLE` upon acknowledgment.

---

## 7. Target Application & Focus Management Specification

### 7.1 Cross-Platform Windows Input Primitives

kutomoto interacts with target applications at the Windows OS boundary using standard Win32 input simulation APIs:
1. **`SendInput` API**:
   - Primary mechanism for injecting synthetic keyboard (`KEYBDINPUT`) and mouse (`MOUSEINPUT`) events.
   - Guarantees proper hardware-level scan codes and Unicode flags (`KEYEVENTF_UNICODE`).
   - Resistant to keyboard layout discrepancies (e.g. QWERTY vs. AZERTY vs. QWERTZ).
2. **Window Activation & Focus Hierarchy**:
   - `FindWindow` / `EnumWindows`: Enumerates top-level desktop windows to identify the target by title regex or process name.
   - `ShowWindow(hWnd, SW_RESTORE)`: Restores target if minimized.
   - `SetForegroundWindow(hWnd)`: Brings the target window to the front and gives it keyboard focus.
   - `AttachThreadInput` (fallback): Ensures input focus transfer even if Windows focus-stealing prevention restricts standard activation.
3. **DPI-Aware Coordinate Translation**:
   - Windows applications may operate under diverse display scaling (100%, 125%, 150%, 200%).
   - kutomoto must register as Per-Monitor DPI Aware (`SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)`).
   - Click coordinates can be computed in either:
     - **Screen Coordinates**: Absolute pixels across the virtual desktop.
     - **Client Coordinates**: Relative to the target window client rect (`GetClientRect` + `ClientToScreen`), ensuring resilience against window repositioning.

### 7.2 Web Browser Interaction Paradigms
For open web browser pages (Chrome, Edge, Firefox):
- **Universal Non-Invasive Approach**: Does not require browser extensions, remote debugging flags, or driver binaries. Treats the browser as a top-level Windows application.
- **Initial Anchor Focus**: A single coordinate click into the first input field anchors DOM focus.
- **Tab Sequence Traversal**: Subsequent field transitions leverage standard HTML tab indexing (`key_press: Tab`), guaranteeing robustness regardless of DOM layout reflows or responsive styling.
- **Submission**: Final form submission dispatches an `Enter` key press or clicks the known coordinate of the submit button.

### 7.3 Desktop Application Interaction Paradigms
For native Windows desktop applications (Win32, WinForms, WPF, Qt, SAP GUI, Electron):
- Directly activates the application window handle.
- Supports coordinate-based clicking on non-focusable canvas elements.
- Supports native keyboard accelerators and navigation chords (`Tab`, `Shift+Tab`, `Alt+Key`, `Enter`, `Space`).
- Handles complex enterprise multi-window popups and modal confirmation dialogues.

---

## 8. Verification & Test Scenarios Specification

To satisfy acceptance criteria, the kutomoto solution must include two fully functional, self-contained verification environments demonstrating end-to-end automated form filling:

### 8.1 Scenario WEB-01: End-to-End Automated Web Form Verification
- **Test Artifact**: `sample_web_form.html` (Local web form served via file:// or lightweight local HTTP server).
- **Target Form Structure**:
  - Form Title: "kutomoto Enterprise Banking & KYC Verification Portal"
  - Input 1: `customer_name` (Text Input)
  - Input 2: `account_number` (Text Input / Numeric)
  - Input 3: `tax_id` (Text Input - SSN / Tax ID)
  - Input 4: `deposit_amount` (Number Input - Currency)
  - Input 5: `account_type` (Select Dropdown - Checking, Savings, Corporate)
  - Input 6: `terms_checkbox` (Checkbox - Compliance Agreement)
  - Button: `submit_button` (Submit Button)
- **Validation Mechanics**:
  - The form includes JavaScript validation: all fields are mandatory, `account_number` must be 10 digits, `deposit_amount` must be > 0.
  - Upon submission, the form suppresses page reload (`e.preventDefault()`), checks all fields, and displays a prominent visual success panel:
    `"Submission Succeeded: All 6 Fields Verified [Timestamp]"` alongside the JSON representation of submitted data.
- **kutomoto Test Workflow**:
  - Pre-built workflow `test_web_kyc_workflow.ktm.json`.
  - Executes countdown -> focuses browser window -> clicks first input -> types all fields -> toggles checkbox -> clicks Submit.
  - Automated or manual assertion verifies the success panel is rendered.

### 8.2 Scenario DSK-01: End-to-End Automated Desktop Application Form Verification
- **Test Artifact**: `sample_desktop_form.py` / `.exe` (Clean native Windows desktop GUI application).
- **Target Form Structure**:
  - Application Window Title: "kutomoto Enterprise Desktop Invoice Portal - 90Studio"
  - Field 1: `Vendor Name` (Entry)
  - Field 2: `Invoice Number` (Entry)
  - Field 3: `Invoice Amount` (Entry)
  - Field 4: `Cost Center Code` (Entry)
  - Field 5: `Approval Category` (Dropdown / Combobox)
  - Field 6: `Urgent Processing` (Checkbutton)
  - Button: `Submit Invoice` (Button)
- **Validation Mechanics**:
  - The desktop form validates that all fields are populated.
  - Upon clicking "Submit Invoice", updates a prominent visual status label:
    `"Status: INVOICE POSTED SUCCESSFULLY - Reference #90S-[RandomID]"`.
- **kutomoto Test Workflow**:
  - Pre-built workflow `test_desktop_invoice_workflow.ktm.json`.
  - Executes countdown -> focuses desktop window -> populates all 6 fields in sequence -> presses Enter or clicks Submit.
  - Asserts that the desktop status label reflects "INVOICE POSTED SUCCESSFULLY".

---

## 9. Requirements Traceability Matrix (R1 - R4)

| Requirement | Acceptance Criteria Item | Addressed in Section | Validation Method |
|-------------|--------------------------|----------------------|-------------------|
| **R1. Specification & User Stories** | Dedicated specification document includes detailed feature list and user stories for business, banking, and telecom use cases. | Section 2 (Features Table), Section 4 (Use Cases BK, TC, GB), Section 5 (User Stories) | Document audit against enterprise criteria. |
| **R1. Specification & User Stories** | User stories cover visual form designing, step-by-step flow creation, execution against target applications, and error handling. | Section 5 (Epics 1 through 8, User Stories US-VFD, US-AWE, US-TRANS, US-EXEC, US-FOC, US-ERR) | Completeness of acceptance criteria and Gherkin scenarios. |
| **R2. Visual Form Designer & Workflow Generation** | Users can visually draw boxes representing form inputs and specify their execution order and text values. | Section 2 (F01, F02, F03), Section 5.1 (US-VFD-01, 02, 03), Section 6.1.1 (Visual Schema) | Interactive canvas drawing, property editor, and sequence re-indexing. |
| **R2. Visual Form Designer & Workflow Generation** | System automatically translates visual box sequence into an executable action workflow. | Section 2 (F05), Section 5.3 (US-TRANS-01), Section 6.2 (Translation Algorithm Pipeline) | Unit and integration test verifying compilation from visual schema to action schema. |
| **R3. Action Flow Creation & Execution** | Users can configure sequential actions including text input, key presses (Tab, Enter), and mouse clicks at coordinates. | Section 2 (F06-F12), Section 5.2 (US-AWE-01 to 04), Section 6.1.2 (Action Workflow Schema) | Step builder UI and action serialization. |
| **R3. Action Flow Creation & Execution** | Automation workflows execute successfully against open web browser pages. | Section 2 (F15), Section 5.4 (US-EXEC-01), Section 7.2, Section 8.1 (Scenario WEB-01) | End-to-end execution against `sample_web_form.html`. |
| **R3. Action Flow Creation & Execution** | Automation workflows execute successfully against Windows desktop application forms. | Section 2 (F16), Section 5.4 (US-EXEC-02), Section 7.3, Section 8.2 (Scenario DSK-01) | End-to-end execution against `sample_desktop_form`. |
| **R4. Application Implementation & UI** | Application presents a clean, professional user interface suitable for enterprise environments. | Section 2 (F20), Section 5.7 (US-UI-01), Section 1.3 | UI theme audit, typography, high-DPI scaling check. |
| **R4. Application Implementation & UI** | Displays name "kutomoto" and attribution "Copyrights reserved to 90Studio". | Section 1.3, Section 2 (F21), Section 5.7 (US-UI-01) | Static code & UI string verification across titles, footers, and About box. |

---

## 10. Conclusion & Recommendations for Implementation

1. **Architecture Decoupling**: Maintain strict architectural separation between the **Visual Form Designer Model**, the **Action Workflow Model**, and the **Execution Engine**. The Visual Designer compiles down to the Action Workflow schema; the Execution Engine executes only the Action Workflow schema. This ensures manual workflows and visually generated workflows run on the identical, battle-tested execution pipeline.
2. **Robust Focus Management**: Do not rely exclusively on window title exact matching. Implement regex and substring matching, combined with the 3-second arming countdown and `SetForegroundWindow` API calls.
3. **Emergency Stop is Mandatory**: Enterprise deployments require immediate operator override (`Escape` or `F10` global hotkey) to guarantee safety in production banking and telecom environments.
4. **Clean Enterprise Branding**: Ensure `kutomoto` and `Copyrights reserved to 90Studio` are permanently displayed in the primary window title bar, footer/status bar, and system metadata.

---
*Report compiled and delivered by spec_miner_survey_1.*  
*Copyrights reserved to 90Studio.*
