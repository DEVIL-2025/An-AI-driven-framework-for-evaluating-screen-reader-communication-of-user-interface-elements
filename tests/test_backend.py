"""
Unit Tests for Backend API Layer.
Mocks all browser, Selenium, and NVDA components so tests run 100% offline and quickly.
"""

import sys
import os
import time
import threading
import unittest
from unittest.mock import patch, MagicMock

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app
from backend.audit_service import AuditService, audit_service
from backend.schemas import AuditStatus


class TestBackendAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.orig_runner = audit_service._audit_runner
        cls.mock_runner = MagicMock(return_value={
            "status": "completed",
            "url": "https://example.com",
            "analysis_type": "AI_ACCESSIBILITY_ANALYSIS",
            "compliance_score": 100.0,
            "total_elements_audited": 10,
            "total_violations": 0,
            "severity_summary": {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "INFO": 0},
            "analysis": {
                "analysis_type": "AI_ACCESSIBILITY_ANALYSIS",
                "analysis_status": "NO_VIOLATIONS",
                "summary": {
                    "total_elements_analyzed": 10,
                    "total_violations": 0,
                    "compliance_score": 100.0,
                    "severity_summary": {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "INFO": 0},
                },
                "violations": [],
            },
            "output_dir": None,
        })
        audit_service._audit_runner = cls.mock_runner

    @classmethod
    def tearDownClass(cls):
        audit_service._audit_runner = cls.orig_runner

    def setUp(self):
        audit_service._audit_runner = self.mock_runner
        self.client = TestClient(app)

    # 1. GET /api/health
    def test_1_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "accessibility-testing-api")

    # 2. POST /api/audits with valid URL
    def test_2_create_audit_valid_url(self):
        payload = {
            "url": "https://example.com/test-page",
            "enable_ai": True,
            "tab_limit": 50,
        }
        response = self.client.post("/api/audits", json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("audit_id", data)
        self.assertEqual(data["url"], "https://example.com/test-page")
        self.assertEqual(data["status"], "queued")
        self.assertEqual(data["tab_limit"], 50)
        self.assertTrue(data["enable_ai"])

    # 3. POST /api/audits with malformed URL
    def test_3_create_audit_malformed_url(self):
        payload = {"url": "not-a-valid-url"}
        response = self.client.post("/api/audits", json=payload)
        self.assertEqual(response.status_code, 422)  # Pydantic validation error

    # 4. POST /api/audits with unsupported scheme (ftp://, javascript:, file:)
    def test_4_create_audit_unsupported_scheme(self):
        for unsupported in ["ftp://ftp.example.com", "javascript:alert(1)", "file:///C:/test.html"]:
            response = self.client.post("/api/audits", json={"url": unsupported})
            self.assertEqual(response.status_code, 422)

    # 5. POST /api/audits with invalid tab_limit (<= 0 or > 500)
    def test_5_create_audit_invalid_tab_limit(self):
        # Negative limit
        res_neg = self.client.post("/api/audits", json={"url": "https://example.com", "tab_limit": -5})
        self.assertEqual(res_neg.status_code, 422)

        # Zero limit
        res_zero = self.client.post("/api/audits", json={"url": "https://example.com", "tab_limit": 0})
        self.assertEqual(res_zero.status_code, 422)

        # Exceeds maximum 500
        res_high = self.client.post("/api/audits", json={"url": "https://example.com", "tab_limit": 9999})
        self.assertEqual(res_high.status_code, 422)

    # 6. GET /api/audits/{unknown_id} returns 404
    def test_6_get_unknown_audit_id(self):
        response = self.client.get("/api/audits/non-existent-uuid-12345")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("detail", data)

    # 7. Successful audit service behavior using a MOCKED audit engine
    def test_7_successful_audit_mocked_engine(self):
        mock_audit_result = {
            "status": "completed",
            "url": "https://mocked.example.com",
            "analysis_type": "AI_ACCESSIBILITY_ANALYSIS",
            "compliance_score": 92.5,
            "total_elements_audited": 20,
            "total_violations": 1,
            "severity_summary": {"CRITICAL": 0, "MAJOR": 1, "MINOR": 0, "INFO": 0},
            "analysis": {
                "analysis_type": "AI_ACCESSIBILITY_ANALYSIS",
                "analysis_status": "COMPLETED",
                "summary": {
                    "total_elements_analyzed": 20,
                    "total_violations": 1,
                    "compliance_score": 92.5,
                    "severity_summary": {"CRITICAL": 0, "MAJOR": 1, "MINOR": 0, "INFO": 0},
                },
                "violations": [],
            },
            "output_dir": "reports/mock-id",
        }

        # Create isolated service with fast mock runner
        mock_runner = MagicMock(return_value=mock_audit_result)
        custom_service = AuditService(audit_runner=mock_runner)

        audit = custom_service.create_audit(
            url="https://mocked.example.com",
            enable_ai=True,
            tab_limit=25,
        )
        self.assertEqual(audit.status, AuditStatus.QUEUED)

        # Wait briefly for worker thread to process mock task
        for _ in range(50):
            record = custom_service.get_audit(audit.audit_id)
            if record and record.status == AuditStatus.COMPLETED:
                break
            time.sleep(0.05)

        record = custom_service.get_audit(audit.audit_id)
        self.assertIsNotNone(record)
        self.assertEqual(record.status, AuditStatus.COMPLETED)
        self.assertIsNotNone(record.result)
        self.assertEqual(record.result["compliance_score"], 92.5)
        self.assertIsNotNone(record.analysis)
        self.assertEqual(record.analysis["analysis_status"], "COMPLETED")
        self.assertEqual(record.analysis["summary"]["compliance_score"], 92.5)
        self.assertIsNotNone(record.completed_at)
        mock_runner.assert_called_once()

    # 8. Failed audit behavior using a MOCKED audit engine (e.g. NVDA not running)
    def test_8_failed_audit_mocked_engine(self):
        # Simulate NVDA unavailable RuntimeError
        mock_failing_runner = MagicMock(
            side_effect=RuntimeError("NVDA Speech Viewer is not available: Could not find Speech Viewer window.")
        )
        custom_service = AuditService(audit_runner=mock_failing_runner)

        audit = custom_service.create_audit(
            url="https://failing.example.com",
            enable_ai=True,
            tab_limit=10,
        )

        for _ in range(50):
            record = custom_service.get_audit(audit.audit_id)
            if record and record.status == AuditStatus.FAILED:
                break
            time.sleep(0.05)

        record = custom_service.get_audit(audit.audit_id)
        self.assertIsNotNone(record)
        self.assertEqual(record.status, AuditStatus.FAILED)
        self.assertIsNotNone(record.error)
        self.assertEqual(record.error.code, "NVDA_UNAVAILABLE")
        self.assertIn("NVDA Speech Viewer is not available", record.error.message)

    # 9. enable_ai=false is passed correctly
    def test_9_enable_ai_false_passed_correctly(self):
        mock_runner = MagicMock(return_value={"status": "completed"})
        custom_service = AuditService(audit_runner=mock_runner)

        audit = custom_service.create_audit(
            url="https://no-ai.example.com",
            enable_ai=False,
            tab_limit=10,
        )

        for _ in range(50):
            record = custom_service.get_audit(audit.audit_id)
            if record and record.status == AuditStatus.COMPLETED:
                break
            time.sleep(0.05)

        self.assertFalse(audit.enable_ai)
        # Verify mock received enable_ai=False
        _, kwargs = mock_runner.call_args
        self.assertFalse(kwargs["enable_ai"])

    # 10. Audit IDs are unique
    def test_10_unique_audit_ids(self):
        ids = set()
        for i in range(10):
            res = self.client.post("/api/audits", json={"url": f"https://example.com/page-{i}"})
            data = res.json()
            ids.add(data["audit_id"])
        self.assertEqual(len(ids), 10)

    # 11. Audit status transitions work correctly (queued -> running -> completed)
    def test_11_status_transitions(self):
        started_event = threading.Event()
        finish_event = threading.Event()

        def controlled_runner(url, tab_limit, enable_ai, output_dir):
            started_event.set()
            finish_event.wait(timeout=5)
            return {"status": "completed"}

        custom_service = AuditService(audit_runner=controlled_runner)
        audit = custom_service.create_audit(url="https://transitions.example.com")
        self.assertEqual(audit.status, AuditStatus.QUEUED)

        # Wait until it enters RUNNING
        started_event.wait(timeout=2)
        running_record = custom_service.get_audit(audit.audit_id)
        self.assertEqual(running_record.status, AuditStatus.RUNNING)

        # Let it finish
        finish_event.set()
        time.sleep(0.1)

        completed_record = custom_service.get_audit(audit.audit_id)
        self.assertEqual(completed_record.status, AuditStatus.COMPLETED)

    # 12. GET /api/audits returns list of created audits
    def test_12_list_audits(self):
        res = self.client.get("/api/audits")
        self.assertEqual(res.status_code, 200)
        audits_list = res.json()
        self.assertIsInstance(audits_list, list)
        self.assertTrue(len(audits_list) > 0)

    # 13. Verify public API response contract has url, status, analysis_type, analysis and no internal leakages
    def test_13_public_api_response_contract(self):
        # Create audit and wait for completion with mock runner
        res = self.client.post("/api/audits", json={"url": "https://contract-test.example.com"})
        self.assertEqual(res.status_code, 201)
        audit_id = res.json()["audit_id"]

        # Poll until complete
        for _ in range(50):
            res_get = self.client.get(f"/api/audits/{audit_id}")
            if res_get.status_code == 200 and res_get.json().get("status") == "completed":
                break
            time.sleep(0.05)

        res_final = self.client.get(f"/api/audits/{audit_id}")
        self.assertEqual(res_final.status_code, 200)
        data = res_final.json()

        # 1. Required public fields present
        self.assertIn("url", data)
        self.assertEqual(data["url"], "https://contract-test.example.com")
        self.assertIn("status", data)
        self.assertEqual(data["status"], "completed")
        self.assertIn("analysis_type", data)
        self.assertEqual(data["analysis_type"], "AI_ACCESSIBILITY_ANALYSIS")
        self.assertIn("analysis", data)
        self.assertIsInstance(data["analysis"], dict)

        # 2. Verify analysis retains all its fields untouched
        analysis = data["analysis"]
        self.assertIn("summary", analysis)
        self.assertIn("violations", analysis)
        self.assertIn("analysis_status", analysis)
        self.assertIn("analysis_type", analysis)

        # 3. Verify public API response DOES NOT leak internal fields at the top level
        self.assertNotIn("output_dir", data)
        self.assertNotIn("compliance_score", data)
        self.assertNotIn("severity_summary", data)
        self.assertNotIn("total_violations", data)
        self.assertNotIn("total_elements_audited", data)


    # 14. DELETE /api/audits clears history from database
    def test_14_clear_audits_deletes_from_database(self):
        # Create an audit
        res_create = self.client.post("/api/audits", json={"url": "https://clear-test.example.com"})
        self.assertEqual(res_create.status_code, 201)

        # Confirm audits exist
        res_list = self.client.get("/api/audits")
        self.assertTrue(len(res_list.json()) > 0)

        # Call DELETE /api/audits
        res_del = self.client.delete("/api/audits")
        self.assertEqual(res_del.status_code, 200)
        data = res_del.json()
        self.assertIn("deleted_count", data)
        self.assertIn("message", data)

        # Verify database is now empty
        res_after = self.client.get("/api/audits")
        self.assertEqual(res_after.status_code, 200)
        self.assertEqual(len(res_after.json()), 0)

    # 15. GET /api/audits/{audit_id}/download returns JSON with understandable website-specific filename
    def test_15_download_report_with_understandable_filename(self):
        from backend.main import generate_report_filename

        # 1. Verify filename generation logic for specific websites
        fn_irctc = generate_report_filename("https://www.irctc.co.in/nget/train-search", "2026-09-29T12:00:00Z")
        self.assertEqual(fn_irctc, "irctc-co-in_nget-train-search_ai_accessibility_report_2026-09-29.json")

        fn_flipkart = generate_report_filename("https://www.flipkart.com/", "2026-09-29T12:00:00Z")
        self.assertEqual(fn_flipkart, "flipkart-com_ai_accessibility_report_2026-09-29.json")

        fn_makaut = generate_report_filename("https://makautwb.ac.in/", "2026-09-29T12:00:00Z")
        self.assertEqual(fn_makaut, "makautwb-ac-in_ai_accessibility_report_2026-09-29.json")

        # 2. Test download endpoint with completed audit
        res_create = self.client.post("/api/audits", json={"url": "https://www.flipkart.com"})
        self.assertEqual(res_create.status_code, 201)
        audit_id = res_create.json()["audit_id"]

        # Wait for worker thread to complete the audit
        max_wait = 10.0
        start = time.time()
        while time.time() - start < max_wait:
            res_poll = self.client.get(f"/api/audits/{audit_id}")
            if res_poll.json()["status"] == "completed":
                break
            time.sleep(0.1)

        # Download the report
        res_down = self.client.get(f"/api/audits/{audit_id}/download")
        self.assertEqual(res_down.status_code, 200)
        self.assertIn("Content-Disposition", res_down.headers)
        self.assertIn("flipkart-com_ai_accessibility_report_", res_down.headers["Content-Disposition"])
        self.assertTrue(res_down.headers["Content-Disposition"].endswith('.json"'))

        # Verify payload is valid JSON report
        payload = res_down.json()
        self.assertEqual(payload["analysis_type"], "AI_ACCESSIBILITY_ANALYSIS")
        self.assertEqual(payload["url"], "https://www.flipkart.com")
        self.assertEqual(payload["audit_id"], audit_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
