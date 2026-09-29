import { useState } from 'react'
import Header from './components/Header'
import AuditInput from './components/AuditInput'
import SummaryCard from './components/SummaryCard'
import SeverityOverview from './components/SeverityOverview'
import ViolationCard from './components/ViolationCard'
import RecommendationCard from './components/RecommendationCard'
import AuditHistory from './components/AuditHistory'
import { startAudit, getAuditById } from './services/api'

function App() {
  const [currentView, setCurrentView] = useState('dashboard') // 'dashboard' | 'history'
  const [url, setUrl] = useState('')
  const [tabLimit, setTabLimit] = useState('100')
  const [validationError, setValidationError] = useState(null)
  const [auditResult, setAuditResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [statusText, setStatusText] = useState('')
  const [error, setError] = useState(null)

  const handleStartAudit = async () => {
    if (!url.trim()) return

    // Validate Tab Limit (positive integer 1-500 matching FastAPI backend schema)
    const parsedLimit = parseInt(tabLimit, 10)
    if (isNaN(parsedLimit) || parsedLimit < 1 || parsedLimit > 500) {
      setValidationError('Tab Limit must be a whole number between 1 and 500 steps.')
      return
    }

    setValidationError(null)
    setIsLoading(true)
    setError(null)
    setStatusText('Initiating audit request...')

    try {
      const response = await startAudit(url, parsedLimit, true, (update) => {
        if (update.status === 'queued') {
          setStatusText('Audit queued on server...')
        } else if (update.status === 'running') {
          setStatusText('Auditing browser & capturing NVDA speech...')
        }
      })

      setAuditResult(response)
    } catch (err) {
      setError(err.message || 'An unexpected error occurred during audit.')
    } finally {
      setIsLoading(false)
      setStatusText('')
    }
  }

  // Handle selecting an audit from Audit History
  const handleSelectAuditFromHistory = async (auditId) => {
    setError(null)
    try {
      const fullAudit = await getAuditById(auditId)
      setAuditResult(fullAudit)
      if (fullAudit.url) {
        setUrl(fullAudit.url)
      }
      if (fullAudit.tab_limit) {
        setTabLimit(String(fullAudit.tab_limit))
      }
      // Switch back to dashboard to display loaded audit
      setCurrentView('dashboard')
    } catch (err) {
      setError(err.message || `Failed to load audit ${auditId}`)
    }
  }

  // Extract analysis fields if result exists
  const analysis = auditResult?.analysis
  const summary = analysis?.summary
  const severitySummary = summary?.severity_summary || { CRITICAL: 0, MAJOR: 0, MINOR: 0, INFO: 0 }
  const violations = analysis?.violations || []
  const recommendations = analysis?.recommendations || []
  const auditStatus = auditResult?.status || 'idle'

  return (
    <div className="min-h-screen bg-mesh-light text-slate-800 flex flex-col font-sans antialiased selection:bg-blue-500 selection:text-white">
      {/* 1. Header with View Toggle */}
      <Header
        currentView={currentView}
        onViewChange={(view) => setCurrentView(view)}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
        {/* Error Alert Banner */}
        {error && (
          <div
            role="alert"
            className="flex items-start gap-3 p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 shadow-sm"
          >
            <svg
              className="w-5 h-5 text-rose-600 shrink-0 mt-0.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1 text-sm">
              <strong className="font-bold block text-rose-900">Error</strong>
              <p className="mt-0.5 text-rose-700">{error}</p>
            </div>
            <button
              type="button"
              onClick={() => setError(null)}
              className="text-rose-500 hover:text-rose-700 p-1 rounded-lg transition-colors cursor-pointer"
              aria-label="Dismiss error"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* View Switch: History vs Dashboard */}
        {currentView === 'history' ? (
          <AuditHistory
            onSelectAudit={handleSelectAuditFromHistory}
            onBackToDashboard={() => setCurrentView('dashboard')}
          />
        ) : (
          <>
            {/* Live Progress Banner while running */}
            {isLoading && (
              <div className="glass-card flex items-center justify-between px-5 py-3.5 rounded-2xl border border-blue-200/80 text-xs text-blue-800 shadow-sm animate-pulse">
                <div className="flex items-center gap-2.5">
                  <svg className="w-4 h-4 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span>
                    <strong className="font-bold">Audit in progress:</strong> {statusText || 'Evaluating website and capturing screen reader telemetry...'}
                  </span>
                </div>
                <span className="font-mono text-blue-600 font-bold">{url} ({tabLimit} steps)</span>
              </div>
            )}

            {/* Banner when viewing a previously executed audit */}
            {auditResult && auditResult.audit_id && !isLoading && (
              <div className="glass-card flex flex-wrap items-center justify-between gap-3 px-5 py-3 rounded-2xl border border-white text-xs text-slate-600 shadow-xs">
                <div className="flex items-center gap-2.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" aria-hidden="true"></span>
                  <span>Viewing Audit: <strong className="text-slate-900 font-mono font-bold">{auditResult.audit_id}</strong></span>
                  {auditResult.created_at && (
                    <span className="text-slate-500 hidden sm:inline font-medium">
                      ({new Date(auditResult.created_at).toLocaleString()})
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => setCurrentView('history')}
                  className="text-xs font-bold text-blue-600 hover:text-blue-800 transition-colors cursor-pointer"
                >
                  View All Audits &rarr;
                </button>
              </div>
            )}

            {/* 2. Audit Input Form with Tab Limit */}
            <AuditInput
              url={url}
              setUrl={setUrl}
              tabLimit={tabLimit}
              setTabLimit={(val) => {
                setTabLimit(val)
                if (validationError) setValidationError(null)
              }}
              onSubmit={handleStartAudit}
              isLoading={isLoading}
              statusText={statusText}
              validationError={validationError}
            />

            {/* 3. Summary Metrics Cards */}
            <section aria-labelledby="summary-heading">
              <h2 id="summary-heading" className="sr-only">
                Audit Summary Metrics
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                <SummaryCard
                  title="Compliance Score"
                  value={summary ? `${summary.compliance_score}%` : '—'}
                  icon={
                    <svg className="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  }
                />

                <SummaryCard
                  title="Total Violations"
                  value={summary !== undefined && summary !== null ? String(summary.total_violations) : '—'}
                  icon={
                    <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  }
                />

                <SummaryCard
                  title="Recommendations"
                  value={summary !== undefined && summary !== null ? String(summary.total_recommendations ?? recommendations.length) : '—'}
                  icon={
                    <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  }
                />

                <SummaryCard
                  title="Elements Analyzed"
                  value={summary ? String(summary.total_elements_analyzed) : '—'}
                  icon={
                    <svg className="w-5 h-5 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                    </svg>
                  }
                />

                <SummaryCard
                  title="Audit Status"
                  value={
                    auditResult
                      ? auditStatus === 'completed'
                        ? 'Completed'
                        : auditStatus
                      : 'Not Started'
                  }
                  statusType={auditResult ? auditStatus : null}
                  icon={
                    auditStatus === 'completed' ? (
                      <svg className="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                      </svg>
                    ) : auditStatus === 'running' ? (
                      <svg className="w-5 h-5 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                    ) : auditStatus === 'failed' ? (
                      <svg className="w-5 h-5 text-rose-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                    )
                  }
                />
              </div>
            </section>

            {/* 4. Severity Distribution Overview */}
            <SeverityOverview
              critical={severitySummary.CRITICAL || 0}
              major={severitySummary.MAJOR || 0}
              minor={severitySummary.MINOR || 0}
              info={severitySummary.INFO || 0}
            />

            {/* 5. Detected Violations Section */}
            <section aria-labelledby="violations-heading" className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 id="violations-heading" className="text-xl font-extrabold text-slate-900 tracking-tight">
                    Detected Accessibility Violations
                  </h3>
                  <p className="text-xs text-slate-500 font-medium">
                    Accessibility violations and WCAG remediation guidance
                  </p>
                </div>
                {auditResult && (
                  <span className="text-xs font-mono font-bold text-blue-700 px-3 py-1 rounded-full bg-blue-50 border border-blue-200">
                    {violations.length} {violations.length === 1 ? 'finding' : 'findings'}
                  </span>
                )}
              </div>

              {!auditResult ? (
                <div className="glass-card rounded-3xl p-12 text-center border-dashed border-slate-300">
                  <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-3">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                    </svg>
                  </div>
                  <h4 className="text-base font-bold text-slate-800">No audit results yet</h4>
                  <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 font-medium">
                    Enter a target URL and tab step limit above, then click "Start Audit".
                  </p>
                </div>
              ) : violations.length === 0 ? (
                <div className="glass-card rounded-3xl p-8 text-center border border-emerald-200 bg-emerald-50/40">
                  <div className="w-10 h-10 rounded-xl bg-emerald-500 text-white flex items-center justify-center mx-auto mb-2 shadow-sm font-bold">
                    ✓
                  </div>
                  <h4 className="text-base font-extrabold text-slate-900">No Accessibility Violations Detected</h4>
                  <p className="text-xs text-slate-600 mt-1 font-medium">
                    All focusable interactive elements have valid accessible names and screen reader announcements.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {violations.map((v, index) => (
                    <ViolationCard
                      key={v.violation_id ? `${v.violation_id}-${index}` : `v-${index}`}
                      violation={v}
                    />
                  ))}
                </div>
              )}
            </section>

            {/* 6. Accessibility Recommendations & Best Practices Section */}
            {auditResult && recommendations.length > 0 && (
              <section aria-labelledby="recommendations-heading" className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 id="recommendations-heading" className="text-xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
                      <span>Accessibility Recommendations</span>
                      <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                        Advisory / Best Practices
                      </span>
                    </h3>
                    <p className="text-xs text-slate-500 font-medium">
                      Structural enhancements and advisory guidance that do not violate normative WCAG criteria (0 score penalty)
                    </p>
                  </div>
                  <span className="text-xs font-mono font-bold text-blue-700 px-3 py-1 rounded-full bg-blue-50 border border-blue-200">
                    {recommendations.length} {recommendations.length === 1 ? 'recommendation' : 'recommendations'}
                  </span>
                </div>

                <div className="space-y-4">
                  {recommendations.map((rec, index) => (
                    <RecommendationCard
                      key={rec.recommendation_id ? `${rec.recommendation_id}-${index}` : `rec-${index}`}
                      recommendation={rec}
                    />
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200/80 bg-white/50 backdrop-blur-sm py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-xs text-slate-500 font-medium">
          <p>&copy; {new Date().getFullYear()} AI Accessibility Analyzer. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}

export default App
