import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import SettingsView from './SettingsView.vue'
import { mountWithPlugins } from '../test/test-utils'
import { useAuthStore } from '../stores/auth'

// Mock vue-router
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn()
  })
}))

describe('SettingsView', () => {
  let wrapper
  let authStore

  beforeEach(() => {
    vi.clearAllMocks()
    wrapper = mountWithPlugins(SettingsView)
    authStore = useAuthStore()
    authStore.user = { username: 'testuser', email: 'test@example.com' }
  })

  describe('rendering', () => {
    it('renders language section', () => {
      expect(wrapper.text()).toContain('Language')
    })

    it('renders account section', () => {
      expect(wrapper.text()).toContain('Account')
    })

    it('renders change password section', () => {
      expect(wrapper.text()).toContain('Change Password')
    })

    it('renders logout section', () => {
      expect(wrapper.text()).toContain('Logout')
    })

    it('displays user information', async () => {
      await flushPromises()
      expect(wrapper.text()).toContain('testuser')
      expect(wrapper.text()).toContain('test@example.com')
    })

    it('shows dash when email is empty', async () => {
      // Update user with empty email - the component reactively updates
      authStore.user = { username: 'testuser', email: '' }
      await flushPromises()
      // Check that the dash is shown for empty email (the || '-' fallback)
      const infoValues = wrapper.findAll('.info-value')
      const emailValue = infoValues[1] // Second info-value is email
      expect(emailValue.text()).toBe('-')
    })
  })

  describe('password change validation', () => {
    it('shows error when fields are empty', async () => {
      const form = wrapper.find('form')
      await form.trigger('submit')
      await flushPromises()

      expect(wrapper.text()).toContain('Please fill in all fields')
    })

    it('shows error when passwords do not match', async () => {
      const inputs = wrapper.findAll('input[type="password"]')
      await inputs[0].setValue('currentpass')
      await inputs[1].setValue('newpassword123')
      await inputs[2].setValue('differentpassword')

      const form = wrapper.find('form')
      await form.trigger('submit')
      await flushPromises()

      expect(wrapper.text()).toContain('Passwords do not match')
    })

    it('shows error when password is too short', async () => {
      const inputs = wrapper.findAll('input[type="password"]')
      await inputs[0].setValue('currentpass')
      await inputs[1].setValue('short')
      await inputs[2].setValue('short')

      const form = wrapper.find('form')
      await form.trigger('submit')
      await flushPromises()

      expect(wrapper.text()).toContain('Password must be at least 8 characters')
    })
  })

  describe('password change API', () => {
    beforeEach(() => {
      authStore.changePassword = vi.fn()
    })

    it('calls changePassword on valid submission', async () => {
      authStore.changePassword.mockResolvedValue(true)

      const inputs = wrapper.findAll('input[type="password"]')
      await inputs[0].setValue('currentpass')
      await inputs[1].setValue('newpassword123')
      await inputs[2].setValue('newpassword123')

      const form = wrapper.find('form')
      await form.trigger('submit')
      await flushPromises()

      expect(authStore.changePassword).toHaveBeenCalledWith('currentpass', 'newpassword123')
    })

    it('clears form on successful password change', async () => {
      authStore.changePassword.mockResolvedValue(true)

      const inputs = wrapper.findAll('input[type="password"]')
      await inputs[0].setValue('currentpass')
      await inputs[1].setValue('newpassword123')
      await inputs[2].setValue('newpassword123')

      const form = wrapper.find('form')
      await form.trigger('submit')
      await flushPromises()

      // Form should be cleared
      expect(inputs[0].element.value).toBe('')
    })

    it('shows error when current password is incorrect', async () => {
      authStore.changePassword.mockResolvedValue(false)

      const inputs = wrapper.findAll('input[type="password"]')
      await inputs[0].setValue('wrongpass')
      await inputs[1].setValue('newpassword123')
      await inputs[2].setValue('newpassword123')

      const form = wrapper.find('form')
      await form.trigger('submit')
      await flushPromises()

      expect(wrapper.text()).toContain('Current password is incorrect')
    })

    it('shows error when API call fails', async () => {
      authStore.changePassword.mockRejectedValue(new Error('API Error'))

      const inputs = wrapper.findAll('input[type="password"]')
      await inputs[0].setValue('currentpass')
      await inputs[1].setValue('newpassword123')
      await inputs[2].setValue('newpassword123')

      const form = wrapper.find('form')
      await form.trigger('submit')
      await flushPromises()

      expect(wrapper.text()).toContain('Failed to change password')
    })
  })

  describe('logout', () => {
    it('renders logout button', () => {
      const logoutButton = wrapper.findAll('button').find(b => b.text().includes('Logout'))
      expect(logoutButton).toBeDefined()
    })
  })

  describe('language selection', () => {
    it('renders language selector', () => {
      const select = wrapper.find('select')
      expect(select.exists()).toBe(true)
    })
  })
})
