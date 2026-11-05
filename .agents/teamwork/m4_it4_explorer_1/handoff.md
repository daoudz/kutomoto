# Investigation Report: Route Matching and Static Fallthrough in kutomoto Server

**Agent**: `m4_it4_explorer_1` (Explorer: investigation, synthesis)  
**Parent Agent**: `7675637a-9a1e-40c3-a3cd-063a24f49a5c`  
**Date**: 2026-11-05T08:28:00Z  
**Status**: COMPLETE (Read-Only Analysis)  

---

## 1. Observation

### 1.1 Direct Reproduction of the Fallthrough Bug
Executing a direct probe request against `kutomoto.server.app`:
```powershell
python -c "import sys; sys.path.insert(0, 'src'); from fastapi.testclient import TestClient; from kutomoto.server.app import app; c = TestClient(app); r = c.get('/api/execute/audit/C%3A%2F'); print('STATUS:', r.status_code); print('CONTENT-TYPE:', r.headers.get('content-type')); print('BODY:', r.text[:120])"
```
**Output**:
```
STATUS: 200
CONTENT-TYPE: text/html; charset=utf-8
BODY: <!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, in
```

### 1.2 Route Configuration in `src/kutomoto/server/app.py`
Inspection of `src/kutomoto/server/app.py`:
- **Line 900**:
  ```python
  @app_instance.get("/api/execute/audit/{workflow_id}")
  async def get_execution_audit(
      workflow_id: str,
      runner_mgr: ServerExecutionManager = Depends(get_runner),
  ):
      """Retrieve audit log summary for a workflow execution."""
      summary = runner_mgr.get_audit_summary(workflow_id)
      if summary is None:
          raise HTTPException(
              status_code=404,
              detail=f"Audit log summary for workflow '{workflow_id}' not found.",
          )
      return summary
  ```
- **Line 960**:
  ```python
  # Mount UI directory for /css, /js, etc. (registered after API routes)
  if UI_DIR.exists():
      app_instance.mount("/", StaticFiles(directory=str(UI_DIR), html=True), name="ui")
  ```

### 1.3 ASGI Path Decoding and Starlette Parameter Matching
When tracing the ASGI scope for `/api/execute/audit/C%3A%2F`:
```
SCOPE path: /api/execute/audit/C:/ raw_path: b'/api/execute/audit/C%3A%2F'
```
1. In the ASGI HTTP specification, the ASGI server decodes percent-encoded characters into `scope["path"]`.
2. Starlette's `StringConvertor` (the default converter for `{workflow_id}`) has regex `[^/]+`.
   Testing `CONVERTOR_TYPES["str"].regex` yields `[^/]+`.
3. When `scope["path"]` is `/api/execute/audit/C:/`, the trailing `/` violates `[^/]+`.
   Therefore, route `APIRoute(path='/api/execute/audit/{workflow_id}')` **fails to match**.
4. By contrast, Starlette's `PathConvertor` (`{workflow_id:path}`) has regex `.*`.
   Testing `CONVERTOR_TYPES["path"].regex` yields `.*`.
   With `{workflow_id:path}`, `/api/execute/audit/C:/` matches with `workflow_id="C:/"`.

### 1.4 Windows-Specific Path Resolution in `StaticFiles(html=True)`
When no API route matches `/api/execute/audit/C:/`, Starlette falls through to the root mount:
`app_instance.mount("/", StaticFiles(directory=str(UI_DIR), html=True), name="ui")`.

Inspecting `StaticFiles.get_path(scope)` and `lookup_path`:
1. `StaticFiles.get_path(scope)` performs:
   ```python
   route_path = get_route_path(scope)  # '/api/execute/audit/C:/'
   parts = route_path.split("/")        # ['', 'api', 'execute', 'audit', 'C:', '']
   return os.path.normpath(os.path.join(*parts))
   ```
2. **On Windows**, `os.path.join` treats drive letters (`'C:'`) as root drive resets:
   ```powershell
   os.path.join('', 'api', 'execute', 'audit', 'C:', '') -> 'C:'
   ```
   All segments prior to `'C:'` (`'api'`, `'execute'`, `'audit'`) are stripped.
3. `StaticFiles.lookup_path('C:')` calls:
   ```python
   joined_path = os.path.join(directory, 'C:')
   ```
   where `directory` is `C:\Users\daoud\projects\kutomoto\src\kutomoto\ui`.
   On Windows, appending `'C:'` (drive without slash) to a path already located on drive C returns the path itself (`C:\Users\daoud\projects\kutomoto\src\kutomoto\ui`).
4. `os.stat('C:\Users\daoud\projects\kutomoto\src\kutomoto\ui')` confirms this is a directory (`stat.S_ISDIR` is True).
5. In `StaticFiles.get_response`, because `stat.S_ISDIR` is True and `self.html=True`:
   ```python
   index_path = os.path.join(path, "index.html")  # os.path.join('C:', 'index.html')
   full_path, stat_result = await anyio.to_thread.run_sync(self.lookup_path, index_path)
   ```
   `lookup_path('C:\index.html')` resolves to `C:\Users\daoud\projects\kutomoto\src\kutomoto\ui\index.html`.
6. Because `index.html` exists and is a regular file, `StaticFiles` returns `FileResponse` with `status_code=200` and `Content-Type: text/html; charset=utf-8`.

### 1.5 Comparison: `{workflow_id}` vs `{workflow_id:path}`
Testing route matching with `{workflow_id:path}` on an app instance:
```powershell
python -c "import sys; sys.path.insert(0, 'src'); from kutomoto.server.app import create_app; from fastapi.testclient import TestClient; from starlette.routing import compile_path; app = create_app()
for route in app.routes:
    if getattr(route, 'path', '') == '/api/execute/audit/{workflow_id}':
        route.path = '/api/execute/audit/{workflow_id:path}'
        route.path_regex, route.path_format, route.param_convertors = compile_path(route.path)
c = TestClient(app); r = c.get('/api/execute/audit/C%3A%2F'); print('STATUS:', r.status_code); print('JSON:', r.json())"
```
**Output**:
```
STATUS: 404
JSON: {'type': 'https://90studio.com/errors/404', 'title': "Audit log summary for workflow 'C:/' not found.", 'status': 404, 'detail': "Audit log summary for workflow 'C:/' not found.", 'instance': '/api/execute/audit/C:/', 'copyright': 'Copyrights reserved to 90Studio'}
```

### 1.6 OpenAPI Schema Invariance
Comparing OpenAPI schemas generated by FastAPI for `{workflow_id}` vs `{workflow_id:path}`:
- **Paths key**: Identical (`/api/execute/audit/{workflow_id}`). FastAPI strips the `:path` converter suffix when generating OpenAPI path templates.
- **Parameter definition**: Identical (`name: 'workflow_id'`, `in: 'path'`, `required: True`, `schema: {'type': 'string', 'title': 'Workflow Id'}`).
- **Swagger UI (`/docs`) & ReDoc (`/redoc`)**: Zero breaking changes.

---

## 2. Logic Chain

1. **Step 1 (ASGI Layer)**: The client query `GET /api/execute/audit/C%3A%2F` has an encoded forward slash (`%2F`). Per ASGI specification, ASGI servers unquote this parameter in `scope["path"]`, yielding `/api/execute/audit/C:/`. (Observation 1.3)
2. **Step 2 (Route Mismatch)**: The route defined at `src/kutomoto/server/app.py:900` uses `@app_instance.get("/api/execute/audit/{workflow_id}")`. In Starlette, `{workflow_id}` compiles to `[^/]+`, which rejects strings containing `/`. Because `/api/execute/audit/C:/` ends in `/`, the route matcher rejects it. (Observation 1.3)
3. **Step 3 (SPA Fallthrough)**: Because no API route matches `/api/execute/audit/C:/`, Starlette routes the request to the catch-all mount at `src/kutomoto/server/app.py:960`: `app_instance.mount("/", StaticFiles(directory=str(UI_DIR), html=True), name="ui")`. (Observation 1.2, 1.4)
4. **Step 4 (Windows Drive Ingestion)**: In `StaticFiles.get_path()`, splitting `/api/execute/audit/C:/` yields segment `'C:'`. Under Windows path semantics in Python's standard library, `os.path.join(*parts)` resets to `'C:'`, discarding the `/api/execute/audit` prefix. (Observation 1.4)
5. **Step 5 (Directory Index Serving)**: Appending `'C:'` to the UI directory path on drive C returns the UI directory itself. Since `html=True` is enabled on `StaticFiles`, Starlette treats this as a directory URL and serves `UI_DIR / "index.html"` with HTTP 200 OK. (Observation 1.4)
6. **Step 6 (Security & Contract Breach)**: Instead of the endpoint executing `ServerExecutionManager.get_audit_summary()`, which contains strict alphanumeric slug validation (`re.sub(r"[^a-zA-Z0-9_\-]", "", workflow_id)`), the request never reaches the handler. The client receives an HTML SPA page with HTTP 200 OK rather than an RFC 7807 404 Problem Details JSON response with 90Studio copyright attribution. (Observation 1.1, 1.4)
7. **Step 7 (Remediation via `:path`)**: Updating the route decorator to `@app_instance.get("/api/execute/audit/{workflow_id:path}")` instructs Starlette to use `PathConvertor` (`.*`), matching any arbitrary path including forward slashes. The handler receives `workflow_id="C:/"`. The sanitization logic in `get_audit_summary` immediately rejects it (`safe_id != workflow_id`), raising `HTTPException(404)` which is translated by the registered RFC 7807 handler into a compliant JSON response with 90Studio attribution. (Observation 1.5)
8. **Step 8 (Safety & Compatibility)**: Changing to `{workflow_id:path}` has zero side effects on valid queries, does not shadow preceding routes (`/api/execute/status` is defined prior to line 900), and produces an identical OpenAPI 3.1 schema. (Observation 1.5, 1.6)

---

## 3. Caveats

- **Scope of Route Fallthrough**: This specific drive-letter fallthrough (`C%3A%2F` returning 200 HTML) only occurs on Windows systems when `html=True` is configured on `StaticFiles` and a URL contains a drive specifier (`C:`). On non-Windows platforms, `os.path.join` does not treat `'C:'` as a root specifier, so `StaticFiles` would raise 404. However, on Windows, it is a reproducible security/API integrity issue.
- **Other Path Parameter Endpoints**:
  - `/api/workflows/{workflow_id}` (lines 756 and 767) also uses `{workflow_id}` without `:path`. Queries like `/api/workflows/C%3A%2F` will exhibit identical fallthrough behavior to `StaticFiles`. While the immediate failure reported in Milestone 4 is on `/api/execute/audit/{workflow_id}`, applying defense-in-depth to all `/api/` endpoints is strongly recommended.
- **Read-Only Constraint**: In compliance with the explorer archetype rules, no changes have been made to `src/kutomoto/server/app.py`. The remediation must be executed by a worker agent.

---

## 4. Conclusion

### Root Cause Summary
Queries with encoded slashes such as `/api/execute/audit/C%3A%2F` bypass `@app_instance.get("/api/execute/audit/{workflow_id}")` because ASGI decodes `%2F` into `/`, which violates Starlette's `StringConvertor` regex (`[^/]+`). The unhandled route falls through to `StaticFiles(directory=str(UI_DIR), html=True)` mounted at `"/"`. On Windows, `StaticFiles.get_path()` strips preceding path segments upon encountering `'C:'`, matches the root UI directory, and serves `index.html` with HTTP 200 OK.

### Remediation Strategy for Worker Agent

#### Primary Fix (Mandatory)
In `src/kutomoto/server/app.py`, update line 900:
```python
# Before (Line 900):
@app_instance.get("/api/execute/audit/{workflow_id}")
async def get_execution_audit(
    workflow_id: str,
    runner_mgr: ServerExecutionManager = Depends(get_runner),
):

# After (Line 900):
@app_instance.get("/api/execute/audit/{workflow_id:path}")
async def get_execution_audit(
    workflow_id: str,
    runner_mgr: ServerExecutionManager = Depends(get_runner),
):
```

#### Secondary Defense-in-Depth (Recommended)
1. **Workflows Endpoint Symmetry**:
   In `src/kutomoto/server/app.py` lines 756 and 767:
   ```python
   # Line 756:
   @app_instance.get("/api/workflows/{workflow_id:path}")
   # Line 767:
   @app_instance.delete("/api/workflows/{workflow_id:path}")
   ```
2. **Explicit API Fallback Guard**:
   Right before line 960 (before `app_instance.mount("/", ...)`), add an explicit unhandled API route guard:
   ```python
   @app_instance.api_route("/api/{unmatched:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
   async def api_not_found(unmatched: str):
       raise HTTPException(
           status_code=404,
           detail=f"API endpoint '/api/{unmatched}' not found.",
       )
   ```
   This guarantees that no request under `/api/` can ever fall through to `StaticFiles` or return HTML.

---

## 5. Verification Method

### 5.1 Verification Commands
The worker agent can independently verify the defect and the remediation using these commands:

1. **Reproduction probe before fix** (must return 200 HTML):
   ```powershell
   python -c "import sys; sys.path.insert(0, 'src'); from fastapi.testclient import TestClient; from kutomoto.server.app import app; c = TestClient(app); r = c.get('/api/execute/audit/C%3A%2F'); assert r.status_code == 200"
   ```

2. **Verification probe after applying `{workflow_id:path}`** (must return 404 JSON):
   ```powershell
   python -c "import sys; sys.path.insert(0, 'src'); from fastapi.testclient import TestClient; from kutomoto.server.app import app; c = TestClient(app); r = c.get('/api/execute/audit/C%3A%2F'); assert r.status_code == 404; assert r.headers['content-type'] == 'application/json'; assert r.json()['copyright'] == 'Copyrights reserved to 90Studio'"
   ```

3. **Adversarial challenge test execution**:
   ```powershell
   python -m pytest tests/test_m4_it3_adversarial_challenge.py -v
   ```

4. **Full repository test suite execution**:
   ```powershell
   python -m pytest tests/
   ```

5. **Code style and linter check**:
   ```powershell
   python -m ruff check src/ tests/
   ```

### 5.2 Invalidation Conditions
This analysis and remediation strategy are invalidated if:
1. Changing `{workflow_id:path}` causes any route conflict with `/api/execute/status` or other `/api/execute/*` endpoints. (Empirically verified: `/api/execute/status` precedes line 900 and has no path parameters).
2. FastAPI OpenAPI generation fails or alters the documentation path template. (Empirically verified: OpenAPI strips `:path` converter, schema is identical).
3. `re.sub(r"[^a-zA-Z0-9_\-]", "", workflow_id)` in `get_audit_summary` accepts a malicious path. (Empirically verified: slashes and colons cause `safe_id != workflow_id`, returning None -> 404).
