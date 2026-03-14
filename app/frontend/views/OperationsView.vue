<script setup>
import { ref, computed } from 'vue'
import FilterIcon from '../assets/icons/FilterIcon.vue'
import SearchIcon from '../assets/icons/SearchIcon.vue'
import Papa from 'papaparse'
import './styles/OperationsViewStyles.css'
import fetchExportToCSV from '../request/importCSV.js'

const operations = ref([])

// пошук / сортування
const searchQuery = ref('')
const isSortMenuOpen = ref(false)
const sortConfig = ref({ key: 'worker', direction: 'asc' })

// кольори по робітнику
const colorPalette = [
  '#FF6B6B','#54D6B1','#6B9AFF','#F7D154','#B36BFF',
  '#FF6BF1','#FF936B','#4CE0E0','#FF8A80','#FFB080',
  '#B0FF80','#80B0FF','#B080FF','#FF80FF','#9BF6FF','#A0C4FF',
]
const workerColorMap = computed(() => {
  const map = new Map()
  const uniqueWorkers = [...new Set(operations.value.map((op) => op.worker))]
  uniqueWorkers.forEach((w, i) => map.set(w, colorPalette[i % colorPalette.length]))
  return map
})
function getWorkerColor(w) { return workerColorMap.value.get(w) || '#FFFFFF' }
function getRowStyle(w) { return { backgroundColor: `${getWorkerColor(w)}AA` } }

// фільтр
const filteredOperations = computed(() => {
  const q = searchQuery.value.toLowerCase()
  if (!q) return operations.value
  return operations.value.filter(op =>
    ['block','worker','num','name','equipment','conditions'].some(k =>
      op[k] && String(op[k]).toLowerCase().includes(q)
    )
  )
})

// сортування
const sortedOperations = computed(() => {
  const { key, direction } = sortConfig.value
  return [...filteredOperations.value].sort((a, b) => {
    let vA = a[key], vB = b[key]
    let r = typeof vA === 'string' ? vA.localeCompare(vB) : (vA||0) - (vB||0)
    return direction === 'asc' ? r : -r
  })
})

// групування по робітнику
const groupedOperations = computed(() => {
  const ops = sortedOperations.value
  return ops.map((op, i) => {
    const isStart = i === 0 || ops[i - 1].worker !== op.worker
    let rowspan = 0
    if (isStart) {
      rowspan = 1
      for (let j = i + 1; j < ops.length && ops[j].worker === op.worker; j++) rowspan++
    }
    return { op, isGroupStart: isStart, rowspan }
  })
})

const getSortLabel = computed(() => {
  const { key, direction } = sortConfig.value
  const arrow = direction === 'asc' ? '↑' : '↓'
  const labels = { block: 'Блок', worker: 'Виконавець', time: 'Час', rank: 'Розряд', num: '№ Операції' }
  return `Сорт: ${labels[key] || key} ${arrow}`
})

function goBack() { window.history.back() }
function setSort(key) {
  if (sortConfig.value.key === key) {
    sortConfig.value.direction = sortConfig.value.direction === 'asc' ? 'desc' : 'asc'
  } else {
    sortConfig.value.key = key
    sortConfig.value.direction = 'asc'
  }
  isSortMenuOpen.value = false
}

// завантаження CSV
async function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file || !file.name.endsWith('.csv')) {
    alert('Завантажуйте лише CSV-файл!')
    return
  }
  try {
    const result = await fetchExportToCSV(file)
    if (!result.success || !Array.isArray(result.data)) {
      throw new Error(result.error || 'Помилка обробки на сервері')
    }
    operations.value = result.data.map(row => ({
      id: crypto.randomUUID(),
      block:      row['Блок'] || '',
      worker:     row['Робітник'] || '',
      rank:       row['Розряд'] || 0,
      equipment:  row['Обладнання'] || '',
      num:        row['№ п/п'] || '',
      techNum:    row['№ тех.оп.'] || '',
      name:       row['Назва технологічної операції'] || '',
      time:       row['Затрати часу, хв'] || 0,
      conditions: row['Технічні умови'] || '',
    }))
  } catch (err) {
    alert('Помилка: ' + (err.message || 'Не вдалося обробити файл'))
    console.error(err)
  }
}

// експорт CSV
function exportToCSV() {
  if (operations.value.length === 0) { alert('Немає даних для експорту!'); return }
  const data = operations.value.map((op, i) => ({
    'Блок':                          op.block || '',
    'Робітник':                      op.worker || '',
    'Розряд':                        op.rank || '',
    'Обладнання':                    op.equipment || '',
    '№ п/п':                         i + 1,
    '№ тех.оп.':                     op.techNum || '',
    'Назва технологічної операції':  op.name || '',
    'Затрати часу, хв':              op.time || 0,
    'Технічні умови':                op.conditions || '',
  }))
  const csv = Papa.unparse(data, { header: true, quotes: true })
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'operations_export.csv'
  a.style.visibility = 'hidden'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

function addNewRow() {
  operations.value.push({
    id: crypto.randomUUID(),
    block: '', worker: '', rank: null, equipment: '',
    num: '', techNum: '', name: '', time: null, conditions: '',
  })
}

function countTime(group) {
  const w = group.op.worker
  const workerOps = operations.value.filter(op => op.worker === w)
  const total = workerOps.reduce((s, op) => s + (Number(op.time) || 0), 0)
  alert(`Виконавець: ${w}\nВсього операцій: ${workerOps.length}\nЗагальний час: ${total.toFixed(2)} хв`)
}
</script>

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
            <button @click="setSort('block')"  class="sort-menu-item">За Блоком   <span v-if="sortConfig.key==='block'">{{ sortConfig.direction==='asc'?'↑':'↓' }}</span></button>
            <button @click="setSort('worker')" class="sort-menu-item">За Виконавцем <span v-if="sortConfig.key==='worker'">{{ sortConfig.direction==='asc'?'↑':'↓' }}</span></button>
            <button @click="setSort('time')"   class="sort-menu-item">За Часом    <span v-if="sortConfig.key==='time'">{{ sortConfig.direction==='asc'?'↑':'↓' }}</span></button>
            <button @click="setSort('rank')"   class="sort-menu-item">За Розрядом <span v-if="sortConfig.key==='rank'">{{ sortConfig.direction==='asc'?'↑':'↓' }}</span></button>
            <button @click="setSort('num')"    class="sort-menu-item">За № Операції <span v-if="sortConfig.key==='num'">{{ sortConfig.direction==='asc'?'↑':'↓' }}</span></button>
          </div>
        </div>
        <div class="search-input-wrapper">
          <input v-model="searchQuery" type="text" placeholder="Search all fields..." class="search-input" />
          <button class="search-icon-btn" aria-label="Пошук"><SearchIcon class="search-icon-svg" /></button>
        </div>
      </div>

      <div class="table-container">
        <table class="operations-table">
          <thead>
            <tr>
              <th>Блок</th>
              <th>Виконавець</th>
              <th>Розряд</th>
              <th>Обладнання</th>
              <th>№ п/п</th>
              <th>№ тех.оп.</th>
              <th>Назва технологічної операції</th>
              <th>Затрати часу, хв</th>
              <th>Технічні умови</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="groupedOperations.length === 0">
              <td :colspan="10" class="empty-table-cell">
                Не знайдено жодних операцій. Спробуйте змінити фільтри або завантажити CSV.
              </td>
            </tr>
            <template v-for="(group, index) in groupedOperations" :key="group.op.id">
              <tr :style="getRowStyle(group.op.worker)">
                <td><input v-model="group.op.block"      class="table-input" /></td>
                <td><input v-model="group.op.worker"     class="table-input" /></td>
                <td><input v-model.number="group.op.rank" type="number" step="1" class="table-input table-input-number" /></td>
                <td><input v-model="group.op.equipment"  class="table-input" /></td>
                <td><input v-model="group.op.num"        class="table-input" /></td>
                <td><input v-model="group.op.techNum"    class="table-input" /></td>
                <td><input v-model="group.op.name"       class="table-input" /></td>
                <td><input v-model.number="group.op.time" type="number" step="0.1" class="table-input table-input-number" /></td>
                <td><input v-model="group.op.conditions" class="table-input" /></td>
                <td v-if="group.isGroupStart" :rowspan="group.rowspan" class="action-cell-grouped" @click="countTime(group)">
                  <button class="view-btn">Переглянути</button>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <div class="table-actions-bar">
        <label for="file-upload" class="action-btn">Завантажити CSV</label>
        <input id="file-upload" type="file" @change="handleFileUpload" accept=".csv" />
        <button @click="addNewRow"   class="action-btn">Додати рядок</button>
        <button @click="exportToCSV" class="action-btn export-btn">Експорт / Зберегти</button>
      </div>
    </div>
  </main>
</template>
