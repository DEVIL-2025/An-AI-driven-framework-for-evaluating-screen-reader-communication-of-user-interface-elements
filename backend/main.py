"""
FastAPI Main Application for AI-Powered Web Accessibility Testing Framework.
Exposes REST API endpoints for initiating audits, tracking progress, and retrieving reports.
"""

import os
import logging
from typing import List
from fastapi import FastAPI, HTTPException, status
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
