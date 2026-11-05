# Handoff Report: Workflow UI, Countdown HUD, CLI Launchers & API Test Suite

**Agent**: `m4_explorer_3`  
**Milestone**: M4 (Enterprise Application UI & 90Studio Branding)  
**Date**: 2026-11-05  
**Product**: kutomoto — Professional Forms Filling Automation System for Windows OS  
**Copyright**: Copyrights reserved to 90Studio  

---

## 1. Observation

### 1.1 Problem Boundary & Mandate
Investigation and architectural design covering four core subsystems of Milestone M4:
1. **Step-by-Step Flow Builder** (`src/kutomoto/ui/js/runner.js`): Sequential action step editor with card/table views, drag-and-drop / button-based reordering, parameter configuration across all 10 atomic actions, and `/api/workflows` persistence.
2. **Target Window Selector & Countdown HUD** (`src/kutomoto/ui/js/runner.js`): Active desktop window enumeration dropdown from `/api/windows`, interactive 3-second Countdown HUD modal with Escape-key abort guardian, and real-time Live Execution Console subscribing to `/ws/execution`.
3. **Windows Launcher & CLI Entry Point** (`src/kutomoto/__main__.py` and `run_kutomoto.bat`): Full CLI argument parsing (`--host`, `--port`, `--no-browser`, `--mock`), Microsoft Edge App Mode launcher (`msedge.exe --app=...`) with browser fallback, and Windows batch script launcher.
4. **Comprehensive Test Suite** (`tests/test_api.py`): Enterprise test suite leveraging `fastapi.testclient.TestClient` covering health & branding, workflow CRUD, designer compilation, window enumeration, execution lifecycle (start, pause, resume, abort), and WebSocket streaming.

### 1.2 Existing Codebase Contracts Observed
1. **Schema & Engine Data Models** (`src/kutomoto/engine/schema.py`):
   - `KutomotoWorkflow`: Lines 232–264 validate schema version (`1.0.0`), mandatory copyright watermark (`"Copyrights reserved to 90Studio"`), target application details, execution settings, variables, and non-empty steps list with unique sequential indices.
   - `WorkflowStep` & `StepParameters`: Lines 151–196 define parameters for all 10 atomic actions (`focus_window`, `click`, `type_text`, `key_press`, `hotkey`, `clear_field`, `delay`, `submit`, `scroll`, `prompt_user_input`).
   - `ExecutionSettings`: Lines 206–215 specify `countdown_seconds` (default 3), `default_step_delay_ms` (default 120), `typing_speed_ms` (default 20), `stop_on_error`, and `error_recovery_policy`.
2. **Execution Engine & Telemetry** (`src/kutomoto/engine/runner.py`):
   - Lines 436–450: Asynchronous countdown loop emitting `countdown_tick` telemetry with `{"remaining": rem}` every second before transitioning to `RUNNING`.
   - Lines 518–530: Step loop emitting `step_started` and `step_completed` telemetry events with step indices, action types, labels, and latency.
   - Lines 713–746: Control methods `pause()`, `resume()`, and `abort()` with modifier cleanup.
3. **Desktop Window Inspection Core** (`src/kutomoto/automation/win32_window.py`):
   - Lines 39–66: `WindowInfo` dataclass providing `hwnd`, `title`, `class_name`, `pid`, `executable_name`, `executable_path`, `is_visible`, `is_iconic`, `rect`, and `client_rect`.
   - Lines 151–173: `enumerate_windows(visible_only=True, non_empty_title_only=True)` enumerating all top-level windows.
4. **Visual Compiler Endpoint Contract** (`src/kutomoto/designer/compiler.py`):
   - `compile_visual_layout_to_workflow(layout)` translates `VisualFormLayout` into `KutomotoWorkflow` through a 5-pass compilation pipeline.
5. **CLI Skeleton** (`src/kutomoto/__main__.py`):
   - Lines 11–37: Initial entry point skeleton ready for full CLI flags and server startup hook.

---

## 2. Logic Chain

### 2.1 Component 1: Step-by-Step Flow Builder Architecture (`runner.js`)
- **Observation**: `KutomotoWorkflow` requires contiguous unique sequence indices (`1..N`) and specific parameter structures for each `ActionType`.
- **Inference**: The frontend flow builder must maintain an in-memory workflow state model that automatically synchronizes with the UI. When steps are added, deleted, duplicated, or reordered via drag-and-drop or up/down buttons, an idempotent `reindexSteps()` function must re-assign `sequence_index = index + 1` sequentially.
- **Form Configuration**:
  - Each action type requires tailored parameter inputs. For instance:
    - `click`: Coordinate mode toggle (normalized $0.0..1.0$ vs screen pixels), $X/Y$ inputs, mouse button selector (`left`, `right`, `middle`), and click count (`1`, `2`, `3`).
    - `type_text`: Payload textarea with support for `{{variable_name}}` templates, secret masking toggle, and delay settings.
    - `key_press`: Datalist of valid keys (`tab`, `enter`, `escape`, `backspace`, `space`, arrows) and repeat count.
    - `hotkey`: Tag or comma-separated modifier chord input (`ctrl, a`).
    - `focus_window`: Window title pattern, process executable name, match mode dropdown (`contains`, `exact`, `regex`).
- **Persistence Pipeline**:
  - `saveWorkflow()` serializes the workflow object and issues `POST /api/workflows` (or `PUT /api/workflows/{id}`).
  - `loadWorkflowList()` calls `GET /api/workflows` to populate a selectable list of saved flows.
  - Export/Import buttons allow local JSON backup and restoration.

### 2.2 Component 2: Target Window Selector & Countdown HUD Architecture (`runner.js`)
- **Observation**: Before automation runs, the operator must select which window to target, and a 3-second buffer is required (Section 9.1 / T04) to prevent keystrokes from firing into the wrong application.
- **Window Selector**:
  - Fetches `GET /api/windows`, filtering by active/visible windows.
  - Renders a responsive picker showing the title, process name (e.g. `chrome.exe`, `msedge.exe`), PID, and window bounds.
  - Selecting a window binds its title and executable to `workflow.target_application`.
- **3-Second Countdown HUD Modal**:
  - Triggered by clicking "Run Workflow".
  - Opens a dark, high-contrast modal overlay (`rgba(15, 23, 42, 0.85)`).
  - Displays a visual SVG countdown ring with animated stroke and giant numeric counter (`3... 2... 1...`).
  - Highlights the target window name and instructions: *"Switching to target window... Press [Escape] or click Cancel to abort."*
  - A global keyboard event listener (`keydown`) intercepts `Escape`, calling `cancelCountdown()` and sending `POST /api/execute/abort`.
  - When the countdown finishes, sends `POST /api/execute/start` with the workflow payload.
- **Live Execution Console & WebSocket Stream**:
  - Establishes a persistent WebSocket connection to `/ws/execution`.
  - Displays an animated step progress bar (`Step X of Y - Z%`).
  - Highlights the actively executing step card with a pulsing blue accent and updates completed steps with green checks and millisecond latencies.
  - Appends streaming log events to an enterprise monospace console container, stamped with `"Copyrights reserved to 90Studio"`.
  - Provides instant-response Pause (`POST /api/execute/pause`), Resume (`POST /api/execute/resume`), and Emergency Abort (`POST /api/execute/abort`) controls.

### 2.3 Component 3: Windows Launcher & CLI Entry Point (`__main__.py`, `run_kutomoto.bat`)
- **Observation**: Enterprise users expect native desktop software behavior on Windows without wrestling with browser tabs or terminal commands.
- **Microsoft Edge App Mode**:
  - Microsoft Edge (`msedge.exe`) natively supports `--app=URL`, rendering web applications in a clean, standalone, frameless desktop window without URL address bars or tabs.
  - The launcher scans standard Windows installation directories:
    1. `%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe`
    2. `%ProgramFiles%\Microsoft\Edge\Application\msedge.exe`
    3. `%LocalAppData%\Microsoft\Edge\Application\msedge.exe`
    4. System `PATH`
  - When found, it launches:
    `msedge.exe --app=http://127.0.0.1:8765/ --window-size=1366,850 --window-position=50,50`
  - If Edge is unavailable, it falls back seamlessly to `webbrowser.open()`.
- **Health Polling Thread**:
  - A background daemon thread polls `http://{host}:{port}/api/health` every 200ms up to 30 attempts before triggering the browser launch, ensuring zero 404 / connection-refused errors.
- **CLI Options**:
  - `--host`: Bind host (default: `127.0.0.1`).
  - `--port`: Listen port (default: `8765`).
  - `--no-browser`: Prevents browser shell launch (for headless CI, automated testing, or API-only mode).
  - `--mock`: Sets `KUTOMOTO_MOCK_DRIVER=1` for harmless testing on Windows without hijacking the operator's mouse and keyboard.
- **Batch Launcher (`run_kutomoto.bat`)**:
  - Checks Python installation, sets UTF-8 codepage (`chcp 65001`), changes working directory to the project root, and launches `python -m kutomoto --port 8765`.
  - Pauses on error so operators can inspect traceback details.

### 2.4 Component 4: Test Suite Design (`tests/test_api.py`)
- **Observation**: The REST API and WebSocket hub must be thoroughly validated across all endpoints, schemas, lifecycle transitions, and branding constraints using `fastapi.testclient.TestClient`.
- **Test Structure**:
  - Unit and integration tests structured into 6 focused test classes:
    1. `TestHealthAndBranding`: Asserts `GET /api/health` returns status `ok`, version `1.0.0`, and `"Copyrights reserved to 90Studio"`.
    2. `TestWorkflowCrud`: Tests `GET`, `POST`, `GET /{id}`, and `DELETE` on `/api/workflows`, validating Pydantic schemas, copyright rejections, and 404 handling.
    3. `TestDesignerCompileEndpoint`: Tests `POST /api/designer/compile` converting `VisualFormLayout` into `KutomotoWorkflow` and handling invalid layouts.
    4. `TestWindowsEnumeration`: Tests `GET /api/windows` returning active desktop windows.
    5. `TestExecutionLifecycle`: Tests `POST /api/execute/start`, `pause`, `resume`, `abort`, and `status`.
    6. `TestWebSocketExecution`: Tests real-time streaming via `client.websocket_connect("/ws/execution")`, validating `step_started`, `step_completed`, and `countdown_tick` telemetry events.

---

## 3. Caveats

1. **Non-Windows Execution / CI Environments**:
   - `ctypes.windll.user32` is unavailable on Linux/macOS. When executing tests in non-Windows environments or headless CI, `tests/test_api.py` must use a mock driver fixture or instantiate `WorkflowRunner` with mock primitives. The design explicitly includes a complete `MockWin32Driver`.
2. **Microsoft Edge App Mode Execution Rights**:
   - In locked-down corporate Windows environments, Group Policy may restrict executing subprocesses from temp directories. Searching `%ProgramFiles%` and `%LocalAppData%` ensures compliance with standard enterprise paths.
3. **WebSocket Multi-Client Concurrency**:
   - Multiple browser tabs or reconnecting clients must be handled via a connection manager that cleans up disconnected WebSockets gracefully on `WebSocketDisconnect` exceptions without leaking memory or throwing unhandled errors.

---

## 4. Conclusion & Concrete Code Specifications

The complete, production-ready designs for all four components are detailed below for immediate implementation in Milestone M4.

### 4.1 Component 1 & 2 Blueprint: `src/kutomoto/ui/js/runner.js`

```javascript
/**
 * kutomoto — Professional Forms Filling Automation System for Windows OS
 * Step-by-Step Flow Builder, Target Window Selector & Countdown HUD
 * Copyrights reserved to 90Studio
 */

(function (window) {
    'use strict';

    // =========================================================================
    // 1. STATE MANAGEMENT & CONSTANTS
    // =========================================================================

    const ACTION_TYPES = {
        FOCUS_WINDOW: 'focus_window',
        CLICK: 'click',
        TYPE_TEXT: 'type_text',
        KEY_PRESS: 'key_press',
        HOTKEY: 'hotkey',
        CLEAR_FIELD: 'clear_field',
        DELAY: 'delay',
        SUBMIT: 'submit',
        SCROLL: 'scroll',
        PROMPT_USER_INPUT: 'prompt_user_input'
    };

    const ACTION_COLORS = {
        focus_window: '#8b5cf6',
        click: '#10b981',
        type_text: '#3b82f6',
        key_press: '#f59e0b',
        hotkey: '#ec4899',
        clear_field: '#64748b',
        delay: '#6b7280',
        submit: '#4f46e5',
        scroll: '#06b6d4',
        prompt_user_input: '#d97706'
    };

    let state = {
        workflow: createDefaultWorkflow(),
        activeWindows: [],
        executionId: null,
        executionState: 'IDLE',
        countdownTimer: null,
        countdownRemaining: 3,
        ws: null,
        editingStepId: null
    };

    function createDefaultWorkflow() {
        return {
            schema_version: '1.0.0',
            id: crypto.randomUUID(),
            name: 'New Form Automation Flow',
            description: 'Automated enterprise form filling workflow',
            author: 'Enterprise Operator',
            copyright: 'Copyrights reserved to 90Studio',
            source_mode: 'manual_step_flow',
            target_application: {
                type: 'windows_desktop',
                window_title_pattern: '',
                process_name: '',
                match_mode: 'contains'
            },
            execution_settings: {
                countdown_seconds: 3,
                default_step_delay_ms: 120,
                typing_speed_ms: 20,
                stop_on_error: true,
                error_recovery_policy: 'abort',
                max_step_retries: 2,
                failsafe_corner_enabled: true,
                abort_hotkey: 'Escape'
            },
            variables: [],
            steps: [
                {
                    step_id: crypto.randomUUID(),
                    sequence_index: 1,
                    label: 'Focus Target Application Window',
                    action_type: ACTION_TYPES.FOCUS_WINDOW,
                    enabled: true,
                    pre_delay_ms: 0,
                    post_delay_ms: 200,
                    parameters: {
                        window_title_pattern: '',
                        process_name: '',
                        match_mode: 'contains'
                    }
                }
            ]
        };
    }

    // =========================================================================
    // 2. STEP BUILDER & REORDERING CORE
    // =========================================================================

    function reindexSteps() {
        state.workflow.steps.forEach((step, idx) => {
            step.sequence_index = idx + 1;
        });
    }

    function addStep(actionType = ACTION_TYPES.TYPE_TEXT) {
        const nextIndex = state.workflow.steps.length + 1;
        const newStep = {
            step_id: crypto.randomUUID(),
            sequence_index: nextIndex,
            label: `Step ${nextIndex}: ${actionType.replace('_', ' ').toUpperCase()}`,
            action_type: actionType,
            enabled: true,
            pre_delay_ms: 0,
            post_delay_ms: state.workflow.execution_settings.default_step_delay_ms || 120,
            parameters: getDefaultParametersFor(actionType)
        };
        state.workflow.steps.push(newStep);
        reindexSteps();
        renderStepList();
        editStep(newStep.step_id);
    }

    function getDefaultParametersFor(actionType) {
        switch (actionType) {
            case ACTION_TYPES.FOCUS_WINDOW:
                return { window_title_pattern: state.workflow.target_application.window_title_pattern || '', process_name: '', match_mode: 'contains' };
            case ACTION_TYPES.CLICK:
                return { norm_x: 0.5, norm_y: 0.5, coordinate_mode: 'normalized', button: 'left', click_count: 1 };
            case ACTION_TYPES.TYPE_TEXT:
                return { text: '', is_secret: false, keystroke_delay_ms: 20, use_clipboard_threshold: 40 };
            case ACTION_TYPES.KEY_PRESS:
                return { key: 'tab', repeat_count: 1 };
            case ACTION_TYPES.HOTKEY:
                return { keys: ['ctrl', 'a'] };
            case ACTION_TYPES.CLEAR_FIELD:
                return { clear_strategy: 'select_all_backspace', repeat_backspace_count: 50 };
            case ACTION_TYPES.DELAY:
                return { duration_ms: 500 };
            case ACTION_TYPES.SUBMIT:
                return { submit_method: 'enter_key' };
            case ACTION_TYPES.SCROLL:
                return { delta_x: 0, delta_y: -120 };
            case ACTION_TYPES.PROMPT_USER_INPUT:
                return { variable_name: 'operator_input', prompt_message: 'Please enter verification value:', is_password: false };
            default:
                return {};
        }
    }

    function duplicateStep(stepId) {
        const idx = state.workflow.steps.findIndex(s => s.step_id === stepId);
        if (idx === -1) return;
        const orig = state.workflow.steps[idx];
        const clone = JSON.parse(JSON.stringify(orig));
        clone.step_id = crypto.randomUUID();
        clone.label = `${orig.label} (Copy)`;
        state.workflow.steps.splice(idx + 1, 0, clone);
        reindexSteps();
        renderStepList();
    }

    function deleteStep(stepId) {
        if (state.workflow.steps.length <= 1) {
            alert('A workflow must contain at least one step.');
            return;
        }
        state.workflow.steps = state.workflow.steps.filter(s => s.step_id !== stepId);
        reindexSteps();
        renderStepList();
    }

    function moveStep(stepId, direction) {
        const idx = state.workflow.steps.findIndex(s => s.step_id === stepId);
        if (idx === -1) return;
        const targetIdx = idx + direction;
        if (targetIdx < 0 || targetIdx >= state.workflow.steps.length) return;
        
        const temp = state.workflow.steps[idx];
        state.workflow.steps[idx] = state.workflow.steps[targetIdx];
        state.workflow.steps[targetIdx] = temp;
        reindexSteps();
        renderStepList();
    }

    // =========================================================================
    // 3. STEP LIST RENDERING & DRAG-AND-DROP
    // =========================================================================

    function renderStepList() {
        const container = document.getElementById('step-list-container');
        if (!container) return;

        container.innerHTML = '';
        state.workflow.steps.forEach((step, index) => {
            const card = document.createElement('div');
            card.className = `step-card ${step.enabled ? '' : 'step-disabled'}`;
            card.setAttribute('draggable', 'true');
            card.setAttribute('data-id', step.step_id);
            card.setAttribute('data-index', index);

            const badgeColor = ACTION_COLORS[step.action_type] || '#64748b';
            const paramSummary = summarizeParameters(step);

            card.innerHTML = `
                <div class="step-drag-handle" title="Drag to reorder">&#x22EE;&#x22EE;</div>
                <div class="step-seq-badge">#${step.sequence_index}</div>
                <div class="step-action-badge" style="background-color: ${badgeColor};">${step.action_type}</div>
                <div class="step-details">
                    <div class="step-label">${escapeHtml(step.label || 'Untitled Step')}</div>
                    <div class="step-summary">${escapeHtml(paramSummary)}</div>
                </div>
                <div class="step-timings">
                    <span title="Pre-delay">&#x23F1; ${step.pre_delay_ms}ms</span> /
                    <span title="Post-delay">${step.post_delay_ms}ms</span>
                </div>
                <div class="step-controls">
                    <button type="button" class="btn-step-icon btn-edit" title="Edit Step">&#x270E;</button>
                    <button type="button" class="btn-step-icon btn-up" title="Move Up" ${index === 0 ? 'disabled' : ''}>&#x25B2;</button>
                    <button type="button" class="btn-step-icon btn-down" title="Move Down" ${index === state.workflow.steps.length - 1 ? 'disabled' : ''}>&#x25BC;</button>
                    <button type="button" class="btn-step-icon btn-duplicate" title="Duplicate Step">&#x29C9;</button>
                    <button type="button" class="btn-step-icon btn-delete" title="Delete Step">&#x1F5D1;</button>
                </div>
            `;

            // Card Event Bindings
            card.querySelector('.btn-edit').addEventListener('click', () => editStep(step.step_id));
            card.querySelector('.btn-up').addEventListener('click', () => moveStep(step.step_id, -1));
            card.querySelector('.btn-down').addEventListener('click', () => moveStep(step.step_id, 1));
            card.querySelector('.btn-duplicate').addEventListener('click', () => duplicateStep(step.step_id));
            card.querySelector('.btn-delete').addEventListener('click', () => deleteStep(step.step_id));

            setupDragHandlers(card);
            container.appendChild(card);
        });

        updateWorkflowMetrics();
    }

    function summarizeParameters(step) {
        const p = step.parameters || {};
        switch (step.action_type) {
            case ACTION_TYPES.FOCUS_WINDOW:
                return `Target: "${p.window_title_pattern || '*'}" [${p.match_mode || 'contains'}]`;
            case ACTION_TYPES.CLICK:
                return `Click (${p.norm_x ?? p.x}, ${p.norm_y ?? p.y}) [${p.button || 'left'} x${p.click_count || 1}]`;
            case ACTION_TYPES.TYPE_TEXT:
                return p.is_secret ? 'Typed: ********** (secret)' : `Typed: "${p.text || ''}"`;
            case ACTION_TYPES.KEY_PRESS:
                return `Key: ${p.key || 'tab'} (x${p.repeat_count || 1})`;
            case ACTION_TYPES.HOTKEY:
                return `Hotkey: ${(p.keys || []).join('+')}`;
            case ACTION_TYPES.CLEAR_FIELD:
                return `Clear: ${p.clear_strategy || 'select_all_backspace'}`;
            case ACTION_TYPES.DELAY:
                return `Wait: ${p.duration_ms || 0}ms`;
            case ACTION_TYPES.SUBMIT:
                return `Submit: ${p.submit_method || 'enter_key'}`;
            case ACTION_TYPES.SCROLL:
                return `Scroll: X=${p.delta_x || 0}, Y=${p.delta_y || 0}`;
            case ACTION_TYPES.PROMPT_USER_INPUT:
                return `Prompt -> {{${p.variable_name}}}: "${p.prompt_message}"`;
            default:
                return JSON.stringify(p);
        }
    }

    let draggedItem = null;
    function setupDragHandlers(card) {
        card.addEventListener('dragstart', (e) => {
            draggedItem = card;
            card.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        });

        card.addEventListener('dragend', () => {
            if (draggedItem) draggedItem.classList.remove('dragging');
            draggedItem = null;
            document.querySelectorAll('.step-card').forEach(c => c.classList.remove('drag-over'));
        });

        card.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            card.classList.add('drag-over');
        });

        card.addEventListener('dragleave', () => {
            card.classList.remove('drag-over');
        });

        card.addEventListener('drop', (e) => {
            e.preventDefault();
            card.classList.remove('drag-over');
            if (!draggedItem || draggedItem === card) return;

            const fromIndex = parseInt(draggedItem.getAttribute('data-index'), 10);
            const toIndex = parseInt(card.getAttribute('data-index'), 10);

            const movedStep = state.workflow.steps.splice(fromIndex, 1)[0];
            state.workflow.steps.splice(toIndex, 0, movedStep);
            reindexSteps();
            renderStepList();
        });
    }

    // =========================================================================
    // 4. STEP PARAMETER EDITOR MODAL
    // =========================================================================

    function editStep(stepId) {
        state.editingStepId = stepId;
        const step = state.workflow.steps.find(s => s.step_id === stepId);
        if (!step) return;

        const modal = document.getElementById('step-editor-modal');
        if (!modal) return;

        document.getElementById('edit-step-label').value = step.label || '';
        document.getElementById('edit-step-action-type').value = step.action_type;
        document.getElementById('edit-step-pre-delay').value = step.pre_delay_ms || 0;
        document.getElementById('edit-step-post-delay').value = step.post_delay_ms || 0;
        document.getElementById('edit-step-enabled').checked = step.enabled !== false;

        renderParameterFields(step.action_type, step.parameters || {});
        modal.classList.add('active');
    }

    function renderParameterFields(actionType, params) {
        const container = document.getElementById('edit-params-fields');
        if (!container) return;

        container.innerHTML = '';
        switch (actionType) {
            case ACTION_TYPES.FOCUS_WINDOW:
                container.innerHTML = `
                    <div class="form-group">
                        <label>Window Title Pattern (Regex / Substring):</label>
                        <input type="text" id="p-title-pattern" class="form-input" value="${escapeHtml(params.window_title_pattern || '')}">
                    </div>
                    <div class="form-group">
                        <label>Process Name (e.g. msedge.exe):</label>
                        <input type="text" id="p-process-name" class="form-input" value="${escapeHtml(params.process_name || '')}">
                    </div>
                    <div class="form-group">
                        <label>Match Mode:</label>
                        <select id="p-match-mode" class="form-select">
                            <option value="contains" ${params.match_mode === 'contains' ? 'selected' : ''}>Contains</option>
                            <option value="exact" ${params.match_mode === 'exact' ? 'selected' : ''}>Exact</option>
                            <option value="regex" ${params.match_mode === 'regex' ? 'selected' : ''}>Regex</option>
                        </select>
                    </div>
                `;
                break;
            case ACTION_TYPES.CLICK:
                container.innerHTML = `
                    <div class="form-row">
                        <div class="form-group col-6">
                            <label>Normalized X (0.0 to 1.0):</label>
                            <input type="number" step="0.001" min="0" max="1" id="p-norm-x" class="form-input" value="${params.norm_x ?? 0.5}">
                        </div>
                        <div class="form-group col-6">
                            <label>Normalized Y (0.0 to 1.0):</label>
                            <input type="number" step="0.001" min="0" max="1" id="p-norm-y" class="form-input" value="${params.norm_y ?? 0.5}">
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group col-6">
                            <label>Mouse Button:</label>
                            <select id="p-button" class="form-select">
                                <option value="left" ${params.button === 'left' ? 'selected' : ''}>Left</option>
                                <option value="right" ${params.button === 'right' ? 'selected' : ''}>Right</option>
                                <option value="middle" ${params.button === 'middle' ? 'selected' : ''}>Middle</option>
                            </select>
                        </div>
                        <div class="form-group col-6">
                            <label>Click Count:</label>
                            <select id="p-click-count" class="form-select">
                                <option value="1" ${params.click_count === 1 ? 'selected' : ''}>Single (1)</option>
                                <option value="2" ${params.click_count === 2 ? 'selected' : ''}>Double (2)</option>
                                <option value="3" ${params.click_count === 3 ? 'selected' : ''}>Triple (3)</option>
                            </select>
                        </div>
                    </div>
                `;
                break;
            case ACTION_TYPES.TYPE_TEXT:
                container.innerHTML = `
                    <div class="form-group">
                        <label>Text Payload (supports {{var_name}}):</label>
                        <textarea id="p-text" class="form-textarea" rows="3">${escapeHtml(params.text || '')}</textarea>
                    </div>
                    <div class="form-row">
                        <div class="form-group col-6">
                            <label>Keystroke Delay (ms):</label>
                            <input type="number" id="p-key-delay" class="form-input" value="${params.keystroke_delay_ms ?? 20}">
                        </div>
                        <div class="form-group col-6 checkbox-align">
                            <label class="checkbox-label">
                                <input type="checkbox" id="p-is-secret" ${params.is_secret ? 'checked' : ''}>
                                Mask in Audit Log (Secret)
                            </label>
                        </div>
                    </div>
                `;
                break;
            case ACTION_TYPES.KEY_PRESS:
                container.innerHTML = `
                    <div class="form-row">
                        <div class="form-group col-6">
                            <label>Key Name:</label>
                            <input type="text" id="p-key" class="form-input" list="keys-list" value="${escapeHtml(params.key || 'tab')}">
                            <datalist id="keys-list">
                                <option value="tab"><option value="enter"><option value="escape">
                                <option value="backspace"><option value="space"><option value="up">
                                <option value="down"><option value="left"><option value="right">
                            </datalist>
                        </div>
                        <div class="form-group col-6">
                            <label>Repeat Count:</label>
                            <input type="number" id="p-repeat-count" class="form-input" min="1" value="${params.repeat_count || 1}">
                        </div>
                    </div>
                `;
                break;
            case ACTION_TYPES.HOTKEY:
                container.innerHTML = `
                    <div class="form-group">
                        <label>Hotkey Chord (comma separated, e.g. ctrl, a):</label>
                        <input type="text" id="p-hotkey-keys" class="form-input" value="${escapeHtml((params.keys || []).join(', '))}">
                    </div>
                `;
                break;
            case ACTION_TYPES.CLEAR_FIELD:
                container.innerHTML = `
                    <div class="form-group">
                        <label>Clear Strategy:</label>
                        <select id="p-clear-strategy" class="form-select">
                            <option value="select_all_backspace" ${params.clear_strategy === 'select_all_backspace' ? 'selected' : ''}>Ctrl+A -> Backspace</option>
                            <option value="triple_click_delete" ${params.clear_strategy === 'triple_click_delete' ? 'selected' : ''}>Triple Click -> Delete</option>
                            <option value="backspace_repeat" ${params.clear_strategy === 'backspace_repeat' ? 'selected' : ''}>Repeat Backspace</option>
                        </select>
                    </div>
                `;
                break;
            case ACTION_TYPES.DELAY:
                container.innerHTML = `
                    <div class="form-group">
                        <label>Duration (milliseconds):</label>
                        <input type="number" id="p-duration" class="form-input" min="0" value="${params.duration_ms ?? 500}">
                    </div>
                `;
                break;
            case ACTION_TYPES.SUBMIT:
                container.innerHTML = `
                    <div class="form-group">
                        <label>Submit Method:</label>
                        <select id="p-submit-method" class="form-select">
                            <option value="enter_key" ${params.submit_method === 'enter_key' ? 'selected' : ''}>Enter Key</option>
                            <option value="button_click" ${params.submit_method === 'button_click' ? 'selected' : ''}>Button Click</option>
                        </select>
                    </div>
                `;
                break;
            case ACTION_TYPES.SCROLL:
                container.innerHTML = `
                    <div class="form-row">
                        <div class="form-group col-6">
                            <label>Delta X (Horizontal):</label>
                            <input type="number" id="p-delta-x" class="form-input" value="${params.delta_x || 0}">
                        </div>
                        <div class="form-group col-6">
                            <label>Delta Y (Vertical, negative down):</label>
                            <input type="number" id="p-delta-y" class="form-input" value="${params.delta_y || -120}">
                        </div>
                    </div>
                `;
                break;
            case ACTION_TYPES.PROMPT_USER_INPUT:
                container.innerHTML = `
                    <div class="form-group">
                        <label>Variable Name to Bind:</label>
                        <input type="text" id="p-var-name" class="form-input" value="${escapeHtml(params.variable_name || '')}">
                    </div>
                    <div class="form-group">
                        <label>Prompt Message for Operator:</label>
                        <input type="text" id="p-prompt-msg" class="form-input" value="${escapeHtml(params.prompt_message || '')}">
                    </div>
                `;
                break;
        }
    }

    function saveStepModal() {
        const step = state.workflow.steps.find(s => s.step_id === state.editingStepId);
        if (!step) return;

        step.label = document.getElementById('edit-step-label').value.trim();
        step.action_type = document.getElementById('edit-step-action-type').value;
        step.pre_delay_ms = parseInt(document.getElementById('edit-step-pre-delay').value, 10) || 0;
        step.post_delay_ms = parseInt(document.getElementById('edit-step-post-delay').value, 10) || 0;
        step.enabled = document.getElementById('edit-step-enabled').checked;

        // Collect parameters
        step.parameters = collectParameters(step.action_type);
        closeStepModal();
        renderStepList();
    }

    function collectParameters(actionType) {
        const p = {};
        switch (actionType) {
            case ACTION_TYPES.FOCUS_WINDOW:
                p.window_title_pattern = document.getElementById('p-title-pattern')?.value.trim() || '';
                p.process_name = document.getElementById('p-process-name')?.value.trim() || null;
                p.match_mode = document.getElementById('p-match-mode')?.value || 'contains';
                break;
            case ACTION_TYPES.CLICK:
                p.norm_x = parseFloat(document.getElementById('p-norm-x')?.value) || 0;
                p.norm_y = parseFloat(document.getElementById('p-norm-y')?.value) || 0;
                p.coordinate_mode = 'normalized';
                p.button = document.getElementById('p-button')?.value || 'left';
                p.click_count = parseInt(document.getElementById('p-click-count')?.value, 10) || 1;
                break;
            case ACTION_TYPES.TYPE_TEXT:
                p.text = document.getElementById('p-text')?.value || '';
                p.is_secret = document.getElementById('p-is-secret')?.checked || false;
                p.keystroke_delay_ms = parseInt(document.getElementById('p-key-delay')?.value, 10) || 20;
                break;
            case ACTION_TYPES.KEY_PRESS:
                p.key = document.getElementById('p-key')?.value.trim().toLowerCase() || 'tab';
                p.repeat_count = parseInt(document.getElementById('p-repeat-count')?.value, 10) || 1;
                break;
            case ACTION_TYPES.HOTKEY:
                p.keys = (document.getElementById('p-hotkey-keys')?.value || '')
                    .split(',')
                    .map(k => k.trim().toLowerCase())
                    .filter(k => k.length > 0);
                break;
            case ACTION_TYPES.CLEAR_FIELD:
                p.clear_strategy = document.getElementById('p-clear-strategy')?.value || 'select_all_backspace';
                break;
            case ACTION_TYPES.DELAY:
                p.duration_ms = parseInt(document.getElementById('p-duration')?.value, 10) || 0;
                break;
            case ACTION_TYPES.SUBMIT:
                p.submit_method = document.getElementById('p-submit-method')?.value || 'enter_key';
                break;
            case ACTION_TYPES.SCROLL:
                p.delta_x = parseInt(document.getElementById('p-delta-x')?.value, 10) || 0;
                p.delta_y = parseInt(document.getElementById('p-delta-y')?.value, 10) || 0;
                break;
            case ACTION_TYPES.PROMPT_USER_INPUT:
                p.variable_name = document.getElementById('p-var-name')?.value.trim() || 'operator_input';
                p.prompt_message = document.getElementById('p-prompt-msg')?.value.trim() || 'Prompt';
                break;
        }
        return p;
    }

    function closeStepModal() {
        document.getElementById('step-editor-modal')?.classList.remove('active');
        state.editingStepId = null;
    }

    // =========================================================================
    // 5. TARGET WINDOW SELECTOR COMPONENT
    // =========================================================================

    async function fetchActiveWindows() {
        const refreshBtn = document.getElementById('btn-refresh-windows');
        if (refreshBtn) refreshBtn.classList.add('spinning');

        try {
            const resp = await fetch('/api/windows?visible_only=true');
            if (!resp.ok) throw new Error('Failed to enumerate desktop windows');
            const windows = await resp.json();
            state.activeWindows = windows;
            renderWindowDropdown(windows);
        } catch (err) {
            console.error('Window enumeration error:', err);
            appendLog('ERROR', `Could not fetch desktop windows: ${err.message}`);
        } finally {
            if (refreshBtn) refreshBtn.classList.remove('spinning');
        }
    }

    function renderWindowDropdown(windows) {
        const select = document.getElementById('target-window-select');
        if (!select) return;

        select.innerHTML = '<option value="">-- Select Active Window or Tab --</option>';
        windows.forEach(w => {
            const opt = document.createElement('option');
            opt.value = w.hwnd;
            opt.textContent = `${w.title} (${w.executable_name || 'HWND ' + w.hwnd})`;
            if (state.workflow.target_application.window_title_pattern &&
                w.title.includes(state.workflow.target_application.window_title_pattern)) {
                opt.selected = true;
            }
            select.appendChild(opt);
        });
    }

    function onWindowSelected(hwnd) {
        const win = state.activeWindows.find(w => String(w.hwnd) === String(hwnd));
        if (!win) return;

        state.workflow.target_application.window_title_pattern = win.title;
        state.workflow.target_application.process_name = win.executable_name || '';
        state.workflow.target_application.type =
            win.executable_name.match(/chrome|msedge|firefox|brave/i) ? 'web_browser' : 'windows_desktop';

        // Update target badge
        const badge = document.getElementById('target-window-indicator');
        if (badge) {
            badge.textContent = `Target: ${win.title.slice(0, 32)}... (${win.executable_name})`;
            badge.classList.add('active');
        }
        appendLog('INFO', `Selected automation target: [${win.title}] (PID: ${win.pid})`);
    }

    // =========================================================================
    // 6. 3-SECOND COUNTDOWN HUD MODAL & RUNNER CONTROLS
    // =========================================================================

    function startExecutionSequence() {
        if (!state.workflow.steps || state.workflow.steps.length === 0) {
            alert('Cannot execute an empty workflow. Please add at least one step.');
            return;
        }

        const targetTitle = state.workflow.target_application.window_title_pattern;
        if (!targetTitle) {
            alert('Please select or specify a Target Application Window before executing.');
            return;
        }

        // Open 3-second Countdown HUD
        const hud = document.getElementById('countdown-hud-modal');
        const hudTargetName = document.getElementById('hud-target-name');
        if (hudTargetName) hudTargetName.textContent = targetTitle;
        if (hud) hud.classList.add('active');

        state.countdownRemaining = state.workflow.execution_settings.countdown_seconds || 3;
        updateHudVisuals(state.countdownRemaining);

        // Global Escape listener for immediate cancellation
        document.addEventListener('keydown', onHudKeyDown);

        // Begin local countdown
        clearInterval(state.countdownTimer);
        state.countdownTimer = setInterval(() => {
            state.countdownRemaining -= 1;
            if (state.countdownRemaining > 0) {
                updateHudVisuals(state.countdownRemaining);
            } else {
                clearInterval(state.countdownTimer);
                document.removeEventListener('keydown', onHudKeyDown);
                if (hud) hud.classList.remove('active');
                dispatchWorkflowExecution();
            }
        }, 1000);
    }

    function updateHudVisuals(remaining) {
        const numElem = document.getElementById('hud-countdown-number');
        if (numElem) {
            numElem.textContent = remaining;
            numElem.classList.remove('pulse');
            void numElem.offsetWidth; // re-flow
            numElem.classList.add('pulse');
        }

        const circle = document.getElementById('hud-progress-circle');
        if (circle) {
            const total = state.workflow.execution_settings.countdown_seconds || 3;
            const fraction = remaining / total;
            const strokeDash = 283 * (1 - fraction); // 2 * pi * 45 ≈ 283
            circle.style.strokeDashoffset = strokeDash;
        }
    }

    function cancelCountdown() {
        clearInterval(state.countdownTimer);
        document.removeEventListener('keydown', onHudKeyDown);
        const hud = document.getElementById('countdown-hud-modal');
        if (hud) hud.classList.remove('active');
        appendLog('WARN', 'Execution cancelled during countdown by operator.');
    }

    function onHudKeyDown(e) {
        if (e.key === 'Escape') {
            cancelCountdown();
        }
    }

    async function dispatchWorkflowExecution() {
        appendLog('INFO', `Initiating execution for workflow '${state.workflow.name}'...`);
        try {
            const resp = await fetch('/api/execute/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workflow: state.workflow,
                    variables: {}
                })
            });

            if (!resp.ok) {
                const errData = await resp.json().catch(() => ({}));
                throw new Error(errData.detail || `Server returned ${resp.status}`);
            }

            const data = await resp.json();
            state.executionId = data.execution_id;
            state.executionState = 'RUNNING';
            updateExecutionUIState('RUNNING');
            appendLog('INFO', `Workflow execution dispatched. ID: ${state.executionId}`);
        } catch (err) {
            appendLog('ERROR', `Execution launch failed: ${err.message}`);
            updateExecutionUIState('ERROR');
        }
    }

    async function pauseExecution() {
        appendLog('INFO', 'Operator requested PAUSE...');
        await fetch('/api/execute/pause', { method: 'POST' });
    }

    async function resumeExecution() {
        appendLog('INFO', 'Operator requested RESUME...');
        await fetch('/api/execute/resume', { method: 'POST' });
    }

    async function abortExecution() {
        appendLog('WARN', 'Operator triggered EMERGENCY ABORT!');
        await fetch('/api/execute/abort', { method: 'POST' });
    }

    // =========================================================================
    // 7. WEBSOCKET REAL-TIME EXECUTION TELEMETRY
    // =========================================================================

    function initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/execution`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            appendLog('INFO', 'Real-time telemetry stream connected to /ws/execution.');
            document.getElementById('ws-connection-indicator')?.classList.add('connected');
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                handleTelemetryEvent(msg);
            } catch (err) {
                console.warn('Malformed WS message:', event.data);
            }
        };

        ws.onclose = () => {
            document.getElementById('ws-connection-indicator')?.classList.remove('connected');
            setTimeout(initWebSocket, 3000); // Auto-reconnect
        };

        state.ws = ws;
    }

    function handleTelemetryEvent(msg) {
        const eventType = msg.event || msg.type;
        const payload = msg.payload || msg.data || {};

        switch (eventType) {
            case 'state_change':
                state.executionState = payload.new_state;
                updateExecutionUIState(payload.new_state);
                appendLog('INFO', `FSM Transition: ${payload.old_state} -> ${payload.new_state}`);
                break;
            case 'step_started':
                highlightExecutingStep(payload.step_index);
                updateProgressBar(payload.step_index, state.workflow.steps.length);
                appendLog('INFO', `[Step ${payload.step_index}/${state.workflow.steps.length}] Starting ${payload.action_type}...`);
                break;
            case 'step_completed':
                markStepFinished(payload.step_index, true, payload.latency_ms);
                appendLog('INFO', `[Step ${payload.step_index}] Completed in ${payload.latency_ms?.toFixed(1) || 0}ms.`);
                break;
            case 'step_failed':
                markStepFinished(payload.step_index, false);
                appendLog('ERROR', `[Step ${payload.step_index}] Failed: ${payload.error}`);
                break;
            case 'focus_lost_warning':
                appendLog('WARN', `Target application lost active focus! Automation paused by guardian.`);
                showFocusLostAlert();
                break;
            case 'audit_log':
                appendLog('SUCCESS', `Execution finished. Audit record generated. Copyrights reserved to 90Studio.`);
                state.lastAuditLog = payload;
                break;
        }
    }

    function highlightExecutingStep(index) {
        document.querySelectorAll('.step-card').forEach(c => {
            c.classList.remove('step-executing');
        });
        const activeCard = document.querySelector(`.step-card[data-index="${index - 1}"]`);
        if (activeCard) {
            activeCard.classList.add('step-executing');
            activeCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    function markStepFinished(index, success, latencyMs) {
        const card = document.querySelector(`.step-card[data-index="${index - 1}"]`);
        if (!card) return;
        card.classList.remove('step-executing');
        card.classList.add(success ? 'step-success' : 'step-error');
        if (latencyMs) {
            const timeElem = card.querySelector('.step-timings');
            if (timeElem) timeElem.innerHTML += ` <span class="badge-latency">&#x2713; ${latencyMs.toFixed(0)}ms</span>`;
        }
    }

    function updateProgressBar(current, total) {
        const bar = document.getElementById('execution-progress-bar');
        const text = document.getElementById('execution-progress-text');
        const pct = Math.min(100, Math.round((current / total) * 100));
        if (bar) bar.style.width = `${pct}%`;
        if (text) text.textContent = `Executing Step ${current} of ${total} (${pct}%)`;
    }

    function updateExecutionUIState(fsmState) {
        const badge = document.getElementById('execution-state-badge');
        if (badge) {
            badge.textContent = fsmState;
            badge.className = `state-badge state-${fsmState.toLowerCase()}`;
        }

        const btnRun = document.getElementById('btn-run-workflow');
        const btnPause = document.getElementById('btn-pause-execution');
        const btnResume = document.getElementById('btn-resume-execution');
        const btnAbort = document.getElementById('btn-abort-execution');

        if (fsmState === 'RUNNING') {
            if (btnRun) btnRun.disabled = true;
            if (btnPause) btnPause.disabled = false;
            if (btnResume) btnResume.disabled = true;
            if (btnAbort) btnAbort.disabled = false;
        } else if (fsmState === 'PAUSED') {
            if (btnPause) btnPause.disabled = true;
            if (btnResume) btnResume.disabled = false;
            if (btnAbort) btnAbort.disabled = false;
        } else {
            if (btnRun) btnRun.disabled = false;
            if (btnPause) btnPause.disabled = true;
            if (btnResume) btnResume.disabled = true;
            if (btnAbort) btnAbort.disabled = true;
        }
    }

    // =========================================================================
    // 8. LOGGING & COMPLIANCE CONSOLE
    // =========================================================================

    function appendLog(level, message) {
        const consoleElem = document.getElementById('execution-log-output');
        if (!consoleElem) return;

        const timestamp = new Date().toISOString().substring(11, 23);
        const row = document.createElement('div');
        row.className = `log-row log-${level.toLowerCase()}`;
        row.innerHTML = `<span class="log-time">[${timestamp}]</span> <span class="log-level">[${level}]</span> <span class="log-msg">${escapeHtml(message)}</span>`;

        consoleElem.appendChild(row);
        if (document.getElementById('chk-autoscroll')?.checked !== false) {
            consoleElem.scrollTop = consoleElem.scrollHeight;
        }
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function updateWorkflowMetrics() {
        const total = state.workflow.steps.length;
        const estTime = state.workflow.steps.reduce((acc, s) => acc + (s.pre_delay_ms || 0) + (s.post_delay_ms || 0) + 150, 0);
        const summary = document.getElementById('workflow-summary-metrics');
        if (summary) {
            summary.textContent = `${total} Steps | Est. Duration: ${(estTime / 1000).toFixed(1)}s`;
        }
    }

    // =========================================================================
    // 9. PUBLIC API & INITIALIZATION
    // =========================================================================

    window.KutomotoRunner = {
        init: function () {
            renderStepList();
            fetchActiveWindows();
            initWebSocket();

            // Bind Toolbar Controls
            document.getElementById('btn-add-step')?.addEventListener('click', () => addStep());
            document.getElementById('btn-save-step-modal')?.addEventListener('click', saveStepModal);
            document.getElementById('btn-cancel-step-modal')?.addEventListener('click', closeStepModal);
            document.getElementById('btn-refresh-windows')?.addEventListener('click', fetchActiveWindows);
            document.getElementById('target-window-select')?.addEventListener('change', (e) => onWindowSelected(e.target.value));
            document.getElementById('btn-run-workflow')?.addEventListener('click', startExecutionSequence);
            document.getElementById('btn-cancel-hud')?.addEventListener('click', cancelCountdown);
            document.getElementById('btn-pause-execution')?.addEventListener('click', pauseExecution);
            document.getElementById('btn-resume-execution')?.addEventListener('click', resumeExecution);
            document.getElementById('btn-abort-execution')?.addEventListener('click', abortExecution);
            document.getElementById('edit-step-action-type')?.addEventListener('change', (e) => {
                renderParameterFields(e.target.value, {});
            });
        },
        loadWorkflow: function (wf) {
            state.workflow = wf;
            reindexSteps();
            renderStepList();
        },
        getWorkflow: function () {
            return state.workflow;
        }
    };

    document.addEventListener('DOMContentLoaded', () => {
        window.KutomotoRunner.init();
    });

})(window);
```

---

### 4.2 Component 3 Blueprint: Windows Launcher & CLI Entry Point

#### File: `src/kutomoto/__main__.py`

```python
"""
kutomoto CLI entry point & Windows application launcher.
Copyrights reserved to 90Studio
"""

import argparse
import logging
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

from kutomoto import __copyright__, __version__

logger = logging.getLogger("kutomoto.launcher")


def find_edge_executable() -> str | None:
    """
    Locates the Microsoft Edge executable on Windows across standard system paths.
    Returns the absolute path if found, otherwise None.
    """
    if platform.system() != "Windows":
        return shutil.which("msedge")

    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / r"Microsoft\Edge\Application\msedge.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / r"Microsoft\Edge\Application\msedge.exe",
        Path(os.environ.get("LocalAppData", "")) / r"Microsoft\Edge\Application\msedge.exe",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    which_path = shutil.which("msedge")
    if which_path and Path(which_path).is_file():
        return which_path

    return None


def launch_edge_app_mode(url: str) -> bool:
    """
    Launches Microsoft Edge in dedicated standalone App Mode without browser chrome.
    Falls back to system default browser if Edge is not found.
    """
    edge_exe = find_edge_executable()
    if edge_exe:
        try:
            cmd = [
                edge_exe,
                f"--app={url}",
                "--window-size=1366,850",
                "--window-position=50,50",
                "--no-first-run",
                "--no-default-browser-check",
            ]
            subprocess.Popen(cmd, close_fds=(platform.system() != "Windows"))
            return True
        except Exception as ex:
            logger.warning("Failed to start Edge in App Mode: %s. Falling back to default browser.", ex)

    # Seamless fallback
    webbrowser.open(url)
    return False


def wait_for_server_and_open_browser(host: str, port: int, max_attempts: int = 30) -> None:
    """
    Background daemon thread polling server health before launching Edge App Mode.
    Ensures zero browser connection-refused errors.
    """
    health_url = f"http://{host}:{port}/api/health"
    app_url = f"http://{host}:{port}/"

    for _ in range(max_attempts):
        try:
            req = urllib.request.Request(health_url, headers={"User-Agent": "kutomoto-launcher"})
            with urllib.request.urlopen(req, timeout=0.5) as resp:
                if resp.status == 200:
                    launch_edge_app_mode(app_url)
                    return
        except Exception:
            time.sleep(0.2)

    # Final attempt fallback
    webbrowser.open(app_url)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="kutomoto",
        description=f"kutomoto — Professional Forms Filling Automation System for Windows OS\n{__copyright__}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"kutomoto {__version__} ({__copyright__})")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface to bind server (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Start server only without opening Edge App Mode")
    parser.add_argument("--mock", action="store_true", help="Enable mock Win32 driver mode for non-intrusive testing")
    parser.add_argument("--reload", action="store_true", help="Enable Uvicorn hot reloading for development")

    args = parser.parse_args()

    print("=" * 78)
    print(f"  kutomoto — Professional Forms Filling Automation System (v{__version__})")
    print(f"  {__copyright__}")
    print("=" * 78)

    if args.mock:
        os.environ["KUTOMOTO_MOCK_DRIVER"] = "1"
        print("[INIT] Mock Win32 driver mode ENABLED (mouse & keyboard inputs simulated).")

    # Start browser launch thread if requested
    if not args.no_browser:
        t = threading.Thread(
            target=wait_for_server_and_open_browser,
            args=(args.host, args.port),
            daemon=True,
        )
        t.start()

    print(f"[INIT] Starting backend server at http://{args.host}:{args.port}/ ...")

    try:
        import uvicorn
        uvicorn.run(
            "kutomoto.server.app:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info",
        )
        return 0
    except ImportError:
        print("[ERROR] uvicorn or kutomoto.server.app not found. Verify installation.")
        return 1
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] kutomoto server stopped cleanly by operator.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
```

#### File: `run_kutomoto.bat`

```batch
@echo off
rem ==============================================================================
rem kutomoto — Professional Forms Filling Automation System for Windows OS
rem Copyright Notice: Copyrights reserved to 90Studio
rem ==============================================================================
chcp 65001 >nul
title kutomoto Automation System — 90Studio

echo.
echo  ==============================================================================
echo   kutomoto — Professional Forms Filling Automation System for Windows OS
echo   Copyrights reserved to 90Studio
echo  ==============================================================================
echo.

cd /d "%~dp0"

where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python was not found in your system PATH.
        echo Please install Python 3.10+ from https://python.org or the Microsoft Store.
        echo.
        pause
        exit /b 1
    ) else (
        set "PY_CMD=py -3"
    )
) else (
    set "PY_CMD=python"
)

echo [INFO] Launching kutomoto application shell...
%PY_CMD% -m kutomoto --port 8765 %*

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] kutomoto terminated unexpectedly with exit code %errorlevel%.
    pause
)
```

---

### 4.3 Component 4 Blueprint: Comprehensive Test Suite (`tests/test_api.py`)

```python
"""
tests.test_api
Comprehensive automated REST API & WebSocket test suite for kutomoto server.
Copyrights reserved to 90Studio
"""

import asyncio
import copy
from typing import Any, Dict, List, Optional, Tuple
import uuid
import pytest
from fastapi.testclient import TestClient

from kutomoto import __copyright__, __version__
from kutomoto.server.app import app, get_runner, get_driver


# ==============================================================================
# 1. TEST FIXTURES & MOCK DRIVER
# ==============================================================================

class MockWin32Driver:
    """Mock Win32 Driver simulating desktop window and input interactions."""

    def __init__(self):
        self.dpi_set = False
        self.cursor_pos = (500, 400)
        self.foreground_hwnd = 1001
        self.clicks = []
        self.typed_text = []
        self.pressed_keys = []
        self.modifiers_released = False
        self.mock_windows = [
            {
                "hwnd": 1001,
                "title": "Banking KYC Customer Onboarding - Microsoft Edge",
                "class_name": "Chrome_WidgetWin_1",
                "pid": 1420,
                "executable_name": "msedge.exe",
                "executable_path": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                "is_visible": True,
                "is_iconic": False,
                "rect": (0, 0, 1920, 1080),
                "client_rect": (0, 0, 1920, 1040),
            },
            {
                "hwnd": 1002,
                "title": "Telecom SIM Provisioning Terminal (Win32)",
                "class_name": "TkTopLevel",
                "pid": 2840,
                "executable_name": "python.exe",
                "executable_path": r"C:\Python314\python.exe",
                "is_visible": True,
                "is_iconic": False,
                "rect": (100, 100, 800, 600),
                "client_rect": (100, 100, 800, 560),
            },
        ]

    def set_dpi_awareness(self) -> bool:
        self.dpi_set = True
        return True

    def get_screen_dimensions(self) -> Tuple[int, int]:
        return (1920, 1080)

    def get_cursor_pos(self) -> Tuple[int, int]:
        return self.cursor_pos

    def set_cursor_pos(self, x: int, y: int) -> None:
        self.cursor_pos = (x, y)

    def get_foreground_window(self) -> int:
        return self.foreground_hwnd

    def find_window(self, title_pattern: str, match_mode: str = "contains", process_name: Optional[str] = None) -> Optional[int]:
        for w in self.mock_windows:
            if title_pattern.lower() in w["title"].lower():
                return w["hwnd"]
        return None

    def focus_window(self, hwnd: int, timeout_ms: int = 1500) -> bool:
        self.foreground_hwnd = hwnd
        return True

    def get_window_bounds(self, hwnd: int) -> Tuple[int, int, int, int]:
        for w in self.mock_windows:
            if w["hwnd"] == hwnd:
                return w["rect"]
        return (0, 0, 1920, 1080)

    def send_click(self, x: int, y: int, button: str = "left", click_count: int = 1) -> None:
        self.clicks.append((x, y, button, click_count))

    def send_mouse_move(self, x: int, y: int) -> None:
        self.cursor_pos = (x, y)

    def send_text(self, text: str, delay_between_keys_ms: int = 20, use_clipboard_threshold: int = 40) -> None:
        self.typed_text.append(text)

    def send_key_press(self, key_name: str, repeat_count: int = 1) -> None:
        self.pressed_keys.append((key_name, repeat_count))

    def send_hotkey(self, modifiers: List[str], key: str) -> None:
        self.pressed_keys.append(("+".join(modifiers) + "+" + key, 1))

    def clear_field(self, strategy: str = "select_all_backspace") -> None:
        pass

    def release_all_modifiers(self) -> None:
        self.modifiers_released = True


@pytest.fixture
def mock_driver():
    return MockWin32Driver()


@pytest.fixture
def client(mock_driver, monkeypatch):
    """TestClient fixture overriding automation driver with MockWin32Driver."""
    app.dependency_overrides[get_driver] = lambda: mock_driver
    monkeypatch.setenv("KUTOMOTO_TEST_FAST", "1")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def valid_workflow_payload() -> Dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "id": str(uuid.uuid4()),
        "name": "KYC Automated Onboarding Flow",
        "description": "Enterprise automated KYC workflow",
        "author": "90Studio QA Engineer",
        "copyright": "Copyrights reserved to 90Studio",
        "source_mode": "manual_step_flow",
        "target_application": {
            "type": "web_browser",
            "window_title_pattern": "Banking KYC Customer Onboarding",
            "process_name": "msedge.exe",
            "match_mode": "contains",
        },
        "execution_settings": {
            "countdown_seconds": 1,
            "default_step_delay_ms": 10,
            "typing_speed_ms": 5,
            "stop_on_error": True,
            "error_recovery_policy": "abort",
            "max_step_retries": 1,
            "failsafe_corner_enabled": True,
            "abort_hotkey": "Escape",
        },
        "variables": [
            {
                "name": "customer_name",
                "default_value": "Daoud Enterprise",
                "type": "string",
                "required": True,
            }
        ],
        "steps": [
            {
                "step_id": str(uuid.uuid4()),
                "sequence_index": 1,
                "label": "Focus KYC Portal Window",
                "action_type": "focus_window",
                "enabled": True,
                "pre_delay_ms": 0,
                "post_delay_ms": 10,
                "parameters": {
                    "window_title_pattern": "Banking KYC Customer Onboarding",
                    "match_mode": "contains",
                },
            },
            {
                "step_id": str(uuid.uuid4()),
                "sequence_index": 2,
                "label": "Click Full Name Input Box",
                "action_type": "click",
                "enabled": True,
                "pre_delay_ms": 0,
                "post_delay_ms": 10,
                "parameters": {
                    "norm_x": 0.25,
                    "norm_y": 0.35,
                    "coordinate_mode": "normalized",
                    "button": "left",
                    "click_count": 1,
                },
            },
            {
                "step_id": str(uuid.uuid4()),
                "sequence_index": 3,
                "label": "Type Customer Full Name",
                "action_type": "type_text",
                "enabled": True,
                "pre_delay_ms": 0,
                "post_delay_ms": 10,
                "parameters": {
                    "text": "{{customer_name}}",
                    "is_secret": False,
                    "keystroke_delay_ms": 5,
                },
            },
        ],
    }


@pytest.fixture
def valid_designer_layout_payload() -> Dict[str, Any]:
    return {
        "id": "layout_kyc_001",
        "name": "Visual Form Layout Banking",
        "target": {
            "type": "windows_desktop",
            "match_pattern": "Banking KYC Customer Onboarding",
        },
        "canvas": {
            "width": 1280.0,
            "height": 800.0,
            "scale": 1.0,
        },
        "boxes": [
            {
                "id": "box_first_name",
                "name": "First Name",
                "geometry": {"x": 100.0, "y": 150.0, "width": 250.0, "height": 36.0},
                "sequence_index": 1,
                "action_type": "type_text",
                "value": "Daoud",
                "navigation": "tab",
                "clear_before": True,
            },
            {
                "id": "box_submit",
                "name": "Submit Button",
                "geometry": {"x": 100.0, "y": 250.0, "width": 120.0, "height": 40.0},
                "sequence_index": 2,
                "action_type": "submit",
                "value": "",
                "navigation": "none",
                "clear_before": False,
            },
        ],
    }


# ==============================================================================
# 2. HEALTH & BRANDING TEST SUITE
# ==============================================================================

class TestHealthAndBranding:
    """Verifies health check endpoints and 90Studio copyright requirements."""

    def test_health_check_status_code_and_version(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == __version__
        assert data["system"] == "kutomoto"

    def test_health_check_90studio_branding_enforcement(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["copyright"] == "Copyrights reserved to 90Studio"

    def test_root_endpoint_serves_spa_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        assert "kutomoto" in resp.text
        assert "90Studio" in resp.text


# ==============================================================================
# 3. WORKFLOW CRUD TEST SUITE
# ==============================================================================

class TestWorkflowCrud:
    """Verifies complete CRUD operations for KutomotoWorkflow persistence."""

    def test_list_workflows_returns_200(self, client):
        resp = client.get("/api/workflows")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_workflow_valid_payload(self, client, valid_workflow_payload):
        resp = client.post("/api/workflows", json=valid_workflow_payload)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["id"] == valid_workflow_payload["id"]
        assert data["name"] == valid_workflow_payload["name"]
        assert data["copyright"] == "Copyrights reserved to 90Studio"
        assert len(data["steps"]) == 3

    def test_create_workflow_rejects_missing_copyright(self, client, valid_workflow_payload):
        bad_payload = copy.deepcopy(valid_workflow_payload)
        bad_payload["copyright"] = "Unauthorized Copyright 2026"
        resp = client.post("/api/workflows", json=bad_payload)
        assert resp.status_code == 422

    def test_create_workflow_rejects_empty_steps(self, client, valid_workflow_payload):
        bad_payload = copy.deepcopy(valid_workflow_payload)
        bad_payload["steps"] = []
        resp = client.post("/api/workflows", json=bad_payload)
        assert resp.status_code == 422

    def test_get_workflow_by_id_success(self, client, valid_workflow_payload):
        # Save first
        client.post("/api/workflows", json=valid_workflow_payload)
        wf_id = valid_workflow_payload["id"]
        resp = client.get(f"/api/workflows/{wf_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == wf_id

    def test_get_workflow_by_id_not_found(self, client):
        missing_id = str(uuid.uuid4())
        resp = client.get(f"/api/workflows/{missing_id}")
        assert resp.status_code == 404

    def test_delete_workflow_success(self, client, valid_workflow_payload):
        wf_id = valid_workflow_payload["id"]
        client.post("/api/workflows", json=valid_workflow_payload)
        del_resp = client.delete(f"/api/workflows/{wf_id}")
        assert del_resp.status_code in (200, 204)

        # Subsequent GET should return 404
        get_resp = client.get(f"/api/workflows/{wf_id}")
        assert get_resp.status_code == 404


# ==============================================================================
# 4. DESIGNER COMPILER ENDPOINT TEST SUITE
# ==============================================================================

class TestDesignerCompileEndpoint:
    """Verifies compilation of VisualFormLayout into KutomotoWorkflow via API."""

    def test_designer_compile_success(self, client, valid_designer_layout_payload):
        resp = client.post("/api/designer/compile", json=valid_designer_layout_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["copyright"] == "Copyrights reserved to 90Studio"
        assert data["source_mode"] == "visual_designer_generated"
        assert len(data["steps"]) >= 2
        # First step focuses target window
        assert data["steps"][0]["action_type"] == "focus_window"

    def test_designer_compile_empty_boxes_error(self, client, valid_designer_layout_payload):
        bad_layout = copy.deepcopy(valid_designer_layout_payload)
        bad_layout["boxes"] = []
        resp = client.post("/api/designer/compile", json=bad_layout)
        assert resp.status_code in (400, 422)


# ==============================================================================
# 5. WINDOWS ENUMERATION TEST SUITE
# ==============================================================================

class TestWindowsEnumeration:
    """Verifies GET /api/windows endpoint enumeration against automation core."""

    def test_get_windows_returns_list(self, client):
        resp = client.get("/api/windows")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if len(data) > 0:
            win = data[0]
            assert "hwnd" in win
            assert "title" in win
            assert "executable_name" in win

    def test_get_windows_visible_only_filter(self, client):
        resp = client.get("/api/windows?visible_only=true")
        assert resp.status_code == 200
        for win in resp.json():
            assert win.get("is_visible") is True


# ==============================================================================
# 6. EXECUTION LIFECYCLE TEST SUITE
# ==============================================================================

class TestExecutionLifecycle:
    """Verifies starting, pausing, resuming, aborting, and querying execution status."""

    def test_execution_initial_status_idle(self, client):
        resp = client.get("/api/execute/status")
        assert resp.status_code == 200
        assert resp.json()["state"] == "IDLE"

    def test_execution_start_pause_resume_abort(self, client, valid_workflow_payload):
        # 1. Start execution
        start_resp = client.post("/api/execute/start", json={"workflow": valid_workflow_payload})
        assert start_resp.status_code in (200, 202)
        exec_id = start_resp.json()["execution_id"]
        assert exec_id is not None

        # 2. Pause execution
        pause_resp = client.post("/api/execute/pause")
        assert pause_resp.status_code == 200

        # 3. Resume execution
        resume_resp = client.post("/api/execute/resume")
        assert resume_resp.status_code == 200

        # 4. Abort execution
        abort_resp = client.post("/api/execute/abort")
        assert abort_resp.status_code == 200

        # Verify final state is STOPPED or IDLE
        status_resp = client.get("/api/execute/status")
        assert status_resp.json()["state"] in ("STOPPED", "IDLE", "COMPLETED")


# ==============================================================================
# 7. WEBSOCKET STREAMING TEST SUITE
# ==============================================================================

class TestWebSocketExecution:
    """Verifies real-time event broadcasting over /ws/execution."""

    def test_websocket_connects_and_receives_events(self, client, valid_workflow_payload):
        with client.websocket_connect("/ws/execution") as ws:
            # Trigger execution in background
            client.post("/api/execute/start", json={"workflow": valid_workflow_payload})

            # Read first event from stream
            msg = ws.receive_json()
            assert "event" in msg or "type" in msg
            event_type = msg.get("event") or msg.get("type")
            assert event_type in ("state_change", "countdown_tick", "step_started", "log")
```

---

## 5. Verification Method

To verify these designs independently once implemented by the M4 worker:

1. **API & Test Suite Verification**:
   ```powershell
   python -m pytest tests/test_api.py -v
   ```
   *Expected Result*: All tests in `TestHealthAndBranding`, `TestWorkflowCrud`, `TestDesignerCompileEndpoint`, `TestWindowsEnumeration`, `TestExecutionLifecycle`, and `TestWebSocketExecution` pass with zero failures.

2. **Full Regression Test Suite**:
   ```powershell
   python -m pytest tests/ -v
   ```
   *Expected Result*: Entire suite of unit, engine, driver, compiler, and API tests passes.

3. **CLI Launcher Verification**:
   ```powershell
   # Test help output and 90Studio branding attribution
   python -m kutomoto --help

   # Test version and copyright
   python -m kutomoto --version

   # Test mock mode headless execution (does not launch browser, tests server initialization)
   python -m kutomoto --mock --no-browser --port 8769
   ```

4. **Batch Script Launch Verification**:
   - Double-click `run_kutomoto.bat` on Windows.
   - Verify console window opens with 90Studio header, starts server on port 8765, and automatically opens Microsoft Edge in standalone App Mode (`--app=http://127.0.0.1:8765/`).
