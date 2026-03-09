<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <div class="header-content">
          <div class="header-icon-wrapper">
            <Upload :size="20" />
          </div>
          <h2>Импорт портфеля</h2>
        </div>
        <button class="close-btn" @click="$emit('close')" aria-label="Закрыть">
          <X :size="16" />
        </button>
      </div>

      <div v-if="loading" class="modal-loading">
        <Loader2 :size="32" class="spinner-icon" />
        <span>Импортируем...</span>
      </div>

      <form v-else @submit.prevent="handleImport" class="form-content">
        <div class="form-section">
          <CustomSelect
            v-model="brokerId"
            :options="brokers"
            label="Брокер"
            placeholder="Выберите брокера"
            :show-empty-option="false"
            option-label="name"
            option-value="id"
            :min-width="'100%'"
            :flex="'none'"
            :disabled="loadingBrokers"
          />
        </div>

        <div class="form-section">
          <FormInput
            v-model="token"
            label="Токен API"
            :icon="Key"
            type="text"
            placeholder="Введите токен API"
            required
          />
        </div>

        <div class="form-section">
          <CustomSelect
            v-model="portfolioId"
            :options="portfolios"
            label="Портфель"
            placeholder="Создать новый"
            empty-option-text="Создать новый"
            option-label="name"
            option-value="id"
            :min-width="'100%'"
            :flex="'none'"
          />
        </div>

        <div v-if="!portfolioId" class="form-section">
          <FormInput
            v-model="portfolioName"
            label="Название нового портфеля"
            :icon="FileText"
            type="text"
            placeholder="Введите название портфеля"
            required
          />
        </div>

        <div v-if="error" class="error">{{ error }}</div>

        <div class="form-actions">
          <Button variant="secondary" type="button" @click="$emit('close')" :disabled="loading">
            Отмена
          </Button>
          <Button variant="primary" type="submit" :disabled="loading || !brokerId" :loading="loading">
            <template #icon>
              <Upload :size="16" />
            </template>
            Импортировать
          </Button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Upload, X, Key, FileText, Loader2 } from 'lucide-vue-next'
import { Button } from '../base'
import CustomSelect from '../base/CustomSelect.vue'
import FormInput from '../base/FormInput.vue'
import portfolioService from '../../services/portfolioService'

const props = defineProps({
  onImport: Function,
  portfolios: Array,
  onTaskCreated: Function // Callback при создании задачи
})
const emit = defineEmits(['close'])

// Получаем значение по умолчанию из env
const getDefaultBrokerId = () => {
  const envBrokerId = import.meta.env.VITE_DEFAULT_BROKER_ID
  if (envBrokerId) {
    const parsed = parseInt(envBrokerId, 10)
    if (!isNaN(parsed)) {
      return parsed
    }
  }
  return null
}

// Получаем токен по умолчанию из env
const getDefaultToken = () => {
  const envToken = import.meta.env.VITE_DEFAULT_BROKER_TOKEN
  return envToken || ''
}

// Получаем название портфеля по умолчанию из env
const getDefaultPortfolioName = () => {
  const envName = import.meta.env.VITE_DEFAULT_PORTFOLIO_NAME
  return envName || ''
}

const token = ref(getDefaultToken())
const brokerId = ref(null)
const brokers = ref([])
const loadingBrokers = ref(false)
const portfolioId = ref(null)
const portfolioName = ref(getDefaultPortfolioName())
const loading = ref(false)
const error = ref('')

// Загружаем список брокеров
const loadBrokers = async () => {
  loadingBrokers.value = true
  try {
    const brokersList = await portfolioService.getBrokers()
    brokers.value = Array.isArray(brokersList) ? brokersList : []
    
    // Устанавливаем значение по умолчанию
    const defaultBrokerId = getDefaultBrokerId()
    if (defaultBrokerId && brokers.value.find(b => b.id === defaultBrokerId)) {
      brokerId.value = defaultBrokerId
    } else if (brokers.value.length > 0) {
      // Если нет значения из env, берем первого брокера
      brokerId.value = brokers.value[0].id
    }
  } catch (e) {
    console.error('Ошибка загрузки брокеров:', e)
    console.error('Детали ошибки:', e.response?.data || e.message)
    error.value = 'Не удалось загрузить список брокеров'
  } finally {
    loadingBrokers.value = false
  }
}

onMounted(() => {
  loadBrokers()
})

const handleImport = async () => {
  if (!token.value) {
    error.value = 'Введите токен'
    return
  }

  if (!brokerId.value) {
    error.value = 'Выберите брокера'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const result = await props.onImport({
      broker_id: brokerId.value,
      token: token.value,
      portfolioId: portfolioId.value,
      portfolio_name: portfolioName.value
    })
    
    // Если создана задача, вызываем callback
    if (result.success && result.task_id && props.onTaskCreated) {
      props.onTaskCreated(result.task_id)
    }
    
    emit('close')
  } catch (e) {
    error.value = e.message || 'Ошибка импорта'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(8px);
  padding: 16px;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-content {
  background: white;
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  border-radius: 20px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes slideUp {
  from {
    transform: scale(0.95) translateY(10px);
    opacity: 0;
  }
  to {
    transform: scale(1) translateY(0);
    opacity: 1;
  }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #f3f4f6;
  background: #fff;
  flex-shrink: 0;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3b82f6;
}

.modal-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #111827;
  letter-spacing: -0.01em;
}

.close-btn {
  background: #f3f4f6;
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #6b7280;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.close-btn:hover {
  background: #fee2e2;
  color: #dc2626;
  transform: scale(1.05);
}

.close-btn:active {
  transform: scale(0.95);
}

.form-content {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.form-content::-webkit-scrollbar {
  width: 6px;
}

.form-content::-webkit-scrollbar-track {
  background: #f9fafb;
}

.form-content::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.form-section {
  margin-bottom: 24px;
}

.form-section:last-of-type {
  margin-bottom: 20px;
}

.error {
  padding: 10px 14px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 10px;
  color: #dc2626;
  font-size: 13px;
  margin-bottom: 12px;
}

.modal-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 16px;
  font-weight: 500;
  font-size: 14px;
  color: #6b7280;
}

.spinner-icon {
  color: #3b82f6;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 16px;
  margin-top: 8px;
  border-top: 1px solid #f3f4f6;
}
</style>
