<template>
  <ModalBase title="Импорт портфеля" :icon="Upload" @close="$emit('close')">
    <div v-if="loading" class="modal-loading">
      <Loader2 :size="32" class="spinner-icon" />
      <span>Импортируем...</span>
    </div>

    <form v-else @submit.prevent="handleImport">
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
            :options="availablePortfolios"
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
  </ModalBase>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Upload, Key, FileText, Loader2 } from 'lucide-vue-next'
import { Button } from '../base'
import CustomSelect from '../base/CustomSelect.vue'
import FormInput from '../base/FormInput.vue'
import portfolioService from '../../services/portfolioService'
import ModalBase from './ModalBase.vue'

const props = defineProps({
  onImport: Function,
  portfolios: Array,
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
const portfolioId = ref(null)
const portfolioName = ref(getDefaultPortfolioName())
const loading = ref(false)
const error = ref('')

// Портфели, доступные для выбранного брокера:
// — без привязки к брокеру
// — уже привязанные к этому же брокеру
// — не являющиеся дочерними портфеля другого брокера
const availablePortfolios = computed(() => {
  if (!props.portfolios || !brokerId.value) return props.portfolios || []

  const allPortfolios = props.portfolios
  const blockedIds = new Set()

  const portfoliosWithOtherBroker = allPortfolios.filter(p => {
    const connBroker = p.connection?.broker_id || null
    return connBroker && connBroker !== brokerId.value
  })

  const collectChildren = (parentId) => {
    allPortfolios.forEach(p => {
      if (p.parent_portfolio_id === parentId && !blockedIds.has(p.id)) {
        blockedIds.add(p.id)
        collectChildren(p.id)
      }
    })
  }

  portfoliosWithOtherBroker.forEach(p => {
    blockedIds.add(p.id)
    collectChildren(p.id)
  })

  return allPortfolios.filter(p => !blockedIds.has(p.id))
})

watch(brokerId, () => {
  if (portfolioId.value) {
    const stillAvailable = availablePortfolios.value.some(p => p.id === portfolioId.value)
    if (!stillAvailable) {
      portfolioId.value = null
    }
  }
})

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
