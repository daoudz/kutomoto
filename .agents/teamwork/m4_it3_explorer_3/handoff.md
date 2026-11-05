# Handoff Report: Milestone 4 Iteration 3 — QA Regression Test Suite Formulation

**Agent**: `m4_it3_explorer_3` (QA, Regression Testing, and Security Verification)  
**Parent Agent**: `59700fc9-320d-4ed3-b1db-2fc709fed831`  
**Date**: 2026-11-05T08:12:00Z  
**Target Test File**: `c:\Users\daoud\projects\kutomoto\tests\test_api.py`  
**Target Implementation File**: `c:\Users\daoud\projects\kutomoto\src\kutomoto\server\app.py`  
**Status**: COMPLETE (Read-Only Investigation & Test Formulation)

---

## 1. Observation

Direct empirical investigation and code inspection of `tests/test_api.py` and `src/kutomoto/server/app.py` revealed the following observations:

### 1.1 Existing Test Suite Status in `tests/test_api.py`
Running baseline verification:
```powershell
python -m pytest tests/test_api.py -v
```
Output:
`20 passed in 0.73s` (100% pass rate).
In `TestAuditLogEndpoint` (lines 495–564), only three tests currently exist:
1. `test_get_audit_non_existent_workflow_returns_404` (tests missing random UUID)
2. `test_get_audit_completed_workflow_returns_200_with_watermark` (tests query by `workflow_id` after fast completion)
3. `test_get_audit_aborted_workflow_returns_200_with_aborted_status` (tests query by `workflow_id` after abort)

Neither of the empirical defects identified in M4 Iteration 2 (F-M4-03 and F-M4-04) are covered by the current test suite.

### 1.2 Observation on Finding F-M4-03: Glob Pattern Injection & Information Disclosure
In `src/kutomoto/server/app.py`, line 560–564:
```python
audit_dirs = [Path.home() / ".kutomoto" / "audit", BASE_DIR / "data" / "audit", BASE_DIR / "logs" / "audit"]
for audit_dir in audit_dirs:
    if audit_dir.is_dir():
        for p in audit_dir.glob(f"audit_{workflow_id}_*.json"):
```
When an on-disk audit log exists (e.g., `audit_sensitive_wf_exec99_20261105.json`), invoking:
- `client.get("/api/execute/audit/*")`
- `client.get("/api/execute/audit/*sensitive*")`
evaluates `audit_dir.glob("audit_*_*.json")` and `audit_dir.glob("audit_*sensitive*_*.json")`.

**Empirical Result Observed**:
```
r1 status: 200 {'workflow_id': 'sensitive_wf', 'execution_id': '', 'workflow_name': 'CONFIDENTIAL PAYROLL', 'status': 'SUCCESS', ... 'copyright': 'Copyrights reserved to 90Studio'}
r2 status: 200 {'workflow_id': 'sensitive_wf', 'execution_id': '', 'workflow_name': 'CONFIDENTIAL PAYROLL', 'status': 'SUCCESS', ... 'copyright': 'Copyrights reserved to 90Studio'}
```
The endpoint returns HTTP 200 OK and discloses confidential execution data belonging to other workflows.

### 1.3 Observation on Path Traversal and RFC 7807 Exception Handlers
When issuing a path traversal query:
```python
client.get("/api/execute/audit/..%2F..%2Fwin.ini")
```
**Empirical Result Observed**:
```
traversal: 404 {'detail': 'Not Found'}
```
In `src/kutomoto/server/app.py` lines 665–677, only `fastapi.exceptions.HTTPException` is handled:
```python
@app_instance.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
```
Because Starlette decodes `%2F` prior to route matching, traversal paths fail route matching, causing Starlette to raise `starlette.exceptions.HTTPException(status_code=404)`. In FastAPI, `starlette.exceptions.HTTPException` is not caught by `@app_instance.exception_handler(HTTPException)`, resulting in a raw `{"detail": "Not Found"}` response missing RFC 7807 fields and the mandatory 90Studio copyright attribution.

Handling `from starlette.exceptions import HTTPException as StarletteHTTPException` with `@app_instance.exception_handler(StarletteHTTPException)` produces:
```json
{
  "type": "https://90studio.com/errors/404",
  "title": "Not Found",
  "status": 404,
  "detail": "Not Found",
  "instance": "/api/execute/audit/../../win.ini",
  "copyright": "Copyrights reserved to 90Studio"
}
```

### 1.4 Observation on Finding F-M4-04: Asymmetric Identifier Handling in Active Polling & Disk Fallback
In `src/kutomoto/server/app.py`:
1. **Active Execution Polling (lines 547–558)**:
```python
if self._workflow_id == workflow_id and self.is_active():
    return {
        "workflow_id": self._workflow_id,
        "execution_id": self._execution_id,
        "workflow_name": self._workflow_name,
        "status": self.get_state(),
        ...
```
Line 547 tests ONLY `self._workflow_id == workflow_id`. It omits `self._execution_id == workflow_id`.
**Empirical Result Observed**:
When a client executes `POST /api/execute/start`, the API returns `{"execution_id": "<uuid>", "workflow_id": "<uuid>", ...}`.
Querying `/api/execute/audit/{execution_id}` while active returns HTTP 404 Not Found:
```json
{
  "type": "https://90studio.com/errors/404",
  "title": "Audit log summary for workflow '<exec_id>' not found.",
  "status": 404,
  "detail": "Audit log summary for workflow '<exec_id>' not found.",
  "instance": "/api/execute/audit/<exec_id>",
  "copyright": "Copyrights reserved to 90Studio"
}
```
2. **On-Disk File Lookup Fallback (lines 563–564)**:
In `src/kutomoto/engine/audit.py`, line 271, audit files are saved with the schema:
`audit_{workflow_id}_{execution_id}_{timestamp}.json`
In `app.py`, line 563:
`for p in audit_dir.glob(f"audit_{workflow_id}_*.json"):`
Because `workflow_id` is matched only as prefix, if in-memory cache is cleared and a caller queries by `execution_id`, the pattern does not match the file, returning HTTP 404.

---

## 2. Logic Chain

1. **Vulnerability F-M4-03 Chain**:
   - `get_audit_summary` accepts any string from the path parameter `{workflow_id}`.
   - It directly interpolates that string into `audit_dir.glob(f"audit_{workflow_id}_*.json")`.
   - In Python `pathlib.Path.glob`, `*`, `?`, and `[` are interpreted as pattern wildcards.
   - Any query containing wildcards matches unrelated audit files on disk and exposes them to unauthenticated callers.
   - Furthermore, path traversal sequences (`..%2F..%2Fwin.ini`) must be intercepted and rejected with HTTP 404 Problem Details stamped with `copyright: "Copyrights reserved to 90Studio"`.
   - **Test Design**: The regression test must persist a mock confidential audit file to disk, clear in-memory caches, execute queries for `"*"`, `"*sensitive*"`, and `"..%2F..%2Fwin.ini"`, and verify that all three return HTTP 404 Problem Details with 90Studio attribution and zero leakage of the confidential file.

2. **Defect F-M4-04 Chain**:
   - Callers initiating workflows via `POST /api/execute/start` receive both `execution_id` and `workflow_id`.
   - While a workflow is active, the caller queries `/api/execute/audit/{execution_id}` to track execution progress.
   - Line 547 checks only `self._workflow_id == workflow_id`, causing active queries by `execution_id` to fail with HTTP 404.
   - When execution finishes or when in-memory cache is cleared (simulating server restarts or worker recycling), callers querying on-disk records by `execution_id` fail because the glob searches only the prefix `audit_{id}_*.json` rather than matching `execution_id` (either as midfix `audit_*_{id}_*.json` or verified within the JSON payload).
   - **Test Design**: The regression test must:
     a) Start a workflow with a non-zero delay (`pre_delay_ms=1000`) so the runner is active.  
     b) Poll `/api/execute/audit/{execution_id}` while active, asserting HTTP 200 OK with `status: "RUNNING"` and `copyright: "Copyrights reserved to 90Studio"`.  
     c) Cleanly abort execution via `POST /api/execute/abort`.  
     d) Place an on-disk audit log formatted as `audit_{wf_id}_{exec_id}_{timestamp}.json`.  
     e) Clear in-memory caches (`_audit_summaries.clear()`, `_last_audit_summary = None`).  
     f) Query `/api/execute/audit/{execution_id}` against on-disk fallback, asserting HTTP 200 OK with matching identifiers and 90Studio attribution.  
     g) Clean up the on-disk file in a `try...finally` block.

---

## 3. Caveats

1. **Read-Only Investigation**: As an explorer agent, no changes have been committed directly to `tests/test_api.py` or `src/kutomoto/server/app.py`. The exact, copy-paste ready code proposals are specified in Section 4 for Worker 1 to implement.
2. **Lifespan Context Requirement**: When using `TestClient(app)`, background `asyncio` execution tasks are bound to the client lifespan. Tests starting background executions must execute within the `with client:` or standard `client` fixture context, and MUST abort any dangling executions cleanly in a `finally` block to prevent background task leaks across test cases.
3. **Exception Handler Prerequisite**: For `..%2F..%2Fwin.ini` to return RFC 7807 Problem Details with 90Studio attribution, `src/kutomoto/server/app.py` must register an exception handler for `StarletteHTTPException` (from `starlette.exceptions`).

---

## 4. Conclusion & Concrete Code Additions

### 4.1 Proposed Additions to `tests/test_api.py`

#### Part A: Import Updates (Top of `tests/test_api.py`)
Add `import json` and import `BASE_DIR, execution_manager` from `kutomoto.server.app`:

```python
# In tests/test_api.py, lines 7-23:
import copy
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

import pytest

SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from fastapi.testclient import TestClient  # noqa: E402

from kutomoto import __version__  # noqa: E402
from kutomoto.server.app import BASE_DIR, app, execution_manager, get_driver  # noqa: E402
```

#### Part B: Regression Test Methods (Appended to `TestAuditLogEndpoint` in `tests/test_api.py`)
Add the two regression test methods directly after `test_get_audit_aborted_workflow_returns_200_with_aborted_status` (line 564):

```python
    def test_get_audit_wildcard_and_path_traversal_sanitization_rejects_404(self, client):
        """
        Regression test for Finding F-M4-03 (Glob Pattern Injection & Information Disclosure).
        Ensures wildcard patterns (*, *sensitive*) and path traversal attempts (..%2F..%2Fwin.ini)
        are neutralized, returning HTTP 404 Problem Details with 90Studio copyright attribution
        and strictly preventing disclosure of stored on-disk audit records.
        """
        audit_dir = BASE_DIR / "data" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        confidential_wf_name = "TOP_SECRET_BANKING_WIRE_COMPLIANCE_90STUDIO"
        confidential_wf_id = f"sensitive_payroll_{uuid.uuid4().hex[:8]}"
        confidential_file = audit_dir / f"audit_{confidential_wf_id}_exec99_20261105.json"

        confidential_file.write_text(
            json.dumps({
                "workflow_id": confidential_wf_id,
                "execution_id": "exec-confidential-99",
                "workflow_name": confidential_wf_name,
                "timestamp_utc": "2026-11-05T00:00:00Z",
                "copyright": "Copyrights reserved to 90Studio",
                "execution_summary": {
                    "total_steps": 3,
                    "successful_steps": 3,
                    "failed_steps": 0,
                    "retried_steps": 0,
                    "duration_seconds": 1.5,
                    "final_status": "SUCCESS",
                },
            }),
            encoding="utf-8",
        )

        try:
            # Clear in-memory caches to guarantee disk query resolution is evaluated
            execution_manager._audit_summaries.clear()
            execution_manager._last_audit_summary = None

            adversarial_queries = [
                "*",
                "*sensitive*",
                "..%2F..%2Fwin.ini",
            ]

            for query in adversarial_queries:
                resp = client.get(f"/api/execute/audit/{query}")
                assert resp.status_code == 404, f"Query '{query}' expected HTTP 404, got {resp.status_code}: {resp.text}"
                data = resp.json()

                # Verify RFC 7807 Problem Details and 90Studio attribution
                assert data.get("copyright") == "Copyrights reserved to 90Studio"
                assert data.get("status") == 404
                assert "404" in str(data.get("type", ""))

                # Verify strict non-disclosure of confidential execution history
                assert confidential_wf_name not in resp.text
                assert confidential_wf_id not in resp.text
                assert "exec-confidential-99" not in resp.text
        finally:
            if confidential_file.exists():
                confidential_file.unlink()

    def test_get_audit_active_execution_and_disk_fallback_by_execution_id(self, client, valid_workflow_payload):
        """
        Regression test for Finding F-M4-04 (Asymmetric Identifier Handling in Active Polling & Disk Fallback).
        1. Launches a workflow with non-zero step delay.
        2. Queries /api/execute/audit/{execution_id} while active: asserts HTTP 200 OK, status 'RUNNING',
           and 90Studio attribution watermark.
        3. Cleans up execution via emergency abort.
        4. Writes an on-disk audit log with pattern audit_{wf_id}_{exec_id}_{timestamp}.json.
        5. Clears in-memory caches to force disk lookup fallback.
        6. Queries /api/execute/audit/{execution_id}: asserts HTTP 200 OK matching execution_id, workflow_id,
           and 90Studio attribution watermark.
        """
        active_payload = copy.deepcopy(valid_workflow_payload)
        active_payload["execution_settings"]["countdown_seconds"] = 0
        for s in active_payload["steps"]:
            s["pre_delay_ms"] = 1000
            s["post_delay_ms"] = 1000

        # 1. Start execution
        start_resp = client.post("/api/execute/start", json={"workflow": active_payload})
        assert start_resp.status_code in (200, 202)
        start_data = start_resp.json()
        exec_id = start_data["execution_id"]
        wf_id = active_payload["id"]

        audit_dir = BASE_DIR / "data" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        disk_file = audit_dir / f"audit_{wf_id}_{exec_id}_20261105_120000.json"

        try:
            # Wait briefly for runner to enter active RUNNING state
            for _ in range(20):
                st = client.get("/api/execute/status").json()
                if st.get("state") == "RUNNING":
                    break
                time.sleep(0.02)

            # 2. Query while actively running using execution_id
            active_resp = client.get(f"/api/execute/audit/{exec_id}")
            assert active_resp.status_code == 200, f"Active query by execution_id failed: {active_resp.text}"
            active_data = active_resp.json()
            assert active_data["execution_id"] == exec_id
            assert active_data["workflow_id"] == wf_id
            assert active_data["status"] == "RUNNING"
            assert active_data.get("copyright") == "Copyrights reserved to 90Studio"

            # 3. Cleanly abort execution
            abort_resp = client.post("/api/execute/abort")
            assert abort_resp.status_code == 200

            # 4. Create on-disk audit record matching engine format
            disk_content = {
                "workflow_id": wf_id,
                "execution_id": exec_id,
                "workflow_name": active_payload["name"],
                "timestamp_utc": "2026-11-05T12:00:00Z",
                "copyright": "Copyrights reserved to 90Studio",
                "execution_summary": {
                    "total_steps": len(active_payload["steps"]),
                    "successful_steps": 0,
                    "failed_steps": 0,
                    "retried_steps": 0,
                    "duration_seconds": 0.25,
                    "final_status": "ABORTED",
                },
            }
            disk_file.write_text(json.dumps(disk_content), encoding="utf-8")

            # 5. Clear in-memory caches to force disk fallback
            execution_manager._audit_summaries.clear()
            execution_manager._last_audit_summary = None

            # 6. Query by execution_id on disk fallback
            disk_resp = client.get(f"/api/execute/audit/{exec_id}")
            assert disk_resp.status_code == 200, f"Disk fallback by execution_id failed: {disk_resp.text}"
            disk_data = disk_resp.json()
            assert disk_data["execution_id"] == exec_id
            assert disk_data["workflow_id"] == wf_id
            assert disk_data["status"] == "ABORTED"
            assert disk_data.get("copyright") == "Copyrights reserved to 90Studio"

        finally:
            if disk_file.exists():
                disk_file.unlink()
            if execution_manager.is_active():
                client.post("/api/execute/abort")
```

---

### 4.2 Required Companion Implementation in `src/kutomoto/server/app.py`

To enable the above regression tests to pass, Worker 1 should make the following changes in `src/kutomoto/server/app.py`:

1. **Catch StarletteHTTPException** (lines 22 & 665):
   ```python
   from starlette.exceptions import HTTPException as StarletteHTTPException
   ```
   In `create_app()`:
   ```python
   @app_instance.exception_handler(StarletteHTTPException)
   async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
       return JSONResponse(
           status_code=exc.status_code,
           content={
               "type": f"https://90studio.com/errors/{exc.status_code}",
               "title": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
               "status": exc.status_code,
               "detail": exc.detail,
               "instance": str(request.url.path),
               "copyright": __copyright__,
           },
       )
   ```

2. **Patch `get_audit_summary` in `ServerExecutionManager`** (lines 539–583):
   ```python
   def get_audit_summary(self, workflow_id: str) -> Optional[Dict[str, Any]]:
       """Retrieve audit log summary for a workflow ID or execution ID."""
       if not workflow_id or not isinstance(workflow_id, str):
           return None

       # Check in-memory completed cache
       if workflow_id in self._audit_summaries:
           return self._audit_summaries[workflow_id]

       if (self._workflow_id == workflow_id or self._execution_id == workflow_id) and self._last_audit_summary:
           return self._last_audit_summary

       # Check active execution (both workflow_id and execution_id)
       if (self._workflow_id == workflow_id or self._execution_id == workflow_id) and self.is_active():
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

       # Neutralize wildcard metacharacters and directory traversal
       if any(c in workflow_id for c in ("*", "?", "[", "]", "/", "\\")):
           return None
       safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "", workflow_id)
       if not safe_id or safe_id != workflow_id:
           return None

       # On-disk fallback search by workflow_id (prefix) or execution_id (midfix)
       audit_dirs = [Path.home() / ".kutomoto" / "audit", BASE_DIR / "data" / "audit", BASE_DIR / "logs" / "audit"]
       for audit_dir in audit_dirs:
           if audit_dir.is_dir():
               candidates = list(audit_dir.glob(f"audit_{safe_id}_*.json"))
               if not candidates:
                   candidates = list(audit_dir.glob(f"audit_*_{safe_id}_*.json"))

               for p in candidates:
                   try:
                       data = json.loads(p.read_text(encoding="utf-8"))
                       if data.get("workflow_id") != safe_id and data.get("execution_id") != safe_id:
                           continue
                       summary = data.get("execution_summary", {})
                       return {
                           "workflow_id": data.get("workflow_id", safe_id),
                           "execution_id": data.get("execution_id", ""),
                           "workflow_name": data.get("workflow_name", ""),
                           "status": summary.get("final_status", "UNKNOWN"),
                           "duration_seconds": summary.get("duration_seconds", 0.0),
                           "total_steps": summary.get("total_steps", 0),
                           "successful_steps": summary.get("successful_steps", 0),
                           "failed_steps": summary.get("failed_steps", 0),
                           "retried_steps": summary.get("retried_steps", 0),
                           "timestamp_utc": data.get("timestamp_utc", ""),
                           "copyright": data.get("copyright", __copyright__,
                       }
                   except Exception:
                       pass
       return None
   ```

---

## 5. Verification Method

To independently verify this formulation:

### 5.1 Project Test Command
Once Worker 1 applies the proposed code changes:
```powershell
python -m pytest tests/test_api.py -v
```
**Expected Outcome**: `22 passed` (20 baseline tests + 2 new regression tests).

### 5.2 Specific Regression Target Execution
```powershell
python -m pytest tests/test_api.py -k "wildcard or disk_fallback" -v
```
**Expected Outcome**:
- `test_get_audit_wildcard_and_path_traversal_sanitization_rejects_404 PASSED`
- `test_get_audit_active_execution_and_disk_fallback_by_execution_id PASSED`

### 5.3 Invalidation Conditions
The verification is invalidated if:
1. Querying `/api/execute/audit/*` returns HTTP 200 or discloses any stored audit JSON filename or content.
2. Querying `/api/execute/audit/..%2F..%2Fwin.ini` returns a response without `"copyright": "Copyrights reserved to 90Studio"`.
3. Querying `/api/execute/audit/{execution_id}` while active returns HTTP 404 instead of HTTP 200 with `status: "RUNNING"`.
4. Querying `/api/execute/audit/{execution_id}` from on-disk fallback returns HTTP 404 instead of HTTP 200 with the completed/aborted audit record.
