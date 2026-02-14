<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>Переместить актив</h2>
        <button class="close-btn" @click="$emit('close')" aria-label="Закрыть">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <div v-if="loading" class="modal-loading">
        <div class="spinner"></div>
        <span>Перемещение актива...</span>
      </div>

      <form v-else @submit.prevent="submitForm" class="form-content">
        <div class="form-section">
          <div class="info-card">
            <span class="info-icon">📈</span>
            <div>
              <div class="info-label">Актив</div>
              <div class="info-value">
                <strong>{{ asset?.name || asset?.ticker || 'Неизвестный актив' }}</strong>
                <span v-if="asset?.ticker" class="ticker">({{ asset.ticker }})</span>
              </div>
            </div>
          </div>
        </div>

        <div class="form-section">
          <div class="section-divider"></div>
          <div class="info-card">
            <span class="info-icon">💼</span>
            <div>
              <div class="info-label">Текущий портфель</div>
              <div class="info-value">{{ currentPortfolioName || 'Неизвестный портфель' }}</div>
            </div>
          </div>
        </div>

        <div class="form-section">
          <div class="section-divider"></div>
          <CustomSelect
            v-model="form.target_portfolio_id"
            :options="availablePortfolios"
            label="Целевой портфель"
            placeholder="Выберите портфель"
            :show-empty-option="false"
            option-label="name"
            option-value="id"
            :min-width="'100%'"
            :flex="'none'"
          />
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <div class="form-actions">
          <Button variant="secondary" type="button" @click="$emit('close')" :disabled="loading">
            Отмена
          </Button>
          <Button variant="primary" type="submit" :disabled="loading || !form.target_portfolio_id" :loading="loading">
            <template #icon>
              <ArrowRight :size="16" />
            </template>
            Переместить
          </Button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ArrowRight } from 'lucide-vue-next'
import { Button } from '../base'
import CustomSelect from '../base/CustomSelect.vue'

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
  backdrop-filter: blur(8px);
  padding: 16px;
  animation: fadeIn 0.2s ease;
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
  border-radius: 20px;
  padding: 0;
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
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
  justify-content: space-between;
  align-items: center;
  padding: 18px 20px;
  border-bottom: 1px solid #f3f4f6;
  background: #fff;
  flex-shrink: 0;
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

.close-btn svg {
  width: 16px;
  height: 16px;
}

.form-content {
  padding: 20px;
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
  margin-bottom: 20px;
}

.form-section:last-of-type {
  margin-bottom: 16px;
}

.section-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, #e5e7eb, transparent);
  margin: 16px 0;
}

.info-card {
  padding: 12px 16px;
  background: #f9fafb;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  gap: 12px;
}

.info-icon {
  font-size: 20px;
  opacity: 0.8;
  flex-shrink: 0;
}

.info-label {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.info-value {
  font-size: 14px;
  color: #111827;
  font-weight: 500;
}

.info-value strong {
  color: #111827;
  font-weight: 600;
}

.ticker {
  color: #6b7280;
  margin-left: 6px;
  font-size: 13px;
  font-weight: 400;
}

select {
  width: 100%;
  padding: 10px 12px;
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
  color: #111827;
  transition: all 0.2s ease;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

select:hover {
  border-color: #d1d5db;
  background: #fff;
}

select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1), 0 2px 4px rgba(0,0,0,0.05);
  background: #fff;
}

select:disabled {
  background: #f3f4f6;
  color: #9ca3af;
  cursor: not-allowed;
  opacity: 0.6;
}

.modal-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
  font-weight: 500;
  font-size: 14px;
  color: #6b7280;
}

.spinner {
  width: 32px;
  height: 32px;
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
  padding: 10px 14px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 10px;
  color: #dc2626;
  font-size: 13px;
  margin-bottom: 12px;
}

.form-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  padding-top: 16px;
  margin-top: 8px;
  border-top: 1px solid #f3f4f6;
}

</style>

