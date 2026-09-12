import EvidenceSection from './EvidenceSection'

export default function ViolationDetails({ violation }) {
  if (!violation) return null

  const {
    violation_id = "AI-001",
    user_impact,
    ai_rationale,
    wcag_context,
    recommendation,
    developer_guidance,
    element_reference,
    evidence,
  } = violation

  const engineName =
    violation.engine ||
    violation.ai_metadata?.model ||
    violation.ai_metadata?.provider ||
    'Gemini AI'

  return (
    <div className="mt-5 pt-5 border-t border-slate-200/80 space-y-5">
      {/* 1. Header meta banner */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-2xl bg-slate-50/90 border border-slate-200/90 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-slate-700 font-bold">Violation Identifier:</span>
          <span className="font-mono font-bold text-blue-800 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
            {violation_id}
          </span>
        </div>
        <div className="flex items-center gap-4 text-slate-700 font-medium">
          <span>Scope: <strong className="text-slate-950 font-bold">{violation.scope || 'ELEMENT'}</strong></span>
          <span>Engine: <strong className="text-slate-950 font-bold">{engineName}</strong></span>
        </div>
      </div>

      {/* 2. Analysis & Impact Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* User Impact */}
        <div className="rounded-2xl bg-amber-50/70 border border-amber-200 p-4 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-amber-900 uppercase tracking-wider">
            <svg className="w-4 h-4 text-amber-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            User Impact
          </div>
          <p className="text-xs text-slate-900 leading-relaxed font-medium">
            {user_impact || "User impact details not provided for this finding."}
          </p>
        </div>

        {/* AI Rationale */}
        <div className="rounded-2xl bg-blue-50/70 border border-blue-200 p-4 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-blue-900 uppercase tracking-wider">
            <svg className="w-4 h-4 text-blue-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            AI Rationale
          </div>
          <p className="text-xs text-slate-900 leading-relaxed font-medium">
            {ai_rationale || "AI rationale details not provided for this finding."}
          </p>
        </div>
      </div>

      {/* 3. WCAG Context */}
      <div className="rounded-2xl bg-indigo-50/70 border border-indigo-200 p-4 space-y-2">
        <div className="flex items-center gap-2 text-xs font-bold text-indigo-900 uppercase tracking-wider">
          <svg className="w-4 h-4 text-indigo-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          WCAG Normative Context
        </div>
        <p className="text-xs text-slate-900 leading-relaxed font-medium">
          {wcag_context || "WCAG normative context not specified."}
        </p>
      </div>

      {/* 4. Recommendation & Developer Code Fix */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Recommendation */}
        <div className="rounded-2xl bg-emerald-50/60 border border-emerald-200/80 p-4 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-emerald-800 uppercase tracking-wider">
            <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Remediation Recommendation
          </div>
          <p className="text-xs text-slate-700 leading-relaxed font-normal">
            {recommendation || "Remediation guidance not specified."}
          </p>
        </div>

        {/* Developer Guidance (Code format) */}
        <div className="rounded-2xl bg-slate-50/80 border border-slate-200/90 p-4 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-800 uppercase tracking-wider">
            <svg className="w-4 h-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
            Developer Code Guidance
          </div>
          <div className="rounded-xl bg-slate-900 p-3 border border-slate-800 text-[11px] font-mono text-emerald-300 overflow-x-auto shadow-inner">
            <code>
              {developer_guidance || "/* No specific code snippet provided. */"}
            </code>
          </div>
        </div>
      </div>

      {/* 5. Authoritative Evidence (Selenium + NVDA + Comparison) */}
      <EvidenceSection
        evidence={evidence}
        elementReference={element_reference}
      />
    </div>
  )
}
