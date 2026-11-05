# ==============================================================================
# PROPOSED TEST ADDITIONS FOR tests/test_api.py (under TestAuditLogEndpoint)
# ==============================================================================

    def test_get_audit_active_execution_by_execution_id_returns_200(self, client, valid_workflow_payload):
        """Verify GET /api/execute/audit/{execution_id} during active execution returns 200 (F-M4-04)."""
        active_payload = copy.deepcopy(valid_workflow_payload)
        for s in active_payload["steps"]:
            s["pre_delay_ms"] = 500
            s["post_delay_ms"] = 500

        try:
            start_resp = client.post("/api/execute/start", json={"workflow": active_payload})
            assert start_resp.status_code in (200, 202)
            data = start_resp.json()
            exec_id = data["execution_id"]
            wf_id = data["workflow_id"]

            # Query by execution_id while active
            audit_resp = client.get(f"/api/execute/audit/{exec_id}")
            assert audit_resp.status_code == 200
            audit = audit_resp.json()
            assert audit["execution_id"] == exec_id
            assert audit["workflow_id"] == wf_id
            assert audit["copyright"] == "Copyrights reserved to 90Studio"
            assert audit["status"] in ("COUNTDOWN", "VALIDATING", "ATTACHING", "RUNNING")
        finally:
            client.post("/api/execute/abort")

    def test_get_audit_on_disk_fallback_by_execution_id_returns_200(self, client):
        """Verify on-disk audit log resolution by execution_id when cache is empty (F-M4-04)."""
        from kutomoto.server.app import execution_manager, BASE_DIR
        audit_dir = BASE_DIR / "data" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)

        wf_id = f"wf-disk-{uuid.uuid4()}"
        exec_id = f"exec-disk-{uuid.uuid4()}"
        filename = f"audit_{wf_id}_{exec_id}_20261105_120000.json"
        p = audit_dir / filename

        audit_content = {
            "workflow_id": wf_id,
            "execution_id": exec_id,
            "workflow_name": "Disk Retrieval Test",
            "timestamp_utc": "2026-11-05T12:00:00Z",
            "copyright": "Copyrights reserved to 90Studio",
            "execution_summary": {
                "total_steps": 2,
                "successful_steps": 2,
                "failed_steps": 0,
                "retried_steps": 0,
                "duration_seconds": 0.45,
                "final_status": "SUCCESS"
            }
        }
        p.write_text(json.dumps(audit_content), encoding="utf-8")

        try:
            # Clear memory cache
            execution_manager._audit_summaries.clear()
            execution_manager._last_audit_summary = None

            # Query by execution_id
            resp = client.get(f"/api/execute/audit/{exec_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["execution_id"] == exec_id
            assert data["workflow_id"] == wf_id
            assert data["status"] == "SUCCESS"
            assert data["copyright"] == "Copyrights reserved to 90Studio"
        finally:
            if p.exists():
                p.unlink()

    def test_get_audit_wildcard_glob_injection_blocked_returns_404(self, client):
        """Verify glob injection patterns like '*' or '?sensitive?' return 404 and leak nothing (F-M4-03)."""
        from kutomoto.server.app import execution_manager, BASE_DIR
        audit_dir = BASE_DIR / "data" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)

        p = audit_dir / f"audit_secret_bank_wf_exec999_20261105_120000.json"
        p.write_text(json.dumps({
            "workflow_id": "secret_bank_wf",
            "execution_id": "exec999",
            "workflow_name": "SECRET FINANCIAL AUDIT",
            "execution_summary": {"final_status": "SUCCESS"}
        }), encoding="utf-8")

        try:
            execution_manager._audit_summaries.clear()
            execution_manager._last_audit_summary = None

            resp = client.get("/api/execute/audit/*")
            assert resp.status_code == 404

            resp2 = client.get("/api/execute/audit/*secret*")
            assert resp2.status_code == 404
        finally:
            if p.exists():
                p.unlink()
