# kutomoto Engine & Visual Designer Architecture Survey Report
**System**: kutomoto Forms Filling Automation System for Windows OS  
**Copyright**: Copyrights reserved to 90Studio  
**Author**: explorer_survey_3 (Investigation & Engine Survey)  
**Date**: 2026-11-04  
**Status**: APPROVED SURVEY / COMPREHENSIVE DESIGN SPECIFICATION  

---

## Executive Summary

This report establishes the comprehensive technical architecture, interaction mechanics, data schemas, compilation algorithms, and runtime execution models for **kutomoto** — an enterprise-grade forms filling automation system for Windows OS (desktop applications and open web browser tabs).

The investigation provides concrete answers and formal specifications for five foundational pillars:
1. **Visual Form Designer Mechanics & Interaction Model**: Click-and-drag bounding box definition, multi-field sequence management, canvas coordinate mapping with DPI independence, property inspector, and live visual preview simulation.
2. **Unified Workflow & Action Schema**: A robust JSON Schema unifying visual-designer compiled workflows and manual custom fill flows, covering 10 atomic action primitives (`focus_window`, `click`, `type_text`, `key_press`, `hotkey`, `clear_field`, `delay`, `submit`, `scroll`, `prompt_user_input`).
3. **Visual-to-Workflow Compilation Algorithm**: A deterministic multi-pass compiler translating spatial bounding boxes into linear, optimized OS action steps with coordinate resolution, field clearing, typing pacing, and navigation key injection.
4. **Execution Engine Runtime & State Machine**: A resilient state machine (`IDLE`, `COUNTDOWN`, `RUNNING`, `PAUSED`, `STOPPING`, `COMPLETED`, `ERROR`), non-intrusive target window attachment strategies (Window Title Regex, Process Matching, Interactive Countdown HUD, and Global Hotkey Trigger), and a non-blocking step loop.
5. **Error Handling, Safety Guardrails & Compliance Audit Logging**: Loss-of-focus detection, emergency failsafe hotkeys, configurable recovery policies (`ABORT`, `RETRY`, `PROMPT`, `SKIP`), masked credential handling, and structured JSON audit logging tailored for regulated banking, telecom, and business environments.

---

## 1. Visual Form Designer Mechanics & Interaction Model

### 1.1 Mental Model & Workspace Paradigm

In enterprise environments (such as bank branch loan processing, telecom subscriber provisioning, or corporate invoice entry), users frequently interact with standardized forms displayed either in desktop native windows (WPF, WinForms, Qt, SAP GUI) or web applications running in modern browsers (Chrome, Edge).

The **kutomoto Visual Form Designer** provides a zero-code visual layout canvas where users can:
- Define form input fields by drawing bounding boxes directly onto an interactive canvas.
- Optionally load a screenshot or template overlay of the target form as a canvas backdrop for pixel-perfect alignment.
- Assign semantic field properties: Name, Label, Field Type, Sequence Order, Input Value/Variable, and Navigation Action.
- Visually reorder fields with instant live sequence badge updates.
- Test and simulate the fill flow in an isolated visual simulator before executing against the live application.

```
+------------------------------------------------------------------------------------+
| kutomoto - Visual Form Designer (Copyrights reserved to 90Studio)                  |
+------------------------------------------------------------------------------------+
| [New Box] [Select] [Delete] [Auto-Sequence] | Canvas Zoom: 100% | [Simulate] [Run] |
+-------------------------------------------------+----------------------------------+
| Interactive Canvas (Drawing & Positioning)      | Field Property Inspector         |
| +---------------------------------------------+ | +------------------------------+ |
| | [Backdrop: Target Form Screenshot / Grid]   | | | Field Name: cust_full_name   | |
| |                                             | | | Label: Customer Full Name    | |
| |  +-----------------------+                  | | | Type: [Text Input         v] | |
| |  | [1] First Name        |                  | | | Sequence Index: [ 1        ] | |
| |  | value: "Alice"        |                  | | | Value Type: [Static Value v] | |
| |  +-----------------------+                  | | | Text Value: "Alice"          | |
| |                                             | | | Clear Before: [x] Yes        | |
| |  +-----------------------+                  | | | Navigation: [Tab Key      v] | |
| |  | [2] Account Number    |                  | | | Pre-delay (ms):  100         | |
| |  | value: {{account_no}} |                  | | | Post-delay (ms): 150         | |
| |  +-----------------------+                  | | +------------------------------+ |
| |                                             | | Sequence Ordering List         | |
| |  +-----------------------+                  | | [=] 1. First Name  (Tab)       | |
| |  | [3] Submit Button     |                  | | [=] 2. Account No  (Tab)       | |
| |  | action: Click         |                  | | [=] 3. Submit      (Click)     | |
| |  +-----------------------+                  | |                                | |
| +---------------------------------------------+ | [Compile to Action Workflow]   | |
+-------------------------------------------------+----------------------------------+
```

### 1.2 Coordinate System & Resolution Independence

A critical challenge in Windows form automation is screen resolution variability, high-DPI scaling (e.g. 100%, 125%, 150%, 200%), and window repositioning. 

To guarantee cross-machine portability, kutomoto implements a **Dual-Coordinate Architecture**:
1. **Canvas Normalized Coordinates ($0.0 \le u, v \le 1.0$)**:
   $$\text{norm\_x} = \frac{x_{\text{canvas}}}{W_{\text{canvas}}}, \quad \text{norm\_y} = \frac{y_{\text{canvas}}}{H_{\text{canvas}}}$$
   $$\text{norm\_w} = \frac{w_{\text{box}}}{W_{\text{canvas}}}, \quad \text{norm\_h} = \frac{h_{\text{box}}}{H_{\text{canvas}}}$$
2. **Absolute Screen / Client Pixel Coordinates**:
   When targeting an active application window with client rectangle $(X_{\text{win}}, Y_{\text{win}}, W_{\text{win}}, H_{\text{win}})$:
   $$\text{target\_click\_x} = X_{\text{win}} + (\text{norm\_x} + 0.5 \times \text{norm\_w}) \times W_{\text{win}}$$
   $$\text{target\_click\_y} = Y_{\text{win}} + (\text{norm\_y} + 0.5 \times \text{norm\_h}) \times H_{\text{win}}$$

This dual mapping guarantees that even if the target browser or desktop window is scaled or moved to another monitor, click targets calculate reliably at the center of the defined form box.

### 1.3 Canvas Drawing & Manipulation Mechanics

The designer supports three drawing modes:
1. **Click-and-Drag Box Creation**:
   - `onMouseDown(event)`: Captures starting anchor $(X_0, Y_0)$. Activates rubber-band box preview.
   - `onMouseMove(event)`: Updates bounding rectangle $[ \min(X_0, X_t), \min(Y_0, Y_t), |X_t - X_0|, |Y_t - Y_0| ]$.
   - `onMouseUp(event)`: Enforces minimum dimensions ($W \ge 24\text{px}, H \ge 16\text{px}$). Instantiates a new `FormBox` entity, assigns the next available `sequence_index`, and opens the Property Inspector.
2. **Click-to-Place Tool Palette**:
   - User clicks a field preset in the toolbar (e.g. "Add Text Field", "Add Checkbox", "Add Submit Button"), then clicks on the canvas to place a pre-sized box.
3. **8-Handle Bounding Box Manipulation**:
   - Selected boxes display 8 manipulation handles ($N, S, E, W, NW, NE, SW, SE$).
   - Dragging the interior moves the box with boundary clamping within canvas limits.
   - Configurable **Snap-to-Grid** (default 8px grid) and **Magnetic Alignment Guides** (visual dotted guidelines when box edges align with neighboring boxes horizontally or vertically within $\pm 4\text{px}$).

### 1.4 FormBox Data Structure

Each visual form field is represented by a structured `FormBox` object:

```typescript
export type FieldType = 
  | "text"            // Single line text input
  | "number"          // Numeric field
  | "date"            // Date input (YYYY-MM-DD or custom format)
  | "select"          // Dropdown / combo-box
  | "checkbox"        // Checkbox toggle
  | "radio"           // Radio button option
  | "textarea"        // Multi-line text area
  | "submit_button";  // Form submission button

export type ValueSourceType = 
  | "static"          // Hardcoded string
  | "variable"        // Dynamic placeholder e.g. {{customer_id}}
  | "generated"       // System generated: timestamp, uuid, counter
  | "runtime_prompt"; // Prompts operator at execution time if not provided

export type NavigationAction = 
  | "tab"             // Emit Tab key after entering value
  | "enter"           // Emit Enter key after entering value
  | "click_next"      // Explicitly mouse-click center of subsequent box
  | "none";           // Do not emit navigation key (leave focus in field)

export interface FormBoxBounds {
  x: number;          // Canvas pixel X
  y: number;          // Canvas pixel Y
  width: number;      // Canvas pixel width
  height: number;     // Canvas pixel height
  norm_x: number;     // Normalized 0.0 to 1.0
  norm_y: number;     // Normalized 0.0 to 1.0
  norm_w: number;     // Normalized width 0.0 to 1.0
  norm_h: number;     // Normalized height 0.0 to 1.0
}

export interface ValueConfiguration {
  source_type: ValueSourceType;
  static_value?: string;
  variable_name?: string;
  generator_pattern?: "timestamp_iso" | "timestamp_compact" | "uuid4" | "counter_increment";
  is_secret: boolean;               // If true, masks value in logs and UI (e.g. passwords, SSN)
  clear_before_type: boolean;       // If true, emits Ctrl+A + Backspace prior to typing
}

export interface FormBox {
  id: string;                       // Unique UUID v4
  name: string;                     // Programmatic identifier, e.g. "account_holder"
  label: string;                    // Human display label, e.g. "Account Holder Name"
  field_type: FieldType;
  sequence_index: number;           // Execution order (1, 2, 3...)
  bounds: FormBoxBounds;
  value_config: ValueConfiguration;
  navigation_action: NavigationAction;
  timing: {
    pre_delay_ms: number;           // Delay before interacting with this box (default: 100ms)
    typing_speed_ms: number;        // Delay per keystroke (default: 20ms)
    post_delay_ms: number;          // Delay after interaction/navigation (default: 150ms)
  };
}
```

### 1.5 Visual Reordering & Preview Simulator

- **Visual Badges**: Every box renders an amber/cyan badge displaying `[#1]`, `[#2]`, `[#3]` in its top-left corner.
- **Bidirectional Sidebar Reordering**:
  - The right-hand panel renders a draggable list of all fields. Dragging an item from position 3 to position 1 immediately updates all `sequence_index` values and refreshes the canvas badges in real time.
- **Auto-Sequence Layout Engine**:
  - Automatically orders fields using a **Top-to-Bottom, Left-to-Right Topological Sweep**:
    1. Group boxes into horizontal rows/bands using a vertical proximity threshold $T_y = \text{median}(\text{height}) \times 0.6$.
    2. Sort bands top-to-bottom by band minimum $Y$.
    3. Sort boxes within each band left-to-right by $X$.
    4. Renumber `sequence_index` sequentially from $1$ to $N$.
- **In-Canvas Visual Preview Simulator**:
  - A "Dry Run / Simulate" mode steps through the sequence within the designer itself.
  - The canvas renders a high-contrast glowing outline around the active box.
  - A virtual mouse cursor animates smoothly from box to box.
  - Text fields display simulated typewriter typing animation at the configured speed.
  - Displays elapsed time and verifies sequence logic without injecting OS-level events.

---

## 2. Unified Workflow Engine & Action Schema

### 2.1 Unification Principle

In kutomoto, **Visual Form Designer layouts and Manual Step-by-Step Custom Fill Flows compile into the exact same unified Action Workflow schema**.

```
[Visual Form Designer (Canvas Boxes)] --\
                                         +--> [Unified Action Workflow JSON] --> [Execution Engine]
[Manual Step-by-Step Flow Builder]    --/
```

Benefits of this unified architecture:
- **Zero Duplication**: A single execution engine runs both visual forms and custom step flows.
- **Round-Trip Inspectability**: Visual forms can be inspected, fine-tuned, or converted into custom step-by-step flows where individual low-level actions can be modified.
- **Enterprise Storage & Version Control**: Workflows are stored as declarative JSON files that can be checked into Git, audited by enterprise security, or synced across corporate branches.

### 2.2 Atomic Action Primitives (10 Core Actions)

The kutomoto engine executes workflows composed of 10 atomic, well-defined action primitives:

| Action Type | Description | Key Parameters |
|:---|:---|:---|
| `focus_window` | Brings target application window to front and activates focus | `window_title_pattern`, `process_name`, `timeout_ms`, `restore_if_minimized` |
| `click` | Dispatches mouse click (left, double, right, middle) | `x`, `y`, `coordinate_mode` (`screen` \| `window_client` \| `normalized`), `button`, `click_count` |
| `type_text` | Types string into focused element with keystroke pacing | `text`, `keystroke_delay_ms`, `is_secret`, `interpolate_variables` |
| `key_press` | Sends special keyboard key (Tab, Enter, Escape, Arrows) | `key` (`tab`, `enter`, `escape`, `backspace`, `space`, etc.), `repeat_count` |
| `hotkey` | Sends keyboard shortcut combination | `keys` (e.g. `["ctrl", "a"]`, `["ctrl", "v"]`, `["alt", "tab"]`) |
| `clear_field` | Emits field clearing sequence before typing | `strategy` (`select_all_backspace`, `triple_click_delete`, `backspace_repeat`) |
| `delay` | Pauses execution for UI rendering or network waiting | `duration_ms` |
| `submit` | Triggers form submission (Enter or coordinate click) | `method` (`enter_key` \| `button_click`), `button_coords`, `post_submit_wait_ms` |
| `scroll` | Dispatches vertical/horizontal mouse wheel scroll | `delta_x`, `delta_y`, `target_x`, `target_y` |
| `prompt_user_input` | Halts execution to prompt operator for dynamic value | `variable_name`, `prompt_message`, `is_password`, `default_value` |

### 2.3 Formal Workflow JSON Schema (Draft 7 / 2020-12)

Below is the complete, normative JSON Schema defining the kutomoto Workflow representation:

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
      "required": ["type"],
      "properties": {
        "type": { "type": "string", "enum": ["web_browser", "windows_desktop", "any"] },
        "window_title_pattern": { "type": "string" },
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
      "description": "Optional metadata preserving visual designer canvas state",
      "properties": {
        "canvas_width": { "type": "number" },
        "canvas_height": { "type": "number" },
        "background_image_path": { "type": "string" },
        "boxes": { "type": "array", "items": { "type": "object" } }
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
                "default": "window_client" 
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

### 2.4 Concrete JSON Example of Compiled Workflow

Below is a valid instance of a compiled Banking KYC onboarding flow:

```json
{
  "schema_version": "1.0.0",
  "id": "7b8e19d2-3140-4968-a40e-7d6f5c88102a",
  "name": "Corporate KYC Account Verification Flow",
  "description": "Automates account holder and TIN entry in Core Banking Portal",
  "author": "90Studio Enterprise Template",
  "created_at": "2026-11-04T22:15:00Z",
  "updated_at": "2026-11-04T22:15:00Z",
  "copyright": "Copyrights reserved to 90Studio",
  "source_mode": "visual_designer_generated",
  "target_application": {
    "type": "web_browser",
    "window_title_pattern": "Corporate Banking Portal",
    "match_mode": "contains"
  },
  "execution_settings": {
    "countdown_seconds": 3,
    "default_step_delay_ms": 120,
    "typing_speed_ms": 25,
    "stop_on_error": true,
    "error_recovery_policy": "retry_step",
    "max_step_retries": 2,
    "failsafe_corner_enabled": true,
    "abort_hotkey": "Escape"
  },
  "variables": [
    { "name": "customer_name", "description": "Legal Business Name", "default_value": "Acme Global Corp" },
    { "name": "tax_id", "description": "Federal Tax Identification Number", "default_value": "99-1234567" }
  ],
  "steps": [
    {
      "step_id": "00000001-0000-0000-0000-000000000001",
      "sequence_index": 1,
      "label": "Focus Banking Window",
      "action_type": "focus_window",
      "enabled": true,
      "pre_delay_ms": 0,
      "post_delay_ms": 300,
      "parameters": {
        "window_title_pattern": "Corporate Banking Portal"
      }
    },
    {
      "step_id": "00000001-0000-0000-0000-000000000002",
      "sequence_index": 2,
      "label": "Click 'Customer Name' Field",
      "action_type": "click",
      "enabled": true,
      "pre_delay_ms": 50,
      "post_delay_ms": 100,
      "parameters": {
        "norm_x": 0.325,
        "norm_y": 0.240,
        "coordinate_mode": "normalized",
        "button": "left",
        "click_count": 1
      }
    },
    {
      "step_id": "00000001-0000-0000-0000-000000000003",
      "sequence_index": 3,
      "label": "Clear Existing Name Input",
      "action_type": "clear_field",
      "enabled": true,
      "pre_delay_ms": 0,
      "post_delay_ms": 50,
      "parameters": {
        "clear_strategy": "select_all_backspace"
      }
    },
    {
      "step_id": "00000001-0000-0000-0000-000000000004",
      "sequence_index": 4,
      "label": "Type Customer Name",
      "action_type": "type_text",
      "enabled": true,
      "pre_delay_ms": 0,
      "post_delay_ms": 100,
      "parameters": {
        "text": "{{customer_name}}",
        "keystroke_delay_ms": 25,
        "is_secret": false
      }
    },
    {
      "step_id": "00000001-0000-0000-0000-000000000005",
      "sequence_index": 5,
      "label": "Tab to Tax ID Field",
      "action_type": "key_press",
      "enabled": true,
      "pre_delay_ms": 0,
      "post_delay_ms": 120,
      "parameters": {
        "key": "tab",
        "repeat_count": 1
      }
    },
    {
      "step_id": "00000001-0000-0000-0000-000000000006",
      "sequence_index": 6,
      "label": "Type Tax ID",
      "action_type": "type_text",
      "enabled": true,
      "pre_delay_ms": 0,
      "post_delay_ms": 150,
      "parameters": {
        "text": "{{tax_id}}",
        "keystroke_delay_ms": 25,
        "is_secret": false
      }
    },
    {
      "step_id": "00000001-0000-0000-0000-000000000007",
      "sequence_index": 7,
      "label": "Submit Form via Enter Key",
      "action_type": "submit",
      "enabled": true,
      "pre_delay_ms": 100,
      "post_delay_ms": 1000,
      "parameters": {
        "submit_method": "enter_key"
      }
    }
  ]
}
```

---

## 3. Visual-to-Workflow Compilation & Translation Algorithm

### 3.1 Compilation Pipeline Overview

The translation engine transforms unordered spatial visual boxes into an ordered, executable, timing-optimized action workflow. The compilation pipeline operates in 5 deterministic passes:

```
+-------------------------------------------------------------------------------+
| Phase 1: Validation & Integrity Check                                         |
| - Verify bounding boxes, ensure unique IDs, validate types & variables       |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Phase 2: Sequence Ordering & Topological Sorting                             |
| - Sort by explicit sequence_index OR 2D spatial reading-order band sort      |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Phase 3: Traversal Strategy Selection                                         |
| - Strategy A: Explicit Coordinate Focus (High Reliability)                    |
| - Strategy B: Tab-Chain Fast-Fill (High Speed Keyboard Navigation)           |
| - Strategy C: Hybrid Adaptive (Tab for adjacent text, Click for far/controls) |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Phase 4: Atomic Step Generation & Coordinate Synthesis                        |
| - Synthesize center coordinates, clear operations, typing pacing, navigation  |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Phase 5: Peephole Optimization & Safety Post-Processing                       |
| - Merge redundant delays, inject failsafe checks, validate step reachability  |
+-------------------------------------------------------------------------------+
```

### 3.2 Formal Algorithm Specification

#### Algorithm 1: Visual-to-Workflow Compilation (`CompileVisualBoxesToWorkflow`)

```python
"""
Translation Algorithm: Visual Boxes to Executable Action Workflow
Author: explorer_survey_3
Copyright: Copyrights reserved to 90Studio
"""
import uuid
from typing import List, Dict, Any, Optional

def compile_visual_boxes_to_workflow(
    boxes: List[Dict[str, Any]],
    workflow_metadata: Dict[str, Any],
    traversal_mode: str = "coordinate_targeted", # "coordinate_targeted" | "tab_chained" | "hybrid"
    canvas_dimensions: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Translates an array of visual FormBox definitions into a fully validated
    and executable kutomoto Action Workflow.
    """
    # -------------------------------------------------------------
    # PASS 1: Integrity Validation
    # -------------------------------------------------------------
    if not boxes:
        raise ValueError("Cannot compile workflow: visual box list is empty.")
    
    validated_boxes = []
    seen_ids = set()
    for idx, b in enumerate(boxes):
        box_id = b.get("id") or str(uuid.uuid4())
        if box_id in seen_ids:
            box_id = str(uuid.uuid4())
        seen_ids.add(box_id)
        
        bounds = b.get("bounds", {})
        w = bounds.get("width", 0)
        h = bounds.get("height", 0)
        if w <= 0 or h <= 0:
            raise ValueError(f"Box '{b.get('name', idx)}' has invalid zero or negative dimensions.")
        
        # Calculate center normalized coordinates
        norm_x = bounds.get("norm_x", 0.0)
        norm_y = bounds.get("norm_y", 0.0)
        norm_w = bounds.get("norm_w", 0.0)
        norm_h = bounds.get("norm_h", 0.0)
        center_norm_x = round(norm_x + (norm_w / 2.0), 4)
        center_norm_y = round(norm_y + (norm_h / 2.0), 4)
        
        validated_boxes.append({
            **b,
            "id": box_id,
            "center_norm_x": center_norm_x,
            "center_norm_y": center_norm_y,
            "bounds": bounds
        })

    # -------------------------------------------------------------
    # PASS 2: Sequence Ordering
    # -------------------------------------------------------------
    # If all boxes have positive sequence_index, sort by sequence_index.
    # Otherwise, fallback to spatial reading order (Top-to-Bottom, Left-to-Right).
    has_explicit_indices = all(b.get("sequence_index", 0) > 0 for b in validated_boxes)
    
    if has_explicit_indices:
        ordered_boxes = sorted(validated_boxes, key=lambda x: x["sequence_index"])
    else:
        # 2D Spatial Band Sort:
        # Group into bands using vertical threshold (median height * 0.75)
        median_h = sorted([b["bounds"].get("norm_h", 0.05) for b in validated_boxes])[len(validated_boxes)//2]
        band_threshold = median_h * 0.75
        
        # Sort primarily by Y
        sorted_by_y = sorted(validated_boxes, key=lambda b: b["bounds"].get("norm_y", 0.0))
        bands = []
        current_band = [sorted_by_y[0]]
        
        for b in sorted_by_y[1:]:
            prev_y = current_band[-1]["bounds"].get("norm_y", 0.0)
            curr_y = b["bounds"].get("norm_y", 0.0)
            if abs(curr_y - prev_y) <= band_threshold:
                current_band.append(b)
            else:
                bands.append(current_band)
                current_band = [b]
        bands.append(current_band)
        
        ordered_boxes = []
        for band in bands:
            # Sort each horizontal band left-to-right
            band_sorted = sorted(band, key=lambda b: b["bounds"].get("norm_x", 0.0))
            ordered_boxes.extend(band_sorted)

    # -------------------------------------------------------------
    # PASS 3 & 4: Step Generation
    # -------------------------------------------------------------
    steps: List[Dict[str, Any]] = []
    step_counter = 1
    
    # 3.1 Initial Target Window Focus Step
    target_info = workflow_metadata.get("target_application", {})
    steps.append({
        "step_id": str(uuid.uuid4()),
        "sequence_index": step_counter,
        "label": f"Activate Window: {target_info.get('window_title_pattern', 'Target Application')}",
        "action_type": "focus_window",
        "enabled": True,
        "pre_delay_ms": 0,
        "post_delay_ms": 250,
        "parameters": {
            "window_title_pattern": target_info.get("window_title_pattern", ""),
            "process_name": target_info.get("process_name", "")
        }
    })
    step_counter += 1

    # 3.2 Form Box Action Synthesis
    for i, box in enumerate(ordered_boxes):
        field_type = box.get("field_type", "text")
        val_cfg = box.get("value_config", {})
        nav_action = box.get("navigation_action", "tab")
        timing = box.get("timing", {})
        pre_delay = timing.get("pre_delay_ms", 100)
        post_delay = timing.get("post_delay_ms", 120)
        typing_speed = timing.get("typing_speed_ms", 20)
        
        # Decide whether mouse click is required
        # Mode 'coordinate_targeted': click every box.
        # Mode 'tab_chained': click only first box, tab for remainder unless button/checkbox.
        requires_click = True
        if traversal_mode == "tab_chained" and i > 0 and field_type in ("text", "number", "date", "textarea"):
            requires_click = False
        
        # Emit Focus / Click Step if needed
        if requires_click:
            steps.append({
                "step_id": str(uuid.uuid4()),
                "sequence_index": step_counter,
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
            step_counter += 1

        # Emit Clear Field Step if text field and configured
        if field_type in ("text", "number", "date", "textarea") and val_cfg.get("clear_before_type", True):
            steps.append({
                "step_id": str(uuid.uuid4()),
                "sequence_index": step_counter,
                "label": f"Clear Field [{box.get('name')}]",
                "action_type": "clear_field",
                "enabled": True,
                "pre_delay_ms": 0,
                "post_delay_ms": 40,
                "parameters": {
                    "clear_strategy": "select_all_backspace"
                }
            })
            step_counter += 1

        # Emit Value Input Step
        if field_type in ("text", "number", "date", "textarea"):
            # Determine text payload
            text_value = ""
            if val_cfg.get("source_type") == "variable":
                var_name = val_cfg.get("variable_name", box.get("name"))
                text_value = f"{{{{{var_name}}}}}"
            elif val_cfg.get("source_type") == "runtime_prompt":
                # Inject interactive prompt step before typing
                var_name = box.get("name")
                steps.append({
                    "step_id": str(uuid.uuid4()),
                    "sequence_index": step_counter,
                    "label": f"Prompt User for [{box.get('label')}]",
                    "action_type": "prompt_user_input",
                    "enabled": True,
                    "pre_delay_ms": 0,
                    "post_delay_ms": 50,
                    "parameters": {
                        "variable_name": var_name,
                        "prompt_message": f"Enter value for {box.get('label')}:"
                    }
                })
                step_counter += 1
                text_value = f"{{{{{var_name}}}}}"
            elif val_cfg.get("source_type") == "generated":
                gen = val_cfg.get("generator_pattern", "timestamp_iso")
                text_value = f"{{{{${gen}}}}}"
            else:
                text_value = val_cfg.get("static_value", "")

            steps.append({
                "step_id": str(uuid.uuid4()),
                "sequence_index": step_counter,
                "label": f"Type Value into [{box.get('name')}]",
                "action_type": "type_text",
                "enabled": True,
                "pre_delay_ms": 0,
                "post_delay_ms": post_delay,
                "parameters": {
                    "text": text_value,
                    "keystroke_delay_ms": typing_speed,
                    "is_secret": val_cfg.get("is_secret", False)
                }
            })
            step_counter += 1

        elif field_type == "checkbox":
            # Checkbox click already focused it; toggle via Spacebar or left click
            steps.append({
                "step_id": str(uuid.uuid4()),
                "sequence_index": step_counter,
                "label": f"Toggle Checkbox [{box.get('name')}]",
                "action_type": "key_press",
                "enabled": True,
                "pre_delay_ms": 0,
                "post_delay_ms": post_delay,
                "parameters": { "key": "space", "repeat_count": 1 }
            })
            step_counter += 1

        elif field_type == "submit_button":
            steps.append({
                "step_id": str(uuid.uuid4()),
                "sequence_index": step_counter,
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
            step_counter += 1
            continue  # Do not append navigation after submit button

        # Emit Navigation Step (Tab or Enter)
        if nav_action == "tab":
            steps.append({
                "step_id": str(uuid.uuid4()),
                "sequence_index": step_counter,
                "label": f"Navigation: Tab from [{box.get('name')}]",
                "action_type": "key_press",
                "enabled": True,
                "pre_delay_ms": 0,
                "post_delay_ms": 100,
                "parameters": { "key": "tab", "repeat_count": 1 }
            })
            step_counter += 1
        elif nav_action == "enter":
            steps.append({
                "step_id": str(uuid.uuid4()),
                "sequence_index": step_counter,
                "label": f"Navigation: Enter from [{box.get('name')}]",
                "action_type": "key_press",
                "enabled": True,
                "pre_delay_ms": 0,
                "post_delay_ms": 250,
                "parameters": { "key": "enter", "repeat_count": 1 }
            })
            step_counter += 1

    # -------------------------------------------------------------
    # PASS 5: Peephole Optimization
    # -------------------------------------------------------------
    optimized_steps = []
    for s in steps:
        # Deduplicate consecutive delays by merging duration
        if optimized_steps and optimized_steps[-1]["action_type"] == "delay" and s["action_type"] == "delay":
            optimized_steps[-1]["parameters"]["duration_ms"] += s["parameters"]["duration_ms"]
        else:
            optimized_steps.append(s)

    # Re-index sequence cleanly
    for idx, s in enumerate(optimized_steps):
        s["sequence_index"] = idx + 1

    # Build final action workflow document
    workflow = {
        "schema_version": "1.0.0",
        "id": workflow_metadata.get("id", str(uuid.uuid4())),
        "name": workflow_metadata.get("name", "Generated Visual Form Workflow"),
        "description": workflow_metadata.get("description", "Compiled from kutomoto Visual Form Designer"),
        "author": workflow_metadata.get("author", "kutomoto Visual Designer"),
        "created_at": workflow_metadata.get("created_at", "2026-11-04T22:15:00Z"),
        "updated_at": "2026-11-04T22:15:00Z",
        "copyright": "Copyrights reserved to 90Studio",
        "source_mode": "visual_designer_generated",
        "target_application": target_info,
        "execution_settings": workflow_metadata.get("execution_settings", {
            "countdown_seconds": 3,
            "default_step_delay_ms": 120,
            "typing_speed_ms": 20,
            "stop_on_error": True,
            "error_recovery_policy": "abort"
        }),
        "variables": workflow_metadata.get("variables", []),
        "designer_metadata": {
            "canvas_dimensions": canvas_dimensions or {"width": 1024, "height": 768},
            "box_count": len(ordered_boxes)
        },
        "steps": optimized_steps
    }
    
    return workflow
```

---

## 4. Execution Engine Runtime & State Machine

### 4.1 Target Application Attachment Strategies

Automating forms across Windows requires attaching to and targeting two distinct application environments:
1. **Web Browser Pages** (Google Chrome, Microsoft Edge, Mozilla Firefox)
2. **Native Windows Desktop Applications** (Win32, WinForms, WPF, Qt, Java Swing, SAP GUI)

To ensure maximum reliability without requiring invasive browser extensions or OS driver installations, kutomoto provides four complementary attachment strategies:

```
+-----------------------------------------------------------------------------------------+
| Target Attachment Strategies in kutomoto                                                |
+-----------------------------------------------------------------------------------------+
| 1. Window Title Regex Matching      | Scans open top-level Windows via EnumWindows API. |
|                                     | Matches against title (e.g. "*Core Banking*").     |
| 2. Process Executable Filter        | Scans process list by name (e.g. "msedge.exe",     |
|                                     | "crm_client.exe") and picks active main window.   |
| 3. Interactive Countdown HUD        | Displays a 3-second floating HUD countdown        |
|                                     | ("Switch to target form... 3.. 2.. 1.."). User     |
|                                     | clicks target window; kutomoto locks foreground!  |
| 4. Global Hotkey In-Place Trigger   | User activates target window directly, then       |
|                                     | presses F9 or Ctrl+Alt+K to execute immediately.  |
+-----------------------------------------------------------------------------------------+
```

#### Windows OS Focus Restoration Mechanics
Under Windows 10/11, OS "Focus Stealing Prevention" can prevent background windows from bringing themselves to the foreground via a simple `SetForegroundWindow`. 

Kutomoto solves this via the canonical Windows API pattern:
```python
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def force_activate_window(hwnd: int) -> bool:
    """
    Activates and brings target window to foreground reliably on Windows OS
    by temporarily attaching thread input to the current foreground thread.
    """
    if not user32.IsWindow(hwnd):
        return False
        
    foreground_hwnd = user32.GetForegroundWindow()
    if foreground_hwnd == hwnd:
        return True
        
    foreground_thread = user32.GetWindowThreadProcessId(foreground_hwnd, None)
    current_thread = kernel32.GetCurrentThreadId()
    
    # Attach input queues to bypass focus-stealing prevention
    attached = False
    if foreground_thread != current_thread:
        attached = bool(user32.AttachThreadInput(current_thread, foreground_thread, True))
        
    try:
        user32.ShowWindow(hwnd, 9) # SW_RESTORE
        user32.BringWindowToTop(hwnd)
        success = bool(user32.SetForegroundWindow(hwnd))
    finally:
        if attached:
            user32.AttachThreadInput(current_thread, foreground_thread, False)
            
    return success
```

### 4.2 Execution State Machine

The kutomoto execution runtime is governed by a deterministic, non-blocking finite state machine (FSM).

```
          [Start Execution]
                  |
                  v
             +----------+
             |   IDLE   |
             +----------+
                  |
             (Validate)
                  v
         +-----------------+
         |   VALIDATING    |---[Validation Error]---> [ ERROR ]
         +-----------------+
                  |
          (Target Located)
                  v
         +-----------------+
         |    COUNTDOWN    |---[User Abort (Esc)]---> [ STOPPED ]
         +-----------------+
                  |
        (Countdown Expired)
                  v
         +-----------------+       [Pause Hotkey / Dialog]      +----------+
         |     RUNNING     |<==================================>|  PAUSED  |
         +-----------------+                                    +----------+
            |      |     |                                           |
    (Step Err)     |   (Done)                                  (User Abort)
            |      |     |                                           v
            v      |     +-----------------------------------> [ STOPPED ]
   +-------------+ |
   | ERROR_RECOV | |
   +-------------+ |
     |         |   |
(Retry/Skip) (Abort)
     |         |   |
     v         v   v
[ RUNNING ]   [ ERROR ] [ COMPLETED ]
```

#### State Transition Matrix

| Current State | Trigger Event | Next State | Action / Side Effect |
|:---|:---|:---|:---|
| `IDLE` | `EXECUTE_START` | `VALIDATING` | Check schema, compile variables, inspect target window availability |
| `VALIDATING` | `VALIDATION_OK` | `COUNTDOWN` | Launch Countdown Overlay HUD (e.g. 3s timer) |
| `VALIDATING` | `VALIDATION_FAILED`| `ERROR` | Log reason (missing variable, window not found), notify UI |
| `COUNTDOWN` | `COUNTDOWN_TICK` | `COUNTDOWN` | Update countdown HUD (3 -> 2 -> 1) |
| `COUNTDOWN` | `COUNTDOWN_DONE` | `RUNNING` | Activate target `hWnd`, initialize step loop at index 0 |
| `COUNTDOWN` | `ABORT_TRIGGERED`| `STOPPED` | Close HUD, release locks, reset to `IDLE` |
| `RUNNING` | `STEP_SUCCESS` | `RUNNING` | Advance `step_index += 1`, wait `inter_step_delay` |
| `RUNNING` | `ALL_STEPS_DONE` | `COMPLETED` | Emit audit log, play success chime, return focus |
| `RUNNING` | `USER_PAUSE` | `PAUSED` | Halt loop timer, show floating "PAUSED" badge |
| `RUNNING` | `USER_ABORT` | `STOPPING` | Cancel current keystroke queue, transition to `STOPPED` |
| `RUNNING` | `STEP_EXCEPTION` | `ERROR_RECOV`| Check `error_recovery_policy` (`retry`, `prompt`, `skip`, `abort`) |
| `PAUSED` | `USER_RESUME` | `RUNNING` | Re-verify target window focus, resume step loop |
| `PAUSED` | `USER_ABORT` | `STOPPED` | Abort flow, flush partial execution log |
| `ERROR_RECOV`| `RETRY_ATTEMPT` | `RUNNING` | Decrement retry counter, wait backoff delay, re-dispatch step |
| `ERROR_RECOV`| `SKIP_STEP` | `RUNNING` | Log step warning, increment `step_index += 1` |
| `ERROR_RECOV`| `ABORT_FATAL` | `ERROR` | Flush error details to audit log, notify UI |

### 4.3 Asynchronous Non-Blocking Execution Loop

The engine runs on a dedicated worker thread or asynchronous event loop (e.g., Python `asyncio` or Node.js event loop) to ensure the UI remains 100% responsive during automation.

```python
"""
Execution Loop Engine Core
Author: explorer_survey_3
Copyright: Copyrights reserved to 90Studio
"""
import time
import asyncio
from typing import Dict, Any, Callable

class KutomotoExecutionEngine:
    def __init__(self, platform_driver, audit_logger):
        self.driver = platform_driver      # Win32 SendInput / Mouse / Keyboard driver
        self.logger = audit_logger        # Compliance Audit Logger
        self.state = "IDLE"
        self._pause_event = asyncio.Event()
        self._pause_event.set()           # Set = running, Clear = paused
        self._stop_requested = False

    async def execute_workflow(
        self, 
        workflow: Dict[str, Any], 
        runtime_variables: Dict[str, str],
        on_step_callback: Optional[Callable[[int, str, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes an action workflow asynchronously with non-blocking delays
        and real-time safety telemetry.
        """
        self.state = "RUNNING"
        self._stop_requested = False
        steps = workflow.get("steps", [])
        total_steps = len(steps)
        settings = workflow.get("execution_settings", {})
        default_delay = settings.get("default_step_delay_ms", 120) / 1000.0
        
        exec_record = {
            "workflow_id": workflow["id"],
            "workflow_name": workflow["name"],
            "start_time": time.time(),
            "completed_steps": 0,
            "status": "IN_PROGRESS",
            "step_logs": []
        }
        
        target_hwnd = None
        
        for idx, step in enumerate(steps):
            # 1. Check for cancellation / emergency abort
            if self._stop_requested:
                self.state = "STOPPED"
                exec_record["status"] = "ABORTED"
                break
                
            # 2. Check for pause state
            await self._pause_event.wait()
            
            step_id = step["step_id"]
            action_type = step["action_type"]
            params = step.get("parameters", {})
            label = step.get("label", f"Step {idx+1}")
            
            if on_step_callback:
                on_step_callback(idx + 1, total_steps, label)
                
            step_start = time.time()
            step_status = "SUCCESS"
            error_msg = None
            
            try:
                # Pre-step delay
                pre_delay = step.get("pre_delay_ms", 0) / 1000.0
                if pre_delay > 0:
                    await asyncio.sleep(pre_delay)

                # Pre-flight window focus verification
                if target_hwnd and action_type not in ("focus_window", "delay"):
                    if not self.driver.is_window_active(target_hwnd):
                        # Re-activate target window
                        self.driver.activate_window(target_hwnd)
                        await asyncio.sleep(0.1)

                # Execute atomic action
                if action_type == "focus_window":
                    target_hwnd = self.driver.find_and_activate_window(
                        params.get("window_title_pattern"),
                        params.get("process_name")
                    )
                elif action_type == "click":
                    self.driver.dispatch_click(
                        norm_x=params.get("norm_x"),
                        norm_y=params.get("norm_y"),
                        hwnd=target_hwnd,
                        button=params.get("button", "left"),
                        clicks=params.get("click_count", 1)
                    )
                elif action_type == "clear_field":
                    self.driver.dispatch_clear_field(params.get("clear_strategy"))
                elif action_type == "type_text":
                    raw_text = params.get("text", "")
                    # Variable interpolation
                    interpolated_text = self._interpolate(raw_text, runtime_variables)
                    self.driver.dispatch_type_text(
                        text=interpolated_text,
                        keystroke_delay_ms=params.get("keystroke_delay_ms", 20)
                    )
                elif action_type == "key_press":
                    self.driver.dispatch_key_press(
                        key=params.get("key"),
                        repeat=params.get("repeat_count", 1)
                    )
                elif action_type == "submit":
                    if params.get("submit_method") == "enter_key":
                        self.driver.dispatch_key_press("enter", 1)
                    else:
                        self.driver.dispatch_click(
                            norm_x=params.get("norm_x"),
                            norm_y=params.get("norm_y"),
                            hwnd=target_hwnd
                        )
                elif action_type == "delay":
                    await asyncio.sleep(params.get("duration_ms", 500) / 1000.0)

                # Post-step delay
                post_delay = step.get("post_delay_ms", 0) / 1000.0
                await asyncio.sleep(post_delay if post_delay > 0 else default_delay)

            except Exception as ex:
                step_status = "ERROR"
                error_msg = str(ex)
                if settings.get("stop_on_error", True):
                    self.state = "ERROR"
                    exec_record["status"] = "FAILED"
                    exec_record["error"] = error_msg
                    break

            finally:
                step_duration = round((time.time() - step_start) * 1000, 2)
                exec_record["step_logs"].append({
                    "step_index": idx + 1,
                    "action_type": action_type,
                    "label": label,
                    "duration_ms": step_duration,
                    "status": step_status,
                    "error": error_msg
                })

        if exec_record["status"] == "IN_PROGRESS":
            exec_record["status"] = "COMPLETED"
            self.state = "COMPLETED"
            
        exec_record["end_time"] = time.time()
        exec_record["total_duration_sec"] = round(exec_record["end_time"] - exec_record["start_time"], 2)
        
        # Persist tamper-evident enterprise log
        self.logger.log_execution(exec_record)
        return exec_record

    def _interpolate(self, text: str, vars: Dict[str, str]) -> str:
        res = text
        for k, v in vars.items():
            res = res.replace(f"{{{{{k}}}}}", str(v))
        return res
        
    def pause(self):
        self._pause_event.clear()
        self.state = "PAUSED"
        
    def resume(self):
        self._pause_event.set()
        self.state = "RUNNING"
        
    def abort(self):
        self._stop_requested = True
        self._pause_event.set() # Unpause to exit loop immediately
```

---

## 5. Error Handling, Safety Guardrails & Audit Logging

### 5.1 Enterprise Safety Guardrails

Automating keyboard and mouse operations in live banking, telecom, or corporate environments carries inherent risks if unconstrained. Kutomoto enforces **Four Layers of Hardened Safety Guardrails**:

1. **Corner Failsafe Trigger (Hardware Fail-Safe)**:
   - Built directly into the mouse driver loop: If the operator slams the physical mouse into the top-left coordinate $(0, 0)$ of the primary screen, the engine immediately terminates input dispatch and transitions to `STOPPED`.
2. **Global Emergency Abort Hotkey**:
   - Registered at the OS level via `RegisterHotKey` (Win32): Pressing `Escape` (or user-configured hotkey like `Pause/Break` or `Ctrl+Alt+Q`) instantly aborts in-flight keystrokes and releases any pressed modifier keys (`Ctrl`, `Alt`, `Shift`).
3. **Loss-of-Focus Guard**:
   - Before dispatching any click or typing action, the engine inspects `GetForegroundWindow()`. If the user accidentally clicked outside the target window (e.g. an unexpected email popup or notification stole focus), the engine immediately pauses rather than blindly typing sensitive data into an unintended application.
4. **Credential Masking & Memory Security**:
   - Steps marked with `is_secret: true` (e.g. passwords, customer PINs, credit card numbers, SSNs) are masked in all execution logs and UI telemetry with `********`.
   - Variable values marked secret are scrubbed from memory buffers upon workflow termination.

### 5.2 Error Recovery Policies

Workflows can be configured with four distinct recovery policies on step failure:

```
+------------------------------------------------------------------------------------+
| Error Recovery Policies                                                            |
+------------------------------------------------------------------------------------+
| 1. ABORT_ON_FAILURE (Default)  | Halt execution immediately. Log error with exact  |
|                                | line, step, and screenshot. Leave form intact.    |
| 2. RETRY_STEP                  | Automatically attempt re-focus and re-dispatch of |
|                                | current step up to N times (default 2) with 250ms |
|                                | exponential backoff before failing.               |
| 3. PROMPT_OPERATOR             | Suspends workflow into PAUSED state and renders a |
|                                | modal dialog: [Retry Step] [Skip Step] [Abort].   |
| 4. SKIP_STEP                   | Logs a WARNING entry in the audit trail and       |
|                                | proceeds to the subsequent step.                  |
+------------------------------------------------------------------------------------+
```

### 5.3 Enterprise Audit Trail Schema (90Studio Standard)

In regulated enterprise environments (Banking KYC, Telecom provisioning), every automated action must be fully auditable for compliance and incident investigations.

Every workflow execution produces a structured JSON audit log saved to `logs/audit_YYYYMMDD_HHMMSS_<id>.json`:

```json
{
  "audit_version": "1.0",
  "system": "kutomoto",
  "copyright": "Copyrights reserved to 90Studio",
  "execution_id": "c92d5218-12f8-4e89-9a25-b467ef8741da",
  "workflow_id": "7b8e19d2-3140-4968-a40e-7d6f5c88102a",
  "workflow_name": "Corporate KYC Account Verification Flow",
  "timestamp_utc": "2026-11-04T22:18:32.410Z",
  "operator_username": "enterprise_teller_04",
  "host_machine": "CORP-W11-B042",
  "target_application": {
    "title": "Corporate Banking Portal - Google Chrome",
    "hwnd": 196840,
    "process_name": "chrome.exe",
    "pid": 14220
  },
  "execution_summary": {
    "total_steps": 7,
    "successful_steps": 7,
    "failed_steps": 0,
    "retried_steps": 0,
    "duration_seconds": 4.15,
    "final_status": "SUCCESS"
  },
  "step_events": [
    {
      "step_index": 1,
      "action_type": "focus_window",
      "timestamp_offset_ms": 15,
      "parameters_summary": "pattern='Corporate Banking Portal'",
      "latency_ms": 254,
      "status": "SUCCESS"
    },
    {
      "step_index": 2,
      "action_type": "click",
      "timestamp_offset_ms": 270,
      "parameters_summary": "norm_coords=(0.325, 0.240), button=left",
      "latency_ms": 62,
      "status": "SUCCESS"
    },
    {
      "step_index": 3,
      "action_type": "clear_field",
      "timestamp_offset_ms": 335,
      "parameters_summary": "strategy=select_all_backspace",
      "latency_ms": 41,
      "status": "SUCCESS"
    },
    {
      "step_index": 4,
      "action_type": "type_text",
      "timestamp_offset_ms": 380,
      "parameters_summary": "text='Acme Global Corp' (16 chars)",
      "latency_ms": 398,
      "status": "SUCCESS"
    },
    {
      "step_index": 5,
      "action_type": "key_press",
      "timestamp_offset_ms": 782,
      "parameters_summary": "key=tab, count=1",
      "latency_ms": 102,
      "status": "SUCCESS"
    },
    {
      "step_index": 6,
      "action_type": "type_text",
      "timestamp_offset_ms": 888,
      "parameters_summary": "text='99-1234567' (10 chars)",
      "latency_ms": 248,
      "status": "SUCCESS"
    },
    {
      "step_index": 7,
      "action_type": "submit",
      "timestamp_offset_ms": 1140,
      "parameters_summary": "method=enter_key",
      "latency_ms": 1012,
      "status": "SUCCESS"
    }
  ]
}
```

---

## 6. Synthesis & Implementation Recommendations for Milestone Planners

Based on the survey findings, the following concrete recommendations are provided to the Orchestrator for task decomposition and milestone scheduling:

1. **Engine Decoupling**:
   Keep the Workflow Engine (`kutomoto.engine`) strictly separated from UI rendering. The engine should accept plain JSON workflow objects and expose an async Python or Node API (`executeWorkflow(workflow, vars, callbacks)`).
2. **Unified Schema as the Source of Truth**:
   The JSON Schema documented in Section 2.3 should be stored as `schemas/workflow.schema.json` and used to validate all saved workflows, whether created via visual designer or custom manual flow.
3. **Dual Form-Filling Verification Test Suite**:
   Create two isolated, reproducible test fixtures:
   - **Sample Web Form**: A local HTML/JavaScript single-page application with customer KYC inputs, validation alerts, and submission feedback.
   - **Sample Desktop Form**: A standalone native Windows desktop application (e.g. lightweight Tkinter/PyQt or WinForms dialog) with account registration inputs and a submit button.
   These two targets will verify cross-platform automation primitives without external dependencies.
4. **Visual Designer Canvas Component**:
   The visual designer should be built as an interactive canvas component supporting backdrop screenshot upload, click-drag box placement, sequence badges, and real-time JSON compilation.
5. **Branding & Legal Notice Compliance**:
   Ensure all UI header bars, splash screens, about dialogs, schema metadata, and generated audit logs display:
   `kutomoto — Copyrights reserved to 90Studio`.

---
*End of Report — Delivered by explorer_survey_3*
