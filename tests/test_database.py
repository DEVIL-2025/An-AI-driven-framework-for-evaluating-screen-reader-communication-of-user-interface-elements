"""
Database Integration Tests for PostgreSQL Accessibility Audits.
Validates SQLAlchemy models, JSONB serialization, UUID generation,
and audit lifecycle persistence.
"""

import os
import sys
import uuid
import unittest
from datetime import datetime, timezone

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, init_db, check_db_connection
from backend.models import Audit
from backend.schemas import AuditStatus, AuditError


class TestPostgreSQLDatabase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Ensure database tables exist before testing."""
        init_db()

    def setUp(self):
        self.session = SessionLocal()

    def tearDown(self):
        try:
            self.session.query(Audit).delete()
            self.session.commit()
        except Exception:
            self.session.rollback()
        finally:
            self.session.close()

    # 1. Test database connectivity
    def test_1_db_connectivity(self):
        self.assertTrue(check_db_connection())

    # 2. Test Audit creation and UUID generation
    def test_2_create_audit_model(self):
        audit = Audit(
            url="https://db-test.example.com",
            status=AuditStatus.QUEUED.value,
            enable_ai=True,
            tab_limit=75,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(audit)
        self.session.commit()
        self.session.refresh(audit)

        self.assertIsInstance(audit.id, uuid.UUID)
        self.assertEqual(audit.url, "https://db-test.example.com")
        self.assertEqual(audit.status, "queued")
        self.assertEqual(audit.tab_limit, 75)
        self.assertTrue(audit.enable_ai)

    # 3. Test retrieving audit record by UUID
    def test_3_retrieve_audit_record(self):
        test_id = uuid.uuid4()
        audit = Audit(
            id=test_id,
            url="https://retrieve-test.example.com",
            status=AuditStatus.QUEUED.value,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(audit)
        self.session.commit()

        retrieved = self.session.query(Audit).filter(Audit.id == test_id).first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.url, "https://retrieve-test.example.com")
        self.assertEqual(retrieved.id, test_id)

    # 4. Test updating audit status
    def test_4_update_audit_status(self):
        audit = Audit(
            url="https://status-update.example.com",
            status=AuditStatus.QUEUED.value,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(audit)
        self.session.commit()
        audit_id = audit.id

        # Update to RUNNING
        audit.status = AuditStatus.RUNNING.value
        self.session.commit()

        reloaded = self.session.query(Audit).filter(Audit.id == audit_id).first()
        self.assertEqual(reloaded.status, "running")

    # 5. Test JSONB result round-trip and completed state
    def test_5_store_completed_report_jsonb(self):
        sample_result = {
            "url": "https://jsonb-test.example.com",
            "compliance_score": 87.5,
            "total_elements_audited": 16,
            "total_violations": 2,
            "severity_summary": {
                "CRITICAL": 1,
                "MAJOR": 1,
                "MINOR": 0,
                "INFO": 0,
            },
            "report": {
                "violations": [
                    {
                        "rule_id": "WCAG 4.1.2",
                        "title": "Unlabelled button",
                        "severity": "CRITICAL",
                    }
                ]
            },
            "ai_report": {
                "ai_status": "COMPLETED",
                "enriched_violations": [
                    {
                        "original_finding": {"rule_id": "WCAG 4.1.2"},
                        "ai_analysis": {
                            "explanation": "Button lacks accessible name.",
                            "developer_guidance": "<button aria-label='[Name]'>",
                        },
                    }
                ],
            },
        }

        audit = Audit(
            url="https://jsonb-test.example.com",
            status=AuditStatus.COMPLETED.value,
            compliance_score=87.5,
            total_elements_audited=16,
            total_violations=2,
            severity_summary=sample_result["severity_summary"],
            result=sample_result,
            completed_at=datetime.now(timezone.utc),
        )
        self.session.add(audit)
        self.session.commit()
        audit_id = audit.id

        fetched = self.session.query(Audit).filter(Audit.id == audit_id).first()
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.compliance_score, 87.5)
        self.assertEqual(fetched.total_violations, 2)
        self.assertIsInstance(fetched.result, dict)
        self.assertEqual(fetched.result["ai_report"]["ai_status"], "COMPLETED")
        self.assertEqual(
            fetched.result["report"]["violations"][0]["rule_id"],
            "WCAG 4.1.2"
        )

        # Test to_schema() conversion
        schema = fetched.to_schema()
        self.assertEqual(schema.compliance_score if hasattr(schema, 'compliance_score') else schema.result['compliance_score'], 87.5)
        self.assertEqual(schema.status, AuditStatus.COMPLETED)
        # Verify legacy format gracefully populated analysis field
        self.assertIsNotNone(schema.analysis)
        self.assertEqual(schema.analysis.get("ai_status"), "COMPLETED")

    # 5b. Test modern clean analysis JSONB format
    def test_5b_store_modern_analysis_jsonb(self):
        clean_result = {
            "status": "completed",
            "url": "https://clean-test.example.com",
            "compliance_score": 95.0,
            "total_elements_audited": 10,
            "total_violations": 1,
            "severity_summary": {"CRITICAL": 0, "MAJOR": 1, "MINOR": 0, "INFO": 0},
            "analysis": {
                "analysis_type": "AI_ACCESSIBILITY_ANALYSIS",
                "analysis_status": "COMPLETED",
                "url": "https://clean-test.example.com",
                "summary": {
                    "total_elements_analyzed": 10,
                    "total_violations": 1,
                    "compliance_score": 95.0,
                    "severity_summary": {"CRITICAL": 0, "MAJOR": 1, "MINOR": 0, "INFO": 0},
                },
                "violations": [
                    {
                        "violation_id": "AI-001",
                        "rule_id": "WCAG 4.1.2",
                        "severity": "MAJOR",
                        "title": "Unlabelled button",
                    }
                ],
                "ai_metadata": {"provider": "GeminiProvider", "model": "gemini-2.5-flash"},
            },
            "output_dir": "reports/clean-test",
        }

        audit = Audit(
            url="https://clean-test.example.com",
            status=AuditStatus.COMPLETED.value,
            compliance_score=95.0,
            total_elements_audited=10,
            total_violations=1,
            severity_summary=clean_result["severity_summary"],
            result=clean_result,
            completed_at=datetime.now(timezone.utc),
        )
        self.session.add(audit)
        self.session.commit()
        audit_id = audit.id

        fetched = self.session.query(Audit).filter(Audit.id == audit_id).first()
        self.assertIsNotNone(fetched)
        schema = fetched.to_schema()
        self.assertEqual(schema.status, AuditStatus.COMPLETED)
        self.assertIsNotNone(schema.analysis)
        self.assertEqual(schema.analysis["analysis_status"], "COMPLETED")
        self.assertEqual(schema.analysis["summary"]["compliance_score"], 95.0)
        self.assertEqual(len(schema.analysis["violations"]), 1)

    # 6. Test storing failed audit with error code and message
    def test_6_store_failed_audit(self):
        audit = Audit(
            url="https://failed-audit.example.com",
            status=AuditStatus.FAILED.value,
            error_code="NVDA_UNAVAILABLE",
            error_message="NVDA Speech Viewer is not running.",
            completed_at=datetime.now(timezone.utc),
        )
        self.session.add(audit)
        self.session.commit()
        audit_id = audit.id

        fetched = self.session.query(Audit).filter(Audit.id == audit_id).first()
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.status, "failed")
        self.assertEqual(fetched.error_code, "NVDA_UNAVAILABLE")
        self.assertEqual(fetched.error_message, "NVDA Speech Viewer is not running.")

        schema = fetched.to_schema()
        self.assertIsNotNone(schema.error)
        self.assertEqual(schema.error.code, "NVDA_UNAVAILABLE")
        self.assertEqual(schema.error.message, "NVDA Speech Viewer is not running.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
