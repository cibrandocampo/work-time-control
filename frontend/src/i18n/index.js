import { createI18n } from 'vue-i18n'

import en from './locales/en.json'
import es from './locales/es.json'
import pt from './locales/pt.json'
import gl from './locales/gl.json'

const messages = { en, es, pt, gl }

// Get saved language or detect from browser
function getDefaultLocale() {
  const saved = localStorage.getItem('locale')
  if (saved && messages[saved]) {
    return saved
  }

  // Detect from browser
  const browserLang = navigator.language.split('-')[0]
  if (messages[browserLang]) {
    return browserLang
  }

  return 'en'
}

const i18n = createI18n({
  legacy: false, // Use Composition API
  locale: getDefaultLocale(),
  fallbackLocale: 'en',
  messages
})

export const availableLocales = [
  { code: 'en', name: 'English' },
  { code: 'es', name: 'Español' },
  { code: 'pt', name: 'Português' },
  { code: 'gl', name: 'Galego' }
]

export function setLocale(locale) {
  i18n.global.locale.value = locale
  localStorage.setItem('locale', locale)
}

export default i18n
