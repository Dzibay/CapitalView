<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { Check, Edit, TrendingUp, RefreshCw, Hash, DollarSign, Calendar, Loader2 } from 'lucide-vue-next'
import { Button, DateInput, ToggleSwitch } from '../base'
import CustomSelect from '../base/CustomSelect.vue'
import assetsService from '../../services/assetsService'
import { useDashboardStore } from '../../stores/dashboard.store'
import { normalizeDateToString } from '../../utils/date'
import { getCurrencySymbol } from '../../utils/currencySymbols'
import ModalBase from './ModalBase.vue'
import { fetchReferenceAssetMeta } from '../../services/referenceService'

const props = defineProps({
  transaction: Object,
  visible: Boolean
})

const emit = defineEmits(['close', 'save'])

const dashboardStore = useDashboardStore()

const resolvedAssetMeta = ref(null)

const editedTx = ref({ ...props.transaction })
const saving = ref(false)
const loadingPrice = ref(false)
const priceHistoryCache = ref(null)
const isLoadingHistory = ref(false)
const minDate = ref(null)
const useMarketPrice = ref(true) // Включен по умолчанию
const lastMarketPrice = ref(null) // Последняя загруженная рыночная цена

// Определяем, является ли актив системным
const isSystemAsset = computed(() => {
  const assetId = props.transaction?.asset_id
  if (!assetId) return false
  const m = resolvedAssetMeta.value
  if (!m || m.id !== assetId) return false
  return m.user_id == null || m.is_custom === false
})

// Валюта актива для отображения в поле Цена
const assetCurrencyTicker = computed(() => {
  if (props.transaction?.currency_ticker) return props.transaction.currency_ticker
  const refData = dashboardStore.referenceData
  const assetId = props.transaction?.asset_id
  if (!assetId) return 'RUB'
  const m = resolvedAssetMeta.value
  if (m && m.id === assetId && m.quote_ticker) return m.quote_ticker
  if (m?.quote_asset_id != null && refData?.currencies) {
    const c = refData.currencies.find((x) => x.id === m.quote_asset_id)
    if (c?.ticker) return c.ticker
  }
  return 'RUB'
})
const assetCurrencySymbol = computed(() => getCurrencySymbol(assetCurrencyTicker.value))

// Только для покупки: ищем связанную операцию пополнения и предлагаем её обновить
const isBuy = computed(() => {
  const t = props.transaction?.transaction_type ?? editedTx.value?.transaction_type
  return t === 1 || t === '1' || (typeof t === 'string' && (t === 'Покупка' || t.toLowerCase().includes('buy')))
})
const originalAmount = computed(() => {
  const q = props.transaction?.quantity ?? 0
  const p = props.transaction?.price ?? 0
  return Number(q) * Number(p)
})
const originalDateDay = computed(() => {
  const d = props.transaction?.transaction_date
  if (!d) return ''
  const s = normalizeDateToString(d)
  return s ? s.slice(0, 10) : ''
})
const newAmount = computed(() => {
  const q = editedTx.value?.quantity ?? 0
  const p = editedTx.value?.price ?? 0
  return Number(q) * Number(p)
})
const newDateDay = computed(() => {
  const d = editedTx.value?.transaction_date
  if (!d) return ''
  const s = normalizeDateToString(d)
  return s ? s.slice(0, 10) : ''
})
const hasRelevantChanges = computed(() => {
  return Math.abs(originalAmount.value - newAmount.value) > 1e-6 || originalDateDay.value !== newDateDay.value
})
// Тип операции пополнения: в API может быть type (число) или operation_type (число/строка)
const isDepositOperation = (op) => {
  const t = op.type ?? op.operation_type
  if (t === 5 || t === '5') return true
  if (typeof t === 'string' && (t.toLowerCase().includes('пополнение') || t.toLowerCase().includes('deposit') || t.toLowerCase().includes('депозит'))) return true
  return false
}
// Нормализация даты операции к YYYY-MM-DD для сравнения
const opDateDay = (op) => {
  const d = op.operation_date ?? op.date
  if (!d) return ''
  const s = normalizeDateToString(d)
  return s ? s.slice(0, 10) : ''
}
const relatedDeposit = computed(() => {
  if (!isBuy.value) return null
  const tx = props.transaction
  const paId = tx?.portfolio_asset_id
  const assetId = tx?.asset_id
  const portfolioId = tx?.portfolio_id
  if (!paId && !assetId) return null
  const ops = dashboardStore.operations || []
  const origAmt = originalAmount.value
  const origDay = originalDateDay.value
  for (const op of ops) {
    if (!isDepositOperation(op)) continue
    if (paId != null) {
      const opPaId = op.portfolio_asset_id
      if (opPaId != null && opPaId !== paId) continue
    }
    if (assetId != null) {
      const opAssetId = op.asset_id
      if (opAssetId != null && opAssetId !== assetId) continue
    }
    if (portfolioId != null && op.portfolio_id != null && op.portfolio_id !== portfolioId) continue
    const opDay = opDateDay(op)
    if (opDay !== origDay) continue
    const opAmt = Number(op.amount ?? op.amount_rub ?? 0)
    if (Math.abs(opAmt - origAmt) > 0.01) continue
    const opId = op.id ?? op.cash_operation_id ?? op.operation_id
    if (!opId) continue
    return { id: opId, operation_date: editedTx.value?.transaction_date || op.operation_date || op.date, amount: newAmount.value }
  }
  return null
})
const showUpdateDepositOption = computed(() => isBuy.value && hasRelevantChanges.value && relatedDeposit.value != null)
const updateRelatedDeposit = ref(true)

watch(
  () => props.transaction,
  async (newTx, oldTx) => {
    if (!newTx) return

    if (oldTx && newTx?.asset_id !== oldTx?.asset_id) {
      priceHistoryCache.value = null
      minDate.value = null
    }
    
    // Сохраняем оригинальную дату транзакции перед обновлением
    const originalDate = newTx?.transaction_date
    
    // Сохраняем текущую дату из editedTx (пользователь мог её изменить)
    // Приоритет текущей дате, если она есть, иначе используем оригинальную
    const savedDate = editedTx.value?.transaction_date || originalDate
    
    // Обновляем editedTx, но сохраняем дату отдельно
    editedTx.value = { ...newTx }
    
    // Восстанавливаем дату сразу после обновления (нормализуем формат)
    if (savedDate) {
      const normalizedDate = normalizeDateToString(savedDate)
      if (normalizedDate) {
        editedTx.value.transaction_date = normalizedDate
      }
    }

    resolvedAssetMeta.value = newTx.asset_id
      ? await fetchReferenceAssetMeta(newTx.asset_id)
      : null

    const system =
      resolvedAssetMeta.value &&
      (resolvedAssetMeta.value.user_id == null || resolvedAssetMeta.value.is_custom === false)

    if (system && newTx?.asset_id) {
      await loadPriceHistoryForDateRestriction(savedDate || originalDate)
      if (useMarketPrice.value && editedTx.value.transaction_date) {
        await loadMarketPrice(true)
      }
    } else {
      minDate.value = null
    }
  },
  { immediate: true }
)

// Загрузка истории цен для ограничения даты
// originalDate - оригинальная дата транзакции, которую нужно сохранить
async function loadPriceHistoryForDateRestriction(originalDate = null) {
  const assetId = props.transaction?.asset_id
  if (!assetId) return
  
  // Сохраняем текущую дату транзакции (приоритет переданной дате, иначе из editedTx)
  const currentDate = originalDate || editedTx.value?.transaction_date
  
  // Нормализуем формат даты используя утилиту
  const currentDateStr = normalizeDateToString(currentDate)
  
  try {
    isLoadingHistory.value = true
    
    // Используем кеш, если история уже загружена, чтобы не делать повторный запрос
    let prices = priceHistoryCache.value
    if (!prices || prices.length === 0) {
      const priceHistoryResponse = await assetsService.getAssetPriceHistory(
        assetId,
        null,
        null,
        10000
      )
      if (priceHistoryResponse.success && priceHistoryResponse.prices && priceHistoryResponse.prices.length > 0) {
        prices = priceHistoryResponse.prices
        priceHistoryCache.value = prices
      } else {
        prices = []
      }
    }
    
    if (prices && prices.length > 0) {
      const sortedPrices = [...prices].sort((a, b) => {
        const dateA = new Date(a.trade_date)
        const dateB = new Date(b.trade_date)
        return dateA - dateB
      })
      
      if (sortedPrices.length > 0) {
        const firstPriceDate = sortedPrices[0].trade_date
        minDate.value = firstPriceDate
        
        // Корректируем дату только если она действительно раньше первой цены
        // И сохраняем оригинальную дату, если она валидна
        if (currentDateStr) {
          const firstPriceDateObj = new Date(firstPriceDate)
          const currentDateObj = new Date(currentDateStr)
          
          // Нормализуем для сравнения
          currentDateObj.setHours(0, 0, 0, 0)
          firstPriceDateObj.setHours(0, 0, 0, 0)
          
          if (currentDateObj < firstPriceDateObj) {
            // Только если дата действительно раньше первой цены, корректируем её
            editedTx.value.transaction_date = firstPriceDate
          } else {
            // Сохраняем оригинальную дату, если она валидна
            // Не перезаписываем, если дата уже установлена и совпадает
            if (!editedTx.value.transaction_date || editedTx.value.transaction_date !== currentDateStr) {
              editedTx.value.transaction_date = currentDateStr
            }
          }
        }
      }
    } else {
      minDate.value = null
    }
  } catch (e) {
    console.error('Ошибка при загрузке истории цен для ограничения даты:', e)
    minDate.value = null
  } finally {
    isLoadingHistory.value = false
  }
}

// Получение цены актива на дату
async function getAssetPriceOnDate(assetId, targetDate, cachedHistory = null) {
  try {
    const refData = dashboardStore.referenceData
    let assetInfo =
      resolvedAssetMeta.value?.id === assetId ? resolvedAssetMeta.value : null
    if (!assetInfo) {
      assetInfo = await fetchReferenceAssetMeta(assetId)
    }
    const assetTicker = assetInfo?.ticker || null
    
    let priceHistory = cachedHistory || priceHistoryCache.value
    
    if (priceHistory && priceHistory.length > 0) {
      const targetDateNormalized = new Date(targetDate)
      targetDateNormalized.setHours(0, 0, 0, 0)
      
      const sortedPrices = [...priceHistory].sort((a, b) => {
        const dateA = new Date(a.trade_date)
        const dateB = new Date(b.trade_date)
        return dateB - dateA
      })
      
      for (const priceRecord of sortedPrices) {
        const priceDate = new Date(priceRecord.trade_date)
        priceDate.setHours(0, 0, 0, 0)
        
        if (priceDate <= targetDateNormalized) {
          const price = parseFloat(priceRecord.price)
          if (price && price > 0) {
            return price
          }
        }
      }
    }
    
    if (refData && assetInfo?.last_price) {
      const price = parseFloat(assetInfo.last_price)
      if (price && price > 0) return price
    }

    if (assetTicker && refData?.currencies) {
      const currency = refData.currencies.find((c) => c.ticker === assetTicker)
      if (currency?.rate_to_rub) {
        const rate = parseFloat(currency.rate_to_rub)
        if (rate && rate > 0) return rate
      }
      if (currency?.last_price) {
        const p = parseFloat(currency.last_price)
        if (p && p > 0) return p
      }
    }
    
    return null
  } catch (error) {
    console.error('Ошибка при получении цены актива:', error)
    return null
  }
}

// Загрузка рыночной цены
async function loadMarketPrice(silent = false) {
  const assetId = props.transaction?.asset_id
  if (!assetId || !editedTx.value.transaction_date) {
    return false
  }
  
  if (!silent) {
    loadingPrice.value = true
  }
  
  try {
    const marketPrice = await getAssetPriceOnDate(
      assetId,
      editedTx.value.transaction_date,
      priceHistoryCache.value
    )
    
    if (marketPrice && marketPrice > 0) {
      editedTx.value.price = marketPrice
      lastMarketPrice.value = marketPrice
      return true
    }
    
    return false
  } catch (e) {
    console.error('Ошибка при получении рыночной цены:', e)
    return false
  } finally {
    if (!silent) {
      loadingPrice.value = false
    }
  }
}

// Отслеживание изменений тумблера
watch(useMarketPrice, async (newValue) => {
  if (newValue) {
    // При включении загружаем рыночную цену
    await loadMarketPrice(true)
  }
})

// Отслеживание изменений даты
watch(() => editedTx.value.transaction_date, async (newDate, oldDate) => {
  // Валидация: если дата раньше minDate, корректируем её (приоритет валидации)
  if (minDate.value && newDate) {
    const newDateObj = new Date(newDate)
    const minDateObj = new Date(minDate.value)
    if (newDateObj < minDateObj) {
      editedTx.value.transaction_date = minDate.value
      return
    }
  }
  // Загружаем рыночную цену, если тумблер включен
  if (useMarketPrice.value && newDate && newDate !== oldDate) {
    await loadMarketPrice(true)
  }
})

// Отслеживание ручного изменения цены
watch(() => editedTx.value.price, (newPrice, oldPrice) => {
  // Если цена изменена вручную и отличается от последней рыночной цены, выключаем тумблер
  if (useMarketPrice.value && lastMarketPrice.value !== null && Math.abs(newPrice - lastMarketPrice.value) > 0.0001) {
    useMarketPrice.value = false
  }
})

// История цен и рыночная цена загружаются через watch(props.transaction, { immediate: true })
// Дополнительные вызовы при монтировании и открытии модалки не нужны и приводят к дублированию запросов

const error = ref('')

const handleSave = () => {
  error.value = ''
  
  // Проверка для системных активов: дата не должна быть раньше первой цены
  if (isSystemAsset.value && minDate.value && editedTx.value.transaction_date && 
      new Date(editedTx.value.transaction_date) < new Date(minDate.value)) {
    error.value = `Дата транзакции не может быть раньше первой доступной даты: ${minDate.value}`
    return
  }
  
  // Валидация полей
  if (!editedTx.value.quantity || editedTx.value.quantity <= 0) {
    error.value = 'Введите количество'
    return
  }
  
  if (!editedTx.value.price || editedTx.value.price <= 0) {
    error.value = 'Введите цену'
    return
  }
  
  if (!editedTx.value.transaction_date) {
    error.value = 'Выберите дату транзакции'
    return
  }

  const payload = { ...editedTx.value }
  if (showUpdateDepositOption.value && relatedDeposit.value) {
    payload.updateRelatedDeposit = updateRelatedDeposit.value
    payload.relatedDepositOperation = updateRelatedDeposit.value ? {
      id: relatedDeposit.value.id,
      operation_date: relatedDeposit.value.operation_date,
      amount: relatedDeposit.value.amount
    } : null
  }
  emit('save', payload)
  emit('close')
}
</script>

<template>
  <ModalBase :show="visible" title="Редактировать транзакцию" :icon="Edit" :wide="true" @close="$emit('close')">
    <form @submit.prevent="handleSave">
        <div class="form-section">
          <div class="asset-info">
            <TrendingUp :size="18" class="asset-icon" />
            <div>
              <strong>{{ editedTx.asset_name }}</strong>
              <span class="ticker" v-if="editedTx.asset_ticker">({{ editedTx.asset_ticker }})</span>
            </div>
          </div>
        </div>

        <div class="form-section">
          <div class="section-divider"></div>
          <label class="form-label">
            <RefreshCw :size="16" class="label-icon" />
            Тип транзакции
          </label>
          <div class="readonly-value">{{ editedTx.transaction_type }}</div>
        </div>

        <div class="form-section">
          <div class="section-divider"></div>
          
          <!-- Переключатель использования рыночной цены (только для системных активов) -->
          <div v-if="isSystemAsset" class="toggle-wrapper">
            <ToggleSwitch v-model="useMarketPrice" />
            <span class="toggle-label-text">
              Использовать рыночную цену на дату транзакции
            </span>
          </div>
          
          <div class="form-row">
            <div class="form-field">
              <label class="form-label">
                <Hash :size="16" class="label-icon" />
                Количество
              </label>
              <input 
                type="number" 
                v-model.number="editedTx.quantity" 
                min="0"
                step="0.000001" 
                class="form-input" 
                required
              />
              <small class="form-hint" style="margin-top: 4px;">
                Можно вводить до 6 знаков после запятой
              </small>
            </div>
            <div class="form-field">
              <label class="form-label">
                <DollarSign :size="16" class="label-icon" />
                Цена ({{ assetCurrencySymbol || '₽' }})
                <span v-if="loadingPrice" style="margin-left: 8px; color: #3b82f6; display: inline-flex; align-items: center; gap: 4px;">
                  <Loader2 :size="14" class="spinner-icon" />
                  Загрузка...
                </span>
              </label>
              <input 
                type="number" 
                v-model.number="editedTx.price" 
                min="0"
                step="0.000001" 
                class="form-input"
                :disabled="useMarketPrice && loadingPrice"
                required
              />
              <small class="form-hint" style="margin-top: 4px;" v-if="useMarketPrice && isSystemAsset">
                Цена автоматически обновляется при изменении даты
              </small>
              <small class="form-hint" style="margin-top: 4px;">
                Можно вводить до 6 знаков после запятой
              </small>
            </div>
          </div>
          <div class="form-field" style="margin-top: 12px;">
            <label class="form-label">
              <Calendar :size="16" class="label-icon" />
              Дата транзакции
            </label>
            <!-- Используем key для пересоздания компонента после установки minDate, чтобы даты стали тусклыми -->
            <DateInput 
              v-model="editedTx.transaction_date" 
              :min="minDate" 
              :key="`date-input-${minDate || 'no-min'}-${isLoadingHistory}`"
              required
            />
            <small v-if="minDate" class="form-hint" style="margin-top: 4px;">
              Первая доступная дата: {{ minDate }}
            </small>
          </div>
          <!-- Предложение обновить связанную операцию пополнения при изменении даты или суммы -->
          <div v-if="showUpdateDepositOption" class="toggle-wrapper" style="margin-top: 16px;">
            <ToggleSwitch v-model="updateRelatedDeposit" />
            <span class="toggle-label-text">
              Обновить связанную операцию пополнения
              <template v-if="relatedDeposit">
                (дата: {{ newDateDay }}, сумма: {{ newAmount.toFixed(2) }} {{ assetCurrencySymbol }})
              </template>
            </span>
            <small class="form-hint block" style="margin-top: 6px;">
              Найдена операция пополнения с той же суммой и датой; при сохранении у неё обновятся дата и сумма в соответствии с транзакцией.
            </small>
          </div>
        </div>

        <div v-if="error" class="error">{{ error }}</div>

        <div class="form-actions">
          <Button variant="secondary" type="button" @click="$emit('close')" :disabled="saving">Отмена</Button>
          <Button variant="primary" type="submit" :loading="saving">
            <template #icon>
              <Check :size="16" />
            </template>
            Сохранить
          </Button>
        </div>
      </form>
  </ModalBase>
</template>

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

.asset-info {
  padding: 12px 16px;
  background: #f9fafb;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}

.asset-icon {
  color: #6b7280;
  flex-shrink: 0;
  opacity: 0.8;
}

.asset-info strong {
  color: #111827;
  font-weight: 600;
}

.ticker {
  color: #6b7280;
  margin-left: 6px;
  font-size: 13px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  letter-spacing: -0.01em;
}

.label-icon {
  color: #6b7280;
  flex-shrink: 0;
}

.readonly-value {
  padding: 9px 12px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  font-size: 14px;
  background: #f9fafb;
  color: #6b7280;
}

.form-input {
  width: 100%;
  padding: 9px 12px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  font-size: 14px;
  transition: all 0.2s ease;
  background: #fff;
  color: #111827;
  box-sizing: border-box;
  font-family: inherit;
}

.form-input:hover {
  border-color: #d1d5db;
  background: #fafafa;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
  background: #fff;
}

.form-input:disabled {
  background: #f9fafb;
  color: #9ca3af;
  cursor: not-allowed;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-field {
  display: flex;
  flex-direction: column;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 16px;
  margin-top: 8px;
  border-top: 1px solid #f3f4f6;
}

.toggle-wrapper {
  margin-bottom: 12px;
  padding: 8px 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.toggle-label-text {
  font-size: 13px;
  color: #374151;
  font-weight: 500;
}

.form-hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
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

.spinner-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

</style>
