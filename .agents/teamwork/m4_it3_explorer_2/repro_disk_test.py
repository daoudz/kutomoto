import asyncio
import json
import os
from pathlib import Path
import sys
import httpx
import uuid

sys.path.insert(0, os.path.abspath("src"))

from kutomoto.server.app import app, execution_manager, BASE_DIR

async def test_on_disk():
    audit_dir = BASE_DIR / "data" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    
    wf_id = f"wf-disk-{uuid.uuid4()}"
    exec_id = f"exec-disk-{uuid.uuid4()}"
    
    # Audit file named according to AuditLogger format:
    # audit_{workflow_id}_{execution_id}_{timestamp}.json
    filename = f"audit_{wf_id}_{exec_id}_20261105_120000.json"
    p = audit_dir / filename
    
    audit_content = {
        "workflow_id": wf_id,
        "execution_id": exec_id,
        "workflow_name": "Disk Test Workflow",
        "timestamp_utc": "2026-11-05T12:00:00Z",
        "copyright": "Copyrights reserved to 90Studio",
        "execution_summary": {
            "total_steps": 5,
            "successful_steps": 5,
            "failed_steps": 0,
            "retried_steps": 0,
            "duration_seconds": 1.25,
            "final_status": "SUCCESS"
        }
    }
    p.write_text(json.dumps(audit_content), encoding="utf-8")
    
    try:
        # Clear in-memory caches to force disk lookup
        execution_manager._audit_summaries.clear()
        execution_manager._last_audit_summary = None
        
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            # Query by wf_id
            r_wf = await c.get(f"/api/execute/audit/{wf_id}")
            print("Disk query wf_id status:", r_wf.status_code)
            
            # Query by exec_id
            r_exec = await c.get(f"/api/execute/audit/{exec_id}")
            print("Disk query exec_id status:", r_exec.status_code)
            print("Disk query exec_id response:", r_exec.json())
    finally:
        if p.exists():
            p.unlink()

if __name__ == "__main__":
    asyncio.run(test_on_disk())
