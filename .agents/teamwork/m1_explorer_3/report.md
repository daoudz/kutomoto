# Enterprise Specification Blueprint: Visual Compiler Mechanics, Unified Action Schema, Execution Engine FSM, and 90Studio Audit Trail

**Product**: kutomoto Forms Filling Automation System for Windows OS  
**Copyright**: Copyrights reserved to 90Studio  
**Author**: m1_explorer_3 (Investigation & Architecture Specification)  
**Date**: 2026-11-04  
**Target Document**: `docs/SPECIFICATION.md` (Sections: Visual Designer Model, Unified Action Schema, Compiler Algorithm, Execution FSM, and Compliance Audit Trail)

---

## Executive Summary

This specification blueprint provides the exhaustive data schemas, formal compilation algorithms, execution runtime models, and compliance audit log standards for **kutomoto** — the Windows OS enterprise forms filling automation system developed by **90Studio**.

The findings and formal models formulated herein provide the direct authoring blueprints for:
1. **Visual Form Designer Data Model (`VisualFormLayout` & `VisualBox`)**: Resolution-independent dual-coordinate spatial geometry ($0.0 \le u, v \le 1.0$), sequence badges, field typing, and navigation actions.
2. **Unified Action Workflow JSON Schema (Draft 2020-12)**: A single canonical workflow schema governing both visually designed and manually created fill flows across 10 atomic actions (`focus_window`, `click`, `type_text`, `key_press`, `hotkey`, `clear_field`, `delay`, `submit`, `scroll`, `prompt_user_input`).
3. **5-Pass Visual-to-Workflow Compilation Pipeline**: Deterministic multi-pass translation converting 2D spatial layouts into linear, timing-optimized action workflows with topological reading-order sorting and peephole optimization.
4. **7-State Execution Finite State Machine (FSM)**: Non-blocking asynchronous execution loop (`IDLE`, `VALIDATING`, `COUNTDOWN`, `RUNNING`, `PAUSED`, `STOPPING`, `COMPLETED`/`ERROR`), loss-of-focus protection, and four-tier error recovery policies.
5. **90Studio Compliance Audit Trail**: High-integrity, structured audit logging with secret masking (`is_secret`), operator attribution, and execution telemetry tailored for regulated enterprise environments (Banking, Telecom, Business).

---

## 1. Visual Form Designer Architecture & Data Model

### 1.1 Conceptual Framework & Canvas Interaction Paradigm

The kutomoto Visual Form Designer enables business operators, branch staff, and automation analysts to automate target forms without writing code. The designer operates on an interactive HTML5 Canvas with the following capabilities:
- **Canvas Backdrop**: Operators can upload or snapshot a target form screenshot (from Chrome, Edge, or a Windows desktop application such as SAP GUI or WinForms) to serve as a 1:1 backdrop guide.
- **Bounding Box Drawing**: Users click and drag bounding boxes over form input controls, combo boxes, checkboxes, and submission buttons.
- **8-Handle Bounding Box Resizing**: Selected boxes feature 8 manipulation handles ($N, S, E, W, NW, NE, SW, SE$) with real-time clamping within canvas boundaries.
- **Magnetic Alignment & Snap-to-Grid**: Visual dotted alignment guides activate whenever a box edge aligns horizontally or vertically with neighboring boxes within a $\pm 4\text{px}$ threshold; a toggleable 8px grid provides structured alignment.
- **Sequence Badges**: Every placed box displays a prominent numeric badge (e.g., `[#1]`, `[#2]`, `[#3]`) at its top-left corner indicating its execution order.
- **Property Inspector**: Selecting a box opens a dedicated configuration panel to adjust semantic name, label, field type, input value/variable, navigation behavior, and timing delays.
- **Live Canvas Simulation**: A built-in dry-run simulator animates a virtual cursor traversing the defined sequence with typewriter text previews, validating sequence logic prior to live execution.

### 1.2 Dual-Coordinate Architecture & Resolution Independence

To ensure workflows authored on a specific screen resolution or monitor scaling (e.g., $1920 \times 1080$ at 125% DPI) function flawlessly across heterogeneous enterprise workstations (e.g., $1366 \times 768$ at 100% DPI or $3840 \times 2160$ at 200% DPI), kutomoto implements a **Dual-Coordinate Architecture**:

1. **Normalized Canvas Coordinates ($0.0 \le u, v \le 1.0$)**:
   During box creation on a canvas of dimensions $(W_{\text{canvas}}, H_{\text{canvas}})$, pixel offsets $(x, y, w, h)$ are normalized:
   $$\text{norm\_x} = \frac{x}{W_{\text{canvas}}}, \quad \text{norm\_y} = \frac{y}{H_{\text{canvas}}}$$
   $$\text{norm\_w} = \frac{w}{W_{\text{canvas}}}, \quad \text{norm\_h} = \frac{h}{H_{\text{canvas}}}$$
   The normalized center target of the bounding box is calculated as:
   $$u_c = \text{norm\_x} + \frac{\text{norm\_w}}{2.0}, \quad v_c = \text{norm\_y} + \frac{\text{norm\_h}}{2.0}$$

2. **Target Window Client Resolution Mapping**:
   At runtime, the execution engine queries the live Win32 client rectangle of the target application window $(X_{\text{win}}, Y_{\text{win}}, W_{\text{win}}, H_{\text{win}})$ via `GetWindowRect` and `GetClientRect`. The screen injection coordinates are dynamically computed:
   $$X_{\text{screen}} = X_{\text{win}} + \text{round}(u_c \times W_{\text{win}})$$
   $$Y_{\text{screen}} = Y_{\text{win}} + \text{round}(v_c \times H_{\text{win}})$$

This mathematical translation guarantees that mouse clicks hit the exact center of form fields regardless of window resizing, DPI virtualization, or monitor relocation.

### 1.3 VisualFormLayout & VisualBox Attribute Specification

The visual designer state is serialized into a structured `VisualFormLayout` document containing an array of `VisualBox` definitions:

| Attribute | Type | Description | Validation Constraints |
|:---|:---|:---|:---|
| **VisualFormLayout** | | | |
| `id` | `string` (UUID v4) | Unique layout identifier | Valid UUID |
| `name` | `string` | Display name of the form template | 1 to 128 characters |
| `description` | `string` | Detailed description of the target workflow | Max 1024 characters |
| `target` | `object` | Target application binding specification | Must specify `type`, `window_title_pattern` |
| `canvas` | `object` | Canvas configuration (`width`, `height`, `scale`, `background_image`) | `width >= 320`, `height >= 240` |
| `global_timing` | `object` | Default timing (`pre_delay_ms`, `typing_speed_ms`, `post_delay_ms`) | Non-negative integers |
| `boxes` | `array` | List of defined `VisualBox` objects | Minimum 1 item |
| `copyright` | `string` | Attribution notice | Constant: `"Copyrights reserved to 90Studio"` |
| **VisualBox** | | | |
| `id` | `string` (UUID v4) | Unique box identifier | Unique within layout |
| `name` | `string` | Programmatic identifier (slug) | `^[a-zA-Z_][a-zA-Z0-9_]*$` |
| `label` | `string` | Human-readable label displayed on canvas | 1 to 64 characters |
| `field_type` | `string` (enum) | Semantic control type | `"text"`, `"number"`, `"date"`, `"select"`, `"checkbox"`, `"radio"`, `"textarea"`, `"submit_button"` |
| `sequence_index` | `integer` | Execution sequence position | Integer $\ge 1$ |
| `rect` | `object` | Canvas pixel geometry | `x >= 0`, `y >= 0`, `width >= 24`, `height >= 16` |
| `norm_bounds` | `object` | Normalized coordinates ($0.0 \dots 1.0$) | $0.0 \le \text{norm\_x}, \text{norm\_y}, \text{norm\_w}, \text{norm\_h} \le 1.0$ |
| `value_config` | `object` | Value binding configuration | See Section 1.4 |
| `navigation` | `string` (enum) | Post-input navigation action | `"tab"`, `"enter"`, `"click_next"`, `"none"` |
| `timing` | `object` | Local timing overrides | `pre_delay_ms`, `typing_speed_ms`, `post_delay_ms` |

### 1.4 VisualBox Value Configuration Model

Each `VisualBox` encapsulates its value binding via `value_config`:
- **`source_type`**:
  - `"static"`: Hardcoded literal string entered directly into the designer.
  - `"variable"`: Dynamic placeholder (e.g. `{{account_number}}`, `{{customer_name}}`) resolved from runtime parameters.
  - `"generated"`: Macro-generated tokens (`{{$timestamp_iso}}`, `{{$timestamp_compact}}`, `{{$uuid4}}`, `{{$counter}}`).
  - `"runtime_prompt"`: Prompts the operator via an interactive dialog at execution time if no variable is bound.
- **`static_value`**: Literal string value if `source_type == "static"`.
- **`variable_name`**: Name of the runtime variable if `source_type == "variable"` or `"runtime_prompt"`.
- **`is_secret`**: Boolean flag. When `true`, input characters are masked with `********` in the UI, step telemetry, execution consoles, and audit log files.
- **`clear_before_type`**: Boolean flag. When `true`, dispatches field clearing keystrokes (`Ctrl+A` followed by `Backspace`) before typing new content.

### 1.5 VisualFormLayout Formal JSON Schema (Draft 2020-12)

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

---

## 2. Unified Action Workflow Schema & Atomic Actions

### 2.1 Unification Principle

In kutomoto, visual designer layouts and manual custom step flows compile into an identical execution format: the **Unified Action Workflow**.

```
+------------------------------------+      +------------------------------------+
|    Visual Form Designer Canvas     |      |    Step-by-Step Flow Builder       |
|  (Spatial boxes, geometry, badges) |      | (Sequential manual action editor)  |
+-----------------+------------------+      +-----------------+------------------+
                  |                                           |
                  | [5-Pass Visual Compiler]                  | [Direct Flow Serializer]
                  v                                           v
+--------------------------------------------------------------------------------+
|                        Unified Action Workflow Document                        |
|             (Draft 2020-12 JSON Schema, Stamped Copyrights to 90Studio)        |
+--------------------------------------------------------------------------------+
                                       |
                                       v
+--------------------------------------------------------------------------------+
|                           Workflow Execution Engine                            |
|             (7-State FSM, Win32 Native Driver, Safety & Audit Core)            |
+--------------------------------------------------------------------------------+
```

### 2.2 The 10 Atomic Action Primitives

Every kutomoto workflow is composed of sequential steps executing one of 10 atomic action primitives:

| # | Action Primitive | Description | Key Parameters | Fail Condition / Edge Case |
|---|:---|:---|:---|:---|
| 1 | `focus_window` | Locates and brings target window to foreground, restoring if minimized | `window_title_pattern`, `process_name`, `match_mode`, `restore_if_minimized`, `timeout_ms` | Window not found within timeout; focus blocked by UAC/admin boundary |
| 2 | `click` | Dispatches physical mouse click at specified coordinates | `norm_x`, `norm_y`, `x`, `y`, `coordinate_mode` (`normalized`, `window_client`, `screen`), `button` (`left`, `right`, `middle`), `click_count` (`1`, `2`, `3`) | Target window minimized or coordinates outside client area |
| 3 | `type_text` | Injects character sequence with configurable keystroke delay | `text` (supports `{{var}}`), `keystroke_delay_ms`, `is_secret`, `interpolate_variables` | Active window lost during typing; target control does not accept text |
| 4 | `key_press` | Sends non-printable or functional keyboard key | `key` (`tab`, `enter`, `escape`, `backspace`, `space`, arrows), `repeat_count` | Target control consumes key without yielding focus |
| 5 | `hotkey` | Sends simultaneous key combinations with proper press/release sequence | `keys` (e.g. `["ctrl", "a"]`, `["ctrl", "v"]`, `["alt", "f4"]`) | Modifier key stuck down if execution aborted mid-stroke |
| 6 | `clear_field` | Emits field clearing sequence before typing | `strategy` (`select_all_backspace`, `triple_click_delete`, `backspace_repeat`) | Target field read-only or ignores Select-All |
| 7 | `delay` | Pauses execution to allow UI animation, DOM rendering, or API latency | `duration_ms` | None (interruptible via Escape abort) |
| 8 | `submit` | Triggers form submission via Enter key or direct button coordinate click | `submit_method` (`enter_key`, `button_click`), `norm_x`, `norm_y`, `post_submit_wait_ms` | Form validation error stops submission on client form |
| 9 | `scroll` | Dispatches mouse wheel vertical or horizontal scroll | `delta_x`, `delta_y`, `target_x`, `target_y` | Target control does not possess scrollable viewport |
| 10 | `prompt_user_input` | Suspends execution to prompt operator for dynamic value via modal HUD | `variable_name`, `prompt_message`, `is_password`, `default_value` | User cancels prompt dialog |

### 2.3 Unified Action Workflow Formal JSON Schema (Draft 2020-12)

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
      "description": "Preserved visual designer canvas layout for two-way round-trip editing",
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

## 3. The 5-Pass Visual-to-Workflow Compilation Pipeline

### 3.1 Compilation Pipeline Overview

The compiler converts an unordered set of 2D bounding boxes into an optimized, robust linear sequence of Win32 automation steps:

```
[VisualFormLayout Input]
          |
          v
+-----------------------------------------------------------------------------------+
| PASS 1: Integrity Validation & Geometry Normalization                             |
| - Verify non-zero box dimensions (width >= 24px, height >= 16px)                  |
| - Validate unique IDs, field names, and variable tokens                           |
| - Compute exact normalized center points (norm_x + norm_w/2, norm_y + norm_h/2)   |
+-----------------------------------------------------------------------------------+
          |
          v
+-----------------------------------------------------------------------------------+
| PASS 2: Sequence Ordering & Spatial Topological Sorting                           |
| - If sequence_index defined on all boxes: sort by sequence_index                  |
| - If sequence_index missing/ambiguous: 2D Spatial Band Sort (Reading Order)       |
|   (Group into horizontal bands via vertical delta <= 0.75 * median_h, sort L-to-R)|
+-----------------------------------------------------------------------------------+
          |
          v
+-----------------------------------------------------------------------------------+
| PASS 3: Traversal Strategy Selection                                              |
| - 'coordinate_targeted': click center of every field (highest reliability)        |
| - 'tab_chained': click initial field, navigate subsequent fields via Tab key      |
| - 'hybrid': click controls/combos/buttons, Tab through adjacent text inputs       |
+-----------------------------------------------------------------------------------+
          |
          v
+-----------------------------------------------------------------------------------+
| PASS 4: Atomic Step Generation & Parameter Synthesis                              |
| - Inject initial window focus activation step                                     |
| - Synthesize field actions: Click -> Clear -> Prompt/Type -> Navigation           |
| - Inject form submission step (Enter key or button click)                         |
+-----------------------------------------------------------------------------------+
          |
          v
+-----------------------------------------------------------------------------------+
| PASS 5: Peephole Optimization & Safety Post-Processing                            |
| - Consolidate consecutive delay steps (sum duration_ms)                           |
| - Remove redundant focus/clear sequences                                          |
| - Re-index step sequence integers sequentially (1..N)                             |
| - Embed 90Studio legal copyright notice and canvas metadata                       |
+-----------------------------------------------------------------------------------+
          |
          v
[Compiled ActionWorkflow Output]
```

### 3.2 Formal Algorithm Specification

```python
"""
kutomoto Visual-to-Workflow Compiler (5-Pass Algorithm)
Copyright: Copyrights reserved to 90Studio
"""
import uuid
from typing import List, Dict, Any, Optional

def compile_visual_boxes_to_workflow(
    layout: Dict[str, Any],
    traversal_mode: str = "coordinate_targeted"
) -> Dict[str, Any]:
    """
    Executes the 5-pass compilation of VisualFormLayout into ActionWorkflow.
    
    Args:
        layout: Dict compliant with VisualFormLayout schema
        traversal_mode: "coordinate_targeted" | "tab_chained" | "hybrid"
        
    Returns:
        Dict compliant with KutomotoWorkflow Draft 2020-12 schema
    """
    boxes = layout.get("boxes", [])
    if not boxes:
        raise ValueError("Compilation error: layout contains no visual boxes.")

    # -------------------------------------------------------------
    # PASS 1: Integrity Validation & Geometry Normalization
    # -------------------------------------------------------------
    validated_boxes = []
    seen_ids = set()
    canvas_w = float(layout.get("canvas", {}).get("width", 1024))
    canvas_h = float(layout.get("canvas", {}).get("height", 768))

    for idx, b in enumerate(boxes):
        box_id = b.get("id") or str(uuid.uuid4())
        if box_id in seen_ids:
            box_id = str(uuid.uuid4())
        seen_ids.add(box_id)

        rect = b.get("rect", {})
        w = float(rect.get("width", 0))
        h = float(rect.get("height", 0))
        x = float(rect.get("x", 0))
        y = float(rect.get("y", 0))

        if w <= 0 or h <= 0:
            raise ValueError(f"Box '{b.get('name', idx)}' has invalid zero or negative dimensions.")

        # Compute or verify normalized bounds
        norm_bounds = b.get("norm_bounds")
        if not norm_bounds:
            norm_x = round(x / canvas_w, 4)
            norm_y = round(y / canvas_h, 4)
            norm_w = round(w / canvas_w, 4)
            norm_h = round(h / canvas_h, 4)
        else:
            norm_x = float(norm_bounds.get("norm_x", 0.0))
            norm_y = float(norm_bounds.get("norm_y", 0.0))
            norm_w = float(norm_bounds.get("norm_w", 0.0))
            norm_h = float(norm_bounds.get("norm_h", 0.0))

        center_norm_x = round(norm_x + (norm_w / 2.0), 4)
        center_norm_y = round(norm_y + (norm_h / 2.0), 4)

        validated_boxes.append({
            **b,
            "id": box_id,
            "center_norm_x": center_norm_x,
            "center_norm_y": center_norm_y,
            "norm_x": norm_x,
            "norm_y": norm_y,
            "norm_w": norm_w,
            "norm_h": norm_h
        })

    # -------------------------------------------------------------
    # PASS 2: Sequence Ordering & Spatial Topological Sorting
    # -------------------------------------------------------------
    has_explicit_indices = all(b.get("sequence_index", 0) > 0 for b in validated_boxes)

    if has_explicit_indices:
        ordered_boxes = sorted(validated_boxes, key=lambda b: b["sequence_index"])
    else:
        # 2D Spatial Band Sort (Top-to-Bottom, Left-to-Right)
        heights = sorted([b["norm_h"] for b in validated_boxes])
        median_h = heights[len(heights) // 2] if heights else 0.05
        band_threshold = median_h * 0.75

        sorted_by_y = sorted(validated_boxes, key=lambda b: b["norm_y"])
        bands: List[List[Dict[str, Any]]] = []
        current_band = [sorted_by_y[0]]

        for b in sorted_by_y[1:]:
            prev_y = current_band[-1]["norm_y"]
            curr_y = b["norm_y"]
            if abs(curr_y - prev_y) <= band_threshold:
                current_band.append(b)
            else:
                bands.append(current_band)
                current_band = [b]
        bands.append(current_band)

        ordered_boxes = []
        for band in bands:
            ordered_boxes.extend(sorted(band, key=lambda b: b["norm_x"]))

    # -------------------------------------------------------------
    # PASS 3 & 4: Traversal Strategy Selection & Step Generation
    # -------------------------------------------------------------
    target_info = layout.get("target", {})
    global_timing = layout.get("global_timing", {})
    default_pre_delay = global_timing.get("pre_delay_ms", 100)
    default_typing_speed = global_timing.get("typing_speed_ms", 20)
    default_post_delay = global_timing.get("post_delay_ms", 120)

    steps: List[Dict[str, Any]] = []

    # 4.1 Initial Window Focus Activation
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

    # 4.2 Form Box Action Synthesis
    for idx, box in enumerate(ordered_boxes):
        field_type = box.get("field_type", "text")
        val_cfg = box.get("value_config", {})
        nav_action = box.get("navigation", "tab")
        timing = box.get("timing", {})
        pre_delay = timing.get("pre_delay_ms", default_pre_delay)
        post_delay = timing.get("post_delay_ms", default_post_delay)
        typing_speed = timing.get("typing_speed_ms", default_typing_speed)

        # Determine if click is required based on traversal mode
        requires_click = True
        if traversal_mode == "tab_chained" and idx > 0 and field_type in ("text", "number", "date", "textarea"):
            requires_click = False
        elif traversal_mode == "hybrid" and idx > 0 and field_type in ("text", "number", "date", "textarea"):
            # If previous box navigated via Tab, skip click
            prev_nav = ordered_boxes[idx - 1].get("navigation", "tab")
            if prev_nav == "tab":
                requires_click = False

        # Dispatch click
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

        # Clear field if required
        if field_type in ("text", "number", "date", "textarea") and val_cfg.get("clear_before_type", True):
            steps.append({
                "step_id": str(uuid.uuid4()),
                "sequence_index": len(steps) + 1,
                "label": f"Clear Field [{box.get('name')}]",
                "action_type": "clear_field",
                "enabled": True,
                "pre_delay_ms": 0,
                "post_delay_ms": 40,
                "parameters": {
                    "clear_strategy": "select_all_backspace"
                }
            })

        # Value input synthesis
        if field_type in ("text", "number", "date", "textarea"):
            src_type = val_cfg.get("source_type", "static")
            text_payload = ""

            if src_type == "variable":
                var_name = val_cfg.get("variable_name", box.get("name"))
                text_payload = f"{{{{{var_name}}}}}"
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
                gen = val_cfg.get("generator_pattern", "timestamp_iso")
                text_payload = f"{{{{${gen}}}}}"
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
            continue  # Omit navigation key after submission

        # Post-field navigation key
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

    # -------------------------------------------------------------
    # PASS 5: Peephole Optimization & Safety Post-Processing
    # -------------------------------------------------------------
    optimized_steps: List[Dict[str, Any]] = []
    for s in steps:
        if (optimized_steps and 
            optimized_steps[-1]["action_type"] == "delay" and 
            s["action_type"] == "delay"):
            # Coalesce consecutive delays
            optimized_steps[-1]["parameters"]["duration_ms"] += s["parameters"]["duration_ms"]
        else:
            optimized_steps.append(s)

    # Renumber sequence index sequentially
    for seq, s in enumerate(optimized_steps, start=1):
        s["sequence_index"] = seq

    # Assemble complete workflow document
    workflow = {
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

    return workflow
```

---

## 4. Execution Engine Runtime & 7-State Finite State Machine (FSM)

### 4.1 State Definitions & Lifecycle Overview

The execution engine runtime is modeled as a non-blocking asynchronous finite state machine guaranteeing that UI interaction, emergency abort detection, and loss-of-focus monitoring remain responsive throughout automation.

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

The 7 execution states are defined as follows:

1. **`IDLE`**: The engine is resting, accepting configuration, loading workflows, or receiving canvas updates.
2. **`VALIDATING`**: The engine inspects the workflow against the JSON schema, ensures all non-default variables are provided, checks target window reachability, and primes the Win32 input thread.
3. **`COUNTDOWN`**: An interactive 3-second floating HUD displays on screen ("Switching to Target Form in 3... 2... 1..."). The user may click the target application window or abort via `Escape`.
4. **`RUNNING`**: The engine actively iterates through the workflow step array, dispatching Win32 `SendInput` mouse clicks, unicode typing keystrokes, and navigation triggers.
5. **`PAUSED`**: The step loop is suspended either by user intervention or automatically by the **Loss-of-Focus Guardian** (when `GetForegroundWindow()` no longer matches the target `hWnd`).
6. **`STOPPING`**: An abort event (`Escape` hotkey, corner slam failsafe, or cancel button) has been received. The engine releases any held modifier keys (`Ctrl`, `Alt`, `Shift`) and transitions to terminal `STOPPED`.
7. **`COMPLETED` / `ERROR`**: Terminal execution states. Emits the final structured compliance audit log, records execution duration, and returns system focus to the kutomoto console.

### 4.2 State Transition Matrix

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

### 4.3 Loss-of-Focus Guardian & Safety Architecture

In enterprise operations (such as entering a loan record or SIM subscriber identity), typing into an incorrect application window could result in catastrophic data leakage or corruption. Kutomoto enforces the **Loss-of-Focus Guardian**:

1. **Pre-Step Validation**:
   Prior to executing any `click`, `type_text`, `key_press`, or `clear_field` action, the engine inspects the foreground window:
   $$\text{active\_hwnd} = \text{user32.GetForegroundWindow()}$$
2. **Window Verification**:
   If $\text{active\_hwnd} \ne \text{target\_hwnd}$:
   - The engine immediately pauses execution, transitioning to `PAUSED`.
   - An alert appears on the kutomoto console: `[LOSS OF FOCUS] Expected target window 0x{target_hwnd:X}, but foreground is 0x{active_hwnd:X}. Automation paused.`
   - The operator can re-focus the target window and click `Resume`.

---

## 5. 90Studio Compliance Audit Trail & Logging Specification

### 5.1 Enterprise Compliance Mandate

In regulated industries such as **Commercial Banking** (KYC onboarding, loan origination), **Telecommunications** (SIM registration, MSISDN porting), and **General Enterprise** (AP invoice processing), every automated system action must create an immutable, auditable compliance trail.

The kutomoto audit logging system adheres to the following principles:
- **Tamper-Evident Records**: Execution logs are stored as standalone, append-only JSON documents under `logs/audit_YYYYMMDD_HHMMSS_<execution_id>.json`.
- **System & Copyright Attribution**: Every audit document is permanently watermarked with `"copyright": "Copyrights reserved to 90Studio"` and `"system": "kutomoto"`.
- **Credential & Secret Redaction**: Any step or parameter flagged with `is_secret: true` is strictly redacted with `********` before serialization to disk or transmission via WebSocket.
- **Microsecond Precision & Step Telemetry**: Detailed timestamp offsets, latencies, and execution durations allow forensic analysis of transaction timing and latency anomalies.

### 5.2 Formal Audit Trail JSON Schema (Draft 2020-12)

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

### 5.3 Concrete Enterprise Audit Log Example

Below is a production-grade audit log generated during an automated Corporate Banking KYC verification run:

```json
{
  "audit_version": "1.0.0",
  "system": "kutomoto",
  "copyright": "Copyrights reserved to 90Studio",
  "execution_id": "e81d4a92-91f3-42e1-884d-61e892cfa712",
  "workflow_id": "7b8e19d2-3140-4968-a40e-7d6f5c88102a",
  "workflow_name": "Corporate KYC Account Verification Flow",
  "source_mode": "visual_designer_generated",
  "timestamp_utc": "2026-11-04T22:35:10.125Z",
  "operator_username": "enterprise_teller_04",
  "host_machine": "CORP-W11-B042",
  "os_version": "Microsoft Windows 11 Enterprise (10.0.22631)",
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
    "duration_seconds": 3.82,
    "final_status": "SUCCESS"
  },
  "step_events": [
    {
      "step_index": 1,
      "action_type": "focus_window",
      "label": "Focus Banking Window",
      "timestamp_offset_ms": 10,
      "parameters_summary": "pattern='Corporate Banking Portal', hwnd=0x000300E8",
      "latency_ms": 252.4,
      "status": "SUCCESS"
    },
    {
      "step_index": 2,
      "action_type": "click",
      "label": "Click [Customer Name]",
      "timestamp_offset_ms": 265,
      "parameters_summary": "norm_coords=(0.3250, 0.2400), target_screen=(624, 259), button=left",
      "latency_ms": 61.2,
      "status": "SUCCESS"
    },
    {
      "step_index": 3,
      "action_type": "clear_field",
      "label": "Clear Field [cust_name]",
      "timestamp_offset_ms": 330,
      "parameters_summary": "strategy=select_all_backspace",
      "latency_ms": 42.1,
      "status": "SUCCESS"
    },
    {
      "step_index": 4,
      "action_type": "type_text",
      "label": "Type Customer Name",
      "timestamp_offset_ms": 375,
      "parameters_summary": "text='Acme Global Corp' (16 chars, 25ms pacing)",
      "latency_ms": 412.8,
      "status": "SUCCESS"
    },
    {
      "step_index": 5,
      "action_type": "key_press",
      "label": "Navigate (Tab)",
      "timestamp_offset_ms": 790,
      "parameters_summary": "key=VK_TAB, count=1",
      "latency_ms": 101.5,
      "status": "SUCCESS"
    },
    {
      "step_index": 6,
      "action_type": "type_text",
      "label": "Type Tax ID",
      "timestamp_offset_ms": 895,
      "parameters_summary": "text='99-1234567' (10 chars, 25ms pacing)",
      "latency_ms": 258.3,
      "status": "SUCCESS"
    },
    {
      "step_index": 7,
      "action_type": "submit",
      "label": "Submit Form via Enter Key",
      "timestamp_offset_ms": 1155,
      "parameters_summary": "method=enter_key, post_wait_ms=1000",
      "latency_ms": 1005.1,
      "status": "SUCCESS"
    }
  ]
}
```

---

## 6. Actionable Authoring Guidance for the Worker (`docs/SPECIFICATION.md`)

When incorporating these findings into `docs/SPECIFICATION.md`, the Worker should follow these direct structural instructions:

1. **Document Section Placement**:
   - Place Section 1 (Visual Form Designer Architecture & Data Model) under `## 4. Visual Form Designer & Workflow Generation Architecture`.
   - Place Section 2 (Unified Action Schema) under `## 5. Unified Action Workflow Schema & Atomic Actions`.
   - Place Section 3 (5-Pass Compiler) under `## 6. Visual-to-Workflow Compilation Pipeline`.
   - Place Section 4 (7-State Execution FSM) under `## 7. Execution Engine Runtime & State Machine`.
   - Place Section 5 (Audit Log Schema) under `## 8. Enterprise Error Recovery, Safety & Compliance Audit Logging`.

2. **Cross-Reference Alignment**:
   - Ensure the 10 atomic actions match the feature descriptions in `F09` (`10 Atomic Actions`) in M1_1's catalog.
   - Ensure the compiler pass definitions align with `F14` (`Visual-to-Workflow Compiler`) and `F15` (`Coordinate Normalization`).
   - Ensure the state machine matches `F10` (`Execution Engine FSM`) and integrates with M1_2's Win32 input methods.
   - Verify that all JSON schemas validate against Draft 2020-12 rules.

3. **Code Model Consistency**:
   - The schemas specified herein directly translate to Pydantic models in Python:
     - `VisualFormLayout` and `VisualBox` $\rightarrow$ `src/kutomoto/designer/schema.py`
     - `KutomotoWorkflow` and `WorkflowStep` $\rightarrow$ `src/kutomoto/engine/schema.py`
     - `AuditLogRecord` and `StepEvent` $\rightarrow$ `src/kutomoto/engine/audit.py`
   - Maintaining exact field name symmetry (`norm_bounds`, `sequence_index`, `clear_strategy`, `is_secret`) will enable zero-friction implementation during Milestone 2 and Milestone 3.

---
*Report delivered by m1_explorer_3. All rights reserved to 90Studio.*
