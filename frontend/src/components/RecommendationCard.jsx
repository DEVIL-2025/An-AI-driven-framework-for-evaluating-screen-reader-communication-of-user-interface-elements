import { useState } from 'react'

export default function RecommendationCard({ recommendation }) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!recommendation) return null

  const {
    recommendation_id,
    category,
    scope,
    title,
    description,
    rationale,
    remediation_guidance,
    code_example,
    related_guidance,
  } = recommendation

  const getCategoryBadge = () => {
    switch (category?.toUpperCase()) {
      case 'BEST_PRACTICE':
        return 'bg-blue-50 text-blue-700 border-blue-200'
      case 'STRUCTURAL_ENHANCEMENT':
        return 'bg-indigo-50 text-indigo-700 border-indigo-200'
      case 'ADVISORY':
        return 'bg-teal-50 text-teal-700 border-teal-200'
      default:
        return 'bg-slate-50 text-slate-700 border-slate-200'
    }
  }

  return (
    <article
      aria-labelledby={`rec-title-${recommendation_id}`}
      className="glass-card rounded-3xl p-6 sm:p-7 transition-all border border-blue-100 bg-blue-50/20"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1.5 max-w-2xl">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${getCategoryBadge()}`}
            >
              {category?.replace(/_/g, ' ') || 'BEST PRACTICE'}
            </span>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
              {scope?.replace(/_/g, ' ') || 'PAGE LEVEL'}
            </span>
            {related_guidance && related_guidance.success_criterion && (
              <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                {related_guidance.relationship || 'Advisory'} to {related_guidance.success_criterion}
                {related_guidance.technique ? ` (${related_guidance.technique})` : ''}
              </span>
            )}
            <span className="text-xs font-mono font-bold text-slate-500">
              ID: {recommendation_id}
            </span>
          </div>

          <h4
            id={`rec-title-${recommendation_id}`}
            className="text-lg font-extrabold text-slate-950 tracking-tight pt-1"
          >
            {title}
          </h4>
        </div>

        {/* Expand / Collapse Button */}
        <button
          type="button"
          onClick={() => setIsExpanded((prev) => !prev)}
          aria-expanded={isExpanded}
          aria-controls={`rec-details-${recommendation_id}`}
          className={`inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl transition-all shadow-xs focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer ${
            isExpanded
              ? 'bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300'
              : 'bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200'
          }`}
        >
          <span>{isExpanded ? 'Hide Guidance' : 'View Guidance'}</span>
          <svg
            className={`w-3.5 h-3.5 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {/* Primary Description */}
      <div className="mt-4 text-sm text-slate-700 leading-relaxed bg-white/90 rounded-2xl p-4 border border-slate-200/80 shadow-xs">
        <p>{description}</p>
      </div>

      {/* Expandable Guidance */}
      {isExpanded && (
        <div id={`rec-details-${recommendation_id}`} className="mt-4 space-y-3 pt-3 border-t border-blue-100">
          {rationale && (
            <div className="bg-slate-50/80 rounded-2xl p-4 border border-slate-200">
              <h5 className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                Rationale & Impact
              </h5>
              <p className="text-xs text-slate-700 leading-relaxed">{rationale}</p>
            </div>
          )}

          {remediation_guidance && (
            <div className="bg-blue-50/60 rounded-2xl p-4 border border-blue-100">
              <h5 className="text-xs font-bold uppercase tracking-wider text-blue-800 mb-1">
                Suggested Remediation
              </h5>
              <p className="text-xs text-slate-700 leading-relaxed">{remediation_guidance}</p>
            </div>
          )}

          {code_example && (
            <div className="bg-slate-900 rounded-2xl p-4 text-slate-100">
              <h5 className="text-xs font-mono font-semibold text-slate-400 mb-2 uppercase">
                Example Implementation
              </h5>
              <pre className="text-xs font-mono overflow-x-auto p-2 bg-slate-950/60 rounded-xl text-emerald-300">
                <code>{code_example}</code>
              </pre>
            </div>
          )}

          <div className="flex items-center gap-2 text-xs text-slate-500 italic pt-1">
            <svg className="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>Informational best practice recommendation. Carries zero score penalty.</span>
          </div>
        </div>
      )}
    </article>
  )
}
