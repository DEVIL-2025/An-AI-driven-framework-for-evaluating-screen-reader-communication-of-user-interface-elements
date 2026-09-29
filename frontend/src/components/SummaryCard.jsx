export default function SummaryCard({ title, value, subtitle, icon, statusType }) {
  const getStatusBadge = () => {
    if (!statusType) return null
    const s = String(statusType).toLowerCase()
    if (s === 'completed') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" aria-hidden="true"></span>
          Completed
        </span>
      )
    }
    if (s === 'running') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 animate-pulse">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500" aria-hidden="true"></span>
          Running...
        </span>
      )
    }
    if (s === 'queued') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500" aria-hidden="true"></span>
          Queued
        </span>
      )
    }
    if (s === 'failed') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
          <span className="w-1.5 h-1.5 rounded-full bg-rose-500" aria-hidden="true"></span>
          Failed
        </span>
      )
    }
    return null
  }

  const getStatusDot = () => {
    if (!statusType) return null
    const s = String(statusType).toLowerCase()
    if (s === 'completed') {
      return (
        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0" aria-hidden="true" />
      )
    }
    if (s === 'running') {
      return (
        <span className="relative flex h-2.5 w-2.5 shrink-0" aria-hidden="true">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500"></span>
        </span>
      )
    }
    if (s === 'queued') {
      return (
        <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0" aria-hidden="true" />
      )
    }
    if (s === 'failed') {
      return (
        <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shrink-0" aria-hidden="true" />
      )
    }
    return null
  }

  const s = statusType ? String(statusType).toLowerCase().trim() : ''
  const valStr = value ? String(value).toLowerCase().trim() : ''
  const isRedundantStatus = s && (valStr === s || valStr.startsWith(s))

  return (
    <div className="glass-card glass-card-hover rounded-2xl p-5 flex flex-col justify-between overflow-hidden">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-700 truncate">
          {title}
        </span>
        <div className="p-2 rounded-xl bg-slate-100 text-slate-700 shrink-0" aria-hidden="true">
          {icon}
        </div>
      </div>

      <div className="mt-4">
        {statusType ? (
          <div className="flex items-center gap-2.5 flex-wrap min-w-0">
            {getStatusDot()}
            <span className="text-2xl sm:text-3xl font-extrabold text-slate-950 tracking-tight truncate">
              {value}
            </span>
            {!isRedundantStatus && getStatusBadge()}
          </div>
        ) : (
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-950 tracking-tight truncate">
            {value}
          </div>
        )}
        <p className="text-xs text-slate-700 mt-1.5 font-medium leading-relaxed truncate">
          {subtitle}
        </p>
      </div>
    </div>
  )
}
