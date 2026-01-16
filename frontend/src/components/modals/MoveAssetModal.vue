<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>Переместить актив</h2>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>

      <div v-if="loading" class="modal-loading">
        <div class="loader"></div>
        <span>Перемещение актива...</span>
      </div>

      <form v-else @submit.prevent="submitForm">
        <div class="form-group">
          <label>Актив:</label>
          <div class="asset-info">
            <strong>{{ asset?.name || asset?.ticker || 'Неизвестный актив' }}</strong>
            <span v-if="asset?.ticker" class="ticker">({{ asset.ticker }})</span>
          </div>
        </div>

        <div class="form-group">
          <label>Текущий портфель:</label>
          <div class="portfolio-info">
            {{ currentPortfolioName || 'Неизвестный портфель' }}
          </div>
        </div>

        <div class="form-group">
          <label for="target-portfolio">Целевой портфель: <span class="required">*</span></label>
          <select
            id="target-portfolio"
            v-model="form.target_portfolio_id"
            required
            :disabled="loading"
          >
            <option value="">Выберите портфель</option>
            <option
              v-for="portfolio in availablePortfolios"
              :key="portfolio.id"
              :value="portfolio.id"
            >
              {{ portfolio.name }}
            </option>
          </select>
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" @click="$emit('close')" :disabled="loading">
            Отмена
          </button>
          <button type="submit" class="btn btn-primary" :disabled="loading || !form.target_portfolio_id">
            Переместить
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  asset: {
    type: Object,
    required: true
  },
  portfolios: {
    type: Array,
    default: () => []
  },
  onSubmit: {
    type: Function,
    required: true
  }
})

const emit = defineEmits(['close'])

const form = ref({
  target_portfolio_id: ''
})

const loading = ref(false)
const error = ref('')

// Получаем текущий портфель актива
// Ищем портфель, который содержит этот актив
const currentPortfolioId = computed(() => {
  // Пробуем получить portfolio_id из актива
  if (props.asset?.portfolio_id) {
    return props.asset.portfolio_id
  }
  
  // Если нет, ищем портфель, содержащий этот актив
  if (props.asset?.portfolio_asset_id) {
    const portfolio = props.portfolios.find(p => 
      p.assets && p.assets.some(a => a.portfolio_asset_id === props.asset.portfolio_asset_id)
    )
    if (portfolio) {
      return portfolio.id
    }
  }
  
  return null
})

const currentPortfolioName = computed(() => {
  if (!currentPortfolioId.value) return 'Неизвестный портфель'
  const portfolio = props.portfolios.find(p => p.id === currentPortfolioId.value)
  return portfolio?.name || 'Неизвестный портфель'
})

// Фильтруем портфели, исключая текущий
const availablePortfolios = computed(() => {
  return props.portfolios.filter(p => p.id !== currentPortfolioId.value)
})

const submitForm = async () => {
  if (!form.value.target_portfolio_id) {
    error.value = 'Выберите целевой портфель'
    return
  }

  if (form.value.target_portfolio_id === currentPortfolioId.value) {
    error.value = 'Актив уже находится в этом портфеле'
    return
  }

  loading.value = true
  error.value = ''

  try {
    await props.onSubmit({
      portfolio_asset_id: props.asset.portfolio_asset_id,
      target_portfolio_id: parseInt(form.value.target_portfolio_id)
    })
    emit('close')
  } catch (err) {
    error.value = err.message || 'Ошибка при перемещении актива'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  // Сбрасываем форму при открытии
  form.value.target_portfolio_id = ''
  error.value = ''
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.modal-content {
  background: white;
  border-radius: 12px;
  padding: 24px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s;
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #111827;
}

.close-btn {
  background: none;
  border: none;
  font-size: 28px;
  color: #6b7280;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #f3f4f6;
  color: #111827;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #374151;
  font-size: 14px;
}

.required {
  color: #ef4444;
}

.asset-info,
.portfolio-info {
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  font-size: 14px;
  color: #374151;
}

.asset-info strong {
  color: #111827;
}

.ticker {
  color: #6b7280;
  margin-left: 8px;
}

select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  background: white;
  color: #111827;
  transition: all 0.2s;
}

select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

select:disabled {
  background: #f3f4f6;
  color: #9ca3af;
  cursor: not-allowed;
}

.modal-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  gap: 16px;
}

.loader {
  width: 40px;
  height: 40px;
  border: 3px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-message {
  padding: 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #dc2626;
  font-size: 14px;
  margin-bottom: 20px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #e5e7eb;
}

.btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-primary:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.btn-secondary:hover:not(:disabled) {
  background: #e5e7eb;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>

