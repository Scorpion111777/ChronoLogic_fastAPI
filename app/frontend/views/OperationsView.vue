<script setup>
import { ref, computed } from 'vue'
import FilterIcon from '../assets/icons/FilterIcon.vue'
import SearchIcon from '../assets/icons/SearchIcon.vue'
import Papa from 'papaparse'
import './styles/OperationsViewStyles.css'
import fetchExportToCSV from '../request/importCSV.js'
const operations = ref([])
const workers = ref([])


// логіка пошуку
const searchQuery = ref('')
const isSortMenuOpen = ref(false)
const sortConfig = ref({ key: 'worker', direction: 'asc' })

// логіка кольорів
const colorPalette = [
  '#FF6B6B',
  '#54D6B1',
  '#6B9AFF',
  '#F7D154',
  '#B36BFF',
  '#FF6BF1',
  '#FF936B',
  '#4CE0E0',
  '#FF8A80',
  '#FFB080',
  '#B0FF80',
  '#80B0FF',
  '#B080FF',
  '#FF80FF',
  '#9BF6FF',
  '#A0C4FF',
]
const workerColorMap = computed(() => {
  const map = new Map()
  const uniqueWorkers = [...new Set(operations.value.map((op) => op.worker))]
  uniqueWorkers.forEach((workerName, index) => {
    const color = colorPalette[index % colorPalette.length]
    map.set(workerName, color)
  })
  return map
})
function getWorkerColor(workerName) {
  return workerColorMap.value.get(workerName) || '#FFFFFF'
}
function getRowStyle(workerName) {
  const color = getWorkerColor(workerName)
  return { backgroundColor: `${color}AA` }
}

// сортування

const filteredOperations = computed(() => {
  let result = operations.value
  const query = searchQuery.value.toLowerCase()
  if (query) {
    result = result.filter(
      (op) =>
        (op.name && op.name.toLowerCase().includes(query)) ||
        (op.num && op.num.toLowerCase().includes(query)) ||
        (op.worker && op.worker.toLowerCase().includes(query)) ||
        (op.equipment && op.equipment.toLowerCase().includes(query)) ||
        (op.conditions && op.conditions.toLowerCase().includes(query)),
    )
  }
  return result
})

const sortedOperations = computed(() => {
  const { key, direction } = sortConfig.value
  const sortable = [...filteredOperations.value]

  sortable.sort((a, b) => {
    let valA = a[key]
    let valB = b[key]

    let result = 0
    if (typeof valA === 'string') {
      result = valA.localeCompare(valB)
    } else {
      valA = valA || 0
      valB = valB || 0
      result = valA - valB
    }

    return direction === 'asc' ? result : -result
  })

  return sortable
})

const groupedOperations = computed(() => {
  const result = []

  if (sortedOperations.value.length === 0) {
    return result
  }

  for (let i = 0; i < sortedOperations.value.length; i++) {
    const currentOp = sortedOperations.value[i]
    const isGroupStart = i === 0 || sortedOperations.value[i - 1].worker !== currentOp.worker

    if (isGroupStart) {
      let rowspan = 1
      for (let j = i + 1; j < sortedOperations.value.length; j++) {
        if (sortedOperations.value[j].worker === currentOp.worker) {
          rowspan++
        } else {
          break
        }
      }
      result.push({
        op: currentOp,
        isGroupStart: true,
        rowspan: rowspan,
      })
    } else {
      result.push({
        op: currentOp,
        isGroupStart: false,
        rowspan: 0,
      })
    }
  }
  return result
})

const getSortLabel = computed(() => {
  const { key, direction } = sortConfig.value

  const dirArrow = direction === 'asc' ? '↑' : '↓'
  let dirLabel = ''
  if (key === 'worker') {
    dirLabel = direction === 'asc' ? 'А-Я / ↑' : 'Я-А / ↓'
  } else {
    dirLabel = `${dirArrow}`
  }

  switch (key) {
    case 'worker':
      return `Сорт: Виконавець ${dirLabel}`
    case 'time':
      return `Сорт: Час ${dirLabel}`
    case 'rank':
      return `Сорт: Розряд ${dirLabel}`
    case 'num':
      return `Сорт: № Операції ${dirLabel}`
    default:
      return 'Сортування'
  }
})

// обробники подій
function goBack() {
  window.history.back()
}

//сортування
function setSort(key) {
  if (sortConfig.value.key === key) {
    sortConfig.value.direction = sortConfig.value.direction === 'asc' ? 'desc' : 'asc'
  } else {
    sortConfig.value.key = key
    sortConfig.value.direction = 'asc'
  }
  isSortMenuOpen.value = false
}



function parseCombinedCSV(text) {
  const lines = text.trim().split('\n').map(l => l.trim())
  const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''))

  const workerRows = []
  const operationRows = []

  lines.slice(1).forEach(line => {
    const values = line.split(',').map(v => v.trim().replace(/^"|"$/g, ''))
    const row = {}
    headers.forEach((h, i) => row[h] = values[i] || '')

    if (row['Назва технологічної операції']?.includes('ВСЬОГО ДЛЯ РОБІТНИКА')) {
      // Робітник: Блок, Робітник, Розряд, Обладнання
      const id = row['Робітник'] || `w-${crypto.randomUUID().slice(0,4)}`
      workerRows.push({
        id,
        grade: parseInt(row['Розряд']) || 1,
        equipment: (row['Обладнання'] || '').trim()
      })
    } else if (row['№ п/п'] && row['№ тех.оп.']) {
      operationRows.push(row)
    }
  })

  return { workers: workerRows, operations: operationRows }
}




// csv таблиця
// Повністю видаліть вашу стару функцію parseCombinedCSV
// ...

// Замініть вашу стару функцію handleFileUpload на цю:
async function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file || !file.name.endsWith('.csv')) {
    alert('Завантажуйте лише CSV-файл!')
    return
  }

  try {
    // Відправляємо тільки файл — бекенд сам розбере робітників і все інше
    const result = await fetchExportToCSV(file, []) // другий параметр порожній або можна взагалі прибрати в fetchExportToCSV

    if (!result.success || !Array.isArray(result.data)) {
      throw new Error(result.error || 'Помилка обробки на сервері')
    }

    // Заповнюємо таблицю з готового JSON від бекенду
    operations.value = result.data.map(row => ({
      id: crypto.randomUUID(),
      num: row['№ тех.оп.'] || '',
      name: row['Назва технологічної операції'] || '',
      time: row['Затрати часу, хв'] || 0,
      rank: row['Розряд'] || 4,
      equipment: row['Обладнання'] || '',
      conditions: row['Технічні умови'] || '',
      worker: row['Робітник'] || '',
    }))

    // Оновлюємо workers (якщо треба для кольорів і групування)
    const uniqueWorkers = [...new Set(result.data.map(r => r['Робітник']).filter(Boolean))]
    workers.value = uniqueWorkers.map((id, i) => ({
      id: String(id),
      grade: 4,
      equipment: ''
    }))


    // Автозавантаження
    const blob = new Blob([result.csv], { type: 'text/csv;charset=utf-8-sig' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'result.csv'
    a.click()
    URL.revokeObjectURL(url)

  } catch (err) {
    alert('Помилка: ' + (err.message || 'Не вдалося обробити файл'))
    console.error(err)
  }
}

function exportToCSV() {
  if (operations.value.length === 0) {
    alert('Немає даних для експорту!')
    return
  }

  const dataToExport = operations.value.map((op) => {
    return {
      '№ Тех. операції': op.num,
      'Назва технологічної операції': op.name,
      'Затрати часу, хв': op.time,
      Розряд: op.rank,
      Обладнання: op.equipment,
      'Технічні умови': op.conditions,
      Виконавець: op.worker,
    }
  })

  const csv = Papa.unparse(dataToExport, {
    header: true,
  })

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', 'edited_operations.csv')
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function addNewRow() {
  operations.value.push({
    id: crypto.randomUUID(),
    num: '',
    name: '',
    time: null,
    rank: null,
    equipment: '',
    conditions: '',
    worker: '',
  })
}
</script>
// головна сторінка
<template>
  <main class="operations-page">
    <header class="app-header">
      <button @click="goBack" class="header-back-link">← Назад</button>

      <img src="../assets/icons/logo.svg" alt="Chronologic Logo" class="header-logo-img" />

      <div class="header-user-icon"></div>
    </header>

    <div class="content-wrapper">
      <div class="filter-bar">
        <div class="sort-menu-wrapper">
          <button @click="isSortMenuOpen = !isSortMenuOpen" class="filter-btn">
            {{ getSortLabel }} <FilterIcon />
          </button>

          <div v-if="isSortMenuOpen" class="sort-menu">
            <button @click="setSort('worker')" class="sort-menu-item">
              За Виконавцем
              <span v-if="sortConfig.key === 'worker'">{{
                sortConfig.direction === 'asc' ? '↑' : '↓'
              }}</span>
            </button>
            <button @click="setSort('time')" class="sort-menu-item">
              За Часом
              <span v-if="sortConfig.key === 'time'">{{
                sortConfig.direction === 'asc' ? '↑' : '↓'
              }}</span>
            </button>
            <button @click="setSort('rank')" class="sort-menu-item">
              За Розрядом
              <span v-if="sortConfig.key === 'rank'">{{
                sortConfig.direction === 'asc' ? '↑' : '↓'
              }}</span>
            </button>
            <button @click="setSort('num')" class="sort-menu-item">
              За № Операції
              <span v-if="sortConfig.key === 'num'">{{
                sortConfig.direction === 'asc' ? '↑' : '↓'
              }}</span>
            </button>
          </div>
        </div>

        <div class="search-input-wrapper">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search all fields..."
            class="search-input"
          />
          <button class="search-icon-btn" aria-label="Пошук">
            <SearchIcon class="search-icon-svg" />
          </button>
        </div>
      </div>

      <div class="table-container">
        <table class="operations-table">
          <thead>
            <tr>
              <th>№</th>
              <th>№ Тех. операції</th>
              <th>Назва технологічної операції</th>
              <th>Затрати часу, хв</th>
              <th>Розряд</th>
              <th>Обладнання</th>
              <th>Технічні умови</th>
              <th>Виконавець</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="groupedOperations.length === 0">
              <td :colspan="9" class="empty-table-cell">
                Не знайдено жодних операцій. Спробуйте змінити фільтри або завантажити CSV.
              </td>
            </tr>
            <template v-for="(group, index) in groupedOperations" :key="group.op.id">
              <tr :style="getRowStyle(group.op.worker)">
                <td>{{ index + 1 }}</td>

                <td>
                  <input v-model="group.op.num" class="table-input" />
                </td>

                <td>
                  <input v-model="group.op.name" class="table-input" />
                </td>

                <td>
                  <input
                    v-model.number="group.op.time"
                    type="number"
                    step="0.1"
                    class="table-input table-input-number"
                  />
                </td>

                <td>
                  <input
                    v-model.number="group.op.rank"
                    type="number"
                    step="1"
                    class="table-input table-input-number"
                  />
                </td>

                <td>
                  <input v-model="group.op.equipment" class="table-input" />
                </td>

                <td class="conditions-cell">
                  <input v-model="group.op.conditions" class="table-input" />
                </td>

                <td>
                  <input v-model="group.op.worker" class="table-input" />
                </td>

                <td v-if="group.isGroupStart" :rowspan="group.rowspan" class="action-cell-grouped">
                  <button class="view-btn">Переглянути</button>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <div class="table-actions-bar">
        <label for="file-upload" class="action-btn"> Завантажити CSV </label>
        <input id="file-upload" type="file" @change="handleFileUpload" accept=".csv" />

        <button @click="addNewRow" class="action-btn">Додати рядок</button>

        <button @click="exportToCSV" class="action-btn export-btn">Експорт / Зберегти</button>
      </div>
    </div>
  </main>
</template>

