<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Bell, X, CheckCircle2, XCircle, Calendar, Coins, Building2 } from 'lucide-vue-next'
import ModalBase from './ModalBase.vue'
import { Button } from '../base'
import missedPayoutsService from '../../services/missedPayoutsService'
import { normalizeDateToString } from '../../utils/date'
import { useDashboardStore } from '../../stores/dashboard.store'

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

const payoutRowKey = (p) =>
  `${p.portfolio_asset_id}:${p.payout_id}`

const samePayoutKey = (a, b) =>
  a.portfolio_asset_id === b.portfolio_asset_id && a.payout_id === b.payout_id
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
const togglePayout = (payout) => {
  const row = {
    portfolio_asset_id: payout.portfolio_asset_id,
    payout_id: payout.payout_id
  }
  const index = selectedPayouts.value.findIndex((x) => samePayoutKey(x, row))
  if (index > -1) {
    selectedPayouts.value.splice(index, 1)
  } else {
    selectedPayouts.value.push(row)
  }
}

// Выбрать все
const selectAll = () => {
  selectedPayouts.value = missedPayouts.value.map((p) => ({
    portfolio_asset_id: p.portfolio_asset_id,
    payout_id: p.payout_id
  }))
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
    // Используем новый батч-эндпоинт для создания всех операций за один раз
    const result = await missedPayoutsService.addOperationsFromMissedPayoutsBatch(selectedPayouts.value)
    
    const insertedCount = result?.data?.inserted_count || 0
    const failedCount = result?.data?.failed_count || 0
    
    if (failedCount > 0) {
      const failedOps = result?.data?.failed_operations || []
      const errorMessages = failedOps.map(op => op.error || 'Неизвестная ошибка').join('; ')
      error.value = `Создано ${insertedCount} операций, ошибок: ${failedCount}. Ошибки: ${errorMessages}`
    }

    // Обновляем список и счетчик
    const addedCount = insertedCount
    selectedPayouts.value = []
    
    // Перезагружаем список выплат для обновления модалки
    await loadMissedPayouts()
    
    // Уведомляем родительский компонент (он обновит dashboard)
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
const allSelected = computed(() => {
  if (missedPayouts.value.length === 0) return false
  if (selectedPayouts.value.length !== missedPayouts.value.length) return false
  const sel = new Set(selectedPayouts.value.map(payoutRowKey))
  return missedPayouts.value.every((p) => sel.has(payoutRowKey(p)))
})

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
              id="select-all-checkbox"
            />
            <label for="select-all-checkbox" class="select-all-text">
              {{ allSelected ? 'Снять выбор' : 'Выбрать все' }}
            </label>
            <span class="selected-count" v-if="hasSelected">
              (Выбрано: {{ selectedPayouts.length }})
            </span>
          </div>
        </div>

        <!-- Список выплат -->
        <div class="payouts-items">
          <div 
            v-for="payout in missedPayouts" 
            :key="payoutRowKey(payout)"
            class="payout-item"
            :class="{ selected: selectedPayouts.some((s) => samePayoutKey(s, payout)) }"
          >
            <div class="payout-checkbox">
              <input 
                type="checkbox"
                :checked="selectedPayouts.some((s) => samePayoutKey(s, payout))"
                @change="togglePayout(payout)"
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
            :loading="processing"
            variant="primary"
            class="action-btn"
          >
            <template #icon>
              <CheckCircle2 :size="16" />
            </template>
            Добавить выбранные ({{ selectedPayouts.length }})
          </Button>
          <Button 
            @click="ignoreSelectedPayouts" 
            :disabled="processing"
            :loading="processing"
            variant="secondary"
            class="action-btn"
          >
            <template #icon>
              <XCircle :size="16" />
            </template>
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

.empty-state {
  padding: 80px 20px;
}

.empty-icon {
  color: #10b981;
  margin-bottom: 16px;
  opacity: 0.8;
}

.empty-state p {
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
}

.error-state {
  padding: 20px;
}

.error-text {
  padding: 12px 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 10px;
  color: #dc2626;
  font-size: 13px;
  font-weight: 500;
}

.list-header {
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
  margin-bottom: 16px;
}

.select-all-section {
  display: flex;
  align-items: center;
  gap: 10px;
}

.checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #527de5;
  flex-shrink: 0;
}

.select-all-text {
  font-weight: 600;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
  user-select: none;
  transition: color 0.2s ease;
}

.select-all-text:hover {
  color: #527de5;
}

.selected-count {
  color: #6b7280;
  font-size: 12px;
  font-weight: 500;
}

.payouts-items {
  flex: 1;
  overflow-y: auto;
  max-height: 400px;
  padding-right: 4px;
}

.payouts-items::-webkit-scrollbar {
  width: 6px;
}

.payouts-items::-webkit-scrollbar-track {
  background: #f9fafb;
  border-radius: 3px;
}

.payouts-items::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.payouts-items::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

.payout-item {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  margin-bottom: 10px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  background: #fff;
}

.payout-item:hover {
  border-color: #527de5;
  background-color: #f9fafb;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.payout-item.selected {
  border-color: #527de5;
  background-color: #eff6ff;
  box-shadow: 0 2px 8px rgba(82, 125, 229, 0.15);
}

.payout-checkbox {
  display: flex;
  align-items: flex-start;
  padding-top: 2px;
  flex-shrink: 0;
}

.payout-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.payout-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.asset-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #111827;
  font-weight: 600;
  font-size: 14px;
  flex: 1;
  min-width: 0;
}

.asset-info svg {
  flex-shrink: 0;
  color: #6b7280;
  opacity: 0.8;
}

.asset-name {
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.asset-ticker {
  color: #6b7280;
  font-weight: 400;
  font-size: 13px;
  white-space: nowrap;
}

.payout-type {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}

.payout-type svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
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
  font-size: 13px;
  flex-wrap: wrap;
}

.detail-item svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  color: #9ca3af;
}

.amount-label {
  font-weight: 500;
  color: #6b7280;
}

.amount-value {
  font-weight: 700;
  color: #10b981;
  font-size: 15px;
}

.actions-section {
  display: flex;
  gap: 10px;
  padding-top: 16px;
  border-top: 1px solid #f3f4f6;
  margin-top: 16px;
  flex-shrink: 0;
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.action-btn :deep(.btn-icon) {
  flex-shrink: 0;
}
</style>
