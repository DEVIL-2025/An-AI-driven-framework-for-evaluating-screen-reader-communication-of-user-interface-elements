/**
 * Frontend API Service for AI Accessibility Analyzer.
 * Wraps communication with the existing FastAPI backend (/api/audits).
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Initiates an accessibility audit for a given target website URL.
 * Submits POST /api/audits and polls GET /api/audits/{audit_id} until completed or failed.
 *
 * @param {string} url - Target website URL to audit
 * @param {number} [tabLimit=100] - Keyboard navigation steps
 * @param {boolean} [enableAi=true] - Enable Gemini AI remediation
 * @param {Function} [onStatusUpdate] - Optional callback receiving intermediate AuditResponse updates
 * @returns {Promise<Object>} Completed AuditResponse object
 */
export async function startAudit(url, tabLimit = 100, enableAi = true, onStatusUpdate = null) {
  if (!url || typeof url !== 'string' || !url.trim()) {
    throw new Error('Please enter a valid website URL.')
  }

  // 1. Submit Audit Request (POST /api/audits)
  let createRes
  try {
    createRes = await fetch(`${API_BASE_URL}/api/audits`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        url: url.trim(),
        tab_limit: tabLimit,
        enable_ai: enableAi,
      }),
    })
  } catch (netErr) {
    throw new Error(
      `Cannot connect to FastAPI backend at ${API_BASE_URL}. Ensure the backend server is running.`
    )
  }

  if (!createRes.ok) {
    let errorDetail = 'Failed to submit audit.'
    try {
      const errJson = await createRes.json()
      if (errJson.detail) {
        errorDetail = Array.isArray(errJson.detail)
          ? errJson.detail.map((d) => d.msg || d.message).join(', ')
          : String(errJson.detail)
      }
    } catch (_) {
      errorDetail = `Server returned HTTP ${createRes.status} (${createRes.statusText})`
    }
    throw new Error(errorDetail)
  }

  const initialData = await createRes.json()
  const auditId = initialData.audit_id

  if (!auditId) {
    throw new Error('Malformed backend response: missing audit_id.')
  }

  if (onStatusUpdate) {
    onStatusUpdate(initialData)
  }

  // If already completed immediately (or mock sync)
  if (initialData.status === 'completed') {
    return initialData
  }

  if (initialData.status === 'failed') {
    const msg = initialData.error?.message || 'Audit execution failed on server.'
    throw new Error(msg)
  }

  // 2. Poll Status (GET /api/audits/{audit_id})
  const POLL_INTERVAL_MS = 1500
  const MAX_POLL_ATTEMPTS = 200 // ~5 minutes max

  for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt++) {
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS))

    let statusRes
    try {
      statusRes = await fetch(`${API_BASE_URL}/api/audits/${auditId}`)
    } catch (pollNetErr) {
      // Temporary network jitter during polling; continue next attempt
      continue
    }

    if (!statusRes.ok) {
      throw new Error(`Failed to retrieve audit status (HTTP ${statusRes.status}).`)
    }

    const currentData = await statusRes.json()

    if (onStatusUpdate) {
      onStatusUpdate(currentData)
    }

    if (currentData.status === 'completed') {
      return currentData
    }

    if (currentData.status === 'failed') {
      const msg = currentData.error?.message || 'Audit execution failed on the backend.'
      throw new Error(msg)
    }
  }

  throw new Error('Audit timed out waiting for server completion.')
}

/**
 * Retrieves all historical audits from PostgreSQL (newest first).
 * Calls GET /api/audits
 *
 * @returns {Promise<Array<Object>>} List of AuditResponse objects
 */
export async function getAudits() {
  let res
  try {
    res = await fetch(`${API_BASE_URL}/api/audits`)
  } catch (err) {
    throw new Error(`Cannot connect to FastAPI backend at ${API_BASE_URL}. Ensure the backend server is running.`)
  }

  if (!res.ok) {
    throw new Error(`Failed to retrieve audit history (HTTP ${res.status}: ${res.statusText}).`)
  }

  return await res.json()
}

/**
 * Retrieves a single complete audit record by UUID.
 * Calls GET /api/audits/{auditId}
 *
 * @param {string} auditId - Audit UUID
 * @returns {Promise<Object>} Complete AuditResponse object
 */
export async function getAuditById(auditId) {
  if (!auditId) {
    throw new Error('Audit ID is required.')
  }

  let res
  try {
    res = await fetch(`${API_BASE_URL}/api/audits/${encodeURIComponent(auditId)}`)
  } catch (err) {
    throw new Error(`Cannot connect to FastAPI backend at ${API_BASE_URL}. Ensure the backend server is running.`)
  }

  if (!res.ok) {
    if (res.status === 404) {
      throw new Error(`Audit with ID '${auditId}' was not found.`)
    }
    throw new Error(`Failed to load audit details (HTTP ${res.status}: ${res.statusText}).`)
  }

  return await res.json()
}

/**
 * Checks connectivity with the FastAPI backend.
 * @returns {Promise<boolean>}
 */
export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/health`)
    return res.ok
  } catch (_) {
    return false
  }
}

/**
 * Clears all historical audit records in PostgreSQL.
 * Calls DELETE /api/audits
 *
 * @returns {Promise<Object>}
 */
export async function clearAudits() {
  let res
  try {
    res = await fetch(`${API_BASE_URL}/api/audits`, {
      method: 'DELETE',
    })
  } catch (err) {
    throw new Error(`Cannot connect to FastAPI backend at ${API_BASE_URL}. Ensure the backend server is running.`)
  }

  if (!res.ok) {
    throw new Error(`Failed to clear audit history (HTTP ${res.status}: ${res.statusText}).`)
  }

  return await res.json()
}

