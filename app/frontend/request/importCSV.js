async function fetchExportToCSV(file) {
  const formData = new FormData()
  formData.append('file', file)
  // workers більше не потрібні — бекенд сам їх знайде

  const response = await fetch('http://127.0.0.1:8000/api/process-fixed', {
    method: 'POST',
    body: formData,
  })

  const text = await response.text()
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${text}`)

  return JSON.parse(text)
}

export default fetchExportToCSV