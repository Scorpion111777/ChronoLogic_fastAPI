<script setup>
import { ref, computed, onMounted } from 'vue'
import { useWorkersStore } from '../stores/workers.js'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth.js'
import { useLocaleStore } from '../stores/locale.js'

const store = useWorkersStore()
const router = useRouter()
const authStore = useAuthStore()
const localeStore = useLocaleStore()
const { t, toggleLocale } = localeStore
const { isEN } = storeToRefs(localeStore)

const userId = computed(() => authStore.currentUser?.id || 'guest')

onMounted(() => {
  store.loadForUser(userId.value)
})

function handleLogout() { authStore.logout(); router.push('/') }

const activeTab = ref('workers') // 'workers' | 'teams'
const selectedTeamFilter = ref('all')

const newWorker = ref({ name: '', rank: '', equipment_type: '', equipment_quantity: 1, teamId: '' })
const editingId = ref(null)
const editBuffer = ref({})
const showForm = ref(false)
const validationError = ref('')

const newTeam = ref({ name: '', description: '' })
const editingTeamId = ref(null)
const editTeamBuffer = ref({})
const showTeamForm = ref(false)
const teamValidationError = ref('')

const RANKS = [1, 2, 3, 4, 5, 6, 7, 8]

const rankColor = (rank) => {
  const colors = ['#e3f2fd','#bbdefb','#90caf9','#64b5f6','#42a5f5','#1e88e5','#1565c0','#0d47a1']
  return colors[(rank - 1) % colors.length] || '#f0f0f0'
}

function getTeamName(teamId) {
  if (!teamId) return t('teams.noTeam')
  const team = store.teams.find(t => t.id === teamId)
  return team ? team.name : t('teams.noTeam')
}

function getWorkerEquipmentList(worker) {
  if (Array.isArray(worker.equipment_types) && worker.equipment_types.length > 0) {
    return worker.equipment_types
  }
  if (worker.equipment_type) {
    return String(worker.equipment_type).split(/[,;/|\n]/).map(s => s.trim()).filter(Boolean)
  }
  return []
}

// Worker actions
function startEdit(worker) {
  editingId.value = worker.id
  editBuffer.value = {
    ...worker,
    equipment_type: worker.equipment_type || (worker.equipment_types ? worker.equipment_types.join(', ') : '')
  }
}

function saveEdit(id) {
  if (!editBuffer.value.name.trim()) { validationError.value = t('profile.nameRequired'); return }
  store.updateWorker(id, editBuffer.value, userId.value)
  editingId.value = null
  validationError.value = ''
}

function cancelEdit() {
  editingId.value = null
  validationError.value = ''
}

function addWorker() {
  if (!newWorker.value.name.trim()) { validationError.value = t('profile.enterName'); return }
  if (!newWorker.value.rank) { validationError.value = t('profile.selectRank'); return }
  store.addWorker({ ...newWorker.value }, userId.value)
  newWorker.value = { name: '', rank: '', equipment_type: '', equipment_quantity: 1, teamId: selectedTeamFilter.value !== 'all' ? selectedTeamFilter.value : '' }
  showForm.value = false
  validationError.value = ''
}

function removeWorker(id) {
  store.removeWorker(id, userId.value)
}

// Team actions
function addTeam() {
  if (!newTeam.value.name.trim()) {
    teamValidationError.value = t('profile.enterName')
    return
  }
  store.addTeam({ ...newTeam.value }, userId.value)
  newTeam.value = { name: '', description: '' }
  showTeamForm.value = false
  teamValidationError.value = ''
}

function startEditTeam(team) {
  editingTeamId.value = team.id
  editTeamBuffer.value = { ...team }
}

function saveEditTeam(id) {
  if (!editTeamBuffer.value.name.trim()) return
  store.updateTeam(id, editTeamBuffer.value, userId.value)
  editingTeamId.value = null
}

function cancelEditTeam() {
  editingTeamId.value = null
}

function removeTeam(id) {
  if (confirm(t('teams.confirmDelete'))) {
    store.removeTeam(id, userId.value)
    if (selectedTeamFilter.value === id) {
      selectedTeamFilter.value = 'all'
    }
  }
}

function getTeamMemberCount(teamId) {
  return store.workers.filter(w => w.teamId === teamId).length
}

// Filtered workers
const filteredWorkers = computed(() => {
  if (selectedTeamFilter.value === 'all') return store.workers
  return store.workers.filter(w => w.teamId === selectedTeamFilter.value)
})

const totalEquipment = computed(() =>
  filteredWorkers.value.reduce((s, w) => s + (Number(w.equipment_quantity) || 0), 0)
)

const rankCounts = computed(() => {
  const m = {}
  filteredWorkers.value.forEach(w => { m[w.rank] = (m[w.rank] || 0) + 1 })
  return m
})
</script>

<template>
  <main class="profile-page">
    <header class="app-header">
      <button @click="router.push('/operations')" class="header-back-link">{{ t('nav.back') }}</button>
      <img src="../assets/icons/logo.svg" alt="Chronologic Logo" class="header-logo-img" />
      <div class="header-right">
        <button class="lang-toggle" @click="toggleLocale" :title="isEN ? 'Українська' : 'English'">
          {{ isEN ? 'UA' : 'EN' }}
        </button>
        <div class="user-menu-profile">
          <div class="user-avatar-profile">{{ authStore.username ? authStore.username[0].toUpperCase() : '?' }}</div>
          <span class="user-name-profile">{{ authStore.username }}</span>
          <button @click="handleLogout" class="logout-btn-profile">{{ t('nav.logout') }}</button>
        </div>
      </div>
    </header>

    <div class="content-wrapper">
      <!-- Tabs header -->
      <div class="tabs-nav">
        <button class="tab-btn" :class="{ 'tab-btn--active': activeTab === 'workers' }" @click="activeTab = 'workers'">
          {{ t('teams.tabWorkers') }} ({{ store.workers.length }})
        </button>
        <button class="tab-btn" :class="{ 'tab-btn--active': activeTab === 'teams' }" @click="activeTab = 'teams'">
          {{ t('teams.tabTeams') }} ({{ store.teams.length }})
        </button>
      </div>

      <!-- WORKERS TAB -->
      <div v-if="activeTab === 'workers'">
        <div class="page-title-row">
          <div class="title-with-filter">
            <h2 class="page-title">{{ t('profile.title') }}</h2>
            <div class="team-filter-inline" v-if="store.teams.length > 0">
              <label>{{ t('teams.teamLabel') }}:</label>
              <select v-model="selectedTeamFilter" class="team-select">
                <option value="all">{{ t('teams.all') }}</option>
                <option v-for="team in store.teams" :key="team.id" :value="team.id">{{ team.name }}</option>
              </select>
            </div>
          </div>
          <button class="add-btn" @click="showForm = !showForm">
            {{ showForm ? t('profile.cancel') : t('profile.add') }}
          </button>
        </div>

        <!-- Stats bar -->
        <div class="stats-bar" v-if="filteredWorkers.length > 0">
          <div class="stat-card">
            <span class="stat-num">{{ filteredWorkers.length }}</span>
            <span class="stat-label">{{ t('profile.workers') }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-num">{{ totalEquipment }}</span>
            <span class="stat-label">{{ t('profile.equipmentUnits') }}</span>
          </div>
          <div class="stat-card" v-for="(cnt, rank) in rankCounts" :key="rank">
            <span class="stat-num rank-badge" :style="{ background: rankColor(Number(rank)) }">{{ rank }}</span>
            <span class="stat-label">{{ t('profile.rank', { n: cnt }) }}</span>
          </div>
        </div>

        <!-- Add worker form -->
        <div v-if="showForm" class="add-form-card">
          <h3 class="form-title">{{ t('profile.newWorker') }}</h3>
          <p v-if="validationError" class="error-msg">{{ validationError }}</p>
          <div class="form-grid">
            <div class="form-group">
              <label>{{ t('profile.nameLabel') }}</label>
              <input v-model="newWorker.name" type="text" :placeholder="t('profile.namePlaceholder')" class="form-input" />
            </div>
            <div class="form-group">
              <label>{{ t('profile.rankLabel') }}</label>
              <select v-model.number="newWorker.rank" class="form-input">
                <option value="" disabled>{{ t('profile.rankPlaceholder') }}</option>
                <option v-for="r in RANKS" :key="r" :value="r">{{ r }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>{{ t('teams.teamLabel') }}</label>
              <select v-model="newWorker.teamId" class="form-input">
                <option value="">{{ t('teams.noTeam') }}</option>
                <option v-for="team in store.teams" :key="team.id" :value="team.id">{{ team.name }}</option>
              </select>
            </div>
            <div class="form-group span-2">
              <label>{{ t('profile.equipmentTypeLabel') }}</label>
              <input v-model="newWorker.equipment_type" type="text" :placeholder="t('equip.multipleHelp')" class="form-input" />
              <span class="form-hint">{{ t('equip.multipleHelp') }}</span>
            </div>
          </div>
          <button @click="addWorker" class="save-btn">{{ t('profile.save') }}</button>
        </div>

        <!-- Workers table -->
        <div class="table-card" v-if="filteredWorkers.length > 0">
          <table class="workers-table">
            <thead>
              <tr>
                <th>{{ t('profile.workerNum') }}</th>
                <th>{{ t('profile.name') }}</th>
                <th>{{ t('profile.rankLabel') }}</th>
                <th>{{ t('teams.teamLabel') }}</th>
                <th>{{ t('equip.types') }}</th>
                <th>{{ t('profile.equipmentQty') }}</th>
                <th>{{ t('profile.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(worker, idx) in filteredWorkers" :key="worker.id"
                  :class="{ 'editing-row': editingId === worker.id }">
                <td class="row-num">{{ idx + 1 }}</td>

                <template v-if="editingId === worker.id">
                  <td><input v-model="editBuffer.name" class="inline-input" /></td>
                  <td>
                    <select v-model.number="editBuffer.rank" class="inline-input inline-select">
                      <option v-for="r in RANKS" :key="r" :value="r">{{ r }}</option>
                    </select>
                  </td>
                  <td>
                    <select v-model="editBuffer.teamId" class="inline-input inline-select">
                      <option value="">{{ t('teams.noTeam') }}</option>
                      <option v-for="team in store.teams" :key="team.id" :value="team.id">{{ team.name }}</option>
                    </select>
                  </td>
                  <td>
                    <input v-model="editBuffer.equipment_type" class="inline-input" :placeholder="t('equip.multipleHelp')" />
                  </td>
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
                  <td>
                    <span class="team-badge-cell" :class="{ 'team-badge--none': !worker.teamId }">
                      {{ getTeamName(worker.teamId) }}
                    </span>
                  </td>
                  <td class="equip-cell">
                    <div class="equip-tags-wrap" v-if="getWorkerEquipmentList(worker).length > 0">
                      <span v-for="eq in getWorkerEquipmentList(worker)" :key="eq" class="equip-tag">
                        {{ eq }}
                      </span>
                    </div>
                    <span v-else class="text-muted">—</span>
                  </td>
                  <td class="num-cell">{{ worker.equipment_quantity }}</td>
                  <td class="actions-cell">
                    <button @click="startEdit(worker)" class="icon-btn edit-icon" title="Редагувати">✏️</button>
                    <button @click="removeWorker(worker.id)" class="icon-btn delete-icon" title="Видалити">🗑️</button>
                  </td>
                </template>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else-if="!showForm" class="empty-state">
          <p>{{ t('profile.empty', { btn: t('profile.add') }) }}</p>
        </div>
      </div>

      <!-- TEAMS TAB -->
      <div v-else-if="activeTab === 'teams'">
        <div class="page-title-row">
          <h2 class="page-title">{{ t('teams.title') }}</h2>
          <button class="add-btn" @click="showTeamForm = !showTeamForm">
            {{ showTeamForm ? t('profile.cancel') : t('teams.newTeam') }}
          </button>
        </div>

        <!-- Add team form -->
        <div v-if="showTeamForm" class="add-form-card">
          <h3 class="form-title">{{ t('teams.newTeam') }}</h3>
          <p v-if="teamValidationError" class="error-msg">{{ teamValidationError }}</p>
          <div class="form-grid">
            <div class="form-group">
              <label>{{ t('teams.teamName') }}</label>
              <input v-model="newTeam.name" type="text" :placeholder="t('teams.teamNamePlaceholder')" class="form-input" />
            </div>
            <div class="form-group span-2">
              <label>{{ t('teams.teamDesc') }}</label>
              <input v-model="newTeam.description" type="text" :placeholder="t('teams.teamDescPlaceholder')" class="form-input" />
            </div>
          </div>
          <button @click="addTeam" class="save-btn">{{ t('profile.save') }}</button>
        </div>

        <!-- Teams table -->
        <div class="table-card" v-if="store.teams.length > 0">
          <table class="workers-table">
            <thead>
              <tr>
                <th>#</th>
                <th>{{ t('teams.teamName') }}</th>
                <th>{{ t('teams.teamDesc') }}</th>
                <th>{{ t('teams.members') }}</th>
                <th>{{ t('profile.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(team, idx) in store.teams" :key="team.id" :class="{ 'editing-row': editingTeamId === team.id }">
                <td class="row-num">{{ idx + 1 }}</td>

                <template v-if="editingTeamId === team.id">
                  <td><input v-model="editTeamBuffer.name" class="inline-input" /></td>
                  <td><input v-model="editTeamBuffer.description" class="inline-input" /></td>
                  <td class="num-cell">{{ getTeamMemberCount(team.id) }}</td>
                  <td class="actions-cell">
                    <button @click="saveEditTeam(team.id)" class="icon-btn save-icon">✓</button>
                    <button @click="cancelEditTeam" class="icon-btn cancel-icon">✕</button>
                  </td>
                </template>

                <template v-else>
                  <td class="name-cell">
                    <span class="team-name-highlight">{{ team.name }}</span>
                  </td>
                  <td class="equip-cell">{{ team.description || '—' }}</td>
                  <td class="num-cell">
                    <span class="members-chip">{{ getTeamMemberCount(team.id) }}</span>
                  </td>
                  <td class="actions-cell">
                    <button @click="startEditTeam(team)" class="icon-btn edit-icon" title="Редагувати">✏️</button>
                    <button @click="removeTeam(team.id)" class="icon-btn delete-icon" title="Видалити">🗑️</button>
                  </td>
                </template>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else-if="!showTeamForm" class="empty-state">
          <p>{{ t('teams.empty') }}</p>
        </div>
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

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

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

.content-wrapper { max-width: 1200px; margin: 0 auto; padding: 25px 20px; }

/* Tabs */
.tabs-nav {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  border-bottom: 2px solid #e5e7eb;
  padding-bottom: 2px;
}
.tab-btn {
  padding: 10px 20px;
  border: none;
  background: transparent;
  font-size: 15px;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
  border-radius: 8px 8px 0 0;
  transition: all 0.2s;
}
.tab-btn:hover { color: #4e48eb; background: #eef2ff; }
.tab-btn--active {
  color: #4e48eb;
  border-bottom: 3px solid #4e48eb;
  background: #fff;
}

.page-title-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
.title-with-filter { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 0; }

.team-filter-inline {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #555;
}
.team-select {
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  background: #fff;
  font-size: 13px;
  font-family: inherit;
  color: #333;
}

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
.span-2 { grid-column: span 2; }
@media (max-width: 640px) { .span-2 { grid-column: span 1; } }

.form-group { display: flex; flex-direction: column; gap: 4px; }
.form-group label { font-size: 12px; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: .4px; }
.form-input {
  padding: 9px 12px; border: 1px solid #ddd; border-radius: 8px;
  font-size: 14px; background: #fafafa; transition: border .2s;
  font-family: inherit;
}
.form-input:focus { outline: none; border-color: #4e48eb; background: #fff; }
.form-hint { font-size: 11px; color: #888; margin-top: 2px; }

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

.team-badge-cell {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
  background: #eef2ff;
  color: #4e48eb;
  border: 1px solid #c7d2fe;
}
.team-badge--none {
  background: #f3f4f6;
  color: #9ca3af;
  border-color: #e5e7eb;
}

.equip-tags-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.equip-tag {
  display: inline-block;
  padding: 2px 8px;
  background: #f0fdf4;
  color: #166534;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}
.text-muted { color: #999; }

.team-name-highlight {
  font-size: 15px;
  font-weight: 700;
  color: #1a1a2e;
}

.members-chip {
  display: inline-block;
  padding: 3px 12px;
  background: #f3f4f6;
  border-radius: 12px;
  font-weight: 700;
  color: #4b5563;
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
