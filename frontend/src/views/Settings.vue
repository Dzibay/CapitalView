<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth.store'
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

// Функция для сохранения настроек профиля
const saveProfile = () => {
  console.log('Сохранение профиля:', settings.value.profile)
  // TODO: Добавить API вызов для сохранения
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
          <div class="form-group">
            <label for="name">Имя</label>
            <input 
              id="name"
              type="text" 
              v-model="settings.profile.name"
              placeholder="Введите ваше имя"
              class="form-input"
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
            />
          </div>
          
          <button @click="saveProfile" class="btn-primary">
            Сохранить изменения
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

@media (max-width: 768px) {
  .settings-content {
    padding: 16px;
  }
  
  .section-header {
    padding: 16px;
  }
}
</style>