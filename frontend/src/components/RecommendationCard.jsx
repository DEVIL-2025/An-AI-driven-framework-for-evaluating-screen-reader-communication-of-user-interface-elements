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
    element_reference,
  } = recommendation

  // Robust multi-schema field resolution across AI report formats
  const rationaleText = recommendation.ai_rationale || recommendation.rationale
  const guidanceText =
    recommendation.developer_guidance ||
    recommendation.remediation_guidance ||
    recommendation.recommendation
  const impactText = recommendation.user_impact
  const relatedGuidance = recommendation.related_guidance
  const codeExample = recommendation.code_example

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
            {element_reference && element_reference.step != null && (
              <span className="text-xs font-mono font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                Step {element_reference.step}{element_reference.direction ? ` (${element_reference.direction})` : ''}
              </span>
            )}
            {relatedGuidance && relatedGuidance.success_criterion && (
              <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                {relatedGuidance.relationship || 'Advisory'} to {relatedGuidance.success_criterion}
                {relatedGuidance.technique ? ` (${relatedGuidance.technique})` : ''}
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
        <div id={`rec-details-${recommendation_id}`} className="mt-4 space-y-4 pt-4 border-t border-blue-100">
          {/* Developer Remediation Guidance */}
          {guidanceText && (
            <div className="bg-emerald-50/70 rounded-2xl p-4 border border-emerald-200 space-y-1.5">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-900 uppercase tracking-wider">
                <svg className="w-4 h-4 text-emerald-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Developer Guidance & Remediation
              </div>
              <p className="text-xs text-slate-900 leading-relaxed font-medium">{guidanceText}</p>
            </div>
          )}

          {/* Rationale & User Impact Grid */}
          {(rationaleText || impactText) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {rationaleText && (
                <div className="bg-blue-50/70 rounded-2xl p-4 border border-blue-200 space-y-1.5">
                  <div className="flex items-center gap-2 text-xs font-bold text-blue-900 uppercase tracking-wider">
                    <svg className="w-4 h-4 text-blue-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    AI Rationale
                  </div>
                  <p className="text-xs text-slate-900 leading-relaxed font-medium">{rationaleText}</p>
                </div>
              )}

              {impactText && (
                <div className="bg-amber-50/70 rounded-2xl p-4 border border-amber-200 space-y-1.5">
                  <div className="flex items-center gap-2 text-xs font-bold text-amber-900 uppercase tracking-wider">
                    <svg className="w-4 h-4 text-amber-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    User Impact
                  </div>
                  <p className="text-xs text-slate-900 leading-relaxed font-medium">{impactText}</p>
                </div>
              )}
            </div>
          )}

          {/* Code Example Implementation */}
          {codeExample && (
            <div className="bg-slate-900 rounded-2xl p-4 text-slate-100 space-y-2">
              <div className="flex items-center gap-2 text-xs font-mono font-semibold text-slate-400 uppercase">
                <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
                Example Implementation
              </div>
              <pre className="text-xs font-mono overflow-x-auto p-3 bg-slate-950/80 rounded-xl text-emerald-300 border border-slate-800">
                <code>{codeExample}</code>
              </pre>
            </div>
          )}

          {/* Footer Note */}
          <div className="flex items-center gap-2 text-xs text-slate-500 italic pt-1">
            <svg className="w-4 h-4 text-blue-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>Informational best practice recommendation. Carries zero score penalty.</span>
          </div>
        </div>
      )}
    </article>
  )
}
