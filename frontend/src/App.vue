<script setup>
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from './stores/auth'
import Menubar from 'primevue/menubar'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import { useRouter } from 'vue-router'

const { t } = useI18n()
const authStore = useAuthStore()
const router = useRouter()

const menuItems = computed(() => [
  {
    label: t('nav.home'),
    icon: 'pi pi-home',
    command: () => router.push('/')
  },
  {
    label: t('nav.signings'),
    icon: 'pi pi-clock',
    command: () => router.push('/signings')
  },
  {
    label: t('nav.integration'),
    icon: 'pi pi-sync',
    command: () => router.push('/integration')
  },
  {
    label: t('nav.settings'),
    icon: 'pi pi-cog',
    command: () => router.push('/settings')
  }
])

onMounted(async () => {
  await authStore.init()
})
</script>

<template>
  <Toast />
  <ConfirmDialog />

  <div class="app-container">
    <Menubar v-if="authStore.isAuthenticated" :model="menuItems" class="app-menubar">
      <template #start>
        <span class="app-title">WTC</span>
      </template>
      <template #end>
        <span v-if="authStore.user" class="user-info">
          <i class="pi pi-user"></i>
          {{ authStore.user.username }}
        </span>
      </template>
    </Menubar>

    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  background-color: #f5f5f5;
  min-height: 100vh;
}

.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-menubar {
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-top: none;
}

.app-title {
  font-weight: bold;
  font-size: 1.2rem;
  margin-right: 2rem;
  color: var(--p-primary-color);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-text-muted-color);
}

.app-main {
  flex: 1;
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

@media (max-width: 768px) {
  .app-main {
    padding: 1rem;
  }
}
</style>
