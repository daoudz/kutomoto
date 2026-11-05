"""
Independent verification and stress testing script for docs/SPECIFICATION.md
Author: m1_reviewer_2
"""
import ast
import json
import os
import re
import sys
import uuid

spec_path = r"c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md"
with open(spec_path, "r", encoding="utf-8") as f:
    spec_text = f.read()

print("--- 1. SPECIFICATION BASIC METRICS ---")
print(f"File size: {len(spec_text)} bytes")
print(f"Total lines: {len(spec_text.splitlines())}")

print("\n--- 2. PYTHON REFERENCE BLOCKS SYNTAX CHECK ---")
py_blocks = re.findall(r"```python\n(.*?)\n```", spec_text, re.DOTALL)
print(f"Found {len(py_blocks)} Python code blocks.")
for idx, code in enumerate(py_blocks, 1):
    try:
        ast.parse(code)
        print(f"Block {idx}: Valid Python syntax (ast.parse passed)")
    except SyntaxError as e:
        print(f"Block {idx}: SYNTAX ERROR: {e}")

print("\n--- 3. JSON SCHEMA & PAYLOAD VALIDATION ---")
json_blocks = re.findall(r"```json\n(.*?)\n```", spec_text, re.DOTALL)
print(f"Found {len(json_blocks)} JSON blocks.")
parsed_json = []
for idx, code in enumerate(json_blocks, 1):
    try:
        data = json.loads(code)
        name = data.get("title") or data.get("audit_version") or "unknown"
        parsed_json.append(data)
        print(f"Block {idx}: Valid JSON ({name})")
    except Exception as e:
        print(f"Block {idx}: JSON ERROR: {e}")

print("\n--- 4. COMPILER PASSES & EXECUTION TEST ---")
compiler_code = None
for code in py_blocks:
    if "def compile_visual_boxes_to_workflow" in code:
        compiler_code = code
        break

if compiler_code:
    scope = {"uuid": uuid, "List": list, "Dict": dict, "Any": object}
    exec(compiler_code, scope)
    compile_fn = scope["compile_visual_boxes_to_workflow"]

    test_layout = {
        "name": "Test Form",
        "canvas": {"width": 1000, "height": 800},
        "target": {"window_title_pattern": ".*Test Window.*"},
        "boxes": [
            {
                "name": "username",
                "label": "Username",
                "field_type": "text",
                "sequence_index": 1,
                "rect": {"x": 100, "y": 100, "width": 200, "height": 40},
                "value_config": {
                    "source_type": "static",
                    "static_value": "admin",
                    "is_secret": False,
                    "clear_before_type": True,
                },
                "navigation": "tab",
            },
            {
                "name": "password",
                "label": "Password",
                "field_type": "text",
                "sequence_index": 2,
                "rect": {"x": 100, "y": 160, "width": 200, "height": 40},
                "value_config": {
                    "source_type": "static",
                    "static_value": "secret123",
                    "is_secret": True,
                    "clear_before_type": True,
                },
                "navigation": "tab",
            },
            {
                "name": "submit_btn",
                "label": "Submit",
                "field_type": "submit_button",
                "sequence_index": 3,
                "rect": {"x": 100, "y": 220, "width": 120, "height": 40},
                "value_config": {
                    "source_type": "static",
                    "is_secret": False,
                    "clear_before_type": False,
                },
                "navigation": "none",
            },
        ],
    }

    # Test coordinate_targeted traversal
    wf_targeted = compile_fn(test_layout, "coordinate_targeted")
    print(f"Targeted mode compiled: {len(wf_targeted['steps'])} steps")
    for s in wf_targeted["steps"]:
        print(f"  Step {s['sequence_index']}: {s['action_type']} - {s['label']}")

    # Test tab_chained traversal
    wf_chained = compile_fn(test_layout, "tab_chained")
    print(f"Tab-chained mode compiled: {len(wf_chained['steps'])} steps")
    for s in wf_chained["steps"]:
        print(f"  Step {s['sequence_index']}: {s['action_type']} - {s['label']}")

    # Test spatial reading-order fallback (sequence_index = 0)
    spatial_layout = {
        "name": "Spatial Form",
        "canvas": {"width": 1000, "height": 800},
        "target": {"window_title_pattern": ".*Spatial.*"},
        "boxes": [
            {
                "name": "row1_right",
                "label": "R1 Right",
                "field_type": "text",
                "sequence_index": 0,
                "rect": {"x": 500, "y": 100, "width": 200, "height": 40},
                "value_config": {"source_type": "static", "static_value": "B"},
            },
            {
                "name": "row1_left",
                "label": "R1 Left",
                "field_type": "text",
                "sequence_index": 0,
                "rect": {"x": 100, "y": 100, "width": 200, "height": 40},
                "value_config": {"source_type": "static", "static_value": "A"},
            },
            {
                "name": "row2_field",
                "label": "R2 Field",
                "field_type": "text",
                "sequence_index": 0,
                "rect": {"x": 100, "y": 200, "width": 200, "height": 40},
                "value_config": {"source_type": "static", "static_value": "C"},
            },
        ],
    }
    wf_spatial = compile_fn(spatial_layout)
    print(f"Spatial mode compiled: {len(wf_spatial['steps'])} steps")
    labels = [s["label"] for s in wf_spatial["steps"] if s["action_type"] == "click"]
    print("Click sequence in spatial mode:", labels)
else:
    print("Compiler code block not found!")

print("\n--- 5. CHECKING 7-STATE FSM TRANSITIONS (T01 - T18) ---")
# Check all transitions
transitions = [f"T{i:02d}" for i in range(1, 19)]
missing_transitions = [t for t in transitions if t not in spec_text]
print(f"Missing transitions: {missing_transitions if missing_transitions else 'None (All 18 present)'}")

# Check 7 states
states = ["IDLE", "VALIDATING", "COUNTDOWN", "RUNNING", "PAUSED", "STOPPING", "COMPLETED", "ERROR"]
missing_states = [s for s in states if s not in spec_text]
print(f"Missing states: {missing_states if missing_states else 'None (All states present)'}")

print("\n--- 6. CHECKING 10 ATOMIC ACTIONS ---")
actions = [
    "focus_window", "click", "type_text", "key_press", "hotkey",
    "clear_field", "delay", "submit", "scroll", "prompt_user_input"
]
missing_actions = [a for a in actions if a not in spec_text]
print(f"Missing actions: {missing_actions if missing_actions else 'None (All 10 present)'}")

print("\n--- 7. 90STUDIO COPYRIGHT ATTRIBUTION COUNT ---")
attribution = "Copyrights reserved to 90Studio"
count = spec_text.count(attribution)
print(f"Occurrences of '{attribution}': {count}")
