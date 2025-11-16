async function fetchExportToCSV(file, workers) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('workers', JSON.stringify(workers));

  const response = await fetch('http://127.0.0.1:8000/api/process', {
    method: 'POST',
    body: formData,
  });
const text = await response.text()
console.log('Raw response:', text)  // ← Побачиш, що саме прийшло

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${text}`)
  }

  let result
  try {
    result = JSON.parse(text)
  } catch (e) {
    throw new Error('Invalid JSON: ' + text)
  }

  return result
}

export default fetchExportToCSV;