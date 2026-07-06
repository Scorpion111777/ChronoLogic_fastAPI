import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  // Load persisted users from localStorage
  const _loadUsers = () => {
    try { return JSON.parse(localStorage.getItem('chronologic_users') || '[]') }
    catch { return [] }
  }
  const _saveUsers = (users) => {
    localStorage.setItem('chronologic_users', JSON.stringify(users))
  }
  const _loadSession = () => {
    try { return JSON.parse(localStorage.getItem('chronologic_session') || 'null') }
    catch { return null }
  }

  const users = ref(_loadUsers())
  const currentUser = ref(_loadSession())

  const isLoggedIn = computed(() => !!currentUser.value)
  const username = computed(() => currentUser.value?.name || '')

  function register(name, email, password) {
    const exists = users.value.find(u => u.email.toLowerCase() === email.toLowerCase())
    if (exists) return { success: false, error: 'Користувач з таким email вже існує' }
    if (password.length < 6) return { success: false, error: 'Пароль має бути не менше 6 символів' }

    const user = {
      id: crypto.randomUUID(),
      name: name.trim(),
      email: email.trim().toLowerCase(),
      password, // in production, hash this
      createdAt: new Date().toISOString(),
      avatar: name.trim()[0].toUpperCase(),
    }
    users.value.push(user)
    _saveUsers(users.value)
    _setSession(user)
    return { success: true }
  }

  function login(email, password) {
    const user = users.value.find(
      u => u.email.toLowerCase() === email.trim().toLowerCase() && u.password === password
    )
    if (!user) return { success: false, error: 'Невірний email або пароль' }
    _setSession(user)
    return { success: true }
  }

  function logout() {
    currentUser.value = null
    localStorage.removeItem('chronologic_session')
  }

  function _setSession(user) {
    const session = { id: user.id, name: user.name, email: user.email, avatar: user.avatar }
    currentUser.value = session
    localStorage.setItem('chronologic_session', JSON.stringify(session))
  }

  function updateProfile(updates) {
    const idx = users.value.findIndex(u => u.id === currentUser.value?.id)
    if (idx === -1) return { success: false, error: 'Користувача не знайдено' }
    users.value[idx] = { ...users.value[idx], ...updates }
    _saveUsers(users.value)
    _setSession(users.value[idx])
    return { success: true }
  }

  return { users, currentUser, isLoggedIn, username, register, login, logout, updateProfile }
})
