# Milestone 4 Iteration 2 Test Plan & QA Remediation Report

**Agent**: `m4_fix_explorer_3` (Testing, Quality Assurance & Regression Protection)  
**Target Files Analyzed**:
- `tests/test_api.py`
- `tests/test_m4_empirical_challenge.py`
- `tests/test_ui_m4_challenge.py`
- `src/kutomoto/server/app.py`
- `src/kutomoto/engine/runner.py`
- `src/kutomoto/engine/audit.py`
- `src/kutomoto/engine/safety.py`
- `src/kutomoto/ui/index.html`  
**Parent Agent**: `59700fc9-320d-4ed3-b1db-2fc709fed831`  
**Integrity Mode**: Development (Strict 90Studio Attribution & Zero Bare Pass Policy)  
**Date**: 2026-11-05T07:40:00Z  

---

## 1. Observation

### 1.1 Direct File Observations

#### 1.1.1 Bare Passes in `tests/test_api.py`
In `tests/test_api.py`, class `MockWin32Driver` (lines 129–152):
```python
129:     def clear_field(self, strategy: str = "select_all_backspace") -> None:
130:         pass
131: 
132:     def send_scroll(self, delta_x: int, delta_y: int) -> None:
133:         pass
...
141:     def send_key_down(self, vk_name: Any) -> None:
142:         pass
143: 
144:     def send_key_up(self, vk_name: Any) -> None:
145:         pass
146: 
147:     def send_mouse_down(self, button: str = "left") -> None:
148:         pass
149: 
150:     def send_mouse_up(self, button: str = "left") -> None:
151:         pass
```
Lines 130, 133, 142, 145, 148, and 151 contain bare `pass` statements rather than recording simulator state.

#### 1.1.2 Bare Passes in `tests/test_m4_empirical_challenge.py`
In `tests/test_m4_empirical_challenge.py`, class `MockWin32Driver` (lines 119–142):
```python
119:     def clear_field(self, strategy: str = "select_all_backspace") -> None:
120:         pass
121: 
122:     def send_scroll(self, delta_x: int, delta_y: int) -> None:
123:         pass
...
131:     def send_key_down(self, vk_name: Any) -> None:
132:         pass
133: 
134:     def send_key_up(self, vk_name: Any) -> None:
135:         pass
136: 
137:     def send_mouse_down(self, button: str = "left") -> None:
138:         pass
139: 
140:     def send_mouse_up(self, button: str = "left") -> None:
141:         pass
```
Lines 120, 123, 132, 135, 138, and 141 in `tests/test_m4_empirical_challenge.py` duplicate the exact 6 bare `pass` methods.

#### 1.1.3 Missing Title Attribution Assertion in `tests/test_api.py`
In `tests/test_api.py`, lines 311–317:
```python
311:     def test_root_endpoint_serves_spa_html(self, client):
312:         resp = client.get("/")
313:         assert resp.status_code == 200
314:         assert "text/html" in resp.headers.get("content-type", "")
315:         assert "kutomoto" in resp.text
316:         assert "90Studio" in resp.text
```
The test verifies `"90Studio"` generally within the HTML body, but lacks an explicit assertion verifying `<title>` contains `"Copyrights reserved to 90Studio"`.

#### 1.1.4 Cross-Suite Title Regression Risk in `tests/test_ui_m4_challenge.py`
In `tests/test_ui_m4_challenge.py`, line 96:
```python
96:         assert "<title>kutomoto — Enterprise Form Automation</title>" in content, "Invalid page title"
```
When `src/kutomoto/ui/index.html` line 6 is updated from:
`<title>kutomoto — Enterprise Form Automation</title>`
to:
`<title>kutomoto — Enterprise Form Automation — Copyrights reserved to 90Studio</title>`
`test_ui_m4_challenge.py` line 96 will fail unless updated concurrently.

#### 1.1.5 Missing Endpoint `GET /api/execute/audit/{workflow_id}`
Inspection of `src/kutomoto/server/app.py`:
Currently, routes exist for `/api/health`, `/api/workflows`, `/api/designer/compile`, `/api/windows`, `/api/execute/start`, `/api/execute/pause`, `/api/execute/resume`, `/api/execute/abort`, and `/api/execute/status`.
`GET /api/execute/audit/{workflow_id}` does not exist in `src/kutomoto/server/app.py`, nor do tests exist for it in `tests/test_api.py`.

#### 1.1.6 `xfail` Tests in `tests/test_m4_empirical_challenge.py`
Lines 596 and 652:
```python
596:     @pytest.mark.xfail(strict=True, reason="Confirmed Vulnerability F-M4-01: Post-delay pause crashes FSM with InvalidTransitionError and locks server into Ghost Running state")
597:     async def test_vulnerability_post_delay_pause_causes_invalid_fsm_transition(self):
...
652:     @pytest.mark.xfail(strict=True, reason="Confirmed Vulnerability F-M4-02: Pre-delay pause crashes FSM with InvalidTransitionError (PAUSED -> STEP_SUCCESS)")
653:     async def test_vulnerability_pre_delay_pause_causes_invalid_fsm_transition(self):
```
Both tests are currently marked `@pytest.mark.xfail(strict=True, ...)` because the underlying runner engine did not check `pause_event` during `pre_delay` and `post_delay`, leading to `InvalidTransitionError`.

---

## 2. Logic Chain

1. **Bare Passes Elimination**:
   - The project integrity policy forbids bare `pass` statements in concrete class methods.
   - `MockWin32Driver` in `tests/test_api.py` and `tests/test_m4_empirical_challenge.py` can record interactions into instance lists (`cleared_fields`, `scrolls`, `down_keys`, `up_keys`, `mouse_down_events`, `mouse_up_events`).
   - This preserves existing test contracts, requires no changes to tests calling `MockWin32Driver`, and eliminates all 6 bare passes.

2. **Root Endpoint HTML `<title>` Assertion**:
   - The UI HTML title in `src/kutomoto/ui/index.html` line 6 is being updated to:
     `<title>kutomoto — Enterprise Form Automation — Copyrights reserved to 90Studio</title>`.
   - `tests/test_api.py::test_root_endpoint_serves_spa_html` must assert this exact title string to prevent future regressions.
   - Concurrently, `tests/test_ui_m4_challenge.py` line 96 must be synchronized to expect the same title string, preserving full green pass across the UI challenge suite.

3. **`GET /api/execute/audit/{workflow_id}` Specification & Test Coverage**:
   - `AuditLogger` in `src/kutomoto/engine/audit.py` generates `KutomotoAuditLog` stamped with `"copyright": "Copyrights reserved to 90Studio"`.
   - `ServerExecutionManager` in `src/kutomoto/server/app.py` should record audit records indexed by `workflow_id` and `execution_id` upon step completion, error, or abort.
   - The route `GET /api/execute/audit/{workflow_id}` must:
     - Return `404 Not Found` with problem details when the workflow has never executed.
     - Return `200 OK` with structured audit log and 90Studio copyright watermark when completed.
     - Return `200 OK` with `status: "ABORTED"` and 90Studio watermark when aborted.
   - A dedicated test class `TestAuditLogEndpoint` in `tests/test_api.py` must thoroughly exercise all 3 scenarios.

4. **Converting `xfail` into Active Regression Tests**:
   - When the worker applies fixes in `src/kutomoto/engine/runner.py` (checking `ctx.pause_event` during `pre_delay`, `post_delay`, and before `ALL_STEPS_DONE`), the runner stays paused and does NOT trigger transitions while paused.
   - In `test_vulnerability_post_delay_pause_causes_invalid_fsm_transition`: mid-post_delay pause will halt the delay countdown, resume will complete the delay, and `ALL_STEPS_DONE` will transition cleanly to `COMPLETED`. The server will NOT enter Ghost Running lockout, allowing new executions.
   - In `test_vulnerability_pre_delay_pause_causes_invalid_fsm_transition`: mid-pre_delay pause will halt execution without firing `STEP_SUCCESS` from `PAUSED`. The background task remains alive and paused until resumed.
   - Removing `@pytest.mark.xfail(strict=True)` and adding assertions for full pause/resume completion converts both probes into active regression shields.

---

## 3. Caveats

- Tests continue using `MockWin32Driver` for headless CI/CD execution without requiring an interactive Windows desktop session (end-to-end live OS desktop automation is scheduled for Milestone 5).
- Audit logs in `ServerExecutionManager` are held in in-memory storage per server session; persistence to disk is handled by `AuditLogger` file logs in `logs/audit/`.

---

## 4. Conclusion & Exact Test Code Proposals

### 4.1 Changes to `tests/test_api.py`

#### 4.1.1 Add `time` to imports
In `tests/test_api.py` line 12:
```python
# BEFORE (lines 10-14):
from typing import Any, Dict, List, Optional, Tuple
import uuid

import pytest

# AFTER:
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

import pytest
```

#### 4.1.2 Replace bare passes in `MockWin32Driver`
In `tests/test_api.py`, update `MockWin32Driver.__init__` and replace lines 129–152:
```python
# BEFORE (lines 32-40):
    def __init__(self):
        self.dpi_set = False
        self.cursor_pos = (500, 400)
        self.foreground_hwnd = 1001
        self.clicks: List[Tuple[int, int, str, int]] = []
        self.typed_text: List[str] = []
        self.pressed_keys: List[Tuple[str, int]] = []
        self.modifiers_released = False

# AFTER:
    def __init__(self):
        self.dpi_set = False
        self.cursor_pos = (500, 400)
        self.foreground_hwnd = 1001
        self.clicks: List[Tuple[int, int, str, int]] = []
        self.typed_text: List[str] = []
        self.pressed_keys: List[Tuple[str, int]] = []
        self.modifiers_released = False
        self.cleared_fields: List[str] = []
        self.scrolls: List[Tuple[int, int]] = []
        self.down_keys: List[Any] = []
        self.up_keys: List[Any] = []
        self.mouse_down_events: List[str] = []
        self.mouse_up_events: List[str] = []
```

```python
# BEFORE (lines 129-152):
    def clear_field(self, strategy: str = "select_all_backspace") -> None:
        pass

    def send_scroll(self, delta_x: int, delta_y: int) -> None:
        pass

    def release_all_modifiers(self) -> None:
        self.modifiers_released = True

    def is_key_pressed(self, vk_code_or_name: Any) -> bool:
        return False

    def send_key_down(self, vk_name: Any) -> None:
        pass

    def send_key_up(self, vk_name: Any) -> None:
        pass

    def send_mouse_down(self, button: str = "left") -> None:
        pass

    def send_mouse_up(self, button: str = "left") -> None:
        pass

# AFTER:
    def clear_field(self, strategy: str = "select_all_backspace") -> None:
        self.cleared_fields.append(strategy)

    def send_scroll(self, delta_x: int, delta_y: int) -> None:
        self.scrolls.append((delta_x, delta_y))

    def release_all_modifiers(self) -> None:
        self.modifiers_released = True

    def is_key_pressed(self, vk_code_or_name: Any) -> bool:
        return False

    def send_key_down(self, vk_name: Any) -> None:
        self.down_keys.append(vk_name)

    def send_key_up(self, vk_name: Any) -> None:
        self.up_keys.append(vk_name)

    def send_mouse_down(self, button: str = "left") -> None:
        self.mouse_down_events.append(button)

    def send_mouse_up(self, button: str = "left") -> None:
        self.mouse_up_events.append(button)
```

#### 4.1.3 Update `test_root_endpoint_serves_spa_html`
In `tests/test_api.py`, lines 311–317:
```python
# BEFORE:
    def test_root_endpoint_serves_spa_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        assert "kutomoto" in resp.text
        assert "90Studio" in resp.text

# AFTER:
    def test_root_endpoint_serves_spa_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        assert "kutomoto" in resp.text
        assert "90Studio" in resp.text
        assert "<title>kutomoto — Enterprise Form Automation — Copyrights reserved to 90Studio</title>" in resp.text
```

#### 4.1.4 Append `TestAuditLogEndpoint`
Add to the end of `tests/test_api.py`:
```python
# ==============================================================================
# 8. AUDIT LOG ENDPOINT TEST SUITE
# ==============================================================================

class TestAuditLogEndpoint:
    """Verifies GET /api/execute/audit/{workflow_id} compliance and 90Studio audit trails."""

    def test_get_audit_non_existent_workflow_returns_404(self, client):
        """Verify 404 Not Found when workflow has not been executed or does not exist."""
        non_existent_id = str(uuid.uuid4())
        resp = client.get(f"/api/execute/audit/{non_existent_id}")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        assert f"'{non_existent_id}'" in data["detail"] or non_existent_id in data["detail"]
        assert data.get("copyright") == "Copyrights reserved to 90Studio"

    def test_get_audit_completed_workflow_returns_200_with_watermark(self, client, valid_workflow_payload):
        """Verify 200 OK returning structured audit log with 90Studio watermark upon completion."""
        wf_id = valid_workflow_payload["id"]
        # Fast execution with 0 delay
        fast_payload = copy.deepcopy(valid_workflow_payload)
        for s in fast_payload["steps"]:
            s["pre_delay_ms"] = 0
            s["post_delay_ms"] = 0

        # Start execution
        start_resp = client.post("/api/execute/start", json={"workflow": fast_payload})
        assert start_resp.status_code in (200, 202)
        exec_id = start_resp.json()["execution_id"]

        # Wait briefly for execution completion
        for _ in range(30):
            st = client.get("/api/execute/status").json()
            if st["state"] in ("IDLE", "COMPLETED", "SUCCESS"):
                break
            time.sleep(0.05)

        # Query audit endpoint
        audit_resp = client.get(f"/api/execute/audit/{wf_id}")
        assert audit_resp.status_code == 200
        audit = audit_resp.json()

        assert audit["workflow_id"] == wf_id
        assert audit["execution_id"] == exec_id
        assert audit["copyright"] == "Copyrights reserved to 90Studio"
        assert audit["status"] in ("SUCCESS", "COMPLETED")
        assert audit["total_steps"] == len(fast_payload["steps"])
        assert "duration_seconds" in audit

    def test_get_audit_aborted_workflow_returns_200_with_aborted_status(self, client, valid_workflow_payload):
        """Verify 200 OK returning ABORTED audit record with 90Studio watermark when aborted."""
        wf_id = valid_workflow_payload["id"]
        long_payload = copy.deepcopy(valid_workflow_payload)
        for s in long_payload["steps"]:
            s["pre_delay_ms"] = 500

        # Start execution
        start_resp = client.post("/api/execute/start", json={"workflow": long_payload})
        assert start_resp.status_code in (200, 202)

        # Abort execution immediately
        abort_resp = client.post("/api/execute/abort")
        assert abort_resp.status_code == 200

        # Query audit endpoint
        audit_resp = client.get(f"/api/execute/audit/{wf_id}")
        assert audit_resp.status_code == 200
        audit = audit_resp.json()

        assert audit["workflow_id"] == wf_id
        assert audit["copyright"] == "Copyrights reserved to 90Studio"
        assert audit["status"] in ("ABORTED", "STOPPED")
```

---

### 4.2 Changes to `tests/test_m4_empirical_challenge.py`

#### 4.2.1 Replace bare passes in `MockWin32Driver`
In `tests/test_m4_empirical_challenge.py`, lines 41–48 and 119–142:
Update `MockWin32Driver.__init__`:
```python
        self.cleared_fields: List[str] = []
        self.scrolls: List[Tuple[int, int]] = []
        self.down_keys: List[Any] = []
        self.up_keys: List[Any] = []
        self.mouse_down_events: List[str] = []
        self.mouse_up_events: List[str] = []
```
And replace lines 119–142:
```python
    def clear_field(self, strategy: str = "select_all_backspace") -> None:
        self.cleared_fields.append(strategy)

    def send_scroll(self, delta_x: int, delta_y: int) -> None:
        self.scrolls.append((delta_x, delta_y))

    def release_all_modifiers(self) -> None:
        self.modifiers_released = True

    def is_key_pressed(self, vk_code_or_name: Any) -> bool:
        return False

    def send_key_down(self, vk_name: Any) -> None:
        self.down_keys.append(vk_name)

    def send_key_up(self, vk_name: Any) -> None:
        self.up_keys.append(vk_name)

    def send_mouse_down(self, button: str = "left") -> None:
        self.mouse_down_events.append(button)

    def send_mouse_up(self, button: str = "left") -> None:
        self.mouse_up_events.append(button)
```

#### 4.2.2 Update Post-Delay and Pre-Delay Pause Regression Tests (Removing `xfail`)
In `tests/test_m4_empirical_challenge.py`, replace lines 595–687 with:
```python
    @pytest.mark.asyncio
    async def test_vulnerability_post_delay_pause_causes_invalid_fsm_transition(self):
        """
        Regression Test (Resolves Finding F-M4-01):
        When a user pauses execution while the step is in post_delay:
        1. post_delay safely awaits pause_event without triggering ALL_STEPS_DONE from PAUSED.
        2. Resume continues execution cleanly through to completion.
        3. Background runner does not crash, and server never enters a Ghost Running lockout.
        """
        payload = _make_workflow(countdown=0, pre_delay=0, post_delay=100, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
            r_start = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            # Pause mid-post_delay (at 20ms)
            await asyncio.sleep(0.02)
            r_pause = await async_client.post("/api/execute/pause")
            assert r_pause.status_code == 200

            # Wait while paused (150ms) - runner must remain paused, task must NOT crash
            await asyncio.sleep(0.15)
            r_status_paused = await async_client.get("/api/execute/status")
            assert r_status_paused.json()["state"] == "PAUSED"
            assert execution_manager._active_task is not None and not execution_manager._active_task.done()

            # Resume execution
            r_resume = await async_client.post("/api/execute/resume")
            assert r_resume.status_code == 200

            # Wait for remaining post_delay and completion (150ms)
            await asyncio.sleep(0.15)

            # Check status: must complete cleanly
            r_status = await async_client.get("/api/execute/status")
            status_data = r_status.json()
            assert status_data["state"] in ("COMPLETED", "IDLE")

            # Verify next workflow starts cleanly without 409 ghost lockout
            r_start2 = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start2.status_code == 200

            # Clean up
            await async_client.post("/api/execute/abort")

    @pytest.mark.asyncio
    async def test_vulnerability_pre_delay_pause_causes_invalid_fsm_transition(self):
        """
        Regression Test (Resolves Finding F-M4-02):
        When a user pauses execution while a step is in its pre_delay:
        1. pre_delay respects pause_event and halts execution.
        2. Step does not proceed to execute action or trigger STEP_SUCCESS while in PAUSED state.
        3. Task remains alive, resumes cleanly, and reaches completion.
        """
        payload = _make_workflow(countdown=0, pre_delay=100, post_delay=10, num_steps=1)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as async_client:
            r_start = await async_client.post("/api/execute/start", json={"workflow": payload})
            assert r_start.status_code == 200

            # Pause mid-pre_delay (at 20ms)
            await asyncio.sleep(0.02)
            r_pause = await async_client.post("/api/execute/pause")
            assert r_pause.status_code == 200

            # Wait while paused (150ms)
            await asyncio.sleep(0.15)

            # Check that task is still alive and runner is paused (did NOT crash on STEP_SUCCESS)
            task_crashed = execution_manager._active_task is not None and execution_manager._active_task.done()
            assert not task_crashed, "Runner crashed during pre-delay pause with InvalidTransitionError!"

            r_status_paused = await async_client.get("/api/execute/status")
            assert r_status_paused.json()["state"] == "PAUSED"

            # Resume and let finish
            r_resume = await async_client.post("/api/execute/resume")
            assert r_resume.status_code == 200

            # Wait for step completion (150ms)
            await asyncio.sleep(0.15)
            r_status_done = await async_client.get("/api/execute/status")
            assert r_status_done.json()["state"] in ("COMPLETED", "IDLE")

            # Clean up
            await async_client.post("/api/execute/abort")
```

---

### 4.3 Changes to `tests/test_ui_m4_challenge.py`

In `tests/test_ui_m4_challenge.py`, line 96:
```python
# BEFORE (line 96):
        assert "<title>kutomoto — Enterprise Form Automation</title>" in content, "Invalid page title"

# AFTER (line 96):
        assert "<title>kutomoto — Enterprise Form Automation — Copyrights reserved to 90Studio</title>" in content, "Invalid page title"
```

---

### 4.4 Complementary Implementation Needed in Production Code (`app.py`)
To satisfy the audit tests above, the worker implementing the fix in `src/kutomoto/server/app.py` should:
1. In `ServerExecutionManager`:
   - Initialize `self._audit_records: Dict[str, Dict[str, Any]] = {}`
   - In `_run_wrapper`: store the generated summary stamped with `__copyright__` into `self._audit_records[self._workflow_id]` and `self._audit_records[self._execution_id]`.
   - In `abort()`: store aborted audit record stamped with `__copyright__` and `status: "ABORTED"`.
   - Add helper method `get_audit(self, identifier: str) -> Optional[Dict[str, Any]]: return self._audit_records.get(identifier)`.
2. In `create_app()`:
   - Add endpoint:
     ```python
     @app_instance.get("/api/execute/audit/{workflow_id}")
     async def get_execution_audit(workflow_id: str):
         """Retrieve structured audit log summary for a workflow execution."""
         audit = execution_manager.get_audit(workflow_id)
         if audit is None:
             raise HTTPException(
                 status_code=404,
                 detail=f"No audit logs found for workflow '{workflow_id}'.",
             )
         return audit
     ```

---

## 5. Verification Method

Once changes are applied by the implementation worker, run the following commands to verify:

### 5.1 Verification Commands
```powershell
# 1. Verify zero bare passes in test_api.py
python -c "import re; content = open('tests/test_api.py', encoding='utf-8').read(); passes = [m.start() for m in re.finditer(r'^\s*pass\b', content, re.M)]; assert len(passes) == 0, f'Found {len(passes)} bare passes'"

# 2. Verify zero bare passes in MockWin32Driver of test_m4_empirical_challenge.py
python -c "import re; content = open('tests/test_m4_empirical_challenge.py', encoding='utf-8').read(); passes = [m.start() for m in re.finditer(r'^\s*pass\b', content[:4000], re.M)]; assert len(passes) == 0, f'Found {len(passes)} bare passes'"

# 3. Verify HTML title watermark
python -c "assert 'Copyrights reserved to 90Studio' in open('src/kutomoto/ui/index.html', encoding='utf-8').readlines()[5]"

# 4. Run baseline API tests (must be 20 passed, 0 failed)
python -m pytest tests/test_api.py -v

# 5. Run empirical challenge stress suite (must be 14 passed, 0 xfailed, 0 failed)
python -m pytest tests/test_m4_empirical_challenge.py -v

# 6. Run UI challenge test suite (must be 22 passed, 0 failed)
python -m pytest tests/test_ui_m4_challenge.py -v

# 7. Run full project test suite
python -m pytest tests/ -v

# 8. Run code linter
python -m ruff check src/ tests/
```

### 5.2 Invalidation Conditions
- Any bare `pass` method in `MockWin32Driver`.
- Any `409 Conflict` during workflow execution start after pause and resume.
- Missing `"Copyrights reserved to 90Studio"` in `/api/execute/audit/{workflow_id}` response.
- Any lint error reported by `ruff check src/ tests/`.
