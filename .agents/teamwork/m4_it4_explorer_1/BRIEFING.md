# BRIEFING — 2026-11-05T08:29:00Z

## Mission
Investigate route matching in `src/kutomoto/server/app.py` for `/api/execute/audit/{workflow_id}` and static file fallthrough on encoded slashes (%2F).

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_it4_explorer_1
- Original parent: 7675637a-9a1e-40c3-a3cd-063a24f49a5c
- Milestone: m4_it4

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code
- Produce structured 5-component handoff report in `handoff.md`
- Provide exact remediation strategy for the worker agent

## Current Parent
- Conversation ID: 7675637a-9a1e-40c3-a3cd-063a24f49a5c
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `src/kutomoto/server/app.py` (lines 545-605, 880-970)
  - `tests/test_m4_it3_adversarial_challenge.py`
  - Starlette `StringConvertor` (`[^/]+`) vs `PathConvertor` (`.*`)
  - `StaticFiles(html=True)` path resolution and Windows `os.path.join` drive reset semantics
  - OpenAPI schema generation under FastAPI for `:path` converters
- **Key findings**:
  - `%2F` is unquoted to `/` by ASGI into `scope['path']` -> `/api/execute/audit/C:/`.
  - `{workflow_id}` (regex `[^/]+`) fails on the trailing slash, bypassing the endpoint.
  - The unmatched path falls through to `StaticFiles(directory=..., html=True)` mounted at `"/"`.
  - On Windows, `StaticFiles.get_path` splits by `/` and calls `os.path.normpath(os.path.join(*parts))`. `os.path.join('anything', 'C:')` drops preceding parts and resets to `'C:'`.
  - `StaticFiles.lookup_path('C:')` joins `UI_DIR` with `'C:'`, resolving to `UI_DIR`.
  - `StaticFiles` detects a directory, and with `html=True`, serves `index.html` with HTTP 200 OK.
  - Changing `{workflow_id}` to `{workflow_id:path}` matches `C:/`, routes into `get_execution_audit`, where `get_audit_summary` safely rejects it via alphanumeric slug check (`re.sub`), raising HTTP 404 RFC 7807 problem details with 90Studio attribution.
  - OpenAPI schema is 100% invariant (path stays `/api/execute/audit/{workflow_id}`).
- **Unexplored areas**: None. Root cause, Windows mechanics, route matching, and remediation verified empirically.

## Key Decisions Made
- Confirmed primary remediation: `@app_instance.get("/api/execute/audit/{workflow_id:path}")` at line 900.
- Recommended defense-in-depth: apply `{workflow_id:path}` to workflows endpoints and consider an explicit `/api/{unmatched:path}` 404 fallback before static files mount.
- Produced 5-component handoff report in `handoff.md`.

## Artifact Index
- `DISPATCH.md` — Initial dispatch message
- `BRIEFING.md` — Working memory
- `progress.md` — Liveness heartbeat
- `handoff.md` — Final analysis report
