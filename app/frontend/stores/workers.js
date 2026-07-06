import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useWorkersStore = defineStore('workers', () => {
  const workers = ref([])

  function addWorker(worker) {
    workers.value.push({
      id: crypto.randomUUID(),
      name: worker.name || '',
      rank: Number(worker.rank) || 0,
      equipment_type: worker.equipment_type || '',
      equipment_quantity: Number(worker.equipment_quantity) || 1,
    })
  }

  function updateWorker(id, updates) {
    const idx = workers.value.findIndex(w => w.id === id)
    if (idx !== -1) workers.value[idx] = { ...workers.value[idx], ...updates }
  }

  function removeWorker(id) {
    workers.value = workers.value.filter(w => w.id !== id)
  }

  function getProfile() {
    return { workers: workers.value.map(w => ({
      name: w.name,
      rank: Number(w.rank),
      equipment_type: w.equipment_type,
      equipment_quantity: Number(w.equipment_quantity),
    })) }
  }

  return { workers, addWorker, updateWorker, removeWorker, getProfile }
})
