const API_BASE = 'http://127.0.0.1:8000'

async function fetchExportToCSV(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/api/process-fixed`, {
    method: 'POST',
    body: formData,
  })

  const text = await response.text()
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${text}`)
  return JSON.parse(text)
}

/**
 * Process multiple files, each with its own product quantity.
 * @param {File[]} files
 * @param {object} workersProfile
 * @param {number|number[]} quantities - single number (legacy) or array matching files
 * @param {string|null} timeUnit - 'minutes', 'seconds', or null for auto-detect
 */
export async function fetchMultiProcess(files, workersProfile, quantities, timeUnit = null) {
  const formData = new FormData()
  files.forEach(f => formData.append('files', f))
  formData.append('workers_profile', JSON.stringify(workersProfile))
  if (timeUnit) formData.append('time_unit', timeUnit)

  if (Array.isArray(quantities)) {
    formData.append('sample_quantities', JSON.stringify(quantities))
    formData.append('sample_quantity', String(quantities.reduce((s, q) => s + q, 0)))
  } else {
    const qty = Math.max(1, parseInt(quantities) || 1)
    formData.append('sample_quantity', String(qty))
    formData.append('sample_quantities', JSON.stringify(files.map(() => qty)))
  }

  const response = await fetch(`${API_BASE}/api/process-multi`, {
    method: 'POST',
    body: formData,
  })

  const text = await response.text()
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${text}`)
  return JSON.parse(text)
}

/**
 * Process a single file (CSV or XLSX) via the fixed endpoint.
 * @param {File} file
 * @param {string|null} timeUnit
 */
export async function fetchProcessFixed(file, timeUnit = null) {
  const formData = new FormData()
  formData.append('file', file)
  if (timeUnit) formData.append('time_unit', timeUnit)

  const response = await fetch(`${API_BASE}/api/process-fixed`, {
    method: 'POST',
    body: formData,
  })

  const text = await response.text()
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${text}`)
  return JSON.parse(text)
}

/**
 * Import XLSX with column mapping info returned.
 * @param {File} file
 * @param {string|null} timeUnit
 */
export async function fetchImportXlsx(file, timeUnit = null) {
  const formData = new FormData()
  formData.append('file', file)
  if (timeUnit) formData.append('time_unit', timeUnit)

  const response = await fetch(`${API_BASE}/api/import-xlsx`, {
    method: 'POST',
    body: formData,
  })

  const text = await response.text()
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${text}`)
  return JSON.parse(text)
}

/**
 * Export operations data to XLSX via backend.
 * @param {object[]} rows - array of operation objects
 * @returns {Promise<Blob>} - XLSX blob
 */
export async function fetchExportXlsx(rows) {
  const formData = new FormData()
  formData.append('data', JSON.stringify(rows))

  const response = await fetch(`${API_BASE}/api/export-xlsx`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`HTTP ${response.status}: ${text}`)
  }

  return response.blob()
}

export default fetchExportToCSV
