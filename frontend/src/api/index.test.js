import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api } from './index.js'

describe('ApiClient', () => {
  beforeEach(() => {
    api.accessToken = null
    api.refreshToken = null
    vi.clearAllMocks()
  })

  describe('setTokens', () => {
    it('sets tokens in instance and localStorage', () => {
      api.setTokens('access123', 'refresh456')

      expect(api.accessToken).toBe('access123')
      expect(api.refreshToken).toBe('refresh456')
      expect(localStorage.setItem).toHaveBeenCalledWith('accessToken', 'access123')
      expect(localStorage.setItem).toHaveBeenCalledWith('refreshToken', 'refresh456')
    })
  })

  describe('clearTokens', () => {
    it('clears tokens from instance and localStorage', () => {
      api.accessToken = 'access123'
      api.refreshToken = 'refresh456'

      api.clearTokens()

      expect(api.accessToken).toBeNull()
      expect(api.refreshToken).toBeNull()
      expect(localStorage.removeItem).toHaveBeenCalledWith('accessToken')
      expect(localStorage.removeItem).toHaveBeenCalledWith('refreshToken')
    })
  })

  describe('login', () => {
    it('returns success and sets tokens on valid login', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ access: 'new-access', refresh: 'new-refresh' })
      })

      const result = await api.login('user', 'pass')

      expect(result.success).toBe(true)
      expect(api.accessToken).toBe('new-access')
      expect(api.refreshToken).toBe('new-refresh')
      expect(fetch).toHaveBeenCalledWith('/api/auth/token/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: 'user', password: 'pass' })
      })
    })

    it('returns error on invalid credentials', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ detail: 'Invalid credentials' })
      })

      const result = await api.login('user', 'wrongpass')

      expect(result.success).toBe(false)
      expect(result.error).toBe('Invalid credentials')
      expect(api.accessToken).toBeNull()
    })
  })

  describe('request', () => {
    it('adds authorization header when token exists', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({ status: 200, ok: true })

      await api.request('/test/')

      expect(fetch).toHaveBeenCalledWith('/api/test/', {
        headers: {
          'Authorization': 'Bearer test-token',
          'Content-Type': 'application/json'
        }
      })
    })

    it('does not add Content-Type for FormData', async () => {
      api.accessToken = 'test-token'
      const formData = new FormData()
      global.fetch = vi.fn().mockResolvedValue({ status: 200, ok: true })

      await api.request('/upload/', { method: 'POST', body: formData })

      const callArgs = fetch.mock.calls[0][1]
      expect(callArgs.headers['Content-Type']).toBeUndefined()
      expect(callArgs.headers['Authorization']).toBe('Bearer test-token')
    })

    it('attempts token refresh on 401 response', async () => {
      api.accessToken = 'expired-token'
      api.refreshToken = 'valid-refresh'

      let callCount = 0
      global.fetch = vi.fn().mockImplementation((url) => {
        if (url.includes('/refresh/')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ access: 'new-access' })
          })
        }
        callCount++
        if (callCount === 1) {
          return Promise.resolve({ status: 401, ok: false })
        }
        return Promise.resolve({ status: 200, ok: true })
      })

      await api.request('/protected/')

      expect(api.accessToken).toBe('new-access')
      expect(fetch).toHaveBeenCalledTimes(3)
    })

    it('clears tokens if refresh fails', async () => {
      api.accessToken = 'expired-token'
      api.refreshToken = 'invalid-refresh'

      global.fetch = vi.fn().mockImplementation((url) => {
        if (url.includes('/refresh/')) {
          return Promise.resolve({ ok: false })
        }
        return Promise.resolve({ status: 401, ok: false })
      })

      await api.request('/protected/')

      expect(api.accessToken).toBeNull()
      expect(api.refreshToken).toBeNull()
    })
  })

  describe('getMe', () => {
    it('returns user data on success', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ id: 1, username: 'testuser' })
      })

      const user = await api.getMe()

      expect(user).toEqual({ id: 1, username: 'testuser' })
    })

    it('returns null on failure', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401
      })

      const user = await api.getMe()

      expect(user).toBeNull()
    })
  })

  describe('changePassword', () => {
    it('returns true on successful password change', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200
      })

      const result = await api.changePassword('oldpass', 'newpass')

      expect(result).toBe(true)
    })

    it('returns false on failed password change', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 400
      })

      const result = await api.changePassword('wrongpass', 'newpass')

      expect(result).toBe(false)
    })
  })

  describe('getActiveSigning', () => {
    it('returns active signing when present', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ id: 1, start_time: '2026-02-08T09:00:00Z' })
      })

      const signing = await api.getActiveSigning()

      expect(signing).toEqual({ id: 1, start_time: '2026-02-08T09:00:00Z' })
    })

    it('returns active from wrapper object', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ active: { id: 1, start_time: '2026-02-08T09:00:00Z' } })
      })

      const signing = await api.getActiveSigning()

      expect(signing).toEqual({ id: 1, start_time: '2026-02-08T09:00:00Z' })
    })

    it('returns null on no active signing', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404
      })

      const signing = await api.getActiveSigning()

      expect(signing).toBeNull()
    })
  })

  describe('createSigning', () => {
    it('creates signing and returns data', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 201,
        json: () => Promise.resolve({ id: 1, start_time: '2026-02-08T09:00:00Z' })
      })

      const signing = await api.createSigning({ location: 1 })

      expect(signing).toEqual({ id: 1, start_time: '2026-02-08T09:00:00Z' })
    })

    it('throws error on failure', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 400
      })

      await expect(api.createSigning({ location: 1 })).rejects.toThrow('Failed to create signing')
    })
  })

  describe('checkoutSigning', () => {
    it('checks out signing and returns data', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ id: 1, end_time: '2026-02-08T18:00:00Z' })
      })

      const signing = await api.checkoutSigning(1)

      expect(signing).toEqual({ id: 1, end_time: '2026-02-08T18:00:00Z' })
    })

    it('sends end_time when provided', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ id: 1 })
      })

      await api.checkoutSigning(1, '2026-02-08T17:30:00Z')

      const callBody = JSON.parse(fetch.mock.calls[0][1].body)
      expect(callBody.end_time).toBe('2026-02-08T17:30:00Z')
    })

    it('throws error on failure', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 400
      })

      await expect(api.checkoutSigning(1)).rejects.toThrow('Failed to checkout')
    })
  })

  describe('getSignings', () => {
    it('returns signings list', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve([{ id: 1 }, { id: 2 }])
      })

      const signings = await api.getSignings({ start_date: '2026-02-01', end_date: '2026-02-08' })

      expect(signings).toHaveLength(2)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('start_date=2026-02-01'),
        expect.any(Object)
      )
    })

    it('returns empty array on failure', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500
      })

      const signings = await api.getSignings()

      expect(signings).toEqual([])
    })
  })

  describe('updateSigning', () => {
    it('updates signing and returns data', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ id: 1, description: 'Updated' })
      })

      const signing = await api.updateSigning(1, { description: 'Updated' })

      expect(signing).toEqual({ id: 1, description: 'Updated' })
    })

    it('throws error on failure', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404
      })

      await expect(api.updateSigning(999, {})).rejects.toThrow('Failed to update signing')
    })
  })

  describe('deleteSigning', () => {
    it('returns true on successful delete', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 204
      })

      const result = await api.deleteSigning(1)

      expect(result).toBe(true)
    })

    it('returns false on failed delete', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404
      })

      const result = await api.deleteSigning(999)

      expect(result).toBe(false)
    })
  })

  describe('getDaySummary', () => {
    it('returns summary for today', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ total_worked_minutes: 480 })
      })

      const summary = await api.getDaySummary()

      expect(summary).toEqual({ total_worked_minutes: 480 })
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/summary/day/'), expect.any(Object))
    })

    it('returns summary for specific date', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ total_worked_minutes: 510 })
      })

      await api.getDaySummary('2026-02-07')

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/summary/day/2026-02-07/'),
        expect.any(Object)
      )
    })

    it('returns null on failure', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404
      })

      const summary = await api.getDaySummary('2026-02-07')

      expect(summary).toBeNull()
    })
  })

  describe('exportSignings', () => {
    it('returns blob on success', async () => {
      api.accessToken = 'test-token'
      const mockBlob = new Blob(['csv,data'], { type: 'text/csv' })
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        blob: () => Promise.resolve(mockBlob)
      })

      const blob = await api.exportSignings('2026-02-01', '2026-02-08')

      expect(blob).toBe(mockBlob)
    })

    it('throws error on failure', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 400
      })

      await expect(api.exportSignings('2026-02-01', '2026-02-08')).rejects.toThrow('Export failed')
    })
  })

  describe('importSignings', () => {
    it('imports file and returns result', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ imported: 5, errors: [] })
      })

      const file = new File(['csv,data'], 'test.csv', { type: 'text/csv' })
      const result = await api.importSignings(file)

      expect(result).toEqual({ imported: 5, errors: [] })
      const callBody = fetch.mock.calls[0][1].body
      expect(callBody).toBeInstanceOf(FormData)
    })
  })

  describe('getLocations', () => {
    it('returns locations list', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve([{ id: 1, name: 'Madrid HQ' }])
      })

      const locations = await api.getLocations()

      expect(locations).toEqual([{ id: 1, name: 'Madrid HQ' }])
    })

    it('returns empty array on failure', async () => {
      api.accessToken = 'test-token'
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500
      })

      const locations = await api.getLocations()

      expect(locations).toEqual([])
    })
  })
})
