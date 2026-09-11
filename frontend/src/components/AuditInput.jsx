export default function AuditInput({
  url,
  setUrl,
  tabLimit,
  setTabLimit,
  onSubmit,
  isLoading,
  statusText,
  validationError,
}) {
  const handleSubmit = (e) => {
    e.preventDefault()
    if (!isLoading && onSubmit) {
      onSubmit()
    }
  }

  return (
    <section aria-labelledby="audit-input-heading" className="w-full">
      <div className="glass-card rounded-3xl p-6 sm:p-10 transition-all">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50/90 border border-blue-100 text-blue-700 text-xs font-semibold mb-3">
            <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse"></span>
            Automated Screen Reader Evaluation
          </div>
          <h2 id="audit-input-heading" className="text-2xl sm:text-4xl font-extrabold text-slate-950 tracking-tight leading-tight">
            Test any website for accessibility.
          </h2>
          <p className="text-sm sm:text-base text-slate-700 mt-2.5 max-w-2xl font-medium leading-relaxed">
            Enter a public URL and optional keyboard traversal limit to run automated testing with live screen reader synchronization and AI remediation.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <div className="flex flex-col md:flex-row items-start md:items-end gap-3.5">
            {/* Website URL Field */}
            <div className="w-full flex-1">
              <label htmlFor="website-url" className="block text-xs font-bold uppercase tracking-wider text-slate-800 mb-1.5">
                Website URL
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-500" aria-hidden="true">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                  </svg>
                </div>
                <input
                  type="url"
                  id="website-url"
                  name="website-url"
                  placeholder="https://example.com"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  disabled={isLoading}
                  required
                  className="w-full pl-11 pr-4 py-3 bg-white border border-slate-300 rounded-2xl text-slate-950 placeholder-slate-400 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all shadow-xs disabled:opacity-60 disabled:cursor-not-allowed"
                />
              </div>
            </div>

            {/* Tab Limit Field */}
            <div className="w-full md:w-44">
              <div className="flex items-center justify-between mb-1.5">
                <label htmlFor="tab-limit" className="block text-xs font-bold uppercase tracking-wider text-slate-800">
                  Tab Limit
                </label>
                <span className="text-[11px] font-bold text-slate-600">1 – 500</span>
              </div>
              <div className="relative">
                <input
                  type="number"
                  id="tab-limit"
                  name="tab-limit"
                  min="1"
                  max="500"
                  step="1"
                  value={tabLimit}
                  onChange={(e) => setTabLimit(e.target.value)}
                  disabled={isLoading}
                  required
                  aria-describedby="tab-limit-help"
                  className="w-full px-3.5 py-3 pr-14 bg-white border border-slate-300 rounded-2xl text-slate-950 placeholder-slate-400 text-sm font-mono font-bold focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all shadow-xs disabled:opacity-60 disabled:cursor-not-allowed"
                />
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3.5 text-xs text-slate-600 font-bold" aria-hidden="true">
                  steps
                </div>
              </div>
            </div>

            {/* Submit Button (matching 'Get Started' pill button from reference) */}
            <div className="w-full md:w-auto">
              <button
                type="submit"
                disabled={isLoading || !url.trim()}
                className="w-full md:w-auto inline-flex items-center justify-center gap-2 px-8 py-3.5 btn-primary-gradient disabled:opacity-60 disabled:cursor-not-allowed text-white font-bold text-sm rounded-2xl transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2"
              >
                {isLoading ? (
                  <>
                    <svg className="w-4 h-4 animate-spin text-blue-200" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>{statusText || 'Starting Audit...'}</span>
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>Start Audit</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Inline Validation Error if any */}
          {validationError && (
            <p id="tab-limit-help" className="text-xs text-rose-600 flex items-center gap-1.5 font-semibold" role="alert">
              <svg className="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span>{validationError}</span>
            </p>
          )}
        </form>
      </div>
    </section>
  )
}
