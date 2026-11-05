import asyncio
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from typing import Any, Dict, Optional
import uuid

# Replicate ServerExecutionManager.get_audit_summary with proposed fix
def proposed_get_audit_summary(
    mgr: Any,
    workflow_id: str,
    audit_dirs: list[Path]
) -> Optional[Dict[str, Any]]:
    """Retrieve audit log summary for a workflow ID or execution ID."""
    # 1. Live active execution check by workflow_id OR execution_id
    if (mgr._workflow_id == workflow_id or mgr._execution_id == workflow_id) and mgr.is_active():
        return {
            "workflow_id": mgr._workflow_id,
            "execution_id": mgr._execution_id,
            "workflow_name": mgr._workflow_name,
            "status": mgr.get_state(),
            "duration_seconds": round(time.perf_counter() - mgr._start_time, 2),
            "total_steps": mgr._total_steps,
            "current_step_index": mgr._current_step_index,
            "timestamp_utc": "2026-11-05T00:00:00Z",
            "copyright": "Copyrights reserved to 90Studio",
        }

    # 2. In-memory completed / aborted audit summaries
    if workflow_id in mgr._audit_summaries:
        return mgr._audit_summaries[workflow_id]

    if (mgr._workflow_id == workflow_id or mgr._execution_id == workflow_id) and mgr._last_audit_summary:
        return mgr._last_audit_summary

    # 3. On-disk fallback search by workflow_id or execution_id
    safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "", workflow_id)
    if not safe_id:
        return None

    for audit_dir in audit_dirs:
        if audit_dir.is_dir():
            # Check prefix match for workflow_id (latest timestamp first)
            candidates = sorted(audit_dir.glob(f"audit_{safe_id}_*.json"), reverse=True)
            if not candidates:
                # Check midfix match for execution_id (latest timestamp first)
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
                            "copyright": data.get("copyright", "Copyrights reserved to 90Studio"),
                        }
                except Exception:
                    pass
    return None


class FakeMgr:
    def __init__(self):
        self._workflow_id = None
        self._execution_id = None
        self._workflow_name = "Mock Flow"
        self._start_time = time.perf_counter()
        self._total_steps = 3
        self._current_step_index = 1
        self._audit_summaries = {}
        self._last_audit_summary = None
        self._active = False
        self._state = "IDLE"

    def is_active(self):
        return self._active

    def get_state(self):
        return self._state


def run_all_checks():
    mgr = FakeMgr()
    with tempfile.TemporaryDirectory() as td:
        audit_dir = Path(td)
        dirs = [audit_dir]

        # Scenario 1: Active execution
        mgr._active = True
        mgr._state = "RUNNING"
        mgr._workflow_id = "wf-active-10"
        mgr._execution_id = "exec-active-99"

        res_wf = proposed_get_audit_summary(mgr, "wf-active-10", dirs)
        assert res_wf is not None
        assert res_wf["status"] == "RUNNING"
        assert res_wf["execution_id"] == "exec-active-99"
        print("Scenario 1 (Active query by wf_id): PASSED")

        res_exec = proposed_get_audit_summary(mgr, "exec-active-99", dirs)
        assert res_exec is not None
        assert res_exec["status"] == "RUNNING"
        assert res_exec["workflow_id"] == "wf-active-10"
        print("Scenario 2 (Active query by exec_id): PASSED")

        # Scenario 3: Execution completes
        mgr._active = False
        mgr._state = "IDLE"
        completed_summary = {
            "workflow_id": "wf-active-10",
            "execution_id": "exec-active-99",
            "status": "SUCCESS",
            "copyright": "Copyrights reserved to 90Studio"
        }
        mgr._audit_summaries["wf-active-10"] = completed_summary
        mgr._audit_summaries["exec-active-99"] = completed_summary
        mgr._last_audit_summary = completed_summary

        res_comp_wf = proposed_get_audit_summary(mgr, "wf-active-10", dirs)
        assert res_comp_wf["status"] == "SUCCESS"
        res_comp_exec = proposed_get_audit_summary(mgr, "exec-active-99", dirs)
        assert res_comp_exec["status"] == "SUCCESS"
        print("Scenario 3 (Completed in-memory queries): PASSED")

        # Scenario 4: In-memory cache cleared (simulate server restart)
        # Write to disk
        p1 = audit_dir / "audit_wf-disk-1_exec-disk-10_20261105_120000.json"
        p1.write_text(json.dumps({
            "workflow_id": "wf-disk-1",
            "execution_id": "exec-disk-10",
            "workflow_name": "Disk Flow 1",
            "timestamp_utc": "2026-11-05T12:00:00Z",
            "execution_summary": {"final_status": "SUCCESS", "duration_seconds": 2.5, "total_steps": 2}
        }), encoding="utf-8")

        mgr._audit_summaries.clear()
        mgr._last_audit_summary = None
        mgr._workflow_id = None
        mgr._execution_id = None

        disk_wf = proposed_get_audit_summary(mgr, "wf-disk-1", dirs)
        assert disk_wf is not None
        assert disk_wf["workflow_id"] == "wf-disk-1"
        assert disk_wf["execution_id"] == "exec-disk-10"
        print("Scenario 4 (Disk query by wf_id): PASSED")

        disk_exec = proposed_get_audit_summary(mgr, "exec-disk-10", dirs)
        assert disk_exec is not None
        assert disk_exec["workflow_id"] == "wf-disk-1"
        assert disk_exec["execution_id"] == "exec-disk-10"
        print("Scenario 5 (Disk query by exec_id): PASSED")

        # Scenario 6: Non-existent ID
        none_res = proposed_get_audit_summary(mgr, "unknown-id", dirs)
        assert none_res is None
        print("Scenario 6 (Non-existent returns None): PASSED")

        # Scenario 7: F-M4-03 Glob Injection
        leak_res = proposed_get_audit_summary(mgr, "*", dirs)
        assert leak_res is None
        print("Scenario 7 (Wildcard * returns None): PASSED")

        leak_pattern = proposed_get_audit_summary(mgr, "*disk*", dirs)
        assert leak_pattern is None
        print("Scenario 8 (Wildcard pattern returns None): PASSED")

    print("\nALL 8 SCENARIOS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_all_checks()
