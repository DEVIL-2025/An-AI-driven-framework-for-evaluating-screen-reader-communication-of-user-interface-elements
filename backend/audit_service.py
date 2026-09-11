"""
Audit Service Layer for Accessibility Testing Framework.
Manages persistent audit records in PostgreSQL, orchestrates single-threaded
background audit execution via a controlled worker thread, and isolates report artifacts.
"""

import os
import uuid
import queue
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable

from backend.database import SessionLocal
from backend.models import Audit
from backend.schemas import AuditStatus, AuditError, AuditResponse

logger = logging.getLogger("AuditService")

# Base directory where per-audit output files are isolated
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_ROOT = os.path.join(BASE_DIR, "reports")


class AuditService:
    """
    Thread-safe service to manage accessibility audits backed by PostgreSQL.
    Guarantees only ONE Selenium + NVDA audit executes at a time by processing
    audits sequentially through a dedicated worker thread.
    """

    def __init__(
        self,
        audit_runner: Optional[Callable] = None,
        session_factory: Optional[Callable] = None,
    ):
        """
        Initialize the audit service.
        audit_runner and session_factory can be overridden for testing/mocking.
        """
        self._session_factory = session_factory or SessionLocal
        self._audit_runner = audit_runner or self._default_audit_runner
        self._queue: queue.Queue = queue.Queue()
        
        # Start the background worker thread
        self._worker_thread = threading.Thread(
            target=self._process_queue,
            daemon=True,
            name="AuditWorkerThread"
        )
        self._worker_thread.start()
        logger.info("AuditService initialized with PostgreSQL storage and worker thread.")

    @staticmethod
    def _default_audit_runner(url: str, tab_limit: int, enable_ai: bool, output_dir: str) -> Dict[str, Any]:
        """Invokes the existing run_automated_audit from main.py."""
        from main import run_automated_audit
        return run_automated_audit(
            url=url,
            tab_limit=tab_limit,
            enable_ai=enable_ai,
            output_dir=output_dir,
        )

    def create_audit(self, url: str, enable_ai: bool = True, tab_limit: int = 100) -> AuditResponse:
        """
        Create a new audit row in PostgreSQL with status='queued',
        queue it for background execution, and return immediately.
        """
        session = self._session_factory()
        try:
            audit = Audit(
                url=url,
                enable_ai=enable_ai,
                tab_limit=tab_limit,
                status=AuditStatus.QUEUED.value,
                created_at=datetime.now(timezone.utc),
            )
            session.add(audit)
            session.commit()
            session.refresh(audit)
            
            audit_id_str = str(audit.id)
            response = audit.to_schema()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create audit record in PostgreSQL: {e}", exc_info=True)
            raise
        finally:
            session.close()

        # Enqueue for background execution by single worker thread
        self._queue.put((audit_id_str, url, enable_ai, tab_limit))
        logger.info(f"Enqueued audit {audit_id_str} for {url} (status: queued)")

        return response

    def get_audit(self, audit_id: str) -> Optional[AuditResponse]:
        """Retrieve audit record from PostgreSQL by ID, or None if not found."""
        try:
            audit_uuid = uuid.UUID(audit_id)
        except (ValueError, TypeError):
            return None

        session = self._session_factory()
        try:
            record = session.query(Audit).filter(Audit.id == audit_uuid).first()
            if record:
                return record.to_schema()
            return None
        finally:
            session.close()

    def list_audits(self) -> List[AuditResponse]:
        """Return all audits from PostgreSQL sorted by creation time descending."""
        session = self._session_factory()
        try:
            records = session.query(Audit).order_by(Audit.created_at.desc()).all()
            return [r.to_schema() for r in records]
        finally:
            session.close()

    def clear_audits(self) -> int:
        """Delete all audits from PostgreSQL."""
        session = self._session_factory()
        try:
            deleted_count = session.query(Audit).delete(synchronize_session=False)
            session.commit()
            return deleted_count
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to clear audits: {e}")
            raise
        finally:
            session.close()

    def _process_queue(self) -> None:
        """Worker loop that executes audits one at a time."""
        while True:
            try:
                task = self._queue.get()
                if task is None:
                    break
                audit_id_str, url, enable_ai, tab_limit = task
                self._execute_single_audit(audit_id_str, url, enable_ai, tab_limit)
            except Exception as e:
                logger.error(f"Unexpected error in audit queue worker: {e}", exc_info=True)
            finally:
                self._queue.task_done()

    def _execute_single_audit(self, audit_id_str: str, url: str, enable_ai: bool, tab_limit: int) -> None:
        """Execute a single audit with isolated artifact storage and PostgreSQL persistence."""
        logger.info(f"Starting background audit execution for {audit_id_str} -> {url}")
        
        try:
            audit_uuid = uuid.UUID(audit_id_str)
        except Exception as e:
            logger.error(f"Invalid UUID in queue: {audit_id_str}: {e}")
            return

        # Transition status to RUNNING in PostgreSQL
        session = self._session_factory()
        try:
            record = session.query(Audit).filter(Audit.id == audit_uuid).first()
            if record:
                record.status = AuditStatus.RUNNING.value
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update status to RUNNING for {audit_id_str}: {e}")
        finally:
            session.close()

        # Prepare isolated report directory: reports/<audit_id>/
        audit_output_dir = os.path.join(REPORTS_ROOT, audit_id_str)
        os.makedirs(audit_output_dir, exist_ok=True)

        try:
            result = self._audit_runner(
                url=url,
                tab_limit=tab_limit,
                enable_ai=enable_ai,
                output_dir=audit_output_dir,
            )

            # Persist completed state and full result to PostgreSQL
            session = self._session_factory()
            try:
                record = session.query(Audit).filter(Audit.id == audit_uuid).first()
                if record:
                    record.status = AuditStatus.COMPLETED.value
                    record.completed_at = datetime.now(timezone.utc)
                    record.compliance_score = result.get("compliance_score")
                    record.total_elements_audited = result.get("total_elements_audited")
                    record.total_violations = result.get("total_violations")
                    record.severity_summary = result.get("severity_summary")
                    record.result = result
                    session.commit()
                logger.info(f"Audit {audit_id_str} completed and persisted successfully.")
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to persist completed audit {audit_id_str}: {e}")
            finally:
                session.close()

        except Exception as exc:
            logger.error(f"Audit {audit_id_str} failed with error: {exc}")
            structured_error = self._map_exception_to_error(exc)
            
            # Persist failed state to PostgreSQL
            session = self._session_factory()
            try:
                record = session.query(Audit).filter(Audit.id == audit_uuid).first()
                if record:
                    record.status = AuditStatus.FAILED.value
                    record.completed_at = datetime.now(timezone.utc)
                    record.error_code = structured_error.code
                    record.error_message = structured_error.message
                    session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to persist failed audit {audit_id_str}: {e}")
            finally:
                session.close()

    @staticmethod
    def _map_exception_to_error(exc: Exception) -> AuditError:
        """Classify exception into a structured, safe AuditError without exposing stack traces."""
        msg = str(exc)
        lowered = msg.lower()

        if "speech viewer" in lowered or "nvda" in lowered:
            return AuditError(
                code="NVDA_UNAVAILABLE",
                message="NVDA Speech Viewer is not available. Please ensure NVDA is running and the Speech Viewer window is open."
            )
        elif "chrome" in lowered or "webdriver" in lowered or "session" in lowered:
            return AuditError(
                code="BROWSER_ERROR",
                message="Chrome browser or WebDriver encountered an initialization or communication error."
            )
        elif "connection" in lowered or "timeout" in lowered or "unreachable" in lowered:
            return AuditError(
                code="TARGET_UNREACHABLE",
                message="Target website is unreachable or timed out during audit traversal."
            )
        else:
            return AuditError(
                code="AUDIT_FAILED",
                message=f"Audit execution encountered an error: {msg}"
            )


# Global singleton instance for the FastAPI application
audit_service = AuditService()
