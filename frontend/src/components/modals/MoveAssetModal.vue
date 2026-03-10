<template>
  <ModalBase title="Переместить актив" :icon="MoveRight" @close="$emit('close')">
    <div v-if="loading" class="modal-loading">
      <Loader2 :size="32" class="spinner-icon" />
      <span>Перемещение актива...</span>
    </div>

    <form v-else @submit.prevent="submitForm">
      <div class="form-section">
        <div class="info-card">
          <TrendingUp :size="18" class="info-icon" />
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
          <Briefcase :size="18" class="info-icon" />
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

      <div v-if="error" class="error">
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
  </ModalBase>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ArrowRight, MoveRight, TrendingUp, Briefcase, Loader2 } from 'lucide-vue-next'
import { Button } from '../base'
import CustomSelect from '../base/CustomSelect.vue'
import ModalBase from './ModalBase.vue'

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
  color: #6b7280;
  flex-shrink: 0;
  opacity: 0.8;
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

.spinner-icon {
  color: #3b82f6;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
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

.form-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  padding-top: 16px;
  margin-top: 8px;
  border-top: 1px solid #f3f4f6;
}
</style>

