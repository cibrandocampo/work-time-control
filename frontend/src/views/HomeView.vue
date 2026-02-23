<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import Select from 'primevue/select'
import Message from 'primevue/message'
import { api } from '../api'

const { t } = useI18n()
const toast = useToast()

const loading = ref(true)
const activeSigning = ref(null)
const daySummary = ref(null)
const todaySignings = ref([])
const locations = ref([])
const selectedLocation = ref(null)
const actionLoading = ref(false)
const locationDetected = ref(false)
const userCoords = ref(null)
const weekMonthSummary = ref(null)
let timerInterval = null

// Distance threshold in meters to consider "at" a location
const LOCATION_THRESHOLD_METERS = 500

// Haversine formula to calculate distance between two coordinates
function calculateDistance(lat1, lon1, lat2, lon2) {
  const R = 6371000 // Earth's radius in meters
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLon = (lon2 - lon1) * Math.PI / 180
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

// Find nearest location or default to remote
function findBestLocation(userLat, userLon, locs) {
  let nearestLocation = null
  let nearestDistance = Infinity

  for (const loc of locs) {
    const distance = calculateDistance(
      userLat, userLon,
      parseFloat(loc.latitude), parseFloat(loc.longitude)
    )
    if (distance < nearestDistance) {
      nearestDistance = distance
      nearestLocation = loc
    }
  }

  // If within threshold, return that location
  if (nearestDistance <= LOCATION_THRESHOLD_METERS) {
    return { location: nearestLocation, distance: nearestDistance, isNearby: true }
  }

  // Otherwise, find a "Remote" location or return the first one
  const remoteLocation = locs.find(loc =>
    loc.name.toLowerCase().includes('remote') ||
    loc.name.toLowerCase().includes('remoto')
  )

  return {
    location: remoteLocation || locs[0],
    distance: nearestDistance,
    isNearby: false
  }
}

// Detect user location via GPS
async function detectUserLocation() {
  if (!navigator.geolocation) {
    return null
  }

  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude
        })
      },
      () => resolve(null),
      { enableHighAccuracy: true, timeout: 5000 }
    )
  })
}

const isWorking = computed(() => !!activeSigning.value)

// Minutes from active signing (real-time)
const currentSigningMinutes = computed(() => {
  if (!activeSigning.value) return 0
  const start = new Date(activeSigning.value.start_time)
  const diffMs = currentTime.value - start
  return Math.floor(diffMs / (1000 * 60))
})

// Total worked = completed signings + current active signing
const totalWorkedMinutes = computed(() => {
  const completedMinutes = daySummary.value?.total_worked_minutes || 0
  return completedMinutes + currentSigningMinutes.value
})

const expectedMinutes = computed(() => {
  return daySummary.value?.expected_minutes || 480
})

// Dynamic overtime calculation
const overtimeMinutes = computed(() => {
  return totalWorkedMinutes.value - expectedMinutes.value
})

const workedTimeFormatted = computed(() => {
  const minutes = totalWorkedMinutes.value
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${hours}h ${mins}m`
})

const expectedTimeFormatted = computed(() => {
  const minutes = expectedMinutes.value
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${hours}h ${mins}m`
})

// Label changes based on positive/negative
const overtimeLabel = computed(() => {
  return overtimeMinutes.value >= 0 ? t('home.overtime') : t('home.remaining')
})

const overtimeFormatted = computed(() => {
  const minutes = overtimeMinutes.value
  const absMinutes = Math.abs(minutes)
  const hours = Math.floor(absMinutes / 60)
  const mins = absMinutes % 60
  // Show + only for positive overtime, no sign for remaining
  if (minutes >= 0) {
    return `+${hours}h ${mins}m`
  }
  return `${hours}h ${mins}m`
})

const overtimeClass = computed(() => {
  return overtimeMinutes.value >= 0 ? 'positive' : 'negative'
})

const currentTime = ref(new Date())

const currentSigningDuration = computed(() => {
  if (!activeSigning.value) return null
  const start = new Date(activeSigning.value.start_time)
  const diffMs = currentTime.value - start
  const hours = Math.floor(diffMs / (1000 * 60 * 60))
  const mins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))
  const secs = Math.floor((diffMs % (1000 * 60)) / 1000)
  return `${hours}h ${mins}m ${secs}s`
})

function formatTime(dateTimeStr) {
  if (!dateTimeStr) return '-'
  const date = new Date(dateTimeStr)
  return date.toLocaleTimeString('en-US', {
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

// Format date as YYYY-MM-DD in local timezone
function formatDateLocal(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function getCurrentMonthRange() {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), 1)
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  return { start: formatDateLocal(start), end: formatDateLocal(end) }
}

function getISOWeek(d) {
  const date = new Date(d.getTime())
  date.setHours(0, 0, 0, 0)
  date.setDate(date.getDate() + 3 - ((date.getDay() + 6) % 7))
  const week1 = new Date(date.getFullYear(), 0, 4)
  return 1 + Math.round(((date - week1) / 86400000 - 3 + ((week1.getDay() + 6) % 7)) / 7)
}

function formatOvertimeMinutes(minutes) {
  const abs = Math.abs(minutes)
  const hours = Math.floor(abs / 60)
  const mins = abs % 60
  if (minutes >= 0) return `+${hours}h ${mins}m`
  return `-${hours}h ${mins}m`
}

const currentWeekData = computed(() => {
  if (!weekMonthSummary.value) return null
  const now = new Date()
  const isoYear = now.getFullYear()
  const isoWeek = getISOWeek(now)
  return weekMonthSummary.value.weekly?.find(
    w => w.year === isoYear && w.week === isoWeek
  ) || { worked_minutes: 0, expected_minutes: 0, overtime_minutes: 0 }
})

const currentMonthData = computed(() => {
  if (!weekMonthSummary.value) return null
  const now = new Date()
  return weekMonthSummary.value.monthly?.find(
    m => m.year === now.getFullYear() && m.month === now.getMonth() + 1
  ) || { worked_minutes: 0, expected_minutes: 0, overtime_minutes: 0 }
})

async function loadData() {
  loading.value = true
  try {
    const today = formatDateLocal(new Date())
    const monthRange = getCurrentMonthRange()
    const [active, summary, locs, signings, rangeSummary] = await Promise.all([
      api.getActiveSigning(),
      api.getDaySummary(),
      api.getLocations(),
      api.getSignings({ start_date: today, end_date: today }),
      api.getRangeSummary(monthRange.start, monthRange.end)
    ])
    activeSigning.value = active
    daySummary.value = summary
    locations.value = locs
    todaySignings.value = signings
    weekMonthSummary.value = rangeSummary

    // Auto-detect location based on GPS
    if (locs.length > 0 && !selectedLocation.value) {
      const coords = await detectUserLocation()
      if (coords) {
        userCoords.value = coords
        const result = findBestLocation(coords.latitude, coords.longitude, locs)
        selectedLocation.value = result.location
        locationDetected.value = true

        if (result.isNearby) {
          toast.add({
            severity: 'info',
            summary: t('home.locationDetected'),
            detail: t('home.youreAt', { location: result.location.name }),
            life: 3000
          })
        } else {
          toast.add({
            severity: 'info',
            summary: t('home.remoteLocation'),
            detail: t('home.notNearOffice', { location: result.location.name }),
            life: 3000
          })
        }
      } else {
        // Fallback to first location if GPS not available
        selectedLocation.value = locs[0]
      }
    }
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('common.error'),
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

async function handleCheckIn() {
  if (actionLoading.value) return
  actionLoading.value = true
  try {
    const data = {
      start_time: new Date().toISOString()
    }
    if (selectedLocation.value) {
      data.location_id = selectedLocation.value.id
    }
    await api.createSigning(data)
    toast.add({
      severity: 'success',
      summary: t('home.checkedIn'),
      detail: t('home.productiveDay'),
      life: 3000
    })
    await loadData()
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('common.error'),
      life: 3000
    })
  } finally {
    actionLoading.value = false
  }
}

async function handleCheckOut() {
  if (actionLoading.value) return
  actionLoading.value = true
  try {
    await api.checkoutSigning(activeSigning.value.id)
    toast.add({
      severity: 'success',
      summary: t('home.checkedOut'),
      detail: t('home.sessionEnded'),
      life: 3000
    })
    await loadData()
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('common.error'),
      life: 3000
    })
  } finally {
    actionLoading.value = false
  }
}

onMounted(() => {
  loadData()
  timerInterval = setInterval(() => {
    currentTime.value = new Date()
  }, 1000)
})

onUnmounted(() => {
  if (timerInterval) {
    clearInterval(timerInterval)
  }
})
</script>

<template>
  <div class="home-view">
    <div v-if="loading" class="loading-container">
      <ProgressSpinner />
    </div>

    <template v-else>
      <!-- Check In/Out Card -->
      <Card class="action-card">
        <template #content>
          <div class="action-content">
            <div v-if="!isWorking" class="check-in-section">
              <h2>{{ t('home.readyToStart') }}</h2>
              <p>{{ t('home.selectLocation') }}</p>

              <Message v-if="!locationDetected" severity="info" :closable="false" class="gps-hint">
                <i class="pi pi-map-marker"></i> {{ t('home.gpsHint') }}
              </Message>

              <div class="check-in-controls">
                <Select
                  v-if="locations.length > 0"
                  v-model="selectedLocation"
                  :options="locations"
                  optionLabel="name"
                  :placeholder="t('common.selectPlaceholder', { item: t('signings.location') })"
                  class="location-select"
                />

                <Button
                  :label="t('home.checkIn')"
                  icon="pi pi-sign-in"
                  size="large"
                  :loading="actionLoading"
                  :disabled="actionLoading"
                  @click="handleCheckIn"
                  class="action-button"
                />
              </div>
            </div>

            <div v-else class="check-out-section">
              <h2>{{ t('home.currentlyWorking') }}</h2>
              <p class="current-duration">
                <i class="pi pi-clock"></i>
                {{ currentSigningDuration }}
              </p>
              <p v-if="activeSigning.location" class="current-location">
                <i class="pi pi-map-marker"></i>
                {{ activeSigning.location.name }}
              </p>

              <Button
                :label="t('home.checkOut')"
                icon="pi pi-sign-out"
                size="large"
                severity="secondary"
                :loading="actionLoading"
                @click="handleCheckOut"
                class="action-button"
              />
            </div>
          </div>
        </template>
      </Card>

      <!-- Day Summary Card -->
      <Card class="summary-card">
        <template #title>{{ t('home.todaySummary') }}</template>
        <template #content>
          <div class="summary-grid">
            <div class="summary-item">
              <span class="summary-label">{{ t('home.worked') }}</span>
              <span class="summary-value">{{ workedTimeFormatted }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">{{ t('home.expected') }}</span>
              <span class="summary-value">{{ expectedTimeFormatted }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">{{ overtimeLabel }}</span>
              <span class="summary-value" :class="overtimeClass">
                {{ overtimeFormatted }}
              </span>
            </div>
          </div>
        </template>
      </Card>

      <!-- Week / Month Summary Card -->
      <Card v-if="weekMonthSummary" class="week-month-card">
        <template #title>{{ t('home.weekSummary') }} / {{ t('home.monthSummary') }}</template>
        <template #content>
          <div class="week-month-grid">
            <div class="wm-column">
              <h3 class="wm-title">{{ t('home.weekSummary') }}</h3>
              <div class="wm-row">
                <span class="wm-label">{{ t('home.worked') }}</span>
                <span class="wm-value">{{ formatDuration(currentWeekData?.worked_minutes || 0) }}</span>
              </div>
              <div class="wm-row">
                <span class="wm-label">{{ t('home.expected') }}</span>
                <span class="wm-value">{{ formatDuration(currentWeekData?.expected_minutes || 0) }}</span>
              </div>
              <div class="wm-row">
                <span class="wm-label">
                  {{ (currentWeekData?.overtime_minutes || 0) >= 0 ? t('home.overtime') : t('home.pending') }}
                </span>
                <span class="wm-value" :class="(currentWeekData?.overtime_minutes || 0) >= 0 ? 'positive' : 'negative'">
                  {{ formatOvertimeMinutes(currentWeekData?.overtime_minutes || 0) }}
                </span>
              </div>
            </div>
            <div class="wm-column">
              <h3 class="wm-title">{{ t('home.monthSummary') }}</h3>
              <div class="wm-row">
                <span class="wm-label">{{ t('home.worked') }}</span>
                <span class="wm-value">{{ formatDuration(currentMonthData?.worked_minutes || 0) }}</span>
              </div>
              <div class="wm-row">
                <span class="wm-label">{{ t('home.expected') }}</span>
                <span class="wm-value">{{ formatDuration(currentMonthData?.expected_minutes || 0) }}</span>
              </div>
              <div class="wm-row">
                <span class="wm-label">
                  {{ (currentMonthData?.overtime_minutes || 0) >= 0 ? t('home.overtime') : t('home.pending') }}
                </span>
                <span class="wm-value" :class="(currentMonthData?.overtime_minutes || 0) >= 0 ? 'positive' : 'negative'">
                  {{ formatOvertimeMinutes(currentMonthData?.overtime_minutes || 0) }}
                </span>
              </div>
            </div>
          </div>
        </template>
      </Card>

      <!-- Today's Signings -->
      <Card v-if="todaySignings.length > 0" class="signings-card">
        <template #title>{{ t('home.todaySignings') }}</template>
        <template #content>
          <div class="signings-list">
            <div
              v-for="signing in todaySignings"
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
              </div>
              <div class="signing-duration">
                {{ formatDuration(signing.duration_minutes) }}
              </div>
              <div v-if="signing.location" class="signing-location">
                <i class="pi pi-map-marker"></i>
                {{ signing.location.name }}
              </div>
            </div>
          </div>
        </template>
      </Card>
    </template>
  </div>
</template>

<style scoped>
.home-view {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  max-width: 600px;
  margin: 0 auto;
}

.loading-container {
  display: flex;
  justify-content: center;
  padding: 3rem;
}

.action-card {
  text-align: center;
}

.action-content {
  padding: 1rem 0;
}

.action-content h2 {
  margin-bottom: 0.5rem;
  color: var(--p-text-color);
}

.action-content p {
  color: var(--p-text-muted-color);
  margin-bottom: 1rem;
}

.gps-hint {
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.check-in-controls {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.location-select {
  width: 100%;
  max-width: 300px;
}

.action-button {
  min-width: 200px;
}

.current-duration {
  font-size: 2rem;
  font-weight: bold;
  color: var(--p-primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.current-location {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  text-align: center;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.summary-label {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
}

.summary-value {
  font-size: 1.5rem;
  font-weight: bold;
}

.summary-value.positive {
  color: var(--p-green-500);
}

.summary-value.negative {
  color: var(--p-red-500);
}

.signings-list {
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

.signing-duration {
  font-weight: bold;
  color: var(--p-primary-color);
}

.signing-location {
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.week-month-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.wm-column {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.wm-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--p-text-color);
  margin: 0;
  text-align: center;
}

.wm-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.wm-label {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
}

.wm-value {
  font-weight: bold;
  font-size: 1rem;
}

.wm-value.positive {
  color: var(--p-green-500);
}

.wm-value.negative {
  color: var(--p-red-500);
}

@media (max-width: 480px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .signing-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .week-month-grid {
    grid-template-columns: 1fr;
  }
}
</style>
