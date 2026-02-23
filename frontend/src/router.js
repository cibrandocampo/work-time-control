import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'

import LoginView from './views/LoginView.vue'
import HomeView from './views/HomeView.vue'
import SigningsView from './views/SigningsView.vue'
import IntegrationView from './views/IntegrationView.vue'
import SettingsView from './views/SettingsView.vue'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'home',
    component: HomeView,
    meta: { requiresAuth: true }
  },
  {
    path: '/signings',
    name: 'signings',
    component: SigningsView,
    meta: { requiresAuth: true }
  },
  {
    path: '/integration',
    name: 'integration',
    component: IntegrationView,
    meta: { requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsView,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
