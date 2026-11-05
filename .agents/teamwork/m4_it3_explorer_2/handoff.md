# Investigation Report: Finding F-M4-04 (Asymmetric Identifier Handling in Active Execution Polling and On-Disk Fallback)

**Agent**: `m4_it3_explorer_2` (Identifier Resolution and Audit Trail Persistence Specialist)  
**Parent Agent**: `59700fc9-320d-4ed3-b1db-2fc709fed831`  
**Date**: 2026-11-05T05:10:00Z  
**Target File**: `src/kutomoto/server/app.py`  
**Related Components**: `src/kutomoto/engine/audit.py`, `tests/test_api.py`

---

## 1. Observation

### 1.1 Baseline System Status
The existing API test suite in `tests/test_api.py` passes 20 of 20 tests:
```powershell
python -m pytest tests/test_api.py -v
```
**Output**: `20 passed in 0.72s`.

However, the existing tests in `TestAuditLogEndpoint` (`tests/test_api.py:495-564`) only query completed or aborted workflows using `workflow_id` (`f"/api/execute/audit/{wf_id}"`). They never query an active execution using `execution_id`, nor do they query on-disk audit records using `execution_id` after memory cache clearing.

### 1.2 Inspection of `src/kutomoto/server/app.py` (Active Execution Polling Defect)
In `src/kutomoto/server/app.py`, lines 539-558:
```python
539:     def get_audit_summary(self, workflow_id: str) -> Optional[Dict[str, Any]]:
540:         """Retrieve audit log summary for a workflow ID or execution ID."""
541:         if workflow_id in self._audit_summaries:
542:             return self._audit_summaries[workflow_id]
543: 
544:         if (self._workflow_id == workflow_id or self._execution_id == workflow_id) and self._last_audit_summary:
545:             return self._last_audit_summary
546: 
547:         if self._workflow_id == workflow_id and self.is_active():
548:             return {
549:                 "workflow_id": self._workflow_id,
550:                 "execution_id": self._execution_id,
551:                 "workflow_name": self._workflow_name,
552:                 "status": self.get_state(),
553:                 "duration_seconds": round(time.perf_counter() - self._start_time, 2),
554:                 "total_steps": self._total_steps,
555:                 "current_step_index": self._current_step_index,
556:                 "timestamp_utc": datetime.now(timezone.utc).isoformat(),
557:                 "copyright": __copyright__,
558:             }
```
**Observations**:
1. At line 540, the docstring explicitly specifies: `"Retrieve audit log summary for a workflow ID or execution ID."`
2. At line 544, the method checks both identifiers: `(self._workflow_id == workflow_id or self._execution_id == workflow_id)`.
3. At lines 388-390, 414-416, and 516-518, upon completion, failure, or abort, the server populates `self._audit_summaries` under **both** identifiers:
   ```python
   self._audit_summaries[self._workflow_id] = summary
   self._audit_summaries[self._execution_id] = summary
   ```
4. In `POST /api/execute/start` (`src/kutomoto/server/app.py:346-353`), the server returns both identifiers:
   ```python
   return {
       "status": "started",
       "execution_id": self._execution_id,
       "workflow_id": self._workflow_id,
       ...
   }
   ```
5. **Defect**: At line 547, the condition is strictly:
   ```python
   if self._workflow_id == workflow_id and self.is_active():
   ```
   It checks **only** `self._workflow_id == workflow_id`, omitting `self._execution_id == workflow_id`.

**Empirical Reproduction Output**:
Running reproduction test (`repro_test.py`) against `POST /api/execute/start` followed by live polling:
```
Start resp: {'status': 'started', 'execution_id': '1c26c421-e932-4ac7-b255-a3e0acb444b0', 'workflow_id': 'wf-ce2bdb81-c1a8-46ec-bbe7-71d8d30498db', ...}
Active query wf_id status: 200
Active query wf_id response: {'workflow_id': 'wf-ce2bdb81...', 'execution_id': '1c26c421...', 'status': 'RUNNING', ...}
Active query exec_id status: 404
Active query exec_id response: {'type': 'https://90studio.com/errors/404', 'title': "Audit log summary for workflow '1c26c421-e932-4ac7-b255-a3e0acb444b0' not found.", 'status': 404, 'detail': "Audit log summary for workflow '1c26c421-e932-4ac7-b255-a3e0acb444b0' not found.", 'instance': '/api/execute/audit/1c26c421-e932-4ac7-b255-a3e0acb444b0', 'copyright': 'Copyrights reserved to 90Studio'}
```
When queried by `execution_id` while active, the client receives HTTP 404 Problem Details instead of the live execution state.

### 1.3 Inspection of `src/kutomoto/server/app.py` (On-Disk File Resolution Defect)
In `src/kutomoto/engine/audit.py`, line 271:
```python
filename = f"audit_{log.workflow_id}_{log.execution_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
```
All on-disk audit trail files adhere to the canonical template:
`audit_<workflow_id>_<execution_id>_<timestamp>.json`

In `src/kutomoto/server/app.py`, lines 560-565:
```python
560:         audit_dirs = [Path.home() / ".kutomoto" / "audit", BASE_DIR / "data" / "audit", BASE_DIR / "logs" / "audit"]
561:         for audit_dir in audit_dirs:
562:             if audit_dir.is_dir():
563:                 for p in audit_dir.glob(f"audit_{workflow_id}_*.json"):
564:                     try:
565:                         data = json.loads(p.read_text(encoding="utf-8"))
```
**Observations**:
1. At line 563, the fallback query uses `audit_dir.glob(f"audit_{workflow_id}_*.json")`.
2. This pattern strictly matches files with prefix `audit_<id>_...`.
3. If an audit file is saved as `audit_wf-disk-1_exec-disk-10_20261105_120000.json`, querying on disk with `workflow_id="wf-disk-1"` matches `audit_wf-disk-1_*.json`.
4. If a client or operator queries with `workflow_id="exec-disk-10"`, the glob evaluates to `audit_exec-disk-10_*.json`.
5. Because `exec-disk-10` is situated in the midfix position (`audit_<wf_id>_<exec_id>_<ts>.json`), `audit_exec-disk-10_*.json` will **never** match the file on disk.

**Empirical Reproduction Output**:
Running on-disk reproduction script (`repro_disk_test.py`) with memory caches cleared:
```
Disk query wf_id status: 200
Disk query exec_id status: 404
Disk query exec_id response: {'type': 'https://90studio.com/errors/404', 'title': "Audit log summary for workflow 'exec-disk-c048cd2c-a436-4a68-96c9-c94cfc5fb25e' not found.", 'status': 404, 'detail': "Audit log summary for workflow 'exec-disk-c048cd2c-a436-4a68-96c9-c94cfc5fb25e' not found.", 'instance': '/api/execute/audit/exec-disk-c048cd2c-a436-4a68-96c9-c94cfc5fb25e', 'copyright': 'Copyrights reserved to 90Studio'}
```
When memory cache is empty, querying by `execution_id` fails to match the on-disk file, producing HTTP 404 Problem Details.

### 1.4 Additional Hazard: Evaluation Order in `get_audit_summary`
In `src/kutomoto/server/app.py`:
- Line 544 evaluates `if (self._workflow_id == workflow_id or self._execution_id == workflow_id) and self._last_audit_summary:` **before** line 547 (`if ... and self.is_active():`).
- If workflow `wf-1` completes, `self._last_audit_summary` holds the completed summary of `exec-1`.
- When workflow `wf-1` is launched a second time, `self._execution_id` becomes `exec-2`, and the runner is active.
- Polling `exec-2` or `wf-1` triggers line 544 because `self._execution_id == "exec-2"` matches and `self._last_audit_summary` is still non-None.
- The method immediately returns the stale completed summary of `exec-1` instead of reporting the live active state of `exec-2`.

---

## 2. Logic Chain

1. **Client Contract**:
   - When a client issues `POST /api/execute/start`, the server initiates execution and returns `{"execution_id": "<uuid>", "workflow_id": "<id>", ...}`.
   - Frontends, automated agents, and external systems track the flight using `execution_id` to differentiate separate executions of the same workflow template.
   - The API contract specifies `GET /api/execute/audit/{workflow_id}` where the path parameter is documented to accept either `workflow_id` or `execution_id`.

2. **Active Execution Failure Chain**:
   - During execution, the task has not finished, so `self._audit_summaries` does not yet contain this run's summary.
   - At line 547, the guard evaluates `self._workflow_id == workflow_id and self.is_active()`.
   - If `workflow_id` is the `execution_id`, `self._workflow_id == workflow_id` is `False`.
   - The active state block is bypassed.
   - Because execution is still running, no file has been written to disk yet.
   - On-disk fallback search fails to find any matching records.
   - `get_audit_summary` returns `None`.
   - Endpoint `get_execution_audit` (`app.py:872-876`) converts `None` to `HTTPException(status_code=404, detail="Audit log summary for workflow '<id>' not found.")`.
   - Hence, polling by `execution_id` while active fails with 404.

3. **On-Disk File Resolution Failure Chain**:
   - `AuditLogger.write_to_disk` formats filenames as `audit_{workflow_id}_{execution_id}_{timestamp}.json`.
   - `app.py:563` glob pattern is `audit_{workflow_id}_*.json`.
   - This assumes the search identifier is always in the prefix position (position 1).
   - `execution_id` is always located in position 2 (midfix).
   - Therefore, `glob(f"audit_{execution_id}_*.json")` yields 0 matches on disk.
   - Post-restart or post-cache-eviction lookup by `execution_id` permanently fails with 404.

4. **Synergy with Finding F-M4-03**:
   - Constructing `glob(f"audit_{workflow_id}_*.json")` without input sanitization allows wildcards like `*` to match arbitrary files, leaking audit logs across tenants/workflows.
   - Sanitizing input via `safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "", workflow_id)` neutralizes glob injection while permitting valid alphanumeric IDs, underscores, and hyphens (standard UUID format).
   - If `safe_id` is empty, returning `None` immediately blocks wildcard injection attacks.

5. **Optimal Resolution Strategy**:
   - Move active execution check to the top of `get_audit_summary` and check `(self._workflow_id == workflow_id or self._execution_id == workflow_id) and self.is_active()`.
   - In on-disk fallback, sanitize `workflow_id` into `safe_id`.
   - Attempt prefix match (`audit_{safe_id}_*.json`) sorted newest first (`reverse=True`).
   - If no candidates, attempt midfix match (`audit_*_{safe_id}_*.json`) sorted newest first.
   - Verify file JSON data: `data.get("workflow_id") == safe_id or data.get("execution_id") == safe_id`.
   - Return structured summary dictionary.

---

## 3. Caveats

1. **Read-Only Investigation**: As an explorer agent, no modifications were made to `src/kutomoto/server/app.py` or other source files. All proposals are formatted as an exact line-level replacement and a ready-to-apply patch file (`.agents/teamwork/m4_it3_explorer_2/f_m4_04_remediation.patch`).
2. **In-Flight File Writes**: An active execution writes its audit log to disk only when it completes (`runner.execute()` completes or is aborted). Polling during execution relies on in-memory state; on-disk resolution applies to completed runs when in-memory cache is empty or restarted.
3. **No Database Layer**: kutomoto stores audit logs as JSON files on the local filesystem. Sorting candidate files by name descending (`reverse=True`) relies on the timestamp suffix `YYYYMMDD_HHMMSS` to ensure latest execution precedence.

---

## 4. Conclusion & Proposed Code Replacement

### 4.1 Assessment
Finding F-M4-04 is confirmed with 100% empirical reproducibility:
1. `app.py:547` fails to check `self._execution_id == workflow_id` during active execution.
2. `app.py:563` fails to match `execution_id` on disk due to rigid prefix globbing against `audit_{workflow_id}_{execution_id}_{timestamp}.json`.
3. Order of evaluation at lines 544-547 exposes active executions to stale `_last_audit_summary` leakage.

### 4.2 Exact Line-Level Code Replacement in `src/kutomoto/server/app.py`

**Target File**: `c:\Users\daoud\projects\kutomoto\src\kutomoto\server\app.py`  
**Target Lines**: 539–583

#### BEFORE:
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
                "duration_seconds": round(time.perf_counter() - self._start_time, 2),
                "total_steps": self._total_steps,
                "current_step_index": self._current_step_index,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "copyright": __copyright__,
            }

        audit_dirs = [Path.home() / ".kutomoto" / "audit", BASE_DIR / "data" / "audit", BASE_DIR / "logs" / "audit"]
        for audit_dir in audit_dirs:
            if audit_dir.is_dir():
                for p in audit_dir.glob(f"audit_{workflow_id}_*.json"):
                    try:
                        data = json.loads(p.read_text(encoding="utf-8"))
                        summary = data.get("execution_summary", {})
                        return {
                            "workflow_id": data.get("workflow_id", workflow_id),
                            "execution_id": data.get("execution_id", ""),
                            "workflow_name": data.get("workflow_name", ""),
                            "status": summary.get("final_status", "UNKNOWN"),
                            "duration_seconds": summary.get("duration_seconds", 0.0),
                            "total_steps": summary.get("total_steps", 0),
                            "successful_steps": summary.get("successful_steps", 0),
                            "failed_steps": summary.get("failed_steps", 0),
                            "retried_steps": summary.get("retried_steps", 0),
                            "timestamp_utc": data.get("timestamp_utc", ""),
                            "copyright": data.get("copyright", __copyright__),
                        }
                    except Exception:
                        pass
        return None
```

#### AFTER:
```python
    def get_audit_summary(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve audit log summary for a workflow ID or execution ID."""
        # 1. Live active execution: check both workflow_id and execution_id
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

        # 2. In-memory completed / aborted audit summaries
        if workflow_id in self._audit_summaries:
            return self._audit_summaries[workflow_id]

        if (self._workflow_id == workflow_id or self._execution_id == workflow_id) and self._last_audit_summary:
            return self._last_audit_summary

        # 3. On-disk fallback search by workflow_id or execution_id
        safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "", workflow_id)
        if not safe_id:
            return None

        audit_dirs = [Path.home() / ".kutomoto" / "audit", BASE_DIR / "data" / "audit", BASE_DIR / "logs" / "audit"]
        for audit_dir in audit_dirs:
            if audit_dir.is_dir():
                # Check matching prefix (workflow_id) sorted newest first
                candidates = sorted(audit_dir.glob(f"audit_{safe_id}_*.json"), reverse=True)
                # If not found by workflow_id prefix, check midfix (execution_id)
                if not candidates:
                    candidates = sorted(audit_dir.glob(f"audit_*_{safe_id}_*.json"), reverse=True)
                for p in candidates:
                    try:
                        data = json.loads(p.read_text(encoding="utf-8"))
                        if data.get("workflow_id") == safe_id or data.get("execution_id") == safe_id:
                            summary = data.get("execution_summary", {})
                            return {
                                "workflow_id": data.get("workflow_id", workflow_id),
                                "execution_id": data.get("execution_id", ""),
                                "workflow_name": data.get("workflow_name", ""),
                                "status": summary.get("final_status", "UNKNOWN"),
                                "duration_seconds": summary.get("duration_seconds", 0.0),
                                "total_steps": summary.get("total_steps", 0),
                                "successful_steps": summary.get("successful_steps", 0),
                                "failed_steps": summary.get("failed_steps", 0),
                                "retried_steps": summary.get("retried_steps", 0),
                                "timestamp_utc": data.get("timestamp_utc", ""),
                                "copyright": data.get("copyright", __copyright__),
                            }
                    except Exception:
                        pass
        return None
```

### 4.3 Artifacts Generated for Implementer
- Patch File: `.agents/teamwork/m4_it3_explorer_2/f_m4_04_remediation.patch`
- Unit Test Additions: `.agents/teamwork/m4_it3_explorer_2/proposed_test_additions.py`

---

## 5. Verification Method

To independently verify the defects before and the resolution after application:

### 5.1 Verification Script: Active Execution Polling (`repro_test.py`)
Run the test script:
```powershell
python .agents/teamwork/m4_it3_explorer_2/repro_test.py
```
- **Pre-Fix Result**:
  - `Active query wf_id status: 200`
  - `Active query exec_id status: 404` (Defect confirmed)
- **Post-Fix Invalidation Condition**:
  - Both queries return HTTP 200 with identical live status, `workflow_id`, and `execution_id`.

### 5.2 Verification Script: On-Disk Execution ID Lookup (`repro_disk_test.py`)
Run the test script:
```powershell
python .agents/teamwork/m4_it3_explorer_2/repro_disk_test.py
```
- **Pre-Fix Result**:
  - `Disk query wf_id status: 200`
  - `Disk query exec_id status: 404` (Defect confirmed)
- **Post-Fix Invalidation Condition**:
  - Both queries return HTTP 200 with `status: "SUCCESS"`, `workflow_id`, and `execution_id`.

### 5.3 Comprehensive 8-Scenario Test Suite (`test_comprehensive_fix.py`)
Run:
```powershell
python .agents/teamwork/m4_it3_explorer_2/test_comprehensive_fix.py
```
Validates:
1. Active execution queried by `workflow_id` -> 200 live summary.
2. Active execution queried by `execution_id` -> 200 live summary.
3. Completed execution in memory queried by both IDs -> 200 completed summary.
4. On-disk fallback queried by `workflow_id` -> 200 latest execution summary.
5. On-disk fallback queried by `execution_id` -> 200 specific execution summary.
6. Non-existent ID query -> None (HTTP 404).
7. Wildcard `*` injection -> None (HTTP 404, leaks nothing).
8. Pattern `*disk*` injection -> None (HTTP 404, leaks nothing).

### 5.4 Test Suite Regression Command
```powershell
python -m pytest tests/test_api.py -v
```
All existing 20 tests must continue passing 100%.
