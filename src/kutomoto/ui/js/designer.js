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
    if (!this.canvas) return;
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
      if (this.ui.compileModal) this.ui.compileModal.style.display = 'none';
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

  getCanvasCoordinates(e) {
    const rect = this.canvas.getBoundingClientRect();
    const scaleX = this.canvas.width / rect.width;
    const scaleY = this.canvas.height / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY
    };
  }

  snap(val) {
    if (!this.snapEnabled) return val;
    return Math.round(val / this.gridSize) * this.gridSize;
  }

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

    w = Math.max(this.minBoxWidth, w);
    h = Math.max(this.minBoxHeight, h);

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

    newX = this.applyMagneticSnapX(newX, box.geometry.width, box.id);
    newY = this.applyMagneticSnapY(newY, box.geometry.height, box.id);

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
      if (this.ui.inspectorEmpty) this.ui.inspectorEmpty.style.display = 'flex';
      if (this.ui.inspectorForm) this.ui.inspectorForm.style.display = 'none';
      return;
    }

    if (this.ui.inspectorEmpty) this.ui.inspectorEmpty.style.display = 'none';
    if (this.ui.inspectorForm) this.ui.inspectorForm.style.display = 'flex';

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
    if (!this.ctx) return;
    const ctx = this.ctx;
    const cw = this.canvas.width;
    const ch = this.canvas.height;

    ctx.clearRect(0, 0, cw, ch);

    // Layer 0: Backdrop Image or Canvas Underlay
    if (this.backgroundImage) {
      ctx.drawImage(this.backgroundImage, 0, 0, cw, ch);
    } else {
      ctx.fillStyle = '#0d1117';
      ctx.fillRect(0, 0, cw, ch);

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

    const maxLabelW = Math.max(20, g.width - (badgeW + 16));
    this.drawTruncatedText(ctx, labelText, labelX, labelY, maxLabelW);

    // Tag Pill
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

    if (this.ui.btnDownloadJson) {
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
    }

    if (this.ui.btnLoadInBuilder) {
      this.ui.btnLoadInBuilder.onclick = () => {
        this.ui.compileModal.style.display = 'none';
        if (window.KutomotoRunner && typeof window.KutomotoRunner.loadWorkflow === 'function') {
          window.KutomotoRunner.loadWorkflow(workflow);
        }
        document.querySelector('[data-tab="tab-builder"]')?.click();
      };
    }

    if (this.ui.btnRunWorkflow) {
      this.ui.btnRunWorkflow.onclick = () => {
        this.ui.compileModal.style.display = 'none';
        if (window.KutomotoRunner && typeof window.KutomotoRunner.startExecutionWithWorkflow === 'function') {
          window.KutomotoRunner.startExecutionWithWorkflow(workflow);
        } else if (window.KutomotoRunner) {
          window.KutomotoRunner.loadWorkflow(workflow);
          document.querySelector('[data-tab="tab-builder"]')?.click();
          window.KutomotoRunner.startExecutionSequence();
        }
      };
    }
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

// Global initialization
window.addEventListener('DOMContentLoaded', () => {
  window.KutomotoDesigner = new KutomotoVisualDesigner();
});
