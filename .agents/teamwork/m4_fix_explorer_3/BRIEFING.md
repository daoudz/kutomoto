# BRIEFING — 2026-11-05T07:38:00Z

## Mission
Formulate exact test plan and test code changes required for Milestone 4 Iteration 2 (test_api.py, test_m4_empirical_challenge.py, test_ui_m4_challenge.py, and regression verification plan).

## 🔒 My Identity
- Archetype: explorer
- Roles: testing, quality assurance, regression protection
- Working directory: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_fix_explorer_3\
- Original parent: 59700fc9-320d-4ed3-b1db-2fc709fed831
- Milestone: Milestone 4 Iteration 2

## 🔒 Key Constraints
- Read-only investigation — do NOT implement / modify source code or tests
- Write only to working directory .agents/teamwork/m4_fix_explorer_3/
- Provide exact test code proposals, diffs/replacements, and verification plan

## Current Parent
- Conversation ID: 59700fc9-320d-4ed3-b1db-2fc709fed831
- Updated: 2026-11-05T07:38:00Z

## Investigation State
- **Explored paths**:
  - `tests/test_api.py`: Lines 29-152 (MockWin32Driver bare passes), lines 311-317 (root HTML assertion), lines 426-478 (execution lifecycle)
  - `tests/test_m4_empirical_challenge.py`: Lines 38-143 (MockWin32Driver bare passes), lines 571-687 (xfail tests for F-M4-01 and F-M4-02)
  - `tests/test_ui_m4_challenge.py`: Lines 80-120 (line 96 `<title>` assertion vulnerability upon HTML title update)
  - `src/kutomoto/engine/safety.py`: Lines 269-543 (MockWin32Driver implementation)
  - `src/kutomoto/engine/audit.py`: Lines 52-68 (KutomotoAuditLog schema and watermark), lines 235-275 (generate_log)
  - `src/kutomoto/server/app.py`: Lines 280-465 (ServerExecutionManager lifecycle, audit storage), lines 639-742 (REST endpoints)
- **Key findings**:
  1. `tests/test_api.py` lines 130, 133, 142, 145, 148, 151 contain bare `pass` methods in `MockWin32Driver`. Can be replaced cleanly with recording implementations (`self.cleared_fields.append`, `self.scrolls.append`, `self.down_keys.append`, `self.up_keys.append`, `self.mouse_down_events.append`, `self.mouse_up_events.append`).
  2. `tests/test_m4_empirical_challenge.py` lines 120, 123, 132, 135, 138, 141 contain the exact same 6 bare `pass` methods in its mock driver.
  3. `tests/test_ui_m4_challenge.py` line 96 has hardcoded `assert "<title>kutomoto — Enterprise Form Automation</title>" in content`. When `index.html` line 6 is updated with 90Studio attribution, this test will break unless updated concurrently.
  4. Server needs `GET /api/execute/audit/{workflow_id}` endpoint returning 404 if no execution has occurred, and 200 with structured audit dictionary stamped `"copyright": "Copyrights reserved to 90Studio"` upon completion or abort.
  5. The two `@pytest.mark.xfail` tests in `tests/test_m4_empirical_challenge.py` can be converted into active regression tests asserting clean pause hold, task liveness, resume execution, and non-ghost recovery.
- **Unexplored areas**: None. All target files and regression verification paths analyzed.

## Key Decisions Made
- Formulate recording implementations for `MockWin32Driver` rather than subclassing `safety.MockWin32Driver` to preserve exact tuple formats and method signatures expected by tests.
- Propose new `TestAuditLogEndpoint` test class in `test_api.py` with 3 test cases (404 not found, 200 success with watermark, 200 abort with watermark).
- Document and provide fix for `tests/test_ui_m4_challenge.py` line 96 title assertion to prevent regression failure.
- Remove xfail decorators and formulate comprehensive lifecycle pause/resume validation for `test_m4_empirical_challenge.py`.

## Artifact Index
- DISPATCH.md — Incoming dispatch record
- BRIEFING.md — Situational awareness
- progress.md — Liveness heartbeat
- handoff.md — Final 5-component report
