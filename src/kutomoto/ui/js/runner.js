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

        const labelInput = document.getElementById('edit-step-label');
        const actionSelect = document.getElementById('edit-step-action-type');
        const preDelayInput = document.getElementById('edit-step-pre-delay');
        const postDelayInput = document.getElementById('edit-step-post-delay');
        const enabledCheckbox = document.getElementById('edit-step-enabled');

        if (labelInput) labelInput.value = step.label || '';
        if (actionSelect) actionSelect.value = step.action_type;
        if (preDelayInput) preDelayInput.value = step.pre_delay_ms || 0;
        if (postDelayInput) postDelayInput.value = step.post_delay_ms || 0;
        if (enabledCheckbox) enabledCheckbox.checked = step.enabled !== false;

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
                        <input type="text" id="p-title-pattern" class="form-input code-font" value="${escapeHtml(params.window_title_pattern || '')}">
                    </div>
                    <div class="form-group">
                        <label>Process Name (e.g. msedge.exe):</label>
                        <input type="text" id="p-process-name" class="form-input code-font" value="${escapeHtml(params.process_name || '')}">
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
                        <div class="form-group flex-1">
                            <label>Normalized X (0.0 to 1.0):</label>
                            <input type="number" step="0.001" min="0" max="1" id="p-norm-x" class="form-input" value="${params.norm_x ?? 0.5}">
                        </div>
                        <div class="form-group flex-1">
                            <label>Normalized Y (0.0 to 1.0):</label>
                            <input type="number" step="0.001" min="0" max="1" id="p-norm-y" class="form-input" value="${params.norm_y ?? 0.5}">
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group flex-1">
                            <label>Mouse Button:</label>
                            <select id="p-button" class="form-select">
                                <option value="left" ${params.button === 'left' ? 'selected' : ''}>Left</option>
                                <option value="right" ${params.button === 'right' ? 'selected' : ''}>Right</option>
                                <option value="middle" ${params.button === 'middle' ? 'selected' : ''}>Middle</option>
                            </select>
                        </div>
                        <div class="form-group flex-1">
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
                        <div class="form-group flex-1">
                            <label>Keystroke Delay (ms):</label>
                            <input type="number" id="p-key-delay" class="form-input" value="${params.keystroke_delay_ms ?? 20}">
                        </div>
                        <div class="form-group flex-1">
                            <label class="toggle-checkbox" style="margin-top: 20px;">
                                <input type="checkbox" id="p-is-secret" ${params.is_secret ? 'checked' : ''}>
                                <span>Mask in Audit Log (Secret)</span>
                            </label>
                        </div>
                    </div>
                `;
                break;
            case ACTION_TYPES.KEY_PRESS:
                container.innerHTML = `
                    <div class="form-row">
                        <div class="form-group flex-1">
                            <label>Key Name:</label>
                            <input type="text" id="p-key" class="form-input code-font" list="keys-list" value="${escapeHtml(params.key || 'tab')}">
                            <datalist id="keys-list">
                                <option value="tab"><option value="enter"><option value="escape">
                                <option value="backspace"><option value="space"><option value="up">
                                <option value="down"><option value="left"><option value="right">
                            </datalist>
                        </div>
                        <div class="form-group flex-1">
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
                        <input type="text" id="p-hotkey-keys" class="form-input code-font" value="${escapeHtml((params.keys || []).join(', '))}">
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
                        <div class="form-group flex-1">
                            <label>Delta X (Horizontal):</label>
                            <input type="number" id="p-delta-x" class="form-input" value="${params.delta_x || 0}">
                        </div>
                        <div class="form-group flex-1">
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
                        <input type="text" id="p-var-name" class="form-input code-font" value="${escapeHtml(params.variable_name || '')}">
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

        step.label = document.getElementById('edit-step-label')?.value.trim() || step.label;
        step.action_type = document.getElementById('edit-step-action-type')?.value || step.action_type;
        step.pre_delay_ms = parseInt(document.getElementById('edit-step-pre-delay')?.value, 10) || 0;
        step.post_delay_ms = parseInt(document.getElementById('edit-step-post-delay')?.value, 10) || 0;
        step.enabled = document.getElementById('edit-step-enabled')?.checked !== false;

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
    // 5. TARGET WINDOW SELECTOR & EXPLORER
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
            renderWindowsTable(windows);
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
        const pat = (state.workflow && state.workflow.target_application && state.workflow.target_application.window_title_pattern) || '';
        windows.forEach(w => {
            const opt = document.createElement('option');
            opt.value = w.hwnd;
            opt.textContent = `${w.title} (${w.executable_name || 'HWND ' + w.hwnd})`;
            if (pat && w.title) {
                let matched = w.title.toLowerCase().includes(pat.toLowerCase());
                if (!matched && pat !== '.*') {
                    try {
                        matched = new RegExp(pat, 'i').test(w.title);
                    } catch (_) {}
                }
                if (matched) opt.selected = true;
            }
            select.appendChild(opt);
        });
    }

    function renderWindowsTable(windows) {
        const tbody = document.getElementById('windows-table-body');
        const countLabel = document.getElementById('windows-count-label');
        if (!tbody) return;

        if (countLabel) countLabel.textContent = `${windows.length} windows active`;
        tbody.innerHTML = '';

        windows.forEach(w => {
            const tr = document.createElement('tr');
            const wWidth = w.client_rect ? (w.client_rect[2] || 0) : (w.rect ? ((w.rect[2] || 0) - (w.rect[0] || 0)) : 0);
            const wHeight = w.client_rect ? (w.client_rect[3] || 0) : (w.rect ? ((w.rect[3] || 0) - (w.rect[1] || 0)) : 0);
            const dims = (wWidth || wHeight) ? `${wWidth}×${wHeight}` : 'N/A';
            tr.innerHTML = `
                <td><code>${w.hwnd}</code></td>
                <td><strong>${escapeHtml(w.title || '(Untitled)')}</strong></td>
                <td><span class="proc-tag">${escapeHtml(w.executable_name || 'unknown')}</span></td>
                <td><code>${w.pid || 0}</code></td>
                <td>${dims}</td>
                <td>
                    <button class="btn btn-secondary btn-attach-win" data-hwnd="${w.hwnd}">
                        🎯 Attach Target
                    </button>
                </td>
            `;

            tr.querySelector('.btn-attach-win').addEventListener('click', () => {
                onWindowSelected(w.hwnd);
                // Switch to Flow Builder tab
                document.querySelector('[data-tab="tab-builder"]')?.click();
            });

            tbody.appendChild(tr);
        });
    }

    function onWindowSelected(hwnd) {
        const win = state.activeWindows.find(w => String(w.hwnd) === String(hwnd));
        if (!win) return;

        state.workflow.target_application.window_title_pattern = win.title;
        state.workflow.target_application.process_name = win.executable_name || '';
        state.workflow.target_application.match_mode = 'contains';
        state.workflow.target_application.type =
            win.executable_name && win.executable_name.match(/chrome|msedge|firefox|brave/i) ? 'web_browser' : 'windows_desktop';

        // Also update focus_window steps so they focus the newly selected target window
        if (Array.isArray(state.workflow.steps)) {
            state.workflow.steps.forEach(step => {
                if (step.action_type === ACTION_TYPES.FOCUS_WINDOW) {
                    step.parameters = step.parameters || {};
                    step.parameters.window_title_pattern = win.title;
                    step.parameters.process_name = win.executable_name || null;
                    step.parameters.match_mode = 'contains';
                }
            });
            renderStepList();
        }

        // Sync Visual Designer target pattern
        if (window.KutomotoDesigner && window.KutomotoDesigner.layout && window.KutomotoDesigner.layout.target) {
            window.KutomotoDesigner.layout.target.window_title_pattern = win.title;
            window.KutomotoDesigner.layout.target.match_mode = 'contains';
            const titleInput = document.getElementById('target-title-pattern');
            if (titleInput) titleInput.value = win.title;
        }

        // Update target badge
        const badge = document.getElementById('target-window-indicator');
        if (badge) {
            const shortTitle = win.title.length > 28 ? win.title.slice(0, 28) + '...' : win.title;
            badge.innerHTML = `<span class="badge-icon">🎯</span> <span class="target-title">Target: ${escapeHtml(shortTitle)}</span>`;
            badge.classList.add('active');
        }

        // Also sync dropdown
        const select = document.getElementById('target-window-select');
        if (select) select.value = String(hwnd);

        appendLog('INFO', `Selected automation target: [${win.title}] (PID: ${win.pid})`);
    }

    // =========================================================================
    // 5B. PRESET WORKFLOWS & SAMPLE TARGET LAUNCHERS
    // =========================================================================

    let availablePresets = [];

    async function fetchWorkflowPresets() {
        const select = document.getElementById('workflow-preset-select');
        if (!select) return;

        try {
            const [samplesResp, savedResp] = await Promise.all([
                fetch('/api/samples').catch(() => null),
                fetch('/api/workflows').catch(() => null)
            ]);

            const samples = (samplesResp && samplesResp.ok) ? await samplesResp.json() : [];
            const saved = (savedResp && savedResp.ok) ? await savedResp.json() : [];

            const byId = new Map();
            samples.forEach(wf => {
                if (wf && wf.id) byId.set(wf.id, wf);
            });
            saved.forEach(wf => {
                if (wf && wf.id && !byId.has(wf.id)) byId.set(wf.id, wf);
            });

            availablePresets = Array.from(byId.values());
            select.innerHTML = '<option value="">-- Load Sample / Saved Flow --</option>';
            availablePresets.forEach(wf => {
                const opt = document.createElement('option');
                opt.value = wf.id;
                opt.textContent = `${wf.name} (${(wf.steps || []).length} steps)`;
                select.appendChild(opt);
            });
        } catch (err) {
            console.warn('Could not load workflow presets:', err);
        }
    }

    function onPresetSelected(presetId) {
        if (!presetId) return;
        const found = availablePresets.find(w => String(w.id) === String(presetId));
        if (!found) return;
        const clone = JSON.parse(JSON.stringify(found));
        window.KutomotoRunner.loadWorkflow(clone);
        appendLog('INFO', `Loaded workflow preset: '${clone.name}' (${(clone.steps || []).length} steps).`);
        if (window.KutomotoApp) {
            window.KutomotoApp.showToast(`Loaded: ${clone.name}`, 'success');
        }
    }

    async function saveCurrentWorkflow() {
        try {
            const resp = await fetch('/api/workflows', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(state.workflow)
            });
            if (!resp.ok) {
                const errData = await resp.json().catch(() => ({}));
                throw new Error(errData.detail || `HTTP ${resp.status}`);
            }
            const saved = await resp.json();
            state.workflow.id = saved.id;
            appendLog('INFO', `Saved workflow '${saved.name}' (ID: ${saved.id}).`);
            if (window.KutomotoApp) {
                window.KutomotoApp.showToast(`Saved workflow: ${saved.name}`, 'success');
            }
            await fetchWorkflowPresets();
        } catch (err) {
            appendLog('ERROR', `Failed to save workflow: ${err.message}`);
            alert('Failed to save workflow: ' + err.message);
        }
    }

    async function launchSampleWeb() {
        try {
            const resp = await fetch('/api/samples/launch/web', { method: 'POST' });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            appendLog('INFO', `Launched Sample Banking KYC Web Form (${data.url}).`);
            if (window.KutomotoApp) {
                window.KutomotoApp.showToast('Opened Sample Banking KYC Web Form', 'success');
            }
            setTimeout(fetchActiveWindows, 1200);
        } catch (err) {
            appendLog('ERROR', `Failed to launch sample web form: ${err.message}`);
        }
    }

    async function launchSampleDesktop() {
        try {
            const resp = await fetch('/api/samples/launch/desktop', { method: 'POST' });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            appendLog('INFO', 'Launched Sample Telecom SIM Provisioning Desktop Form.');
            if (window.KutomotoApp) {
                window.KutomotoApp.showToast('Opened Sample Telecom SIM Desktop Form', 'success');
            }
            setTimeout(fetchActiveWindows, 1200);
        } catch (err) {
            appendLog('ERROR', `Failed to launch sample desktop form: ${err.message}`);
        }
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

        // Switch to Execution Console tab
        document.querySelector('[data-tab="tab-console"]')?.click();

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
            void numElem.offsetWidth;
            numElem.classList.add('pulse');
        }

        const circle = document.getElementById('hud-progress-circle');
        if (circle) {
            const total = state.workflow.execution_settings.countdown_seconds || 3;
            const fraction = remaining / total;
            const strokeDash = 283 * (1 - fraction);
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
            const workflowPayload = JSON.parse(JSON.stringify(state.workflow));
            if (workflowPayload.execution_settings) {
                workflowPayload.execution_settings.countdown_seconds = 0;
            }
            const resp = await fetch('/api/execute/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workflow: workflowPayload,
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
            const lbl = document.getElementById('connection-status-label');
            if (lbl) lbl.textContent = 'Engine Connected';
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
            const lbl = document.getElementById('connection-status-label');
            if (lbl) lbl.textContent = 'Reconnecting...';
            setTimeout(initWebSocket, 3000);
        };

        state.ws = ws;
    }

    function handleTelemetryEvent(msg) {
        const eventType = msg.event || msg.type;
        const payload = msg.payload || msg.data || msg;

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
                appendLog('WARN', 'Target application lost active focus! Automation paused by guardian.');
                break;
            case 'audit_log':
            case 'execution_completed':
                appendLog('SUCCESS', 'Execution finished. Audit record generated. Copyrights reserved to 90Studio.');
                updateExecutionUIState('COMPLETED');
                updateProgressBar(state.workflow.steps.length, state.workflow.steps.length);
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
            if (timeElem && !timeElem.querySelector('.badge-latency')) {
                timeElem.innerHTML += ` <span class="badge-latency">&#x2713; ${latencyMs.toFixed(0)}ms</span>`;
            }
        }
    }

    function updateProgressBar(current, total) {
        const bar = document.getElementById('execution-progress-bar');
        const text = document.getElementById('execution-progress-text');
        const pct = Math.min(100, Math.round((current / (total || 1)) * 100));
        if (bar) bar.style.width = `${pct}%`;
        if (text) text.textContent = `Executing Step ${current} of ${total} (${pct}%)`;
    }

    function updateExecutionUIState(fsmState) {
        const badge = document.getElementById('execution-state-badge');
        if (badge) {
            badge.textContent = fsmState;
            badge.className = `state-badge state-${fsmState.toLowerCase()}`;
        }

        const footerState = document.getElementById('footer-engine-state');
        if (footerState) footerState.textContent = `Engine Status: ${fsmState}`;

        const btnRun = document.getElementById('btn-run-workflow');
        const btnPause = document.getElementById('btn-pause-execution');
        const btnResume = document.getElementById('btn-resume-execution');
        const btnAbort = document.getElementById('btn-abort-execution');

        if (fsmState === 'RUNNING' || fsmState === 'COUNTDOWN') {
            if (btnRun) btnRun.disabled = true;
            if (btnPause) btnPause.disabled = false;
            if (btnResume) btnResume.disabled = true;
            if (btnAbort) btnAbort.disabled = false;
        } else if (fsmState === 'PAUSED') {
            if (btnRun) btnRun.disabled = true;
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
            fetchWorkflowPresets();
            initWebSocket();

            // Bind Toolbar Controls
            document.getElementById('btn-add-step')?.addEventListener('click', () => addStep());
            document.getElementById('workflow-preset-select')?.addEventListener('change', (e) => onPresetSelected(e.target.value));
            document.getElementById('btn-save-workflow')?.addEventListener('click', saveCurrentWorkflow);
            document.getElementById('btn-launch-sample-web')?.addEventListener('click', launchSampleWeb);
            document.getElementById('btn-launch-sample-desktop')?.addEventListener('click', launchSampleDesktop);
            document.getElementById('btn-save-step-modal')?.addEventListener('click', saveStepModal);
            document.getElementById('btn-cancel-step-modal')?.addEventListener('click', closeStepModal);
            document.getElementById('btn-cancel-step-modal-top')?.addEventListener('click', closeStepModal);
            document.getElementById('btn-refresh-windows')?.addEventListener('click', fetchActiveWindows);
            document.getElementById('btn-refresh-windows-tab')?.addEventListener('click', fetchActiveWindows);
            document.getElementById('target-window-select')?.addEventListener('change', (e) => onWindowSelected(e.target.value));
            document.getElementById('btn-run-workflow')?.addEventListener('click', startExecutionSequence);
            document.getElementById('btn-cancel-hud')?.addEventListener('click', cancelCountdown);
            document.getElementById('btn-pause-execution')?.addEventListener('click', pauseExecution);
            document.getElementById('btn-resume-execution')?.addEventListener('click', resumeExecution);
            document.getElementById('btn-abort-execution')?.addEventListener('click', abortExecution);
            document.getElementById('btn-clear-console')?.addEventListener('click', () => {
                const out = document.getElementById('execution-log-output');
                if (out) out.innerHTML = '<div class="log-watermark">kutomoto Automation Studio — Copyrights reserved to 90Studio</div>';
            });
            document.getElementById('edit-step-action-type')?.addEventListener('change', (e) => {
                renderParameterFields(e.target.value, {});
            });

            // Windows table search filter
            document.getElementById('windows-search-input')?.addEventListener('input', (e) => {
                const query = e.target.value.toLowerCase();
                const filtered = state.activeWindows.filter(w =>
                    (w.title && w.title.toLowerCase().includes(query)) ||
                    (w.executable_name && w.executable_name.toLowerCase().includes(query))
                );
                renderWindowsTable(filtered);
            });
        },
        loadWorkflow: function (wf) {
            state.workflow = wf;
            reindexSteps();
            renderStepList();
            if (wf.target_application && wf.target_application.window_title_pattern) {
                const pat = wf.target_application.window_title_pattern;
                const badge = document.getElementById('target-window-indicator');
                if (badge) {
                    badge.innerHTML = `<span class="badge-icon">🎯</span> <span class="target-title">Target: ${escapeHtml(pat.slice(0, 28))}</span>`;
                    badge.classList.add('active');
                }
                const titleInput = document.getElementById('target-title-pattern');
                if (titleInput) titleInput.value = pat;
            }
            if (state.activeWindows && state.activeWindows.length > 0) {
                renderWindowDropdown(state.activeWindows);
            }
        },
        getWorkflow: function () {
            return state.workflow;
        },
        startExecutionSequence: startExecutionSequence,
        startExecutionWithWorkflow: function (wf) {
            this.loadWorkflow(wf);
            startExecutionSequence();
        }
    };

    document.addEventListener('DOMContentLoaded', () => {
        window.KutomotoRunner.init();
    });

})(window);
