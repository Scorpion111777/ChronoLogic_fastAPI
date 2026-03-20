async function fetchExportToCSV(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch('http://127.0.0.1:8000/api/process-fixed', {
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
 */
export async function fetchMultiProcess(files, workersProfile, quantities) {
  const formData = new FormData()
  files.forEach(f => formData.append('files', f))
  formData.append('workers_profile', JSON.stringify(workersProfile))

  if (Array.isArray(quantities)) {
    formData.append('sample_quantities', JSON.stringify(quantities))
    formData.append('sample_quantity', String(quantities.reduce((s, q) => s + q, 0)))
  } else {
    const qty = Math.max(1, parseInt(quantities) || 1)
    formData.append('sample_quantity', String(qty))
    formData.append('sample_quantities', JSON.stringify(files.map(() => qty)))
  }

  const response = await fetch('http://127.0.0.1:8000/api/process-multi', {
    method: 'POST',
    body: formData,
  })

  const text = await response.text()
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${text}`)
  return JSON.parse(text)
}

export default fetchExportToCSV
