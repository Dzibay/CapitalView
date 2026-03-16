<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.store'
import { authService } from '../services/authService'
import PageLayout from '../layouts/PageLayout.vue'
import PageHeader from '../layouts/PageHeader.vue'
import Widget from '../components/widgets/base/Widget.vue'
import WidgetContainer from '../components/widgets/base/WidgetContainer.vue'
import { User, Lock, LogOut } from 'lucide-vue-next'

const authStore = useAuthStore()
const router = useRouter()

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

// Состояния для настроек профиля
const settings = ref({
  profile: {
    name: authStore.user?.name || '',
    email: authStore.user?.email || '',
  },
  password: {
    current: '',
    new: '',
    confirm: '',
  }
})

// Состояния для UI
const isLoadingProfile = ref(false)
const isLoadingPassword = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const passwordError = ref('')
const passwordSuccess = ref('')

// Обновляем значения при изменении пользователя в store
watch(() => authStore.user, (newUser) => {
  if (newUser) {
    settings.value.profile.name = newUser.name || ''
    settings.value.profile.email = newUser.email || ''
  }
}, { immediate: true })

// Функция для сохранения настроек профиля
const saveProfile = async () => {
  if (isLoadingProfile.value) return
  
  errorMessage.value = ''
  successMessage.value = ''
  isLoadingProfile.value = true

  try {
    if (!settings.value.profile.name || !settings.value.profile.name.trim()) {
      errorMessage.value = 'Имя не может быть пустым'
      isLoadingProfile.value = false
      return
    }

    if (!settings.value.profile.email || !settings.value.profile.email.trim()) {
      errorMessage.value = 'Email не может быть пустым'
      isLoadingProfile.value = false
      return
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(settings.value.profile.email)) {
      errorMessage.value = 'Некорректный формат email'
      isLoadingProfile.value = false
      return
    }

    const response = await authService.updateProfile(
      settings.value.profile.name.trim(),
      settings.value.profile.email.trim()
    )

    const user = response?.user ?? response?.data?.user
    if (user) {
      authStore.setUser(user)
      successMessage.value = 'Профиль успешно обновлён'
      setTimeout(() => { successMessage.value = '' }, 3000)
    }
  } catch (error) {
    console.error('Ошибка при обновлении профиля:', error)
    errorMessage.value = error.response?.data?.detail || error.message || 'Произошла ошибка при обновлении профиля'
  } finally {
    isLoadingProfile.value = false
  }
}

// Функция для смены пароля
const savePassword = async () => {
  if (isLoadingPassword.value) return
  
  passwordError.value = ''
  passwordSuccess.value = ''

  const { current, new: newPass, confirm } = settings.value.password

  if (!current || !newPass || !confirm) {
    passwordError.value = 'Заполните все поля'
    return
  }

  if (newPass.length < 4) {
    passwordError.value = 'Новый пароль должен быть не менее 4 символов'
    return
  }

  if (newPass !== confirm) {
    passwordError.value = 'Новый пароль и подтверждение не совпадают'
    return
  }

  if (current === newPass) {
    passwordError.value = 'Новый пароль должен отличаться от текущего'
    return
  }

  isLoadingPassword.value = true

  try {
    await authService.changePassword(current, newPass)
    passwordSuccess.value = 'Пароль успешно изменён'
    settings.value.password = { current: '', new: '', confirm: '' }
    setTimeout(() => { passwordSuccess.value = '' }, 3000)
  } catch (error) {
    console.error('Ошибка при смене пароля:', error)
    passwordError.value = error.response?.data?.detail || error.message || 'Произошла ошибка при смене пароля'
  } finally {
    isLoadingPassword.value = false
  }
}
</script>

<template>
  <PageLayout>
    <PageHeader 
      title="Настройки"
      subtitle="Управление параметрами аккаунта"
    >
      <template #actions>
        <button class="btn-logout" @click="handleLogout">
          <LogOut :size="18" />
          Выйти
        </button>
      </template>
    </PageHeader>

    <div class="settings-grid">
      <!-- Профиль -->
      <WidgetContainer :gridColumn="6" minHeight="auto">
        <Widget title="Профиль" :icon="User">
          <div v-if="errorMessage" class="message message-error">{{ errorMessage }}</div>
          <div v-if="successMessage" class="message message-success">{{ successMessage }}</div>

          <div class="form-group">
            <label for="name">Имя</label>
            <input 
              id="name"
              type="text" 
              v-model="settings.profile.name"
              placeholder="Введите ваше имя"
              class="form-input"
              :disabled="isLoadingProfile"
            />
          </div>
          
          <div class="form-group">
            <label for="email">Email</label>
            <input 
              id="email"
              type="email" 
              v-model="settings.profile.email"
              placeholder="Введите email"
              class="form-input"
              :disabled="isLoadingProfile"
            />
          </div>
          
          <button 
            @click="saveProfile" 
            class="btn-primary"
            :disabled="isLoadingProfile"
          >
            {{ isLoadingProfile ? 'Сохранение...' : 'Сохранить изменения' }}
          </button>
        </Widget>
      </WidgetContainer>

      <!-- Смена пароля -->
      <WidgetContainer :gridColumn="6" minHeight="auto">
        <Widget title="Безопасность" :icon="Lock">
          <div v-if="passwordError" class="message message-error">{{ passwordError }}</div>
          <div v-if="passwordSuccess" class="message message-success">{{ passwordSuccess }}</div>

          <div class="form-group">
            <label for="current-password">Текущий пароль</label>
            <input 
              id="current-password"
              type="password" 
              v-model="settings.password.current"
              placeholder="Введите текущий пароль"
              class="form-input"
              autocomplete="current-password"
              :disabled="isLoadingPassword"
            />
          </div>

          <div class="form-group">
            <label for="new-password">Новый пароль</label>
            <input 
              id="new-password"
              type="password" 
              v-model="settings.password.new"
              placeholder="Минимум 4 символа"
              class="form-input"
              autocomplete="new-password"
              :disabled="isLoadingPassword"
            />
          </div>

          <div class="form-group">
            <label for="confirm-password">Подтвердите новый пароль</label>
            <input 
              id="confirm-password"
              type="password" 
              v-model="settings.password.confirm"
              placeholder="Повторите новый пароль"
              class="form-input"
              autocomplete="new-password"
              :disabled="isLoadingPassword"
            />
          </div>
          
          <button 
            @click="savePassword" 
            class="btn-primary"
            :disabled="isLoadingPassword"
          >
            {{ isLoadingPassword ? 'Сохранение...' : 'Изменить пароль' }}
          </button>
        </Widget>
      </WidgetContainer>
    </div>
  </PageLayout>
</template>

<style scoped>
.settings-grid {
  display: grid;
  gap: var(--spacing);
  grid-template-columns: repeat(12, 1fr);
  width: 100%;
  min-width: 0;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group:last-of-type {
  margin-bottom: 1.25rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.375rem;
  font-size: var(--text-caption-size);
  font-weight: var(--text-label-weight);
  color: var(--text-tertiary);
}

.form-input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--axis-border);
  border-radius: 8px;
  font-size: var(--text-body-secondary-size);
  color: var(--text-primary);
  background: var(--bg-primary);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-input::placeholder {
  color: var(--text-quaternary);
}

.form-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(82, 125, 229, 0.15);
}

.form-input:disabled {
  background: var(--bg-tertiary);
  cursor: not-allowed;
  opacity: 0.7;
}

.btn-primary {
  padding: 0.5rem 1rem;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: var(--text-caption-size);
  font-weight: var(--text-label-weight);
  cursor: pointer;
  transition: background 0.2s, transform 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-hover);
  transform: translateY(-1px);
}

.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-logout {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: transparent;
  color: var(--text-tertiary);
  border: 1px solid var(--axis-border);
  border-radius: 8px;
  font-size: var(--text-caption-size);
  font-weight: var(--text-label-weight);
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s, background 0.2s;
}

.btn-logout:hover {
  color: var(--danger);
  border-color: var(--danger-light);
  background: rgba(239, 68, 68, 0.05);
}

.message {
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: var(--text-caption-size);
}

.message-error {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.message-success {
  background: rgba(28, 189, 136, 0.1);
  color: var(--success);
  border: 1px solid rgba(28, 189, 136, 0.3);
}

@media (max-width: 768px) {
  .settings-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .settings-grid :deep(.widget-container) {
    grid-column: 1 / -1 !important;
  }
}
</style>
