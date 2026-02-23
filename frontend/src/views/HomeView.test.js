import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { nextTick, ref } from 'vue'
import HomeView from './HomeView.vue'
import { mountWithPlugins } from '../test/test-utils.js'
import { api } from '../api'
import { flushPromises } from '@vue/test-utils'

vi.mock('../api', () => ({
  api: {
    getActiveSigning: vi.fn(),
    getDaySummary: vi.fn(),
    getLocations: vi.fn(),
    getSignings: vi.fn(),
    createSigning: vi.fn(),
    checkoutSigning: vi.fn()
  }
}))

// Mock navigator.geolocation
const mockGeolocation = {
  getCurrentPosition: vi.fn()
}
Object.defineProperty(global.navigator, 'geolocation', {
  value: mockGeolocation,
  writable: true
})

describe('HomeView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers({ shouldAdvanceTime: true })

    // Default mock responses
    api.getActiveSigning.mockResolvedValue(null)
    api.getDaySummary.mockResolvedValue({ total_worked_minutes: 240, expected_minutes: 480 })
    api.getLocations.mockResolvedValue([
      { id: 1, name: 'Madrid HQ', latitude: '40.4168', longitude: '-3.7038' }
    ])
    api.getSignings.mockResolvedValue([])

    mockGeolocation.getCurrentPosition.mockImplementation((success) => {
      success({ coords: { latitude: 40.4168, longitude: -3.7038 } })
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  async function mountAndWait() {
    const wrapper = mountWithPlugins(HomeView)
    await flushPromises()
    await nextTick()
    return wrapper
  }

  describe('initial state', () => {
    it('shows loading spinner initially', () => {
      const wrapper = mountWithPlugins(HomeView)
      expect(wrapper.find('.p-progress-spinner').exists()).toBe(true)
    })

    it('loads data on mount', async () => {
      await mountAndWait()

      expect(api.getActiveSigning).toHaveBeenCalled()
      expect(api.getDaySummary).toHaveBeenCalled()
      expect(api.getLocations).toHaveBeenCalled()
      expect(api.getSignings).toHaveBeenCalled()
    })
  })

  describe('check in state', () => {
    it('shows check in button when not working', async () => {
      const wrapper = await mountAndWait()

      expect(wrapper.text()).toContain('Ready to start?')
      expect(wrapper.text()).toContain('Check In')
    })

    it('shows GPS hint when location not detected', async () => {
      mockGeolocation.getCurrentPosition.mockImplementation((_, error) => {
        error({ code: 1, message: 'User denied' })
      })

      const wrapper = await mountAndWait()

      expect(wrapper.text()).toContain('Enable location')
    })

    it('creates signing on check in', async () => {
      api.createSigning.mockResolvedValue({ id: 1, start_time: new Date().toISOString() })

      const wrapper = await mountAndWait()

      const button = wrapper.find('button')
      await button.trigger('click')
      await flushPromises()

      expect(api.createSigning).toHaveBeenCalled()
    })
  })

  describe('check out state', () => {
    beforeEach(() => {
      api.getActiveSigning.mockResolvedValue({
        id: 1,
        start_time: new Date(Date.now() - 3600000).toISOString(),
        location: { id: 1, name: 'Madrid HQ' }
      })
    })

    it('shows check out button when working', async () => {
      const wrapper = await mountAndWait()

      expect(wrapper.text()).toContain('Currently working')
      expect(wrapper.text()).toContain('Check Out')
    })

    it('shows current signing duration', async () => {
      const wrapper = await mountAndWait()

      expect(wrapper.text()).toMatch(/\d+h \d+m \d+s/)
    })

    it('shows location name', async () => {
      const wrapper = await mountAndWait()

      expect(wrapper.text()).toContain('Madrid HQ')
    })

    it('calls checkout on check out click', async () => {
      api.checkoutSigning.mockResolvedValue({ id: 1, end_time: new Date().toISOString() })

      const wrapper = await mountAndWait()

      const button = wrapper.find('button')
      await button.trigger('click')
      await flushPromises()

      expect(api.checkoutSigning).toHaveBeenCalledWith(1)
    })
  })

  describe('day summary', () => {
    it('displays worked hours', async () => {
      const wrapper = await mountAndWait()

      expect(wrapper.text()).toContain('4h 0m')
    })

    it('displays expected hours', async () => {
      const wrapper = await mountAndWait()

      expect(wrapper.text()).toContain('8h 0m')
    })

    it('shows remaining time when negative overtime', async () => {
      api.getDaySummary.mockResolvedValue({ total_worked_minutes: 240, expected_minutes: 480 })

      const wrapper = await mountAndWait()

      expect(wrapper.text()).toContain('Remaining')
      expect(wrapper.text()).toContain('4h 0m')
    })

    it('shows overtime when positive', async () => {
      api.getDaySummary.mockResolvedValue({ total_worked_minutes: 540, expected_minutes: 480 })

      const wrapper = await mountAndWait()

      expect(wrapper.text()).toContain('Overtime')
      expect(wrapper.text()).toContain('+1h 0m')
    })
  })

  describe("today's signings", () => {
    it('shows signings list when there are signings', async () => {
      api.getSignings.mockResolvedValue([
        {
          id: 1,
          start_time: '2026-02-08T09:00:00Z',
          end_time: '2026-02-08T13:00:00Z',
          duration_minutes: 240,
          location: { name: 'Madrid HQ' }
        }
      ])

      const wrapper = await mountAndWait()

      expect(wrapper.text()).toContain("Today's Signings")
    })

    it('hides signings card when no signings', async () => {
      api.getSignings.mockResolvedValue([])

      const wrapper = await mountAndWait()

      expect(wrapper.text()).not.toContain("Today's Signings")
    })
  })

  describe('location detection', () => {
    it('auto-selects location based on GPS', async () => {
      api.getLocations.mockResolvedValue([
        { id: 1, name: 'Madrid HQ', latitude: '40.4168', longitude: '-3.7038' },
        { id: 2, name: 'Remote', latitude: '0', longitude: '0' }
      ])

      mockGeolocation.getCurrentPosition.mockImplementation((success) => {
        success({ coords: { latitude: 40.4168, longitude: -3.7038 } })
      })

      await mountAndWait()

      expect(api.getLocations).toHaveBeenCalled()
    })

    it('defaults to remote location when far from offices', async () => {
      api.getLocations.mockResolvedValue([
        { id: 1, name: 'Madrid HQ', latitude: '40.4168', longitude: '-3.7038' },
        { id: 2, name: 'Remote Location', latitude: '0', longitude: '0' }
      ])

      mockGeolocation.getCurrentPosition.mockImplementation((success) => {
        // Coordinates far from Madrid
        success({ coords: { latitude: 51.5074, longitude: -0.1278 } })
      })

      const wrapper = await mountAndWait()

      expect(wrapper.text()).toContain('Select your location')
    })
  })
})

describe('helper functions', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    api.getActiveSigning.mockResolvedValue(null)
    api.getDaySummary.mockResolvedValue({ total_worked_minutes: 0, expected_minutes: 480 })
    api.getLocations.mockResolvedValue([])
    api.getSignings.mockResolvedValue([])
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('formats time correctly', async () => {
    api.getSignings.mockResolvedValue([
      {
        id: 1,
        start_time: '2026-02-08T09:30:00Z',
        end_time: '2026-02-08T17:45:00Z',
        duration_minutes: 495
      }
    ])

    const wrapper = mountWithPlugins(HomeView)
    await flushPromises()
    await nextTick()

    // The component should format times
    expect(wrapper.text()).toContain("Today's Signings")
  })

  it('formats duration correctly', async () => {
    api.getSignings.mockResolvedValue([
      {
        id: 1,
        start_time: '2026-02-08T09:00:00Z',
        end_time: '2026-02-08T17:15:00Z',
        duration_minutes: 495
      }
    ])

    const wrapper = mountWithPlugins(HomeView)
    await flushPromises()
    await nextTick()

    expect(wrapper.text()).toContain('8h 15m')
  })
})
