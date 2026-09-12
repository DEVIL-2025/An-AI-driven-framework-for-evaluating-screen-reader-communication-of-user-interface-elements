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

### Option B: Unified CLI Execution (`main.py`)

The unified CLI `main.py` provides simple one-command access to all core modes:

#### 1. Automated Webpage Audit + AI Remediation
Traverses the target URL with Selenium and NVDA, captures full-page screenshot evidence, analyzes results with Gemini, and outputs reports:
```powershell
python main.py https://example.com
```
With a custom keyboard tab limit (default: 100):
```powershell
python main.py https://example.com --limit 30
```
**Evidence-Only Mode (Skip AI / No API key needed):**
To test traversal, speech capture, and visual screenshot evidence without invoking Gemini:
```powershell
python main.py https://example.com --limit 20 --no-ai
```

#### 2. Live Interactive Listener Mode
Audits dynamic pages, modals, drop-downs, and authenticated flows live as you manually navigate:
```powershell
python main.py --live
```

#### 3. Run Automated Unit Test Suite
Runs the 70 offline unit tests across parser, AI agent, backend API, and database models:
```powershell
python main.py --test
```

---

### Option C: Running Individual Files & Modules Standalone

Each component in the repository is modular and can be executed or tested individually:

#### 1. Standalone Synchronized DOM + NVDA Traversal (`synchronisation/sync.py`)
Runs bidirectional keyboard traversal (Tab & Shift+Tab) while capturing NVDA screen reader speech adaptively and comparing accessibility roles against Selenium DOM attributes.

```powershell
# Syntax: python synchronisation/sync.py <URL>
python synchronisation/sync.py https://example.com
```

* **Environment Overrides (Optional):**
  ```powershell
  $env:TAB_LIMIT="50"       # Limit steps (default: 100)
  $env:READ_DELAY="1.5"     # Max wait per element (default: 1.5s adaptive)
  python synchronisation/sync.py https://example.com
  ```
* **Output Artifact:** Saves `synchronized_output.json` with DOM and NVDA matched telemetry.

---

#### 2. Standalone Browser Keyboard Traversal (`Traversing/Traversing.py`)
Performs browser-only forward (Tab) and backward (Shift+Tab) keyboard navigation without requiring NVDA. Useful for inspecting keyboard focus order, tab traps, and DOM element accessibility properties.

```powershell
# Syntax: python Traversing/Traversing.py <URL>
python Traversing/Traversing.py https://example.com
```

* **Environment Overrides (Optional):**
  ```powershell
  $env:TAB_LIMIT="50"       # Maximum tab steps (default: 100)
  $env:WAIT_TIME="1.0"      # Delay between keypresses (default: 1.0s)
  python Traversing/Traversing.py https://example.com
  ```
* **Output Artifact:** Saves `traversal_output.json` containing detailed forward and backward element sequences.

---

#### 3. Standalone FastAPI Backend (`backend/main.py`)
Runs only the REST API server and PostgreSQL worker queue (useful for API testing or headless server deployment):

```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
* **Interactive API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Health Check:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

#### 4. Standalone React Frontend (`frontend/`)
Runs only the React + Vite development server or builds production bundles:

```powershell
cd frontend

# Development server:
npm run dev

# Production build:
npm run build

# Preview production build:
npm run preview
```

---

#### 5. Running Individual Test Files (`tests/`)
Each test suite can be run independently:

```powershell
# 1. Full-Page Screenshot Capture Tests (11 tests - CDP, viewport fallback, tall pages)
python -m unittest tests/test_screenshot_capture.py -v

# 2. DOM / Structural Snapshot Extractor Tests (26 tests - generic landmarks, headings, cards)
python -m unittest tests/test_dom_extractor.py -v

# 3. NVDA Speech Parser Tests (29 tests - speech cleaning, role tokenization, landmarks)
python -m unittest tests/test_parser.py -v

# 4. AI Accessibility Agent Tests (15 tests - Gemini schemas, batching, confidence scoring)
python -m unittest tests/test_ai_agent.py -v

# 5. Backend REST API Tests (13 tests - route validation, worker queue, error handling)
python -m unittest tests/test_backend.py -v

# 6. PostgreSQL Database Integration Tests (13 tests - UUID, JSONB persistence, CRUD)
python -m unittest tests/test_database.py -v

# Run entire test suite (all 107 tests):
python -m unittest discover -s tests -v
```

---

#### 6. Importing Core Tools as a Python Library (`tools/`)
You can import and use individual engine modules directly in your own scripts:

```python
# 1. Capture Full-Page Webpage Screenshot (CDP with Viewport fallback)
from tools.screenshot_capture import capture_webpage_screenshot
screenshot_meta = capture_webpage_screenshot(driver, output_path="webpage_screenshot.png")
# Returns: {"status": "SUCCESS", "capture_mode": "FULL_PAGE", "width": 1900, "height": 1373, ...}

# 2. Extract DOM & Semantic Structural Snapshot
from tools.dom_extractor import extract_dom_snapshot
dom_snapshot = extract_dom_snapshot(driver)
# Returns: {"landmarks": [...], "headings": [...], "sections": [...], "interactive": [...], "images": [...]}

# 3. Extract live speech from NVDA
from tools.nvda_tool import NVDATextExtractor
extractor = NVDATextExtractor()
text = extractor.get_new_text()

# 4. Filter noise and key echoes
from tools.nvda_filter import NVDAFilter
filter_tool = NVDAFilter()
cleaned_lines = filter_tool.clean(text)

# 5. Parse speech into structured AccessibilityEvent objects
from tools.nvda_parser import NVDAParser
parser = NVDAParser()
events = parser.parse(cleaned_lines)

# 6. Run AI accessibility analysis with Gemini
from tools.ai_agent import AIAccessibilityAnalyzer
analyzer = AIAccessibilityAnalyzer()
report = analyzer.analyze_synchronized_evidence(synchronized_data)
```

---

## 🧪 Manual Testing & Verification Guide

Follow this guide to manually test and verify every tier of the system—from individual tools to full automated audits.

### Step 1: Pre-Flight Environment Check
1. **Ensure NVDA is running** on your Windows system.
2. **Open NVDA Speech Viewer**: Right-click the NVDA tray icon $\rightarrow$ **Tools** $\rightarrow$ **Speech Viewer** (or press `NVDA Key + N` $\rightarrow$ Tools $\rightarrow$ Speech Viewer). Keep this window open.
3. **Verify Python connection to NVDA**:
   ```powershell
   python -c "from tools.nvda_tool import NVDATextExtractor; NVDATextExtractor(); print('NVDA Speech Viewer is connected!')"
   ```
   If successful, it prints: `NVDA Speech Viewer is connected!`.

---

### Step 2: Running an Automated Live Audit
Run an end-to-end automated audit against any target website:

```powershell
# Full automated audit with Gemini AI violation analysis:
python main.py https://example.com --limit 20

# Evidence-only automated audit (no Gemini API calls, fast verification):
python main.py https://example.com --limit 20 --no-ai
```

#### What happens during execution:
1. Chrome launches and navigates to the target page.
2. The browser window is maximized.
3. **Forward Traversal**: The system sends `Tab` keystrokes up to the limit, capturing focused DOM element details and corresponding NVDA speech output.
4. **Backward Traversal**: The system sends `Shift+Tab` keystrokes to verify reverse navigation order and loop boundaries.
5. **Screenshot Evidence Capture**: Immediately before closing Chrome, the system triggers Chrome DevTools Protocol (`Page.captureScreenshot` with `captureBeyondViewport: true`), capturing the entire page canvas from top header down to footer without moving focus or scrolling.
6. The browser cleanly closes.

#### Inspecting the Generated Artifacts:
All outputs are saved to the current directory (or the specified `--output-dir`):
- `webpage_screenshot.png`: High-resolution full-page screenshot of the audited page. Open in any image viewer to verify that the top header, logo, body cards, and footer are visually rendered.
- `screenshot_metadata.json`: Metadata verifying status (`SUCCESS`), capture mode (`FULL_PAGE` or `VIEWPORT`), pixel width/height, and file size in bytes.
- `synchronized_output.json`: Detailed JSON array of all forward and backward steps pairing Selenium DOM attributes with NVDA speech readouts and role comparison results.
- `nvda_log.txt`: Complete, raw chronological stream of captured NVDA speech events.
- `ai_accessibility_report.json`: (When AI is enabled) Authoritative WCAG 2.1 mapping, violation severity scores, user impact descriptions, and developer remediation code guidance.

---

### Step 3: Manual Interactive Navigation Mode (`--live`)
Use this mode to audit complex dynamic components (menus, accordions, dialogs, modals, and single-page apps) manually:

1. Launch interactive mode:
   ```powershell
   python main.py --live
   ```
2. Open any browser or application and navigate using the keyboard (`Tab`, `Shift+Tab`, `Arrow Keys`, `Enter`, `Space`).
3. Observe live parsed events in the terminal:
   - Extracted text
   - Identified accessibility roles (e.g. `button`, `graphic link`, `edit text`)
   - Landmarks and states (e.g. `expanded`, `collapsed`, `has popup`)
4. Output is continuously recorded to `nvda_log.txt`.
5. Press `Ctrl+C` to terminate the session.

---

### Step 4: Standalone Tool Testing

#### A. Full-Page Screenshot Evidence Capture:
Test the screenshot utility in isolation:
```powershell
python -c "from selenium import webdriver; from tools.screenshot_capture import capture_webpage_screenshot; d = webdriver.Chrome(); d.get('https://example.com'); meta = capture_webpage_screenshot(d, 'manual_test_shot.png'); print(meta); d.quit()"
```
Verify that `manual_test_shot.png` is generated and that the printed dictionary reports `"status": "SUCCESS"` and `"capture_mode": "FULL_PAGE"`.

#### B. DOM & Structural Snapshot Extraction:
Test the generic DOM extractor in isolation:
```powershell
python -c "from selenium import webdriver; from tools.dom_extractor import extract_dom_snapshot; d = webdriver.Chrome(); d.get('https://example.com'); snap = extract_dom_snapshot(d); print('Headings:', len(snap['headings']), '| Landmarks:', len(snap['landmarks']), '| Sections:', len(snap['sections'])); d.quit()"
```

---

### Step 5: Running the Automated Test Suites
Run unit and integration tests to verify system integrity across all 107 test cases:

```powershell
# 1. Quick sanity check (Core backend, database, parser & AI agent - 70 tests):
python main.py --test

# 2. Screenshot capture tests (11 tests - CDP full-page, viewport fallback, tall document):
python -m unittest tests/test_screenshot_capture.py -v

# 3. DOM extractor tests (26 tests - generic landmarks, cards, headings, redundancy filters):
python -m unittest tests/test_dom_extractor.py -v

# 4. Run the entire project test suite (all 107 tests):
python -m unittest discover -s tests -v
```

---

### Step 6: Testing the Web Application (Backend + Frontend)

#### 1. Test the FastAPI Backend:
Start the backend server:
```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
- Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to inspect interactive Swagger documentation.
- Test the health endpoint:
  ```powershell
  curl http://127.0.0.1:8000/api/health
  ```
  Expected output: `{"status":"ok","service":"accessibility-testing-api","database":"connected"}`.

#### 2. Test the React Frontend Dashboard:
In a separate terminal, start the Vite development server:
```powershell
cd frontend
npm run dev
```
- Navigate to [http://localhost:5173](http://localhost:5173).
- Enter a website URL (e.g. `https://example.com`), specify a tab limit (e.g. `20`), and click **Start Audit**.
- Watch live audit status update, then inspect the completed dashboard:
  - **Compliance Score** and **Severity Breakdown** (Critical, Major, Minor, Info).
  - **Violation Cards** with WCAG success criteria tags and confidence scores.
  - **Expandable Details** showing user impact, AI rationale, and developer remediation code.
  - **Evidence Comparison Cards** contrasting Selenium DOM attributes against NVDA screen reader speech.
  - **Audit History**: Click "Audit History" in the navigation bar to browse past audits stored in PostgreSQL.

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
│   ├── dom_extractor.py              <-- Semantic DOM & structural snapshot extractor
│   ├── nvda_classifier.py            <-- Filters browser chrome & deduplicates elements
│   ├── nvda_filter.py                <-- Cleans speech timestamps & formatting
│   ├── nvda_parser.py                <-- Converts speech into structured AccessibilityEvents
│   ├── nvda_tool.py                  <-- Windows Win32 API bridge to NVDA Speech Viewer
│   └── screenshot_capture.py         <-- Chrome DevTools Protocol full-page screenshot capture
│
├── tests/                            <-- Automated Unit & Integration Tests (107 tests)
│   ├── test_screenshot_capture.py    <-- Full-page & viewport screenshot tests (11 tests)
│   ├── test_dom_extractor.py         <-- DOM structural snapshot extractor tests (26 tests)
│   ├── test_parser.py                <-- NVDA speech parsing tests (29 tests)
│   ├── test_ai_agent.py              <-- AI analyzer evidence & batching tests (15 tests)
│   ├── test_backend.py               <-- FastAPI routes & mock runner tests (13 tests)
│   └── test_database.py              <-- PostgreSQL CRUD & schema tests (13 tests)
│
├── synchronisation/                  <-- Synchronization Engine
│   └── sync.py                       <-- DOM element vs. NVDA readout alignment
│
└── Traversing/                       <-- Browser Keyboard Traversal
    └── Traversing.py                 <-- Bidirectional Tab/Shift+Tab navigation
```
