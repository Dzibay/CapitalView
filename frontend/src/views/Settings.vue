<script setup>
import { ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth.store'
import { authService } from '../services/authService'
import PageLayout from '../components/PageLayout.vue'
import PageHeader from '../components/PageHeader.vue'
import { User } from 'lucide-vue-next'

const authStore = useAuthStore()

// Состояния для настроек профиля
const settings = ref({
  profile: {
    name: authStore.user?.name || '',
    email: authStore.user?.email || '',
  }
})

// Состояния для UI
const isLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

// Обновляем значения при изменении пользователя в store
watch(() => authStore.user, (newUser) => {
  if (newUser) {
    settings.value.profile.name = newUser.name || ''
    settings.value.profile.email = newUser.email || ''
  }
}, { immediate: true })

// Функция для сохранения настроек профиля
const saveProfile = async () => {
  if (isLoading.value) return
  
  errorMessage.value = ''
  successMessage.value = ''
  isLoading.value = true

  try {
    // Валидация
    if (!settings.value.profile.name || !settings.value.profile.name.trim()) {
      errorMessage.value = 'Имя не может быть пустым'
      isLoading.value = false
      return
    }

    if (!settings.value.profile.email || !settings.value.profile.email.trim()) {
      errorMessage.value = 'Email не может быть пустым'
      isLoading.value = false
      return
    }

    // Проверка формата email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(settings.value.profile.email)) {
      errorMessage.value = 'Некорректный формат email'
      isLoading.value = false
      return
    }

    // Вызов API
    const response = await authService.updateProfile(
      settings.value.profile.name.trim(),
      settings.value.profile.email.trim()
    )

    if (response && response.data && response.data.user) {
      // Обновляем пользователя в store
      authStore.setUser(response.data.user)
      successMessage.value = 'Профиль успешно обновлен'
      
      // Скрываем сообщение об успехе через 3 секунды
      setTimeout(() => {
        successMessage.value = ''
      }, 3000)
    }
  } catch (error) {
    console.error('Ошибка при обновлении профиля:', error)
    if (error.response && error.response.data && error.response.data.detail) {
      errorMessage.value = error.response.data.detail
    } else if (error.message) {
      errorMessage.value = error.message
    } else {
      errorMessage.value = 'Произошла ошибка при обновлении профиля'
    }
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <PageLayout>
    <PageHeader 
      title="Настройки"
      subtitle="Управление параметрами аккаунта"
    />

    <div class="settings-container">
      <!-- Профиль -->
      <section class="settings-section">
        <div class="section-header">
          <div class="section-icon">
            <User :size="20" />
          </div>
          <div>
            <h2 class="section-title">Профиль</h2>
            <p class="section-description">Управление личными данными</p>
          </div>
        </div>
        
        <div class="settings-content">
          <!-- Сообщения об ошибках и успехе -->
          <div v-if="errorMessage" class="message message-error">
            {{ errorMessage }}
          </div>
          <div v-if="successMessage" class="message message-success">
            {{ successMessage }}
          </div>

          <div class="form-group">
            <label for="name">Имя</label>
            <input 
              id="name"
              type="text" 
              v-model="settings.profile.name"
              placeholder="Введите ваше имя"
              class="form-input"
              :disabled="isLoading"
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
              :disabled="isLoading"
            />
          </div>
          
          <button 
            @click="saveProfile" 
            class="btn-primary"
            :disabled="isLoading"
          >
            <span v-if="isLoading">Сохранение...</span>
            <span v-else>Сохранить изменения</span>
          </button>
        </div>
      </section>
    </div>
  </PageLayout>
</template>

<style scoped>
.settings-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 24px 0;
}

.settings-section {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
}

.section-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #527de5, #6b91ea);
  color: white;
}

.section-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.section-description {
  margin: 4px 0 0 0;
  font-size: 14px;
  color: #6b7280;
}

.settings-content {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.form-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  color: #111827;
  background: #fff;
  transition: all 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: #527de5;
  box-shadow: 0 0 0 3px rgba(82, 125, 229, 0.1);
}

.btn-primary {
  padding: 10px 20px;
  background: linear-gradient(135deg, #527de5, #6b91ea);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(82, 125, 229, 0.3);
}

.btn-primary:active {
  transform: translateY(0);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.message {
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
}

.message-error {
  background-color: #fee2e2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.message-success {
  background-color: #d1fae5;
  color: #059669;
  border: 1px solid #a7f3d0;
}

.form-input:disabled {
  background-color: #f3f4f6;
  cursor: not-allowed;
  opacity: 0.7;
}

@media (max-width: 768px) {
  .settings-content {
    padding: 16px;
  }
  
  .section-header {
    padding: 16px;
  }
}
</style>