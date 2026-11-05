"""
Comprehensive verification and stress-testing script for docs/SPECIFICATION.md
Author: m1_reviewer_1
Role: Reviewer & Adversarial Critic
"""
import os
import sys
import re
import json
import ast
import ctypes

SPEC_PATH = r"c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md"

def test_specification():
    print("=== STARTING INDEPENDENT SPECIFICATION REVIEW ===")
    assert os.path.isfile(SPEC_PATH), f"File not found: {SPEC_PATH}"
    
    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        text = f.read()
    
    lines = text.splitlines()
    print(f"Total lines: {len(lines)}")
    print(f"Total bytes: {len(text.encode('utf-8'))}")
    
    results = {
        "pass": [],
        "fail": [],
        "warnings": [],
        "adversarial_findings": []
    }
    
    # 1. Branding & Attribution Check
    brand_mentions = len(re.findall(r"Copyrights reserved to 90Studio", text))
    kutomoto_mentions = len(re.findall(r"\bkutomoto\b", text, re.IGNORECASE))
    if brand_mentions >= 15:
        results["pass"].append(f"90Studio copyright check: {brand_mentions} occurrences (>= 15 required)")
    else:
        results["fail"].append(f"90Studio copyright check: only {brand_mentions} occurrences")
        
    if kutomoto_mentions >= 30:
        results["pass"].append(f"kutomoto branding check: {kutomoto_mentions} occurrences (>= 30 required)")
    else:
        results["fail"].append(f"kutomoto branding check: only {kutomoto_mentions} occurrences")

    # 2. Features F01 to F23
    features = [f"F{i:02d}" for i in range(1, 24)]
    missing_features = []
    for f in features:
        if not re.search(r"\b" + f + r"\b", text):
            missing_features.append(f)
    if not missing_features:
        results["pass"].append("Feature Catalog: All 23 features (F01-F23) present")
    else:
        results["fail"].append(f"Feature Catalog: Missing features {missing_features}")

    # 3. Operational Edge Cases E01 to E15
    edge_cases = [f"E{i:02d}" for i in range(1, 16)]
    missing_edge_cases = []
    for e in edge_cases:
        if not re.search(r"\b" + e + r"\b", text):
            missing_edge_cases.append(e)
    if not missing_edge_cases:
        results["pass"].append("Edge Cases: All 15 operational edge cases (E01-E15) present")
    else:
        results["fail"].append(f"Edge Cases: Missing edge cases {missing_edge_cases}")

    # 4. Domain Blueprints (3 Banking, 3 Telecom, 3 Business)
    blueprints = ["BK-01", "BK-02", "BK-03", "TC-01", "TC-02", "TC-03", "GB-01", "GB-02", "GB-03"]
    missing_bps = []
    for bp in blueprints:
        if not re.search(r"\b" + bp + r"\b", text):
            missing_bps.append(bp)
    if not missing_bps:
        results["pass"].append("Enterprise Blueprints: All 9 domain blueprints present (3 BK, 3 TC, 3 GB)")
    else:
        results["fail"].append(f"Enterprise Blueprints: Missing blueprints {missing_bps}")

    # 5. User Story Epics
    epics = ["US-VFD", "US-AWE", "US-TRANS", "US-EXEC", "US-FOC", "US-ERR", "US-UI", "US-TST"]
    missing_epics = []
    for ep in epics:
        if not re.search(r"\b" + ep + r"\b", text):
            missing_epics.append(ep)
    if not missing_epics:
        results["pass"].append("User Story Epics: All 8 epics present")
    else:
        results["fail"].append(f"User Story Epics: Missing epics {missing_epics}")

    # 6. Gherkin Scenarios
    gherkin_blocks = re.findall(r"```gherkin\n(.*?)\n\s*```", text, re.DOTALL)
    if len(gherkin_blocks) >= 19:
        results["pass"].append(f"Gherkin Scenarios: {len(gherkin_blocks)} BDD scenario blocks found (>= 19 required)")
    else:
        results["fail"].append(f"Gherkin Scenarios: Only {len(gherkin_blocks)} found, expected >= 19")

    # 7. State Transitions T01 to T18
    transitions = [f"T{i:02d}" for i in range(1, 19)]
    missing_trans = []
    for t in transitions:
        if not re.search(r"\b" + t + r"\b", text):
            missing_trans.append(t)
    if not missing_trans:
        results["pass"].append("FSM State Transitions: All 18 transitions (T01-T18) present")
    else:
        results["fail"].append(f"FSM State Transitions: Missing transitions {missing_trans}")

    # 8. Requirements Traceability (R1, R2, R3, R4)
    reqs = ["R1", "R2", "R3", "R4"]
    missing_reqs = []
    for r in reqs:
        if not re.search(r"\b" + r + r"\b", text):
            missing_reqs.append(r)
    if not missing_reqs:
        results["pass"].append("Requirements Traceability: R1-R4 present and mapped")
    else:
        results["fail"].append(f"Requirements Traceability: Missing requirements {missing_reqs}")

    # 9. JSON Schema Validation
    json_blocks = re.findall(r"```json\n(.*?)\n```", text, re.DOTALL)
    json_errors = []
    for i, jb in enumerate(json_blocks, 1):
        try:
            parsed = json.loads(jb)
            if "$schema" in parsed:
                if "2020-12" not in parsed["$schema"]:
                    results["warnings"].append(f"JSON block {i} schema is not Draft 2020-12: {parsed.get('$schema')}")
        except Exception as ex:
            json_errors.append(f"Block {i}: {ex}")
    if not json_errors:
        results["pass"].append(f"JSON Schemas: All {len(json_blocks)} JSON blocks are valid JSON")
    else:
        results["fail"].append(f"JSON Schemas invalid: {json_errors}")

    # 10. Python Code Block AST Validation
    python_blocks = re.findall(r"```python\n(.*?)\n```", text, re.DOTALL)
    py_errors = []
    for i, pb in enumerate(python_blocks, 1):
        try:
            ast.parse(pb)
        except Exception as ex:
            py_errors.append(f"Block {i}: {ex}")
    if not py_errors:
        results["pass"].append(f"Python Code: All {len(python_blocks)} python code snippets compile cleanly with ast.parse")
    else:
        results["fail"].append(f"Python Code syntax errors: {py_errors}")

    # 11. ctypes struct execution test
    try:
        struct_code = python_blocks[1]
        s_loc = {}
        exec(struct_code, s_loc)
        in_sz = s_loc['ctypes'].sizeof(s_loc['INPUT'])
        m_sz = s_loc['ctypes'].sizeof(s_loc['MOUSEINPUT'])
        k_sz = s_loc['ctypes'].sizeof(s_loc['KEYBDINPUT'])
        h_sz = s_loc['ctypes'].sizeof(s_loc['HARDWAREINPUT'])
        assert in_sz == 40, f"INPUT size is {in_sz}, expected 40"
        assert m_sz == 32, f"MOUSEINPUT size is {m_sz}, expected 32"
        assert k_sz == 24, f"KEYBDINPUT size is {k_sz}, expected 24"
        assert h_sz == 8, f"HARDWAREINPUT size is {h_sz}, expected 8"
        results["pass"].append("ctypes Win32 64-bit ABI alignment: exact 40/32/24/8 byte sizes confirmed")
    except Exception as ex:
        results["fail"].append(f"ctypes struct test failed: {ex}")

    # 12. Compiler Reference Execution Test
    try:
        compiler_code = python_blocks[4]
        c_loc = {}
        exec(compiler_code, c_loc)
        compile_fn = c_loc['compile_visual_boxes_to_workflow']
        
        # Test Case A: Standard 2-box form with schema-compliant properties
        test_layout_a = {
            "schema_version": "1.0.0",
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "Test Form A",
            "copyright": "Copyrights reserved to 90Studio",
            "target": {
                "type": "window_title",
                "window_title_pattern": "Test Window",
                "match_mode": "contains",
                "process_name": "test.exe"
            },
            "canvas": {"width": 1024, "height": 768},
            "boxes": [
                {
                    "id": "22222222-2222-2222-2222-222222222222",
                    "name": "first_name",
                    "label": "First Name",
                    "rect": {"x": 100, "y": 100, "width": 200, "height": 30},
                    "sequence_index": 1,
                    "field_type": "text",
                    "value_config": {
                        "source_type": "static",
                        "static_value": "Jane",
                        "is_secret": False,
                        "clear_before_type": True
                    },
                    "navigation": "tab"
                },
                {
                    "id": "33333333-3333-3333-3333-333333333333",
                    "name": "last_name",
                    "label": "Last Name",
                    "rect": {"x": 100, "y": 150, "width": 200, "height": 30},
                    "sequence_index": 2,
                    "field_type": "text",
                    "value_config": {
                        "source_type": "static",
                        "static_value": "Doe",
                        "is_secret": False,
                        "clear_before_type": True
                    },
                    "navigation": "none"
                },
                {
                    "id": "44444444-4444-4444-4444-444444444444",
                    "name": "submit_btn",
                    "label": "Submit Button",
                    "rect": {"x": 100, "y": 200, "width": 80, "height": 30},
                    "sequence_index": 3,
                    "field_type": "submit_button",
                    "value_config": {
                        "source_type": "static",
                        "static_value": "",
                        "is_secret": False,
                        "clear_before_type": False
                    },
                    "navigation": "none"
                }
            ]
        }
        wf_a = compile_fn(test_layout_a)
        assert len(wf_a["steps"]) > 0, "No steps generated"
        assert wf_a.get("copyright") == "Copyrights reserved to 90Studio"
        results["pass"].append(f"Compiler reference execution: Test Layout A generated {len(wf_a['steps'])} action steps with copyright")
        
        # Test Case B (Adversarial): Unordered sequence indices and missing sequence index
        test_layout_b = {
            "schema_version": "1.0.0",
            "id": "55555555-5555-5555-5555-555555555555",
            "name": "Test Form B Unordered",
            "copyright": "Copyrights reserved to 90Studio",
            "target": {
                "type": "window_title",
                "window_title_pattern": "Test Window",
                "match_mode": "contains",
                "process_name": "test.exe"
            },
            "canvas": {"width": 1024, "height": 768},
            "boxes": [
                {
                    "id": "66666666-6666-6666-6666-666666666666",
                    "name": "field_2",
                    "label": "Field 2",
                    "rect": {"x": 100, "y": 200, "width": 200, "height": 30},
                    "sequence_index": 10,
                    "field_type": "text",
                    "value_config": {
                        "source_type": "static",
                        "static_value": "Second",
                        "is_secret": False,
                        "clear_before_type": True
                    },
                    "navigation": "tab"
                },
                {
                    "id": "77777777-7777-7777-7777-777777777777",
                    "name": "field_1",
                    "label": "Field 1",
                    "rect": {"x": 100, "y": 100, "width": 200, "height": 30},
                    "sequence_index": 2,
                    "field_type": "text",
                    "value_config": {
                        "source_type": "static",
                        "static_value": "First",
                        "is_secret": False,
                        "clear_before_type": True
                    },
                    "navigation": "tab"
                }
            ]
        }
        wf_b = compile_fn(test_layout_b)
        labels_in_order = [s.get("label", "") for s in wf_b["steps"]]
        first_field_action = [l for l in labels_in_order if "Field" in l][0]
        assert "Field 1" in first_field_action, f"Ordering failed: {first_field_action}"
        results["pass"].append("Compiler reference execution: Correctly sorted out-of-order sequence indices [10, 2] -> [2, 10]")
        
        # Test Case C (Adversarial): Spatial band ordering when sequence_index is 0 / absent
        test_layout_c = {
            "schema_version": "1.0.0",
            "id": "88888888-8888-8888-8888-888888888888",
            "name": "Test Form C Spatial Sort",
            "copyright": "Copyrights reserved to 90Studio",
            "target": {
                "type": "window_title",
                "window_title_pattern": "Test Window",
                "match_mode": "contains"
            },
            "canvas": {"width": 1000, "height": 1000},
            "boxes": [
                {
                    "id": "99999999-9999-9999-9999-999999999999",
                    "name": "bottom_right",
                    "label": "Bottom Right",
                    "rect": {"x": 500, "y": 600, "width": 200, "height": 40},
                    "sequence_index": 0,
                    "field_type": "text",
                    "value_config": {"source_type": "static", "static_value": "BR", "clear_before_type": False, "is_secret": False},
                    "navigation": "none"
                },
                {
                    "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    "name": "top_left",
                    "label": "Top Left",
                    "rect": {"x": 100, "y": 100, "width": 200, "height": 40},
                    "sequence_index": 0,
                    "field_type": "text",
                    "value_config": {"source_type": "static", "static_value": "TL", "clear_before_type": False, "is_secret": False},
                    "navigation": "none"
                }
            ]
        }
        wf_c = compile_fn(test_layout_c)
        labels_c = [s.get("label", "") for s in wf_c["steps"]]
        field_labels_c = [l for l in labels_c if "Top Left" in l or "Bottom Right" in l]
        assert "Top Left" in field_labels_c[0], f"Spatial sort failed: {field_labels_c}"
        results["pass"].append("Compiler reference execution: Correctly performed 2D reading-order spatial band sorting for unindexed boxes")
        
    except Exception as ex:
        results["fail"].append(f"Compiler reference execution failed: {ex}")
        import traceback
        traceback.print_exc()

    print("\n--- SUMMARY OF INDEPENDENT VERIFICATION ---")
    for p in results["pass"]:
        print(f"[PASS] {p}")
    for w in results["warnings"]:
        print(f"[WARN] {w}")
    for f in results["fail"]:
        print(f"[FAIL] {f}")
        
    return results

if __name__ == "__main__":
    test_specification()
