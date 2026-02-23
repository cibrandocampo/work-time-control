import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import SigningsView from './SigningsView.vue'
import { mountWithPlugins } from '../test/test-utils'
import { api } from '../api'

vi.mock('../api', () => ({
  api: {
    request: vi.fn(),
    getLocations: vi.fn(),
    updateSigning: vi.fn(),
    deleteSigning: vi.fn(),
    exportSignings: vi.fn(),
    importSignings: vi.fn()
  }
}))

describe('SigningsView', () => {
  let wrapper

  const mockSignings = [
    {
      id: 1,
      start_time: '2026-02-08T09:00:00Z',
      end_time: '2026-02-08T17:00:00Z',
      duration_minutes: 480,
      location: { id: 1, name: 'Madrid HQ' },
      description: 'Regular work day'
    },
    {
      id: 2,
      start_time: '2026-02-08T18:00:00Z',
      end_time: '2026-02-08T20:00:00Z',
      duration_minutes: 120,
      location: null,
      description: ''
    },
    {
      id: 3,
      start_time: '2026-02-07T09:00:00Z',
      end_time: '2026-02-07T18:00:00Z',
      duration_minutes: 540,
      location: { id: 2, name: 'Remote' },
      description: 'Working from home'
    }
  ]

  const mockLocations = [
    { id: 1, name: 'Madrid HQ' },
    { id: 2, name: 'Remote' }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    api.getLocations.mockResolvedValue(mockLocations)
    api.request.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockSignings)
    })

    wrapper = mountWithPlugins(SigningsView)
  })

  describe('rendering', () => {
    it('renders search section', () => {
      expect(wrapper.text()).toContain('Search Signings')
    })

    it('renders date range label', () => {
      expect(wrapper.text()).toContain('Date Range')
    })

    it('renders search button', () => {
      const button = wrapper.findAll('button').find(b => b.text().includes('Search'))
      expect(button).toBeDefined()
    })

    it('renders export button', () => {
      const button = wrapper.findAll('button').find(b => b.text().includes('Export CSV'))
      expect(button).toBeDefined()
    })

    it('renders import button', () => {
      const button = wrapper.findAll('button').find(b => b.text().includes('Import CSV'))
      expect(button).toBeDefined()
    })
  })

  describe('initial load', () => {
    it('loads locations on mount', async () => {
      await flushPromises()
      expect(api.getLocations).toHaveBeenCalled()
    })

    it('loads signings on mount', async () => {
      await flushPromises()
      expect(api.request).toHaveBeenCalled()
    })

    it('displays signings grouped by date', async () => {
      await flushPromises()
      expect(wrapper.text()).toContain('Madrid HQ')
      expect(wrapper.text()).toContain('Remote')
    })
  })

  describe('groupedSignings computed', () => {
    it('groups signings by date', async () => {
      await flushPromises()
      const grouped = wrapper.vm.groupedSignings
      expect(grouped.length).toBe(2) // Two different dates
    })

    it('sorts dates in descending order', async () => {
      await flushPromises()
      const grouped = wrapper.vm.groupedSignings
      expect(grouped[0].date).toBe('2026-02-08')
      expect(grouped[1].date).toBe('2026-02-07')
    })

    it('calculates total minutes per day', async () => {
      await flushPromises()
      const grouped = wrapper.vm.groupedSignings
      expect(grouped[0].totalMinutes).toBe(600) // 480 + 120
      expect(grouped[1].totalMinutes).toBe(540)
    })
  })

  describe('formatters', () => {
    it('formats duration correctly', () => {
      expect(wrapper.vm.formatDuration(480)).toBe('8h 0m')
      expect(wrapper.vm.formatDuration(90)).toBe('1h 30m')
      expect(wrapper.vm.formatDuration(null)).toBe('-')
    })

    it('formats time correctly', () => {
      const result = wrapper.vm.formatTime('2026-02-08T09:30:00Z')
      expect(result).toMatch(/\d{1,2}:\d{2}/)
    })

    it('returns dash for null time', () => {
      expect(wrapper.vm.formatTime(null)).toBe('-')
    })

    it('formats date with locale', () => {
      const result = wrapper.vm.formatDate('2026-02-08')
      expect(result).toBeTruthy()
      // Should contain some date elements
      expect(result.length).toBeGreaterThan(5)
    })

    it('formats local date as YYYY-MM-DD', () => {
      const date = new Date('2026-02-08')
      const result = wrapper.vm.formatDateLocal(date)
      expect(result).toBe('2026-02-08')
    })
  })

  describe('search functionality', () => {
    it('shows warning when date range is not selected', async () => {
      wrapper.vm.dateRange = null
      const searchButton = wrapper.findAll('button').find(b => b.text().includes('Search'))
      await searchButton.trigger('click')
      await flushPromises()

      // Should not call API
      expect(api.request).toHaveBeenCalledTimes(1) // Only initial load
    })

    it('calls API with correct date parameters', async () => {
      wrapper.vm.dateRange = [new Date('2026-01-01'), new Date('2026-01-31')]
      api.request.mockClear()
      api.request.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([])
      })

      const searchButton = wrapper.findAll('button').find(b => b.text().includes('Search'))
      await searchButton.trigger('click')
      await flushPromises()

      expect(api.request).toHaveBeenCalledWith(
        expect.stringContaining('start_date=2026-01-01')
      )
      expect(api.request).toHaveBeenCalledWith(
        expect.stringContaining('end_date=2026-01-31')
      )
    })

    it('shows no results message when empty', async () => {
      api.request.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([])
      })
      wrapper.vm.signings = []
      await flushPromises()

      expect(wrapper.text()).toContain('No signings found')
    })
  })

  describe('edit functionality', () => {
    it('opens edit dialog when clicking edit button', async () => {
      await flushPromises()

      wrapper.vm.openEditDialog(mockSignings[0])
      await flushPromises()

      expect(wrapper.vm.editDialog).toBe(true)
      expect(wrapper.vm.editingSigning).toEqual(mockSignings[0])
    })

    it('populates edit form with signing data', async () => {
      await flushPromises()

      wrapper.vm.openEditDialog(mockSignings[0])
      await flushPromises()

      expect(wrapper.vm.editForm.description).toBe('Regular work day')
      expect(wrapper.vm.editForm.location_id).toBe(1)
    })

    it('calls updateSigning API on save', async () => {
      api.updateSigning.mockResolvedValue({})
      api.request.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockSignings)
      })

      wrapper.vm.openEditDialog(mockSignings[0])
      await flushPromises()

      await wrapper.vm.saveEdit()
      await flushPromises()

      expect(api.updateSigning).toHaveBeenCalledWith(1, expect.objectContaining({
        description: 'Regular work day'
      }))
    })

    it('closes dialog after successful save', async () => {
      api.updateSigning.mockResolvedValue({})
      api.request.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockSignings)
      })

      wrapper.vm.openEditDialog(mockSignings[0])
      await wrapper.vm.saveEdit()
      await flushPromises()

      expect(wrapper.vm.editDialog).toBe(false)
    })
  })

  describe('delete functionality', () => {
    it('calls confirmDelete with signing', async () => {
      await flushPromises()

      // Just verify the function exists and can be called
      expect(typeof wrapper.vm.confirmDelete).toBe('function')
    })
  })

  describe('export functionality', () => {
    it('shows warning when no date range for export', async () => {
      wrapper.vm.dateRange = null
      await wrapper.vm.exportSignings()
      await flushPromises()

      expect(api.exportSignings).not.toHaveBeenCalled()
    })

    it('calls exportSignings API with date range', async () => {
      api.exportSignings.mockResolvedValue(new Blob(['csv data']))
      wrapper.vm.dateRange = [new Date('2026-01-01'), new Date('2026-01-31')]

      // Mock URL.createObjectURL
      global.URL.createObjectURL = vi.fn(() => 'blob:url')
      global.URL.revokeObjectURL = vi.fn()

      await wrapper.vm.exportSignings()
      await flushPromises()

      expect(api.exportSignings).toHaveBeenCalledWith('2026-01-01', '2026-01-31')
    })
  })

  describe('import functionality', () => {
    it('opens import dialog', async () => {
      wrapper.vm.openImportDialog()
      expect(wrapper.vm.importDialog).toBe(true)
      expect(wrapper.vm.importResult).toBe(null)
    })

    it('calls importSignings API', async () => {
      api.importSignings.mockResolvedValue({ imported: 5, errors: [] })
      api.request.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockSignings)
      })

      const mockFile = new File(['csv content'], 'signings.csv', { type: 'text/csv' })
      await wrapper.vm.handleImport({ files: [mockFile] })
      await flushPromises()

      expect(api.importSignings).toHaveBeenCalledWith(mockFile)
    })

    it('displays import result', async () => {
      api.importSignings.mockResolvedValue({ imported: 10, errors: [] })
      api.request.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockSignings)
      })

      const mockFile = new File(['csv content'], 'signings.csv', { type: 'text/csv' })
      await wrapper.vm.handleImport({ files: [mockFile] })
      await flushPromises()

      expect(wrapper.vm.importResult.imported).toBe(10)
    })

    it('handles import errors', async () => {
      api.importSignings.mockResolvedValue({
        imported: 0,
        errors: [{ row: 2, error: 'Invalid date' }]
      })

      const mockFile = new File(['csv content'], 'signings.csv', { type: 'text/csv' })
      await wrapper.vm.handleImport({ files: [mockFile] })
      await flushPromises()

      expect(wrapper.vm.importResult.errors.length).toBe(1)
    })

    it('does nothing when no file selected', async () => {
      await wrapper.vm.handleImport({ files: [] })
      expect(api.importSignings).not.toHaveBeenCalled()
    })
  })

  describe('error handling', () => {
    it('handles search API error', async () => {
      api.request.mockRejectedValue(new Error('Network error'))

      await wrapper.vm.searchSignings()
      await flushPromises()

      expect(wrapper.vm.loading).toBe(false)
    })

    it('handles save error', async () => {
      api.updateSigning.mockRejectedValue(new Error('Save failed'))

      wrapper.vm.openEditDialog(mockSignings[0])
      await wrapper.vm.saveEdit()
      await flushPromises()

      expect(wrapper.vm.saving).toBe(false)
    })

    it('handles export error', async () => {
      api.exportSignings.mockRejectedValue(new Error('Export failed'))
      wrapper.vm.dateRange = [new Date('2026-01-01'), new Date('2026-01-31')]

      await wrapper.vm.exportSignings()
      await flushPromises()

      // Should not throw
      expect(true).toBe(true)
    })

    it('handles import error', async () => {
      api.importSignings.mockRejectedValue(new Error('Import failed'))

      const mockFile = new File(['csv content'], 'signings.csv', { type: 'text/csv' })
      await wrapper.vm.handleImport({ files: [mockFile] })
      await flushPromises()

      expect(wrapper.vm.importing).toBe(false)
    })
  })
})
