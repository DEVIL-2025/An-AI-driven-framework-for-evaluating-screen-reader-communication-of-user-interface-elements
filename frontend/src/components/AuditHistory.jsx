import { useState, useEffect, useMemo } from 'react'
import { getAudits, clearAudits } from '../services/api'
import { downloadReportAsJson } from '../utils/reportDownload'

export default function AuditHistory({ onSelectAudit, onBackToDashboard }) {
  const [audits, setAudits] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [loadingAuditId, setLoadingAuditId] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [isClearing, setIsClearing] = useState(false)
  const [showConfirmClear, setShowConfirmClear] = useState(false)

  const fetchHistory = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await getAudits()
      setAudits(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message || 'Unable to load audit history.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [])

  const handleClearHistory = async () => {
    setIsClearing(true)
    setError(null)
    try {
      await clearAudits()
      setAudits([])
      setShowConfirmClear(false)
      setSearchQuery('')
    } catch (err) {
      setError(err.message || 'Failed to clear audit history.')
    } finally {
      setIsClearing(false)
    }
  }

  const handleSelect = async (auditId) => {
    if (loadingAuditId) return
    setLoadingAuditId(auditId)
    try {
      await onSelectAudit(auditId)
    } finally {
      setLoadingAuditId(null)
    }
  }

  // Filter audits based on search query matching URL, status, or Audit ID
  const filteredAudits = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    if (!q) return audits
    return audits.filter((item) => {
      const urlMatch = item.url?.toLowerCase().includes(q)
      const idMatch = item.audit_id?.toLowerCase().includes(q)
      const statusMatch = item.status?.toLowerCase().includes(q)
      return urlMatch || idMatch || statusMatch
    })
  }, [audits, searchQuery])

  const getStatusBadge = (status) => {
    const s = String(status || '').toLowerCase()
    switch (s) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" aria-hidden="true"></span>
            Completed
          </span>
        )
      case 'running':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/15 text-indigo-400 border border-indigo-500/30 animate-pulse">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" aria-hidden="true"></span>
            Running...
          </span>
        )
      case 'queued':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" aria-hidden="true"></span>
            Queued
          </span>
        )
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400" aria-hidden="true"></span>
            Failed
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/15 text-slate-300 border border-slate-500/30">
            {status || 'Unknown'}
          </span>
        )
    }
  }

  const formatDate = (isoString) => {
    if (!isoString) return '—'
    try {
      const d = new Date(isoString)
      return d.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch (_) {
      return isoString
    }
  }

  return (
    <section aria-labelledby="history-heading" className="w-full space-y-6">
      {/* Confirmation Modal for Clearing History */}
      {showConfirmClear && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-headline"
            className="glass-card max-w-md w-full rounded-3xl p-6 sm:p-7 shadow-2xl border border-white space-y-4"
          >
            <div className="flex items-center gap-3 text-rose-600">
              <div className="w-10 h-10 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-center shrink-0">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </div>
              <h3 id="modal-headline" className="text-lg font-extrabold text-slate-950">
                Clear Audit History?
              </h3>
            </div>

            <p className="text-sm text-slate-700 font-medium leading-relaxed">
              Are you sure you want to delete all historical accessibility audits? This action cannot be undone.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowConfirmClear(false)}
                disabled={isClearing}
                className="px-4 py-2 text-xs font-bold text-slate-700 hover:text-slate-950 bg-slate-100 hover:bg-slate-200 rounded-xl transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleClearHistory}
                disabled={isClearing}
                className="inline-flex items-center gap-2 px-5 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 active:bg-rose-800 rounded-xl transition-all shadow-md shadow-rose-600/30 cursor-pointer disabled:opacity-60"
              >
                {isClearing ? (
                  <>
                    <svg className="w-3.5 h-3.5 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>Clearing...</span>
                  </>
                ) : (
                  <span>Yes, Clear All</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Top action bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 id="history-heading" className="text-2xl sm:text-3xl font-extrabold text-slate-950 tracking-tight">
            Audit History
          </h2>
          <p className="text-xs sm:text-sm text-slate-700 mt-1 font-semibold">
            Previous web accessibility audit results
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {audits.length > 0 && (
            <button
              type="button"
              onClick={() => setShowConfirmClear(true)}
              disabled={isLoading || isClearing}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-rose-700 bg-rose-50 hover:bg-rose-100 hover:text-rose-900 border border-rose-200 rounded-xl transition-all shadow-xs focus:outline-none focus:ring-2 focus:ring-rose-500 cursor-pointer disabled:opacity-60"
              title="Clear all saved audit history"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Clear History
            </button>
          )}

          <button
            type="button"
            onClick={fetchHistory}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-slate-800 bg-white hover:bg-slate-100 hover:text-slate-950 border border-slate-300 rounded-xl transition-all shadow-xs focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer disabled:opacity-60"
          >
            <svg
              className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-blue-600' : 'text-slate-700'}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2.5"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Refresh
          </button>

          <button
            type="button"
            onClick={onBackToDashboard}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-blue-700 bg-blue-50 hover:bg-blue-100/90 active:bg-blue-200 hover:text-blue-900 border border-blue-200 rounded-xl transition-all shadow-xs focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Dashboard
          </button>
        </div>
      </div>

      {/* Search Input Bar (Shown when audits exist) */}
      {!isLoading && !error && audits.length > 0 && (
        <div className="relative w-full">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4 text-slate-500" aria-hidden="true">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search audits by URL, status, or Audit ID..."
            aria-label="Search audits"
            className="w-full pl-11 pr-10 py-3 bg-white/90 border border-slate-300 rounded-2xl text-slate-950 placeholder-slate-400 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all shadow-xs"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute inset-y-0 right-0 flex items-center pr-3.5 text-slate-400 hover:text-slate-700 transition-colors cursor-pointer"
              title="Clear search"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="glass-card rounded-3xl p-12 text-center shadow-md">
          <svg className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-3" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p className="text-sm text-slate-600 font-semibold">Loading audit history...</p>
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div
          role="alert"
          className="flex items-start justify-between gap-3 p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 shadow-sm"
        >
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <strong className="font-bold block text-rose-900">Unable to load audit history</strong>
              <p className="text-xs text-rose-700 mt-0.5">{error}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={fetchHistory}
            className="px-3 py-1 bg-rose-100 hover:bg-rose-200 text-rose-800 rounded-xl text-xs font-bold border border-rose-300 cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty state (no audits in database) */}
      {!isLoading && !error && audits.length === 0 && (
        <div className="glass-card rounded-3xl p-12 text-center border-dashed border-slate-300">
          <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-3">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-base font-bold text-slate-800">No audits recorded</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 font-medium">
            Run an accessibility test from the Dashboard to record audit history.
          </p>
        </div>
      )}

      {/* Empty search results state */}
      {!isLoading && !error && audits.length > 0 && filteredAudits.length === 0 && (
        <div className="glass-card rounded-3xl p-10 text-center border-dashed border-slate-300">
          <div className="w-10 h-10 rounded-2xl bg-slate-100 text-slate-500 flex items-center justify-center mx-auto mb-2.5">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <h3 className="text-sm font-bold text-slate-800">No matching audits found</h3>
          <p className="text-xs text-slate-500 mt-1 font-medium">
            No audits matched "{searchQuery}". Try a different keyword or URL.
          </p>
          <button
            type="button"
            onClick={() => setSearchQuery('')}
            className="mt-3 text-xs font-bold text-blue-600 hover:text-blue-800 cursor-pointer"
          >
            Clear Search
          </button>
        </div>
      )}

      {/* History table */}
      {!isLoading && !error && filteredAudits.length > 0 && (
        <div className="glass-card rounded-3xl overflow-hidden shadow-lg border border-white">
          {/* Header count summary */}
          <div className="px-6 py-4 border-b border-slate-200/80 bg-white/60 flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
              {searchQuery ? 'Filtered Results' : 'Total Audits Recorded'}
            </span>
            <span className="text-xs font-mono font-bold text-blue-700 bg-blue-50 px-3 py-1 rounded-full border border-blue-200">
              {filteredAudits.length} of {audits.length} {audits.length === 1 ? 'record' : 'records'}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-800">
              <thead className="bg-slate-100/90 text-slate-800 uppercase tracking-wider font-extrabold border-b border-slate-300 text-[11px]">
                <tr>
                  <th scope="col" className="px-6 py-3.5">Target Website</th>
                  <th scope="col" className="px-6 py-3.5">Status</th>
                  <th scope="col" className="px-6 py-3.5 text-center">Score</th>
                  <th scope="col" className="px-6 py-3.5 text-center">Violations</th>
                  <th scope="col" className="px-6 py-3.5 text-center">Elements</th>
                  <th scope="col" className="px-6 py-3.5">Created At</th>
                  <th scope="col" className="px-6 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white/70">
                {filteredAudits.map((item) => {
                  const summary = item.analysis?.summary
                  const score = summary?.compliance_score !== undefined
                    ? `${summary.compliance_score}%`
                    : item.compliance_score !== null && item.compliance_score !== undefined
                    ? `${item.compliance_score}%`
                    : '—'

                  const violations = summary?.total_violations !== undefined
                    ? summary.total_violations
                    : item.total_violations !== null && item.total_violations !== undefined
                    ? item.total_violations
                    : '—'

                  const elements = summary?.total_elements_analyzed !== undefined
                    ? summary.total_elements_analyzed
                    : item.total_elements_audited !== null && item.total_elements_audited !== undefined
                    ? item.total_elements_audited
                    : '—'

                  const isCurrentLoading = loadingAuditId === item.audit_id

                  return (
                    <tr
                      key={item.audit_id}
                      className="hover:bg-blue-50/60 transition-colors"
                    >
                      {/* Target URL */}
                      <td className="px-6 py-4 font-bold text-slate-950 max-w-xs truncate" title={item.url}>
                        <span className="block truncate">{item.url}</span>
                        <span className="block text-[10px] font-mono text-slate-600 font-bold truncate mt-0.5">
                          ID: {item.audit_id}
                        </span>
                      </td>

                      {/* Status */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(item.status)}
                      </td>

                      {/* Compliance Score */}
                      <td className="px-6 py-4 text-center whitespace-nowrap font-mono font-extrabold text-slate-950">
                        {score}
                      </td>

                      {/* Violations Count */}
                      <td className="px-6 py-4 text-center whitespace-nowrap">
                        {violations === 0 ? (
                          <span className="text-emerald-700 font-extrabold font-mono">0</span>
                        ) : violations !== '—' ? (
                          <span className="text-amber-800 font-extrabold font-mono">{violations}</span>
                        ) : (
                          <span className="text-slate-500 font-mono">—</span>
                        )}
                      </td>

                      {/* Elements Audited */}
                      <td className="px-6 py-4 text-center whitespace-nowrap font-mono text-slate-800 font-bold">
                        {elements}
                      </td>

                      {/* Created At */}
                      <td className="px-6 py-4 whitespace-nowrap text-slate-700 font-semibold">
                        {formatDate(item.created_at)}
                      </td>

                      {/* Action Buttons: Download & View */}
                      <td className="px-6 py-4 text-right whitespace-nowrap">
                        <div className="inline-flex items-center gap-2 justify-end">
                          {(item.status === 'completed' || item.analysis) && (
                            <button
                              type="button"
                              onClick={() => downloadReportAsJson(item)}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 active:bg-emerald-200 border border-emerald-200 rounded-xl transition-all shadow-xs focus:outline-none focus:ring-2 focus:ring-emerald-400 cursor-pointer"
                              title={`Download report JSON for ${item.url}`}
                              aria-label={`Download report for ${item.url}`}
                            >
                              <svg className="w-3.5 h-3.5 text-emerald-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                              </svg>
                              <span>Download</span>
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => handleSelect(item.audit_id)}
                            disabled={isCurrentLoading}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-blue-700 bg-blue-50 hover:bg-blue-100 active:bg-blue-200 border border-blue-200 rounded-xl transition-all shadow-xs focus:outline-none focus:ring-2 focus:ring-blue-400 cursor-pointer disabled:opacity-60"
                          >
                            {isCurrentLoading ? (
                              <>
                                <svg className="w-3.5 h-3.5 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
                                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                </svg>
                                <span>Loading...</span>
                              </>
                            ) : (
                              <>
                                <span>View Audit</span>
                                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 5l7 7-7 7" />
                                </svg>
                              </>
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  )
}
