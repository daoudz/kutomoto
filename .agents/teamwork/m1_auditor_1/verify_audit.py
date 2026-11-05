import os
import sys
import re
import json
import ast

def run_checks():
    spec_path = r"c:\Users\daoud\projects\kutomoto\docs\SPECIFICATION.md"
    print("=== STARTING FORENSIC INTEGRITY AUDIT ===")
    print("Checking file existence and size...")
    assert os.path.exists(spec_path), "docs/SPECIFICATION.md missing!"
    size = os.path.getsize(spec_path)
    print(f"File size: {size} bytes")

    with open(spec_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()
    print(f"Total lines: {len(lines)}")
    assert len(lines) >= 1000, f"Specification too short: {len(lines)} lines"

    # 1. Check Copyright and Branding
    print("\n--- 1. Copyright & Branding Compliance ---")
    copyright_needle = "Copyrights reserved to 90Studio"
    c_count = content.count(copyright_needle)
    k_count = content.count("kutomoto")
    s_count = content.count("90Studio")
    print(f"'{copyright_needle}': {c_count} occurrences (min requirement: 20)")
    print(f"'kutomoto': {k_count} occurrences")
    print(f"'90Studio': {s_count} occurrences")
    assert c_count >= 20, f"Insufficient copyright attribution count: {c_count}"
    assert k_count >= 20, f"Insufficient kutomoto mentions: {k_count}"

    # 2. Check Completeness of Requirements & Identifiers
    print("\n--- 2. Completeness of Required IDs ---")
    features = [f"F{i:02d}" for i in range(1, 24)]
    edge_cases = [f"E{i:02d}" for i in range(1, 16)]
    use_cases = ["BK-01", "BK-02", "BK-03", "TC-01", "TC-02", "TC-03", "GB-01", "GB-02", "GB-03"]
    epics = ["US-VFD", "US-AWE", "US-TRANS", "US-EXEC", "US-FOC", "US-ERR", "US-UI", "US-TST"]
    transitions = [f"T{i:02d}" for i in range(1, 19)]

    for f_id in features:
        assert f_id in content, f"Missing feature {f_id}"
    print(f"All 23 features present: F01-F23 PASS")

    for e_id in edge_cases:
        assert e_id in content, f"Missing edge case {e_id}"
    print(f"All 15 edge cases present: E01-E15 PASS")

    for u_id in use_cases:
        assert u_id in content, f"Missing use case {u_id}"
    print(f"All 9 enterprise blueprints present: BK-01..03, TC-01..03, GB-01..03 PASS")

    for ep_id in epics:
        assert ep_id in content, f"Missing epic {ep_id}"
    print(f"All 8 user story epics present: US-VFD..US-TST PASS")

    for t_id in transitions:
        assert t_id in content, f"Missing transition {t_id}"
    print(f"All 18 FSM transitions present: T01-T18 PASS")

    # 3. Code Blocks Extraction & AST Parsing
    print("\n--- 3. Code Blocks & Schema Validation ---")
    blocks = re.findall(r"```([a-zA-Z0-9_-]*)\n(.*?)```", content, re.DOTALL)
    print(f"Total embedded code blocks: {len(blocks)}")

    py_blocks = [(i, c) for i, (lang, c) in enumerate(blocks) if lang.lower() in ["python", "py"]]
    json_blocks = [(i, c) for i, (lang, c) in enumerate(blocks) if lang.lower() in ["json", "json5"]]
    gherkin_blocks = [(i, c) for i, (lang, c) in enumerate(blocks) if lang.lower() == "gherkin"]

    print(f"Python blocks: {len(py_blocks)}")
    print(f"JSON blocks: {len(json_blocks)}")
    print(f"Gherkin blocks: {len(gherkin_blocks)}")

    for i, py_code in py_blocks:
        ast.parse(py_code)
    print("All Python code blocks passed ast.parse() successfully!")

    import jsonschema
    for i, j_code in json_blocks:
        data = json.loads(j_code)
        schema_url = data.get("$schema")
        if schema_url:
            validator_cls = jsonschema.validators.validator_for(data)
            validator_cls.check_schema(data)
            print(f"JSON schema block #{i} ({data.get('title')}) validated against {validator_cls.__name__}: PASS")
        else:
            print(f"JSON data block #{i} parsed as valid JSON: PASS")

    # 4. Check for prohibited patterns (facades, stubs, lorem ipsum)
    print("\n--- 4. Prohibited Patterns & Facade Detection ---")
    prohibited = [
        (r"\bTODO\b", "TODO marker"),
        (r"\bFIXME\b", "FIXME marker"),
        (r"\bTBD\b", "TBD marker"),
        (r"lorem ipsum", "Lorem Ipsum dummy text"),
        (r"\bplaceholder\b", "Placeholder text"),
        (r"\bdummy\b", "Dummy text"),
        (r"coming soon", "Coming soon placeholder"),
        (r"\bnot implemented\b", "Not implemented stub")
    ]
    for pattern, name in prohibited:
        matches = [idx + 1 for idx, l in enumerate(lines) if re.search(pattern, l, re.IGNORECASE)]
        assert len(matches) == 0, f"Prohibited pattern '{name}' found at lines {matches}"
        print(f"Check '{name}': CLEAN (0 occurrences)")

    print("\n=== ALL FORENSIC AUDIT CHECKS PASSED WITH ZERO VIOLATIONS ===")

if __name__ == "__main__":
    run_checks()
