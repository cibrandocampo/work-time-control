import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick } from 'vue'
import LoginView from './LoginView.vue'
import { mountWithPlugins } from '../test/test-utils.js'
import { useAuthStore } from '../stores/auth.js'

const mockPush = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockPush
  })
}))

describe('LoginView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders login form', () => {
    const wrapper = mountWithPlugins(LoginView)

    expect(wrapper.find('input[id="username"]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
    expect(wrapper.find('button').exists()).toBe(true)
  })

  it('shows app title', () => {
    const wrapper = mountWithPlugins(LoginView)

    expect(wrapper.text()).toContain('Work Time Control')
  })

  it('shows error when submitting empty form', async () => {
    const wrapper = mountWithPlugins(LoginView)

    await wrapper.find('form').trigger('submit')
    await nextTick()

    expect(wrapper.find('.p-message').exists()).toBe(true)
    expect(wrapper.text()).toContain('Invalid credentials')
  })

  it('calls login with credentials', async () => {
    const wrapper = mountWithPlugins(LoginView)
    const authStore = useAuthStore()
    authStore.login = vi.fn().mockResolvedValue({ success: true })

    await wrapper.find('input[id="username"]').setValue('testuser')
    await wrapper.find('input[type="password"]').setValue('password123')
    await wrapper.find('form').trigger('submit')

    expect(authStore.login).toHaveBeenCalledWith('testuser', 'password123')
  })

  it('redirects to home on successful login', async () => {
    const wrapper = mountWithPlugins(LoginView)
    const authStore = useAuthStore()
    authStore.login = vi.fn().mockResolvedValue({ success: true })

    await wrapper.find('input[id="username"]').setValue('testuser')
    await wrapper.find('input[type="password"]').setValue('password123')
    await wrapper.find('form').trigger('submit')
    await nextTick()

    expect(mockPush).toHaveBeenCalledWith('/')
  })

  it('shows error on failed login', async () => {
    const wrapper = mountWithPlugins(LoginView)
    const authStore = useAuthStore()
    authStore.login = vi.fn().mockResolvedValue({ success: false, error: 'Invalid credentials' })

    await wrapper.find('input[id="username"]').setValue('testuser')
    await wrapper.find('input[type="password"]').setValue('wrongpass')
    await wrapper.find('form').trigger('submit')
    await nextTick()

    expect(wrapper.find('.p-message').exists()).toBe(true)
    expect(mockPush).not.toHaveBeenCalled()
  })

  it('does not redirect on failed login', async () => {
    const wrapper = mountWithPlugins(LoginView)
    const authStore = useAuthStore()
    authStore.login = vi.fn().mockResolvedValue({ success: false })

    await wrapper.find('input[id="username"]').setValue('user')
    await wrapper.find('input[type="password"]').setValue('wrong')
    await wrapper.find('form').trigger('submit')
    await nextTick()

    expect(mockPush).not.toHaveBeenCalled()
  })
})
