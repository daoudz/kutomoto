# Milestone 4 Iteration 2 Challenger Report: API Robustness & Audit Integrity

**Agent**: `m4_it2_challenger_2` (Empirical Challenger: API Robustness, Audit Integrity, Payload Fuzzing)  
**Parent Agent**: `59700fc9-320d-4ed3-b1db-2fc709fed831`  
**Date**: 2026-11-05T08:02:00Z  
**Verdict**: **FAIL** (2 Confirmed Empirical Vulnerabilities/Defects Identified in `src/kutomoto/server/app.py`)

---

## 1. Observation

Direct empirical testing of the audit endpoint and server API surface revealed the following:

### 1.1 Baseline Test Suite Status
Running the project verification command:
```powershell
python -m pytest tests/test_api.py -v
```
**Result**: `20 passed in 0.67s` (100% pass rate).

### 1.2 Core Audit Verification Items
1. **404 Problem Details when non-existent**:
   `GET /api/execute/audit/{non_existent_id}` returns HTTP 404 with RFC 7807 problem details:
   - `type`: `"https://90studio.com/errors/404"`
   - `title`: `"Audit log summary for workflow '<id>' not found."`
   - `status`: `404`
   - `detail`: `"Audit log summary for workflow '<id>' not found."`
   - `instance`: `"/api/execute/audit/<id>"`
   - `copyright`: `"Copyrights reserved to 90Studio"`
2. **200 OK upon normal completion**:
   Returns HTTP 200 with `status: "SUCCESS"`, duration, step counts, and attribution `"copyright": "Copyrights reserved to 90Studio"`.
3. **200 OK upon abort**:
   Returns HTTP 200 with `status: "ABORTED"` and attribution `"copyright": "Copyrights reserved to 90Studio"`.
4. **API Error Handling & Payload Fuzzing**:
   Non-JSON payloads, syntax-invalid JSON, and empty objects to `/api/workflows`, `/api/designer/compile`, and `/api/execute/start` are rejected with HTTP 422 Problem Details. Out-of-order pause/resume when IDLE return HTTP 409 Conflict without corrupting server state.

### 1.3 Finding F-M4-03: Glob Pattern Injection & Information Disclosure
In `src/kutomoto/server/app.py`, line 563:
```python
        audit_dirs = [Path.home() / ".kutomoto" / "audit", BASE_DIR / "data" / "audit", BASE_DIR / "logs" / "audit"]
        for audit_dir in audit_dirs:
            if audit_dir.is_dir():
                for p in audit_dir.glob(f"audit_{workflow_id}_*.json"):
```
The parameter `workflow_id` is passed directly from URL path without escaping glob metacharacters.
Empirical reproduction script:
```python
# Create an on-disk audit file for a confidential workflow:
# audit_sensitive_wf_exec123_20261105.json
client.get("/api/execute/audit/*")
```
**Verbatim Output**:
```
Pattern "*" -> Status 200
  Leaked workflow_name: Sensitive Banking Wire
Pattern "*sensitive*" -> Status 200
  Leaked workflow_name: Sensitive Banking Wire
```
Supplying `*` or wildcard patterns matches arbitrary audit files stored on disk and discloses execution history belonging to other workflows.

### 1.4 Finding F-M4-04: Asymmetric Identifier Handling in Active Execution Polling
In `src/kutomoto/server/app.py`, lines 541-558:
```python
    def get_audit_summary(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve audit log summary for a workflow ID or execution ID."""
        if workflow_id in self._audit_summaries:
            return self._audit_summaries[workflow_id]

        if (self._workflow_id == workflow_id or self._execution_id == workflow_id) and self._last_audit_summary:
            return self._last_audit_summary

        if self._workflow_id == workflow_id and self.is_active():
            return {
                "workflow_id": self._workflow_id,
                "execution_id": self._execution_id,
                "workflow_name": self._workflow_name,
                "status": self.get_state(),
                ...
```
Line 547 checks ONLY `self._workflow_id == workflow_id`. It omits `or self._execution_id == workflow_id`.
Empirical reproduction script:
```python
# Launch a workflow with 200ms delay:
# r_start returns {"workflow_id": "wf-...", "execution_id": "exec-..."}
# While execution is active:
r_wf = client.get(f"/api/execute/audit/{wf_id}")    # Status: 200 OK
r_exec = client.get(f"/api/execute/audit/{exec_id}") # Status: 404 NOT FOUND
```
**Verbatim Output**:
```
Workflow started: wf_id=8fc1822c-7a05-4a64-b7e3-c201f370b61b, exec_id=09aa5fb2-17e9-4080-8e2f-228e69a47348
Active query by workflow_id: Status 200
Active query by execution_id: Status 404
Active query by execution_id returned 404: {'type': 'https://90studio.com/errors/404', 'title': "Audit log summary for workflow '09aa5fb2-17e9-4080-8e2f-228e69a47348' not found.", 'status': 404, 'detail': "Audit log summary for workflow '09aa5fb2-17e9-4080-8e2f-228e69a47348' not found.", 'instance': '/api/execute/audit/09aa5fb2-17e9-4080-8e2f-228e69a47348', 'copyright': 'Copyrights reserved to 90Studio'}
Completed query by execution_id: Status 200
```
While execution is in progress, querying by `execution_id` (the primary handle returned to the frontend by `POST /api/execute/start`) unexpectedly returns HTTP 404. Once the task finishes, querying by `execution_id` suddenly returns HTTP 200.

Additionally, on-disk fallback retrieval queries `glob(f"audit_{workflow_id}_*.json")`. If memory cache is cleared and a caller queries by `execution_id`, on-disk files (`audit_{wf_id}_{exec_id}_{timestamp}.json`) cannot be found, returning HTTP 404.

---

## 2. Logic Chain

1. **Premise**: In `kutomoto.server.app`, the audit endpoint `GET /api/execute/audit/{workflow_id}` is intended to serve as the unified audit query interface for both completed and in-flight executions, queryable by either `workflow_id` or `execution_id`.
2. **Analysis of F-M4-03**:
   - `get_audit_summary` constructs an unescaped glob pattern `f"audit_{workflow_id}_*.json"`.
   - In Python `pathlib.Path.glob`, characters `*`, `?`, `[` are glob wildcards.
   - Any client requesting `/api/execute/audit/*` causes `audit_dir.glob("audit_*_*.json")` to match the first file in the directory, regardless of workflow identity.
   - This bypasses access controls and leaks execution summaries, timestamps, operator usernames, and target applications across workflows.
3. **Analysis of F-M4-04**:
   - `POST /api/execute/start` generates and returns `execution_id` as the flight identifier.
   - During execution, the docstring specifies querying by either ID.
   - Line 547 only checks `self._workflow_id == workflow_id`.
   - When queried by `execution_id`, the in-memory check fails, the active check fails, and the on-disk glob fails, producing an illegitimate HTTP 404 Problem Details error for active executions.
   - Furthermore, on-disk fallback assumes the query ID is always `workflow_id`. If `execution_id` is queried on disk, the glob fails to match.

---

## 3. Caveats

- Win32 hardware SendInput testing was conducted using simulated drivers (`MockWin32Driver`), as interactive desktop execution is planned for Milestone 5.
- The 20 baseline unit tests in `tests/test_api.py` all pass cleanly because they only query completed or aborted workflows by `workflow_id`, masking both vulnerabilities from CI/CD detection.

---

## 4. Conclusion

**Verdict: FAIL**

The implementation in `src/kutomoto/server/app.py` has two confirmed vulnerabilities/defects that require remediation:

1. **F-M4-03 (High Severity)**: Unsanitized glob pattern injection in `get_audit_summary` (`app.py:563`). Must escape glob metacharacters and sanitize the input ID (e.g. `re.sub(r"[^a-zA-Z0-9_\-]", "", workflow_id)`).
2. **F-M4-04 (Medium Severity)**: Missing `execution_id` match during active execution in `app.py:547`, and inability to find on-disk audit files when querying by `execution_id`.

### Required Worker Remediation
In `src/kutomoto/server/app.py`:
1. Update line 547 to:
   ```python
   if (self._workflow_id == workflow_id or self._execution_id == workflow_id) and self.is_active():
   ```
2. In `get_audit_summary`, sanitize `workflow_id` before performing on-disk glob lookups:
   ```python
   safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "", workflow_id)
   if not safe_id:
       return None
   ```
3. Support matching by either `workflow_id` or `execution_id` in on-disk fallback:
   ```python
   for audit_dir in audit_dirs:
       if audit_dir.is_dir():
           # Check matching prefix (workflow_id) or midfix (execution_id)
           candidates = list(audit_dir.glob(f"audit_{safe_id}_*.json"))
           if not candidates:
               candidates = list(audit_dir.glob(f"audit_*_{safe_id}_*.json"))
           for p in candidates:
               try:
                   data = json.loads(p.read_text(encoding="utf-8"))
                   ...
   ```

---

## 5. Verification Method

To independently reproduce both findings:

### 5.1 Command: Reproduce F-M4-03 (Glob Pattern Injection Leak)
```powershell
python -c @"
import os, sys, json
sys.path.insert(0, os.path.abspath('src'))
from pathlib import Path
from fastapi.testclient import TestClient
from kutomoto.server.app import app, execution_manager, BASE_DIR

client = TestClient(app)
audit_dir = BASE_DIR / 'data' / 'audit'
audit_dir.mkdir(parents=True, exist_ok=True)
p = audit_dir / 'audit_confidential_bank_wf_exec99_20261105.json'
p.write_text(json.dumps({'workflow_id': 'confidential_bank_wf', 'workflow_name': 'SECRET WIRE', 'execution_summary': {'final_status': 'SUCCESS'}}), encoding='utf-8')
try:
    execution_manager._audit_summaries.clear()
    execution_manager._last_audit_summary = None
    r = client.get('/api/execute/audit/*')
    assert r.status_code == 200 and r.json()['workflow_name'] == 'SECRET WIRE'
    print('VULNERABILITY REPRODUCED: Wildcard * matched and leaked audit log!')
finally:
    if p.exists(): p.unlink()
"@
```

### 5.2 Command: Reproduce F-M4-04 (Active Execution ID 404 Defect)
```powershell
python -c @"
import os, sys, asyncio, httpx
sys.path.insert(0, os.path.abspath('src'))
from kutomoto.server.app import app, execution_manager, get_driver
from tests.test_m4_it2_stress_harness import MockStressWin32Driver, _make_test_workflow

async def test():
    app.dependency_overrides[get_driver] = lambda: MockStressWin32Driver()
    payload = _make_test_workflow(countdown=0, pre_delay=200, post_delay=200, num_steps=1)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as c:
        st = (await c.post('/api/execute/start', json={'workflow': payload})).json()
        r_exec = await c.get(f'/api/execute/audit/{st[\"execution_id\"]}')
        await c.post('/api/execute/abort')
        assert r_exec.status_code == 404, f'Expected bug 404, got {r_exec.status_code}'
        print('DEFECT REPRODUCED: Querying active execution by execution_id returned 404!')
asyncio.run(test())
"@
```

### Invalidation Conditions
- Querying `/api/execute/audit/*` returns HTTP 404 Not Found (glob wildcards neutralized).
- Querying `/api/execute/audit/{execution_id}` during active execution returns HTTP 200 OK.
- Querying on-disk audit log by `execution_id` returns HTTP 200 OK.
