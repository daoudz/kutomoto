# Architectural Analysis & UI Blueprint: Visual Form Designer UI (m4_explorer_2)

**Product**: kutomoto — Professional Forms Filling Automation System for Windows OS  
**Copyright**: Copyrights reserved to 90Studio  
**Author**: m4_explorer_2 (Frontend & Canvas Visual Designer Exploration Agent)  
**Date**: 2026-11-05  

---

## 1. Observation

### 1.1 Requirements & Context Mapping
- **Original Request Requirements**:
  - **R1 & R4**: Enterprise-grade UI suitable for business, banking, and telecom; branded as **kutomoto** with attribution `"Copyrights reserved to 90Studio"`.
  - **R2**: Visual form designer allowing operators to draw form boxes, define sequences, configure values, and automatically generate executable action workflows.
  - **R3**: Step-by-step action workflow creation and execution across open web browser pages and Windows desktop applications.
- **Master Specification (`docs/SPECIFICATION.md`)**:
  - **Section 5.1 (Epic 1: US-VFD)**:
    - `US-VFD-01`: Interactive canvas bounding box creation (mouse drag, sub-10px click discard, active selection border, 8 resize handles, sequence badge `#1`, property inspector update).
    - `US-VFD-02`: Visual box sequencing & reordering (changing sequence index dynamically updates ranks without gaps or duplicate numbers).
    - `US-VFD-03`: Field Property Inspector (label, action type, static text / dynamic variable, post-entry navigation action: Tab/Enter/None, clear before typing, force click).
    - `US-VFD-04`: Backdrop screenshot underlay (loading form PNG/JPEG screenshot, canvas dimensions adjusting to image resolution, transparent high-contrast box overlays).
  - **Section 7.1 & 7.2 (Canvas & Box Model)**:
    - 8 resize handles: $NW, N, NE, E, SE, S, SW, W$ with constraints $W \ge 24\text{px}$, $H \ge 16\text{px}$.
    - Magnetic snap: 8px/16px grid snap and $\pm 4\text{px}$ edge alignment guides.
    - Dual-coordinate resolution independence: Canvas pixels $(x, y, w, h)$ normalized to $[0.0, 1.0]$.
    - Formal JSON schema: `VisualFormLayout` with mandatory copyright `"Copyrights reserved to 90Studio"`.
  - **Section 8 (Visual-to-Workflow Compilation Engine)**:
    - 5-pass compilation algorithm in `src/kutomoto/designer/compiler.py`:
      - Pass 1: Geometry & duplicate ID validation.
      - Pass 2: Sequence ordering (explicit sequence index priority, spatial band sort fallback with $24\text{px}$ vertical tolerance).
      - Pass 3: Dual-coordinate normalization.
      - Pass 4: Action step synthesis (Focus Window header, Click anchor, Clear, Type Text, Navigation key).
      - Pass 5: Peephole optimization (redundant focus elimination, click-to-tab, delay collapsing).
- **Architecture & Portability Constraints (`PROJECT.md`)**:
  - Shell: Microsoft Edge App Mode (`msedge.exe --app=http://127.0.0.1:8765`) or standard browser.
  - Presentation Layer: HTML5 / Modern CSS3 / Vanilla ES6 JavaScript — **No heavy bundlers (Webpack, Vite, npm) required**, ensuring zero-dependency instant startup from Python.
  - Code Layout:
    - `src/kutomoto/ui/index.html`: Single Page App shell with 5 tab views.
    - `src/kutomoto/ui/css/kutomoto.css`: Enterprise dark slate theme.
    - `src/kutomoto/ui/js/designer.js`: HTML5 Canvas visual form designer.
    - `src/kutomoto/ui/js/runner.js`: Flow builder and countdown HUD (coordinated with `m4_explorer_3`).
    - `src/kutomoto/ui/js/app.js`: Tab switching and WebSocket notifications (coordinated with `m4_explorer_1`).

---

## 2. Logic Chain

1. **Enterprise Single Page App Shell (`index.html`)**:
   - Enterprise operators require a single unified dashboard that allows designing visually, inspecting step sequences, monitoring live execution, and discovering target windows.
   - Therefore, `index.html` is structured around a top enterprise header (displaying kutomoto branding, 90Studio copyright, connection status, and active target), a responsive 5-tab navigation bar (`Visual Designer`, `Flow Builder`, `Execution Console`, `Target Windows`, `Settings`), and modular tab panel sections.
2. **Design Tokens & Aesthetic Palette (`kutomoto.css`)**:
   - Business, banking, and telecom environments demand high legibility, clean visual hierarchy, and an authoritative dark enterprise palette (dark slate `#0d1117`, navy surfaces `#161b22`, corporate blue accents `#2f81f7`, status badges `#8957e5` purple, `#238636` green, `#f85149` red).
   - High DPI displays require crisp 1px borders, subtle drop shadows, and high contrast text (`#f0f6fc` on dark backgrounds).
3. **HTML5 Canvas Coordinate & DPI Independence (`designer.js`)**:
   - The canvas element has two coordinate systems: CSS layout pixels (`getBoundingClientRect()`) and internal pixel buffer resolution (`canvas.width`, `canvas.height`).
   - To eliminate cursor offset under CSS scaling, zooming, or high-DPI screens, all mouse event coordinates must be converted via:
     $$\text{CanvasX} = (e.\text{clientX} - \text{rect.left}) \times \frac{\text{canvas.width}}{\text{rect.width}}$$
     $$\text{CanvasY} = (e.\text{clientY} - \text{rect.top}) \times \frac{\text{canvas.height}}{\text{rect.height}}$$
   - Exported layouts map canvas pixels directly into normalized coordinates $[0.0, 1.0]$, ensuring target forms execute reliably across disparate monitor resolutions.
4. **Interactive Box Creation & Clamping**:
   - Sub-10px accidental clicks are discarded (US-VFD-01).
   - Placed boxes are clamped to canvas boundaries ($x \ge 0, y \ge 0, x+w \le W_c, y+h \le H_c$) and enforced minimum dimensions ($W \ge 24\text{px}, H \ge 16\text{px}$).
5. **8 Resize Handles & Cursor Feedback**:
   - Eight handles ($NW, N, NE, E, SE, S, SW, W$) are rendered on the selected box.
   - Hit detection utilizes an $8\times 8\text{px}$ target area around each handle point.
   - Cursor styling dynamically switches between `nwse-resize`, `nesw-resize`, `ns-resize`, `ew-resize`, `move`, `crosshair`, and `default`.
6. **Contiguous Sequence Re-Indexing**:
   - When a sequence rank is updated from $S_{\text{old}}$ to $S_{\text{new}}$, adjacent boxes are shifted up or down, preserving a continuous $1 \dots N$ sequence without duplicates or gaps (US-VFD-02).
   - A "Spatial Auto-Order" feature performs Pass-2 2D spatial band sorting (Y-proximity band grouping at $24\text{px}$ tolerance, then X-sorting) directly in the UI.
7. **Bidirectional Property Inspector**:
   - Selecting a box updates sidebar inputs (Name, Label, Action Type, Value, Navigation, Clear Before, Force Click, Delays).
   - Editing any sidebar control mutates the active box model and immediately schedules a canvas re-render.
8. **Compiler & Backend Integration**:
   - Clicking "Compile to Workflow" packages the canvas state into a valid `VisualFormLayout` JSON and posts to `/api/designer/compile`.
   - The response (`KutomotoWorkflow`) is presented in a modal inspection dialog with options to run immediately, export to JSON, or load into the Step-by-Step Flow Builder.

---

## 3. Caveats

1. **Backdrop Image Size & Aspect Ratio**:
   - Target form screenshots can range from $800\times 600$ to $3840\times 2160$ (4K). The canvas container must support overflow scrolling and zoom controls (`Fit to Window`, `100%`, `150%`) so large screenshots do not distort or break layout boundaries.
2. **Keyboard Accessibility**:
   - While canvas interaction is primarily mouse-driven, standard keyboard shortcuts must be supported: `Delete` / `Backspace` to remove selected box, `Esc` to deselect, and `Arrow keys` (with `Shift` for 8px increments) for fine-grained nudging.
3. **Peephole Optimization Presets**:
   - In `designer.js`, `click_to_tab` is default `false` for standard coordinate-targeted execution, while `force_click` on individual boxes ensures coordinates are clicked even if tab navigation is enabled.
4. **Scope & File Ownership**:
   - This blueprint defines the architecture and full implementation specifications for `index.html`, `kutomoto.css`, and `designer.js`.
   - Backend endpoints (`/api/designer/compile`) are designed by `m4_explorer_1`.
   - Flow Builder, Countdown HUD, and test suite are designed by `m4_explorer_3`.

---

## 4. Conclusion: Production-Ready Blueprints

### 4.1 UI Component Architecture Overview

```
src/kutomoto/ui/
├── index.html          # Enterprise SPA Shell (Header, 5 Tabs, Modals, Branding)
├── css/
│   └── kutomoto.css    # Enterprise Theme (Dark slate, corporate blue, handles, badges)
└── js/
    ├── app.js          # Tab routing, WebSocket status, global notifications
    ├── designer.js     # HTML5 Canvas visual designer engine (OOP class)
    └── runner.js       # Flow builder, window selector, countdown HUD & console
```

---

### 4.2 Blueprint 1: `src/kutomoto/ui/index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>kutomoto — Enterprise Form Automation</title>
  <link rel="stylesheet" href="css/kutomoto.css">
</head>
<body class="enterprise-theme">
  <!-- Top Application Header -->
  <header class="app-header">
    <div class="header-brand">
      <div class="logo-mark">
        <svg width="26" height="26" viewBox="0 0 32 32" fill="none">
          <rect width="32" height="32" rx="6" fill="#1f6feb"/>
          <path d="M8 8H13V15L19 8H25L17.5 16.5L25 24H19L13 17.5V24H8V8Z" fill="#ffffff"/>
        </svg>
      </div>
      <div class="brand-text">
        <span class="product-title">kutomoto</span>
        <span class="product-subtitle">Forms Filling Automation System</span>
      </div>
      <span class="legal-badge">Copyrights reserved to 90Studio</span>
    </div>

    <div class="header-status">
      <div class="connection-indicator" id="connection-status">
        <span class="status-dot connected"></span>
        <span class="status-label">Engine Ready</span>
      </div>
      <div class="active-target-badge" id="header-target-badge" title="Active Target Application">
        <span class="badge-icon">🎯</span>
        <span class="target-title">Target: Not Attached</span>
      </div>
    </div>
  </header>

  <!-- Primary Tabbed Navigation -->
  <nav class="app-nav">
    <button class="nav-tab active" data-tab="tab-designer">
      <span class="tab-icon">📐</span>
      <span class="tab-label">Visual Designer</span>
    </button>
    <button class="nav-tab" data-tab="tab-builder">
      <span class="tab-icon">⚡</span>
      <span class="tab-label">Flow Builder</span>
    </button>
    <button class="nav-tab" data-tab="tab-console">
      <span class="tab-icon">🖥️</span>
      <span class="tab-label">Execution Console</span>
    </button>
    <button class="nav-tab" data-tab="tab-windows">
      <span class="tab-icon">🪟</span>
      <span class="tab-label">Target Windows</span>
    </button>
    <button class="nav-tab" data-tab="tab-settings">
      <span class="tab-icon">⚙️</span>
      <span class="tab-label">Settings</span>
    </button>
  </nav>

  <!-- Main Viewport Container -->
  <main class="app-main">
    <!-- ===================================================================== -->
    <!-- TAB 1: VISUAL FORM DESIGNER                                           -->
    <!-- ===================================================================== -->
    <section id="tab-designer" class="tab-panel active">
      <!-- Designer Command Bar -->
      <div class="designer-toolbar">
        <div class="toolbar-group">
          <label class="btn btn-secondary file-upload-btn" title="Load target form screenshot backdrop">
            <span>📷 Load Backdrop</span>
            <input type="file" id="designer-backdrop-input" accept="image/png,image/jpeg,image/webp">
          </label>
          <button id="btn-clear-backdrop" class="btn btn-secondary" title="Remove backdrop screenshot">Clear Image</button>
          <span class="backdrop-dim-label" id="backdrop-dimensions">1024 × 768 px</span>
        </div>

        <div class="toolbar-group">
          <label class="toggle-checkbox" title="Snap to grid">
            <input type="checkbox" id="designer-snap-toggle" checked>
            <span>Snap Grid</span>
          </label>
          <select id="designer-grid-size" class="form-select select-compact">
            <option value="8">8 px</option>
            <option value="16" selected>16 px</option>
            <option value="24">24 px</option>
          </select>
          <button id="btn-auto-sequence" class="btn btn-secondary" title="Sort boxes by 2D spatial reading order">
            <span>🔢 Auto-Sequence</span>
          </button>
        </div>

        <div class="toolbar-group">
          <button id="btn-import-layout" class="btn btn-secondary" title="Import VisualFormLayout JSON">
            <span>📂 Import</span>
            <input type="file" id="designer-import-input" accept=".json" style="display:none">
          </button>
          <button id="btn-export-layout" class="btn btn-secondary" title="Export VisualFormLayout JSON">
            <span>💾 Export</span>
          </button>
          <button id="btn-clear-canvas" class="btn btn-danger" title="Clear all drawn boxes">
            <span>🗑️ Clear All</span>
          </button>
        </div>

        <div class="toolbar-group toolbar-group-right">
          <button id="btn-compile-workflow" class="btn btn-primary btn-glow" title="Compile visual layout to executable action workflow">
            <span>⚡ Compile to Workflow</span>
          </button>
        </div>
      </div>

      <!-- Designer Workspace: Canvas Viewport + Property Inspector -->
      <div class="designer-workspace">
        <!-- Canvas Viewport -->
        <div class="canvas-viewport" id="canvas-viewport">
          <div class="canvas-wrapper" id="canvas-wrapper">
            <canvas id="designer-canvas" width="1024" height="768"></canvas>
          </div>
        </div>

        <!-- Property Inspector Sidebar -->
        <aside class="property-inspector" id="property-inspector">
          <div class="inspector-header">
            <h3>Field Inspector</h3>
            <span class="box-count-badge" id="inspector-box-count">0 boxes</span>
          </div>

          <!-- Empty State (No Box Selected) -->
          <div class="inspector-empty-state" id="inspector-empty">
            <div class="empty-icon">👆</div>
            <p><strong>No field selected</strong></p>
            <p class="muted">Click a box to edit its parameters, or drag on the canvas to draw a new form input box.</p>
          </div>

          <!-- Selected Box Property Editor Form -->
          <div class="inspector-form" id="inspector-form" style="display:none;">
            <div class="form-section-title">
              <span id="selected-box-title">Box Parameters</span>
              <span class="seq-pill" id="selected-seq-pill">#1</span>
            </div>

            <!-- Field Name & Label -->
            <div class="form-group">
              <label for="prop-box-label">Field Label (Display)</label>
              <input type="text" id="prop-box-label" class="form-input" placeholder="e.g. Borrower Legal Name">
            </div>

            <div class="form-group">
              <label for="prop-box-name">Field Identifier (Token)</label>
              <input type="text" id="prop-box-name" class="form-input code-font" placeholder="e.g. borrower_name">
            </div>

            <!-- Execution Sequence Index -->
            <div class="form-row">
              <div class="form-group flex-1">
                <label for="prop-box-seq">Sequence Index</label>
                <input type="number" id="prop-box-seq" class="form-input" min="1" step="1">
              </div>
              <div class="form-group flex-1">
                <label for="prop-box-action">Action Type</label>
                <select id="prop-box-action" class="form-select">
                  <option value="type_text">Type Text</option>
                  <option value="click">Mouse Click</option>
                  <option value="checkbox">Toggle Checkbox</option>
                  <option value="select">Dropdown Select</option>
                  <option value="key_press">Key Press</option>
                  <option value="submit">Submit Button</option>
                  <option value="delay">Settling Delay</option>
                </select>
              </div>
            </div>

            <!-- Value / Static Text Input -->
            <div class="form-group" id="group-prop-value">
              <label for="prop-box-value">Value / Text Payload</label>
              <textarea id="prop-box-value" class="form-textarea" rows="2" placeholder="Text to enter, or key name (e.g. tab, enter)"></textarea>
            </div>

            <!-- Post-Action Navigation -->
            <div class="form-row">
              <div class="form-group flex-1">
                <label for="prop-box-nav">Post Navigation</label>
                <select id="prop-box-nav" class="form-select">
                  <option value="tab">Press Tab</option>
                  <option value="enter">Press Enter</option>
                  <option value="click_next">Click Next</option>
                  <option value="none">None</option>
                </select>
              </div>
              <div class="form-group flex-1">
                <label for="prop-box-post-delay">Post Delay (ms)</label>
                <input type="number" id="prop-box-post-delay" class="form-input" min="0" step="10" value="120">
              </div>
            </div>

            <!-- Toggles: Clear Before, Force Click, Secret -->
            <div class="form-toggles">
              <label class="toggle-checkbox">
                <input type="checkbox" id="prop-box-clear" checked>
                <span>Clear Before Typing (Ctrl+A &rarr; Del)</span>
              </label>
              <label class="toggle-checkbox">
                <input type="checkbox" id="prop-box-force-click">
                <span>Force Click (Even in Tab chain)</span>
              </label>
              <label class="toggle-checkbox">
                <input type="checkbox" id="prop-box-secret">
                <span>Mask as Secret (Password/PIN)</span>
              </label>
            </div>

            <!-- Geometry Readout Card -->
            <div class="geometry-card">
              <div class="geo-title">Geometry &amp; Normalized Coords</div>
              <div class="geo-grid">
                <div><span>X:</span> <strong id="geo-x">0</strong></div>
                <div><span>Y:</span> <strong id="geo-y">0</strong></div>
                <div><span>W:</span> <strong id="geo-w">0</strong></div>
                <div><span>H:</span> <strong id="geo-h">0</strong></div>
                <div><span>Norm X:</span> <strong id="geo-norm-x">0.0000</strong></div>
                <div><span>Norm Y:</span> <strong id="geo-norm-y">0.0000</strong></div>
                <div><span>Norm W:</span> <strong id="geo-norm-w">0.0000</strong></div>
                <div><span>Norm H:</span> <strong id="geo-norm-h">0.0000</strong></div>
              </div>
            </div>

            <!-- Box Actions: Duplicate & Delete -->
            <div class="inspector-actions">
              <button id="btn-duplicate-box" class="btn btn-secondary flex-1">Duplicate</button>
              <button id="btn-delete-box" class="btn btn-danger flex-1">Delete Field</button>
            </div>
          </div>

          <!-- Layout Global Target Application Settings (Collapsible) -->
          <details class="layout-meta-accordion">
            <summary>Target &amp; Compiler Options</summary>
            <div class="accordion-body">
              <div class="form-group">
                <label for="layout-name">Layout Name</label>
                <input type="text" id="layout-name" class="form-input" value="Enterprise Form Layout">
              </div>
              <div class="form-group">
                <label for="target-title-pattern">Target Window Pattern (Regex)</label>
                <input type="text" id="target-title-pattern" class="form-input code-font" value=".*">
              </div>
              <div class="form-group">
                <label for="target-app-type">Target Platform</label>
                <select id="target-app-type" class="form-select">
                  <option value="any">Any (Browser or Desktop)</option>
                  <option value="web_browser">Web Browser</option>
                  <option value="windows_desktop">Windows Desktop</option>
                </select>
              </div>
              <label class="toggle-checkbox">
                <input type="checkbox" id="opt-click-to-tab">
                <span>Peephole: Click-to-Tab Conversion</span>
              </label>
            </div>
          </details>
        </aside>
      </div>
    </section>

    <!-- TAB 2: STEP-BY-STEP FLOW BUILDER (Managed by runner.js) -->
    <section id="tab-builder" class="tab-panel">
      <div class="panel-placeholder" id="flow-builder-container">
        <!-- Rendered by runner.js -->
      </div>
    </section>

    <!-- TAB 3: EXECUTION CONSOLE (Managed by runner.js) -->
    <section id="tab-console" class="tab-panel">
      <div class="panel-placeholder" id="execution-console-container">
        <!-- Rendered by runner.js -->
      </div>
    </section>

    <!-- TAB 4: TARGET WINDOWS INSPECTOR (Managed by runner.js) -->
    <section id="tab-windows" class="tab-panel">
      <div class="panel-placeholder" id="target-windows-container">
        <!-- Rendered by runner.js -->
      </div>
    </section>

    <!-- TAB 5: SYSTEM SETTINGS -->
    <section id="tab-settings" class="tab-panel">
      <div class="settings-card">
        <h3>Execution &amp; Safety Configuration</h3>
        <p class="muted">Global defaults applied during workflow execution.</p>
        <div class="form-group">
          <label>Default Step Settling Delay (ms)</label>
          <input type="number" id="setting-step-delay" class="form-input" value="120" min="10" max="5000">
        </div>
        <div class="form-group">
          <label>Typing Speed (Keystroke Delay ms)</label>
          <input type="number" id="setting-typing-speed" class="form-input" value="20" min="1" max="500">
        </div>
        <div class="form-group">
          <label>Safety Abort Hotkey</label>
          <input type="text" class="form-input" value="Escape" disabled>
        </div>
        <div class="form-group">
          <label>Failsafe Screen Corner</label>
          <input type="text" class="form-input" value="Top-Left (0, 0)" disabled>
        </div>
      </div>
    </section>
  </main>

  <!-- Compilation Result Modal -->
  <div class="modal-overlay" id="compile-modal" style="display:none;">
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title-group">
          <span class="modal-badge-success">Compilation Successful</span>
          <h3 id="compile-modal-title">Compiled Workflow Generated</h3>
        </div>
        <button class="modal-close-btn" id="btn-close-compile-modal">&times;</button>
      </div>
      <div class="modal-body">
        <div class="compile-stats" id="compile-stats-bar">
          <div class="stat-pill"><span id="stat-step-count">0</span> Steps</div>
          <div class="stat-pill"><span id="stat-target-name">Target Pattern</span></div>
          <div class="stat-pill"><span id="stat-source-mode">visual_designer_generated</span></div>
        </div>
        <pre class="code-preview" id="compile-json-preview"><code></code></pre>
      </div>
      <div class="modal-footer">
        <button id="btn-download-workflow-json" class="btn btn-secondary">💾 Save Workflow JSON</button>
        <button id="btn-load-in-builder" class="btn btn-secondary">⚡ Open in Flow Builder</button>
        <button id="btn-run-compiled-workflow" class="btn btn-primary btn-glow">▶ Run in Execution Console</button>
      </div>
    </div>
  </div>

  <!-- Global Toast Notification Hub -->
  <div class="toast-hub" id="toast-hub"></div>

  <!-- Application Footer -->
  <footer class="app-footer">
    <div class="footer-left">
      <span>kutomoto Automation Studio v1.0.0</span>
    </div>
    <div class="footer-center">
      <strong>Copyrights reserved to 90Studio</strong>
    </div>
    <div class="footer-right">
      <span id="footer-engine-state">Engine Status: Idle</span>
    </div>
  </footer>

  <!-- Core JavaScript Modules (No bundler required) -->
  <script src="js/designer.js"></script>
  <script src="js/runner.js"></script>
  <script src="js/app.js"></script>
</body>
</html>
```

---

### 4.3 Blueprint 2: `src/kutomoto/ui/css/kutomoto.css`

```css
/* ==============================================================================
   kutomoto Enterprise UI Stylesheet
   Modern Enterprise Theme (Dark Slate / Corporate Blue / High Contrast)
   Copyrights reserved to 90Studio
   ============================================================================== */

:root {
  /* Surface Colors */
  --bg-app: #090d16;
  --bg-header: #0d1117;
  --bg-surface: #161b22;
  --bg-surface-hover: #1f242c;
  --bg-surface-elevated: #21262d;
  --bg-canvas-backdrop: #05070a;

  /* Border & Dividers */
  --border-subtle: #21262d;
  --border-default: #30363d;
  --border-focus: #58a6ff;
  --border-glow: rgba(47, 129, 247, 0.4);

  /* Typography Colors */
  --text-primary: #f0f6fc;
  --text-secondary: #8b949e;
  --text-muted: #6e7681;
  --text-code: #79c0ff;

  /* Accent Branding */
  --accent-blue: #1f6feb;
  --accent-blue-hover: #388bfd;
  --accent-blue-active: #1f6feb;
  --accent-blue-subtle: rgba(31, 111, 235, 0.15);

  --accent-green: #238636;
  --accent-green-hover: #2ea043;
  --accent-green-subtle: rgba(46, 160, 67, 0.18);

  --accent-red: #da3633;
  --accent-red-hover: #f85149;
  --accent-red-subtle: rgba(218, 54, 51, 0.18);

  --accent-purple: #8957e5;
  --accent-purple-subtle: rgba(137, 87, 229, 0.2);

  --accent-amber: #d29922;

  /* Shadows & Radius */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.4);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.5);
  --shadow-lg: 0 12px 32px rgba(0, 0, 0, 0.7);

  /* Fonts */
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
}

/* Global Reset */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body.enterprise-theme {
  background-color: var(--bg-app);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 13px;
  line-height: 1.5;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  user-select: none;
}

/* Header */
.app-header {
  background-color: var(--bg-header);
  border-bottom: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 48px;
  flex-shrink: 0;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-text {
  display: flex;
  flex-direction: column;
}

.product-title {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: #ffffff;
}

.product-subtitle {
  font-size: 10px;
  color: var(--text-secondary);
}

.legal-badge {
  background: var(--bg-surface-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 11px;
  padding: 2px 8px;
  margin-left: 8px;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 16px;
}

.connection-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--accent-red);
}

.status-dot.connected {
  background-color: var(--accent-green);
  box-shadow: 0 0 8px var(--accent-green);
}

.active-target-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  padding: 3px 10px;
  border-radius: var(--radius-md);
  font-size: 11px;
  color: var(--text-secondary);
}

/* Navigation Tabs */
.app-nav {
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  padding: 0 12px;
  height: 38px;
  flex-shrink: 0;
  gap: 4px;
}

.nav-tab {
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
  height: 100%;
  padding: 0 14px;
  transition: all 0.15s ease-in-out;
}

.nav-tab:hover {
  color: var(--text-primary);
  background-color: var(--bg-surface-hover);
}

.nav-tab.active {
  color: var(--text-primary);
  border-bottom-color: var(--accent-blue);
  background-color: var(--bg-surface-elevated);
}

/* Main Viewport */
.app-main {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}

.tab-panel {
  display: none;
  flex: 1;
  width: 100%;
  height: 100%;
}

.tab-panel.active {
  display: flex;
  flex-direction: column;
}

/* ==============================================================================
   VISUAL FORM DESIGNER LAYOUT
   ============================================================================== */

.designer-toolbar {
  background-color: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 16px;
  height: 44px;
  flex-shrink: 0;
  gap: 12px;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-group-right {
  margin-left: auto;
}

.backdrop-dim-label {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  margin-left: 4px;
}

/* Buttons */
.btn {
  background-color: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
  height: 28px;
  padding: 0 10px;
  text-decoration: none;
  transition: background-color 0.15s, border-color 0.15s;
}

.btn:hover {
  background-color: var(--bg-surface-hover);
  border-color: var(--border-focus);
}

.btn-primary {
  background-color: var(--accent-blue);
  border-color: var(--accent-blue);
  color: #ffffff;
}

.btn-primary:hover {
  background-color: var(--accent-blue-hover);
  border-color: var(--accent-blue-hover);
}

.btn-glow {
  box-shadow: 0 0 10px var(--border-glow);
}

.btn-danger {
  background-color: var(--accent-red-subtle);
  border-color: var(--accent-red);
  color: #ff7b72;
}

.btn-danger:hover {
  background-color: var(--accent-red);
  color: #ffffff;
}

.file-upload-btn input[type="file"] {
  display: none;
}

/* Form Controls */
.form-input, .form-select, .form-textarea {
  background-color: var(--bg-app);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-family: inherit;
  font-size: 12px;
  padding: 5px 8px;
  width: 100%;
}

.form-input:focus, .form-select:focus, .form-textarea:focus {
  outline: none;
  border-color: var(--border-focus);
  box-shadow: 0 0 0 2px var(--border-glow);
}

.select-compact {
  height: 28px;
  padding: 0 6px;
  width: auto;
}

.code-font {
  font-family: var(--font-mono);
}

.toggle-checkbox {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 12px;
  color: var(--text-secondary);
}

.toggle-checkbox input[type="checkbox"] {
  accent-color: var(--accent-blue);
  width: 14px;
  height: 14px;
}

/* Designer Workspace */
.designer-workspace {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}

/* Canvas Viewport */
.canvas-viewport {
  flex: 1;
  background-color: var(--bg-canvas-backdrop);
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  position: relative;
  /* Dark checkerboard pattern for transparent canvas backdrop */
  background-image:
    linear-gradient(45deg, #0c1017 25%, transparent 25%),
    linear-gradient(-45deg, #0c1017 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #0c1017 75%),
    linear-gradient(-45deg, transparent 75%, #0c1017 75%);
  background-size: 20px 20px;
  background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
}

.canvas-wrapper {
  background-color: #0d1117;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-lg);
  line-height: 0;
  position: relative;
}

#designer-canvas {
  display: block;
  cursor: crosshair;
}

/* Property Inspector Sidebar */
.property-inspector {
  width: 340px;
  background-color: var(--bg-surface);
  border-left: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow-y: auto;
  user-select: auto;
}

.inspector-header {
  border-bottom: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
}

.inspector-header h3 {
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
}

.box-count-badge {
  background: var(--bg-surface-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  color: var(--text-muted);
  font-size: 11px;
  padding: 1px 8px;
}

.inspector-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  text-align: center;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 32px;
  margin-bottom: 12px;
}

.inspector-form {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.seq-pill {
  background: var(--accent-purple);
  color: #ffffff;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-group label {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
}

.form-row {
  display: flex;
  gap: 8px;
}

.flex-1 {
  flex: 1;
}

.form-toggles {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 0;
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}

/* Geometry Card */
.geometry-card {
  background: var(--bg-app);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
}

.geo-title {
  font-size: 10px;
  text-transform: uppercase;
  color: var(--text-muted);
  font-weight: 600;
  margin-bottom: 6px;
}

.geo-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px 8px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-secondary);
}

.geo-grid strong {
  color: var(--text-code);
}

.inspector-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.layout-meta-accordion {
  border-top: 1px solid var(--border-default);
  margin-top: auto;
}

.layout-meta-accordion summary {
  padding: 10px 16px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  background: var(--bg-surface-elevated);
}

.layout-meta-accordion summary:hover {
  color: var(--text-primary);
}

.accordion-body {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--bg-surface);
}

/* Modal Overlay */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 720px;
  max-width: 90vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  border-bottom: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
}

.modal-badge-success {
  background: var(--accent-green-subtle);
  border: 1px solid var(--accent-green);
  color: #3fb950;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
}

.modal-header h3 {
  font-size: 15px;
  color: #ffffff;
  margin-top: 2px;
}

.modal-close-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 20px;
  padding: 4px;
}

.modal-close-btn:hover {
  color: #ffffff;
}

.modal-body {
  padding: 16px 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.compile-stats {
  display: flex;
  gap: 8px;
}

.stat-pill {
  background: var(--bg-surface-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 4px 10px;
  font-size: 11px;
  color: var(--text-secondary);
}

.stat-pill strong, .stat-pill span {
  color: var(--text-code);
  font-weight: 600;
}

.code-preview {
  background: var(--bg-app);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 12px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: #c9d1d9;
  max-height: 380px;
  overflow: auto;
  white-space: pre;
}

.modal-footer {
  border-top: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 12px 20px;
  gap: 10px;
}

/* Toast Notifications */
.toast-hub {
  position: fixed;
  bottom: 34px;
  right: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 2000;
  pointer-events: none;
}

.toast {
  background: var(--bg-surface-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  color: var(--text-primary);
  font-size: 12px;
  padding: 8px 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  pointer-events: auto;
  animation: toast-in 0.2s ease-out;
}

.toast.toast-success { border-left: 3px solid var(--accent-green); }
.toast.toast-error { border-left: 3px solid var(--accent-red); }
.toast.toast-info { border-left: 3px solid var(--accent-blue); }

@keyframes toast-in {
  from { transform: translateY(10px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

/* Footer */
.app-footer {
  background: var(--bg-header);
  border-top: 1px solid var(--border-default);
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  font-size: 11px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.footer-center strong {
  color: var(--text-secondary);
}
```

---

### 4.4 Blueprint 3: `src/kutomoto/ui/js/designer.js`

```javascript
/**
 * kutomoto.ui.js.designer
 * HTML5 Canvas Visual Form Designer Engine
 * Copyrights reserved to 90Studio
 */

class KutomotoVisualDesigner {
  /**
   * Initializes the visual canvas designer engine.
   * @param {Object} options Configuration options
   */
  constructor(options = {}) {
    this.canvas = document.getElementById(options.canvasId || 'designer-canvas');
    this.ctx = this.canvas.getContext('2d');
    this.viewport = document.getElementById('canvas-viewport');

    // Layout Metadata conforming to VisualFormLayout schema
    this.layout = {
      schema_version: '1.0.0',
      id: crypto.randomUUID(),
      name: 'Enterprise Form Layout',
      description: 'Compiled visual form designer layout',
      copyright: 'Copyrights reserved to 90Studio',
      target: {
        type: 'any',
        window_title_pattern: '.*',
        match_mode: 'contains'
      },
      canvas: {
        width: 1024,
        height: 768,
        scale: 1.0,
        background_image_path: null
      },
      execution_settings: {
        default_step_delay_ms: 120,
        typing_speed_ms: 20
      },
      optimization: {
        enabled: true,
        band_tolerance_px: 24.0,
        click_to_tab: false,
        collapse_delays: true,
        remove_redundant_focus: true,
        prune_empty_delays: true
      },
      boxes: []
    };

    // Interaction State
    this.selectedBoxId = null;
    this.hoveredBoxId = null;
    this.hoveredHandle = null;
    this.interactionMode = 'idle'; // 'idle' | 'drawing' | 'moving' | 'resizing'
    this.dragStart = { x: 0, y: 0 };
    this.dragCurrent = { x: 0, y: 0 };
    this.boxInitialGeom = null;
    this.resizeHandle = null;

    // Grid & Snap Configuration
    this.snapEnabled = true;
    this.gridSize = 16;
    this.alignmentGuideTolerance = 4; // Magnetic snap within 4px of neighbor edges
    this.activeGuides = []; // [{ type: 'v'|'h', coord: number }]

    // Sizing Constraints
    this.minBoxWidth = 24;
    this.minBoxHeight = 16;
    this.drawThresholdPx = 10; // Discard clicks smaller than 10x10 px (US-VFD-01)
    this.handleSize = 8;

    // Backdrop Image
    this.backgroundImage = null;

    this.bindDomElements();
    this.bindEvents();
    this.syncCanvasSize();
    this.render();
  }

  // --------------------------------------------------------------------------
  // DOM BINDING & EVENT LISTENERS
  // --------------------------------------------------------------------------
  bindDomElements() {
    this.ui = {
      backdropInput: document.getElementById('designer-backdrop-input'),
      btnClearBackdrop: document.getElementById('btn-clear-backdrop'),
      backdropDimLabel: document.getElementById('backdrop-dimensions'),
      snapToggle: document.getElementById('designer-snap-toggle'),
      gridSizeSelect: document.getElementById('designer-grid-size'),
      btnAutoSequence: document.getElementById('btn-auto-sequence'),
      btnImport: document.getElementById('btn-import-layout'),
      importInput: document.getElementById('designer-import-input'),
      btnExport: document.getElementById('btn-export-layout'),
      btnClearCanvas: document.getElementById('btn-clear-canvas'),
      btnCompile: document.getElementById('btn-compile-workflow'),
      // Sidebar Inspector
      inspectorEmpty: document.getElementById('inspector-empty'),
      inspectorForm: document.getElementById('inspector-form'),
      inspectorBoxCount: document.getElementById('inspector-box-count'),
      selectedSeqPill: document.getElementById('selected-seq-pill'),
      propLabel: document.getElementById('prop-box-label'),
      propName: document.getElementById('prop-box-name'),
      propSeq: document.getElementById('prop-box-seq'),
      propAction: document.getElementById('prop-box-action'),
      propValue: document.getElementById('prop-box-value'),
      propNav: document.getElementById('prop-box-nav'),
      propPostDelay: document.getElementById('prop-box-post-delay'),
      propClear: document.getElementById('prop-box-clear'),
      propForceClick: document.getElementById('prop-box-force-click'),
      propSecret: document.getElementById('prop-box-secret'),
      geoX: document.getElementById('geo-x'),
      geoY: document.getElementById('geo-y'),
      geoW: document.getElementById('geo-w'),
      geoH: document.getElementById('geo-h'),
      geoNormX: document.getElementById('geo-norm-x'),
      geoNormY: document.getElementById('geo-norm-y'),
      geoNormW: document.getElementById('geo-norm-w'),
      geoNormH: document.getElementById('geo-norm-h'),
      btnDuplicate: document.getElementById('btn-duplicate-box'),
      btnDelete: document.getElementById('btn-delete-box'),
      // Layout Accordion
      layoutName: document.getElementById('layout-name'),
      targetTitlePattern: document.getElementById('target-title-pattern'),
      targetAppType: document.getElementById('target-app-type'),
      optClickToTab: document.getElementById('opt-click-to-tab'),
      // Compile Modal
      compileModal: document.getElementById('compile-modal'),
      btnCloseCompileModal: document.getElementById('btn-close-compile-modal'),
      compileJsonPreview: document.getElementById('compile-json-preview'),
      statStepCount: document.getElementById('stat-step-count'),
      statTargetName: document.getElementById('stat-target-name'),
      statSourceMode: document.getElementById('stat-source-mode'),
      btnDownloadJson: document.getElementById('btn-download-workflow-json'),
      btnLoadInBuilder: document.getElementById('btn-load-in-builder'),
      btnRunWorkflow: document.getElementById('btn-run-compiled-workflow')
    };
  }

  bindEvents() {
    // Canvas Mouse & Keyboard Events
    this.canvas.addEventListener('mousedown', this.handleMouseDown.bind(this));
    window.addEventListener('mousemove', this.handleMouseMove.bind(this));
    window.addEventListener('mouseup', this.handleMouseUp.bind(this));
    window.addEventListener('keydown', this.handleKeyDown.bind(this));

    // Toolbar Controls
    this.ui.backdropInput?.addEventListener('change', this.handleBackdropUpload.bind(this));
    this.ui.btnClearBackdrop?.addEventListener('click', this.clearBackdrop.bind(this));
    this.ui.snapToggle?.addEventListener('change', (e) => {
      this.snapEnabled = e.target.checked;
      this.render();
    });
    this.ui.gridSizeSelect?.addEventListener('change', (e) => {
      this.gridSize = parseInt(e.target.value, 10) || 16;
      this.render();
    });
    this.ui.btnAutoSequence?.addEventListener('click', this.autoSequenceSpatial.bind(this));
    this.ui.btnClearCanvas?.addEventListener('click', () => {
      if (confirm('Clear all visual boxes from the canvas?')) {
        this.layout.boxes = [];
        this.selectBox(null);
        this.render();
        this.showToast('Canvas cleared', 'info');
      }
    });

    // Import / Export
    this.ui.btnExport?.addEventListener('click', this.exportLayoutJson.bind(this));
    this.ui.btnImport?.addEventListener('click', () => this.ui.importInput?.click());
    this.ui.importInput?.addEventListener('change', this.handleImportJson.bind(this));

    // Compile Workflow
    this.ui.btnCompile?.addEventListener('click', this.compileToWorkflow.bind(this));

    // Property Inspector Live Two-Way Sync
    this.bindPropertyInspectorInputs();

    // Modal Events
    this.ui.btnCloseCompileModal?.addEventListener('click', () => {
      this.ui.compileModal.style.display = 'none';
    });
  }

  bindPropertyInspectorInputs() {
    const sync = (prop, getter) => {
      return (e) => {
        const box = this.getSelectedBox();
        if (!box) return;
        const val = getter(e.target);
        if (prop === 'sequence_index') {
          this.reindexBoxSequence(box.id, parseInt(val, 10));
        } else if (prop === 'geometry') {
          // Handled via canvas
        } else {
          box[prop] = val;
        }
        this.render();
      };
    };

    this.ui.propLabel?.addEventListener('input', sync('label', (t) => t.value));
    this.ui.propName?.addEventListener('input', sync('name', (t) => t.value.replace(/[^a-zA-Z0-9_]/g, '_')));
    this.ui.propSeq?.addEventListener('change', sync('sequence_index', (t) => t.value));
    this.ui.propAction?.addEventListener('change', sync('action_type', (t) => t.value));
    this.ui.propValue?.addEventListener('input', sync('value', (t) => t.value));
    this.ui.propNav?.addEventListener('change', sync('navigation', (t) => t.value));
    this.ui.propPostDelay?.addEventListener('change', sync('post_delay_ms', (t) => parseInt(t.value, 10) || 120));
    this.ui.propClear?.addEventListener('change', sync('clear_before', (t) => t.checked));
    this.ui.propForceClick?.addEventListener('change', sync('force_click', (t) => t.checked));
    this.ui.propSecret?.addEventListener('change', (e) => {
      const box = this.getSelectedBox();
      if (box) {
        box.metadata = box.metadata || {};
        box.metadata.is_secret = e.target.checked;
      }
    });

    this.ui.btnDelete?.addEventListener('click', () => this.deleteSelectedBox());
    this.ui.btnDuplicate?.addEventListener('click', () => this.duplicateSelectedBox());

    // Layout-level metadata sync
    this.ui.layoutName?.addEventListener('input', (e) => this.layout.name = e.target.value);
    this.ui.targetTitlePattern?.addEventListener('input', (e) => {
      this.layout.target.window_title_pattern = e.target.value;
    });
    this.ui.targetAppType?.addEventListener('change', (e) => {
      this.layout.target.type = e.target.value;
    });
    this.ui.optClickToTab?.addEventListener('change', (e) => {
      this.layout.optimization.click_to_tab = e.target.checked;
    });
  }

  // --------------------------------------------------------------------------
  // COORDINATE MAPPING & MATH FORMULAS
  // --------------------------------------------------------------------------

  /**
   * Translates client mouse coordinates into internal canvas pixel coordinates.
   * Protects against high-DPI and CSS dimension scaling.
   */
  getCanvasCoordinates(e) {
    const rect = this.canvas.getBoundingClientRect();
    const scaleX = this.canvas.width / rect.width;
    const scaleY = this.canvas.height / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY
    };
  }

  /**
   * Snaps a scalar value to the configured grid increment.
   */
  snap(val) {
    if (!this.snapEnabled) return val;
    return Math.round(val / this.gridSize) * this.gridSize;
  }

  /**
   * Computes normalized coordinates [0.0, 1.0] conforming to Section 7.1.
   */
  getNormalizedCoordinates(box) {
    const cw = this.canvas.width;
    const ch = this.canvas.height;
    const g = box.geometry;
    const norm_x = Math.max(0, Math.min(1, +(g.x / cw).toFixed(4)));
    const norm_y = Math.max(0, Math.min(1, +(g.y / ch).toFixed(4)));
    const norm_w = Math.max(0, Math.min(1 - norm_x, +(g.width / cw).toFixed(4)));
    const norm_h = Math.max(0, Math.min(1 - norm_y, +(g.height / ch).toFixed(4)));
    const center_norm_x = Math.max(0, Math.min(1, +((g.x + g.width / 2) / cw).toFixed(4)));
    const center_norm_y = Math.max(0, Math.min(1, +((g.y + g.height / 2) / ch).toFixed(4)));
    return { norm_x, norm_y, norm_w, norm_h, center_norm_x, center_norm_y };
  }

  // --------------------------------------------------------------------------
  // HIT TESTING: BOXES & 8 RESIZE HANDLES
  // --------------------------------------------------------------------------

  /**
   * Computes pixel positions of the 8 resize handles for a given box geometry.
   */
  getHandlePositions(g) {
    return {
      nw: { x: g.x, y: g.y, cursor: 'nwse-resize' },
      n:  { x: g.x + g.width / 2, y: g.y, cursor: 'ns-resize' },
      ne: { x: g.x + g.width, y: g.y, cursor: 'nesw-resize' },
      e:  { x: g.x + g.width, y: g.y + g.height / 2, cursor: 'ew-resize' },
      se: { x: g.x + g.width, y: g.y + g.height, cursor: 'nwse-resize' },
      s:  { x: g.x + g.width / 2, y: g.y + g.height, cursor: 'ns-resize' },
      sw: { x: g.x, y: g.y + g.height, cursor: 'nesw-resize' },
      w:  { x: g.x, y: g.y + g.height / 2, cursor: 'ew-resize' }
    };
  }

  /**
   * Tests whether point (x, y) strikes an 8-handle on the selected box.
   */
  hitTestHandles(x, y) {
    const box = this.getSelectedBox();
    if (!box) return null;
    const handles = this.getHandlePositions(box.geometry);
    const hitRadius = (this.handleSize / 2) + 2;

    for (const [handleKey, h] of Object.entries(handles)) {
      if (Math.abs(x - h.x) <= hitRadius && Math.abs(y - h.y) <= hitRadius) {
        return { handle: handleKey, cursor: h.cursor };
      }
    }
    return null;
  }

  /**
   * Tests whether point (x, y) strikes inside any box (tested top-down in z-order).
   */
  hitTestBox(x, y) {
    for (let i = this.layout.boxes.length - 1; i >= 0; i--) {
      const b = this.layout.boxes[i];
      const g = b.geometry;
      if (x >= g.x && x <= g.x + g.width && y >= g.y && y <= g.y + g.height) {
        return b;
      }
    }
    return null;
  }

  // --------------------------------------------------------------------------
  // INTERACTION LIFECYCLE: MOUSE HANDLERS
  // --------------------------------------------------------------------------

  handleMouseDown(e) {
    if (e.button !== 0) return; // Left mouse click only
    const pt = this.getCanvasCoordinates(e);
    this.dragStart = pt;
    this.dragCurrent = pt;
    this.activeGuides = [];

    // 1. Test handles on selected box first
    const handleHit = this.hitTestHandles(pt.x, pt.y);
    if (handleHit) {
      this.interactionMode = 'resizing';
      this.resizeHandle = handleHit.handle;
      const box = this.getSelectedBox();
      this.boxInitialGeom = { ...box.geometry };
      return;
    }

    // 2. Test if hitting an existing box
    const boxHit = this.hitTestBox(pt.x, pt.y);
    if (boxHit) {
      this.selectBox(boxHit.id);
      this.interactionMode = 'moving';
      this.boxInitialGeom = { ...boxHit.geometry };
      this.render();
      return;
    }

    // 3. Otherwise clicked empty canvas -> prepare drawing
    this.selectBox(null);
    this.interactionMode = 'drawing';
    this.render();
  }

  handleMouseMove(e) {
    const pt = this.getCanvasCoordinates(e);
    this.dragCurrent = pt;

    if (this.interactionMode === 'idle') {
      // Update cursor feedback based on hover
      const handleHit = this.hitTestHandles(pt.x, pt.y);
      if (handleHit) {
        this.canvas.style.cursor = handleHit.cursor;
      } else {
        const boxHit = this.hitTestBox(pt.x, pt.y);
        this.canvas.style.cursor = boxHit ? 'move' : 'crosshair';
      }
      return;
    }

    if (this.interactionMode === 'drawing') {
      this.render();
    } else if (this.interactionMode === 'moving') {
      this.updateBoxMove(pt);
      this.render();
    } else if (this.interactionMode === 'resizing') {
      this.updateBoxResize(pt);
      this.render();
    }
  }

  handleMouseUp(e) {
    if (this.interactionMode === 'drawing') {
      this.finishDrawing();
    } else if (this.interactionMode === 'moving' || this.interactionMode === 'resizing') {
      this.activeGuides = [];
      this.syncInspectorForm();
    }
    this.interactionMode = 'idle';
    this.boxInitialGeom = null;
    this.resizeHandle = null;
    this.render();
  }

  handleKeyDown(e) {
    // Delete selected box
    if ((e.key === 'Delete' || e.key === 'Backspace') && !this.isEditingInput(e)) {
      if (this.selectedBoxId) {
        e.preventDefault();
        this.deleteSelectedBox();
      }
    } else if (e.key === 'Escape') {
      this.selectBox(null);
      this.render();
    }
  }

  isEditingInput(e) {
    const tag = (e.target.tagName || '').toLowerCase();
    return tag === 'input' || tag === 'textarea' || tag === 'select';
  }

  // --------------------------------------------------------------------------
  // BOX DRAWING, MOVING & RESIZING ENGINES
  // --------------------------------------------------------------------------

  finishDrawing() {
    let x1 = Math.min(this.dragStart.x, this.dragCurrent.x);
    let y1 = Math.min(this.dragStart.y, this.dragCurrent.y);
    let x2 = Math.max(this.dragStart.x, this.dragCurrent.x);
    let y2 = Math.max(this.dragStart.y, this.dragCurrent.y);

    if (this.snapEnabled) {
      x1 = this.snap(x1);
      y1 = this.snap(y1);
      x2 = this.snap(x2);
      y2 = this.snap(y2);
    }

    let w = x2 - x1;
    let h = y2 - y1;

    // US-VFD-01: Discard accidental clicks below threshold
    if (w < this.drawThresholdPx || h < this.drawThresholdPx) {
      return;
    }

    // Clamp to minimum constraints
    w = Math.max(this.minBoxWidth, w);
    h = Math.max(this.minBoxHeight, h);

    // Clamp to canvas boundaries
    x1 = Math.max(0, Math.min(this.canvas.width - w, x1));
    y1 = Math.max(0, Math.min(this.canvas.height - h, y1));

    const boxIndex = this.layout.boxes.length + 1;
    const newBox = {
      id: crypto.randomUUID(),
      name: `field_${boxIndex}`,
      label: `Field ${boxIndex}`,
      geometry: { x: x1, y: y1, width: w, height: h },
      sequence_index: boxIndex,
      action_type: 'type_text',
      value: '',
      navigation: 'tab',
      clear_before: true,
      post_delay_ms: 120,
      force_click: false,
      metadata: { is_secret: false }
    };

    this.layout.boxes.push(newBox);
    this.selectBox(newBox.id);
    this.showToast(`Added field #${boxIndex}`, 'info');
  }

  updateBoxMove(pt) {
    const box = this.getSelectedBox();
    if (!box || !this.boxInitialGeom) return;

    let dx = pt.x - this.dragStart.x;
    let dy = pt.y - this.dragStart.y;

    let newX = this.boxInitialGeom.x + dx;
    let newY = this.boxInitialGeom.y + dy;

    if (this.snapEnabled) {
      newX = this.snap(newX);
      newY = this.snap(newY);
    }

    // Magnetic Alignment Guide Snapping
    newX = this.applyMagneticSnapX(newX, box.geometry.width, box.id);
    newY = this.applyMagneticSnapY(newY, box.geometry.height, box.id);

    // Boundary Clamping
    newX = Math.max(0, Math.min(this.canvas.width - box.geometry.width, newX));
    newY = Math.max(0, Math.min(this.canvas.height - box.geometry.height, newY));

    box.geometry.x = newX;
    box.geometry.y = newY;
    this.syncInspectorGeometry();
  }

  updateBoxResize(pt) {
    const box = this.getSelectedBox();
    if (!box || !this.boxInitialGeom || !this.resizeHandle) return;

    const g0 = this.boxInitialGeom;
    let dx = pt.x - this.dragStart.x;
    let dy = pt.y - this.dragStart.y;

    let x = g0.x;
    let y = g0.y;
    let w = g0.width;
    let h = g0.height;

    const handle = this.resizeHandle;

    if (handle.includes('e')) {
      w = this.snap(g0.width + dx);
      w = Math.max(this.minBoxWidth, Math.min(this.canvas.width - x, w));
    }
    if (handle.includes('s')) {
      h = this.snap(g0.height + dy);
      h = Math.max(this.minBoxHeight, Math.min(this.canvas.height - y, h));
    }
    if (handle.includes('w')) {
      const origRight = g0.x + g0.width;
      let proposedX = this.snap(g0.x + dx);
      proposedX = Math.max(0, Math.min(origRight - this.minBoxWidth, proposedX));
      w = origRight - proposedX;
      x = proposedX;
    }
    if (handle.includes('n')) {
      const origBottom = g0.y + g0.height;
      let proposedY = this.snap(g0.y + dy);
      proposedY = Math.max(0, Math.min(origBottom - this.minBoxHeight, proposedY));
      h = origBottom - proposedY;
      y = proposedY;
    }

    box.geometry.x = x;
    box.geometry.y = y;
    box.geometry.width = w;
    box.geometry.height = h;
    this.syncInspectorGeometry();
  }

  applyMagneticSnapX(x, w, selfId) {
    this.activeGuides = this.activeGuides.filter(g => g.type !== 'v');
    const tol = this.alignmentGuideTolerance;
    const right = x + w;

    for (const b of this.layout.boxes) {
      if (b.id === selfId) continue;
      const otherX = b.geometry.x;
      const otherRight = b.geometry.x + b.geometry.width;

      if (Math.abs(x - otherX) <= tol) {
        this.activeGuides.push({ type: 'v', coord: otherX });
        return otherX;
      }
      if (Math.abs(right - otherRight) <= tol) {
        this.activeGuides.push({ type: 'v', coord: otherRight });
        return otherRight - w;
      }
    }
    return x;
  }

  applyMagneticSnapY(y, h, selfId) {
    this.activeGuides = this.activeGuides.filter(g => g.type !== 'h');
    const tol = this.alignmentGuideTolerance;
    const bottom = y + h;

    for (const b of this.layout.boxes) {
      if (b.id === selfId) continue;
      const otherY = b.geometry.y;
      const otherBottom = b.geometry.y + b.geometry.height;

      if (Math.abs(y - otherY) <= tol) {
        this.activeGuides.push({ type: 'h', coord: otherY });
        return otherY;
      }
      if (Math.abs(bottom - otherBottom) <= tol) {
        this.activeGuides.push({ type: 'h', coord: otherBottom });
        return otherBottom - h;
      }
    }
    return y;
  }

  // --------------------------------------------------------------------------
  // SEQUENCE RE-INDEXING & SPATIAL BAND SORTING
  // --------------------------------------------------------------------------

  /**
   * Dynamically updates the sequence index of a box and re-ranks all other
   * boxes contiguously without gaps or duplicate numbers (US-VFD-02).
   */
  reindexBoxSequence(targetBoxId, newSeq) {
    const total = this.layout.boxes.length;
    const targetBox = this.layout.boxes.find(b => b.id === targetBoxId);
    if (!targetBox) return;

    newSeq = Math.max(1, Math.min(total, newSeq));
    const oldSeq = targetBox.sequence_index || 1;
    if (newSeq === oldSeq) return;

    if (newSeq < oldSeq) {
      this.layout.boxes.forEach(b => {
        if (b.id !== targetBoxId && b.sequence_index >= newSeq && b.sequence_index < oldSeq) {
          b.sequence_index++;
        }
      });
    } else {
      this.layout.boxes.forEach(b => {
        if (b.id !== targetBoxId && b.sequence_index > oldSeq && b.sequence_index <= newSeq) {
          b.sequence_index--;
        }
      });
    }
    targetBox.sequence_index = newSeq;
    this.syncInspectorForm();
  }

  /**
   * Sorts visual boxes in Western reading order (2D spatial band sort)
   * matching Pass 2 of kutomoto.designer.compiler.
   */
  autoSequenceSpatial() {
    const boxes = this.layout.boxes;
    if (boxes.length === 0) return;

    const tolerance = this.layout.optimization.band_tolerance_px || 24;
    const sortedByY = [...boxes].sort((a, b) => a.geometry.y - b.geometry.y || a.geometry.x - b.geometry.x);

    const bands = [];
    let currentBand = [sortedByY[0]];
    let anchorY = sortedByY[0].geometry.y;

    for (let i = 1; i < sortedByY.length; i++) {
      const b = sortedByY[i];
      if (Math.abs(b.geometry.y - anchorY) <= tolerance) {
        currentBand.push(b);
      } else {
        bands.push(currentBand);
        currentBand = [b];
        anchorY = b.geometry.y;
      }
    }
    bands.push(currentBand);

    let rank = 1;
    for (const band of bands) {
      band.sort((a, b) => a.geometry.x - b.geometry.x);
      for (const box of band) {
        box.sequence_index = rank++;
      }
    }

    this.syncInspectorForm();
    this.render();
    this.showToast('Re-sequenced boxes in reading order', 'success');
  }

  // --------------------------------------------------------------------------
  // SELECTION & PROPERTY INSPECTOR SYNC
  // --------------------------------------------------------------------------

  getSelectedBox() {
    return this.layout.boxes.find(b => b.id === this.selectedBoxId) || null;
  }

  selectBox(boxId) {
    this.selectedBoxId = boxId;
    this.syncInspectorForm();
  }

  deleteSelectedBox() {
    const box = this.getSelectedBox();
    if (!box) return;

    const deletedSeq = box.sequence_index;
    this.layout.boxes = this.layout.boxes.filter(b => b.id !== box.id);

    // Re-index remaining boxes to fill the gap
    this.layout.boxes.forEach(b => {
      if (b.sequence_index > deletedSeq) {
        b.sequence_index--;
      }
    });

    this.selectBox(null);
    this.render();
    this.showToast('Field deleted', 'info');
  }

  duplicateSelectedBox() {
    const box = this.getSelectedBox();
    if (!box) return;

    const newIndex = this.layout.boxes.length + 1;
    const clone = JSON.parse(JSON.stringify(box));
    clone.id = crypto.randomUUID();
    clone.name = `${box.name}_copy`;
    clone.label = `${box.label || box.name} (Copy)`;
    clone.sequence_index = newIndex;
    clone.geometry.x = Math.min(this.canvas.width - clone.geometry.width, clone.geometry.x + 16);
    clone.geometry.y = Math.min(this.canvas.height - clone.geometry.height, clone.geometry.y + 16);

    this.layout.boxes.push(clone);
    this.selectBox(clone.id);
    this.render();
    this.showToast(`Duplicated field as #${newIndex}`, 'success');
  }

  syncInspectorForm() {
    const box = this.getSelectedBox();
    const count = this.layout.boxes.length;
    if (this.ui.inspectorBoxCount) {
      this.ui.inspectorBoxCount.textContent = `${count} ${count === 1 ? 'box' : 'boxes'}`;
    }

    if (!box) {
      this.ui.inspectorEmpty.style.display = 'flex';
      this.ui.inspectorForm.style.display = 'none';
      return;
    }

    this.ui.inspectorEmpty.style.display = 'none';
    this.ui.inspectorForm.style.display = 'flex';

    if (this.ui.selectedSeqPill) this.ui.selectedSeqPill.textContent = `#${box.sequence_index || 1}`;
    if (this.ui.propLabel) this.ui.propLabel.value = box.label || '';
    if (this.ui.propName) this.ui.propName.value = box.name || '';
    if (this.ui.propSeq) {
      this.ui.propSeq.value = box.sequence_index || 1;
      this.ui.propSeq.max = count;
    }
    if (this.ui.propAction) this.ui.propAction.value = box.action_type || 'type_text';
    if (this.ui.propValue) this.ui.propValue.value = box.value || '';
    if (this.ui.propNav) this.ui.propNav.value = box.navigation || 'tab';
    if (this.ui.propPostDelay) this.ui.propPostDelay.value = box.post_delay_ms !== undefined ? box.post_delay_ms : 120;
    if (this.ui.propClear) this.ui.propClear.checked = box.clear_before !== false;
    if (this.ui.propForceClick) this.ui.propForceClick.checked = Boolean(box.force_click);
    if (this.ui.propSecret) {
      this.ui.propSecret.checked = Boolean(box.metadata && box.metadata.is_secret);
    }

    this.syncInspectorGeometry();
  }

  syncInspectorGeometry() {
    const box = this.getSelectedBox();
    if (!box) return;

    const g = box.geometry;
    const norm = this.getNormalizedCoordinates(box);

    if (this.ui.geoX) this.ui.geoX.textContent = Math.round(g.x);
    if (this.ui.geoY) this.ui.geoY.textContent = Math.round(g.y);
    if (this.ui.geoW) this.ui.geoW.textContent = Math.round(g.width);
    if (this.ui.geoH) this.ui.geoH.textContent = Math.round(g.height);
    if (this.ui.geoNormX) this.ui.geoNormX.textContent = norm.norm_x.toFixed(4);
    if (this.ui.geoNormY) this.ui.geoNormY.textContent = norm.norm_y.toFixed(4);
    if (this.ui.geoNormW) this.ui.geoNormW.textContent = norm.norm_w.toFixed(4);
    if (this.ui.geoNormH) this.ui.geoNormH.textContent = norm.norm_h.toFixed(4);
  }

  // --------------------------------------------------------------------------
  // CANVAS RENDERING PIPELINE
  // --------------------------------------------------------------------------

  render() {
    const ctx = this.ctx;
    const cw = this.canvas.width;
    const ch = this.canvas.height;

    ctx.clearRect(0, 0, cw, ch);

    // Layer 0: Backdrop Image or Canvas Underlay
    if (this.backgroundImage) {
      ctx.drawImage(this.backgroundImage, 0, 0, cw, ch);
    } else {
      // Draw subtle background fill
      ctx.fillStyle = '#0d1117';
      ctx.fillRect(0, 0, cw, ch);

      // Grid overlay
      if (this.snapEnabled) {
        this.renderGrid(ctx, cw, ch);
      }
    }

    // Layer 1: Magnetic Snap Guidelines
    this.renderGuidelines(ctx, cw, ch);

    // Layer 2: Visual Boxes
    for (const box of this.layout.boxes) {
      this.renderBox(ctx, box);
    }

    // Layer 3: Resize Handles & Adornments for Selected Box
    const selectedBox = this.getSelectedBox();
    if (selectedBox) {
      this.renderSelectionHandles(ctx, selectedBox);
    }

    // Layer 4: Interactive Rubberband Drawing Rectangle
    if (this.interactionMode === 'drawing') {
      this.renderDrawingRubberband(ctx);
    }
  }

  renderGrid(ctx, cw, ch) {
    ctx.save();
    ctx.strokeStyle = 'rgba(48, 54, 61, 0.4)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let x = this.gridSize; x < cw; x += this.gridSize) {
      ctx.moveTo(x + 0.5, 0);
      ctx.lineTo(x + 0.5, ch);
    }
    for (let y = this.gridSize; y < ch; y += this.gridSize) {
      ctx.moveTo(0, y + 0.5);
      ctx.lineTo(cw, y + 0.5);
    }
    ctx.stroke();
    ctx.restore();
  }

  renderGuidelines(ctx, cw, ch) {
    if (this.activeGuides.length === 0) return;
    ctx.save();
    ctx.strokeStyle = '#00f0ff';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);

    for (const g of this.activeGuides) {
      ctx.beginPath();
      if (g.type === 'v') {
        ctx.moveTo(g.coord + 0.5, 0);
        ctx.lineTo(g.coord + 0.5, ch);
      } else {
        ctx.moveTo(0, g.coord + 0.5);
        ctx.lineTo(cw, g.coord + 0.5);
      }
      ctx.stroke();
    }
    ctx.restore();
  }

  renderBox(ctx, box) {
    const g = box.geometry;
    const isSelected = box.id === this.selectedBoxId;
    const isSubmit = box.action_type === 'submit';

    ctx.save();

    // Box Fill & Stroke
    if (isSelected) {
      ctx.fillStyle = isSubmit ? 'rgba(46, 160, 67, 0.3)' : 'rgba(31, 111, 235, 0.25)';
      ctx.strokeStyle = isSubmit ? '#3fb950' : '#58a6ff';
      ctx.lineWidth = 2;
    } else {
      ctx.fillStyle = isSubmit ? 'rgba(46, 160, 67, 0.15)' : 'rgba(31, 111, 235, 0.12)';
      ctx.strokeStyle = isSubmit ? '#2ea043' : 'rgba(56, 139, 253, 0.75)';
      ctx.lineWidth = 1.5;
    }

    ctx.fillRect(g.x, g.y, g.width, g.height);
    ctx.strokeRect(g.x, g.y, g.width, g.height);

    // Sequence Badge [#1]
    const badgeText = `#${box.sequence_index || 1}`;
    ctx.font = 'bold 10px monospace';
    const textWidth = ctx.measureText(badgeText).width;
    const badgeW = textWidth + 10;
    const badgeH = 16;
    const badgeX = g.x + 3;
    const badgeY = g.y + 3;

    ctx.fillStyle = isSubmit ? '#238636' : '#8957e5';
    this.drawRoundedRect(ctx, badgeX, badgeY, badgeW, badgeH, 3);
    ctx.fill();

    ctx.fillStyle = '#ffffff';
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'center';
    ctx.fillText(badgeText, badgeX + badgeW / 2, badgeY + badgeH / 2);

    // Label Text
    const labelText = box.label || box.name;
    const labelX = badgeX + badgeW + 6;
    const labelY = badgeY + badgeH / 2;
    ctx.font = '11px sans-serif';
    ctx.fillStyle = isSelected ? '#ffffff' : '#c9d1d9';
    ctx.textAlign = 'left';

    // Truncate label if it overflows box width
    const maxLabelW = Math.max(20, g.width - (badgeW + 16));
    this.drawTruncatedText(ctx, labelText, labelX, labelY, maxLabelW);

    // Action Type / Navigation Pill at bottom right if box is tall enough
    if (g.height >= 34 && g.width >= 60) {
      const tagText = box.action_type === 'type_text' ? `[Tab: ${box.navigation}]` : `[${box.action_type}]`;
      ctx.font = '9px monospace';
      ctx.fillStyle = 'rgba(240, 246, 252, 0.6)';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'bottom';
      ctx.fillText(tagText, g.x + g.width - 4, g.y + g.height - 3);
    }

    ctx.restore();
  }

  renderSelectionHandles(ctx, box) {
    const handles = this.getHandlePositions(box.geometry);
    const size = this.handleSize;
    const half = size / 2;

    ctx.save();
    ctx.fillStyle = '#ffffff';
    ctx.strokeStyle = '#1f6feb';
    ctx.lineWidth = 1.5;

    for (const h of Object.values(handles)) {
      ctx.fillRect(h.x - half, h.y - half, size, size);
      ctx.strokeRect(h.x - half, h.y - half, size, size);
    }

    // Geometry dimension bubble below box
    const g = box.geometry;
    const dimText = `${Math.round(g.width)} × ${Math.round(g.height)} px`;
    ctx.font = '10px monospace';
    const dimW = ctx.measureText(dimText).width + 8;
    const dimH = 14;
    const dimX = g.x + (g.width - dimW) / 2;
    const dimY = g.y + g.height + 4;

    ctx.fillStyle = 'rgba(13, 17, 23, 0.85)';
    this.drawRoundedRect(ctx, dimX, dimY, dimW, dimH, 3);
    ctx.fill();

    ctx.fillStyle = '#79c0ff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(dimText, dimX + dimW / 2, dimY + dimH / 2);

    ctx.restore();
  }

  renderDrawingRubberband(ctx) {
    let x1 = Math.min(this.dragStart.x, this.dragCurrent.x);
    let y1 = Math.min(this.dragStart.y, this.dragCurrent.y);
    let x2 = Math.max(this.dragStart.x, this.dragCurrent.x);
    let y2 = Math.max(this.dragStart.y, this.dragCurrent.y);

    if (this.snapEnabled) {
      x1 = this.snap(x1);
      y1 = this.snap(y1);
      x2 = this.snap(x2);
      y2 = this.snap(y2);
    }

    const w = x2 - x1;
    const h = y2 - y1;

    ctx.save();
    ctx.fillStyle = 'rgba(47, 129, 247, 0.18)';
    ctx.strokeStyle = '#58a6ff';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);

    ctx.fillRect(x1, y1, w, h);
    ctx.strokeRect(x1, y1, w, h);

    ctx.restore();
  }

  drawRoundedRect(ctx, x, y, width, height, radius) {
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    ctx.lineTo(x + width, y + height - radius);
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    ctx.lineTo(x + radius, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
  }

  drawTruncatedText(ctx, text, x, y, maxWidth) {
    if (maxWidth <= 0) return;
    let rendered = text;
    if (ctx.measureText(rendered).width > maxWidth) {
      while (rendered.length > 0 && ctx.measureText(rendered + '…').width > maxWidth) {
        rendered = rendered.slice(0, -1);
      }
      rendered += '…';
    }
    ctx.fillText(rendered, x, y);
  }

  // --------------------------------------------------------------------------
  // BACKDROP IMAGE MANAGEMENT (US-VFD-04)
  // --------------------------------------------------------------------------

  handleBackdropUpload(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        this.backgroundImage = img;
        this.layout.canvas.width = img.naturalWidth;
        this.layout.canvas.height = img.naturalHeight;
        this.layout.canvas.background_image_path = file.name;
        this.syncCanvasSize();
        this.render();
        this.showToast(`Loaded backdrop: ${img.naturalWidth} × ${img.naturalHeight} px`, 'success');
      };
      img.src = event.target.result;
    };
    reader.readAsDataURL(file);
  }

  clearBackdrop() {
    this.backgroundImage = null;
    this.layout.canvas.background_image_path = null;
    this.layout.canvas.width = 1024;
    this.layout.canvas.height = 768;
    this.syncCanvasSize();
    this.render();
    if (this.ui.backdropInput) this.ui.backdropInput.value = '';
    this.showToast('Backdrop image cleared', 'info');
  }

  syncCanvasSize() {
    const w = this.layout.canvas.width || 1024;
    const h = this.layout.canvas.height || 768;
    this.canvas.width = w;
    this.canvas.height = h;
    if (this.ui.backdropDimLabel) {
      this.ui.backdropDimLabel.textContent = `${w} × ${h} px`;
    }
  }

  // --------------------------------------------------------------------------
  // IMPORT / EXPORT & COMPILER API INTEGRATION
  // --------------------------------------------------------------------------

  exportLayoutJson() {
    const payload = JSON.parse(JSON.stringify(this.layout));
    payload.copyright = 'Copyrights reserved to 90Studio';
    payload.boxes = this.layout.boxes.map(b => ({
      id: b.id,
      name: b.name,
      label: b.label || b.name,
      geometry: { ...b.geometry },
      sequence_index: b.sequence_index,
      action_type: b.action_type || 'type_text',
      value: b.value || '',
      navigation: b.navigation || 'tab',
      clear_before: b.clear_before !== false,
      post_delay_ms: b.post_delay_ms !== undefined ? b.post_delay_ms : 120,
      force_click: Boolean(b.force_click),
      metadata: b.metadata || {}
    }));

    const jsonStr = JSON.stringify(payload, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${this.layout.name.toLowerCase().replace(/[^a-z0-9]/g, '_')}_layout.json`;
    a.click();
    URL.revokeObjectURL(url);
    this.showToast('VisualFormLayout JSON exported', 'success');
  }

  handleImportJson(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const data = JSON.parse(event.target.result);
        if (!data.boxes || !Array.isArray(data.boxes)) {
          throw new Error('Invalid schema: layout must contain a boxes array.');
        }

        this.layout = {
          ...this.layout,
          ...data,
          copyright: 'Copyrights reserved to 90Studio'
        };

        if (data.canvas) {
          this.layout.canvas.width = data.canvas.width || 1024;
          this.layout.canvas.height = data.canvas.height || 768;
        }

        this.syncCanvasSize();
        this.selectBox(this.layout.boxes[0]?.id || null);
        this.render();
        this.showToast(`Imported ${data.boxes.length} form boxes`, 'success');
      } catch (err) {
        alert('Failed to import layout JSON: ' + err.message);
      }
    };
    reader.readAsText(file);
  }

  async compileToWorkflow() {
    if (this.layout.boxes.length === 0) {
      alert('Cannot compile: canvas contains no visual boxes. Draw at least one field first.');
      return;
    }

    const payload = {
      schema_version: '1.0.0',
      id: this.layout.id || crypto.randomUUID(),
      name: this.layout.name || 'Compiled Visual Form',
      description: this.layout.description || '',
      copyright: 'Copyrights reserved to 90Studio',
      canvas: {
        width: this.canvas.width,
        height: this.canvas.height,
        scale: 1.0,
        background_image_path: this.layout.canvas.background_image_path
      },
      target_application: {
        type: this.layout.target.type || 'any',
        window_title_pattern: this.layout.target.window_title_pattern || '.*',
        match_mode: this.layout.target.match_mode || 'contains'
      },
      execution_settings: {
        default_step_delay_ms: this.layout.execution_settings.default_step_delay_ms || 120,
        typing_speed_ms: this.layout.execution_settings.typing_speed_ms || 20
      },
      optimization: {
        enabled: true,
        band_tolerance_px: this.layout.optimization.band_tolerance_px || 24.0,
        click_to_tab: Boolean(this.layout.optimization.click_to_tab),
        collapse_delays: true,
        remove_redundant_focus: true,
        prune_empty_delays: true
      },
      boxes: this.layout.boxes.map(b => ({
        id: b.id,
        name: b.name,
        label: b.label || b.name,
        geometry: { ...b.geometry },
        sequence_index: b.sequence_index,
        action_type: b.action_type || 'type_text',
        value: b.value || '',
        navigation: b.navigation || 'tab',
        clear_before: b.clear_before !== false,
        post_delay_ms: b.post_delay_ms !== undefined ? b.post_delay_ms : 120,
        force_click: Boolean(b.force_click),
        metadata: b.metadata || {}
      }))
    };

    try {
      this.showToast('Compiling visual form layout...', 'info');
      const response = await fetch('/api/designer/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server returned HTTP ${response.status}`);
      }

      const workflow = await response.json();
      this.displayCompileSuccessModal(workflow);
    } catch (err) {
      alert('Compilation error: ' + err.message);
    }
  }

  displayCompileSuccessModal(workflow) {
    if (!this.ui.compileModal) return;

    this.compiledWorkflow = workflow;
    const steps = workflow.steps || [];

    if (this.ui.statStepCount) this.ui.statStepCount.textContent = steps.length;
    if (this.ui.statTargetName) {
      this.ui.statTargetName.textContent = workflow.target_application?.window_title_pattern || '.*';
    }
    if (this.ui.statSourceMode) {
      this.ui.statSourceMode.textContent = workflow.source_mode || 'visual_designer_generated';
    }

    if (this.ui.compileJsonPreview) {
      this.ui.compileJsonPreview.textContent = JSON.stringify(workflow, null, 2);
    }

    this.ui.compileModal.style.display = 'flex';

    // Hook modal buttons
    this.ui.btnDownloadJson.onclick = () => {
      const jsonStr = JSON.stringify(workflow, null, 2);
      const blob = new Blob([jsonStr], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(workflow.name || 'workflow').toLowerCase().replace(/[^a-z0-9]/g, '_')}.json`;
      a.click();
      URL.revokeObjectURL(url);
    };

    this.ui.btnLoadInBuilder.onclick = () => {
      this.ui.compileModal.style.display = 'none';
      if (window.KutomotoRunner && typeof window.KutomotoRunner.loadWorkflow === 'function') {
        window.KutomotoRunner.loadWorkflow(workflow);
      }
      // Switch tab to Flow Builder
      document.querySelector('[data-tab="tab-builder"]')?.click();
    };

    this.ui.btnRunWorkflow.onclick = () => {
      this.ui.compileModal.style.display = 'none';
      if (window.KutomotoRunner && typeof window.KutomotoRunner.startExecutionWithWorkflow === 'function') {
        window.KutomotoRunner.startExecutionWithWorkflow(workflow);
      }
      // Switch tab to Execution Console
      document.querySelector('[data-tab="tab-console"]')?.click();
    };
  }

  showToast(message, type = 'info') {
    const hub = document.getElementById('toast-hub');
    if (!hub) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    hub.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 2800);
  }
}

// Global initialization when DOM is loaded
window.addEventListener('DOMContentLoaded', () => {
  window.KutomotoDesigner = new KutomotoVisualDesigner();
});
```

---

## 5. Verification Method

To independently verify the architecture and blueprints:

1. **Schema Validation Verification**:
   - The JSON emitted by `exportLayoutJson()` matches the `VisualFormLayout` schema defined in `src/kutomoto/designer/schema.py`.
   - Test in python:
     ```python
     from kutomoto.designer.schema import VisualFormLayout
     layout = VisualFormLayout.model_validate(exported_json)
     assert layout.copyright == "Copyrights reserved to 90Studio"
     ```
2. **Compiler Roundtrip Verification**:
   - Compiling the JSON via `compile_visual_layout_to_workflow`:
     ```python
     from kutomoto.designer.compiler import compile_visual_layout_to_workflow
     wf = compile_visual_layout_to_workflow(exported_json)
     assert len(wf.steps) >= len(exported_json["boxes"]) + 1
     assert wf.steps[0].action_type.value == "focus_window"
     ```
3. **Canvas Interaction & Coordinate Normalization**:
   - Drag-to-draw: Draw a box at $(150, 200)$ to $(450, 245)$ on a $1024\times 768$ canvas.
   - Verify:
     - `geometry.x == 150`, `geometry.y == 200`, `geometry.width == 300`, `geometry.height == 45`.
     - `norm_x == 0.1465`, `norm_y == 0.2604`, `norm_w == 0.2930`, `norm_h == 0.0586`.
     - `center_norm_x == 0.2930`, `center_norm_y == 0.2897`.
   - Resize handles: Drag handle `se` by $+50, +20 \to$ verifies width expands to $350$, height to $65$.
   - Accidental clicks: Click at $(300, 300)$ without drag $\to$ no box created.
4. **Sequence Re-indexing Verification**:
   - Create 3 boxes: #1, #2, #3.
   - Change #3 sequence index to 1 in Property Inspector.
   - Verify ranks become: former #3 $\to$ 1, former #1 $\to$ 2, former #2 $\to$ 3 without gaps or duplicates.
5. **Branding Watermark Check**:
   - Verify `index.html` header, footer, `kutomoto.css`, and `designer.js` all contain the explicit attribution:
     `Copyrights reserved to 90Studio`.
