# BRIEFING — 2026-11-05T05:09:30Z

## Mission
Investigate Finding F-M4-04 regarding asymmetric identifier handling (workflow_id vs execution_id) in active execution polling and on-disk fallback in src/kutomoto/server/app.py.

## 🔒 My Identity
- Archetype: explorer
- Roles: explorer, identifier resolution and audit trail persistence specialist
- Working directory: c:\Users\daoud\projects\kutomoto\.agents\teamwork\m4_it3_explorer_2
- Original parent: 59700fc9-320d-4ed3-b1db-2fc709fed831
- Milestone: M4

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Strictly read-only on codebase! Only write to .agents/teamwork/m4_it3_explorer_2/

## Current Parent
- Conversation ID: 59700fc9-320d-4ed3-b1db-2fc709fed831
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `src/kutomoto/server/app.py` (lines 280-588, lines 814-878)
  - `src/kutomoto/engine/audit.py` (lines 50-70, lines 235-275)
  - `tests/test_api.py` (lines 495-564)
  - `.agents/teamwork/m4_it2_challenger_2/handoff.md`
- **Key findings**:
  - `app.py:547`: Active execution polling checks only `self._workflow_id == workflow_id`, causing 404 when clients query active runs via `execution_id`.
  - `app.py:563`: On-disk lookup queries only `audit_{workflow_id}_*.json`. Persisted files follow `audit_{workflow_id}_{execution_id}_{timestamp}.json`. Querying by `execution_id` fails prefix match, returning 404 on disk fallback.
  - Evaluation order hazard: `self._last_audit_summary` placed before `is_active()` can return stale past summary during active execution.
  - Neutralized glob injection (F-M4-03) via `re.sub(r"[^a-zA-Z0-9_\-]", "", workflow_id)` and dual lookup (prefix then midfix) with JSON verification.
- **Unexplored areas**: None within F-M4-04 scope.

## Key Decisions Made
- Prioritize active execution check `is_active()` before `self._last_audit_summary` in `get_audit_summary` to avoid stale summary delivery.
- Implement dual candidate resolution (prefix match for workflow_id, midfix match for execution_id) with reverse sorting by timestamp and JSON payload confirmation.
- Created `f_m4_04_remediation.patch` and `proposed_test_additions.py` for worker implementation.

## Artifact Index
- DISPATCH.md — record of incoming dispatch instructions
- BRIEFING.md — situational awareness
- progress.md — liveness heartbeat
- repro_test.py — reproduction of active polling 404 defect
- repro_disk_test.py — reproduction of on-disk 404 defect
- test_proposed_resolution.py — standalone logic verification
- test_comprehensive_fix.py — 8-scenario comprehensive test suite
- f_m4_04_remediation.patch — ready-to-apply patch for app.py
- proposed_test_additions.py — proposed test cases for test_api.py
- handoff.md — final 5-component handoff report
