<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Card from 'primevue/card'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import FileUpload from 'primevue/fileupload'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import { api } from '../api'

const { t, locale } = useI18n()
const toast = useToast()
const confirm = useConfirm()

// Date range for search
const dateRange = ref([
  new Date(new Date().setDate(new Date().getDate() - 30)),
  new Date()
])

const loading = ref(false)
const signings = ref([])
const locations = ref([])
const rangeSummary = ref(null)
const activeBreakdown = ref('monthly')

// Edit dialog
const editDialog = ref(false)
const editingSigning = ref(null)
const editForm = ref({
  start_time: null,
  end_time: null,
  location_id: null,
  description: ''
})
const saving = ref(false)

// Import dialog
const importDialog = ref(false)
const importResult = ref(null)
const importing = ref(false)

// Group signings by date
const groupedSignings = computed(() => {
  const groups = {}
  signings.value.forEach(signing => {
    const date = signing.start_time.split('T')[0]
    if (!groups[date]) {
      groups[date] = []
    }
    groups[date].push(signing)
  })

  // Sort dates descending
  const sortedDates = Object.keys(groups).sort((a, b) => b.localeCompare(a))

  return sortedDates.map(date => ({
    date,
    signings: groups[date],
    totalMinutes: groups[date].reduce((sum, s) => sum + (s.duration_minutes || 0), 0)
  }))
})

// Map i18n locale to browser locale
const localeMap = {
  en: 'en-US',
  es: 'es-ES',
  pt: 'pt-PT',
  gl: 'gl-ES'
}

function formatDate(dateStr) {
  const date = new Date(dateStr)
  const browserLocale = localeMap[locale.value] || locale.value
  return date.toLocaleDateString(browserLocale, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

function formatTime(dateTimeStr) {
  if (!dateTimeStr) return '-'
  const date = new Date(dateTimeStr)
  const browserLocale = localeMap[locale.value] || locale.value
  return date.toLocaleTimeString(browserLocale, {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDuration(minutes) {
  if (!minutes) return '-'
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${hours}h ${mins}m`
}

function formatOvertimeMinutes(minutes) {
  const abs = Math.abs(minutes)
  const hours = Math.floor(abs / 60)
  const mins = abs % 60
  if (minutes >= 0) return `+${hours}h ${mins}m`
  return `-${hours}h ${mins}m`
}

const monthNames = {
  en: ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
  es: ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
  pt: ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
  gl: ['', 'Xan', 'Feb', 'Mar', 'Abr', 'Mai', 'Xuñ', 'Xul', 'Ago', 'Set', 'Out', 'Nov', 'Dec']
}

function formatMonthYear(year, month) {
  const names = monthNames[locale.value] || monthNames.en
  return `${names[month]} ${year}`
}

const breakdownOptions = computed(() => [
  { label: t('overtime.monthlyBreakdown'), value: 'monthly' },
  { label: t('overtime.weeklyBreakdown'), value: 'weekly' }
])

const activeBreakdownData = computed(() => {
  if (!rangeSummary.value) return []
  return activeBreakdown.value === 'monthly'
    ? rangeSummary.value.monthly
    : rangeSummary.value.weekly
})

async function loadLocations() {
  locations.value = await api.getLocations()
}

// Format date as YYYY-MM-DD in local timezone
function formatDateLocal(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

async function searchSignings() {
  if (!dateRange.value || dateRange.value.length !== 2) {
    toast.add({
      severity: 'warn',
      summary: t('common.warning'),
      detail: t('signings.selectDateRange'),
      life: 3000
    })
    return
  }

  loading.value = true
  try {
    const startDate = formatDateLocal(dateRange.value[0])
    const endDate = formatDateLocal(dateRange.value[1])

    const [signingsResponse, summary] = await Promise.all([
      api.request(`/signings/?start_date=${startDate}&end_date=${endDate}`),
      api.getRangeSummary(startDate, endDate)
    ])
    if (signingsResponse.ok) {
      signings.value = await signingsResponse.json()
    }
    rangeSummary.value = summary
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('signings.loadFailed'),
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

function openEditDialog(signing) {
  editingSigning.value = signing
  editForm.value = {
    start_time: new Date(signing.start_time),
    end_time: signing.end_time ? new Date(signing.end_time) : null,
    location_id: signing.location?.id || null,
    description: signing.description || ''
  }
  editDialog.value = true
}

async function saveEdit() {
  saving.value = true
  try {
    const data = {
      start_time: editForm.value.start_time.toISOString(),
      description: editForm.value.description
    }

    if (editForm.value.end_time) {
      data.end_time = editForm.value.end_time.toISOString()
    }

    if (editForm.value.location_id) {
      data.location_id = editForm.value.location_id
    }

    await api.updateSigning(editingSigning.value.id, data)

    toast.add({
      severity: 'success',
      summary: t('signings.saved'),
      detail: t('signings.signingUpdated'),
      life: 3000
    })

    editDialog.value = false
    await searchSignings()
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('signings.saveFailed'),
      life: 3000
    })
  } finally {
    saving.value = false
  }
}

function confirmDelete(signing) {
  confirm.require({
    message: t('signings.deleteConfirm'),
    header: t('signings.deleteTitle'),
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await api.deleteSigning(signing.id)
        toast.add({
          severity: 'success',
          summary: t('signings.deleted'),
          detail: t('signings.signingDeleted'),
          life: 3000
        })
        await searchSignings()
      } catch (err) {
        toast.add({
          severity: 'error',
          summary: t('common.error'),
          detail: t('signings.deleteFailed'),
          life: 3000
        })
      }
    }
  })
}

async function exportSignings() {
  if (!dateRange.value || dateRange.value.length !== 2) {
    toast.add({
      severity: 'warn',
      summary: t('common.warning'),
      detail: t('signings.selectDateRange'),
      life: 3000
    })
    return
  }

  try {
    const startDate = formatDateLocal(dateRange.value[0])
    const endDate = formatDateLocal(dateRange.value[1])

    const blob = await api.exportSignings(startDate, endDate)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `signings_${startDate}_${endDate}.csv`
    a.click()
    URL.revokeObjectURL(url)

    toast.add({
      severity: 'success',
      summary: t('signings.exported'),
      detail: t('signings.csvDownloaded'),
      life: 3000
    })
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('signings.exportFailed'),
      life: 3000
    })
  }
}

function openImportDialog() {
  importResult.value = null
  importDialog.value = true
}

async function handleImport(event) {
  const file = event.files[0]
  if (!file) return

  importing.value = true
  try {
    const result = await api.importSignings(file)
    importResult.value = result

    if (result.imported > 0) {
      toast.add({
        severity: 'success',
        summary: t('signings.imported'),
        detail: t('signings.signingsImported', { count: result.imported }),
        life: 3000
      })
      await searchSignings()
    }
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('signings.importFailed'),
      life: 3000
    })
  } finally {
    importing.value = false
  }
}

onMounted(() => {
  loadLocations()
  searchSignings()
})
</script>

<template>
  <div class="signings-view">
    <!-- Search Card -->
    <Card class="search-card">
      <template #title>{{ t('signings.search') }}</template>
      <template #content>
        <div class="search-form">
          <div class="date-range-picker">
            <label>{{ t('signings.dateRange') }}</label>
            <DatePicker
              v-model="dateRange"
              selectionMode="range"
              dateFormat="yy-mm-dd"
              showIcon
              showButtonBar
              class="w-full"
            />
          </div>

          <div class="search-actions">
            <Button
              :label="t('signings.searchBtn')"
              icon="pi pi-search"
              @click="searchSignings"
              :loading="loading"
            />
            <Button
              :label="t('signings.exportCsv')"
              icon="pi pi-download"
              severity="secondary"
              @click="exportSignings"
            />
            <Button
              :label="t('signings.importCsv')"
              icon="pi pi-upload"
              severity="secondary"
              @click="openImportDialog"
            />
          </div>
        </div>
      </template>
    </Card>

    <!-- Overtime Summary -->
    <Card v-if="rangeSummary && !loading" class="overtime-card">
      <template #title>{{ t('overtime.summary') }}</template>
      <template #content>
        <div class="overtime-totals">
          <div class="overtime-total-item">
            <span class="overtime-total-label">{{ t('overtime.worked') }}</span>
            <span class="overtime-total-value">{{ formatDuration(rangeSummary.total_worked_minutes) }}</span>
          </div>
          <div class="overtime-total-item">
            <span class="overtime-total-label">{{ t('overtime.expected') }}</span>
            <span class="overtime-total-value">{{ formatDuration(rangeSummary.total_expected_minutes) }}</span>
          </div>
          <div class="overtime-total-item">
            <span class="overtime-total-label">{{ t('overtime.overtime') }}</span>
            <span class="overtime-total-value" :class="rangeSummary.overtime_minutes >= 0 ? 'positive' : 'negative'">
              {{ formatOvertimeMinutes(rangeSummary.overtime_minutes) }}
            </span>
          </div>
        </div>

        <div class="breakdown-toggle">
          <SelectButton
            v-model="activeBreakdown"
            :options="breakdownOptions"
            optionLabel="label"
            optionValue="value"
          />
        </div>

        <div v-if="activeBreakdownData.length > 0" class="breakdown-table">
          <div class="breakdown-header">
            <span class="breakdown-col period-col">{{ t('overtime.period') }}</span>
            <span class="breakdown-col">{{ t('overtime.worked') }}</span>
            <span class="breakdown-col">{{ t('overtime.expected') }}</span>
            <span class="breakdown-col">{{ t('overtime.overtime') }}</span>
          </div>
          <div
            v-for="(row, idx) in activeBreakdownData"
            :key="idx"
            class="breakdown-row"
          >
            <span class="breakdown-col period-col">
              <template v-if="activeBreakdown === 'monthly'">
                {{ formatMonthYear(row.year, row.month) }}
              </template>
              <template v-else>
                {{ t('overtime.week', { number: row.week }) }} {{ row.year }}
              </template>
            </span>
            <span class="breakdown-col">{{ formatDuration(row.worked_minutes) }}</span>
            <span class="breakdown-col">{{ formatDuration(row.expected_minutes) }}</span>
            <span class="breakdown-col" :class="row.overtime_minutes >= 0 ? 'positive' : 'negative'">
              {{ formatOvertimeMinutes(row.overtime_minutes) }}
            </span>
          </div>
        </div>
        <div v-else class="no-breakdown-data">
          <Message severity="info" :closable="false">{{ t('overtime.noData') }}</Message>
        </div>
      </template>
    </Card>

    <!-- Results -->
    <div v-if="loading" class="loading-container">
      <ProgressSpinner />
    </div>

    <div v-else-if="groupedSignings.length === 0" class="no-results">
      <Message severity="info" :closable="false">
        {{ t('signings.noResults') }}
      </Message>
    </div>

    <div v-else class="signings-list">
      <Card v-for="group in groupedSignings" :key="group.date" class="day-card">
        <template #title>
          <div class="day-header">
            <span>{{ formatDate(group.date) }}</span>
            <span class="day-total">{{ formatDuration(group.totalMinutes) }}</span>
          </div>
        </template>
        <template #content>
          <div class="signing-items">
            <div
              v-for="signing in group.signings"
              :key="signing.id"
              class="signing-item"
            >
              <div class="signing-times">
                <span class="time-badge">
                  <i class="pi pi-sign-in"></i>
                  {{ formatTime(signing.start_time) }}
                </span>
                <span class="time-separator">→</span>
                <span class="time-badge">
                  <i class="pi pi-sign-out"></i>
                  {{ formatTime(signing.end_time) }}
                </span>
                <span class="duration">
                  {{ formatDuration(signing.duration_minutes) }}
                </span>
              </div>

              <div class="signing-details">
                <span v-if="signing.location" class="location">
                  <i class="pi pi-map-marker"></i>
                  {{ signing.location.name }}
                </span>
                <span v-if="signing.description" class="description">
                  {{ signing.description }}
                </span>
              </div>

              <div class="signing-actions">
                <Button
                  icon="pi pi-pencil"
                  severity="secondary"
                  text
                  rounded
                  @click="openEditDialog(signing)"
                />
                <Button
                  icon="pi pi-trash"
                  severity="danger"
                  text
                  rounded
                  @click="confirmDelete(signing)"
                />
              </div>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Edit Dialog -->
    <Dialog
      v-model:visible="editDialog"
      :header="t('signings.editSigning')"
      modal
      :style="{ width: '450px' }"
    >
      <div class="edit-form">
        <div class="field">
          <label>{{ t('signings.startTime') }}</label>
          <DatePicker
            v-model="editForm.start_time"
            showTime
            hourFormat="24"
            dateFormat="yy-mm-dd"
            class="w-full"
          />
        </div>

        <div class="field">
          <label>{{ t('signings.endTime') }}</label>
          <DatePicker
            v-model="editForm.end_time"
            showTime
            hourFormat="24"
            dateFormat="yy-mm-dd"
            class="w-full"
          />
        </div>

        <div class="field">
          <label>{{ t('signings.location') }}</label>
          <Select
            v-model="editForm.location_id"
            :options="locations"
            optionLabel="name"
            optionValue="id"
            :placeholder="t('common.selectPlaceholder', { item: t('signings.location').toLowerCase() })"
            class="w-full"
          />
        </div>

        <div class="field">
          <label>{{ t('signings.description') }}</label>
          <Textarea
            v-model="editForm.description"
            rows="3"
            class="w-full"
          />
        </div>
      </div>

      <template #footer>
        <Button
          :label="t('signings.cancel')"
          severity="secondary"
          @click="editDialog = false"
        />
        <Button
          :label="t('signings.save')"
          icon="pi pi-check"
          @click="saveEdit"
          :loading="saving"
        />
      </template>
    </Dialog>

    <!-- Import Dialog -->
    <Dialog
      v-model:visible="importDialog"
      :header="t('signings.importTitle')"
      modal
      :style="{ width: '500px' }"
    >
      <div class="import-content">
        <p class="import-info">
          {{ t('signings.importInfo', { columns: 'start_time, end_time, location_id, description' }) }}
        </p>

        <FileUpload
          mode="basic"
          accept=".csv"
          :auto="true"
          :chooseLabel="t('signings.selectFile')"
          :customUpload="true"
          @uploader="handleImport"
          :disabled="importing"
        />

        <div v-if="importing" class="import-loading">
          <ProgressSpinner style="width: 30px; height: 30px" />
          <span>{{ t('signings.importing') }}</span>
        </div>

        <div v-if="importResult" class="import-result">
          <Message
            v-if="importResult.imported > 0"
            severity="success"
            :closable="false"
          >
            {{ t('signings.signingsImported', { count: importResult.imported }) }}
          </Message>

          <div v-if="importResult.errors?.length > 0" class="import-errors">
            <Message severity="error" :closable="false">
              {{ t('signings.errorsFound', { count: importResult.errors.length }) }}
            </Message>
            <ul>
              <li v-for="error in importResult.errors" :key="error.row">
                {{ t('signings.row') }} {{ error.row }}: {{ error.error }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <template #footer>
        <Button
          :label="t('signings.close')"
          @click="importDialog = false"
        />
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
.signings-view {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.search-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.date-range-picker {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.search-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.loading-container {
  display: flex;
  justify-content: center;
  padding: 3rem;
}

.no-results {
  text-align: center;
}

.signings-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.day-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.day-total {
  font-size: 1rem;
  color: var(--p-primary-color);
  font-weight: bold;
}

.signing-items {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.signing-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  background: var(--p-surface-100);
  border-radius: 8px;
  flex-wrap: wrap;
}

.signing-times {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.time-badge {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-weight: 500;
}

.time-separator {
  color: var(--p-text-muted-color);
}

.duration {
  color: var(--p-primary-color);
  font-weight: bold;
  margin-left: 0.5rem;
}

.signing-details {
  flex: 1;
  display: flex;
  gap: 1rem;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

.location, .description {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.signing-actions {
  display: flex;
  gap: 0.25rem;
}

.edit-form {
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

.import-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.import-info {
  color: var(--p-text-muted-color);
}

.import-info code {
  background: var(--p-surface-200);
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
}

.import-loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.import-errors ul {
  margin-top: 0.5rem;
  padding-left: 1.5rem;
  color: var(--p-red-500);
}

.overtime-totals {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  text-align: center;
  margin-bottom: 1.5rem;
}

.overtime-total-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.overtime-total-label {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
}

.overtime-total-value {
  font-size: 1.5rem;
  font-weight: bold;
}

.overtime-total-value.positive {
  color: var(--p-green-500);
}

.overtime-total-value.negative {
  color: var(--p-red-500);
}

.breakdown-toggle {
  display: flex;
  justify-content: center;
  margin-bottom: 1rem;
}

.breakdown-table {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.breakdown-header {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 0.5rem;
  padding: 0.75rem;
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  border-bottom: 2px solid var(--p-surface-200);
}

.breakdown-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 0.5rem;
  padding: 0.75rem;
  border-bottom: 1px solid var(--p-surface-100);
}

.breakdown-row:last-child {
  border-bottom: none;
}

.breakdown-col {
  font-size: 0.9rem;
}

.breakdown-col.positive {
  color: var(--p-green-500);
  font-weight: 600;
}

.breakdown-col.negative {
  color: var(--p-red-500);
  font-weight: 600;
}

.period-col {
  font-weight: 500;
}

.no-breakdown-data {
  text-align: center;
}

@media (max-width: 768px) {
  .signing-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .signing-actions {
    align-self: flex-end;
  }

  .overtime-totals {
    grid-template-columns: 1fr 1fr;
  }

  .overtime-total-item:last-child {
    grid-column: 1 / -1;
  }

  .breakdown-header,
  .breakdown-row {
    grid-template-columns: 1.5fr 1fr 1fr 1fr;
    font-size: 0.8rem;
  }
}
</style>
