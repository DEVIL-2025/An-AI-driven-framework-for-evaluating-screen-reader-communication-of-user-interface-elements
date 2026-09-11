"""
Pydantic Request and Response Schemas for Accessibility Audit API.
"""

from enum import Enum
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator


class AuditStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def validate_web_url(url: str) -> str:
    """Validate that a URL has a valid HTTP/HTTPS scheme and hostname."""
    if not isinstance(url, str):
        raise ValueError("URL must be a string.")
    
    clean_url = url.strip()
    if not clean_url:
        raise ValueError("URL cannot be empty.")

    parsed = urlparse(clean_url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(
            f"Unsupported URL scheme '{parsed.scheme}'. Only 'http' and 'https' are allowed."
        )

    if not parsed.netloc:
        raise ValueError("URL must include a valid host or domain name.")

    return clean_url


class AuditCreateRequest(BaseModel):
    """Payload to start a new web accessibility audit."""
    url: str = Field(
        ...,
        description="Target web page URL to audit (must start with http:// or https://)",
        example="https://example.com"
    )
    enable_ai: bool = Field(
        default=True,
        description="Whether to run Gemini AI enrichment for remediation code guidance"
    )
    tab_limit: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Maximum keyboard navigation (Tab/Shift+Tab) steps to traverse (1-500)"
    )

    @field_validator("url")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_web_url(v)


class AuditError(BaseModel):
    """Structured error payload for failed audits or API errors."""
    code: str = Field(..., description="Machine-readable error code", example="NVDA_UNAVAILABLE")
    message: str = Field(..., description="Human-readable explanation of failure", example="NVDA Speech Viewer is not running.")


class AuditResponse(BaseModel):
    """Detailed status and result representation of an accessibility audit."""
    url: str = Field(..., description="Target web page URL")
    status: AuditStatus = Field(..., description="Current status of the audit (queued, running, completed, failed)")
    analysis_type: str = Field(default="AI_ACCESSIBILITY_ANALYSIS", description="Analysis engine type")
    analysis: Optional[Dict[str, Any]] = Field(default=None, description="Clean authoritative AI accessibility analysis report")
    audit_id: Optional[str] = Field(default=None, description="Unique UUID identifier for this audit")
    created_at: Optional[str] = Field(default=None, description="ISO 8601 timestamp when the audit was created")
    completed_at: Optional[str] = Field(default=None, description="ISO 8601 timestamp when audit finished")
    enable_ai: bool = Field(default=True, description="Whether AI enrichment was requested")
    tab_limit: int = Field(default=100, description="Tab traversal limit configured")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Full internal audit payload for backwards compatibility")
    error: Optional[AuditError] = Field(default=None, description="Structured error if audit failed")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(default="ok", example="ok")
    service: str = Field(default="accessibility-testing-api", example="accessibility-testing-api")
    database: Optional[str] = Field(default="connected", example="connected")
