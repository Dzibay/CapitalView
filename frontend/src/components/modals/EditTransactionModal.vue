<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { Check } from 'lucide-vue-next'
import { Button, DateInput, ToggleSwitch } from '../base'
import CustomSelect from '../base/CustomSelect.vue'
import assetsService from '../../services/assetsService'
import { useDashboardStore } from '../../stores/dashboard.store'
import { normalizeDateToString } from '../../utils/date'

const props = defineProps({
  transaction: Object,
  visible: Boolean
})

const emit = defineEmits(['close', 'save'])

const dashboardStore = useDashboardStore()

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
  const refData = dashboardStore.referenceData
  if (refData?.assets) {
    const asset = refData.assets.find(a => a.id === assetId)
    return asset && (asset.user_id === null || asset.is_custom === false)
  }
  return false
})

watch(
  () => props.transaction,
  async (newTx) => {
    if (!newTx) return
    
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
    
    // Загружаем историю цен при изменении транзакции
    if (isSystemAsset.value && newTx?.asset_id) {
      await loadPriceHistoryForDateRestriction(savedDate || originalDate)
      // Загружаем рыночную цену на дату транзакции
      if (useMarketPrice.value && editedTx.value.transaction_date) {
        await loadMarketPrice(true)
      }
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
    
    const priceHistoryResponse = await assetsService.getAssetPriceHistory(
      assetId,
      null,
      null,
      10000
    )
    
    if (priceHistoryResponse.success && priceHistoryResponse.prices && priceHistoryResponse.prices.length > 0) {
      priceHistoryCache.value = priceHistoryResponse.prices
      
      const sortedPrices = [...priceHistoryResponse.prices].sort((a, b) => {
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
    let assetTicker = null
    let assetInfo = null
    
    if (refData?.assets) {
      assetInfo = refData.assets.find(a => a.id === assetId)
      if (assetInfo && assetInfo.ticker) {
        assetTicker = assetInfo.ticker
      }
    }
    
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
    
    if (refData) {
      if (refData.assets && assetInfo && assetInfo.last_price) {
        const price = parseFloat(assetInfo.last_price)
        if (price && price > 0) {
          return price
        }
      }
      
      if (assetTicker && refData.currencies) {
        const currency = refData.currencies.find(c => c.ticker === assetTicker)
        if (currency?.rate_to_rub) {
          const rate = parseFloat(currency.rate_to_rub)
          if (rate && rate > 0) {
            return rate
          }
        }
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

// Загрузка при монтировании и при открытии модалки
onMounted(async () => {
  if (isSystemAsset.value && props.transaction?.asset_id) {
    const originalDate = props.transaction?.transaction_date
    await loadPriceHistoryForDateRestriction(originalDate)
    if (useMarketPrice.value && editedTx.value.transaction_date) {
      await loadMarketPrice(true)
    }
  }
})

// Загрузка истории цен при открытии модалки
watch(() => props.visible, async (isVisible) => {
  if (isVisible && isSystemAsset.value && props.transaction?.asset_id) {
    const originalDate = props.transaction?.transaction_date
    await loadPriceHistoryForDateRestriction(originalDate)
    if (useMarketPrice.value && editedTx.value.transaction_date) {
      await loadMarketPrice(true)
    }
  }
}, { immediate: true })

const handleSave = () => {
  // Проверка для системных активов: дата не должна быть раньше первой цены
  if (isSystemAsset.value && minDate.value && editedTx.value.transaction_date && 
      new Date(editedTx.value.transaction_date) < new Date(minDate.value)) {
    alert(`Дата транзакции не может быть раньше первой доступной даты: ${minDate.value}`)
    return
  }
  
  emit('save', editedTx.value)
  emit('close')
}
</script>

<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>Редактировать транзакцию</h2>
        <button class="close-btn" @click="$emit('close')" aria-label="Закрыть">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      
      <form @submit.prevent="handleSave" class="form-content">
        <div class="form-section">
          <div class="asset-info">
            <span class="asset-icon">📈</span>
            <div>
              <strong>{{ editedTx.asset_name }}</strong>
            </div>
          </div>
        </div>

        <div class="form-section">
          <div class="section-divider"></div>
          <label class="form-label">
            <span class="label-icon">🔄</span>
            Тип
          </label>
          <CustomSelect
            v-model="editedTx.transaction_type"
            :options="[
              { value: 'Покупка', label: 'Покупка' },
              { value: 'Продажа', label: 'Продажа' }
            ]"
            placeholder="Выберите тип"
            :show-empty-option="false"
            option-label="label"
            option-value="value"
            :min-width="'100%'"
            :flex="'none'"
          />
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
                <span class="label-icon">🔢</span>
                Количество
              </label>
              <input type="number" v-model.number="editedTx.quantity" step="0.000001" class="form-input" />
              <small class="form-hint" style="margin-top: 4px;">
                Можно вводить до 6 знаков после запятой
              </small>
            </div>
            <div class="form-field">
              <label class="form-label">
                <span class="label-icon">💰</span>
                Цена (₽)
                <span v-if="loadingPrice" style="margin-left: 8px; color: #3b82f6;">⏳ Загрузка...</span>
              </label>
              <input 
                type="number" 
                v-model.number="editedTx.price" 
                step="0.000001" 
                class="form-input"
                :disabled="useMarketPrice && loadingPrice"
              />
              <small class="form-hint" style="margin-top: 4px;" v-if="useMarketPrice && isSystemAsset">
                Цена автоматически обновляется при изменении даты
              </small>
              <small class="form-hint" style="margin-top: 4px;">
                Можно вводить до 6 знаков после запятой
              </small>
            </div>
          </div>
          <div class="form-field">
            <label class="form-label">
              <span class="label-icon">📅</span>
              Дата транзакции
            </label>
            <!-- Используем key для пересоздания компонента после установки minDate, чтобы даты стали тусклыми -->
            <DateInput 
              v-model="editedTx.transaction_date" 
              :min="minDate" 
              :key="`date-input-${minDate || 'no-min'}-${isLoadingHistory}`"
            />
            <small v-if="minDate" class="form-hint" style="margin-top: 4px;">
              Первая доступная дата: {{ minDate }}
            </small>
          </div>
        </div>

        <div class="form-actions">
          <Button variant="secondary" type="button" @click="$emit('close')">Отмена</Button>
          <Button variant="primary" type="submit" :loading="saving">
            <template #icon>
              <Check :size="16" />
            </template>
            Сохранить
          </Button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
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
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal {
  background: white;
  border-radius: 20px;
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
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
  font-size: 18px;
  opacity: 0.8;
}

.asset-info strong {
  color: #111827;
  font-weight: 600;
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
  font-size: 14px;
  opacity: 0.8;
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

</style>
