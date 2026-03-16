<template>
  <ModalBase title="Импорт портфеля" :icon="Upload" @close="$emit('close')">
    <div v-if="loading" class="modal-loading">
      <Loader2 :size="32" class="spinner-icon" />
      <span>Импортируем...</span>
    </div>

    <form v-else @submit.prevent="handleImport">
        <p class="import-hint">Импорт создаёт новый портфель в «Все активы».</p>

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
          <FormInput
            v-model="portfolioName"
            label="Название портфеля"
            :icon="FileText"
            type="text"
            placeholder="Например: Брокер Tinkoff"
            required
          />
        </div>

        <div v-if="error" class="error">{{ error }}</div>

        <div class="form-actions">
          <Button variant="secondary" type="button" @click="$emit('close')" :disabled="loading">
            Отмена
          </Button>
          <Button variant="primary" type="submit" :disabled="loading || !brokerId || !portfolioName?.trim()" :loading="loading">
            <template #icon>
              <Upload :size="16" />
            </template>
            Импортировать
          </Button>
        </div>
      </form>
  </ModalBase>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Upload, Key, FileText, Loader2 } from 'lucide-vue-next'
import { Button } from '../base'
import CustomSelect from '../base/CustomSelect.vue'
import FormInput from '../base/FormInput.vue'
import portfolioService from '../../services/portfolioService'
import ModalBase from './ModalBase.vue'

const props = defineProps({
  onImport: Function,
  onTaskCreated: Function
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

  if (!portfolioName.value?.trim()) {
    error.value = 'Введите название портфеля'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const result = await props.onImport({
      broker_id: brokerId.value,
      token: token.value,
      portfolioId: null,
      portfolio_name: portfolioName.value.trim()
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
.import-hint {
  margin: 0 0 16px;
  padding: 10px 12px;
  background: #eff6ff;
  border-radius: 8px;
  font-size: 13px;
  color: #1e40af;
}

.form-section {
  margin-bottom: 20px;
}

.form-section:last-of-type {
  margin-bottom: 16px;
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
