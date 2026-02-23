import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => !!api.accessToken)

  async function login(username, password) {
    loading.value = true
    try {
      const result = await api.login(username, password)
      if (result.success) {
        await fetchUser()
      }
      return result
    } finally {
      loading.value = false
    }
  }

  async function fetchUser() {
    user.value = await api.getMe()
  }

  async function logout() {
    api.clearTokens()
    user.value = null
  }

  async function changePassword(currentPassword, newPassword) {
    return api.changePassword(currentPassword, newPassword)
  }

  // Initialize: check if we have a valid token
  async function init() {
    if (api.accessToken) {
      try {
        await fetchUser()
      } catch {
        api.clearTokens()
      }
    }
  }

  return {
    user,
    loading,
    isAuthenticated,
    login,
    logout,
    fetchUser,
    changePassword,
    init
  }
})
