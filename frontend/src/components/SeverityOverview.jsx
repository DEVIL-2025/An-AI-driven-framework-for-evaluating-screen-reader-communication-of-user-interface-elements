export default function SeverityOverview({ critical = 0, major = 0, minor = 0, info = 0 }) {
  const levels = [
    {
      id: 'critical',
      label: 'Critical',
      count: critical,
      description: 'Completely blocks accessibility',
      bgClass: 'bg-rose-50/70',
      borderClass: 'border-rose-200/80',
      textClass: 'text-rose-700',
      badgeClass: 'bg-rose-500 text-white',
    },
    {
      id: 'major',
      label: 'Major',
      count: major,
      description: 'Significant barrier or confusion',
      bgClass: 'bg-amber-50/70',
      borderClass: 'border-amber-200/80',
      textClass: 'text-amber-800',
      badgeClass: 'bg-amber-500 text-white',
    },
    {
      id: 'minor',
      label: 'Minor',
      count: minor,
      description: 'Low-impact or structural defect',
      bgClass: 'bg-blue-50/70',
      borderClass: 'border-blue-200/80',
      textClass: 'text-blue-700',
      badgeClass: 'bg-blue-500 text-white',
    },
    {
      id: 'info',
      label: 'Info',
      count: info,
      description: 'Advisory or speech enhancement',
      bgClass: 'bg-slate-50/70',
      borderClass: 'border-slate-200/80',
      textClass: 'text-slate-700',
      badgeClass: 'bg-slate-500 text-white',
    },
  ]

  return (
    <section aria-labelledby="severity-heading" className="w-full">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 id="severity-heading" className="text-base font-extrabold text-slate-950 tracking-tight">
            Severity Distribution
          </h3>
          <p className="text-xs text-slate-600 font-medium">
            Categorization of detected violations by assistive technology barrier level
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {levels.map((lvl) => (
          <div
            key={lvl.id}
            className={`rounded-2xl border p-4 backdrop-blur-md flex flex-col justify-between shadow-xs transition-all hover:shadow-md ${lvl.bgClass} ${lvl.borderClass}`}
          >
            <div className="flex items-center justify-between">
              <span className={`text-xs font-extrabold uppercase tracking-wider ${lvl.textClass}`}>
                {lvl.label}
              </span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-mono font-bold shadow-xs ${lvl.badgeClass}`}
                aria-label={`${lvl.count} ${lvl.label} violations`}
              >
                {lvl.count}
              </span>
            </div>
            <div className="mt-3">
              <span className="text-3xl font-extrabold text-slate-950 tracking-tight">
                {lvl.count}
              </span>
              <p className="text-xs text-slate-700 mt-1.5 font-medium leading-relaxed">
                {lvl.description}
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
