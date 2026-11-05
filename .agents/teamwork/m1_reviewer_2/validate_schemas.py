"""
Thorough JSON Schema and Draft 2020-12 validation script.
Author: m1_reviewer_2
"""
import json
import re
import uuid
import jsonschema
from jsonschema import Draft202012Validator

spec_path = r"c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md"
with open(spec_path, "r", encoding="utf-8") as f:
    text = f.read()

json_blocks = re.findall(r"```json\n(.*?)\n```", text, re.DOTALL)
print(f"Total JSON blocks extracted: {len(json_blocks)}")

schema_vfd = json.loads(json_blocks[0])
schema_wf = json.loads(json_blocks[1])
schema_audit = json.loads(json_blocks[2])
audit_record = json.loads(json_blocks[3])

# 1. Meta-schema validation
for name, s in [("VisualFormLayout", schema_vfd), ("KutomotoWorkflow", schema_wf), ("KutomotoAuditLog", schema_audit)]:
    try:
        Draft202012Validator.check_schema(s)
        print(f"[PASS] {name} is a valid Draft 2020-12 schema.")
    except Exception as e:
        print(f"[FAIL] {name} schema error: {e}")

# 2. Validate sample audit record against audit schema
validator_audit = Draft202012Validator(schema_audit)
audit_errors = list(validator_audit.iter_errors(audit_record))
if not audit_errors:
    print("[PASS] Sample audit record validates against KutomotoAuditLog schema.")
else:
    print(f"[FAIL] Sample audit record has {len(audit_errors)} errors:")
    for err in audit_errors:
        print(f"  - {err.message} at path {list(err.path)}")

# 3. Compile sample layout and validate against KutomotoWorkflow schema
py_blocks = re.findall(r"```python\n(.*?)\n```", text, re.DOTALL)
compiler_code = [b for b in py_blocks if "def compile_visual_boxes_to_workflow" in b][0]
scope = {"uuid": uuid, "List": list, "Dict": dict, "Any": object}
exec(compiler_code, scope)
compile_fn = scope["compile_visual_boxes_to_workflow"]

sample_layout = {
    "schema_version": "1.0.0",
    "id": str(uuid.uuid4()),
    "name": "KYC Customer Onboarding",
    "copyright": "Copyrights reserved to 90Studio",
    "canvas": {"width": 1024, "height": 768},
    "target": {
        "type": "web_browser",
        "window_title_pattern": ".*KYC Portal.*",
        "match_mode": "regex"
    },
    "boxes": [
        {
            "id": str(uuid.uuid4()),
            "name": "customer_name",
            "label": "Full Name",
            "field_type": "text",
            "sequence_index": 1,
            "rect": {"x": 100, "y": 100, "width": 250, "height": 36},
            "norm_bounds": {"norm_x": 0.0977, "norm_y": 0.1302, "norm_w": 0.2441, "norm_h": 0.0469},
            "value_config": {
                "source_type": "static",
                "static_value": "Eleanor Vance",
                "is_secret": False,
                "clear_before_type": True
            },
            "navigation": "tab"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "submit_btn",
            "label": "Submit Form",
            "field_type": "submit_button",
            "sequence_index": 2,
            "rect": {"x": 100, "y": 180, "width": 150, "height": 40},
            "norm_bounds": {"norm_x": 0.0977, "norm_y": 0.2344, "norm_w": 0.1465, "norm_h": 0.0521},
            "value_config": {
                "source_type": "static",
                "is_secret": False,
                "clear_before_type": False
            },
            "navigation": "none"
        }
    ]
}

# Validate sample_layout against VisualFormLayout schema
validator_vfd = Draft202012Validator(schema_vfd)
vfd_errors = list(validator_vfd.iter_errors(sample_layout))
if not vfd_errors:
    print("[PASS] sample_layout validates against VisualFormLayout schema.")
else:
    print(f"[FAIL] sample_layout has {len(vfd_errors)} errors:")
    for err in vfd_errors:
        print(f"  - {err.message} at path {list(err.path)}")

# Compile to workflow
compiled_wf = compile_fn(sample_layout)

# Validate compiled workflow against KutomotoWorkflow schema
validator_wf = Draft202012Validator(schema_wf)
wf_errors = list(validator_wf.iter_errors(compiled_wf))
if not wf_errors:
    print("[PASS] Compiled workflow validates against KutomotoWorkflow schema.")
else:
    print(f"[FAIL] Compiled workflow has {len(wf_errors)} errors:")
    for err in wf_errors:
        print(f"  - {err.message} at path {list(err.path)}")
