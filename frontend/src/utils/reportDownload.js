/**
 * Utility functions for generating understandable report filenames and downloading
 * AI Accessibility Reports directly in the client browser.
 */

/**
 * Generates an understandable, human-readable filename for an AI accessibility report.
 * Dynamically sanitizes the target website domain and path, appending the audit date.
 *
 * Examples:
 * - https://www.flipkart.com/ -> flipkart-com_ai_accessibility_report_2026-09-29.json
 * - https://www.irctc.co.in/nget/train-search -> irctc-co-in_nget-train-search_ai_accessibility_report_2026-09-29.json
 * - https://makautwb.ac.in/ -> makautwb-ac-in_ai_accessibility_report_2026-09-29.json
 *
 * @param {string} url - Target website URL
 * @param {string|Date} [timestamp] - Audit creation timestamp or current date
 * @returns {string} Understandable filename for the downloaded report
 */
export function generateReportFilename(url, timestamp = null) {
  let siteSlug = 'website'

  try {
    const rawUrl = url && (url.startsWith('http://') || url.startsWith('https://')) ? url : `https://${url || ''}`
    const parsed = new URL(rawUrl)
    let host = (parsed.hostname || '').toLowerCase().replace(/^www\./, '')
    // Replace dots and special characters in hostname with dashes for safe filesystem naming
    const cleanHost = host.replace(/[^a-z0-9_-]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '')

    // Extract first meaningful path segments (up to 30 chars) if present
    const cleanPath = (parsed.pathname || '')
      .toLowerCase()
      .replace(/^\/+|\/+$/g, '')
      .replace(/[^a-z0-9_-]/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')

    if (cleanPath && cleanPath.length > 0 && cleanPath.length <= 30) {
      siteSlug = `${cleanHost}_${cleanPath}`
    } else if (cleanHost) {
      siteSlug = cleanHost
    }
  } catch (_) {
    siteSlug = (url || 'website')
      .replace(/https?:\/\//i, '')
      .replace(/[^a-z0-9_-]/gi, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
      .slice(0, 30) || 'website'
  }

  // Extract or generate date string in YYYY-MM-DD format
  let dateStr = ''
  if (timestamp) {
    try {
      const d = new Date(timestamp)
      if (!isNaN(d.getTime())) {
        dateStr = d.toISOString().split('T')[0]
      }
    } catch (_) {}
  }
  if (!dateStr) {
    dateStr = new Date().toISOString().split('T')[0]
  }

  return `${siteSlug}_ai_accessibility_report_${dateStr}.json`
}

/**
 * Downloads the AI Accessibility Analysis report as a formatted JSON file.
 *
 * @param {Object} auditResult - The audit object containing analysis, url, audit_id, etc.
 */
export function downloadReportAsJson(auditResult) {
  if (!auditResult) return

  // Extract the primary AI analysis report object (conforming to AIAccessibilityAnalysisReport)
  const reportPayload = auditResult.analysis || auditResult.result?.analysis || auditResult

  // Ensure top-level identifying metadata is preserved
  const reportToDownload = {
    ...reportPayload,
    audit_id: auditResult.audit_id || reportPayload.audit_id || undefined,
    url: auditResult.url || reportPayload.url || undefined,
    created_at: auditResult.created_at || reportPayload.created_at || undefined,
  }

  const filename = generateReportFilename(auditResult.url || reportToDownload.url, auditResult.created_at)
  const jsonContent = JSON.stringify(reportToDownload, null, 2)
  const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8' })
  const blobUrl = URL.createObjectURL(blob)

  const downloadLink = document.createElement('a')
  downloadLink.href = blobUrl
  downloadLink.download = filename
  document.body.appendChild(downloadLink)
  downloadLink.click()
  document.body.removeChild(downloadLink)
  URL.revokeObjectURL(blobUrl)
}
