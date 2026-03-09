<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>Добавить актив</h2>
        <button class="close-btn" @click="$emit('close')" aria-label="Закрыть">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <div v-if="saving" class="modal-loading">
        <div class="spinner"></div>
        <span>Сохраняем...</span>
      </div>

      <form v-else @submit.prevent="submitForm" class="form-content">
        <!-- Портфель -->
        <div class="form-section">
          <CustomSelect
            v-model="form.portfolio_id"
            :options="portfolios"
            label="Портфель"
            placeholder="Выберите портфель"
            :show-empty-option="false"
            option-label="name"
            option-value="id"
            :min-width="'100%'"
            :flex="'none'"
          />
        </div>

        <!-- Тип актива -->
        <div class="form-section">
          <label class="form-label">
            <span class="label-icon">📊</span>
            Тип актива
          </label>
          <div class="asset-choice">
            <button
              type="button"
              :class="{ active: assetTypeChoice === 'system' }"
              @click="setAssetTypeChoice('system')"
            >
              <span class="choice-icon">🔍</span>
              Системный
            </button>
            <button
              type="button"
              :class="{ active: assetTypeChoice === 'custom' }"
              @click="setAssetTypeChoice('custom')"
            >
              <span class="choice-icon">✨</span>
              Кастомный
            </button>
          </div>
        </div>

        <!-- Информация об активе -->
        <div class="form-section">
          <div class="section-divider"></div>
          <div v-if="assetTypeChoice === 'system'" class="asset-search-block">
            <label class="form-label">
              <span class="label-icon">📈</span>
              Актив
            </label>
            <div class="search-wrapper">
              <span class="search-icon">🔍</span>
              <input
                type="text"
                v-model="searchQuery"
                placeholder="Поиск по названию или тикеру..."
                @input="form.asset_id = null"
                required
                class="form-input search-input"
              />
              <ul v-if="searchQuery && !form.asset_id" class="dropdown">
                <li
                  v-for="a in filteredAssets"
                  :key="a.id"
                  @click="selectAsset(a)"
                >
                  <span class="asset-name">{{ a.name }}</span>
                  <span class="asset-ticker">{{ a.ticker || '—' }}</span>
                </li>
                <li class="create-new" v-if="filteredAssets.length === 0">
                  <span class="empty-icon">🔍</span>
                  Актив не найден. Выберите "Кастомный" для создания нового.
                </li>
              </ul>
            </div>
            <div v-if="form.asset_id" class="selected-asset">
              <span class="check-icon">✓</span>
              <span>Выбран: <strong>{{ searchQuery }}</strong></span>
            </div>
          </div>

          <div v-if="assetTypeChoice === 'custom'" class="custom-asset-fields">
            <div class="form-row">
              <div class="form-field">
                <label class="form-label">
                  <span class="label-icon">📝</span>
                  Название
                </label>
                <input v-model="form.name" type="text" required class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-field">
                <CustomSelect
                  v-model="form.asset_type_id"
                  :options="referenceData.asset_types.filter(t => t.is_custom)"
                  label="Тип"
                  placeholder="Выберите тип"
                  :show-empty-option="false"
                  option-label="name"
                  option-value="id"
                  :min-width="'100%'"
                  :flex="'none'"
                />
              </div>
              <div class="form-field">
                <CustomSelect
                  v-model="form.currency"
                  :options="fiatCurrencies"
                  label="Валюта"
                  placeholder="Выберите валюту"
                  :show-empty-option="false"
                  option-label="ticker"
                  option-value="id"
                  :min-width="'100%'"
                  :flex="'none'"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Параметры покупки -->
        <div class="form-section">
          <div class="section-divider"></div>
          
          <!-- Переключатель использования рыночной цены (только для системных активов) -->
          <div v-if="assetTypeChoice === 'system'" class="toggle-wrapper">
            <ToggleSwitch v-model="useMarketPrice" />
            <span class="toggle-label-text">
              Использовать рыночную цену на дату добавления
            </span>
          </div>
          
          <div class="form-row">
            <div class="form-field">
              <label class="form-label">
                <span class="label-icon">🔢</span>
                Количество
              </label>
              <input v-model.number="form.quantity" type="number" min="0" step="0.000001" required class="form-input" />
              <small class="form-hint" style="margin-top: 4px;">
                Можно вводить до 6 знаков после запятой
              </small>
            </div>
            <div class="form-field">
              <label class="form-label">
                <span class="label-icon">💰</span>
                Средняя цена
                <span v-if="loadingPrice" style="margin-left: 8px; color: #3b82f6;">⏳ Загрузка...</span>
              </label>
              <input 
                v-model.number="form.average_price" 
                type="number" 
                min="0" 
                step="0.000001" 
                required 
                class="form-input"
                :disabled="useMarketPrice && loadingPrice"
              />
              <small class="form-hint" style="margin-top: 4px;" v-if="useMarketPrice && assetTypeChoice === 'system'">
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
              Дата добавления
            </label>
            <DateInput v-model="form.date" :min="minDate" required />
            <small v-if="minDate && assetTypeChoice === 'system'" class="form-hint" style="margin-top: 4px;">
              Первая доступная дата: {{ minDate }}
            </small>
          </div>
          
          <!-- Галочка для создания операции пополнения при создании актива с покупкой -->
          <div v-if="form.quantity > 0 && form.average_price > 0" class="toggle-wrapper" style="margin-top: 16px;">
            <ToggleSwitch v-model="createDepositOperation" />
            <span class="toggle-label-text">
              Добавить операцию пополнения на сумму покупки ({{ (form.quantity * form.average_price).toFixed(2) }} ₽)
            </span>
          </div>
        </div>

        <div class="form-actions">
          <Button variant="secondary" type="button" @click="$emit('close')">
            Отмена
          </Button>
          <Button variant="primary" type="submit" :loading="saving">
            <template #icon>
              <Check :size="16" />
            </template>
            Добавить актив
          </Button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch } from 'vue'
import { normalizeDateToString } from '../../utils/date'
import { Check } from 'lucide-vue-next'
import { Button, ToggleSwitch, DateInput } from '../base'
import CustomSelect from '../base/CustomSelect.vue'
import assetsService from '../../services/assetsService'
import { useDashboardStore } from '../../stores/dashboard.store'
import { useTransactionsStore } from '../../stores/transactions.store'

const dashboardStore = useDashboardStore()
const transactionsStore = useTransactionsStore()

const props = defineProps({
  onSave: Function, // функция сохранения из родителя
  referenceData: Object,
  portfolios: Object
})

const emit = defineEmits(['close'])

const initialFormState = {
  portfolio_id: null,
  asset_id: null,
  asset_type_id: null,
  name: '',
  ticker: '',
  currency: null,
  quantity: 0,
  average_price: 0,
  date: normalizeDateToString(new Date()) || ''
}

const form = reactive({ ...initialFormState })
const saving = ref(false)           // индикатор сохранения
const searchQuery = ref("")
const assetTypeChoice = ref("system") // 'system' или 'custom' - по умолчанию системный

// Использование рыночной цены для системных активов
const useMarketPrice = ref(true) // Переключатель для автоматической загрузки рыночной цены (включен по умолчанию)
const lastMarketPrice = ref(null) // Последняя загруженная рыночная цена
const loadingPrice = ref(false) // Состояние загрузки рыночной цены
const priceHistoryCache = ref(null) // Кэш истории цен актива
const isLoadingHistory = ref(false) // Флаг для предотвращения двойной загрузки истории
const minDate = ref(null) // Минимальная дата (первая цена в истории)

// Галочка для создания операции пополнения на сумму покупки (по умолчанию включена)
const createDepositOperation = ref(true)

// Фильтруем валюты: исключаем криптовалюты (asset_type_id = 6), оставляем только фиатные валюты (asset_type_id = 7)
const fiatCurrencies = computed(() => {
  if (!props.referenceData?.currencies) return []
  return props.referenceData.currencies.filter(c => c.asset_type_id === 7)
})

const resetAssetFields = () => {
    form.asset_id = null
    form.name = ''
    form.ticker = ''
    form.asset_type_id = null
    form.currency = null
    searchQuery.value = ''
}

const setAssetTypeChoice = (choice) => {
    assetTypeChoice.value = choice
    resetAssetFields() // Сбрасываем все поля актива при переключении
    
    // Устанавливаем обязательные значения по умолчанию для кастомного, если это 'custom'
    if (choice === 'custom') {
        // Устанавливаем первый кастомный тип и первую валюту, если они есть
        const firstCustomType = props.referenceData.asset_types.find(t => t.is_custom)
        if (firstCustomType) {
            form.asset_type_id = firstCustomType.id
        }
        if (fiatCurrencies.value.length > 0) {
            form.currency = fiatCurrencies.value[0].id
        }
    }
}


const submitForm = async () => {
  // Проверка для системного актива: должен быть выбран
  if (assetTypeChoice.value === 'system' && !form.asset_id) {
    alert('Пожалуйста, выберите системный актив из списка.');
    return;
  }
  
  // Проверка для системного актива: дата не должна быть раньше первой цены
  if (assetTypeChoice.value === 'system' && minDate.value && form.date && new Date(form.date) < new Date(minDate.value)) {
    alert(`Дата добавления не может быть раньше первой доступной даты: ${minDate.value}`);
    return;
  }
  
  // Для кастомного актива: заполняем asset_id как null и убираем ticker
  if (assetTypeChoice.value === 'custom') {
      form.asset_id = null;
      form.ticker = null; // Тикер не нужен для кастомных активов
  }
  
  if (!props.onSave) return
  saving.value = true
  try {
    // Создаем актив с флагом создания операции пополнения
    await props.onSave({ 
      ...form,
      create_deposit_operation: createDepositOperation.value && form.quantity > 0 && form.average_price > 0
    })  // ждём промис от родителя
    
    emit('close')
  } catch (err) {
    console.error(err)
    alert('Ошибка при сохранении')
  } finally {
    saving.value = false
  }
}

const filteredAssets = computed(() => {
  if (!searchQuery.value) return props.referenceData.assets
  const q = searchQuery.value.toLowerCase()

  return props.referenceData.assets.filter(a =>
    a.name.toLowerCase().includes(q) ||
    (a.ticker || "").toLowerCase().includes(q)
  )
})

const selectAsset = async (asset) => {
  form.asset_id = asset.id
  // Устанавливаем name, ticker и currency для системного актива, 
  // чтобы передать их на backend (если это требуется) и для отображения в поле поиска
  form.name = asset.name
  form.ticker = asset.ticker
  form.currency = asset.currency
  // Отображаем выбранное значение в поле поиска
  searchQuery.value = `${asset.name} (${asset.ticker || '—'})`
  
  // Очищаем кэш истории цен при выборе нового актива
  priceHistoryCache.value = null
  minDate.value = null
  lastMarketPrice.value = null
  
  // Загружаем историю цен для системного актива
  if (asset.user_id === null || asset.is_custom === false) {
    await loadPriceHistoryForDateRestriction()
    // Загружаем рыночную цену по умолчанию, если тумблер включен
    if (useMarketPrice.value && form.date) {
      await loadPriceHistory()
      await loadMarketPrice(true)
    }
  }
}

// Функция для получения цены актива на дату
// Если передан cachedHistory, использует его вместо загрузки из API
async function getAssetPriceOnDate(assetId, targetDate, cachedHistory = null) {
  try {
    // Сначала пытаемся получить информацию об активе из referenceData
    const refData = dashboardStore.referenceData
    let assetTicker = null
    let assetInfo = null
    
    if (refData?.assets) {
      assetInfo = refData.assets.find(a => a.id === assetId)
      if (assetInfo && assetInfo.ticker) {
        assetTicker = assetInfo.ticker
      }
    }
    
    let priceHistory = cachedHistory
    
    // Если история не передана, но есть в глобальном кэше, используем её
    if (!priceHistory && priceHistoryCache.value && priceHistoryCache.value.length > 0) {
      priceHistory = priceHistoryCache.value
    }
    
    // Загружаем историю цен только если она не передана в кэше и нет в глобальном кэше
    // Это fallback для обратной совместимости (не должно вызываться при использовании переключателя)
    if (!priceHistory) {
      // Получаем историю цен актива
      // Используем дату на день позже, чтобы включить саму дату операции
      const targetDateObj = new Date(targetDate)
      targetDateObj.setHours(23, 59, 59, 999) // Конец дня, чтобы включить саму дату
      const endDateStr = normalizeDateToString(targetDateObj) || '' // YYYY-MM-DD
      
      const priceHistoryResponse = await assetsService.getAssetPriceHistory(
        assetId,
        null, // start_date - не ограничиваем
        endDateStr, // end_date - до даты операции включительно
        1000 // Увеличиваем лимит, чтобы получить больше записей
      )
      
      if (priceHistoryResponse.success && priceHistoryResponse.prices) {
        priceHistory = priceHistoryResponse.prices
      }
    }
    
    if (priceHistory && priceHistory.length > 0) {
      // Нормализуем целевую дату для сравнения
      const targetDateNormalized = new Date(targetDate)
      targetDateNormalized.setHours(0, 0, 0, 0)
      
      // Сортируем по дате (от новых к старым)
      const sortedPrices = [...priceHistory].sort((a, b) => {
        const dateA = new Date(a.trade_date)
        const dateB = new Date(b.trade_date)
        return dateB - dateA
      })
      
      // Ищем цену на точную дату или ближайшую предыдущую
      for (const priceRecord of sortedPrices) {
        const priceDate = new Date(priceRecord.trade_date)
        priceDate.setHours(0, 0, 0, 0)
        
        // Проверяем, что дата цены <= целевой даты
        if (priceDate <= targetDateNormalized) {
          const price = parseFloat(priceRecord.price)
          if (price && price > 0) {
            return price
          }
        }
      }
    }
    
    // Если цена не найдена в истории, пытаемся получить из referenceData
    if (refData) {
      // Сначала пробуем получить из assets
      if (refData.assets && assetInfo) {
        if (assetInfo.last_price) {
          const price = parseFloat(assetInfo.last_price)
          if (price && price > 0) {
            return price
          }
        }
      }
      
      // Если это валюта/криптовалюта, пробуем получить курс из currencies
      if (assetTicker && refData.currencies) {
        const currency = refData.currencies.find(c => c.ticker === assetTicker)
        if (currency) {
          // Для валют/криптовалют используем rate_to_rub как цену в рублях
          if (currency.rate_to_rub) {
            const rate = parseFloat(currency.rate_to_rub)
            if (rate && rate > 0) {
              return rate
            }
          }
          // Если rate_to_rub нет, пробуем получить из asset_last_currency_prices через assets
          if (refData.assets) {
            const currencyAsset = refData.assets.find(a => a.ticker === assetTicker)
            if (currencyAsset && currencyAsset.last_price) {
              const price = parseFloat(currencyAsset.last_price)
              if (price && price > 0) {
                return price
              }
            }
          }
        }
      }
    }
    
    // Если ничего не найдено, возвращаем null (не используем fallback 1)
    // Это позволит системе показать ошибку или запросить цену вручную
    return null
  } catch (error) {
    console.error('Ошибка при получении цены актива:', error)
    return null
  }
}

// Функция для загрузки истории цен актива (вызывается один раз при включении переключателя)
async function loadPriceHistory() {
  if (!form.asset_id) {
    return false
  }
  
  // Если история уже загружена для этого актива, не загружаем повторно
  if (priceHistoryCache.value && priceHistoryCache.value.length > 0) {
    return true
  }
  
  // Если уже идет загрузка истории, не запускаем повторную загрузку
  if (isLoadingHistory.value) {
    // Ждем завершения текущей загрузки
    while (isLoadingHistory.value) {
      await new Promise(resolve => setTimeout(resolve, 50))
    }
    // После завершения проверяем, загрузилась ли история
    return priceHistoryCache.value && priceHistoryCache.value.length > 0
  }
  
  try {
    isLoadingHistory.value = true
    loadingPrice.value = true
    
    // Загружаем полную историю цен актива (без ограничения по дате)
    const priceHistoryResponse = await assetsService.getAssetPriceHistory(
      form.asset_id,
      null, // start_date - не ограничиваем
      null, // end_date - не ограничиваем, загружаем всю историю
      10000 // Большой лимит для получения всей истории
    )
    
    if (priceHistoryResponse.success && priceHistoryResponse.prices) {
      // Сохраняем историю в кэш
      priceHistoryCache.value = priceHistoryResponse.prices
      return true
    }
    
    return false
  } catch (e) {
    console.error('Ошибка при загрузке истории цен:', e)
    return false
  } finally {
    isLoadingHistory.value = false
    loadingPrice.value = false
  }
}

// Функция для загрузки истории цен и установки ограничения даты
async function loadPriceHistoryForDateRestriction() {
  if (!form.asset_id) {
    return
  }
  
  try {
    isLoadingHistory.value = true
    
    // Загружаем полную историю цен актива
    const priceHistoryResponse = await assetsService.getAssetPriceHistory(
      form.asset_id,
      null, // start_date - не ограничиваем
      null, // end_date - не ограничиваем, загружаем всю историю
      10000 // Большой лимит для получения всей истории
    )
    
    if (priceHistoryResponse.success && priceHistoryResponse.prices && priceHistoryResponse.prices.length > 0) {
      // Сохраняем историю в кэш
      priceHistoryCache.value = priceHistoryResponse.prices
      
      // Находим первую дату с ценой (самую раннюю)
      const sortedPrices = [...priceHistoryResponse.prices].sort((a, b) => {
        const dateA = new Date(a.trade_date)
        const dateB = new Date(b.trade_date)
        return dateA - dateB
      })
      
      if (sortedPrices.length > 0) {
        const firstPriceDate = sortedPrices[0].trade_date
        minDate.value = firstPriceDate
        
        // Если текущая дата раньше первой цены, обновляем её
        if (form.date && new Date(form.date) < new Date(firstPriceDate)) {
          form.date = firstPriceDate
        }
      }
    } else {
      // Если истории цен нет, сбрасываем ограничение
      minDate.value = null
    }
  } catch (e) {
    console.error('Ошибка при загрузке истории цен для ограничения даты:', e)
    minDate.value = null
  } finally {
    isLoadingHistory.value = false
  }
}

// Функция для получения рыночной цены на дату транзакции и заполнения поля цены
async function loadMarketPrice(silent = false) {
  if (!form.asset_id) {
    return false
  }
  
  if (!form.date) {
    return false
  }
  
  if (!silent) {
    loadingPrice.value = true
  }
  
  try {
    // Используем кэшированную историю цен, если она есть
    const marketPrice = await getAssetPriceOnDate(
      form.asset_id, 
      form.date, 
      priceHistoryCache.value
    )
    
    if (marketPrice && marketPrice > 0) {
      form.average_price = marketPrice
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

// Автоматическая загрузка истории цен и рыночной цены при включении переключателя
watch(useMarketPrice, async (newValue, oldValue) => {
  // Загружаем историю цен и цену при включении переключателя
  // Только для системных активов
  if (newValue && assetTypeChoice.value === 'system' && form.asset_id && form.date) {
    // Загружаем историю цен один раз при включении переключателя (если еще не загружена)
    const historyLoaded = await loadPriceHistory()
    
    // Если история загружена или уже была в кэше, загружаем цену на текущую дату
    if (historyLoaded) {
      await loadMarketPrice(true) // silent = true, чтобы не показывать ошибки при автоматической загрузке
    }
  }
  // При выключении переключателя НЕ очищаем кэш - сохраняем для повторного использования
})

// Отслеживание ручного изменения цены
watch(() => form.average_price, (newPrice, oldPrice) => {
  // Если цена изменена вручную и отличается от последней рыночной цены, выключаем тумблер
  if (useMarketPrice.value && lastMarketPrice.value !== null && 
      Math.abs(newPrice - lastMarketPrice.value) > 0.0001 && 
      oldPrice !== undefined) {
    useMarketPrice.value = false
  }
})

// Автоматическое обновление цены при изменении даты, если переключатель включен
watch(() => form.date, async (newDate, oldDate) => {
  // Обновляем цену только если переключатель включен, выбран системный актив и дата действительно изменилась
  if (useMarketPrice.value && assetTypeChoice.value === 'system' && form.asset_id && newDate && newDate !== oldDate) {
    // Используем кэшированную историю цен для быстрого поиска цены
    await loadMarketPrice(true) // silent = true, чтобы не показывать ошибки при автоматической загрузке
  }
}, { immediate: false })

// Очистка кэша истории цен при изменении актива
watch(() => form.asset_id, async (newAssetId, oldAssetId) => {
  if (newAssetId !== oldAssetId) {
    priceHistoryCache.value = null
    minDate.value = null
    // Если переключатель включен и актив изменился, загружаем новую историю
    if (useMarketPrice.value && assetTypeChoice.value === 'system' && newAssetId && form.date) {
      loadPriceHistory().then(() => {
        loadMarketPrice(true)
      })
    }
  }
})

// Сброс переключателя при переключении типа актива
watch(assetTypeChoice, (newChoice) => {
  if (newChoice === 'custom') {
    useMarketPrice.value = false
    priceHistoryCache.value = null
    minDate.value = null
  }
})

// Установка начального portfolio_id при загрузке
if (props.portfolios.length > 0) {
    form.portfolio_id = props.portfolios[0].id
}

// Инициализация выбора типа актива для полей кастомного актива
setAssetTypeChoice('system') 
</script>

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

.modal-content {
  background: white;
  width: 100%;
  max-width: 520px;
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

.form-content::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
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
  to { transform: rotate(360deg); }
}

.asset-search-block {
  position: relative;
}

.search-wrapper {
  position: relative;
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  font-size: 14px;
  color: #9ca3af;
  z-index: 1;
}

.search-input {
  padding-left: 36px !important;
}

.dropdown {
  position: absolute;
  background: white;
  border: 1px solid #e5e7eb;
  width: 100%;
  max-height: 180px;
  overflow-y: auto;
  z-index: 10;
  margin-top: 4px;
  padding: 4px 0;
  list-style: none;
  border-radius: 10px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.12), 0 4px 10px rgba(0,0,0,0.08);
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dropdown li {
  padding: 10px 14px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-left: 3px solid transparent;
}

.dropdown li:hover {
  background: #f3f4f6;
  border-left-color: #3b82f6;
  padding-left: 11px;
}

.asset-name {
  font-weight: 500;
  color: #111827;
  font-size: 13px;
}

.asset-ticker {
  font-size: 12px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.dropdown .create-new {
  color: #9ca3af;
  padding: 12px 14px;
  cursor: default;
  text-align: center;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex-direction: column;
}

.empty-icon {
  font-size: 20px;
  opacity: 0.5;
}

.selected-asset {
  margin-top: 8px;
  padding: 8px 12px;
  font-size: 12px;
  color: #166534;
  background: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 8px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}

.check-icon {
  width: 16px;
  height: 16px;
  background: #10b981;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}

.asset-choice {
  display: flex;
  gap: 8px;
  background: #f9fafb;
  padding: 4px;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
}

.asset-choice button {
  flex: 1;
  padding: 10px 14px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-weight: 600;
  font-size: 13px;
  color: #6b7280;
  transition: all 0.2s ease;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.choice-icon {
  font-size: 14px;
}

.asset-choice button.active {
  background: white;
  color: #2563eb;
  box-shadow: 0 2px 4px rgba(0,0,0,0.08), 0 0 0 1px rgba(59,130,246,0.1);
  transform: translateY(-1px);
}

.asset-choice button:not(.active):hover {
  background: #f3f4f6;
  color: #374151;
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

.custom-asset-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
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
