import { useState } from 'react'
import ViolationDetails from './ViolationDetails'

export default function ViolationCard({ violation }) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Default fallback static violation object matching current API structure
  const currentViolation = violation || {
    violation_id: "AI-001",
    scope: "ELEMENT",
    element_reference: {
      direction: "forward",
      step: 1,
    },
    rule_id: "WCAG 1.1.1",
    rule_name: "Non-text Content",
    severity: "MAJOR",
    confidence: 0.95,
    title: "Unlabeled graphic link",
    description:
      "An image link (anchor tag enclosing an image) is announced by NVDA as an 'Unlabeled graphic' with the name 'logo.', lacking a descriptive alternative text that conveys its purpose or destination.",
    ai_rationale:
      "In step 1, Selenium inspects an anchor tag with class 'navbar-brand', and NVDA announces 'logo. ... Unlabeled graphic'. This indicates the image inside or the link itself lacks an appropriate alt text or accessible name, relying on generic fallback text ('logo.').",
    user_impact:
      "Screen reader users encountering an unlabeled graphic link will only hear 'logo.' without understanding what organization or site the logo represents or where the link navigates.",
    wcag_context:
      "WCAG 2.1 Success Criterion 1.1.1 Non-Text Content requires all non-text content that is presented to the user has a text alternative that serves the equivalent purpose.",
    recommendation:
      "Provide a descriptive 'alt' attribute on the inner image element (e.g., alt='[Organization Name] Home') or an aria-label on the anchor element.",
    developer_guidance:
      "Ensure the image inside the navbar brand link has a meaningful alt attribute describing the brand or logo, such as alt='[Organization Name] Logo'.",
    evidence: {
      selenium: {
        tag: "a",
        href: "https://makaut1.ucanapply.com/smartexam/public/#",
        class: "navbar-brand",
        expected_roles: ["button", "link", "graphic link"],
      },
      nvda: {
        name: "logo.",
        role: "graphic link",
        attributes: ["same page"],
        description: "To get missing image descriptions, open the context menu.",
        raw_text:
          "logo. To get missing image descriptions, open the context menu.  Unlabeled graphic    same page  lin",
      },
      comparison: {
        status: "ROLE_MATCH_NAME_UNLABELLED",
        name_match: false,
        role_match: true,
      },
    },
  }

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
