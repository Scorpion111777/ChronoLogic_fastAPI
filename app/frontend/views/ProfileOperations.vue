<script setup>
import { ref, computed } from 'vue'
import { useWorkersStore } from '../stores/workers.js'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const store = useWorkersStore()
const router = useRouter()
const authStore = useAuthStore()
function handleLogout() { authStore.logout(); router.push('/') }

const newWorker = ref({ name: '', rank: '', equipment_type: '', equipment_quantity: 1 })
const editingId = ref(null)
const editBuffer = ref({})
const showForm = ref(false)
const validationError = ref('')

const RANKS = [1, 2, 3, 4, 5, 6, 7, 8]

const rankColor = (rank) => {
  const colors = ['#e3f2fd','#bbdefb','#90caf9','#64b5f6','#42a5f5','#1e88e5','#1565c0','#0d47a1']
  return colors[(rank - 1) % colors.length] || '#f0f0f0'
}

function startEdit(worker) {
  editingId.value = worker.id
  editBuffer.value = { ...worker }
}
function saveEdit(id) {
  if (!editBuffer.value.name.trim()) { validationError.value = "Ім'я не може бути порожнім"; return }
  store.updateWorker(id, editBuffer.value)
  editingId.value = null
  validationError.value = ''
}
function cancelEdit() {
  editingId.value = null
  validationError.value = ''
}

function addWorker() {
  if (!newWorker.value.name.trim()) { validationError.value = "Введіть ім'я"; return }
  if (!newWorker.value.rank) { validationError.value = 'Оберіть розряд'; return }
  store.addWorker({ ...newWorker.value })
  newWorker.value = { name: '', rank: '', equipment_type: '', equipment_quantity: 1 }
  showForm.value = false
  validationError.value = ''
}

const totalEquipment = computed(() =>
  store.workers.reduce((s, w) => s + (Number(w.equipment_quantity) || 0), 0)
)
const rankCounts = computed(() => {
  const m = {}
  store.workers.forEach(w => { m[w.rank] = (m[w.rank] || 0) + 1 })
  return m
})
</script>

<template>
  <main class="profile-page">
    <header class="app-header">
      <button @click="router.push('/operations')" class="header-back-link">← Назад</button>
      <img src="../assets/icons/logo.svg" alt="Chronologic Logo" class="header-logo-img" />
      <div class="user-menu-profile">
        <div class="user-avatar-profile">{{ authStore.username ? authStore.username[0].toUpperCase() : '?' }}</div>
        <span class="user-name-profile">{{ authStore.username }}</span>
        <button @click="handleLogout" class="logout-btn-profile">Вийти</button>
      </div>
    </header>

    <div class="content-wrapper">
      <div class="page-title-row">
        <h2 class="page-title">👷 Профілі робітників</h2>
        <button class="add-btn" @click="showForm = !showForm">
          {{ showForm ? '✕ Скасувати' : '+ Додати робітника' }}
        </button>
      </div>

      <!-- Stats bar -->
      <div class="stats-bar" v-if="store.workers.length > 0">
        <div class="stat-card">
          <span class="stat-num">{{ store.workers.length }}</span>
          <span class="stat-label">Робітників</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ totalEquipment }}</span>
          <span class="stat-label">Одиниць обладнання</span>
        </div>
        <div class="stat-card" v-for="(cnt, rank) in rankCounts" :key="rank">
          <span class="stat-num rank-badge" :style="{ background: rankColor(Number(rank)) }">{{ rank }}</span>
          <span class="stat-label">розряд · {{ cnt }} ос.</span>
        </div>
      </div>

      <!-- Add worker form -->
      <div v-if="showForm" class="add-form-card">
        <h3 class="form-title">Новий робітник</h3>
        <p v-if="validationError" class="error-msg">{{ validationError }}</p>
        <div class="form-grid">
          <div class="form-group">
            <label>Ім'я / Прізвище</label>
            <input v-model="newWorker.name" type="text" placeholder="Іванов І.І." class="form-input" />
          </div>
          <div class="form-group">
            <label>Розряд</label>
            <select v-model.number="newWorker.rank" class="form-input">
              <option value="" disabled>Оберіть...</option>
              <option v-for="r in RANKS" :key="r" :value="r">{{ r }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>Тип обладнання</label>
            <input v-model="newWorker.equipment_type" type="text" placeholder="ВТО" class="form-input" />
          </div>
          <div class="form-group">
            <label>Кількість обладнання</label>
            <input v-model.number="newWorker.equipment_quantity" type="number" min="1" class="form-input" />
          </div>
        </div>
        <button @click="addWorker" class="save-btn">Зберегти</button>
      </div>

      <!-- Workers table -->
      <div class="table-card" v-if="store.workers.length > 0">
        <table class="workers-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Ім'я</th>
              <th>Розряд</th>
              <th>Тип обладнання</th>
              <th>К-сть обладнання</th>
              <th>Дії</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(worker, idx) in store.workers" :key="worker.id"
                :class="{ 'editing-row': editingId === worker.id }">
              <td class="row-num">{{ idx + 1 }}</td>

              <template v-if="editingId === worker.id">
                <td><input v-model="editBuffer.name" class="inline-input" /></td>
                <td>
                  <select v-model.number="editBuffer.rank" class="inline-input inline-select">
                    <option v-for="r in RANKS" :key="r" :value="r">{{ r }}</option>
                  </select>
                </td>
                <td><input v-model="editBuffer.equipment_type" class="inline-input" /></td>
                <td><input v-model.number="editBuffer.equipment_quantity" type="number" min="1" class="inline-input inline-num" /></td>
                <td class="actions-cell">
                  <button @click="saveEdit(worker.id)" class="icon-btn save-icon">✓</button>
                  <button @click="cancelEdit" class="icon-btn cancel-icon">✕</button>
                </td>
              </template>

              <template v-else>
                <td class="name-cell">{{ worker.name }}</td>
                <td>
                  <span class="rank-chip" :style="{ background: rankColor(worker.rank) }">{{ worker.rank }}</span>
                </td>
                <td class="equip-cell">{{ worker.equipment_type || '—' }}</td>
                <td class="num-cell">{{ worker.equipment_quantity }}</td>
                <td class="actions-cell">
                  <button @click="startEdit(worker)" class="icon-btn edit-icon">✏️</button>
                  <button @click="store.removeWorker(worker.id)" class="icon-btn delete-icon">🗑️</button>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else-if="!showForm" class="empty-state">
        <p>Немає жодного робітника.<br/>Натисніть <strong>+ Додати робітника</strong> щоб почати.</p>
      </div>
    </div>
  </main>
</template>

<style scoped>
.profile-page {
  width: 100%;
  min-height: 100vh;
  background-color: #f4f5f7;
  box-sizing: border-box;
  font-family: inherit;
}
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 30px;
  background: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,.05);
}
.header-back-link {
  color: #4e48eb; font-size: 16px; font-weight: 500;
  background: transparent; border: none; cursor: pointer;
}
.header-logo-img { height: 45px; width: auto; }
.header-user-icon { width: 36px; height: 36px; border-radius: 50%; background: #f0f0f0; border: 1px solid #ddd; }

.content-wrapper { max-width: 1200px; margin: 0 auto; padding: 30px 20px; }

.page-title-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }

.add-btn {
  padding: 10px 22px; border-radius: 24px; border: none;
  background: linear-gradient(to right, #4e48eb, #8b3ab3);
  color: #fff; font-weight: 600; font-size: 14px; cursor: pointer;
  transition: opacity .2s;
}
.add-btn:hover { opacity: .85; }

.stats-bar {
  display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 20px;
}
.stat-card {
  background: #fff; border-radius: 10px; padding: 14px 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
  display: flex; flex-direction: column; align-items: center; min-width: 90px;
}
.stat-num { font-size: 22px; font-weight: 700; color: #4e48eb; }
.stat-label { font-size: 11px; color: #888; margin-top: 2px; text-align: center; }
.rank-badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 16px; font-weight: 700; color: #1a237e; }

.add-form-card {
  background: #fff; border-radius: 12px; padding: 24px;
  box-shadow: 0 4px 12px rgba(0,0,0,.08); margin-bottom: 24px;
  border-left: 4px solid #4e48eb;
}
.form-title { font-size: 16px; font-weight: 700; margin: 0 0 16px; color: #333; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; margin-bottom: 16px; }
.form-group { display: flex; flex-direction: column; gap: 4px; }
.form-group label { font-size: 12px; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: .4px; }
.form-input {
  padding: 9px 12px; border: 1px solid #ddd; border-radius: 8px;
  font-size: 14px; background: #fafafa; transition: border .2s;
  font-family: inherit;
}
.form-input:focus { outline: none; border-color: #4e48eb; background: #fff; }

.save-btn {
  padding: 9px 28px; border-radius: 20px;
  background: linear-gradient(to right, #4e48eb, #8b3ab3);
  color: #fff; border: none; font-size: 14px; font-weight: 600; cursor: pointer;
}
.save-btn:hover { opacity: .85; }

.error-msg { color: #e53935; font-size: 13px; margin-bottom: 10px; }

.table-card {
  background: #fff; border-radius: 12px;
  box-shadow: 0 4px 8px rgba(0,0,0,.05); overflow: auto;
}
.workers-table { width: 100%; border-collapse: collapse; }
.workers-table th {
  padding: 12px 16px; background: #fafafa; font-size: 12px;
  font-weight: 600; color: #6b7280; border-bottom: 2px solid #e0e0e0;
  text-align: left; white-space: nowrap;
}
.workers-table td {
  padding: 12px 16px; font-size: 14px; color: #222;
  border-top: 1px solid #f0f0f0;
}
.editing-row td { background: #fafbff; }
.row-num { color: #bbb; font-size: 12px; }
.name-cell { font-weight: 600; }
.num-cell { text-align: center; }
.equip-cell { color: #444; }

.rank-chip {
  display: inline-block; padding: 3px 12px; border-radius: 14px;
  font-weight: 700; font-size: 13px; color: #1a237e;
}

.inline-input {
  padding: 6px 10px; border: 1px solid #c0c0f0; border-radius: 6px;
  font-size: 14px; width: 100%; box-sizing: border-box;
  font-family: inherit; background: #fff;
}
.inline-select { cursor: pointer; }
.inline-num { width: 70px; text-align: center; }

.actions-cell { display: flex; gap: 6px; align-items: center; }
.icon-btn {
  padding: 4px 10px; border-radius: 8px; border: 1px solid transparent;
  cursor: pointer; font-size: 14px; background: transparent; transition: all .15s;
}
.edit-icon:hover { background: #e3f2fd; }
.delete-icon:hover { background: #fce4ec; }
.save-icon { color: #2e7d32; border-color: #a5d6a7; }
.save-icon:hover { background: #e8f5e9; }
.cancel-icon { color: #c62828; border-color: #ef9a9a; }
.cancel-icon:hover { background: #fce4ec; }

.empty-state {
  text-align: center; padding: 60px 20px; color: #999;
  background: #fff; border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,.05);
}

@media (max-width: 640px) {
  .content-wrapper { padding: 15px; }
  .form-grid { grid-template-columns: 1fr; }
}

.user-menu-profile {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 12px 4px 4px;
  background: rgba(78,72,235,0.08);
  border: 1px solid rgba(78,72,235,0.2);
  border-radius: 24px;
}
.user-avatar-profile {
  width: 30px; height: 30px; border-radius: 50%;
  background: linear-gradient(135deg, #4e48eb, #8b3ab3);
  color: #fff; font-size: 13px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.user-name-profile { font-size: 13px; font-weight: 500; color: #444; }
.logout-btn-profile {
  background: none; border: none; font-size: 12px; color: #999;
  cursor: pointer; font-family: inherit; transition: color 0.2s;
}
.logout-btn-profile:hover { color: #e53935; }
@media (max-width: 640px) { .user-name-profile { display: none; } }

</style>
