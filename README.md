# AI-Powered Screen Reader Accessibility Testing System

An automated, website-independent digital accessibility testing pipeline that pairs **Selenium browser automation** with live **NVDA Screen Reader** speech capture, synchronized DOM/screen reader evidence compaction, and **Google Gemini AI** as the sole authority for accessibility violation detection, WCAG criteria mapping, severity scoring, user impact analysis, and developer code remediation. Includes a complete **FastAPI backend**, **PostgreSQL persistence**, and a modern **React + Vite + Tailwind CSS dashboard** with full audit history support.

---

## 🏗️ Architecture & System Flow

```
   Target Website URL
            │
            ▼
┌───────────────────────────────────────────────┐
│ 1. Browser & Screen Reader Traversal          │
│    ├─ Selenium (Chrome)  ──► Tab / Shift+Tab  │
│    └─ NVDA Speech Viewer ──► Live Speech Logs │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ 2. Parsing & Synchronization                  │
│    ├─ nvda_parser.py ──► AccessibilityEvents  │
│    └─ sync.py        ──► DOM vs. NVDA matches │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ 3. Gemini AI Analysis Authority               │
│    ├─ Token-efficient factual evidence        │
│    ├─ WCAG 2.1 mapping, Rationale & Impact    │
│    └─ Developer HTML/ARIA Remediation         │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ 4. FastAPI Backend & PostgreSQL Persistence   │
│    ├─ Sequential Worker Queue (Thread-safe)   │
│    ├─ Native UUID & JSONB Storage (Neon)      │
│    └─ REST API: /api/audits, /api/health      │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ 5. React + Vite + Tailwind Frontend           │
│    ├─ Interactive Audit Input (URL + Limit)   │
│    ├─ Live Dashboard with Severity Breakdown  │
│    ├─ Detailed Evidence Inspection            │
│    └─ PostgreSQL Audit History View           │
└───────────────────────────────────────────────┘
```

---

## 📋 Prerequisites

1. **Operating System**: Windows 10 or 11 (required for NVDA Win32 API hooks).
2. **Python**: Python 3.10 or higher.
3. **Node.js**: Node v18+ and npm (for the React frontend).
4. **Google Chrome**: Installed on your system.
5. **NVDA Screen Reader**:
   - Download & install [NVDA (NonVisual Desktop Access)](https://www.nvaccess.org/download/).
   - Open NVDA Speech Viewer: Press `NVDA Key + N` (or right-click NVDA tray icon) $\rightarrow$ **Tools** $\rightarrow$ **Speech Viewer**.
   - *Keep the Speech Viewer window open while running automated or live audits.*

---

## ⚙️ Installation & Configuration

### 1. Backend & Python Setup
Navigate to the project root and install Python dependencies:
```powershell
pip install selenium requests pywin32 fastapi uvicorn sqlalchemy psycopg2-binary
```

Configure your `.env` file in the project root:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/nvda_accessibility
```

### 2. Frontend Setup
Navigate to the `frontend/` directory and install dependencies:
```powershell
cd frontend
npm install
```

Configure `frontend/.env` (created automatically with defaults):
```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 🚀 How to Run the Application

### Option A: Complete Web Application (Frontend + Backend)

1. **Start the FastAPI Backend** (from project root):
   ```powershell
   uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
   ```
   - Swagger Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Health Check: `GET http://localhost:8000/api/health`

2. **Start the React Frontend** (in a second terminal):
   ```powershell
   cd frontend
   npm run dev
   ```
   - Open your browser to [http://localhost:5173](http://localhost:5173).
   - Enter any website URL, set the optional Tab traversal limit (1–500), and click **Start Audit**.
   - Click **Audit History** in the top navigation to browse and inspect any past audit from PostgreSQL.

---

### Option B: Command-Line CLI Execution

#### 1. Automated Webpage Audit
```powershell
python main.py https://example.com
```
With custom tab traversal limit:
```powershell
python main.py https://example.com --limit 30
```

#### 2. Live Interactive Listener Mode
For auditing dynamic single-page applications, menus, modals, and login forms interactively:
```powershell
python main.py --live
```

#### 3. Run Offline Automated Test Suite
Runs all 69 unit tests across NVDA parser, AI analyzer, FastAPI REST routes, and PostgreSQL:
```powershell
python main.py --test
```

---

## 📊 Public REST API Contract

| Method | Endpoint | Request Body | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | None | Service & PostgreSQL health check. |
| `POST` | `/api/audits` | `{"url": "...", "tab_limit": 100, "enable_ai": true}` | Enqueues a new sequential audit (`201 Created`). |
| `GET` | `/api/audits/{id}` | None | Retrieves audit status and full `analysis` report. |
| `GET` | `/api/audits` | None | Returns all historical audits from PostgreSQL (newest first). |

### Sample Completed Audit Response
```json
{
  "audit_id": "442360e1-a023-4601-bb14-79abe4398cad",
  "url": "https://example.com",
  "status": "completed",
  "analysis_type": "AI_ACCESSIBILITY_ANALYSIS",
  "created_at": "2026-09-09T16:10:00+00:00",
  "completed_at": "2026-09-09T16:10:02+00:00",
  "tab_limit": 100,
  "analysis": {
    "url": "https://example.com",
    "summary": {
      "compliance_score": 92.4,
      "severity_summary": { "CRITICAL": 0, "MAJOR": 1, "MINOR": 0, "INFO": 0 },
      "total_violations": 1,
      "total_elements_analyzed": 7
    },
    "violations": [
      {
        "violation_id": "AI-001",
        "scope": "ELEMENT",
        "element_reference": { "direction": "forward", "step": 1 },
        "rule_id": "WCAG 1.1.1",
        "rule_name": "Non-text Content",
        "severity": "MAJOR",
        "confidence": 0.95,
        "title": "Unlabeled graphic link",
        "description": "...",
        "ai_rationale": "...",
        "user_impact": "...",
        "wcag_context": "...",
        "recommendation": "...",
        "developer_guidance": "...",
        "evidence": {
          "selenium": { "tag": "a", "class": "navbar-brand", ... },
          "nvda": { "name": "logo.", "role": "graphic link", ... },
          "comparison": { "status": "ROLE_MATCH_NAME_UNLABELLED", "name_match": false, "role_match": true }
        }
      }
    ],
    "ai_metadata": { "provider": "GeminiProvider", "model": "gemini-2.5-flash" },
    "analysis_type": "AI_ACCESSIBILITY_ANALYSIS",
    "analysis_status": "COMPLETED"
  },
  "error": null
}
```

---

## 📂 Project Structure

```
NVDA_TEXT_EXTRACTOR - Copy/
├── README.md                         <-- System documentation & run instructions
├── progress.md                       <-- Component tracking & roadmap
├── .env                              <-- API key & PostgreSQL connection
├── main.py                           <-- Unified CLI entry point & test runner
│
├── backend/                          <-- FastAPI Backend & Database Layer
│   ├── main.py                       <-- FastAPI app, CORS & API routes
│   ├── schemas.py                    <-- Pydantic v2 request/response schemas
│   ├── audit_service.py              <-- Background sequential audit worker queue
│   ├── database.py                   <-- SQLAlchemy engine & session factory
│   └── models.py                     <-- PostgreSQL Audit ORM model (UUID + JSONB)
│
├── frontend/                         <-- React + Vite + Tailwind Application
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx            <-- Brand navigation & view toggle
│   │   │   ├── AuditInput.jsx        <-- URL & Tab Limit input form
│   │   │   ├── SummaryCard.jsx       <-- Metric cards (Score, Violations, Status)
│   │   │   ├── SeverityOverview.jsx  <-- 4-level severity distribution cards
│   │   │   ├── ViolationCard.jsx     <-- Expandable violation card
│   │   │   ├── ViolationDetails.jsx  <-- WCAG context, AI rationale, code guidance
│   │   │   ├── EvidenceSection.jsx   <-- Selenium, NVDA & sync comparison cards
│   │   │   └── AuditHistory.jsx      <-- PostgreSQL historical audits table
│   │   ├── services/
│   │   │   └── api.js                <-- Native fetch API client for backend
│   │   ├── App.jsx                   <-- Root application state & view controller
│   │   └── index.css                 <-- Tailwind CSS configuration
│   ├── package.json                  <-- Frontend dependencies (React 19, Vite 8)
│   └── vite.config.js                <-- Vite configuration with @tailwindcss/vite
│
├── tools/                            <-- Core Accessibility Engine Modules
│   ├── ai_agent.py                   <-- Gemini AI Analyzer & Pydantic report schemas
│   ├── ai_providers.py               <-- Gemini REST API provider & mock fallback
│   ├── nvda_classifier.py            <-- Filters browser chrome & deduplicates elements
│   ├── nvda_filter.py                <-- Cleans speech timestamps & formatting
│   ├── nvda_parser.py                <-- Converts speech into structured AccessibilityEvents
│   └── nvda_tool.py                  <-- Windows Win32 API bridge to NVDA Speech Viewer
│
├── tests/                            <-- Offline Automated Unit Tests (69 tests)
│   ├── test_parser.py                <-- NVDA speech parsing tests (29 tests)
│   ├── test_ai_agent.py              <-- AI analyzer evidence & batching tests (14 tests)
│   ├── test_backend.py               <-- FastAPI routes & mock runner tests (13 tests)
│   └── test_database.py              <-- PostgreSQL CRUD & schema tests (13 tests)
│
├── synchronisation/                  <-- Synchronization Engine
│   └── sync.py                       <-- DOM element vs. NVDA readout alignment
│
└── Traversing/                       <-- Browser Keyboard Traversal
    └── Traversing.py                 <-- Bidirectional Tab/Shift+Tab navigation
```
