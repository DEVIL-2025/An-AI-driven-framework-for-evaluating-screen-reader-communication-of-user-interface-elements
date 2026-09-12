import { useState } from 'react'
import ViolationDetails from './ViolationDetails'

export default function ViolationCard({ violation }) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!violation) return null

  const currentViolation = violation
  const {
    violation_id,
    severity,
    wcag,
    rule_id,
    rule_name,
    confidence,
    title,
    description,
  } = currentViolation

  const displayWCAG = wcag || rule_id || "WCAG 1.1.1"
  const displayConfidence =
    typeof confidence === "number" ? `${Math.round(confidence * 100)}%` : confidence

  const getSeverityBadge = () => {
    switch (severity?.toUpperCase()) {
      case "CRITICAL":
        return "bg-rose-50 text-rose-700 border-rose-200"
      case "MAJOR":
        return "bg-amber-50 text-amber-800 border-amber-200"
      case "MINOR":
        return "bg-blue-50 text-blue-700 border-blue-200"
      default:
        return "bg-slate-50 text-slate-700 border-slate-200"
    }
  }

  return (
    <article
      aria-labelledby={`violation-title-${violation_id}`}
      className="glass-card rounded-3xl p-6 sm:p-7 transition-all"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1.5 max-w-2xl">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${getSeverityBadge()}`}
            >
              {severity}
            </span>
            <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-800 border border-slate-300">
              {displayWCAG} · {rule_name || "Non-text Content"}
            </span>
            <span className="text-xs text-slate-700 font-semibold">
              Confidence: <strong className="text-slate-950 font-bold">{displayConfidence}</strong>
            </span>
            <span className="text-xs font-mono font-bold text-slate-600">
              ID: {violation_id}
            </span>
          </div>

          <h4
            id={`violation-title-${violation_id}`}
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
          aria-controls={`details-${violation_id}`}
          className={`inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl transition-all shadow-xs focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer ${
            isExpanded
              ? "bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300"
              : "bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200"
          }`}
        >
          <span>{isExpanded ? "Hide Details" : "View Details"}</span>
          <svg
            className={`w-3.5 h-3.5 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {/* Primary Technical Description */}
      <div className="mt-4 text-sm text-slate-700 leading-relaxed bg-white/90 rounded-2xl p-4 border border-slate-200/80 shadow-xs">
        <p>{description}</p>
      </div>

      {/* Expandable Detailed View */}
      {isExpanded && (
        <div id={`details-${violation_id}`}>
          <ViolationDetails violation={currentViolation} />
        </div>
      )}
    </article>
  )
}
