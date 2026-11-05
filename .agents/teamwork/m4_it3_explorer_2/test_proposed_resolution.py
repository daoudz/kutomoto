import json
from pathlib import Path
import re
import tempfile

def test_proposed_disk_resolution():
    with tempfile.TemporaryDirectory() as tmp_dir:
        audit_dir = Path(tmp_dir)
        
        wf1 = "wf-kyc-100"
        exec1 = "exec-aaa-111"
        ts1 = "20261105_100000"
        
        wf2 = "wf-kyc-100"
        exec2 = "exec-bbb-222"
        ts2 = "20261105_110000"
        
        wf3 = "wf-wire-transfer"
        exec3 = "exec-ccc-333"
        ts3 = "20261105_120000"
        
        files = [
            (f"audit_{wf1}_{exec1}_{ts1}.json", {"workflow_id": wf1, "execution_id": exec1, "workflow_name": "KYC 1", "execution_summary": {"final_status": "SUCCESS"}}),
            (f"audit_{wf2}_{exec2}_{ts2}.json", {"workflow_id": wf2, "execution_id": exec2, "workflow_name": "KYC 2", "execution_summary": {"final_status": "SUCCESS"}}),
            (f"audit_{wf3}_{exec3}_{ts3}.json", {"workflow_id": wf3, "execution_id": exec3, "workflow_name": "Wire Secret", "execution_summary": {"final_status": "SUCCESS"}}),
        ]
        
        for fname, content in files:
            (audit_dir / fname).write_text(json.dumps(content), encoding="utf-8")
            
        def resolve_audit(workflow_id: str):
            safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "", workflow_id)
            if not safe_id:
                return None
            
            candidates = sorted(audit_dir.glob(f"audit_{safe_id}_*.json"), reverse=True)
            if not candidates:
                candidates = sorted(audit_dir.glob(f"audit_*_{safe_id}_*.json"), reverse=True)
                
            for p in candidates:
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    if data.get("workflow_id") == safe_id or data.get("execution_id") == safe_id:
                        return data
                except Exception:
                    pass
            return None
            
        # Test A: Query wf_id (should return latest: exec2)
        res_wf = resolve_audit("wf-kyc-100")
        assert res_wf is not None
        assert res_wf["execution_id"] == exec2, f"Expected {exec2}, got {res_wf['execution_id']}"
        print("Test A (wf_id latest execution): PASSED")
        
        # Test B: Query exec1 by execution_id
        res_exec1 = resolve_audit("exec-aaa-111")
        assert res_exec1 is not None
        assert res_exec1["execution_id"] == exec1
        print("Test B (exec1 by execution_id): PASSED")
        
        # Test C: Query exec3 by execution_id
        res_exec3 = resolve_audit("exec-ccc-333")
        assert res_exec3 is not None
        assert res_exec3["workflow_id"] == wf3
        print("Test C (exec3 by execution_id): PASSED")
        
        # Test D: Query non-existent
        assert resolve_audit("non-existent-id") is None
        print("Test D (non-existent): PASSED")
        
        # Test E: Fuzz / Injection attempt with wildcard '*'
        res_wildcard = resolve_audit("*")
        assert res_wildcard is None, f"Expected None for '*', got {res_wildcard}"
        print("Test E (wildcard injection blocked): PASSED")
        
        # Test F: Fuzz / Injection with regex/glob chars
        assert resolve_audit("wf*") is None
        assert resolve_audit("?exec?") is None
        assert resolve_audit("[a-z]") is None
        print("Test F (glob metacharacters neutralized): PASSED")

if __name__ == "__main__":
    test_proposed_disk_resolution()
