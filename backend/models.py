"""
SQLAlchemy ORM Models for PostgreSQL Database.
Defines the Audit model using native UUID and JSONB types.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from backend.database import Base
from backend.schemas import AuditResponse, AuditStatus, AuditError


class Audit(Base):
    """Represents an accessibility audit record in PostgreSQL."""

    __tablename__ = "audits"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique UUID primary key identifier for the audit"
    )
    url = Column(
        Text,
        nullable=False,
        doc="Target website URL tested"
    )
    status = Column(
        String(50),
        nullable=False,
        default=AuditStatus.QUEUED.value,
        index=True,
        doc="Lifecycle status: queued, running, completed, failed"
    )
    enable_ai = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether Gemini AI enrichment was enabled"
    )
    tab_limit = Column(
        Integer,
        nullable=False,
        default=100,
        doc="Maximum tab steps traversed"
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="Timestamp when the audit was created"
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when the audit finished execution"
    )
    compliance_score = Column(
        Float,
        nullable=True,
        doc="Overall WCAG compliance percentage (0.0 to 100.0)"
    )
    total_elements_audited = Column(
        Integer,
        nullable=True,
        doc="Number of interactive DOM elements audited"
    )
    total_violations = Column(
        Integer,
        nullable=True,
        doc="Total number of WCAG violations detected"
    )
    severity_summary = Column(
        JSONB,
        nullable=True,
        doc="Severity counts breakdown: CRITICAL, MAJOR, MINOR, INFO"
    )
    result = Column(
        JSONB,
        nullable=True,
        doc="Full structured accessibility audit and AI remediation report"
    )
    error_code = Column(
        String(100),
        nullable=True,
        doc="Error code if audit failed (e.g. NVDA_UNAVAILABLE)"
    )
    error_message = Column(
        Text,
        nullable=True,
        doc="Clean, safe error message if audit failed"
    )

    def to_schema(self) -> AuditResponse:
        """Convert SQLAlchemy model instance to Pydantic AuditResponse schema."""
        error_obj: Optional[AuditError] = None
        if self.error_code and self.error_message:
            error_obj = AuditError(code=self.error_code, message=self.error_message)

        # Extract clean analysis object if available, handling both new and legacy formats gracefully
        analysis_data: Optional[Dict[str, Any]] = None
        if isinstance(self.result, dict):
            if "analysis" in self.result and isinstance(self.result["analysis"], dict):
                analysis_data = self.result["analysis"]
            elif "result" in self.result and isinstance(self.result["result"], dict):
                analysis_data = self.result["result"]
            elif "ai_report" in self.result and isinstance(self.result["ai_report"], dict):
                analysis_data = self.result["ai_report"]
            else:
                analysis_data = self.result

        analysis_type = "AI_ACCESSIBILITY_ANALYSIS"
        if isinstance(self.result, dict) and "analysis_type" in self.result:
            analysis_type = self.result["analysis_type"]

        return AuditResponse(
            audit_id=str(self.id),
            url=self.url,
            status=AuditStatus(self.status),
            analysis_type=analysis_type,
            created_at=self.created_at.isoformat() if self.created_at else "",
            completed_at=self.completed_at.isoformat() if self.completed_at else None,
            enable_ai=self.enable_ai,
            tab_limit=self.tab_limit,
            analysis=analysis_data,
            result=self.result,
            error=error_obj,
        )
