import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from './auth.js'
import { api } from '../api'

vi.mock('../api', () => ({
  api: {
    accessToken: null,
    refreshToken: null,
    login: vi.fn(),
    getMe: vi.fn(),
    clearTokens: vi.fn(),
    changePassword: vi.fn()
  }
}))

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    api.accessToken = null
  })

  describe('initial state', () => {
    it('starts with null user and not loading', () => {
      const store = useAuthStore()

      expect(store.user).toBeNull()
      expect(store.loading).toBe(false)
    })

    it('isAuthenticated is false without token', () => {
      const store = useAuthStore()

      expect(store.isAuthenticated).toBe(false)
    })

    it('isAuthenticated is true with token', () => {
      api.accessToken = 'valid-token'
      const store = useAuthStore()

      expect(store.isAuthenticated).toBe(true)
    })
  })

  describe('login', () => {
    it('sets loading during login', async () => {
      const store = useAuthStore()
      api.login.mockImplementation(() => new Promise(resolve => {
        expect(store.loading).toBe(true)
        resolve({ success: false })
      }))

      await store.login('user', 'pass')

      expect(store.loading).toBe(false)
    })

    it('fetches user on successful login', async () => {
      const store = useAuthStore()
      api.login.mockResolvedValue({ success: true })
      api.getMe.mockResolvedValue({ id: 1, username: 'testuser' })

      const result = await store.login('user', 'pass')

      expect(result.success).toBe(true)
      expect(api.getMe).toHaveBeenCalled()
      expect(store.user).toEqual({ id: 1, username: 'testuser' })
    })

    it('does not fetch user on failed login', async () => {
      const store = useAuthStore()
      api.login.mockResolvedValue({ success: false, error: 'Invalid credentials' })

      const result = await store.login('user', 'wrongpass')

      expect(result.success).toBe(false)
      expect(api.getMe).not.toHaveBeenCalled()
      expect(store.user).toBeNull()
    })

    it('resets loading on error', async () => {
      const store = useAuthStore()
      api.login.mockRejectedValue(new Error('Network error'))

      await expect(store.login('user', 'pass')).rejects.toThrow('Network error')

      expect(store.loading).toBe(false)
    })
  })

  describe('logout', () => {
    it('clears tokens and user', async () => {
      const store = useAuthStore()
      store.user = { id: 1, username: 'testuser' }

      await store.logout()

      expect(api.clearTokens).toHaveBeenCalled()
      expect(store.user).toBeNull()
    })
  })

  describe('fetchUser', () => {
    it('sets user from API response', async () => {
      const store = useAuthStore()
      api.getMe.mockResolvedValue({ id: 1, username: 'testuser' })

      await store.fetchUser()

      expect(store.user).toEqual({ id: 1, username: 'testuser' })
    })

    it('sets user to null on API failure', async () => {
      const store = useAuthStore()
      api.getMe.mockResolvedValue(null)

      await store.fetchUser()

      expect(store.user).toBeNull()
    })
  })

  describe('changePassword', () => {
    it('delegates to api.changePassword', async () => {
      const store = useAuthStore()
      api.changePassword.mockResolvedValue(true)

      const result = await store.changePassword('oldpass', 'newpass')

      expect(api.changePassword).toHaveBeenCalledWith('oldpass', 'newpass')
      expect(result).toBe(true)
    })
  })

  describe('init', () => {
    it('fetches user if token exists', async () => {
      api.accessToken = 'valid-token'
      api.getMe.mockResolvedValue({ id: 1, username: 'testuser' })
      const store = useAuthStore()

      await store.init()

      expect(api.getMe).toHaveBeenCalled()
      expect(store.user).toEqual({ id: 1, username: 'testuser' })
    })

    it('does not fetch user if no token', async () => {
      api.accessToken = null
      const store = useAuthStore()

      await store.init()

      expect(api.getMe).not.toHaveBeenCalled()
      expect(store.user).toBeNull()
    })

    it('clears tokens if fetch user fails', async () => {
      api.accessToken = 'invalid-token'
      api.getMe.mockRejectedValue(new Error('Unauthorized'))
      const store = useAuthStore()

      await store.init()

      expect(api.clearTokens).toHaveBeenCalled()
    })
  })
})
