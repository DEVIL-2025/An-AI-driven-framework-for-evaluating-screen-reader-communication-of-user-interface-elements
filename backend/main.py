"""
FastAPI Main Application for AI-Powered Web Accessibility Testing Framework.
Exposes REST API endpoints for initiating audits, tracking progress, and retrieving reports.
"""

import os
import re
import json
import logging
from typing import List, Optional
from datetime import datetime, timezone
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
from backend.schemas import (
    AuditCreateRequest,
    AuditResponse,
    HealthResponse,
)
from backend.database import init_db, check_db_connection
from backend.audit_service import audit_service

# Configure API logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AccessibilityAPI")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Starting up FastAPI application; ensuring database tables exist...")
    try:
        init_db()
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
    yield
    logger.info("Shutting down FastAPI application.")


# Initialize FastAPI application
app = FastAPI(
    title="AI-Powered Web Accessibility Testing API",
    description=(
        "REST API wrapping the automated Selenium + NVDA Screen Reader synchronization "
        "and WCAG 2.1/2.2 audit engine with Google Gemini AI remediation."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS for local development (React / Vite)
frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
allowed_origins = [
    origin.strip()
    for origin in frontend_origin.split(",")
    if origin.strip()
]
# Ensure standard Vite & CRA default ports are allowed locally
for default_origin in ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]:
    if default_origin not in allowed_origins:
        allowed_origins.append(default_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/api/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Health check",
    description="Verify that the backend API service and database are alive and healthy."
)
def get_health():
    """Health check endpoint reporting API and PostgreSQL status."""
    is_db_connected = check_db_connection()
    return HealthResponse(
        status="ok",
        service="accessibility-testing-api",
        database="connected" if is_db_connected else "disconnected",
    )


@app.post(
    "/api/audits",
    response_model=AuditResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Audits"],
    summary="Initiate an accessibility audit",
    description=(
        "Enqueue a new accessibility audit for a target website. "
        "Returns immediately with status='queued' and an assigned audit_id. "
        "Audits run sequentially on the server to prevent screen reader focus conflicts."
    )
)
def create_audit(request: AuditCreateRequest):
    """Enqueue a new accessibility audit for the provided URL."""
    logger.info(f"Received audit request for URL: {request.url} (enable_ai={request.enable_ai}, tab_limit={request.tab_limit})")
    
    created_audit = audit_service.create_audit(
        url=request.url,
        enable_ai=request.enable_ai,
        tab_limit=request.tab_limit,
    )
    return created_audit


@app.get(
    "/api/audits/{audit_id}",
    response_model=AuditResponse,
    status_code=status.HTTP_200_OK,
    tags=["Audits"],
    summary="Get audit status and results",
    description="Retrieve the current status (queued, running, completed, failed) and report for an audit."
)
def get_audit(audit_id: str):
    """Retrieve audit status or final report by ID."""
    record = audit_service.get_audit(audit_id)
    if not record:
        logger.warning(f"Audit not found: {audit_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit with ID '{audit_id}' was not found."
        )
    return record


def generate_report_filename(url: str, timestamp: Optional[str] = None) -> str:
    """Generate an understandable, human-readable filename for an AI accessibility report."""
    site_slug = "website"
    try:
        clean_url = url if "://" in url else f"https://{url}"
        parsed = urlparse(clean_url)
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        clean_host = re.sub(r'[^a-z0-9_-]', '-', host).strip('-')
        clean_path = re.sub(r'[^a-z0-9_-]', '-', (parsed.path or "").lower()).strip('-')
        if clean_path and len(clean_path) <= 30:
            site_slug = f"{clean_host}_{clean_path}"
        elif clean_host:
            site_slug = clean_host
    except Exception:
        site_slug = "website"

    date_str = ""
    if timestamp:
        try:
            date_str = timestamp.split("T")[0]
        except Exception:
            pass
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return f"{site_slug}_ai_accessibility_report_{date_str}.json"


@app.get(
    "/api/audits/{audit_id}/download",
    status_code=status.HTTP_200_OK,
    tags=["Audits"],
    summary="Download AI accessibility report JSON",
    description="Download the full AI accessibility analysis report for the specified audit with an understandable, website-specific filename."
)
def download_audit_report(audit_id: str):
    """Download AI accessibility report JSON for an audit."""
    record = audit_service.get_audit(audit_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit with ID '{audit_id}' was not found."
        )
    analysis_data = record.analysis or record.result
    if not analysis_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI report for audit '{audit_id}' is not yet available."
        )

    # Ensure top-level identifiers are present in downloaded payload
    report_to_export = {
        **analysis_data,
        "audit_id": record.audit_id or audit_id,
        "url": record.url,
        "created_at": record.created_at,
    }

    filename = generate_report_filename(record.url, record.created_at)
    return Response(
        content=json.dumps(report_to_export, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        }
    )


@app.get(
    "/api/audits",
    response_model=List[AuditResponse],
    status_code=status.HTTP_200_OK,
    tags=["Audits"],
    summary="List all audits",
    description="Return a list of all audits stored in the in-memory service layer."
)
def list_audits():
    """List all created audits."""
    return audit_service.list_audits()


@app.delete(
    "/api/audits",
    status_code=status.HTTP_200_OK,
    tags=["Audits"],
    summary="Clear audit history",
    description="Delete all audit records from PostgreSQL database."
)
def clear_audits():
    """Clear all audit history records from the database."""
    deleted_count = audit_service.clear_audits()
    logger.info(f"Cleared {deleted_count} historical audit records from PostgreSQL.")
    return {"message": f"Successfully cleared {deleted_count} audit records.", "deleted_count": deleted_count}
