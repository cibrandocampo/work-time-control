<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import { api } from '../api'

const { t } = useI18n()
const toast = useToast()

const token = ref('')
const apiKey = ref('')
const dateRange = ref([
  new Date(new Date().setDate(new Date().getDate() - 30)),
  new Date()
])

const syncing = ref(false)
const syncResult = ref(null)

// Format date as YYYY-MM-DD in local timezone
function formatDateLocal(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

async function syncData() {
  if (!token.value.trim() || !apiKey.value.trim()) {
    toast.add({
      severity: 'warn',
      summary: t('common.warning'),
      detail: t('integration.enterCredentials'),
      life: 3000
    })
    return
  }

  if (!dateRange.value || dateRange.value.length !== 2) {
    toast.add({
      severity: 'warn',
      summary: t('common.warning'),
      detail: t('integration.selectDateRange'),
      life: 3000
    })
    return
  }

  syncing.value = true
  syncResult.value = null

  try {
    const startDate = formatDateLocal(dateRange.value[0])
    const endDate = formatDateLocal(dateRange.value[1])

    const response = await api.request('/integrations/sync/', {
      method: 'POST',
      body: JSON.stringify({
        token: token.value,
        api_key: apiKey.value,
        start_date: startDate,
        end_date: endDate
      })
    })

    const result = await response.json()

    if (response.ok) {
      syncResult.value = {
        success: true,
        message: t('integration.syncSuccess', { count: result.imported || 0 })
      }
      toast.add({
        severity: 'success',
        summary: t('integration.syncComplete'),
        detail: syncResult.value.message,
        life: 5000
      })
    } else {
      syncResult.value = {
        success: false,
        message: result.error || t('integration.syncFailed')
      }
    }
  } catch (err) {
    syncResult.value = {
      success: false,
      message: t('integration.connectionError')
    }
  } finally {
    syncing.value = false
  }
}
</script>

<template>
  <div class="integration-view">
    <Card>
      <template #title>
        <div class="card-header">
          <i class="pi pi-sync"></i>
          {{ t('integration.title') }}
        </div>
      </template>
      <template #content>
        <div class="integration-form">
          <Message severity="info" :closable="false">
            {{ t('integration.description') }}
          </Message>

          <div class="field">
            <label for="token">{{ t('integration.apiToken') }}</label>
            <InputText
              id="token"
              v-model="token"
              type="password"
              :placeholder="t('integration.tokenPlaceholder')"
              class="w-full"
            />
            <small class="field-help">
              {{ t('integration.tokenHelp') }}
            </small>
          </div>

          <div class="field">
            <label for="apiKey">{{ t('integration.apiKey') }}</label>
            <InputText
              id="apiKey"
              v-model="apiKey"
              type="password"
              :placeholder="t('integration.apiKeyPlaceholder')"
              class="w-full"
            />
            <small class="field-help">
              {{ t('integration.apiKeyHelp') }}
            </small>
          </div>

          <div class="field">
            <label>{{ t('integration.dateRange') }}</label>
            <DatePicker
              v-model="dateRange"
              selectionMode="range"
              dateFormat="yy-mm-dd"
              showIcon
              showButtonBar
              class="w-full"
            />
          </div>

          <div class="sync-actions">
            <Button
              :label="t('integration.syncNow')"
              icon="pi pi-sync"
              :loading="syncing"
              @click="syncData"
              size="large"
            />
          </div>

          <div v-if="syncing" class="sync-progress">
            <ProgressSpinner style="width: 40px; height: 40px" />
            <p>{{ t('integration.syncing') }}</p>
            <small>{{ t('integration.syncingHelp') }}</small>
          </div>

          <div v-if="syncResult" class="sync-result">
            <Message
              :severity="syncResult.success ? 'success' : 'error'"
              :closable="false"
            >
              {{ syncResult.message }}
            </Message>
          </div>
        </div>
      </template>
    </Card>

    <Card class="help-card">
      <template #title>
        <div class="card-header">
          <i class="pi pi-question-circle"></i>
          {{ t('integration.helpTitle') }}
        </div>
      </template>
      <template #content>
        <ol class="help-steps">
          <li>{{ t('integration.helpStep1') }}</li>
          <li>{{ t('integration.helpStep2') }}</li>
          <li>{{ t('integration.helpStep3') }}</li>
          <li>{{ t('integration.helpStep4') }}</li>
          <li>{{ t('integration.helpStep5') }}</li>
        </ol>
        <Message severity="warn" :closable="false">
          {{ t('integration.securityWarning') }}
        </Message>
      </template>
    </Card>
  </div>
</template>

<style scoped>
.integration-view {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  max-width: 700px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.integration-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
}

.field-help {
  color: var(--p-text-muted-color);
}

.w-full {
  width: 100%;
}

.sync-actions {
  display: flex;
  justify-content: center;
  padding: 1rem 0;
}

.sync-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  text-align: center;
}

.sync-progress p {
  font-weight: 500;
  margin: 0;
}

.sync-progress small {
  color: var(--p-text-muted-color);
}

.sync-result {
  margin-top: 1rem;
}

.help-card {
  background: var(--p-surface-50);
}

.help-steps {
  padding-left: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.help-steps li {
  color: var(--p-text-color);
}
</style>
