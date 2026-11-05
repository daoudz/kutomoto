# Investigation & QA Strategy Report: Encoded Slash Route Fallthrough & Test Suite Coverage

**Agent**: `m4_it4_explorer_3` (Explorer: Test Suite Coverage Investigator & QA Strategist)  
**Parent Agent**: `7675637a-9a1e-40c3-a3cd-063a24f49a5c`  
**Date**: 2026-11-05T08:32:00Z  
**Target Milestone**: Milestone 4 Iteration 4  
**Status**: COMPLETE (Hard Handoff — Read-Only Investigation)  

---

## 1. Observation

### 1.1 Direct Inspection of `tests/test_m4_it3_adversarial_challenge.py`
In `tests/test_m4_it3_adversarial_challenge.py`:
- **Docstring of `test_advanced_fuzzing_and_unicode_homoglyphs` (`lines 468-481`)**:
  ```python
  468:     def test_advanced_fuzzing_and_unicode_homoglyphs(self, client):
  469:         """
  470:         Adversarial test with unicode homoglyphs, zero-width chars, and overlong encodings:
  471:         - Fullwidth solidus (%EF%BC%8F)
  472:         - Fullwidth asterisk (%EF%BC%8A)
  473:         - Fullwidth question mark (%EF%BC%9F)
  474:         - Zero-width space (%E2%80%8B)
  475:         - Non-breaking space (%C2%A0)
  476:         - Right-to-left override (%E2%80%AE)
  477:         - Double URL encoding (%252e%252e%252f)
  478:         - Windows device names (CON, PRN, AUX, NUL, COM1, LPT1)
  479:         - Windows drive letters (C:, C%3A, C%3A%2F)
  480:         - Buffer overflow length string ('A' * 4096)
  481:         """
  ```
- **Vector List (`lines 482-501`)**:
  ```python
  482:         advanced_vectors = [
  483:             "%252e%252e%252f",
  484:             "%EF%BC%8F",
  485:             "%EF%BC%8A",
  486:             "%EF%BC%9F",
  487:             "%E2%80%8B",
  488:             "%C2%A0",
  489:             "%E2%80%AE",
  490:             "CON",
  491:             "PRN",
  492:             "AUX",
  493:             "NUL",
  494:             "COM1",
  495:             "LPT1",
  496:             "C:",
  497:             "C%3A",
  498:             "C:%5C",
  499:             "C%3A%5C",
  500:             "A" * 2048,
  501:         ]
  ```
  **Observation**: While line 479 of the docstring explicitly specifies `Windows drive letters (C:, C%3A, C%3A%2F)`, vector `"C%3A%2F"` was omitted from `advanced_vectors` in the current file on disk. When this vector was executed by `m4_it3_challenger_1_gen2`, it produced the failure:
  `AssertionError: Vector 'Advanced/Unicode vector: C%3A%2F...' failed security check: expected HTTP 404, got 200.`

### 1.2 Direct Empirical Reproduction of Vector `"C%3A%2F"`
Executing an isolated HTTP probe against the production server:
```powershell
python -c "import sys; sys.path.insert(0, 'src'); from fastapi.testclient import TestClient; from kutomoto.server.app import app; c = TestClient(app); r = c.get('/api/execute/audit/C%3A%2F'); print('STATUS:', r.status_code); print('CONTENT-TYPE:', r.headers.get('content-type')); print('BODY:', r.text[:120])"
```
**Direct Output**:
```
STATUS: 200
CONTENT-TYPE: text/html; charset=utf-8
BODY: <!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
```

### 1.3 Identification of the Dual-Layer Root Cause Mechanism
1. **Layer 1: Starlette Path Parameter Routing**:
   In `src/kutomoto/server/app.py:900`:
   ```python
   @app_instance.get("/api/execute/audit/{workflow_id}")
   ```
   Starlette compiles standard `{param}` tokens into regex `[^/]+`. When the client sends `GET /api/execute/audit/C%3A%2F`, ASGI unquotes `%2F` into `/`, yielding the request path `/api/execute/audit/C:/`.
   Because `/api/execute/audit/C:/` contains a trailing slash, it matches neither `/api/execute/audit/{workflow_id}` nor any other API route.
2. **Layer 2: Windows OS Drive Letter Reset in Starlette `StaticFiles`**:
   The unhandled request falls through to `src/kutomoto/server/app.py:960`:
   ```python
   app_instance.mount("/", StaticFiles(directory=str(UI_DIR), html=True), name="ui")
   ```
   In `starlette.staticfiles.StaticFiles`:
   - `get_path()` executes `os.path.normpath(os.path.join(*route_path.split("/")))`.
   - Splitting `/api/execute/audit/C:/` gives `['', 'api', 'execute', 'audit', 'C:', '']`.
   - On Windows (`ntpath.py:join`), when `os.path.join` encounters an element with a drive specification (`'C:'`), it discards all preceding relative path segments (`api\execute\audit`), resetting the path to `'C:'`.
   - `lookup_path('C:')` runs `os.path.join(UI_DIR, 'C:')`. Because `UI_DIR` is located on drive `C:` (`c:\Users\daoud\projects\kutomoto\src\kutomoto\ui`), Windows resolves this back to `UI_DIR` itself (`stat.S_ISDIR == True`).
   - Because `html=True` is enabled and the URL ended in `/`, `StaticFiles` checks `os.path.join('C:', 'index.html')`, which exists in `UI_DIR`.
   - `StaticFiles` returns `FileResponse(UI_DIR / "index.html")` with `HTTP 200 OK`.

### 1.4 Discovery of Additional Vulnerability: Unhandled 500 Crash on Alternative Drive Letters
When probing alternative drive letters:
```powershell
python -c "import sys; sys.path.insert(0, 'src'); from fastapi.testclient import TestClient; from kutomoto.server.app import app; c = TestClient(app, raise_server_exceptions=False);
for v in ['C%3A%2F', 'D%3A%2F', 'Z%3A%2F']:
    r = c.get(f'/api/execute/audit/{v}')
    print(v, '-> status:', r.status_code, 'ct:', r.headers.get('content-type', ''))"
```
**Direct Output**:
```
C%3A%2F -> status: 200 ct: text/html; charset=utf-8
D%3A%2F -> status: 500 ct: text/plain; charset=utf-8
Z%3A%2F -> status: 500 ct: text/plain; charset=utf-8
```
**Exception Trace**:
In `starlette/staticfiles.py:160` (`lookup_path`):
`if os.path.commonpath([full_path, directory]) != str(directory):`
`ValueError: Paths don't have the same drive`
Because `full_path` is on drive `D:` while `directory` is on drive `C:`, Python's `os.path.commonpath` raises `ValueError`, crashing the request with an unhandled HTTP 500 server error instead of an RFC 7807 404 Problem Details response.

### 1.5 Full Catalog of Encoded Slash (`%2F`) and Path Separator Vectors

Empirical probing of all slash, traversal, and drive letter variants against the production server:

| Vector | ASGI Decoded Path | Unfixed Status | Unfixed Body Type | Vulnerability / Defect |
|---|---|---|---|---|
| `C%3A%2F` | `/api/execute/audit/C:/` | **200** | `text/html` | Route fallthrough -> StaticFiles serves `index.html` |
| `C:/` | `/api/execute/audit/C:/` | **200** | `text/html` | Route fallthrough -> StaticFiles serves `index.html` |
| `c%3A%2F` | `/api/execute/audit/c:/` | **200** | `text/html` | Lowercase drive letter fallthrough -> `index.html` |
| `c:/` | `/api/execute/audit/c:/` | **200** | `text/html` | Lowercase literal fallthrough -> `index.html` |
| `D%3A%2F` | `/api/execute/audit/D:/` | **500** | `text/plain` | Crash: `ValueError: Paths don't have the same drive` |
| `d%3A%2F` | `/api/execute/audit/d:/` | **500** | `text/plain` | Crash: `ValueError: Paths don't have the same drive` |
| `Z%3A%2F` | `/api/execute/audit/Z:/` | **500** | `text/plain` | Crash: `ValueError: Paths don't have the same drive` |
| `C%3A%2Findex.html` | `/api/execute/audit/C:/index.html` | **200** | `text/html` | Directly serves `index.html` |
| `..%2F` | `/api/execute/audit/../` | 404 | `application/json` | Normal 404 Problem Details (StaticFiles lookup fails) |
| `..%2F..%2F` | `/api/execute/audit/../../` | 404 | `application/json` | Normal 404 Problem Details |
| `..%2F..%2Fwin.ini` | `/api/execute/audit/../../win.ini` | 404 | `application/json` | Normal 404 Problem Details |
| `audit%2F` | `/api/execute/audit/audit/` | 404 | `application/json` | Normal 404 Problem Details |
| `foo%2Fbar` | `/api/execute/audit/foo/bar` | 404 | `application/json` | Normal 404 Problem Details |
| `%2F` | `/api/execute/audit//` | 404 | `application/json` | Normal 404 Problem Details |
| `C%3A%5C` | `/api/execute/audit/C:\` | 404 | `application/json` | Normal 404 Problem Details |
| `C:%5C` | `/api/execute/audit/C:\` | 404 | `application/json` | Normal 404 Problem Details |

### 1.6 Baseline Repository Test Execution
Executing `python -m pytest tests/`:
- **Current result**: **367 passed in 44.93s** (because `C%3A%2F` is currently commented out / absent from `advanced_vectors` in `test_m4_it3_adversarial_challenge.py`).
- **When `C%3A%2F` is added**: 1 failed, 366 passed.
- **When `:path` is applied to route**: 100% pass across all 367+ tests.

---

## 2. Logic Chain

1. **Step 1 (Root Cause)**:
   In `src/kutomoto/server/app.py:900`, `@app_instance.get("/api/execute/audit/{workflow_id}")` uses the standard path converter which does not match forward slashes `/`. Any request with an unquoted `%2F` (such as `C%3A%2F` -> `C:/`) causes Starlette to reject the route match.
2. **Step 2 (Catch-all Fallthrough)**:
   Because `app_instance.mount("/", StaticFiles(directory=str(UI_DIR), html=True), name="ui")` is mounted at root `"/"`, any unmatched request under `/api/` reaches `StaticFiles`.
3. **Step 3 (Windows ntpath Behavior)**:
   In `StaticFiles.get_path()`, `os.path.join(*parts)` discards preceding path components when encountering `'C:'`. Consequently, `lookup_path('C:')` resolves to `UI_DIR` on drive `C:`, and because `html=True` is enabled, Starlette serves `index.html` with HTTP 200 OK.
4. **Step 4 (Remediation Mechanism)**:
   Updating line 900 in `src/kutomoto/server/app.py` from:
   `@app_instance.get("/api/execute/audit/{workflow_id}")`
   to:
   `@app_instance.get("/api/execute/audit/{workflow_id:path}")`
   instructs Starlette's router to match all subpaths and forward slashes.
5. **Step 5 (Input Sanitization Interception)**:
   Once matched by `get_execution_audit(workflow_id: str)`, the request enters `execution_manager.get_audit_summary(workflow_id)`. Lines 549-552 enforce strict alphanumeric and slug validation:
   ```python
   safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "", workflow_id)
   if not safe_id or safe_id != workflow_id:
       return None
   ```
   For `"C:/"`, `safe_id` is `"C"`. Because `"C" != "C:/"`, the method immediately returns `None`.
6. **Step 6 (RFC 7807 Exception Formatting)**:
   Line 907-911 raises:
   ```python
   raise HTTPException(
       status_code=404,
       detail=f"Audit log summary for workflow '{workflow_id}' not found.",
   )
   ```
   FastAPI's exception handler (registered in `create_app()`) formats this into compliant RFC 7807 Problem Details stamped with `"copyright": "Copyrights reserved to 90Studio"`.
7. **Step 7 (Empirical Validation of Fix)**:
   Testing the `:path` route with all 16 vectors listed in Section 1.5 verified that:
   - `C%3A%2F`, `c%3A%2F`, `C:/`, `c:/`, `C%3A%2Findex.html` all return HTTP 404 Problem Details with 90Studio attribution.
   - `D%3A%2F`, `d%3A%2F`, `Z%3A%2F` return HTTP 404 Problem Details (eliminating the HTTP 500 crash).
   - Zero confidential execution data is disclosed.

---

## 3. Caveats

- **Read-Only Explorer Scope**: In accordance with the Teamwork explorer archetype, this agent did not modify any production or test source code. All empirical validations were conducted via in-memory dynamic test harness compilation.
- **Scope of Route Conversion**: Updating `{workflow_id:path}` is specifically required for `/api/execute/audit/{workflow_id:path}`. For `/api/workflows/{workflow_id}`, `WorkflowRepository` already safely sanitizes inputs (`safe_id = re.sub(...)`), but adopting defense-in-depth across `/api/` mounts is also recommended.
- No other caveats.

---

## 4. Conclusion

### Required Worker Code Changes:

#### 1. Primary Remediation in `src/kutomoto/server/app.py`:
Change line 900 from:
```python
@app_instance.get("/api/execute/audit/{workflow_id}")
```
to:
```python
@app_instance.get("/api/execute/audit/{workflow_id:path}")
```

#### 2. Test Restoration in `tests/test_m4_it3_adversarial_challenge.py`:
In `test_advanced_fuzzing_and_unicode_homoglyphs` (`line 500`), restore `"C%3A%2F"` to `advanced_vectors`:
```python
        advanced_vectors = [
            "%252e%252e%252f",
            "%EF%BC%8F",
            "%EF%BC%8A",
            "%EF%BC%9F",
            "%E2%80%8B",
            "%C2%A0",
            "%E2%80%AE",
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "LPT1",
            "C:",
            "C%3A",
            "C:%5C",
            "C%3A%5C",
            "C%3A%2F",
            "A" * 2048,
        ]
```

#### 3. Test Enhancement in `tests/test_api.py`:
In `test_get_audit_wildcard_and_path_traversal_sanitization_rejects_404` (`line 603`), expand `adversarial_queries`:
```python
            adversarial_queries = [
                "*",
                "*sensitive*",
                "..%2F..%2Fwin.ini",
                "C%3A%2F",
                "C:/",
                "D%3A%2F",
            ]
```

---

## 5. Verification Method

The worker agent must execute the following step-by-step verification plan:

### Step 1: Pre-Fix Failure Confirmation
Confirm the route fallthrough reproduces before applying code changes:
```powershell
python -c "import sys; sys.path.insert(0, 'src'); from fastapi.testclient import TestClient; from kutomoto.server.app import app; c = TestClient(app); r = c.get('/api/execute/audit/C%3A%2F'); assert r.status_code == 200, f'Expected 200 before fix, got {r.status_code}'"
```

### Step 2: Apply Implementation Edits
Apply the edits described in Section 4 to:
1. `src/kutomoto/server/app.py:900`
2. `tests/test_m4_it3_adversarial_challenge.py:500`
3. `tests/test_api.py:603`

### Step 3: Run Isolated Route Probes
Verify `C%3A%2F` and alternative drive letters return HTTP 404 with 90Studio attribution:
```powershell
python -c "import sys; sys.path.insert(0, 'src'); from fastapi.testclient import TestClient; from kutomoto.server.app import app; c = TestClient(app);
for v in ['C%3A%2F', 'C:/', 'D%3A%2F']:
    r = c.get(f'/api/execute/audit/{v}')
    assert r.status_code == 404, f'{v} failed: {r.status_code}'
    assert r.json().get('copyright') == 'Copyrights reserved to 90Studio', f'{v} missing copyright'
print('Isolated probe verification passed!')"
```

### Step 4: Run Targeted Test Suites
```powershell
python -m pytest tests/test_api.py -v
python -m pytest tests/test_m4_it3_adversarial_challenge.py -v
python -m pytest tests/test_ui_m4_challenge.py -v
python -m pytest tests/test_m4_empirical_challenge.py tests/test_m4_deep_stress_challenge.py -v
```
All tests across these suites must report 100% pass rate.

### Step 5: Full Repository Regression Test Suite
```powershell
python -m pytest tests/
```
Expected result: **367+ passed with 0 failures** in ~45s.

### Step 6: Code Style & Linting Check
```powershell
python -m ruff check src/ tests/
```
Expected result: `All checks passed!`

### Invalidation Conditions
This QA strategy is invalidated if:
1. `GET /api/execute/audit/C%3A%2F` returns HTTP 200 or serves HTML.
2. `GET /api/execute/audit/D%3A%2F` causes an unhandled 500 `ValueError`.
3. Any test in `tests/test_api.py` or the 367+ full repository suite fails.
4. Any Problem Details response lacks `"copyright": "Copyrights reserved to 90Studio"`.
