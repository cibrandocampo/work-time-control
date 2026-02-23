import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('i18n', () => {
  beforeEach(() => {
    vi.resetModules()
    localStorage.getItem.mockReturnValue(null)
  })

  describe('getDefaultLocale', () => {
    it('uses saved locale from localStorage', async () => {
      localStorage.getItem.mockReturnValue('es')

      const { default: i18n } = await import('./index.js')

      expect(i18n.global.locale.value).toBe('es')
    })

    it('falls back to browser language', async () => {
      localStorage.getItem.mockReturnValue(null)
      Object.defineProperty(navigator, 'language', {
        value: 'pt-BR',
        writable: true
      })

      vi.resetModules()
      const { default: i18n } = await import('./index.js')

      expect(i18n.global.locale.value).toBe('pt')
    })

    it('defaults to English for unsupported language', async () => {
      localStorage.getItem.mockReturnValue(null)
      Object.defineProperty(navigator, 'language', {
        value: 'zh-CN',
        writable: true
      })

      vi.resetModules()
      const { default: i18n } = await import('./index.js')

      expect(i18n.global.locale.value).toBe('en')
    })
  })

  describe('setLocale', () => {
    it('updates locale and saves to localStorage', async () => {
      const { default: i18n, setLocale } = await import('./index.js')

      setLocale('gl')

      expect(i18n.global.locale.value).toBe('gl')
      expect(localStorage.setItem).toHaveBeenCalledWith('locale', 'gl')
    })
  })

  describe('availableLocales', () => {
    it('includes all supported locales', async () => {
      const { availableLocales } = await import('./index.js')

      expect(availableLocales).toHaveLength(4)
      expect(availableLocales.map(l => l.code)).toEqual(['en', 'es', 'pt', 'gl'])
    })

    it('includes locale names', async () => {
      const { availableLocales } = await import('./index.js')

      const names = availableLocales.map(l => l.name)
      expect(names).toContain('English')
      expect(names).toContain('Español')
      expect(names).toContain('Português')
      expect(names).toContain('Galego')
    })
  })

  describe('translations', () => {
    it('has all required translation keys', async () => {
      const { default: i18n } = await import('./index.js')
      const t = i18n.global.t

      // Core keys
      expect(t('app.title')).toBe('Work Time Control')
      expect(t('nav.home')).toBe('Home')
      expect(t('nav.signings')).toBe('Signings')
      expect(t('nav.settings')).toBe('Settings')

      // Home view
      expect(t('home.checkIn')).toBe('Check In')
      expect(t('home.checkOut')).toBe('Check Out')
      expect(t('home.overtime')).toBe('Overtime')
      expect(t('home.remaining')).toBe('Remaining')

      // Login
      expect(t('login.username')).toBe('Username')
      expect(t('login.password')).toBe('Password')

      // Settings - new keys
      expect(t('settings.account')).toBe('Account')
      expect(t('settings.email')).toBe('Email')
      expect(t('settings.fillAllFields')).toBe('Please fill in all fields')
      expect(t('settings.passwordMinLength')).toBe('Password must be at least 8 characters')
      expect(t('settings.passwordIncorrect')).toBe('Current password is incorrect')
      expect(t('settings.passwordFailed')).toBe('Failed to change password')

      // Common
      expect(t('common.error')).toBe('Error')
      expect(t('common.success')).toBe('Success')
    })

    it('supports interpolation', async () => {
      const { default: i18n } = await import('./index.js')
      const t = i18n.global.t

      expect(t('home.youreAt', { location: 'Madrid HQ' })).toBe("You're at Madrid HQ")
      expect(t('integration.syncSuccess', { count: 5 })).toBe('Successfully synced 5 signings')
    })
  })
})
