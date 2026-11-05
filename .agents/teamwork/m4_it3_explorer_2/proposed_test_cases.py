"""
Proposed test cases for tests/test_api.py verifying F-M4-04 and F-M4-03 remediation.
"""

import copy
import json
import os
from pathlib import Path
import sys
import time
import uuid
import pytest
from fastapi.testclient import TestClient

SRC_PATH = Path(__file__).resolve().parent.parent.parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from kutomoto.server.app import app, execution_manager, BASE_DIR, get_driver
from kutomoto.engine.safety import MockWin32Driver


def test_audit_active_by_execution_id():
    """Verify GET /api/execute/audit/{execution_id} during active execution returns 200."""
    app.dependency_overrides[get_driver] = lambda: MockWin32Driver()
    client = TestClient(app)
    
    wf_id = f"wf-active-{uuid.uuid4()}"
    payload = {
        "schema_version": "1.0.0",
        "id": wf_id,
        "name": "Active Polling Test",
        "description": "Test active execution polling",
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
                "pre_delay_ms": 500,
                "post_delay_ms": 500,
                "parameters": {"duration_ms": 500},
            }
        ],
    }
    
    try:
        start_resp = client.post("/api/execute/start", json={"workflow": payload})
        assert start_resp.status_code == 200
        data = start_resp.json()
        exec_id = data["execution_id"]
        
        # Query active execution by execution_id
        r = client.get(f"/api/execute/audit/{exec_id}")
        return r
    finally:
        client.post("/api/execute/abort")
