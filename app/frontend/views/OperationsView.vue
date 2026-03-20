<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import FilterIcon from '../assets/icons/FilterIcon.vue'
import SearchIcon from '../assets/icons/SearchIcon.vue'
import Papa from 'papaparse'
import './styles/OperationsViewStyles.css'
import fetchExportToCSV, { fetchMultiProcess } from '../request/importCSV.js'
import { useWorkersStore } from '../stores/workers.js'
import { useAuthStore } from '../stores/auth.js'

const router = useRouter()
const workersStore = useWorkersStore()
const authStore = useAuthStore()

function handleLogout() {
  authStore.logout()
  router.push('/')
}

const operations = ref([])
const searchQuery = ref('')
const isSortMenuOpen = ref(false)
const sortConfig = ref({ key: 'worker', direction: 'asc' })

// ── Multi-file state ─────────────────────────────────────────────────────────
// Each entry: { id, file, quantity }
const selectedFiles = ref([])
const isProcessing = ref(false)

// Total weighted quantity across all files (for summary display)
const totalWeightedQuantity = computed(() =>
  selectedFiles.value.reduce((s, f) => s + (f.quantity || 1), 0)
)
const processingResult = ref(null) // last server response meta
const showResultPanel = ref(false)

// ── Colors ───────────────────────────────────────────────────────────────────
const colorPalette = [
  '#FF6B6B','#54D6B1','#6B9AFF','#F7D154','#B36BFF',
  '#FF6BF1','#FF936B','#4CE0E0','#FF8A80','#FFB080',
  '#B0FF80','#80B0FF','#B080FF','#FF80FF','#9BF6FF','#A0C4FF',
]
const workerColorMap = computed(() => {
  const map = new Map()
  const uniqueWorkers = [...new Set(operations.value.map(op => op.worker))]
  uniqueWorkers.forEach((w, i) => map.set(w, colorPalette[i % colorPalette.length]))
  return map
})
function getWorkerColor(w) { return workerColorMap.value.get(w) || '#FFFFFF' }
function getRowStyle(w) { return { backgroundColor: `${getWorkerColor(w)}AA` } }

// ── Filter / sort / group ────────────────────────────────────────────────────
const filteredOperations = computed(() => {
  const q = searchQuery.value.toLowerCase()
  if (!q) return operations.value
  return operations.value.filter(op =>
    ['block','worker','num','name','equipment','conditions','sourceFile'].some(k =>
      op[k] && String(op[k]).toLowerCase().includes(q)
    )
  )
})

const sortedOperations = computed(() => {
  const { key, direction } = sortConfig.value
  return [...filteredOperations.value].sort((a, b) => {
    let vA = a[key], vB = b[key]
    let r = typeof vA === 'string' ? vA.localeCompare(vB) : (vA || 0) - (vB || 0)
    return direction === 'asc' ? r : -r
  })
})

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

function setSort(key) {
  if (sortConfig.value.key === key) {
    sortConfig.value.direction = sortConfig.value.direction === 'asc' ? 'desc' : 'asc'
  } else {
    sortConfig.value.key = key
    sortConfig.value.direction = 'asc'
  }
  isSortMenuOpen.value = false
}

// ── Time summary ─────────────────────────────────────────────────────────────
const workerTimeSummary = computed(() => {
  const map = {}
  operations.value.forEach(op => {
    if (!op.worker) return
    if (!map[op.worker]) map[op.worker] = { total: 0, count: 0 }
    map[op.worker].total += Number(op.time) || 0
    map[op.worker].count++
  })
  return Object.entries(map).map(([w, v]) => ({
    worker: w,
    total_min: parseFloat(v.total.toFixed(2)),
    total_hours: parseFloat((v.total / 60).toFixed(3)),
    count: v.count,
  }))
})

const grandTotal = computed(() =>
  workerTimeSummary.value.reduce((s, w) => s + w.total_min, 0).toFixed(2)
)

// ── File handling ─────────────────────────────────────────────────────────────
function onFilesSelected(event) {
  const files = Array.from(event.target.files)
  const csv = files.filter(f => f.name.endsWith('.csv'))
  if (csv.length !== files.length) alert('Лише CSV-файли будуть завантажені.')
  const wrapped = csv.map(f => ({ id: crypto.randomUUID(), file: f, quantity: 1 }))
  selectedFiles.value = [...selectedFiles.value, ...wrapped]
  event.target.value = ''
}

function removeFile(idx) {
  selectedFiles.value.splice(idx, 1)
}

function setFileQty(idx, val) {
  const q = Math.max(1, parseInt(val) || 1)
  selectedFiles.value[idx].quantity = q
}

function mapRow(row) {
  return {
    id: crypto.randomUUID(),
    block:           row['Блок'] || '',
    worker:          row['Робітник'] || '',
    rank:            row['Розряд'] || 0,
    equipment:       row['Обладнання'] || '',
    num:             row['№ п/п'] || '',
    techNum:         row['№ тех.оп.'] || '',
    name:            row['Назва технологічної операції'] || '',
    time:            row['Затрати часу, хв'] || 0,
    conditions:      row['Технічні умови'] || '',
    sourceFile:      row['_source_file'] || '',
    productQuantity: Number(row['_product_quantity']) || 1,
  }
}

async function processFiles() {
  if (selectedFiles.value.length === 0) { alert('Оберіть хоча б один CSV-файл.'); return }
  isProcessing.value = true
  processingResult.value = null
  try {
    const profile = workersStore.getProfile()
    const fileEntries = selectedFiles.value  // [{id, file, quantity}]
    const singleNoProfile = fileEntries.length === 1 && profile.workers.length === 0 && fileEntries[0].quantity === 1
    let result
    if (singleNoProfile) {
      result = await fetchExportToCSV(fileEntries[0].file)
    } else {
      result = await fetchMultiProcess(
        fileEntries.map(e => e.file),
        profile,
        fileEntries.map(e => e.quantity)  // per-file quantities array
      )
    }
    if (!result.success || !Array.isArray(result.data)) {
      throw new Error(result.error || 'Помилка обробки на сервері')
    }
    operations.value = result.data.map(mapRow)
    processingResult.value = result
    showResultPanel.value = true
    selectedFiles.value = []
  } catch (err) {
    alert('Помилка: ' + (err.message || 'Не вдалося обробити файл'))
    console.error(err)
  } finally {
    isProcessing.value = false
  }
}

// Legacy single-file compat
async function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file || !file.name.endsWith('.csv')) { alert('Завантажуйте лише CSV-файл!'); return }
  selectedFiles.value = [{ id: crypto.randomUUID(), file, quantity: 1 }]
  await processFiles()
}

// ── Export ────────────────────────────────────────────────────────────────────
function exportToCSV() {
  if (operations.value.length === 0) { alert('Немає даних для експорту!'); return }
  const data = operations.value.map((op, i) => ({
    'Блок': op.block || '',
    'Робітник': op.worker || '',
    'Розряд': op.rank || '',
    'Обладнання': op.equipment || '',
    '№ п/п': i + 1,
    '№ тех.оп.': op.techNum || '',
    'Назва технологічної операції': op.name || '',
    'Затрати часу, хв': op.time || 0,
    'Технічні умови': op.conditions || '',
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
    num: '', techNum: '', name: '', time: null, conditions: '', sourceFile: '',
  })
}

// ── Worker time popup ─────────────────────────────────────────────────────────
function countTime(group) {
  const w = group.op.worker
  const workerOps = operations.value.filter(op => op.worker === w)
  const total = workerOps.reduce((s, op) => s + (Number(op.time) || 0), 0)
  const hours = (total / 60).toFixed(2)
  // Group by product (sourceFile) and show per-product breakdown
  const byProduct = {}
  workerOps.forEach(op => {
    const key = op.sourceFile || 'Невідомий файл'
    if (!byProduct[key]) byProduct[key] = { time: 0, qty: op.productQuantity || 1 }
    byProduct[key].time += Number(op.time) || 0
  })
  const productLines = Object.entries(byProduct)
    .map(([src, v]) => `  ${src}: ${v.time.toFixed(2)} хв × ${v.qty} = ${(v.time * v.qty).toFixed(2)} хв`)
    .join('\n')
  const weightedTotal = Object.values(byProduct).reduce((s, v) => s + v.time * v.qty, 0)
  alert(
    `Виконавець: ${w}\n` +
    `Кількість операцій: ${workerOps.length}\n` +
    `─────────────────────\n` +
    `${productLines}\n` +
    `─────────────────────\n` +
    `Зважений загальний час: ${weightedTotal.toFixed(2)} хв (${(weightedTotal/60).toFixed(2)} год)\n` +
    `Час без зважування: ${total.toFixed(2)} хв`
  )
}

const hasWorkers = computed(() => workersStore.workers.length > 0)
</script>

<template>
  <main class="operations-page">
    <header class="app-header">
      <button @click="router.push('/')" class="header-back-link">← Головна</button>
      <img src="../assets/icons/logo.svg" alt="Chronologic Logo" class="header-logo-img" />
      <div class="header-right">
        <button @click="router.push('/profileOper')" class="workers-btn" :class="{ 'workers-btn--active': hasWorkers }">
          👷 Профілі
          <span v-if="hasWorkers" class="workers-count-badge">{{ workersStore.workers.length }}</span>
        </button>
        <div class="user-menu">
          <div class="user-avatar">{{ authStore.username ? authStore.username[0].toUpperCase() : '?' }}</div>
          <span class="user-name">{{ authStore.username }}</span>
          <button @click="handleLogout" class="logout-btn">Вийти</button>
        </div>
      </div>
    </header>

    <div class="content-wrapper">

      <!-- ── Upload panel ── -->
      <div class="upload-panel">
        <div class="upload-panel__top">
          <div class="upload-left">
            <h3 class="upload-title">Завантажити CSV файли</h3>
            <label for="multi-file-upload" class="action-btn upload-label">
              📂 Обрати файли
            </label>
            <input id="multi-file-upload" type="file" multiple accept=".csv"
                   @change="onFilesSelected" style="display:none" />
          </div>
          <div class="upload-hint" v-if="selectedFiles.length === 0">
            Кожен файл — окремий продукт. Встановіть кількість для кожного.
          </div>
        </div>

        <!-- File list with per-file quantity -->
        <div v-if="selectedFiles.length > 0" class="file-list">
          <div class="file-list__header">
            <span class="fh-name">Файл (продукт)</span>
            <span class="fh-size">Розмір</span>
            <span class="fh-qty">Кількість</span>
            <span class="fh-remove"></span>
          </div>
          <div v-for="(entry, idx) in selectedFiles" :key="entry.id" class="file-row">
            <span class="file-row__name">📄 {{ entry.file.name }}</span>
            <span class="file-row__size">{{ (entry.file.size / 1024).toFixed(1) }} KB</span>
            <div class="file-row__qty">
              <button @click="setFileQty(idx, entry.quantity - 1)" class="qty-btn">−</button>
              <input
                :value="entry.quantity"
                @input="setFileQty(idx, $event.target.value)"
                type="number" min="1" class="qty-input"
              />
              <button @click="setFileQty(idx, entry.quantity + 1)" class="qty-btn">+</button>
            </div>
            <button @click="removeFile(idx)" class="file-row__remove">✕</button>
          </div>
          <div class="file-list__footer" v-if="selectedFiles.length > 1">
            <span class="file-list__total">
              Всього: {{ selectedFiles.length }} продукт{{ selectedFiles.length > 1 ? 'и' : '' }} ·
              {{ totalWeightedQuantity }} одиниць загалом
            </span>
          </div>
        </div>

        <div class="upload-panel__actions" v-if="selectedFiles.length > 0">
          <div v-if="hasWorkers" class="profile-indicator">
            ✅ Профілі: {{ workersStore.workers.length }} робітників
          </div>
          <button @click="processFiles" class="process-btn" :disabled="isProcessing">
            <span v-if="isProcessing">⏳ Обробка…</span>
            <span v-else>▶ Обробити ({{ selectedFiles.length }} продукт{{ selectedFiles.length > 1 ? 'и' : '' }})</span>
          </button>
        </div>
      </div>

      <!-- ── Result meta panel ── -->
      <div v-if="showResultPanel && processingResult" class="result-panel">
        <button @click="showResultPanel = false" class="result-panel__close">✕</button>
        <div class="result-stats">
          <div class="result-stat">
            <span class="result-stat__n">{{ processingResult.total_after }}</span>
            <span class="result-stat__l">операцій</span>
          </div>
          <div class="result-stat">
            <span class="result-stat__n">{{ processingResult.files_processed ?? 1 }}</span>
            <span class="result-stat__l">файл{{ (processingResult.files_processed ?? 1) > 1 ? 'ів' : '' }}</span>
          </div>
          <div class="result-stat">
            <span class="result-stat__n">{{ processingResult.total_products ?? processingResult.files_processed ?? 1 }}</span>
            <span class="result-stat__l">продукт{{ (processingResult.total_products ?? 1) > 1 ? 'и' : '' }}</span>
          </div>
          <div class="result-stat">
            <span class="result-stat__n">{{ processingResult.processing_time_sec }}с</span>
            <span class="result-stat__l">час обробки</span>
          </div>
          <div class="result-stat">
            <span class="result-stat__n result-stat__n--accent">{{ grandTotal }}</span>
            <span class="result-stat__l">хв загалом</span>
          </div>
        </div>

        <!-- Per-worker time summary -->
        <div v-if="workerTimeSummary.length > 0" class="worker-time-table-wrap">
          <table class="worker-time-table">
            <thead>
              <tr>
                <th>Виконавець</th>
                <th>Операцій</th>
                <th>Час (хв)</th>
                <th>Час (год)</th>

              </tr>
            </thead>
            <tbody>
              <tr v-for="ws in workerTimeSummary" :key="ws.worker">
                <td :style="{ borderLeft: `4px solid ${getWorkerColor(ws.worker)}` }" class="wt-name">
                  {{ ws.worker || '—' }}
                </td>
                <td class="wt-num">{{ ws.count }}</td>
                <td class="wt-num">{{ ws.total_min }}</td>
                <td class="wt-num">{{ ws.total_hours }}</td>

              </tr>
            </tbody>
            <tfoot>
              <tr>
                <td class="wt-total-label">Разом</td>
                <td class="wt-num wt-bold">{{ workerTimeSummary.reduce((s,w)=>s+w.count,0) }}</td>
                <td class="wt-num wt-bold">{{ grandTotal }}</td>
                <td class="wt-num wt-bold">{{ (grandTotal / 60).toFixed(3) }}</td>

              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <!-- ── Filter bar ── -->
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
          <input v-model="searchQuery" type="text" placeholder="Пошук..." class="search-input" />
          <button class="search-icon-btn" aria-label="Пошук"><SearchIcon class="search-icon-svg" /></button>
        </div>
      </div>

      <!-- ── Table ── -->
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
              <th>Файл</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="groupedOperations.length === 0">
              <td :colspan="11" class="empty-table-cell">
                Немає операцій. Завантажте CSV або додайте рядок.
              </td>
            </tr>
            <template v-for="(group) in groupedOperations" :key="group.op.id">
              <tr :style="getRowStyle(group.op.worker)">
                <td><input v-model="group.op.block"       class="table-input" /></td>
                <td><input v-model="group.op.worker"      class="table-input" /></td>
                <td><input v-model.number="group.op.rank" type="number" step="1" class="table-input table-input-number" /></td>
                <td><input v-model="group.op.equipment"   class="table-input" /></td>
                <td><input v-model="group.op.num"         class="table-input" /></td>
                <td><input v-model="group.op.techNum"     class="table-input" /></td>
                <td><input v-model="group.op.name"        class="table-input" /></td>
                <td><input v-model.number="group.op.time" type="number" step="0.1" class="table-input table-input-number" /></td>
                <td><input v-model="group.op.conditions"  class="table-input" /></td>
                <td class="source-file-cell">{{ group.op.sourceFile || '' }}</td>
                <td v-if="group.isGroupStart" :rowspan="group.rowspan" class="action-cell-grouped" @click="countTime(group)">
                  <button class="view-btn">⏱ Час</button>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- ── Bottom actions ── -->
      <div class="table-actions-bar">
        <button @click="addNewRow"   class="action-btn">+ Рядок</button>
        <button @click="exportToCSV" class="action-btn export-btn">↓ Експорт CSV</button>
      </div>
    </div>
  </main>
</template>

<style scoped>
/* Upload panel */
.upload-panel {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 8px rgba(0,0,0,.05);
  margin-bottom: 20px;
  border-left: 4px solid #4e48eb;
}
.upload-panel__top {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 12px;
}
.upload-left { display: flex; align-items: center; gap: 12px; }
.upload-title { margin: 0; font-size: 15px; font-weight: 700; color: #333; }
.upload-label {
  padding: 8px 18px; border-radius: 20px; border: 1px solid #d1d5db;
  background: #fff; color: #374151; font-weight: 600; font-size: 13px;
  cursor: pointer; transition: all .2s; display: inline-block;
}
.upload-label:hover {
  background: linear-gradient(to right,#4e48eb,#8b3ab3);
  color: #fff; border-color: transparent;
}

.sample-qty-group { display: flex; flex-direction: column; gap: 4px; margin-left: auto; }
.qty-label { font-size: 11px; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: .4px; }
.qty-controls { display: flex; align-items: center; gap: 6px; }
.qty-btn {
  width: 30px; height: 30px; border-radius: 50%; border: 1px solid #d1d5db;
  background: #fff; font-size: 18px; cursor: pointer; font-weight: 700;
  display: flex; align-items: center; justify-content: center; transition: all .15s;
}
.qty-btn:hover { background: #4e48eb; color: #fff; border-color: #4e48eb; }
.qty-input {
  width: 60px; text-align: center; padding: 5px; border: 1px solid #d1d5db;
  border-radius: 8px; font-size: 15px; font-weight: 700; font-family: inherit;
}
.qty-input:focus { outline: none; border-color: #4e48eb; }

/* ── File list (per-product quantity) ── */
.upload-hint {
  margin-left: auto; font-size: 12px; color: #9090b0;
  background: rgba(78,72,235,0.07); border: 1px solid rgba(78,72,235,0.15);
  border-radius: 8px; padding: 6px 14px;
}

.file-list {
  margin-bottom: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
}

.file-list__header {
  display: grid;
  grid-template-columns: 1fr 80px 140px 32px;
  gap: 12px;
  padding: 8px 14px;
  background: #fafafa;
  border-bottom: 1px solid #e5e7eb;
  font-size: 11px; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.4px;
}

.file-row {
  display: grid;
  grid-template-columns: 1fr 80px 140px 32px;
  gap: 12px;
  align-items: center;
  padding: 10px 14px;
  border-bottom: 1px solid #f3f4f6;
  transition: background 0.15s;
}
.file-row:last-of-type { border-bottom: none; }
.file-row:hover { background: #f9f9ff; }

.file-row__name { font-size: 13px; font-weight: 500; color: #3730a3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.file-row__size { font-size: 12px; color: #9ca3af; text-align: right; }

.file-row__qty {
  display: flex; align-items: center; gap: 5px;
}
.file-row__remove {
  background: none; border: none; cursor: pointer;
  color: #d1d5db; font-size: 13px; padding: 2px; border-radius: 4px;
  transition: color 0.15s;
}
.file-row__remove:hover { color: #e53935; }

.file-list__footer {
  padding: 8px 14px;
  background: #f8f8ff;
  border-top: 1px solid #e5e7eb;
}
.file-list__total { font-size: 12px; color: #6b7280; font-weight: 500; }

/* qty controls shared */

.upload-panel__actions { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.profile-indicator { font-size: 13px; color: #2e7d32; font-weight: 500; }

.process-btn {
  padding: 9px 28px; border-radius: 24px; border: none;
  background: linear-gradient(to right,#4e48eb,#8b3ab3);
  color: #fff; font-size: 14px; font-weight: 700; cursor: pointer;
  transition: opacity .2s;
}
.process-btn:disabled { opacity: .55; cursor: not-allowed; }
.process-btn:not(:disabled):hover { opacity: .85; }

/* Result panel */
.result-panel {
  background: #fff; border-radius: 12px; padding: 16px 20px;
  box-shadow: 0 4px 8px rgba(0,0,0,.06); margin-bottom: 20px;
  position: relative;
}
.result-panel__close {
  position: absolute; top: 10px; right: 14px;
  background: none; border: none; font-size: 16px; cursor: pointer; color: #aaa;
}
.result-panel__close:hover { color: #555; }

.result-stats { display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 14px; }
.result-stat { display: flex; flex-direction: column; align-items: center; min-width: 70px; }
.result-stat__n { font-size: 22px; font-weight: 700; color: #4e48eb; }
.result-stat__n--accent { color: #8b3ab3; }
.result-stat__l { font-size: 11px; color: #888; }

.worker-time-table-wrap { overflow-x: auto; }
.worker-time-table { border-collapse: collapse; font-size: 13px; min-width: 400px; width: 100%; }
.worker-time-table th {
  padding: 8px 12px; background: #fafafa; font-size: 11px;
  font-weight: 600; color: #6b7280; border-bottom: 2px solid #e0e0e0; text-align: left;
}
.worker-time-table td { padding: 7px 12px; border-top: 1px solid #f0f0f0; }
.worker-time-table tfoot td { border-top: 2px solid #e0e0e0; background: #fafafa; }
.wt-name { font-weight: 600; padding-left: 10px; }
.wt-num { text-align: right; color: #333; }
.wt-bold { font-weight: 700; color: #4e48eb; }
.wt-total-label { font-weight: 700; color: #333; }

/* Workers header button */
.workers-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 16px; border-radius: 20px; border: 1px solid #d1d5db;
  background: #fff; color: #374151; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: all .2s; font-family: inherit;
}
.workers-btn:hover, .workers-btn--active {
  background: linear-gradient(to right,#4e48eb,#8b3ab3);
  color: #fff; border-color: transparent;
}
.workers-count-badge {
  background: #fff; color: #4e48eb; border-radius: 50%; width: 20px; height: 20px;
  font-size: 11px; font-weight: 800; display: flex; align-items: center; justify-content: center;
}
.workers-btn--active .workers-count-badge { color: #8b3ab3; }

.source-file-cell { font-size: 11px; color: #aaa; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Keep all original styles via OperationsViewStyles.css */

/* User menu */
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.user-menu {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px 4px 4px;
  background: rgba(78,72,235,0.08);
  border: 1px solid rgba(78,72,235,0.2);
  border-radius: 24px;
}
.user-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4e48eb, #8b3ab3);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.user-name {
  font-size: 13px;
  font-weight: 500;
  color: #444;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.logout-btn {
  background: none;
  border: none;
  font-size: 12px;
  color: #999;
  cursor: pointer;
  padding: 0;
  font-family: inherit;
  transition: color 0.2s;
}
.logout-btn:hover { color: #e53935; }
@media (max-width: 640px) {
  .user-name { display: none; }
  .header-right { gap: 8px; }
}

</style>
