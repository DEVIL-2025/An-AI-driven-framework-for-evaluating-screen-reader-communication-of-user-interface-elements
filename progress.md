# Project Progress

## Project Goal

Build a **local web-based accessibility testing application** where a user can enter any website URL, run an automated accessibility audit using Selenium + NVDA, analyze the results with pure Gemini AI authority, persist audits to PostgreSQL, and view/interact with the report and past audits through a modern React + Vite + Tailwind interface.

---

# Completed Components (1 – 16)

## 1. Selenium Website Traversal — DONE
- Open a user-provided URL in Google Chrome via Selenium WebDriver
- Bidirectional keyboard navigation: forward `Tab` traversal & reverse `Shift + Tab` traversal
- Collect DOM/element properties (tag, href, aria attributes, expected roles, text, coordinates)
- Configurable keyboard traversal limit (`tab_limit`, default: 100, range: 1–500)

## 2. NVDA Integration — DONE
- Integrates with NVDA Speech Viewer via Windows Win32 API (`pywinauto`)
- Connects to Speech Viewer window dynamically
- Captures newly spoken NVDA text events
- Filters Speech Viewer timestamps and background browser chrome noise
- *Note:* NVDA + Speech Viewer runs alongside the tests.

## 3. NVDA Parser — DONE
- Converts raw screen reader speech strings into structured `AccessibilityEvent` objects
- Extracts `name`, `role`, `value`, `description`, `level`, `attributes`, and `raw_text`
- Comprehensive landmark and widget role support (links, buttons, edits, graphics, combos, dialogs)
- Fully covered by 29 automated unit tests

## 4. Selenium ↔ NVDA Synchronization — DONE
- Temporal and step-based correlation of DOM elements with screen reader announcements
- Evaluates:
  - Exact/normalized name match
  - Role match and compatibility
  - Unlabelled elements announced by screen reader
  - Role mismatches
  - Screen reader silence (`NVDA_SILENT`)
- Produces ground-truth `synchronized_output.json`

## 5. Pure AI Accessibility Analyzer (Gemini Authority) — DONE
- **Deterministic analyzer removed**: Google Gemini AI is the sole authority for violation detection, WCAG criteria mapping, severity classification, and remediation guidance
- Token-efficient evidence compaction: summarizes DOM properties, NVDA speech, and synchronization flags into factual observations
- Dynamic batching logic with auto-retries for large web audits
- Validates all AI findings against Pydantic schemas (`AIViolationFinding`, `AIAccessibilityAnalysisReport`)
- Preserves ground-truth evidence: DOM attributes, NVDA speech, and synchronization comparison are bound directly by the engine, preventing AI hallucination
- Weighted severity scoring algorithm (`CRITICAL: 15`, `MAJOR: 8`, `MINOR: 3`, `INFO: 1`) produces a normalized `compliance_score` (0.0–100.0%)

## 6. Gemini LLM Provider — DONE
- Direct HTTP integration with Google Gemini REST API (`gemini-2.5-flash`, `gemini-3.5-flash-lite`)
- Mock provider fallback for deterministic, offline testing
- Environment variable configuration via `.env` (`GEMINI_API_KEY`, `GEMINI_MODEL`)

## 7. PostgreSQL Database & Neon Integration — DONE
- PostgreSQL `audits` table using native `UUID` and `JSONB`
- SQLAlchemy ORM model `Audit` in `backend/models.py`
- Stores indexed scalars for fast queries: `url`, `status`, `compliance_score`, `total_violations`, `total_elements_audited`, `created_at`, `completed_at`
- Stores structured `severity_summary` and complete `analysis` report in JSONB
- Fully covered by 13 database CRUD and JSONB round-trip tests

## 8. Backend REST API (FastAPI) — DONE
- FastAPI service in `backend/main.py`
- Endpoints:
  - `GET /api/health` — System health and PostgreSQL connectivity check
  - `POST /api/audits` — Submits and enqueues an audit (`url`, `tab_limit`, `enable_ai`)
  - `GET /api/audits/{audit_id}` — Polls status or retrieves complete audit report
  - `GET /api/audits` — Lists all historical audits ordered newest first
- CORS middleware configured for React/Vite development server (`http://localhost:5173`)
- Pydantic v2 schemas in `backend/schemas.py` with URL sanitization and `tab_limit` validation (1–500)

## 9. Background Worker Queue (AuditService) — DONE
- In-memory thread-safe queue (`queue.Queue`) processed sequentially by a dedicated background worker thread
- Eliminates screen reader focus collisions (one browser audit active at a time)
- Updates audit lifecycle: `queued` $\rightarrow$ `running` $\rightarrow$ `completed` / `failed`
- Maps unhandled exceptions safely to structured `error_code` and `error_message`

## 10. Report System & Clean API Contract — DONE
- Clean application-level contract frozen in `AuditResponse`
- Consolidated duplicate `result` and `ai_report` fields into a single authoritative `analysis` object
- Internal scalar metrics preserved for `AuditService` and database query efficiency
- Internal server paths (`output_dir`) removed from public API responses
- Zero leakage of summary fields at the top level — cleanly accessed via `analysis.summary`

## 11. React + Vite + Tailwind Frontend Setup — DONE
- Frontend application initialized in isolated `frontend/` directory
- Built on React 19, Vite 8, and Tailwind CSS
- Accessible dark navy design system with high-contrast typography and focus states

## 12. Static Dashboard UI — DONE
- Header with branding, project description, and view toggle
- Prominent "Test a Website" audit input form
- Four summary metric cards: Compliance Score, Total Violations, Elements Analyzed, Audit Status
- 4-level Severity Distribution overview (`CRITICAL`, `MAJOR`, `MINOR`, `INFO`)
- Clean empty states when awaiting first audit

## 13. Violation Details & Evidence UI — DONE
- Accessible expandable `<ViolationCard />` component with `aria-expanded` and keyboard navigation
- Displays: Title, Severity badge, WCAG rule, Confidence, Violation ID
- Technical breakdown: AI description, User impact, AI rationale, WCAG normative context, Remediation recommendation, and Developer code fix container
- `<EvidenceSection />`: Three dedicated technical cards for **Selenium DOM**, **NVDA Screen Reader Announcement** (with raw speech stream), and **Synchronization Comparison Status** (name match / role match indicators without relying on color alone)

## 14. Tab Limit Option — DONE
- Controlled number input in the audit form (`1` to `500` steps, default: `100`)
- Accessible labels, range indicators, and inline validation warnings
- Sent directly in API payload as `tab_limit`

## 15. Frontend ↔ FastAPI Integration — DONE
- Frontend API service in `frontend/src/services/api.js` using native `fetch()`
- Centralized base URL via `VITE_API_BASE_URL` in `frontend/.env`
- Seamless polling mechanism: displays animated state transitions (`"Audit queued on server..."`, `"Auditing browser & capturing NVDA speech..."`)
- Populates dashboard with live API data from `audit.analysis`
- Graceful error banner with dismiss and retry handling

## 16. Audit History Interface — DONE
- Dedicated Audit History view accessible via Header button
- Calls `GET /api/audits` to fetch all PostgreSQL records ordered newest first
- Responsive table & card layout showing Target URL, Status badge, Score, Violations, Elements, and Localized Timestamp
- "View Audit" action calls `GET /api/audits/{audit_id}` to load any historical audit into the main dashboard and violation viewer
- Easy navigation back to the live audit dashboard via "Back to Dashboard"

## 17. Unified Multimodal Evidence Package & Correlation (Phase 3A) — DONE
- `tools/evidence_correlator.py`: Multi-signal correlation engine matching dynamic Selenium elements against static DOM snapshot elements using weighted signals (id, name, type, normalized text, href, ARIA roles, class overlap, CSS path).
- Produces `unified_evidence_package.json` correlating DOM structure, visual screenshot metadata, and NVDA traversal telemetry.
- Preserves context (parent sections, landmarks, nearest headings, surrounding text) without pre-judging accessibility compliance.

## 18. Generic WCAG Reasoning Engine & Normative Adjudication — DONE
- Clear architectural separation between **Normative WCAG Violations** and **Accessibility Recommendations** (best practices, structural enhancements).
- Multi-gate adjudication engine evaluating:
  - **WCAG 2.4.4 (Link Purpose in Context)**: Accounts for enclosing container headings/context (Technique H80/G91). Does not promote generic link text into a violation if programmatic context is present.
  - **WCAG 1.1.1 (Image Semantics)**: Distinguishes between informative branding logos (genuine Level A violations when missing alt text) vs. decorative icons/badges (advisory recommendations, Technique H67) vs. child graphics in accessible parent controls.
  - **WCAG 2.4.1 (Bypass Blocks) & 1.3.1 (Headings)**: Missing `<main>` or `<h1>` are never automatically treated as normative failures unless true programmatic accessibility barriers exist.
- Deterministic deduction scoring model: `CRITICAL: -15.0`, `MAJOR: -8.0`, `MINOR: -3.0`, `INFO: 0.0`, with Recommendations carrying `0.0` penalty.
- Strict Pydantic model validation (`AINormativeBasis`) ensuring numeric SC identification, conformance levels, and evidence bases.

## 19. NVDA Traversal Synchronization & Pre-Traversal Speech Draining — DONE
- Resolved root-cause element desynchronization caused by Chrome page-load virtual buffer reading and "Automatic Say All on Page Load".
- Implemented 8-state explicit lifecycle model:
  `INITIALIZING` ➔ `PAGE_LOADING` ➔ `PAGE_LOAD_SPEECH` ➔ `NVDA_CAPTURE_READY` ➔ `BASELINE_ESTABLISHED` ➔ `TRAVERSAL_READY` ➔ `TRAVERSING` ➔ `TRAVERSAL_COMPLETE`.
- `NVDATextExtractor.drain_initial_speech()`: Adaptively monitors page-load speech until buffer stabilization, captures all accumulated text into an `initialization` metadata block (`phase: "PAGE_INITIALIZATION"`), and marks an authoritative baseline boundary.
- `NVDATextExtractor.capture_action_response(action_fn)`: Causal action-response synchronization taking a pre-action buffer mark before keystroke execution and capturing only fresh speech strictly succeeding that mark.
- Removed `body.click()` which previously activated the browse-mode buffer at arbitrary mouse coordinates.
- Fully covered by 13 automated synchronization lifecycle scenarios (`tests/test_nvda_synchronization.py`).
- **Comprehensive test suite**: 165 automated tests across all modules passing at 100%.

---

# Remaining Tasks (TODO)

## 20. Security & Reliability — NEXT
- Rate limiting / request throttling on `POST /api/audits`
- Strict timeout handling for unresponsive target websites or frozen browser instances
- Graceful worker thread shutdown on server termination
- Frontend React error boundary to capture unexpected render issues
- Ensure `.env` and sensitive credentials remain secure

## 21. PDF / HTML Report Export — TODO
- Downloadable standalone accessibility report (HTML / PDF format)
- Export audit findings and ground-truth NVDA evidence for developer QA teams

## 22. Final End-to-End System Verification — TODO
- End-to-end multi-site verification across diverse web structures (e-commerce, university portals, forms, SPAs)
- Complete pipeline verification:
  `URL Input → Browser Navigation → NVDA Capture → Synchronization → Gemini Analysis → PostgreSQL Persistence → React Dashboard → History`

## 23. Automatic NVDA Startup — LATER (Deferred)
- Optional Windows service or child process launcher to start NVDA and open Speech Viewer automatically if not already running.

---

# Final Roadmap Summary

1. Core Engine (Selenium + NVDA + Sync + Gemini) — **DONE**
2. Backend API (FastAPI REST Service) — **DONE**
3. PostgreSQL Persistence (Neon / Local DB) — **DONE**
4. Report Contract System — **DONE**
5. React + Vite + Tailwind Dashboard — **DONE**
6. Frontend ↔ Backend Integration — **DONE**
7. Audit History Interface — **DONE**
8. Unified Multimodal Evidence Correlation (Phase 3A) — **DONE**
9. Generic WCAG Reasoning Engine & Normative Adjudication — **DONE**
10. NVDA Traversal Synchronization & Pre-Traversal Speech Draining — **DONE**
11. Security & Reliability Hardening — **NEXT**
12. PDF / HTML Report Export — **TODO**
13. Final End-to-End Verification — **TODO**
14. Automatic NVDA Startup — **LATER**

---

# Development Rule

**Do not implement everything at once.**
Follow: **One component → implement → test → verify → move to the next.**

## Current Next Task
**Security & Reliability (Timeout safeguards, worker shutdown, error boundary)**
