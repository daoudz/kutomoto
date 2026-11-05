# Quality & Adversarial Review Report: Milestone 4 Iteration 3

**Agent**: `m4_it3_reviewer_2_gen2` (Reviewer & Adversarial Critic)  
**Parent Agent**: `7675637a-9a1e-40c3-a3cd-063a24f49a5c`  
**Date**: 2026-11-05T08:22:00Z  
**Verdict**: **REQUEST_CHANGES**  

---

## 1. Observation

A comprehensive inspection and empirical execution of the implementation in `src/kutomoto/server/app.py`, UI static assets in `src/kutomoto/ui/`, and test suites was conducted.

### 1.1 Integrity Check
The implementation was thoroughly examined for integrity violations:
- **Hardcoded test results**: Verified absent. `get_audit_summary()` parses fields dynamically from active state, in-memory structures, and on-disk JSON payloads.
- **Facade implementations**: Verified absent. Genuine FSM transitions, event streaming, and file I/O are implemented.
- **Shortcuts / mock bypasses**: Verified absent. Production code uses genuine adapters; mocks are confined strictly to test fixtures and DI injection points.
- **Fabricated verification outputs**: Verified absent. Worker claims were independently reproduced.
- **Self-certifying work**: All findings and fixes were tested using independent assertions.

### 1.2 Verification of F-M4-04 Remediation & Precedence
In `src/kutomoto/server/app.py`:
1. **Active Execution Precedence (`lines 554-566`)**:
   ```python
   if (self._workflow_id == safe_id or self._execution_id == safe_id) and self.is_active():
       return {
           "workflow_id": self._workflow_id,
           "execution_id": self._execution_id,
           "workflow_name": self._workflow_name,
           "status": self.get_state(),
           "duration_seconds": round(time.perf_counter() - self._start_time, 2),
           "total_steps": self._total_steps,
           "current_step_index": self._current_step_index,
           "timestamp_utc": datetime.now(timezone.utc).isoformat(),
           "copyright": __copyright__,
       }
   ```
   This evaluation occurs **prior** to inspecting `self._audit_summaries` (`line 569`) and `self._last_audit_summary` (`line 573`). Even if a previous run of the workflow completed and left an audit summary in memory, a new execution immediately overrides it, returning active telemetry (`RUNNING`).
2. **Active Query Symmetry**:
   Evaluating `(self._workflow_id == safe_id or self._execution_id == safe_id)` allows clients to query `/api/execute/audit/{id}` by either `workflow_id` or `execution_id` while active. Both yield identical HTTP 200 responses with active runner state.
3. **On-Disk Fallback Symmetry (`lines 576-603`)**:
   ```python
   candidates = sorted(audit_dir.glob(f"audit_{safe_id}_*.json"), reverse=True)
   if not candidates:
       candidates = sorted(audit_dir.glob(f"audit_*_{safe_id}_*.json"), reverse=True)
   for p in candidates:
       try:
           data = json.loads(p.read_text(encoding="utf-8"))
           if data.get("workflow_id") == safe_id or data.get("execution_id") == safe_id:
               summary = data.get("execution_summary", {})
               return { ... }
   ```
   Given the filename convention `audit_{workflow_id}_{execution_id}_{timestamp}.json`, querying by `workflow_id` matches the prefix pattern, while querying by `execution_id` matches the midfix fallback pattern. Secondary JSON validation (`data.get(...) == safe_id`) prevents false positives.

### 1.3 UI Integration & Enterprise Requirements
Inspection of UI static assets confirmed compliance with enterprise requirements:
- **`src/kutomoto/ui/index.html`**: Header brand, tab navigation (Visual Designer, Flow Builder, Execution Console, Target Windows, Settings), canvas workspace, inspector sidebar, modal dialogs, and 3-second countdown HUD modal (`lines 422-450`).
- **`src/kutomoto/ui/css/kutomoto.css`**: Complete enterprise dark theme (slate/blue tokens), 8-handle resize cursors (`nwse-resize`, `nesw-resize`, etc.), SVG circular progress HUD styles, and toast notifications.
- **`src/kutomoto/ui/js/designer.js`**: HTML5 Canvas visual designer engine with 8 resize handles (`nw`, `n`, `ne`, `e`, `se`, `s`, `sw`, `w`), dual-coordinate normalization (`getNormalizedCoordinates`), magnetic edge alignment snapping with visual guides, and 2D spatial reading-order auto-sequencing.
- **`src/kutomoto/ui/js/runner.js`**: Step-by-step flow builder supporting all 10 atomic action types (`focus_window`, `click`, `type_text`, `key_press`, `hotkey`, `clear_field`, `delay`, `submit`, `scroll`, `prompt_user_input`), drag-and-drop step reordering, parameter editing modals, and 3-second countdown HUD animation with Escape-key abort support.
- **Attribution Watermarks**: The watermark `"Copyrights reserved to 90Studio"` is present across `index.html` (title, badge, footer), `kutomoto.css`, `app.js`, `designer.js`, and `runner.js`.

### 1.4 Test Suite & Linting Execution
1. **API Test Suite**:
   `python -m pytest tests/test_api.py -v` -> **22 passed in 0.72s**.
2. **UI Challenge Suite**:
   `python -m pytest tests/test_ui_m4_challenge.py -v` -> **22 passed in 2.19s**.
3. **Linter**:
   `python -m ruff check src/ tests/` -> **All checks passed!**.
4. **Adversarial Stress Challenge**:
   `python -m pytest tests/test_m4_empirical_challenge.py tests/test_m4_deep_stress_challenge.py -v` -> **32 passed in 6.44s**.

### 1.5 Finding: Route Fallthrough Defect on Encoded Slashes (`%2F`)
When running the full repository test suite:
```powershell
python -m pytest tests/
```
Output: **1 failed, 366 passed in 45.06s**.

**Failing test**:
`tests/test_m4_it3_adversarial_challenge.py::TestFM403AdversarialAttackVectors::test_advanced_fuzzing_and_unicode_homoglyphs`

**Empirical verification of the failure**:
```powershell
python -c "import sys; sys.path.insert(0, 'src'); from fastapi.testclient import TestClient; from kutomoto.server.app import app; c = TestClient(app); r = c.get('/api/execute/audit/C%3A%2F'); print('STATUS:', r.status_code); print('BODY:', r.text[:120])"
```
**Output**:
```
STATUS: 200
BODY: <!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
```

**Root Cause**:
In `src/kutomoto/server/app.py:900`:
```python
@app_instance.get("/api/execute/audit/{workflow_id}")
```
In Starlette / FastAPI, the path parameter `{workflow_id}` (without `:path`) only matches a single path segment. When an adversarial query containing an encoded forward slash (e.g. `C%3A%2F`, `foo%2Fbar`, or `audit%2F`) is requested, ASGI decodes `%2F` into `/`. The URL becomes `/api/execute/audit/C:/`, which fails to match `/api/execute/audit/{workflow_id}`.
Because no `/api/` route matches, Starlette routes the request to the catch-all mount at line 960:
```python
app_instance.mount("/", StaticFiles(directory=str(UI_DIR), html=True), name="ui")
```
With `html=True`, `StaticFiles` serves `index.html` with HTTP 200 OK. Consequently, an invalid/adversarial audit query returns an HTML document with HTTP 200 OK instead of an RFC 7807 404 Problem Details response stamped with 90Studio attribution.

---

## 2. Logic Chain

1. **Step 1**: The worker's remediation of F-M4-04 correctly implemented symmetric identifier lookup for active executions and on-disk fallback, and correctly prioritized active executions over stale memory caches.
2. **Step 2**: The UI implementation satisfies all Milestone 4 functional requirements: 8-handle canvas geometry, 10 action handlers, countdown HUD, and 90Studio attribution.
3. **Step 3**: The worker's handoff states in Section 5.2 that the fix is invalidated if "Any test in tests/test_api.py or the test suite fails."
4. **Step 4**: The full test suite has 1 failing test (`tests/test_m4_it3_adversarial_challenge.py::test_advanced_fuzzing_and_unicode_homoglyphs`) because querying `/api/execute/audit/C%3A%2F` returns HTTP 200 HTML.
5. **Step 5**: The root cause is that `@app_instance.get("/api/execute/audit/{workflow_id}")` does not capture slashes, allowing unhandled paths to fall through to `StaticFiles(html=True)`.
6. **Step 6**: Changing the route definition to `@app_instance.get("/api/execute/audit/{workflow_id:path}")` ensures all subpaths under `/api/execute/audit/` are processed by `get_execution_audit()`. The existing sanitization logic (`re.sub(r"[^a-zA-Z0-9_\-]", "", workflow_id)`) will reject any string containing `/` and return a secure HTTP 404 RFC 7807 Problem Details response.
7. **Step 7**: Because there is a failing test in the repository test suite and an unhandled route fallthrough edge case, the reviewer cannot issue APPROVE. A formal verdict of **REQUEST_CHANGES** is required.

---

## 3. Caveats

- **Scope of Defect**: The issue is isolated strictly to route matching for path parameters containing encoded slashes (`%2F`) in the audit endpoint.
- **Engine Core & UI**: The execution engine, 7-state FSM, Win32 input core, 8-handle visual designer, flow builder, and countdown HUD are 100% verified and robust.
- **Reviewer Code Edit Constraint**: Reviewer agents are restricted from modifying implementation source code. The remediation must be applied by a worker agent.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

### Required Remediation:
In `src/kutomoto/server/app.py`, update line 900:
```python
# Change:
@app_instance.get("/api/execute/audit/{workflow_id}")

# To:
@app_instance.get("/api/execute/audit/{workflow_id:path}")
```
This ensures that any identifier containing forward slashes or encoded traversal sequences (e.g., `C%3A%2F`, `foo%2Fbar`, `..%2F..%2Fwin.ini`) is matched by the route handler, intercepted by `get_audit_summary()`, and returned as an RFC 7807 404 Problem Details response rather than falling through to the SPA static files mount.

---

## 5. Verification Method

1. **Reproduce Failure**:
   ```powershell
   python -m pytest tests/test_m4_it3_adversarial_challenge.py -k "test_advanced_fuzzing_and_unicode_homoglyphs" -v
   ```
   Observed: `AssertionError: Vector 'Advanced/Unicode vector: C%3A%2F...' failed security check: expected HTTP 404, got 200.`

2. **Verify After Remediation**:
   Apply `@app_instance.get("/api/execute/audit/{workflow_id:path}")` in `src/kutomoto/server/app.py:900`, then execute:
   ```powershell
   python -m pytest tests/test_m4_it3_adversarial_challenge.py -v
   python -m pytest tests/
   python -m ruff check src/ tests/
   ```
   All 367 tests must pass (100% pass rate) with zero lint errors.
