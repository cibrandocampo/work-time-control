<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Message from 'primevue/message'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')

async function handleLogin() {
  error.value = ''

  if (!username.value || !password.value) {
    error.value = t('login.invalidCredentials')
    return
  }

  const result = await authStore.login(username.value, password.value)

  if (result.success) {
    router.push('/')
  } else {
    error.value = t('login.invalidCredentials')
  }
}
</script>

<template>
  <div class="login-container">
    <Card class="login-card">
      <template #title>
        <div class="login-header">
          <i class="pi pi-clock" style="font-size: 2rem"></i>
          <h1>{{ t('app.title') }}</h1>
        </div>
      </template>
      <template #content>
        <form @submit.prevent="handleLogin" class="login-form">
          <Message v-if="error" severity="error" :closable="false">
            {{ error }}
          </Message>

          <div class="field">
            <label for="username">{{ t('login.username') }}</label>
            <InputText
              id="username"
              v-model="username"
              :placeholder="t('login.username')"
              class="w-full"
              autocomplete="username"
            />
          </div>

          <div class="field">
            <label for="password">{{ t('login.password') }}</label>
            <Password
              id="password"
              v-model="password"
              :placeholder="t('login.password')"
              :feedback="false"
              toggleMask
              class="w-full"
              inputClass="w-full"
              autocomplete="current-password"
            />
          </div>

          <Button
            type="submit"
            :label="t('login.submit')"
            icon="pi pi-sign-in"
            :loading="authStore.loading"
            class="w-full"
          />
        </form>
      </template>
    </Card>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 80vh;
}

.login-card {
  width: 100%;
  max-width: 400px;
}

.login-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-primary-color);
}

.login-header h1 {
  font-size: 1.5rem;
  margin: 0;
}

.login-form {
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
</style>
