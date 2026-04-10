<template>
  <ModalBase title="Добавить актив" :icon="PlusCircle" :wide="true" @close="$emit('close')">
    <div v-if="saving" class="modal-loading">
      <Loader2 :size="32" class="spinner-icon" />
      <span>Сохраняем...</span>
    </div>

    <form v-else @submit.prevent="submitForm">
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
            <BarChart3 :size="16" class="label-icon" />
            Тип актива
          </label>
          <div class="asset-choice">
            <button
              type="button"
              :class="{ active: assetTypeChoice === 'system' }"
              @click="setAssetTypeChoice('system')"
            >
              <Search :size="16" class="choice-icon" />
              <span>Системный</span>
            </button>
            <button
              type="button"
              :class="{ active: assetTypeChoice === 'custom' }"
              @click="setAssetTypeChoice('custom')"
            >
              <Sparkles :size="16" class="choice-icon" />
              <span>Кастомный</span>
            </button>
          </div>
        </div>

        <!-- Информация об активе -->
        <div class="form-section">
          <div v-if="assetTypeChoice === 'system'" class="asset-search-block">
            <label class="form-label">
              <TrendingUp :size="16" class="label-icon" />
              Актив
            </label>
            <div class="search-wrapper">
              <Search :size="16" class="search-icon" />
              <input
                type="text"
                v-model="searchQuery"
                placeholder="Поиск по названию или тикеру (от 2 символов)..."
                @input="onAssetSearchInput"
                required
                class="form-input search-input"
              />
              <ul
                v-if="searchQuery.trim().length >= 2 && !form.asset_id"
                class="dropdown"
              >
                <li v-if="searchLoading" class="create-new">
                  <Loader2 :size="20" class="empty-icon spinner-icon" />
                  <span>Поиск…</span>
                </li>
                <template v-else>
                  <li
                    v-for="a in searchResults"
                    :key="a.id"
                    @click="selectAsset(a)"
                  >
                    <div class="asset-info-row">
                      <span class="asset-name">{{ a.name }}</span>
                      <span class="asset-ticker">{{ a.ticker || '—' }}</span>
                    </div>
                  </li>
                  <li v-if="searchResults.length === 0" class="create-new">
                    <Search :size="20" class="empty-icon" />
                    <span>Актив не найден. Выберите «Кастомный» для создания нового.</span>
                  </li>
                </template>
              </ul>
            </div>
            <div v-if="form.asset_id" class="selected-asset">
              <CheckCircle2 :size="16" class="check-icon" />
              <span>Выбран: <strong>{{ searchQuery }}</strong></span>
            </div>
          </div>

          <div v-if="assetTypeChoice === 'custom'" class="custom-asset-fields">
            <FormInput
              v-model="form.name"
              label="Название"
              :icon="FileText"
              type="text"
              placeholder="Введите название актива"
              required
            />
            <div class="form-row">
              <div class="form-field">
                <CustomSelect
                  v-model="form.asset_type_id"
                  :options="customAssetTypeOptions"
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
          <!-- Переключатель использования рыночной цены (только для системных активов) -->
          <div v-if="assetTypeChoice === 'system'" class="toggle-wrapper">
            <ToggleSwitch v-model="useMarketPrice" />
            <span class="toggle-label-text">
              Использовать рыночную цену на дату добавления
            </span>
          </div>
          
          <div v-if="assetTypeChoice === 'custom' && isCustomDepositType" class="form-row form-row-single">
            <FormInput
              v-model.number="form.quantity"
              :label="'Сумма вклада (' + (customDepositCurrencySymbol || '₽') + ')'"
              :icon="Hash"
              type="number"
              min="0"
              step="0.01"
              placeholder="0.00"
              hint="Размер первоначального пополнения вклада"
              required
            />
          </div>
          <div v-else class="form-row">
            <FormInput
              v-model.number="form.quantity"
              label="Количество"
              :icon="Hash"
              type="number"
              min="0"
              step="0.000001"
              placeholder="0.000000"
              hint="Количество единиц актива в портфеле"
              required
            />
            <FormInput
              v-model.number="form.average_price"
              :label="'Средняя цена' + (form.asset_id ? ` (${depositCurrencySymbol || '₽'})` : '')"
              :icon="DollarSign"
              :loading-icon="loadingPrice ? Loader2 : null"
              type="number"
              min="0"
              step="0.000001"
              placeholder="0.00"
              :disabled="useMarketPrice && loadingPrice"
              :hint="useMarketPrice && assetTypeChoice === 'system' ? 'Цена автоматически обновляется при изменении даты' : 'Цена за единицу актива'"
              required
            />
          </div>
          <div class="form-field date-field">
            <label class="form-label">
              <Calendar :size="16" class="label-icon" />
              Дата добавления
            </label>
            <DateInput v-model="form.date" :min="minDate" required />
            <small v-if="minDate && assetTypeChoice === 'system'" class="form-hint">
              <CalendarDays :size="12" class="hint-icon" />
              Первая доступная дата: {{ minDate }}
            </small>
          </div>
          
          <!-- Галочка для создания операции пополнения при создании актива с покупкой -->
          <div v-if="form.quantity > 0 && form.average_price > 0" class="toggle-wrapper deposit-toggle">
            <ToggleSwitch v-model="createDepositOperation" />
            <div class="toggle-content">
              <Wallet :size="14" class="toggle-icon" />
              <span class="toggle-label-text">
                Добавить операцию пополнения на сумму покупки ({{ (form.quantity * form.average_price).toFixed(2) }} {{ depositCurrencySymbol }})
              </span>
            </div>
            <small class="form-hint block" style="margin-top: 6px;">Будет создана операция пополнения в валюте актива ({{ depositCurrencyTicker }})</small>
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
  </ModalBase>
</template>

<script setup>
import { reactive, ref, computed, watch } from 'vue'
import { normalizeDateToString } from '../../utils/date'
import ModalBase from './ModalBase.vue'
import { 
  Check, 
  PlusCircle, 
  Loader2, 
  BarChart3, 
  Search, 
  Sparkles, 
  TrendingUp, 
  CheckCircle2, 
  FileText, 
  Hash, 
  DollarSign, 
  Calendar, 
  CalendarDays,
  Wallet
} from 'lucide-vue-next'
import { Button, ToggleSwitch, DateInput } from '../base'
import CustomSelect from '../base/CustomSelect.vue'
import FormInput from '../base/FormInput.vue'
import assetsService from '../../services/assetsService'
import {
  searchReferenceAssets,
  fetchReferenceAssetMeta,
} from '../../services/referenceService'
import { useDashboardStore } from '../../stores/dashboard.store'
import { useTransactionsStore } from '../../stores/transactions.store'
import { getCurrencySymbol } from '../../utils/currencySymbols'

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
const searchResults = ref([])
const searchLoading = ref(false)
const selectedAssetMeta = ref(null)
let searchDebounceTimer = null
let searchRequestSeq = 0

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

/** «Другое» / синонимы — в конце списка типов */
function isCatchAllCustomAssetTypeName(name) {
  const n = (name || '').trim().toLowerCase()
  return n === 'другое' || n === 'прочее' || n === 'иное'
}

/** Кастомные типы: алфавит (ru), категория «прочее» последней — единообразно при любом числе типов */
const customAssetTypeOptions = computed(() => {
  const list = (props.referenceData?.asset_types || []).filter((t) => t.is_custom)
  const catchAll = list.filter((t) => isCatchAllCustomAssetTypeName(t.name))
  const main = list.filter((t) => !isCatchAllCustomAssetTypeName(t.name))
  main.sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru'))
  return [...main, ...catchAll]
})

/** Справочный id типа «Вклад» (см. init.sql); имя в БД может быть «Вклад» или «Вклады» */
const DEPOSIT_ASSET_TYPE_ID = 10

function normId(id) {
  if (id === null || id === undefined || id === '') return null
  const n = Number(id)
  return Number.isFinite(n) ? n : null
}

function isDepositAssetTypeLabel(name) {
  const n = (name || '').trim().toLowerCase()
  if (!n) return false
  return n === 'вклад' || n === 'вклады' || n.startsWith('вклад')
}

const isCustomDepositType = computed(() => {
  if (assetTypeChoice.value !== 'custom' || form.asset_type_id == null || form.asset_type_id === '') return false
  const typeId = normId(form.asset_type_id)
  if (typeId === null) return false
  if (typeId === DEPOSIT_ASSET_TYPE_ID) return true
  const t = props.referenceData?.asset_types?.find((x) => normId(x.id) === typeId)
  return t ? isDepositAssetTypeLabel(t.name) : false
})

const customDepositCurrencyTicker = computed(() => {
  if (!form.currency || !props.referenceData?.currencies) return 'RUB'
  const cid = normId(form.currency)
  const c = props.referenceData.currencies.find((x) => normId(x.id) === cid)
  return c?.ticker || 'RUB'
})
const customDepositCurrencySymbol = computed(() => getCurrencySymbol(customDepositCurrencyTicker.value))

// Валюта для текста про операцию пополнения (системный актив или кастомный вклад по выбранной валюте)
const depositCurrencyTicker = computed(() => {
  if (isCustomDepositType.value) {
    return customDepositCurrencyTicker.value
  }
  if (!form.asset_id) return 'RUB'
  const meta = selectedAssetMeta.value
  if (!meta || meta.id !== form.asset_id) return 'RUB'
  if (meta.quote_ticker) return meta.quote_ticker
  if (meta.quote_asset_id != null && props.referenceData?.currencies) {
    const c = props.referenceData.currencies.find((x) => x.id === meta.quote_asset_id)
    return c?.ticker || 'RUB'
  }
  return 'RUB'
})
const depositCurrencySymbol = computed(() => getCurrencySymbol(depositCurrencyTicker.value))

watch(
  () => [assetTypeChoice.value, form.asset_type_id],
  () => {
    if (isCustomDepositType.value) {
      form.average_price = 1
    }
  },
  { immediate: true }
)

function onAssetSearchInput() {
  form.asset_id = null
  selectedAssetMeta.value = null
}

const resetAssetFields = () => {
    clearTimeout(searchDebounceTimer)
    form.asset_id = null
    form.name = ''
    form.ticker = ''
    form.asset_type_id = null
    form.currency = null
    searchQuery.value = ''
    searchResults.value = []
    searchLoading.value = false
    selectedAssetMeta.value = null
}

const setAssetTypeChoice = (choice) => {
    assetTypeChoice.value = choice
    resetAssetFields() // Сбрасываем все поля актива при переключении
    
    // Устанавливаем обязательные значения по умолчанию для кастомного, если это 'custom'
    if (choice === 'custom') {
        const opts = customAssetTypeOptions.value
        if (opts.length > 0) {
            form.asset_type_id = opts[0].id
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
      if (isCustomDepositType.value) {
        form.average_price = 1
      }
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

watch(searchQuery, () => {
  if (form.asset_id) return
  clearTimeout(searchDebounceTimer)
  const q = searchQuery.value.trim()
  if (q.length < 2) {
    searchResults.value = []
    searchLoading.value = false
    return
  }
  searchLoading.value = true
  searchDebounceTimer = setTimeout(async () => {
    const seq = ++searchRequestSeq
    try {
      const items = await searchReferenceAssets(q, 25)
      if (seq === searchRequestSeq) searchResults.value = items
    } catch (e) {
      console.error(e)
      if (seq === searchRequestSeq) searchResults.value = []
    } finally {
      if (seq === searchRequestSeq) searchLoading.value = false
    }
  }, 280)
})

const selectAsset = async (asset) => {
  selectedAssetMeta.value = asset
  form.asset_id = asset.id
  // Устанавливаем name, ticker и currency для системного актива, 
  // чтобы передать их на backend (если это требуется) и для отображения в поле поиска
  form.name = asset.name
  form.ticker = asset.ticker
  form.currency = asset.quote_asset_id ?? null
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
    const refData = dashboardStore.referenceData
    let assetInfo =
      selectedAssetMeta.value?.id === assetId ? selectedAssetMeta.value : null
    if (!assetInfo) {
      assetInfo = await fetchReferenceAssetMeta(assetId)
    }
    const assetTicker = assetInfo?.ticker || null
    
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

.form-section {
  margin-bottom: 24px;
}

.form-section:last-of-type {
  margin-bottom: 20px;
}


.form-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  letter-spacing: -0.01em;
}

.label-icon {
  color: #6b7280;
  flex-shrink: 0;
}

.loading-icon {
  color: #3b82f6;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
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

.asset-search-block {
  position: relative;
  display: flex;
  flex-direction: column;
}

.asset-search-block > .form-label {
  margin-bottom: 10px;
  margin-top: 0;
}

.asset-search-block > .search-wrapper {
  margin-bottom: 0;
  margin-top: 0;
}

.asset-search-block > .selected-asset {
  margin-top: 10px;
  margin-bottom: 0;
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
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  border-left: 3px solid transparent;
}

.asset-info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
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
  padding: 16px 14px;
  cursor: default;
  text-align: center;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-direction: column;
}

.empty-icon {
  color: #d1d5db;
  opacity: 0.6;
}

.selected-asset {
  margin-top: 10px;
  padding: 10px 14px;
  font-size: 13px;
  color: #166534;
  background: linear-gradient(to right, #f0fdf4, #ecfdf5);
  border: 1.5px solid #86efac;
  border-radius: 10px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.1);
}

.check-icon {
  color: #10b981;
  flex-shrink: 0;
}

.asset-choice {
  display: flex;
  gap: 6px;
  background: #f9fafb;
  padding: 4px;
  border-radius: 12px;
  border: 1.5px solid #e5e7eb;
}

.asset-choice button {
  flex: 1;
  padding: 12px 16px;
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
  gap: 8px;
}

.choice-icon {
  color: inherit;
  flex-shrink: 0;
}

.asset-choice button.active {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  color: #2563eb;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.15), 0 0 0 1.5px rgba(59, 130, 246, 0.2);
  transform: translateY(-1px);
}

.asset-choice button.active .choice-icon {
  color: #2563eb;
}

.asset-choice button:not(.active):hover {
  background: #f3f4f6;
  color: #374151;
}

.form-input {
  width: 100%;
  padding: 11px 14px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  font-size: 14px;
  transition: all 0.2s ease;
  background: #fff;
  color: #111827;
  box-sizing: border-box;
  font-family: inherit;
}

.form-input::placeholder {
  color: #9ca3af;
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

.date-field {
  margin-top: 4px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-row-single {
  grid-template-columns: 1fr;
}

.form-field {
  display: flex;
  flex-direction: column;
}

.custom-asset-fields {
  gap: 10px;
  display: flex;
  flex-direction: column;
}

.custom-asset-fields > FormInput {
  margin-bottom: 12px;
  margin-top: 0;
}

.custom-asset-fields > .form-row {
  margin-top: 0;
  margin-bottom: 0;
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

.toggle-wrapper.deposit-toggle {
  margin-top: 16px;
  padding: 12px 14px;
  background: linear-gradient(to right, #eff6ff, #f0f9ff);
  border: 1.5px solid #bfdbfe;
  border-radius: 10px;
}

.toggle-content {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.toggle-icon {
  color: #3b82f6;
  flex-shrink: 0;
}

.toggle-label-text {
  font-size: 13px;
  color: #374151;
  font-weight: 500;
  flex: 1;
}

.toggle-amount {
  font-size: 13px;
  font-weight: 700;
  color: #2563eb;
  background: white;
  padding: 4px 10px;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.2);
}

.form-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  font-size: 12px;
  color: #6b7280;
}

.hint-icon {
  color: #9ca3af;
  flex-shrink: 0;
}

.form-hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

</style>
