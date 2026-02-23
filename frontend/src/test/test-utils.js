import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import en from '../i18n/locales/en.json'

export function createTestI18n() {
  return createI18n({
    legacy: false,
    locale: 'en',
    fallbackLocale: 'en',
    messages: { en }
  })
}

export function mountWithPlugins(component, options = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)

  const i18n = createTestI18n()

  return mount(component, {
    global: {
      plugins: [pinia, i18n, PrimeVue, ToastService, ConfirmationService],
      stubs: {
        Card: {
          template: '<div class="p-card"><slot name="title" /><slot name="content" /></div>'
        },
        Button: {
          template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot />{{ label }}</button>',
          props: ['label', 'disabled', 'loading', 'icon', 'size', 'severity']
        },
        InputText: {
          template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
          props: ['modelValue', 'placeholder']
        },
        Password: {
          template: '<input type="password" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
          props: ['modelValue', 'placeholder', 'feedback', 'toggleMask']
        },
        Message: {
          template: '<div class="p-message" :class="severity"><slot /></div>',
          props: ['severity', 'closable']
        },
        ProgressSpinner: {
          template: '<div class="p-progress-spinner">Loading...</div>'
        },
        Select: {
          template: '<select :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="opt in options" :key="opt.id" :value="opt">{{ opt.name }}</option></select>',
          props: ['modelValue', 'options', 'optionLabel', 'placeholder']
        },
        DatePicker: {
          template: '<input type="text" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
          props: ['modelValue', 'selectionMode', 'dateFormat', 'showIcon', 'showButtonBar']
        },
        Dialog: {
          template: '<div v-if="visible" class="p-dialog"><slot /></div>',
          props: ['visible', 'header', 'modal']
        },
        DataTable: {
          template: '<table><slot /></table>',
          props: ['value', 'paginator', 'rows']
        },
        Column: {
          template: '<td><slot /></td>',
          props: ['field', 'header', 'sortable']
        },
        Dropdown: {
          template: '<select :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"></select>',
          props: ['modelValue', 'options', 'optionLabel']
        },
        FileUpload: {
          template: '<input type="file" @change="$emit(\'uploader\', { files: $event.target.files })" />',
          props: ['mode', 'accept', 'customUpload', 'chooseLabel', 'disabled', 'auto']
        },
        Textarea: {
          template: '<textarea :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
          props: ['modelValue', 'rows']
        },
        ConfirmDialog: {
          template: '<div class="p-confirm-dialog"></div>'
        },
        Toast: {
          template: '<div class="p-toast"></div>'
        }
      },
      ...options.global
    },
    ...options
  })
}
