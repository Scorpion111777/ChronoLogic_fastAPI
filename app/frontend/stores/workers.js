import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useWorkersStore = defineStore('workers', () => {
  const workers = ref([])
  const teams = ref([])

  function _getStorageKey(prefix, userId) {
    return userId ? `chronologic_${prefix}_${userId}` : `chronologic_${prefix}_guest`
  }

  function loadForUser(userId) {
    try {
      const rawWorkers = localStorage.getItem(_getStorageKey('workers', userId))
      workers.value = rawWorkers ? JSON.parse(rawWorkers) : []

      const rawTeams = localStorage.getItem(_getStorageKey('teams', userId))
      teams.value = rawTeams ? JSON.parse(rawTeams) : [
        { id: 'team-1', name: 'Бригада №1', description: 'Основна бригада цеху' },
        { id: 'team-2', name: 'Бригада №2', description: 'Змінна бригада' }
      ]
    } catch (e) {
      console.error('Error loading workers/teams:', e)
      workers.value = []
      teams.value = []
    }
  }

  function _save(userId) {
    try {
      localStorage.setItem(_getStorageKey('workers', userId), JSON.stringify(workers.value))
      localStorage.setItem(_getStorageKey('teams', userId), JSON.stringify(teams.value))
    } catch (e) {
      console.error('Error saving workers/teams:', e)
    }
  }

  function _normalizeEquipment(equipmentInput) {
    if (Array.isArray(equipmentInput)) {
      const cleaned = equipmentInput.map(e => String(e).trim()).filter(Boolean)
      return {
        types: cleaned,
        string: cleaned.join(', ')
      }
    }
    if (typeof equipmentInput === 'string') {
      const parts = equipmentInput
        .split(/[,;/|\n]/)
        .map(p => p.trim())
        .filter(Boolean)
      return {
        types: parts,
        string: parts.join(', ')
      }
    }
    return { types: [], string: '' }
  }

  // --- Team methods ---
  function addTeam(team, userId) {
    const newTeam = {
      id: crypto.randomUUID(),
      name: (team.name || '').trim(),
      description: (team.description || '').trim(),
      createdAt: new Date().toISOString(),
    }
    teams.value.push(newTeam)
    _save(userId)
    return newTeam
  }

  function updateTeam(id, updates, userId) {
    const idx = teams.value.findIndex(t => t.id === id)
    if (idx !== -1) {
      teams.value[idx] = { ...teams.value[idx], ...updates }
      _save(userId)
    }
  }

  function removeTeam(id, userId) {
    teams.value = teams.value.filter(t => t.id !== id)
    // Remove team reference from workers
    workers.value.forEach(w => {
      if (w.teamId === id) w.teamId = null
    })
    _save(userId)
  }

  // --- Worker methods ---
  function addWorker(worker, userId) {
    const eq = _normalizeEquipment(worker.equipment_types || worker.equipment_type)
    const newWorker = {
      id: crypto.randomUUID(),
      name: (worker.name || '').trim(),
      rank: Number(worker.rank) || 1,
      equipment_type: eq.string,
      equipment_types: eq.types,
      equipment_quantity: Number(worker.equipment_quantity) || 1,
      teamId: worker.teamId || null,
    }
    workers.value.push(newWorker)
    _save(userId)
    return newWorker
  }

  function updateWorker(id, updates, userId) {
    const idx = workers.value.findIndex(w => w.id === id)
    if (idx !== -1) {
      let eqData = {}
      if (updates.equipment_types !== undefined || updates.equipment_type !== undefined) {
        const eq = _normalizeEquipment(updates.equipment_types || updates.equipment_type)
        eqData = {
          equipment_type: eq.string,
          equipment_types: eq.types,
        }
      }
      workers.value[idx] = {
        ...workers.value[idx],
        ...updates,
        ...eqData,
        rank: updates.rank !== undefined ? Number(updates.rank) : workers.value[idx].rank,
        equipment_quantity: updates.equipment_quantity !== undefined ? Number(updates.equipment_quantity) : workers.value[idx].equipment_quantity,
      }
      _save(userId)
    }
  }

  function removeWorker(id, userId) {
    workers.value = workers.value.filter(w => w.id !== id)
    _save(userId)
  }

  function getProfile(selectedTeamId = null) {
    let list = workers.value
    if (selectedTeamId && selectedTeamId !== 'all') {
      list = list.filter(w => w.teamId === selectedTeamId)
    }

    return {
      workers: list.map(w => ({
        name: w.name,
        rank: Number(w.rank),
        equipment_type: w.equipment_type,
        equipment_types: w.equipment_types && w.equipment_types.length > 0 ? w.equipment_types : _normalizeEquipment(w.equipment_type).types,
        equipment_quantity: Number(w.equipment_quantity) || 1,
        teamId: w.teamId || null,
      }))
    }
  }

  return {
    workers,
    teams,
    loadForUser,
    addTeam,
    updateTeam,
    removeTeam,
    addWorker,
    updateWorker,
    removeWorker,
    getProfile,
  }
})
