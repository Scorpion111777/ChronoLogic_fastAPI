<script setup>
import { ref, computed } from 'vue'
import FilterIcon from '../assets/icons/FilterIcon.vue'
import SearchIcon from '../assets/icons/SearchIcon.vue'
import Papa from 'papaparse'

const operations = ref([])

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

// csv таблиця
function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file) return

  Papa.parse(file, {
    header: true,
    skipEmptyLines: true,
    complete: (results) => {
      if (!results || !results.data) {
        console.error('Parsing error or empty file')
        alert('Не вдалося розібрати файл. Можливо, він порожній або пошкоджений.')
        return
      }

      const parsedOperations = results.data.map((row, index) => ({
        id: crypto.randomUUID(),
        num: row['№ Тех. операції'] || '',
        name: row['Назва технологічної операції'] || 'Нова операція',
        time: parseFloat(String(row['Затрати часу, хв'] || 0).replace(',', '.')) || 0,
        rank: parseInt(row['Розряд'] || 1) || 1,
        equipment: row['Обладнання'] || '',
        conditions: row['Технічні умови'] || '',
        worker: row['Виконавець'] || 'Не призначено',
      }))

      operations.value = parsedOperations
    },
    error: (error) => {
      console.error('Error parsing CSV:', error)
      alert('Не вдалося розібрати файл. Перевірте консоль.')
    },
  })
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

<style scoped>
.operations-page {
  width: 100%;
  min-height: 100vh;
  background-color: #f4f5f7;
  box-sizing: border-box;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 30px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  width: 100%;
  box-sizing: border-box;
}

.header-back-link {
  text-decoration: none;
  color: #4e48eb;
  font-size: 16px;
  font-weight: 500;
  background-color: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
  font-family: inherit;
}

.header-logo-img {
  height: 45px;
  width: auto;
  display: block;
}

.header-user-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background-color: #f0f0f0;
  border: 1px solid #ddd;
}

.content-wrapper {
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 20px;
  margin-top: 20px;
  box-sizing: border-box;
}

.filter-bar {
  color: #919191;
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  flex-wrap: wrap;

  align-items: flex-start;
}

.sort-menu-wrapper {
  position: relative;
  z-index: 10;
}

.search-input-wrapper {
  position: relative;
  flex-grow: 1;
  min-width: 250px;
  z-index: 5;
}

.search-input {
  padding: 10px 40px 10px 15px;
  border: 1px solid #ccc;
  border-radius: 8px;
  font-size: 14px;
  background-color: #fff;
  width: 100%;
  box-sizing: border-box;
}

.search-input::placeholder {
  color: #c3c3cc;
}

.search-icon-svg {
  color: #c3c3cc;
  font-size: 16px;
  display: block;
}

.search-icon-btn {
  position: absolute;
  right: 0;
  top: 0;
  height: 100%;
  background: transparent;
  border: none;
  margin: 0;
  padding: 0 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-icon-btn:hover .search-icon-svg {
  color: #4e48eb;
}

.filter-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 15px;
  border-radius: 8px;
  font-size: 14px;
  border: 1px solid #d1d5db;
  background-color: #fff;
  color: #555;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  gap: 8px;
  white-space: nowrap;
}

.view-btn {
  padding: 5px 10px;
  border-radius: 20px;
  font-size: 12px;
  border: 1px solid #d1d5db;
  background-color: #fff;
  color: #374151;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  width: 100%;
  height: calc(100% - 10px);
}

.filter-btn:hover,
.view-btn:hover {
  background: linear-gradient(to right, #4e48eb, #8b3ab3);
  color: #fff;
  border-color: transparent;
}
.filter-btn:hover .filter-icon-svg {
  fill: #fff;
}

.sort-menu {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 5px;
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  width: 220px;
  display: flex;
  flex-direction: column;
  padding: 8px;
  box-sizing: border-box;
}

.sort-menu-item {
  background: none;
  border: none;
  text-align: left;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.sort-menu-item:hover {
  background-color: #f5f5f5;
}
.sort-menu-item span {
  font-size: 16px;
  color: #4e48eb;
}

.table-container {
  width: 100%;
  max-height: 70vh;
  overflow-y: auto;
  overflow-x: auto;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
  scrollbar-width: thin;
  scrollbar-color: #8b3ab3 #f1f1f1;
}

.operations-table {
  border-collapse: collapse;
  width: 100%;
}

.operations-table th,
.operations-table td {
  padding: 12px 15px;
  text-align: left;
  font-size: 14px;
  vertical-align: middle;
  border-right: 1px solid #e0e0e0;
}

.operations-table th {
  background-color: #fafafa;
  font-weight: 600;
  color: #6b7280;
  font-size: 12px;
  border-bottom: 2px solid #e0e0e0;
  white-space: nowrap;
}

.operations-table th:last-child {
  border-right: none;
}

.operations-table td {
  border-top: 1px solid #e0e0e0;
  color: #222;
}

.empty-table-cell {
  text-align: center;
  color: #999;
  font-style: italic;
  padding: 40px;
}

.action-cell-grouped {
  background-color: #ffffff;
  border-right: none;
  display: table-cell;
  vertical-align: middle;
  text-align: center;
}

.conditions-cell {
  min-width: 250px;
  max-width: 350px;
  white-space: normal;
}

.table-container::-webkit-scrollbar {
  width: 12px;
  height: 12px;
}
.table-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 10px;
}
.table-container::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #4e48eb, #8b3ab3);
  border-radius: 10px;
}
.table-container::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, #403bb1, #722f92);
}

.table-actions-bar {
  display: flex;
  gap: 15px;
  margin-top: 20px;
  padding: 15px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
  flex-wrap: wrap;
}

.action-btn,
label[for='file-upload'] {
  padding: 5px 15px;
  border-radius: 20px;
  font-size: 12px;
  border: 1px solid #d1d5db;
  background-color: #fff;
  color: #374151;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  display: inline-block;
  line-height: normal;
}

.action-btn:hover,
label[for='file-upload']:hover {
  background: linear-gradient(to right, #4e48eb, #8b3ab3);
  color: #fff;
  border-color: transparent;
  opacity: 1;
}

#file-upload {
  display: none;
}

.table-input {
  width: 100%;
  border: 1px solid transparent;
  background: transparent;
  padding: 8px;
  margin: -8px -9px;
  box-sizing: border-box;
  font-size: 14px;
  font-family: inherit;
  color: inherit;
  border-radius: 4px;
  transition: all 0.2s ease;
}
.table-input:hover {
  border-color: #ddd;
}
.table-input:focus {
  outline: 2px solid #4e48eb;
  border-color: #4e48eb;
  background: #fff;
}
.table-input-number {
  text-align: right;
  -moz-appearance: textfield;
}
.table-input-number::-webkit-outer-spin-button,
.table-input-number::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

/* адаптив */

@media (max-width: 768px) {
  .app-header {
    padding: 10px 15px;
  }
  .content-wrapper {
    padding: 15px;
    margin-top: 10px;
  }
}

@media (max-width: 640px) {
  .header-logo-img {
    height: 35px;
  }
  .header-back-link {
    font-size: 14px;
  }
  .header-user-icon {
    width: 32px;
    height: 32px;
  }

  .filter-bar {
    gap: 10px;
  }

  .sort-menu-wrapper {
    width: 100%;
    order: -1;
  }
  .filter-btn {
    width: 100%;
    justify-content: center;
  }
  .sort-menu {
    width: 100%;
  }
  .search-input-wrapper {
    width: 100%;
    min-width: unset;
  }

  .table-actions-bar {
    flex-direction: column;
    gap: 10px;
  }
  .action-btn,
  label[for='file-upload'] {
    width: 100%;
    text-align: center;
    padding: 10px 15px;
    box-sizing: border-box;
  }
}
</style>
