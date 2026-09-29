# Frontend — AI-Powered Screen Reader Accessibility Dashboard

Interactive modern web interface for the AI-Powered Screen Reader (NVDA) Accessibility Testing Framework. Built with **React 19**, **Vite 8**, and **Tailwind CSS**.

---

## 🌟 Features

- **Live Audit Form**: Enter any target URL and configure traversal depth (`tab_limit` from 1 to 500).
- **Executive Accessibility Metrics**: High-contrast summary cards showing Compliance Score, Total Violations, Elements Analyzed, and Audit Status.
- **Severity Distribution Overview**: Clean visualization across `CRITICAL`, `MAJOR`, `MINOR`, and `INFO` findings.
- **Violation & Recommendation Explorer**:
  - Distinguishes **Normative WCAG Violations** from **Accessibility Recommendations**.
  - Displays user impact, normative WCAG rationale, and developer code fixes.
  - Dedicated **Evidence Viewer** inspecting Selenium DOM attributes, raw NVDA Speech Viewer transcripts, and synchronization comparison statuses.
- **Audit History Dashboard**: Inspect and load past audits stored in PostgreSQL directly into the active dashboard.

---

## 🚀 Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Environment Configuration
Create or verify `.env` in the `frontend/` directory:
```env
VITE_API_BASE_URL=http://localhost:8000
```

### 3. Development Server
```bash
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### 4. Production Build
```bash
npm run build
npm run preview
```

---

## 📁 Component Architecture

```
frontend/src/
├── components/
│   ├── Header.jsx             # Top brand navigation & view switcher
│   ├── AuditInput.jsx         # URL & Tab Limit input submission form
│   ├── SummaryCard.jsx        # Top-level score, violation count & status cards
│   ├── SeverityOverview.jsx   # Severity level breakdown cards
│   ├── ViolationCard.jsx      # Expandable violation container
│   ├── ViolationDetails.jsx   # WCAG criteria, user impact & remediation guidance
│   ├── RecommendationCard.jsx # Advisory recommendations & best practice cards
│   ├── EvidenceSection.jsx    # DOM, NVDA speech & synchronization comparison cards
│   └── AuditHistory.jsx       # PostgreSQL historical audits table & viewer
├── services/
│   └── api.js                 # Native fetch API client for FastAPI backend
├── App.jsx                    # Root application state & audit lifecycle manager
└── index.css                  # Tailwind CSS root stylesheet
```
