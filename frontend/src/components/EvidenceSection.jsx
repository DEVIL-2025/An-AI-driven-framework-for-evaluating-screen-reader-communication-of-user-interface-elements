export default function EvidenceSection({ evidence, elementReference }) {
  if (!evidence) return null

  const { selenium = {}, nvda = {}, comparison = {} } = evidence

  return (
    <div className="space-y-4 pt-4 border-t border-slate-200/80">
      <div className="flex items-center justify-between">
        <div>
          <h5 className="text-sm font-extrabold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Authoritative Synchronized Evidence
          </h5>
          <p className="text-xs text-slate-500 font-medium">
            Telemetry captured at step {elementReference?.step || 1} during browser keyboard navigation
          </p>
        </div>

        {elementReference && (
          <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-lg bg-slate-100 border border-slate-200 text-slate-700">
            Step {elementReference.step} ({elementReference.direction})
          </span>
        )}
      </div>

      {/* 3 Evidence Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* A. Selenium Evidence */}
        <div className="rounded-2xl bg-slate-50/90 border border-slate-200/90 p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-200/80 pb-2">
            <span className="text-xs font-extrabold text-sky-800 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-sky-500" aria-hidden="true"></span>
              Selenium DOM
            </span>
            <span className="text-[10px] font-mono text-slate-700 uppercase font-bold">Focus State</span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div>
              <span className="text-slate-700 block text-[11px] font-sans font-bold">Tag:</span>
              <span className="text-slate-950 bg-white border border-slate-300 px-1.5 py-0.5 rounded font-extrabold">&lt;{selenium.tag || 'N/A'}&gt;</span>
            </div>

            <div>
              <span className="text-slate-700 block text-[11px] font-sans font-bold">Class:</span>
              <span className="text-slate-900 font-medium truncate block bg-white border border-slate-300 px-1.5 py-0.5 rounded" title={selenium.class || ''}>{selenium.class || 'None'}</span>
            </div>

            <div>
              <span className="text-slate-700 block text-[11px] font-sans font-bold">Href:</span>
              <span className="text-blue-700 font-medium truncate block text-[11px] bg-white border border-slate-300 px-1.5 py-0.5 rounded" title={selenium.href || ''}>{selenium.href || 'None'}</span>
            </div>

            {selenium.expected_roles && selenium.expected_roles.length > 0 && (
              <div>
                <span className="text-slate-700 block text-[11px] font-sans font-bold">Expected Roles:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {selenium.expected_roles.map((r, i) => (
                    <span key={i} className="px-1.5 py-0.5 rounded bg-white border border-slate-300 text-slate-900 text-[10px] font-bold">
                      {r}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* B. NVDA Speech Evidence */}
        <div className="rounded-2xl bg-slate-50/90 border border-slate-200/90 p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-200/80 pb-2">
            <span className="text-xs font-extrabold text-violet-800 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-violet-500" aria-hidden="true"></span>
              NVDA Screen Reader
            </span>
            <span className="text-[10px] font-mono text-slate-700 uppercase font-bold">Announcement</span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div>
              <span className="text-slate-700 block text-[11px] font-sans font-bold">Announced Name:</span>
              <span className="text-amber-950 font-bold bg-amber-100/70 border border-amber-300 px-1.5 py-0.5 rounded block truncate">
                "{nvda.name || ''}"
              </span>
            </div>

            <div>
              <span className="text-slate-700 block text-[11px] font-sans font-bold">Announced Role:</span>
              <span className="text-slate-950 font-bold bg-white border border-slate-300 px-1.5 py-0.5 rounded block">{nvda.role || 'None'}</span>
            </div>

            {nvda.attributes && nvda.attributes.length > 0 && (
              <div>
                <span className="text-slate-700 block text-[11px] font-sans font-bold">Attributes:</span>
                <span className="text-slate-900 bg-white border border-slate-300 px-1.5 py-0.5 rounded block truncate font-medium">{nvda.attributes.join(', ')}</span>
              </div>
            )}

            {nvda.description && (
              <div>
                <span className="text-slate-700 block text-[11px] font-sans font-bold">Description:</span>
                <p className="text-slate-900 text-[11px] font-sans italic line-clamp-2 bg-white border border-slate-300 p-1.5 rounded font-medium" title={nvda.description}>
                  "{nvda.description}"
                </p>
              </div>
            )}

            {nvda.raw_text && (
              <div className="pt-1">
                <span className="text-slate-700 block text-[10px] uppercase tracking-wide font-sans font-extrabold">Raw Speech Stream:</span>
                <div className="p-1.5 rounded bg-white text-[10px] text-slate-900 border border-slate-300 truncate font-mono font-medium" title={nvda.raw_text}>
                  {nvda.raw_text}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* C. Comparison Evidence */}
        <div className="rounded-2xl bg-slate-50/90 border border-slate-200/90 p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-200/80 pb-2">
            <span className="text-xs font-extrabold text-emerald-800 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500" aria-hidden="true"></span>
              Synchronization Match
            </span>
            <span className="text-[10px] font-mono text-slate-700 uppercase font-bold">Engine Status</span>
          </div>

          <div className="space-y-2.5 text-xs font-mono">
            <div>
              <span className="text-slate-700 block text-[11px] font-sans font-bold">Comparison Status:</span>
              <span className="inline-block mt-0.5 px-2 py-0.5 text-[11px] font-bold rounded-lg bg-blue-100 text-blue-900 border border-blue-300">
                {comparison.status || 'UNKNOWN'}
              </span>
            </div>

            <div className="space-y-1.5 pt-1">
              <div className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-300">
                <span className="text-slate-900 font-sans text-xs font-bold">Name Match</span>
                <span className={`inline-flex items-center gap-1 text-xs font-bold ${comparison.name_match ? 'text-emerald-700' : 'text-rose-700'}`}>
                  <span aria-hidden="true">{comparison.name_match ? '✓' : '✗'}</span>
                  <span>{comparison.name_match ? 'true (MATCH)' : 'false (MISMATCH)'}</span>
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-300">
                <span className="text-slate-900 font-sans text-xs font-bold">Role Match</span>
                <span className={`inline-flex items-center gap-1 text-xs font-bold ${comparison.role_match ? 'text-emerald-700' : 'text-rose-700'}`}>
                  <span aria-hidden="true">{comparison.role_match ? '✓' : '✗'}</span>
                  <span>{comparison.role_match ? 'true (MATCH)' : 'false (MISMATCH)'}</span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
