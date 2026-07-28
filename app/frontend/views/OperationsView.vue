<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import FilterIcon from '../assets/icons/FilterIcon.vue'
import SearchIcon from '../assets/icons/SearchIcon.vue'
import Papa from 'papaparse'
import './styles/OperationsViewStyles.css'
import fetchExportToCSV, { fetchMultiProcess, fetchProcessFixed, fetchExportXlsx } from '../request/importCSV.js'
import { useWorkersStore } from '../stores/workers.js'
import { useAuthStore } from '../stores/auth.js'
import { useLocaleStore } from '../stores/locale.js'

const router = useRouter()
const workersStore = useWorkersStore()
const authStore = useAuthStore()
const localeStore = useLocaleStore()
const { t, toggleLocale } = localeStore
const { isEN } = storeToRefs(localeStore)

function handleLogout() {
  authStore.logout()
  router.push('/')
}

const operations = ref([])
const searchQuery = ref('')
const isSortMenuOpen = ref(false)
const sortConfig = ref({ key: 'worker', direction: 'asc' })
const groupByEquipment = ref(false)
const selectedIds = ref(new Set())
const showSelectedOnly = ref(false)
const selectAllChecked = ref(false)

// Multi-file state
const selectedFiles = ref([])
const isProcessing = ref(false)
const timeUnitSetting = ref(null) // null = auto, 'minutes', 'seconds'

const ALLOWED_EXTENSIONS = ['.csv', '.xlsx', '.xls']

const totalWeightedQuantity = computed(() =>
  selectedFiles.value.reduce((s, f) => s + (f.quantity || 1), 0)
)
const processingResult = ref(null)
const showResultPanel = ref(false)

// Colors
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

// Equipment color map
const eqColorMap = computed(() => {
  const map = new Map()
  const unique = [...new Set(operations.value.map(op => op.equipment))]
  unique.forEach((e, i) => map.set(e, colorPalette[i % colorPalette.length]))
  return map
})
function getEqColor(e) { return eqColorMap.value.get(e) || '#FFFFFF' }
function getEqRowStyle(e) { return { backgroundColor: `${getEqColor(e)}AA` } }
function getGroupColor(val) {
  return groupByEquipment.value ? getEqColor(val) : getWorkerColor(val)
}
function getGroupRowStyle(val) {
  return groupByEquipment.value ? getEqRowStyle(val) : getRowStyle(val)
}

// Filter / sort / group
const filteredOperations = computed(() => {
  const q = searchQuery.value.toLowerCase()
  if (!q) return operations.value
  return operations.value.filter(op =>
    ['block','worker','num','name','equipment','conditions','sourceFile'].some(k =>
      op[k] && String(op[k]).toLowerCase().includes(q)
    )
  )
})

const checkboxFilteredOperations = computed(() => {
  const ops = filteredOperations.value
  if (!showSelectedOnly.value) return ops
  return ops.filter(op => selectedIds.value.has(op.id))
})

const sortedOperations = computed(() => {
  const { key, direction } = sortConfig.value
  return [...checkboxFilteredOperations.value].sort((a, b) => {
    let vA = a[key], vB = b[key]
    let r = typeof vA === 'string' ? vA.localeCompare(vB) : (vA || 0) - (vB || 0)
    return direction === 'asc' ? r : -r
  })
})

const groupKey = computed(() => groupByEquipment.value ? 'equipment' : 'worker')

const groupedOperations = computed(() => {
  const ops = sortedOperations.value
  return ops.map((op, i) => {
    const key = groupKey.value
    const isStart = i === 0 || ops[i - 1][key] !== op[key]
    let rowspan = 0
    if (isStart) {
      rowspan = 1
      for (let j = i + 1; j < ops.length && ops[j][key] === op[key]; j++) rowspan++
    }
    return { op, isGroupStart: isStart, rowspan }
  })
})

const getSortLabel = computed(() => {
  const { key, direction } = sortConfig.value
  const arrow = direction === 'asc' ? '↑' : '↓'
  const labels = {
    block: t('sort.byBlock').replace('За ', '').replace('By ', ''),
    worker: t('sort.byWorker').replace('За ', '').replace('By ', ''),
    time: t('sort.byTime').replace('За ', '').replace('By ', ''),
    rank: t('sort.byRank').replace('За ', '').replace('By ', ''),
    num: t('sort.byNum').replace('За ', '').replace('By ', ''),
  }
  return `${t('sort.label', { key: labels[key] || key, dir: arrow })}`
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

// Checkbox logic
function toggleSelect(id) {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id)
  } else {
    selectedIds.value.add(id)
  }
  selectAllChecked.value = false
}

function toggleSelectAll() {
  selectAllChecked.value = !selectAllChecked.value
  if (selectAllChecked.value) {
    const ids = checkboxFilteredOperations.value.map(op => op.id)
    ids.forEach(id => selectedIds.value.add(id))
  } else {
    selectedIds.value.clear()
  }
}

const selectedCount = computed(() => selectedIds.value.size)
const totalCount = computed(() => operations.value.length)

// Time summary
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

// File handling
function onFilesSelected(event) {
  const files = Array.from(event.target.files)
  const valid = files.filter(f => {
    const lower = f.name.toLowerCase()
    return ALLOWED_EXTENSIONS.some(ext => lower.endsWith(ext))
  })
  if (valid.length !== files.length) alert(t('op.onlySupported'))
  const wrapped = valid.map(f => ({ id: crypto.randomUUID(), file: f, quantity: 1 }))
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
  if (selectedFiles.value.length === 0) { alert(t('op.selectFileFirst')); return }
  isProcessing.value = true
  processingResult.value = null
  try {
    const profile = workersStore.getProfile()
    const fileEntries = selectedFiles.value
    const hasXlsx = fileEntries.some(e => {
      const lower = e.file.name.toLowerCase()
      return lower.endsWith('.xlsx') || lower.endsWith('.xls')
    })
    const singleNoProfile = fileEntries.length === 1 && profile.workers.length === 0 && fileEntries[0].quantity === 1 && !hasXlsx
    let result
    if (singleNoProfile) {
      result = await fetchProcessFixed(fileEntries[0].file, timeUnitSetting.value)
    } else {
      result = await fetchMultiProcess(
        fileEntries.map(e => e.file),
        profile,
        fileEntries.map(e => e.quantity),
        timeUnitSetting.value
      )
    }
    if (!result.success || !Array.isArray(result.data)) {
      throw new Error(result.error || t('op.serverError'))
    }
    operations.value = result.data.map(mapRow)
    selectedIds.value = new Set()
    showSelectedOnly.value = false
    selectAllChecked.value = false
    processingResult.value = result
    showResultPanel.value = true
    selectedFiles.value = []
  } catch (err) {
    alert(t('op.processError') + ': ' + (err.message || ''))
    console.error(err)
  } finally {
    isProcessing.value = false
  }
}

async function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file) return
  const lower = file.name.toLowerCase()
  const valid = ALLOWED_EXTENSIONS.some(ext => lower.endsWith(ext))
  if (!valid) { alert(t('op.onlySupported')); return }
  selectedFiles.value = [{ id: crypto.randomUUID(), file, quantity: 1 }]
  await processFiles()
}

// Export
function exportToCSV() {
  if (operations.value.length === 0) { alert(t('op.noData')); return }
  const data = operations.value.map((op, i) => ({
    'Блок': op.block || '',
    'Робітник': op.worker || '',
    'Розряд': op.rank || '',
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

async function exportToXLSX() {
  if (operations.value.length === 0) { alert(t('op.noData')); return }
  try {
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
    const blob = await fetchExportXlsx(data)
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'operations_export.xlsx'
    a.style.visibility = 'hidden'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  } catch (err) {
    alert(t('op.exportError') + ': ' + (err.message || ''))
    console.error(err)
  }
}

function addNewRow() {
  operations.value.push({
    id: crypto.randomUUID(),
    block: '', worker: '', rank: null, equipment: '',
    num: '', techNum: '', name: '', time: null, conditions: '', sourceFile: '',
  })
}

// Worker time popup
function countTime(group) {
  const w = group.op.worker
  const workerOps = operations.value.filter(op => op.worker === w)
  const total = workerOps.reduce((s, op) => s + (Number(op.time) || 0), 0)
  const hours = (total / 60).toFixed(2)
  const byProduct = {}
  workerOps.forEach(op => {
    const key = op.sourceFile || t('time.unknownFile')
    if (!byProduct[key]) byProduct[key] = { time: 0, qty: op.productQuantity || 1 }
    byProduct[key].time += Number(op.time) || 0
  })
  const productLines = Object.entries(byProduct)
    .map(([src, v]) => `  ${src}: ${v.time.toFixed(2)} хв × ${v.qty} = ${(v.time * v.qty).toFixed(2)} хв`)
    .join('\n')
  const weightedTotal = Object.values(byProduct).reduce((s, v) => s + v.time * v.qty, 0)
  alert(
    `${t('time.worker')}: ${w}\n` +
    `${t('time.operations')}: ${workerOps.length}\n` +
    `─────────────────────\n` +
    `${productLines}\n` +
    `─────────────────────\n` +
    `${t('time.weighted')}: ${weightedTotal.toFixed(2)} хв (${(weightedTotal/60).toFixed(2)} год)\n` +
    `${t('time.unweighted')}: ${total.toFixed(2)} хв`
  )
}

const hasWorkers = computed(() => workersStore.workers.length > 0)

const sortLabels = computed(() => [
  { key: 'block', label: t('sort.byBlock') },
  { key: 'worker', label: t('sort.byWorker') },
  { key: 'time', label: t('sort.byTime') },
  { key: 'rank', label: t('sort.byRank') },
  { key: 'num', label: t('sort.byNum') },
  { key: 'equipment', label: t('sort.byEquipment') },
])
</script>

<template>
  <main class="operations-page">
    <header class="app-header">
      <button @click="router.push('/')" class="header-back-link">{{ t('nav.home') }}</button>
      <img src="../assets/icons/logo.svg" alt="Chronologic Logo" class="header-logo-img" />
      <div class="header-right">
        <button class="lang-toggle" @click="toggleLocale" :title="isEN ? 'Українська' : 'English'">
          {{ isEN ? 'UA' : 'EN' }}
        </button>
        <button @click="router.push('/profileOper')" class="workers-btn" :class="{ 'workers-btn--active': hasWorkers }">
          {{ t('nav.profilesTitle') }}
          <span v-if="hasWorkers" class="workers-count-badge">{{ workersStore.workers.length }}</span>
        </button>
        <div class="user-menu">
          <div class="user-avatar">{{ authStore.username ? authStore.username[0].toUpperCase() : '?' }}</div>
          <span class="user-name">{{ authStore.username }}</span>
          <button @click="handleLogout" class="logout-btn">{{ t('nav.logout') }}</button>
        </div>
      </div>
    </header>

    <div class="content-wrapper">

      <!-- Upload panel -->
      <div class="upload-panel">
        <div class="upload-panel__top">
          <div class="upload-left">
            <h3 class="upload-title">{{ t('op.title') }}</h3>
            <label for="multi-file-upload" class="action-btn upload-label">
              {{ t('op.selectFiles') }}
            </label>
            <input id="multi-file-upload" type="file" multiple accept=".csv,.xlsx,.xls"
                   @change="onFilesSelected" style="display:none" />
          </div>
          <div class="upload-hint" v-if="selectedFiles.length === 0">
            {{ t('op.hintXlsx') }}
          </div>
        </div>

        <!-- Time unit setting -->
        <div class="time-unit-setting">
          <label class="time-unit-label">{{ t('op.timeUnit') }}:</label>
          <select v-model="timeUnitSetting" class="time-unit-select">
            <option :value="null">{{ t('op.timeAuto') }}</option>
            <option value="minutes">{{ t('op.timeMinutes') }}</option>
            <option value="seconds">{{ t('op.timeSeconds') }}</option>
          </select>
        </div>

        <!-- File list -->
        <div v-if="selectedFiles.length > 0" class="file-list">
          <div class="file-list__header">
            <span class="fh-name">{{ t('op.fileName') }}</span>
            <span class="fh-size">{{ t('op.fileSize') }}</span>
            <span class="fh-qty">{{ t('op.fileQty') }}</span>
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
              {{ t('op.total') }}: {{ selectedFiles.length }} {{ t('op.products') }} ·
              {{ totalWeightedQuantity }} {{ t('op.units') }}
            </span>
          </div>
        </div>

        <div class="upload-panel__actions" v-if="selectedFiles.length > 0">
          <div v-if="hasWorkers" class="profile-indicator">
            {{ t('op.profilesLoaded', { n: workersStore.workers.length }) }}
          </div>
          <button @click="processFiles" class="process-btn" :disabled="isProcessing">
            <span v-if="isProcessing">{{ t('op.processing') }}</span>
            <span v-else>{{ t('op.process', { n: selectedFiles.length }) }}</span>
          </button>
        </div>
      </div>

      <!-- Result meta panel -->
      <div v-if="showResultPanel && processingResult" class="result-panel">
        <button @click="showResultPanel = false" class="result-panel__close">✕</button>
        <div class="result-stats">
          <div class="result-stat">
            <span class="result-stat__n">{{ processingResult.total_after }}</span>
            <span class="result-stat__l">{{ t('result.operations') }}</span>
          </div>
          <div class="result-stat">
            <span class="result-stat__n">{{ processingResult.files_processed ?? 1 }}</span>
            <span class="result-stat__l">{{ t('result.files') }}</span>
          </div>
          <div class="result-stat">
            <span class="result-stat__n">{{ processingResult.total_products ?? processingResult.files_processed ?? 1 }}</span>
            <span class="result-stat__l">{{ t('result.products') }}</span>
          </div>
          <div class="result-stat">
            <span class="result-stat__n">{{ processingResult.processing_time_sec }}с</span>
            <span class="result-stat__l">{{ t('result.processingTime') }}</span>
          </div>
          <div class="result-stat">
            <span class="result-stat__n result-stat__n--accent">{{ grandTotal }}</span>
            <span class="result-stat__l">{{ t('result.totalMinutes') }}</span>
          </div>
        </div>

        <!-- Import meta info (for XLSX) -->
        <div v-if="processingResult.import_meta" class="import-meta">
          <div v-if="processingResult.import_meta.detected_time_unit" class="import-meta__item">
            <span class="import-meta__label">{{ t('result.detectedTime') }}:</span>
            <span class="import-meta__value">{{ processingResult.import_meta.detected_time_unit === 'seconds' ? t('op.timeSeconds') : t('op.timeMinutes') }}</span>
          </div>
          <div v-if="processingResult.import_meta.mapped_count !== undefined" class="import-meta__item">
            <span class="import-meta__label">{{ t('result.columnsMapped') }}:</span>
            <span class="import-meta__value">{{ processingResult.import_meta.mapped_count }}/{{ processingResult.import_meta.total_columns }}</span>
          </div>
        </div>

        <!-- Per-worker time summary -->
        <div v-if="workerTimeSummary.length > 0" class="worker-time-table-wrap">
          <table class="worker-time-table">
            <thead>
              <tr>
                <th>{{ t('result.worker') }}</th>
                <th>{{ t('result.operationsCount') }}</th>
                <th>{{ t('result.timeMin') }}</th>
                <th>{{ t('result.timeHours') }}</th>
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
                <td class="wt-total-label">{{ t('result.total') }}</td>
                <td class="wt-num wt-bold">{{ workerTimeSummary.reduce((s,w)=>s+w.count,0) }}</td>
                <td class="wt-num wt-bold">{{ grandTotal }}</td>
                <td class="wt-num wt-bold">{{ (grandTotal / 60).toFixed(3) }}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <!-- Filter bar -->
      <div class="filter-bar">
        <div class="sort-menu-wrapper">
          <button @click="isSortMenuOpen = !isSortMenuOpen" class="filter-btn">
            {{ getSortLabel }} <FilterIcon />
          </button>
          <div v-if="isSortMenuOpen" class="sort-menu">
            <button v-for="s in sortLabels" :key="s.key" @click="setSort(s.key)" class="sort-menu-item">
              {{ s.label }} <span v-if="sortConfig.key===s.key">{{ sortConfig.direction==='asc'?'↑':'↓' }}</span>
            </button>
          </div>
        </div>

        <div class="search-input-wrapper">
          <input v-model="searchQuery" type="text" :placeholder="t('filter.search')" class="search-input" />
          <button class="search-icon-btn" :aria-label="t('filter.searchAria')"><SearchIcon class="search-icon-svg" /></button>
        </div>

        <button class="filter-btn group-toggle" @click="groupByEquipment = !groupByEquipment">
          {{ groupByEquipment ? t('group.byWorker') : t('group.byEquipment') }}
        </button>

        <div class="checkbox-filter-group">
          <button class="filter-btn" :class="{ active: showSelectedOnly }" @click="showSelectedOnly = !showSelectedOnly">
            {{ showSelectedOnly ? t('filter.showAll') : t('filter.showSelected') }}
          </button>
        </div>
      </div>

      <!-- Selection toolbar -->
      <div v-if="operations.length > 0" class="selection-bar">
        <label class="select-all-checkbox">
          <input type="checkbox" :checked="selectAllChecked" @change="toggleSelectAll" />
          <span>{{ selectAllChecked ? t('filter.deselectAll') : t('filter.selectAll') }}</span>
        </label>
        <span class="selection-info">
          {{ t('filter.selected', { n: selectedCount }) }}
          &middot;
          {{ t('filter.total', { n: totalCount }) }}
        </span>
      </div>

      <!-- Table -->
      <div class="table-container">
        <table class="operations-table">
          <thead>
            <tr>
              <th class="th-checkbox"></th>
              <th>{{ t('th.block') }}</th>
              <th>{{ t('th.worker') }}</th>
              <th>{{ t('th.rank') }}</th>
              <th>{{ t('th.num') }}</th>
              <th>{{ t('th.techNum') }}</th>
              <th>{{ t('th.name') }}</th>
              <th>{{ t('th.time') }}</th>
              <th>{{ t('th.equipment') }}</th>
              <th>{{ t('th.conditions') }}</th>
              <th>{{ t('th.file') }}</th>
              <th>{{ t('th.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="groupedOperations.length === 0">
              <td :colspan="12" class="empty-table-cell">
                {{ t('empty.operations') }}
              </td>
            </tr>
            <template v-for="(group) in groupedOperations" :key="group.op.id">
              <tr :style="getGroupRowStyle(groupByEquipment ? group.op.equipment : group.op.worker)">
                <td class="td-checkbox">
                  <input type="checkbox" :checked="selectedIds.has(group.op.id)" @change="toggleSelect(group.op.id)" />
                </td>
                <td><input v-model="group.op.block"       class="table-input" /></td>
                <td><input v-model="group.op.worker"      class="table-input" /></td>
                <td><select v-model.number="group.op.rank" class="table-input"><option v-for="n in 8" :key="n" :value="n">{{ n }}</option></select></td>
                <td><input v-model="group.op.num"         class="table-input" /></td>
                <td><input v-model="group.op.techNum"     class="table-input" /></td>
                <td><input v-model="group.op.name"        class="table-input" /></td>
                <td><input v-model.number="group.op.time" type="number" step="0.1" class="table-input table-input-number" /></td>
                <td><input v-model="group.op.equipment"   class="table-input" /></td>
                <td><input v-model="group.op.conditions"  class="table-input" /></td>
                <td class="source-file-cell">{{ group.op.sourceFile || '' }}</td>
                <td v-if="group.isGroupStart" :rowspan="group.rowspan" class="action-cell-grouped" @click="countTime(group)">
                  <button class="view-btn">⏱ {{ t('result.timeMin') }}</button>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- Bottom actions -->
      <div class="table-actions-bar">
        <button @click="addNewRow"   class="action-btn">{{ t('op.addRow') }}</button>
        <button @click="exportToCSV" class="action-btn export-btn">{{ t('op.exportCSV') }}</button>
        <button @click="exportToXLSX" class="action-btn export-btn export-btn--xlsx">{{ t('op.exportXLSX') }}</button>
      </div>
    </div>
  </main>
</template>

<style scoped>
/* ── Language toggle ── */
.lang-toggle {
  padding: 6px 12px; border-radius: 8px; border: 1px solid #d1d5db;
  background: #fff; color: #4e48eb; font-weight: 700; font-size: 13px;
  cursor: pointer; transition: all .2s; font-family: inherit;
  letter-spacing: .5px;
}
.lang-toggle:hover {
  background: linear-gradient(to right,#4e48eb,#8b3ab3);
  color: #fff; border-color: transparent;
}

/* ── Group toggle ── */
.group-toggle {
  min-width: 140px; justify-content: center;
}

/* ── Checkbox filter ── */
.checkbox-filter-group {
  display: flex; gap: 6px;
}
.checkbox-filter-group .filter-btn.active {
  background: linear-gradient(to right,#4e48eb,#8b3ab3);
  color: #fff; border-color: transparent;
}

/* ── Selection bar ── */
.selection-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 8px 16px; background: #fff; border-radius: 8px;
  margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,.04);
  font-size: 13px; color: #555;
}
.select-all-checkbox {
  display: flex; align-items: center; gap: 6px; cursor: pointer; font-weight: 600;
}
.select-all-checkbox input { accent-color: #4e48eb; width: 16px; height: 16px; cursor: pointer; }
.selection-info { color: #999; font-size: 12px; }

/* ── Checkbox column ── */
.th-checkbox { width: 36px; min-width: 36px; padding: 12px 8px !important; text-align: center; }
.td-checkbox { text-align: center; padding: 12px 8px !important; vertical-align: middle; }
.td-checkbox input { accent-color: #4e48eb; width: 16px; height: 16px; cursor: pointer; }

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
.file-row__qty { display: flex; align-items: center; gap: 5px; }
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

/* Time unit setting */
.time-unit-setting {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 12px; font-size: 13px;
}
.time-unit-label { font-weight: 600; color: #555; }
.time-unit-select {
  padding: 5px 10px; border: 1px solid #d1d5db; border-radius: 8px;
  font-size: 13px; font-family: inherit; background: #fff; color: #374151;
  cursor: pointer;
}
.time-unit-select:focus { outline: none; border-color: #4e48eb; }

/* Import meta */
.import-meta {
  display: flex; flex-wrap: wrap; gap: 12px;
  padding: 8px 12px; margin-top: 8px;
  background: rgba(78,72,235,0.05); border: 1px solid rgba(78,72,235,0.12);
  border-radius: 8px; font-size: 12px;
}
.import-meta__item { display: flex; align-items: center; gap: 4px; }
.import-meta__label { color: #888; font-weight: 500; }
.import-meta__value { color: #4e48eb; font-weight: 700; }

/* XLSX export button */
.export-btn--xlsx {
  background: linear-gradient(to right, #2e7d32, #43a047);
  border-color: transparent;
}
.export-btn--xlsx:hover { opacity: 0.85; }

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
