# Handoff Report: Milestone 4 Iteration 3 Empirical Stress Challenge

**Agent**: `m4_it3_challenger_1_gen2` (Empirical Challenger: critic, specialist)  
**Parent Agent**: `7675637a-9a1e-40c3-a3cd-063a24f49a5c`  
**Date**: 2026-11-05T08:18:00Z  
**Verdict**: **FAIL** (1 blocking route fallthrough defect preventing 100% test pass rate)

---

## 1. Observation

### 1.1 Empirical Verification of F-M4-01 and F-M4-02 (Pause/Resume during Pre-Delay and Post-Delay)
Tests were executed against `src/kutomoto/engine/runner.py` and `src/kutomoto/engine/fsm.py` using both existing and newly authored adversarial harnesses:
```powershell
python -m pytest tests/test_m4_empirical_challenge.py tests/test_m4_deep_stress_challenge.py -v
```
**Command Output**:
```
============================= 32 passed in 6.44s ==============================
```
Specific findings on F-M4-01 and F-M4-02:
- Multi-cycle pause and resume within a single step's `pre_delay_ms` (e.g., pause @ 20ms, resume @ 60ms, pause again @ 80ms, resume @ 120ms): **PASSED** (`tests/test_m4_deep_stress_challenge.py::test_multi_cycle_pause_resume_during_pre_delay`).
- Multi-cycle pause and resume within `post_delay_ms`: **PASSED** (`test_multi_cycle_pause_resume_during_post_delay`).
- Interleaved pre-delay and post-delay pauses across multiple steps: **PASSED** (`test_interleaved_pre_and_post_delay_pauses_across_multiple_steps`).
- Zero instances of `InvalidTransitionError` observed.
- In-step abort during pre-delay, post-delay, and `ActionType.DELAY`: **PASSED** (all halted in <100ms with state `STOPPED`).

### 1.2 Concurrency, Rapid Status Polling, WebSocket Telemetry, and Ghost State Stress
- **Single-flight execution lock**: 20 concurrent start requests resulted in exactly 1 success (200) and 19 conflicts (409) with RFC 7807 problem details and 90Studio attribution.
- **Start vs Abort contention**: 25 concurrent starts and 25 concurrent aborts fired simultaneously; zero 500 errors; FSM cleanly settled into `STOPPED` or `IDLE`.
- **Status & Audit polling storm**: 50 simultaneous status requests and 20 simultaneous audit requests during active multi-step execution returned 100% HTTP 200 OK without deadlocks.
- **WebSocket control & telemetry**: Bi-directional pause, resume, and abort sent over `/ws/execution` exhibited 100% parity with REST endpoints. Disconnect storms (dropping 7 of 10 clients mid-stream) caused zero server crashes.
- **Ghost running state prevention**: Force-cancelling `execution_manager._active_task` mid-run immediately yielded `execution_manager.is_active() == False`, allowing subsequent workflow starts without 409 lockout.

### 1.3 Full Repository Test Suite Failure: Route Fallthrough Bug on Encoded Slash `%2F`
When executing the full repository test suite:
```powershell
python -m pytest tests/
```
**Output**:
```
=========================== short test summary info ===========================
FAILED tests/test_m4_it3_adversarial_challenge.py::TestFM403AdversarialAttackVectors::test_advanced_fuzzing_and_unicode_homoglyphs
======================= 1 failed, 366 passed in 45.06s ========================
```
**Verbatim Failure Trace**:
```python
>           self._assert_secure_404_response(
                resp,
                f"Advanced/Unicode vector: {vec[:20]}...",
                query_contained_wf_id=False,
            )

tests\test_m4_it3_adversarial_challenge.py:506: 
...
self = <tests.test_m4_it3_adversarial_challenge.TestFM403AdversarialAttackVectors object>
resp = <Response [200 OK]>, vector_desc = 'Advanced/Unicode vector: C%3A%2F...'
query_contained_wf_id = False

    def _assert_secure_404_response(self, resp, vector_desc: str, query_contained_wf_id: bool = False):
        """Verify RFC 7807 problem details, 90Studio attribution, and zero confidential data leakage."""
>       assert resp.status_code == 404, (
            f"Vector '{vector_desc}' failed security check: expected HTTP 404, got {resp.status_code}."
        )
E       AssertionError: Vector 'Advanced/Unicode vector: C%3A%2F...' failed security check: expected HTTP 404, got 200.
E       assert 200 == 404
E        +  where 200 = <Response [200 OK]>.status_code
```

### 1.4 Direct Empirical Isolation of the Defect
Running an isolated probe request:
```powershell
python -c "import sys; sys.path.insert(0, 'src'); from fastapi.testclient import TestClient; from kutomoto.server.app import app; c = TestClient(app); r = c.get('/api/execute/audit/C%3A%2F'); print('STATUS:', r.status_code); print('BODY:', r.text[:150])"
```
**Output**:
```
STATUS: 200
BODY: <!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>kut
```
In `src/kutomoto/server/app.py`:
- Line 900: `@app_instance.get("/api/execute/audit/{workflow_id}")`
- Line 960: `app_instance.mount("/", StaticFiles(directory=str(UI_DIR), html=True), name="ui")`

When the client requests `/api/execute/audit/C%3A%2F`, the ASGI/Starlette layer decodes `%2F` to `/`, resulting in the path `/api/execute/audit/C:/`. Because `{workflow_id}` in Starlette does not match `/` path delimiters, the route does not match `get_execution_audit`. Instead of returning an RFC 7807 404 Problem Details response, the unhandled `/api/` path falls through to the root mount `StaticFiles(directory=..., html=True)`. Because `html=True` is enabled, Starlette serves `index.html` with HTTP 200 OK.

---

## 2. Logic Chain

1. **Premise 1**: Section 5.2 of the worker handoff states that the fix is invalidated if "Any test in tests/test_api.py or the test suite fails."
2. **Premise 2**: Running `pytest tests/` fails on `tests/test_m4_it3_adversarial_challenge.py::test_advanced_fuzzing_and_unicode_homoglyphs` (Observation 1.3).
3. **Premise 3**: The test vector `C%3A%2F` tests path traversal and drive letter handling in the `/api/execute/audit/{workflow_id}` endpoint.
4. **Premise 4**: In Starlette, path parameters without `:path` converters (`{workflow_id}`) terminate at `/`. Therefore, any URL containing an encoded slash `%2F` (such as `C%3A%2F`, `foo%2Fbar`, or nested traversals ending in `%2F`) splits the path into additional segments.
5. **Premise 5**: In `src/kutomoto/server/app.py:960`, `StaticFiles(..., html=True)` is mounted at `"/"` to serve the SPA. When Starlette fails to match an API route with a trailing slash or extra segments, it falls through to this mount. With `html=True`, StaticFiles catches directory-like paths and returns `index.html` with HTTP 200 OK (Observation 1.4).
6. **Premise 6**: Returning an HTML web page with HTTP 200 OK for an invalid API call under `/api/execute/audit/` violates the API contract, fails to return RFC 7807 Problem Details, and fails the security regression test.
7. **Conclusion**: While concurrency, pause/resume, pre/post delay transitions (F-M4-01 & F-M4-02), and single-flight execution locks are 100% verified and robust, the test suite contains an active failing test due to the route fallthrough bug in `src/kutomoto/server/app.py`. Under empirical challenger rules, the verdict must be **FAIL** until this route fallthrough is remediated.

---

## 3. Caveats

- **Scope of Failure**: The failure is strictly confined to route matching for path inputs containing encoded slashes (`%2F`) falling through to the SPA static file mount. Core workflow execution, the 7-state FSM, 10 atomic actions, pause/resume, in-step aborts, and WebSocket streaming all pass 100% of stress tests.
- **Review-Only Constraint**: As an Empirical Challenger, agent rules prohibit modifying implementation code in `src/kutomoto/server/app.py`. Remediation is documented below for implementation by a worker agent.
- **Hardware Automation**: Win32 SendInput testing used mock drivers as planned for Milestone 4; live OS form interaction is scheduled for Milestone 5.

---

## 4. Conclusion

### Verdict: **FAIL**

**Summary**:
- **F-M4-01 & F-M4-02**: **PASS (100% Fixed & Verified)**. No `InvalidTransitionError` can be provoked under single or multi-cycle pause/resume during pre_delay or post_delay.
- **Concurrency & Lifecycle Stress**: **PASS (100% Verified)**. Single-flight locks, status storms, abort idempotency, and WebSocket telemetry handled flawlessly across 32 challenge tests.
- **API Security / Route Matching**: **FAIL**. `GET /api/execute/audit/C%3A%2F` bypasses the API route handler and falls through to `StaticFiles(..., html=True)`, returning HTTP 200 HTML instead of HTTP 404 Problem Details.

### Recommended Remediation for Worker Agent:
In `src/kutomoto/server/app.py`:
Change the audit endpoint route definition at line 900 from:
```python
@app_instance.get("/api/execute/audit/{workflow_id}")
```
to:
```python
@app_instance.get("/api/execute/audit/{workflow_id:path}")
```
This ensures that any identifier containing forward slashes or encoded path traversal sequences (such as `C:/`, `../../win.ini`, or `foo/bar`) is captured by `get_execution_audit`, where `get_audit_summary` safely rejects it with a RFC 7807 404 Problem Details response rather than falling through to `StaticFiles`.

---

## 5. Verification Method

To independently reproduce the finding and verify the failure:

1. **Run the failing adversarial test**:
   ```powershell
   python -m pytest tests/test_m4_it3_adversarial_challenge.py -k "test_advanced_fuzzing_and_unicode_homoglyphs" -v
   ```
   **Observed Result**: Fails with `AssertionError: Vector 'Advanced/Unicode vector: C%3A%2F...' failed security check: expected HTTP 404, got 200.`

2. **Run the isolated probe script**:
   ```powershell
   python -c "import sys; sys.path.insert(0, 'src'); from fastapi.testclient import TestClient; from kutomoto.server.app import app; c = TestClient(app); r = c.get('/api/execute/audit/C%3A%2F'); print('Status:', r.status_code); print('Is HTML:', 'html' in r.headers.get('content-type', ''))"
   ```
   **Observed Result**: `Status: 200`, `Is HTML: True`.

3. **Verify Milestone 4 Concurrency & Lifecycle Challenge Suites**:
   ```powershell
   python -m pytest tests/test_m4_empirical_challenge.py tests/test_m4_deep_stress_challenge.py -v
   ```
   **Observed Result**: `32 passed in 6.44s` (100% pass rate).

4. **Invalidation Condition**:
   This FAIL verdict is invalidated when `GET /api/execute/audit/C%3A%2F` returns HTTP 404 with RFC 7807 Problem Details and all 367 tests across `pytest tests/` pass with zero failures.
