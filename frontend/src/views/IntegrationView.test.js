import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import IntegrationView from './IntegrationView.vue'
import { mountWithPlugins } from '../test/test-utils'
import { api } from '../api'

vi.mock('../api', () => ({
  api: {
    request: vi.fn()
  }
}))

describe('IntegrationView', () => {
  let wrapper

  beforeEach(() => {
    vi.clearAllMocks()
    wrapper = mountWithPlugins(IntegrationView)
  })

  describe('rendering', () => {
    it('renders integration title', () => {
      expect(wrapper.text()).toContain('External Time Manager Integration')
    })

    it('renders token input field', () => {
      const tokenInput = wrapper.find('input[type="password"]')
      expect(tokenInput.exists()).toBe(true)
    })

    it('renders date picker', () => {
      const datePicker = wrapper.find('input[type="text"]')
      expect(datePicker.exists()).toBe(true)
    })

    it('renders sync button', () => {
      const syncButton = wrapper.findAll('button').find(b => b.text().includes('Sync Now'))
      expect(syncButton).toBeDefined()
    })

    it('renders help section', () => {
      expect(wrapper.text()).toContain('How to get your API Token')
    })

    it('renders security warning', () => {
      expect(wrapper.text()).toContain('Keep your API token secure')
    })

    it('renders help steps', () => {
      expect(wrapper.text()).toContain('Log in to your external time management system')
      expect(wrapper.text()).toContain('Go to Settings or Profile section')
      expect(wrapper.text()).toContain('Generate a new API token')
    })
  })

  describe('validation', () => {
    it('shows warning when token is empty', async () => {
      const syncButton = wrapper.findAll('button').find(b => b.text().includes('Sync Now'))
      await syncButton.trigger('click')
      await flushPromises()

      // API should not be called
      expect(api.request).not.toHaveBeenCalled()
    })

    it('shows warning when date range is not selected', async () => {
      // Set both token and apiKey
      wrapper.vm.token = 'test-token'
      wrapper.vm.apiKey = 'test-api-key'

      // Clear date range by setting component data
      wrapper.vm.dateRange = null

      const syncButton = wrapper.findAll('button').find(b => b.text().includes('Sync Now'))
      await syncButton.trigger('click')
      await flushPromises()

      expect(api.request).not.toHaveBeenCalled()
    })
  })

  describe('sync functionality', () => {
    beforeEach(() => {
      // Set valid token and apiKey
      wrapper.vm.token = 'valid-api-token'
      wrapper.vm.apiKey = 'valid-api-key'
      wrapper.vm.dateRange = [new Date('2026-01-01'), new Date('2026-01-31')]
    })

    it('calls API with correct parameters on sync', async () => {
      api.request.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ imported: 10 })
      })

      const syncButton = wrapper.findAll('button').find(b => b.text().includes('Sync Now'))
      await syncButton.trigger('click')
      await flushPromises()

      expect(api.request).toHaveBeenCalledWith('/integrations/sync/', {
        method: 'POST',
        body: JSON.stringify({
          token: 'valid-api-token',
          api_key: 'valid-api-key',
          start_date: '2026-01-01',
          end_date: '2026-01-31'
        })
      })
    })

    it('shows success message on successful sync', async () => {
      api.request.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ imported: 15 })
      })

      const syncButton = wrapper.findAll('button').find(b => b.text().includes('Sync Now'))
      await syncButton.trigger('click')
      await flushPromises()

      expect(wrapper.text()).toContain('Successfully synced 15 signings')
    })

    it('shows error message on failed sync', async () => {
      api.request.mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ error: 'Invalid token' })
      })

      const syncButton = wrapper.findAll('button').find(b => b.text().includes('Sync Now'))
      await syncButton.trigger('click')
      await flushPromises()

      expect(wrapper.text()).toContain('Invalid token')
    })

    it('shows connection error on network failure', async () => {
      api.request.mockRejectedValue(new Error('Network error'))

      const syncButton = wrapper.findAll('button').find(b => b.text().includes('Sync Now'))
      await syncButton.trigger('click')
      await flushPromises()

      expect(wrapper.text()).toContain('Connection error')
    })

    it('shows loading state during sync', async () => {
      let resolveSync
      api.request.mockReturnValue(new Promise(resolve => {
        resolveSync = resolve
      }))

      const syncButton = wrapper.findAll('button').find(b => b.text().includes('Sync Now'))
      await syncButton.trigger('click')

      expect(wrapper.text()).toContain('Syncing data from external system')

      resolveSync({
        ok: true,
        json: () => Promise.resolve({ imported: 5 })
      })
      await flushPromises()

      expect(wrapper.text()).not.toContain('Syncing data from external system')
    })
  })

  describe('formatDateLocal', () => {
    it('formats date correctly', () => {
      const date = new Date('2026-02-15')
      const result = wrapper.vm.formatDateLocal(date)
      expect(result).toBe('2026-02-15')
    })

    it('pads single digit month and day', () => {
      const date = new Date('2026-01-05')
      const result = wrapper.vm.formatDateLocal(date)
      expect(result).toBe('2026-01-05')
    })
  })
})
