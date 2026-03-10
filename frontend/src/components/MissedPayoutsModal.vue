<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Bell, X, CheckCircle2, XCircle, Calendar, Coins, Building2 } from 'lucide-vue-next'
import ModalBase from './modals/ModalBase.vue'
import { Button } from './base'
import missedPayoutsService from '../services/missedPayoutsService'
import operationsService from '../services/operationsService'
import { normalizeDateToString } from '../utils/date'
import { useDashboardStore } from '../stores/dashboard.store'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'payouts-added', 'payouts-ignored'])

const dashboardStore = useDashboardStore()

const missedPayouts = ref([])
const selectedPayouts = ref([])
const loading = ref(false)
const processing = ref(false)
const error = ref('')

// Загружаем неполученные выплаты
const loadMissedPayouts = async () => {
  loading.value = true
  error.value = ''
  try {
    missedPayouts.value = await missedPayoutsService.getMissedPayouts()
  } catch (err) {
    error.value = err.response?.data?.message || 'Ошибка при загрузке неполученных выплат'
    console.error('Ошибка загрузки неполученных выплат:', err)
  } finally {
    loading.value = false
  }
}

// Выбор/снятие выбора выплаты
const togglePayout = (payoutId) => {
  const index = selectedPayouts.value.indexOf(payoutId)
  if (index > -1) {
    selectedPayouts.value.splice(index, 1)
  } else {
    selectedPayouts.value.push(payoutId)
  }
}

// Выбрать все
const selectAll = () => {
  selectedPayouts.value = missedPayouts.value.map(p => p.id || p.missed_payout_id)
}

// Снять выбор со всех
const deselectAll = () => {
  selectedPayouts.value = []
}

// Добавить выбранные выплаты как операции
const addSelectedPayouts = async () => {
  if (selectedPayouts.value.length === 0) {
    error.value = 'Выберите хотя бы одну выплату'
    return
  }

  processing.value = true
  error.value = ''

  try {
    const selectedPayoutsData = missedPayouts.value.filter(p => 
      selectedPayouts.value.includes(p.id || p.missed_payout_id)
    )

    // Создаем операции для каждой выбранной выплаты
    // Используем Promise.all для параллельного создания операций
    await Promise.all(
      selectedPayoutsData.map(async (payout) => {
        const operationType = payout.payout_type?.toLowerCase() === 'coupon' ? 4 : 3 // 4 = Coupon, 3 = Dividend
        // Используем expected_amount из API (уже рассчитано с учетом количества акций)
        const expectedAmount = payout.expected_amount || payout.payout_value || 0
        
        const operationData = {
          portfolio_id: payout.portfolio_id,
          operation_type: operationType,
          amount: expectedAmount,
          currency_id: 1, // RUB
          operation_date: normalizeDateToString(new Date(payout.payment_date || payout.payout_payment_date)) || '',
          asset_id: payout.asset_id,
          portfolio_asset_id: payout.portfolio_asset_id
        }
        
        return operationsService.addOperation(operationData)
      })
    )

    // Удаляем добавленные выплаты из списка неполученных
    await missedPayoutsService.deleteMissedPayoutsBatch(selectedPayouts.value)

    // Обновляем список и счетчик
    const addedCount = selectedPayouts.value.length
    await loadMissedPayouts()
    selectedPayouts.value = []
    
    // Обновляем dashboard store для отображения новых операций
    try {
      await dashboardStore.reloadDashboard(false)
    } catch (err) {
      console.error('Ошибка обновления dashboard после добавления выплат:', err)
    }
    
    // Уведомляем родительский компонент
    emit('payouts-added', addedCount)
  } catch (err) {
    error.value = err.response?.data?.message || 'Ошибка при добавлении выплат'
    console.error('Ошибка добавления выплат:', err)
  } finally {
    processing.value = false
  }
}

// Игнорировать выбранные выплаты (удалить записи)
const ignoreSelectedPayouts = async () => {
  if (selectedPayouts.value.length === 0) {
    error.value = 'Выберите хотя бы одну выплату'
    return
  }

  processing.value = true
  error.value = ''

  try {
    await missedPayoutsService.deleteMissedPayoutsBatch(selectedPayouts.value)
    
    // Обновляем список и счетчик
    await loadMissedPayouts()
    const ignoredCount = selectedPayouts.value.length
    selectedPayouts.value = []
    
    // Уведомляем родительский компонент
    emit('payouts-ignored', ignoredCount)
  } catch (err) {
    error.value = err.response?.data?.message || 'Ошибка при игнорировании выплат'
    console.error('Ошибка игнорирования выплат:', err)
  } finally {
    processing.value = false
  }
}

// Форматирование даты
const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('ru-RU', { 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit' 
  })
}

// Форматирование суммы
const formatAmount = (amount) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 2
  }).format(amount || 0)
}

// Вычисляемые свойства
const hasSelected = computed(() => selectedPayouts.value.length > 0)
const allSelected = computed(() => 
  missedPayouts.value.length > 0 && 
  selectedPayouts.value.length === missedPayouts.value.length
)

// Загружаем данные при открытии модалки
onMounted(() => {
  if (props.show) {
    loadMissedPayouts()
  }
})

// Отслеживаем открытие модалки
watch(() => props.show, (newVal) => {
  if (newVal) {
    loadMissedPayouts()
    selectedPayouts.value = []
  }
})
</script>

<template>
  <ModalBase 
    :show="show" 
    title="Неполученные выплаты" 
    :icon="Bell"
    wide
    @close="$emit('close')"
  >
    <div class="missed-payouts-content">
      <!-- Загрузка -->
      <div v-if="loading" class="loading-state">
        <p>Загрузка неполученных выплат...</p>
      </div>

      <!-- Ошибка -->
      <div v-else-if="error" class="error-state">
        <p class="error-text">{{ error }}</p>
      </div>

      <!-- Пустой список -->
      <div v-else-if="missedPayouts.length === 0" class="empty-state">
        <CheckCircle2 :size="48" class="empty-icon" />
        <p>Нет неполученных выплат</p>
      </div>

      <!-- Список выплат -->
      <div v-else class="payouts-list">
        <!-- Заголовок с действиями -->
        <div class="list-header">
          <div class="select-all-section">
            <input 
              type="checkbox" 
              :checked="allSelected"
              @change="allSelected ? deselectAll() : selectAll()"
              class="checkbox"
            />
            <span class="select-all-text">
              {{ allSelected ? 'Снять выбор' : 'Выбрать все' }}
            </span>
            <span class="selected-count" v-if="hasSelected">
              (Выбрано: {{ selectedPayouts.length }})
            </span>
          </div>
        </div>

        <!-- Список выплат -->
        <div class="payouts-items">
          <div 
            v-for="payout in missedPayouts" 
            :key="payout.id || payout.missed_payout_id"
            class="payout-item"
            :class="{ selected: selectedPayouts.includes(payout.id || payout.missed_payout_id) }"
          >
            <div class="payout-checkbox">
              <input 
                type="checkbox"
                :checked="selectedPayouts.includes(payout.id || payout.missed_payout_id)"
                @change="togglePayout(payout.id || payout.missed_payout_id)"
                class="checkbox"
              />
            </div>

            <div class="payout-info">
              <div class="payout-header">
                <div class="asset-info">
                  <Building2 :size="16" />
                  <span class="asset-name">{{ payout.asset_name || payout.asset_ticker }}</span>
                  <span class="asset-ticker">({{ payout.asset_ticker }})</span>
                </div>
                <div class="payout-type" :class="payout.payout_type?.toLowerCase()">
                  <Coins :size="14" />
                  <span>{{ payout.payout_type === 'coupon' ? 'Купон' : 'Дивиденд' }}</span>
                </div>
              </div>

              <div class="payout-details">
                <div class="detail-item">
                  <Calendar :size="14" />
                  <span>Дата выплаты: {{ formatDate(payout.payment_date || payout.payout_payment_date) }}</span>
                </div>
                <div class="detail-item">
                  <span class="amount-label">Сумма выплаты:</span>
                  <span class="amount-value">{{ formatAmount(payout.expected_amount || payout.payout_value) }}</span>
                </div>
                <div class="detail-item" v-if="payout.portfolio_name">
                  <span>Портфель: {{ payout.portfolio_name }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Действия -->
        <div class="actions-section" v-if="hasSelected">
          <Button 
            @click="addSelectedPayouts" 
            :disabled="processing"
            class="action-btn add-btn"
          >
            <CheckCircle2 :size="16" />
            Добавить выбранные ({{ selectedPayouts.length }})
          </Button>
          <Button 
            @click="ignoreSelectedPayouts" 
            :disabled="processing"
            variant="secondary"
            class="action-btn ignore-btn"
          >
            <XCircle :size="16" />
            Игнорировать ({{ selectedPayouts.length }})
          </Button>
        </div>
      </div>
    </div>
  </ModalBase>
</template>

<style scoped>
.missed-payouts-content {
  min-height: 300px;
  max-height: 600px;
  display: flex;
  flex-direction: column;
}

.loading-state,
.empty-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  color: #6b7280;
}

.empty-icon {
  color: #10b981;
  margin-bottom: 16px;
}

.error-text {
  color: #ef4444;
}

.list-header {
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
  margin-bottom: 16px;
}

.select-all-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #3b82f6;
}

.select-all-text {
  font-weight: 600;
  color: #1f2937;
  cursor: pointer;
}

.selected-count {
  color: #6b7280;
  font-size: 14px;
}

.payouts-items {
  flex: 1;
  overflow-y: auto;
  max-height: 400px;
}

.payout-item {
  display: flex;
  gap: 12px;
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  margin-bottom: 12px;
  transition: all 0.2s ease;
  cursor: pointer;
}

.payout-item:hover {
  border-color: #3b82f6;
  background-color: #f9fafb;
}

.payout-item.selected {
  border-color: #3b82f6;
  background-color: #eff6ff;
}

.payout-checkbox {
  display: flex;
  align-items: flex-start;
  padding-top: 2px;
}

.payout-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.payout-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.asset-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #1f2937;
  font-weight: 600;
}

.asset-name {
  color: #1f2937;
}

.asset-ticker {
  color: #6b7280;
  font-weight: 400;
}

.payout-type {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
}

.payout-type.coupon {
  background-color: #fef3c7;
  color: #92400e;
}

.payout-type.dividend {
  background-color: #dbeafe;
  color: #1e40af;
}

.payout-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6b7280;
  font-size: 14px;
}

.amount-label {
  font-weight: 600;
}

.amount-value {
  font-weight: 700;
  color: #10b981;
  font-size: 16px;
}

.actions-section {
  display: flex;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #f3f4f6;
  margin-top: 16px;
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.add-btn {
  background-color: #10b981;
}

.add-btn:hover {
  background-color: #059669;
}

.ignore-btn {
  background-color: #6b7280;
}

.ignore-btn:hover {
  background-color: #4b5563;
}
</style>
