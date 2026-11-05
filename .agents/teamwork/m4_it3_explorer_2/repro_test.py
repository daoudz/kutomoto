import asyncio
import os
import sys
import httpx
import uuid

sys.path.insert(0, os.path.abspath("src"))

from kutomoto.server.app import app, get_driver
from kutomoto.engine.safety import MockWin32Driver

async def test():
    app.dependency_overrides[get_driver] = lambda: MockWin32Driver()
    wf_id = f"wf-{uuid.uuid4()}"
    payload = {
        "schema_version": "1.0.0",
        "id": wf_id,
        "name": "Active Test Workflow",
        "description": "Enterprise test workflow",
        "author": "90Studio",
        "copyright": "Copyrights reserved to 90Studio",
        "source_mode": "manual_step_flow",
        "target_application": {
            "type": "web_browser",
            "window_title_pattern": "Banking KYC Customer Onboarding",
            "process_name": "msedge.exe",
            "match_mode": "contains",
        },
        "execution_settings": {
            "countdown_seconds": 0,
            "default_step_delay_ms": 10,
            "typing_speed_ms": 5,
            "stop_on_error": True,
            "error_recovery_policy": "abort",
            "max_step_retries": 1,
            "failsafe_corner_enabled": True,
            "abort_hotkey": "Escape",
        },
        "variables": [],
        "steps": [
            {
                "step_id": str(uuid.uuid4()),
                "sequence_index": 1,
                "label": "Delay step",
                "action_type": "delay",
                "enabled": True,
                "pre_delay_ms": 1000,
                "post_delay_ms": 1000,
                "parameters": {"duration_ms": 1000},
            }
        ],
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        st_resp = await c.post("/api/execute/start", json={"workflow": payload})
        st = st_resp.json()
        print("Start resp:", st)
        exec_id = st["execution_id"]
        
        # Test 1: Query by wf_id during active
        r_wf = await c.get(f"/api/execute/audit/{wf_id}")
        print("Active query wf_id status:", r_wf.status_code)
        print("Active query wf_id response:", r_wf.json())
        
        # Test 2: Query by exec_id during active
        r_exec = await c.get(f"/api/execute/audit/{exec_id}")
        print("Active query exec_id status:", r_exec.status_code)
        print("Active query exec_id response:", r_exec.json())
        
        await c.post("/api/execute/abort")

if __name__ == "__main__":
    asyncio.run(test())
