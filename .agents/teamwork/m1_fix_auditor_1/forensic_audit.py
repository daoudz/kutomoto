"""
Forensic Integrity Audit Script for Milestone 1 (Iteration 2).
Audited files: docs/SPECIFICATION.md, tests/test_specification.py
Copyrights reserved to 90Studio
"""
import ast
import ctypes
from ctypes import wintypes
import json
import os
import re
import sys
import textwrap
from pathlib import Path

WORKSPACE = Path(r"c:\Users\daoud\projects\kutomoto")
SPEC_PATH = WORKSPACE / "docs" / "SPECIFICATION.md"
TEST_SPEC_PATH = WORKSPACE / "tests" / "test_specification.py"
CONFTEST_PATH = WORKSPACE / "tests" / "conftest.py"

failures = []

def record_failure(check_name: str, reason: str):
    print(f"[FAIL] {check_name}: {reason}")
    failures.append((check_name, reason))

def record_pass(check_name: str, details: str):
    print(f"[PASS] {check_name}: {details}")

print("=== STARTING FORENSIC INTEGRITY AUDIT (M1 Iteration 2) ===")

# ----------------------------------------------------------------------
# Check 1: File Existence & Metrics
# ----------------------------------------------------------------------
if not SPEC_PATH.exists():
    record_failure("SPEC_PATH existence", f"File missing at {SPEC_PATH}")
else:
    spec_bytes = len(SPEC_PATH.read_bytes())
    spec_lines = len(SPEC_PATH.read_text(encoding="utf-8").splitlines())
    if spec_lines < 2000:
        record_failure("SPEC line count", f"Expected >= 2000 lines, got {spec_lines}")
    else:
        record_pass("SPEC file metrics", f"{spec_lines} lines, {spec_bytes} bytes")

if not TEST_SPEC_PATH.exists():
    record_failure("TEST_SPEC_PATH existence", f"File missing at {TEST_SPEC_PATH}")
else:
    test_lines = len(TEST_SPEC_PATH.read_text(encoding="utf-8").splitlines())
    record_pass("TEST_SPEC file metrics", f"{test_lines} lines")

spec_text = SPEC_PATH.read_text(encoding="utf-8")
test_text = TEST_SPEC_PATH.read_text(encoding="utf-8")

# ----------------------------------------------------------------------
# Check 2: 90Studio Branding & Attribution
# ----------------------------------------------------------------------
spec_cr_count = spec_text.count("Copyrights reserved to 90Studio")
spec_kuto_count = spec_text.count("kutomoto")
spec_90_count = spec_text.count("90Studio")

if spec_cr_count < 10:
    record_failure("SPEC Copyright Attribution", f"Found {spec_cr_count} occurrences (min: 10)")
else:
    record_pass("SPEC Copyright Attribution", f"Found {spec_cr_count} occurrences of 'Copyrights reserved to 90Studio'")

if "Copyrights reserved to 90Studio" not in test_text:
    record_failure("TEST Copyright Attribution", "Missing 'Copyrights reserved to 90Studio' in test_specification.py")
else:
    record_pass("TEST Copyright Attribution", "Found 90Studio copyright notice in test_specification.py")

# ----------------------------------------------------------------------
# Check 3: Prohibited Patterns & Facade Detection
# ----------------------------------------------------------------------
prohibited_words = [
    ("TODO marker", r"\bTODO\b"),
    ("FIXME marker", r"\bFIXME\b"),
    ("TBD marker", r"\bTBD\b"),
    ("Lorem Ipsum", r"Lorem\s+Ipsum"),
    ("Placeholder", r"\bplaceholder\b"),
    ("Dummy", r"\bdummy\b"),
    ("Coming soon", r"coming\s+soon"),
    ("Not implemented", r"not\s+implemented|NotImplementedError")
]

for label, pat in prohibited_words:
    # Scan in spec_text (ignoring case)
    matches = list(re.finditer(pat, spec_text, re.IGNORECASE))
    if matches:
        real_matches = []
        for m in matches:
            line_no = spec_text[:m.start()].count("\n") + 1
            line_str = spec_text[m.start():m.end()+40].strip()
            real_matches.append(f"Line {line_no}: {line_str}")
        record_failure(f"Prohibited pattern in SPEC: {label}", f"Found {len(matches)} occurrences: {real_matches[:3]}")
    else:
        record_pass(f"Prohibited pattern check in SPEC: {label}", "CLEAN (0 occurrences)")

# Check test_text for facade or dummy tests
for label, pat in prohibited_words:
    matches = list(re.finditer(pat, test_text, re.IGNORECASE))
    if matches:
        record_failure(f"Prohibited pattern in TEST: {label}", f"Found {len(matches)} occurrences")
    else:
        record_pass(f"Prohibited pattern check in TEST: {label}", "CLEAN (0 occurrences)")

# ----------------------------------------------------------------------
# Check 4: Pre-populated Artifacts Detection
# ----------------------------------------------------------------------
artifact_hits = []
for root, dirs, files in os.walk(WORKSPACE):
    # Skip .git and .agents
    if ".git" in root or ".agents" in root:
        continue
    for f in files:
        if f.endswith(".log") or "result" in f.lower() or "output" in f.lower():
            artifact_hits.append(os.path.join(root, f))

if artifact_hits:
    record_failure("Pre-populated Artifacts", f"Found illicit artifact files: {artifact_hits}")
else:
    record_pass("Pre-populated Artifacts", "CLEAN (0 illicit log/result/output files in workspace)")

# ----------------------------------------------------------------------
# Check 5: Domain Blueprints Completeness (all 9 blueprints)
# ----------------------------------------------------------------------
blueprints = [
    ("BK-01", "Commercial Loan Origination & UCC-1 Filing"),
    ("BK-02", "Retail Account Opening & KYC Identity Verification"),
    ("BK-03", "Treasury Wire Transfer MT103 Processing"),
    ("TC-01", "Prepaid & Postpaid SIM Card Subscriber Registration"),
    ("TC-02", "FTTH Broadband ONT Provisioning & Port Assignment"),
    ("TC-03", "Corporate Fleet Mobile Plan Migration"),
    ("GB-01", "Accounts Payable Invoice Voucher Entry (SAP GUI)"),
    ("GB-02", "New Vendor Master Data Onboarding"),
    ("GB-03", "Employee Expense Reimbursement Entry")
]

for bp_id, name in blueprints:
    pattern = rf"#### 4\.[123]\.[123]\s+Use Case {bp_id}:(.*?)(?=#### 4\.[123]\.[123]|---|\Z)"
    match = re.search(pattern, spec_text, re.DOTALL)
    if not match:
        record_failure(f"Blueprint section {bp_id}", "Missing header/section in SPECIFICATION.md")
        continue
    body = match.group(1)
    
    # Check Workflow Execution Sequence
    has_seq = "- **Workflow Execution Sequence**:" in body or "- **Workflow Execution Sequence**" in body
    if not has_seq:
        record_failure(f"Blueprint {bp_id} sequence", "Missing '- **Workflow Execution Sequence**'")
    else:
        seq_start = body.find("Workflow Execution Sequence")
        seq_snippet = body[seq_start:seq_start+300]
        if len(seq_snippet.strip()) < 50:
            record_failure(f"Blueprint {bp_id} sequence length", "Workflow Execution Sequence appears trivial or empty")
        else:
            record_pass(f"Blueprint {bp_id} sequence", f"Present and non-trivial ({len(seq_snippet)} chars snippet)")

    # Check Expected Outcome
    has_outcome = "- **Expected Outcome**:" in body or "- **Expected Outcome**" in body
    if not has_outcome:
        record_failure(f"Blueprint {bp_id} outcome", "Missing '- **Expected Outcome**'")
    else:
        out_start = body.find("Expected Outcome")
        out_snippet = body[out_start:out_start+200]
        if len(out_snippet.strip()) < 30:
            record_failure(f"Blueprint {bp_id} outcome length", "Expected Outcome appears trivial or empty")
        else:
            record_pass(f"Blueprint {bp_id} outcome", f"Present and non-trivial ({len(out_snippet)} chars snippet)")

# ----------------------------------------------------------------------
# Check 6: Section 8.2 Compiler Production Hardening Directives
# ----------------------------------------------------------------------
if "### 8.2 Compiler Production Hardening Directives" in spec_text:
    record_pass("Section 8.2 Hardening Directives", "Present in SPECIFICATION.md")
else:
    record_failure("Section 8.2 Hardening Directives", "Section 8.2 missing from SPECIFICATION.md")

# ----------------------------------------------------------------------
# Check 7: AST Validation of Embedded Python Blocks in SPEC
# ----------------------------------------------------------------------
spec_lines = spec_text.splitlines()
in_py_block = False
cur_block = []
py_blocks = []
block_start_line = 0

for i, line in enumerate(spec_lines, start=1):
    stripped = line.strip()
    if stripped.startswith("```python"):
        in_py_block = True
        cur_block = []
        block_start_line = i
    elif in_py_block and stripped.startswith("```"):
        in_py_block = False
        py_blocks.append((block_start_line, "\n".join(cur_block)))
    elif in_py_block:
        cur_block.append(line)

record_pass("Embedded Python block count", f"Extracted {len(py_blocks)} Python blocks")

for start_line, code in py_blocks:
    try:
        ast.parse(textwrap.dedent(code))
        record_pass(f"AST parse Python block (line {start_line})", "Valid syntax")
    except Exception as e:
        record_failure(f"AST parse Python block (line {start_line})", str(e))

# ----------------------------------------------------------------------
# Check 8: Win32 ABI Struct sizeof(INPUT) == 40
# ----------------------------------------------------------------------
ULONG_PTR = ctypes.c_size_t
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ('dx', wintypes.LONG),
        ('dy', wintypes.LONG),
        ('mouseData', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ULONG_PTR)
    ]
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ('wVk', wintypes.WORD),
        ('wScan', wintypes.WORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ULONG_PTR)
    ]
class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ('uMsg', wintypes.DWORD),
        ('wParamL', wintypes.WORD),
        ('wParamH', wintypes.WORD)
    ]
class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ('mi', MOUSEINPUT),
        ('ki', KEYBDINPUT),
        ('hi', HARDWAREINPUT)
    ]
class INPUT(ctypes.Structure):
    _fields_ = [
        ('type', wintypes.DWORD),
        ('union', _INPUT_UNION)
    ]

input_sz = ctypes.sizeof(INPUT)
if input_sz == 40:
    record_pass("Win32 ctypes sizeof(INPUT)", f"40 bytes (exact 64-bit alignment verified)")
else:
    record_failure("Win32 ctypes sizeof(INPUT)", f"Expected 40 bytes, got {input_sz}")

# ----------------------------------------------------------------------
# Check 9: JSON Schemas Validation against Draft 2020-12
# ----------------------------------------------------------------------
try:
    from jsonschema import Draft202012Validator
    json_blocks = re.findall(r"```json\s*(.*?)\s*```", spec_text, re.DOTALL)
    valid_schemas = 0
    for idx, jb in enumerate(json_blocks, start=1):
        parsed = json.loads(jb)
        if isinstance(parsed, dict) and "$schema" in parsed:
            Draft202012Validator.check_schema(parsed)
            valid_schemas += 1
            record_pass(f"JSON Schema #{idx} validation", f"Schema title='{parsed.get('title')}' is valid Draft 2020-12")
    if valid_schemas < 2:
        record_failure("JSON Schema Count", f"Expected at least 2 formal schemas, found {valid_schemas}")
except Exception as e:
    record_failure("JSON Schema Draft202012 check", str(e))

# ----------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------
print("\n=== AUDIT SUMMARY ===")
print(f"Total Failures: {len(failures)}")
if failures:
    for f in failures:
        print(f"  - {f[0]}: {f[1]}")
    sys.exit(1)
else:
    print("ALL FORENSIC CHECKS PASSED EMPIRICALLY WITH ZERO VIOLATIONS!")
    sys.exit(0)
