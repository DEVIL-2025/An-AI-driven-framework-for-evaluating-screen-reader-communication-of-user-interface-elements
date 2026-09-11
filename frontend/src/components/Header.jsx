export default function Header({ currentView, onViewChange }) {
  return (
    <header className="border-b border-indigo-100/70 bg-white/75 backdrop-blur-md sticky top-0 z-20 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="flex items-center gap-3 text-left focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-xl p-1 -ml-1 transition-opacity hover:opacity-90 cursor-pointer"
          title="Reload page"
        >
          <div className="w-10 h-10 rounded-xl bg-white border border-slate-200/80 shadow-xs flex items-center justify-center p-1.5 overflow-hidden">
            <img
              src="/logo.png"
              alt="AI Accessibility Analyzer Logo"
              className="w-full h-full object-contain"
            />
          </div>
          <div>
            <h1 className="text-lg font-extrabold text-slate-950 tracking-tight leading-tight">
              AI Accessibility Analyzer
            </h1>
            <p className="text-xs font-semibold text-slate-600 hidden sm:block">
              Web accessibility testing with screen reader synchronization
            </p>
          </div>
        </button>

        <nav aria-label="Main Navigation">
          {currentView === 'history' ? (
            <button
              type="button"
              onClick={() => onViewChange && onViewChange('dashboard')}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100/80 border border-blue-200/80 rounded-xl transition-all shadow-xs focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Dashboard
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onViewChange && onViewChange('history')}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50/90 border border-slate-200/90 rounded-xl transition-all shadow-xs focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
              title="View previous accessibility audits"
            >
              <svg
                className="w-3.5 h-3.5 text-slate-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              Audit History
            </button>
          )}
        </nav>
      </div>
    </header>
  )
}
