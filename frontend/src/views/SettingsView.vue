<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { useAuthStore } from '../stores/auth'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Password from 'primevue/password'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import { availableLocales, setLocale } from '../i18n'
import { api } from '../api'

const { t, locale } = useI18n()
const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const authStore = useAuthStore()

// Language
const selectedLocale = computed({
  get: () => availableLocales.find(l => l.code === locale.value),
  set: (val) => {
    setLocale(val.code)
  }
})

// Integration settings
const externalUserId = ref('')
const savingIntegration = ref(false)

onMounted(() => {
  if (authStore.user?.external_user_id) {
    externalUserId.value = authStore.user.external_user_id
  }
})

async function saveIntegrationSettings() {
  savingIntegration.value = true
  try {
    await api.updateProfile({ external_user_id: externalUserId.value })
    await authStore.fetchUser()
    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: t('settings.integrationSaved'),
      life: 3000
    })
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('settings.integrationFailed'),
      life: 3000
    })
  } finally {
    savingIntegration.value = false
  }
}

// Password change
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const changingPassword = ref(false)
const passwordError = ref('')

async function changePassword() {
  passwordError.value = ''

  if (!currentPassword.value || !newPassword.value || !confirmPassword.value) {
    passwordError.value = t('settings.fillAllFields')
    return
  }

  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = t('settings.passwordMismatch')
    return
  }

  if (newPassword.value.length < 8) {
    passwordError.value = t('settings.passwordMinLength')
    return
  }

  changingPassword.value = true
  try {
    const success = await authStore.changePassword(
      currentPassword.value,
      newPassword.value
    )

    if (success) {
      toast.add({
        severity: 'success',
        summary: t('settings.passwordChanged'),
        detail: t('settings.passwordSuccess'),
        life: 3000
      })
      currentPassword.value = ''
      newPassword.value = ''
      confirmPassword.value = ''
    } else {
      passwordError.value = t('settings.passwordIncorrect')
    }
  } catch (err) {
    passwordError.value = t('settings.passwordFailed')
  } finally {
    changingPassword.value = false
  }
}

function confirmLogout() {
  confirm.require({
    message: t('settings.logoutConfirm'),
    header: t('settings.logoutTitle'),
    icon: 'pi pi-sign-out',
    accept: async () => {
      await authStore.logout()
      router.push('/login')
    }
  })
}
</script>

<template>
  <div class="settings-view">
    <!-- Language -->
    <Card>
      <template #title>
        <div class="card-header">
          <i class="pi pi-globe"></i>
          {{ t('settings.language') }}
        </div>
      </template>
      <template #content>
        <Select
          v-model="selectedLocale"
          :options="availableLocales"
          optionLabel="name"
          class="w-full"
        />
      </template>
    </Card>

    <!-- User Info -->
    <Card>
      <template #title>
        <div class="card-header">
          <i class="pi pi-user"></i>
          {{ t('settings.account') }}
        </div>
      </template>
      <template #content>
        <div v-if="authStore.user" class="user-info">
          <div class="info-row">
            <span class="info-label">{{ t('login.username') }}</span>
            <span class="info-value">{{ authStore.user.username }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">{{ t('settings.email') }}</span>
            <span class="info-value">{{ authStore.user.email || '-' }}</span>
          </div>
        </div>
      </template>
    </Card>

    <!-- Integration Settings -->
    <Card>
      <template #title>
        <div class="card-header">
          <i class="pi pi-sync"></i>
          {{ t('settings.integration') }}
        </div>
      </template>
      <template #content>
        <div class="integration-form">
          <div class="field">
            <label for="external-user-id">{{ t('settings.externalUserId') }}</label>
            <InputText
              id="external-user-id"
              v-model="externalUserId"
              :placeholder="t('settings.externalUserIdPlaceholder')"
              class="w-full"
            />
            <small class="field-help">{{ t('settings.externalUserIdHelp') }}</small>
          </div>
          <Button
            :label="t('signings.save')"
            icon="pi pi-check"
            :loading="savingIntegration"
            @click="saveIntegrationSettings"
          />
        </div>
      </template>
    </Card>

    <!-- Change Password -->
    <Card>
      <template #title>
        <div class="card-header">
          <i class="pi pi-lock"></i>
          {{ t('settings.changePassword') }}
        </div>
      </template>
      <template #content>
        <form @submit.prevent="changePassword" class="password-form">
          <Message v-if="passwordError" severity="error" :closable="false">
            {{ passwordError }}
          </Message>

          <div class="field">
            <label for="current-password">{{ t('settings.currentPassword') }}</label>
            <Password
              id="current-password"
              v-model="currentPassword"
              :feedback="false"
              toggleMask
              class="w-full"
              inputClass="w-full"
            />
          </div>

          <div class="field">
            <label for="new-password">{{ t('settings.newPassword') }}</label>
            <Password
              id="new-password"
              v-model="newPassword"
              toggleMask
              class="w-full"
              inputClass="w-full"
            />
          </div>

          <div class="field">
            <label for="confirm-password">{{ t('settings.confirmPassword') }}</label>
            <Password
              id="confirm-password"
              v-model="confirmPassword"
              :feedback="false"
              toggleMask
              class="w-full"
              inputClass="w-full"
            />
          </div>

          <Button
            type="submit"
            :label="t('settings.updatePassword')"
            icon="pi pi-check"
            :loading="changingPassword"
          />
        </form>
      </template>
    </Card>

    <!-- Logout -->
    <Card class="logout-card">
      <template #content>
        <div class="logout-section">
          <div class="logout-info">
            <h3>{{ t('settings.logout') }}</h3>
          </div>
          <Button
            :label="t('settings.logout')"
            icon="pi pi-sign-out"
            severity="danger"
            outlined
            @click="confirmLogout"
          />
        </div>
      </template>
    </Card>
  </div>
</template>

<style scoped>
.settings-view {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  max-width: 600px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
}

.info-row {
  display: flex;
  justify-content: space-between;
  width: 100%;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--p-surface-200);
  gap: 1rem;
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  color: var(--p-text-muted-color);
}

.info-value {
  font-weight: 500;
}

.integration-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field-help {
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

.password-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
}

.w-full {
  width: 100%;
}

.logout-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logout-info h3 {
  margin: 0 0 0.25rem 0;
}

.logout-info p {
  margin: 0;
  color: var(--p-text-muted-color);
}
</style>
