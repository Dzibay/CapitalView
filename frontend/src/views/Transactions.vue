<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useDashboardStore } from '../stores/dashboard.store'
import { useTransactionsStore } from '../stores/transactions.store'
import { useContextMenu } from '../composables/useContextMenu'
import EditTransactionModal from '../components/modals/EditTransactionModal.vue'
import ContextMenu from '../components/base/ContextMenu.vue'
import CustomSelect from '../components/base/CustomSelect.vue'
import { ToggleSwitch, PeriodFilter, Tooltip } from '../components/base'
import { Search, SlidersHorizontal, ChevronDown, RotateCcw, MoreHorizontal, Trash2 } from 'lucide-vue-next'
import CvPageHead from '../cabinet/ui/CvPageHead.vue'
import CvKpiStrip from '../cabinet/ui/CvKpiStrip.vue'
import CvSegmented from '../cabinet/ui/CvSegmented.vue'
import OpsActivityWidget from '../cabinet/operations/OpsActivityWidget.vue'
import { OP_GROUPS, TX_ORDER, OP_ORDER, groupOf } from '../cabinet/operations/opKinds'
import { money, moneyIn, plural } from '../cabinet/format'
import { payoutAmountToRub } from '../utils/currencyRatesToRub'
import { formatOperationAmount } from '../utils/formatCurrency'
import { normalizeDateToString, formatDateForDisplay } from '../utils/date'
import operationsService from '../services/operationsService'

const dashboardStore = useDashboardStore()
const transactionsStore = useTransactionsStore()
const route = useRoute()

const {
  viewMode,
  selectedAsset,
  assetSearch,
  recentAssets,
  selectedPortfolio,
  selectedType,
  selectedCurrency,
  periodPreset,
  startDate,
  endDate,
  globalSearch,
  showPeriodTrack,
} = storeToRefs(transactionsStore)

// Полные списки транзакций и операций: всегда запрашиваем при входе на страницу,
// чтобы не показывать пустую вкладку «Операции» после сбоя одного из запросов или устаревший кэш.
onMounted(() => {
  dashboardStore.fetchTransactionsAndOperationsInBackground()
})

// Транзакции и операции — единственный источник: dashboard store
const transactions = computed(() => dashboardStore.transactions || [])
const operations = computed(() => dashboardStore.operations || [])

const referenceData = computed(() => dashboardStore.referenceData || {})

const tickerByAssetName = computed(() => {
  const map = new Map()
  for (const t of transactions.value) {
    const name = t.asset_name
    if (name && t.ticker != null && t.ticker !== '' && !map.has(name)) {
      map.set(name, t)
    }
  }
  return map
})

// Обертки для совместимости
const deleteTransactions = async (transaction_ids) => {
  await transactionsStore.deleteTransactions(transaction_ids)
}

const deleteOperations = async (operation_ids) => {
  await transactionsStore.deleteOperations(operation_ids)
}

// --- списки для фильтров ---
// Оптимизировано: кэшируем уникальные значения
const assets = computed(() => {
  const tx = transactions.value
  if (!tx.length) return []
  const assetSet = new Set()
  for (const t of tx) {
    if (t.asset_name) assetSet.add(t.asset_name)
  }
  return Array.from(assetSet)
})

// Список активов для операций
const operationsAssets = computed(() => {
  const ops = operations.value
  if (!ops.length) return []
  const assetSet = new Set()
  for (const op of ops) {
    if (op.asset_name) assetSet.add(op.asset_name)
  }
  return Array.from(assetSet)
})

const portfolios = computed(() => {
  const data = viewMode.value === 'transactions' ? transactions.value : operations.value
  if (!data.length) return []
  const portfolioMap = new Map()
  for (const item of data) {
    const portfolioId = item.portfolio_id
    const portfolioName = item.portfolio_name
    if (portfolioId && !portfolioMap.has(portfolioId)) {
      portfolioMap.set(portfolioId, { id: portfolioId, name: portfolioName })
    }
  }
  return Array.from(portfolioMap.values())
})

const txTypes = computed(() => {
  const tx = transactions.value
  if (!tx.length) return []
  const typeSet = new Set()
  for (const t of tx) {
    if (t.transaction_type) typeSet.add(t.transaction_type)
  }
  return Array.from(typeSet)
})

const operationTypes = computed(() => {
  const ops = operations.value
  if (!ops.length) return []
  const typeSet = new Set()
  for (const op of ops) {
    if (op.operation_type) typeSet.add(op.operation_type)
  }
  return Array.from(typeSet)
})

/** Самая ранняя дата среди транзакций и операций — левая граница шкалы периода */
const earliestDataDate = computed(() => {
  let best = ''
  const consider = (raw) => {
    const s = normalizeDateToString(raw)
    if (!s) return
    if (!best || s < best) best = s
  }
  for (const tx of transactions.value) consider(tx.transaction_date)
  for (const op of operations.value) consider(op.operation_date)
  return best
})

// Фильтры хранятся в transactionsStore для сохранения при навигации

// отфильтрованные транзакции/операции
const filteredTransactions = ref([])
const filteredOperations = ref([])

// выделенные транзакции
const selectedTxIds = ref([])
// выделенные операции
const selectedOpIds = ref([])

// главный чекбокс
const allSelected = ref(false)
const allOperationsSelected = ref(false)

// модальное окно
const showEditModal = ref(false)
const currentTransaction = ref(null)

// контекстное меню
const { openMenu } = useContextMenu()

// Карточный вид на планшетах и мобильных (как в PortfolioTree)
const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1200)
const isCardView = computed(() => windowWidth.value <= 1024)
const isMobilePeriod = computed(() => windowWidth.value <= 768)

// Опции периода для выпадающего списка на мобильных
const periodOptions = [
  { value: 'today', label: 'Сегодня' },
  { value: 'week', label: 'Неделя' },
  { value: 'month', label: 'Месяц' },
  { value: 'year', label: 'Год' },
  { value: 'all', label: 'Всё время' },
  { value: 'custom', label: 'Период...' }
]
const updateWindowWidth = () => { windowWidth.value = window.innerWidth }
onMounted(() => {
  window.addEventListener('resize', updateWindowWidth)
})
onUnmounted(() => {
  window.removeEventListener('resize', updateWindowWidth)
})

const handleEditTransaction = (transaction) => {
  openEditModal(transaction)
}

const handleDeleteTransaction = (transaction) => {
  if (transaction && transaction.transaction_id) {
    deleteOne(transaction.transaction_id)
  }
}

const handleDeleteOperation = (operation) => {
  if (operation && (operation.cash_operation_id || operation.id)) {
    deleteOneOperation(operation.cash_operation_id || operation.id)
  }
}

// --- ВСПОМОГАТЕЛЬНОЕ: нормализация типа ---
const isSellTransaction = (tx) =>
  tx?.transaction_type_id === 2 || normalizeType(tx?.transaction_type) === 'sell'

/** Реализованная прибыль (₽) для продажи; null — не рендерим ValueChange под суммой */
const txSellRealizedPnlNumber = (tx) => {
  if (!isSellTransaction(tx)) return null
  const v = Number(tx?.realized_pnl)
  return Number.isNaN(v) ? null : v
}

const normalizeType = (type) => {
  const t = (type || '').toString().toLowerCase()
  if (t.includes('покуп') || t.includes('buy')) return 'buy'
  if (t.includes('прод') || t.includes('sell')) return 'sell'
  if (t.includes('див') || t.includes('div')) return 'dividend'
  if (t.includes('купон') || t.includes('coupon')) return 'coupon'
  // SQL: Amortization → «Амортизация»; виджет выплат раньше подставлял «Погашение»
  if (t.includes('аморт') || t.includes('amort') || t.includes('погаш')) return 'amortization'
  if (t.includes('налог') || t.includes('tax')) return 'tax'
  if (t.includes('комисс') || t.includes('commission') || t.includes('commision')) return 'commission'
  if (t.includes('ввод') || t.includes('пополн') || t.includes('депозит') || t.includes('deposit')) return 'deposit'
  if (t.includes('вывод') || t.includes('withdraw')) return 'withdraw'
  return 'other'
}

// Функция для получения даты в формате YYYY-MM-DD по локальному времени пользователя
const getLocalYMD = (dateObj) => {
  return normalizeDateToString(dateObj) || ''
}

// --- ПРЕСЕТЫ ПЕРИОДОВ ---
const setPeriodPreset = (preset) => {
  periodPreset.value = preset
  if (preset === 'custom') return

  const now = new Date()
  let start = null

  if (preset === 'today') {
    start = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  } else if (preset === 'week') {
    start = new Date(now)
    start.setDate(start.getDate() - 7)
  } else if (preset === 'month') {
    start = new Date(now)
    start.setMonth(start.getMonth() - 1)
  } else if (preset === 'quarter') {
    start = new Date(now)
    start.setMonth(start.getMonth() - 3)
  } else if (preset === 'year') {
    start = new Date(now)
    start.setFullYear(start.getFullYear() - 1)
  } else if (preset === 'all') {
    startDate.value = ''
    endDate.value = ''
    return
  }

  if (start) {
    startDate.value = getLocalYMD(start)
    endDate.value = getLocalYMD(new Date())
  }
}

// --- формат даты ---
const formatDate = formatDateForDisplay

const COMMISSION_EPS = 1e-8

// Сумма операции как в БД (get_cash_operations): без пересчёта с комиссией на фронте. Комиссия — в tooltip.
const getOperationAmount = (op, { rubOnly = false } = {}) => {
  if (rubOnly || selectedCurrency.value === 'RUB') {
    return Number(op.amount_rub ?? op.amountRub ?? op.amount) || 0
  }
  return Number(op.amount) || 0
}

// Нормализует код валюты (защита от некорректных значений типа "RUB000UTSTOM")
const normalizeCurrencyTicker = (ticker) => {
  if (!ticker || typeof ticker !== 'string') return 'RUB'
  
  // Берем только первые 3 символа и приводим к верхнему регистру
  const normalized = ticker.trim().substring(0, 3).toUpperCase()
  
  // Список валидных кодов валют
  const validCurrencyCodes = ['RUB', 'USD', 'EUR', 'GBP', 'CNY', 'JPY', 'BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL']
  if (validCurrencyCodes.includes(normalized)) {
    return normalized
  }
  
  // Если не валидный код, пробуем найти в referenceData
  const refData = referenceData.value
  if (refData && refData.currencies) {
    const currency = refData.currencies.find(c => {
      const cTicker = c.ticker || ''
      return cTicker.toUpperCase() === normalized || cTicker.toUpperCase().startsWith(normalized)
    })
    if (currency && currency.ticker) {
      return currency.ticker.toUpperCase()
    }
  }
  
  // Если ничего не найдено, возвращаем нормализованный код (первые 3 символа)
  return normalized
}

// Получаем валюту для отображения операции
const getOperationCurrency = (op) => {
  if (selectedCurrency.value === 'RUB') {
    return 'RUB'
  } else {
    // Нормализуем валюту для корректного отображения
    const originalCurrency = op.currency_ticker || 'RUB'
    return normalizeCurrencyTicker(originalCurrency)
  }
}

/** Текст tooltip с комиссией; пустая строка — подсказку не показываем */
const getOperationCommissionTooltipContent = (op) => {
  const comm = Number(op.commission)
  const commRubRaw = op.commission_rub
  const commRub =
    commRubRaw != null && commRubRaw !== '' ? Number(commRubRaw) : NaN
  const hasCommNative = Number.isFinite(comm) && Math.abs(comm) > COMMISSION_EPS
  const hasCommRub = Number.isFinite(commRub) && Math.abs(commRub) > COMMISSION_EPS
  if (!hasCommNative && !hasCommRub) return ''

  if (selectedCurrency.value === 'RUB') {
    if (hasCommRub) {
      return `Комиссия: ${formatOperationAmount(Math.abs(commRub), 'RUB')}`
    }
    const cur = normalizeCurrencyTicker(op.currency_ticker || 'RUB')
    return `Комиссия: ${formatOperationAmount(Math.abs(comm), cur)}`
  }

  const cur = normalizeCurrencyTicker(op.currency_ticker || 'RUB')
  if (hasCommNative) {
    let s = `Комиссия: ${formatOperationAmount(Math.abs(comm), cur)}`
    if (hasCommRub && cur !== 'RUB') {
      s += `\nВ рублях: ${formatOperationAmount(Math.abs(commRub), 'RUB')}`
    }
    return s
  }
  return `Комиссия: ${formatOperationAmount(Math.abs(commRub), 'RUB')}`
}

// --- фильтр активов для дропа ---
const filteredAssetsList = computed(() => {
  const base = assets.value
  if (!assetSearch.value) return base

  const q = assetSearch.value.toLowerCase()
  return base.filter(a => a?.toLowerCase().includes(q))
})

// Фильтр активов для операций
const filteredOperationsAssetsList = computed(() => {
  const base = operationsAssets.value
  if (!assetSearch.value) return base

  const q = assetSearch.value.toLowerCase()
  return base.filter(a => a?.toLowerCase().includes(q))
})

// Тикер для подсказки в фильтре: из загруженных транзакций (поле ticker в API)
const getAssetMeta = (name) => {
  if (!name) return null
  return tickerByAssetName.value.get(name) || null
}

// Экранирование HTML для защиты от XSS
const escapeHtml = (str) => {
  if (str == null) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

// подсветка совпадения в названии актива (с экранированием для защиты от XSS)
const highlightMatch = (text) => {
  if (!assetSearch.value) return escapeHtml(text || '')
  const t = String(text || '')
  const q = assetSearch.value
  const idx = t.toLowerCase().indexOf(q.toLowerCase())
  if (idx === -1) return escapeHtml(t)
  const before = escapeHtml(t.slice(0, idx))
  const match = escapeHtml(t.slice(idx, idx + q.length))
  const after = escapeHtml(t.slice(idx + q.length))
  return `${before}<mark>${match}</mark>${after}`
}

// выбор актива из списка
const selectAssetFilter = (name) => {
  selectedAsset.value = name
  assetSearch.value = name

  // обновляем список последних активов
  recentAssets.value = [
    name,
    ...recentAssets.value.filter(a => a !== name)
  ].slice(0, 5)

  applyFilter()
}

// очистка выбранного актива при ручном вводе
watch(assetSearch, (newVal) => {
  if (newVal !== selectedAsset.value) {
    selectedAsset.value = ''
  }
})

const normalizeFilterList = (v) => {
  if (Array.isArray(v)) return v.filter((x) => x != null && x !== '')
  if (v == null || v === '') return []
  return [v]
}

/** Совпадение по типу: одна и та же суть на русском/англ. и разные подписи (Амортизация vs Погашение). */
const matchesAnyTypeFilter = (itemType, typeFilters) => {
  if (!typeFilters.length) return true
  const slug = normalizeType(itemType)
  return typeFilters.some((f) => normalizeType(f) === slug)
}

// --- ГЛАВНЫЙ ФИЛЬТР ---
// Оптимизировано: ранний выход из проверок для лучшей производительности
const applyFilter = () => {
  const assetFilter = selectedAsset.value
  const portfolioNames = normalizeFilterList(selectedPortfolio.value)
  const typeFilters = normalizeFilterList(selectedType.value)
  const term = globalSearch.value.trim().toLowerCase()
  const hasTerm = term.length > 0

  let start = null
  let end = null

  if (periodPreset.value === 'custom') {
    start = startDate.value ? new Date(startDate.value) : null
    end = endDate.value ? new Date(endDate.value) : null
  } else {
    if (startDate.value) start = new Date(startDate.value)
    if (endDate.value) end = new Date(endDate.value)
  }

  if (end) {
    end.setHours(23, 59, 59, 999)
  }

  // Предвычисляем форматированные строки для глобального поиска только если нужно
  const txList = transactions.value
  filteredTransactions.value = txList.filter(tx => {
    // Быстрые проверки с ранним выходом
    if (assetFilter && tx.asset_name !== assetFilter) return false
    if (portfolioNames.length > 0 && !portfolioNames.includes(tx.portfolio_name)) return false
    if (!matchesAnyTypeFilter(tx.transaction_type, typeFilters)) return false

    // Период (только если заданы даты)
    if (start || end) {
      const txDate = new Date(tx.transaction_date)
      if (start && txDate < start) return false
      if (end && txDate > end) return false
    }

    // Глобальный поиск (только если задан)
    if (hasTerm) {
      // Оптимизированная проверка без создания массива и join
      const searchableText = `${tx.asset_name || ''} ${tx.portfolio_name || ''} ${tx.transaction_type || ''} ${tx.quantity || ''} ${tx.price || ''} ${formatDate(tx.transaction_date)}`.toLowerCase()
      if (!searchableText.includes(term)) return false
    }

    return true
  })

  // Фильтрация операций
  if (viewMode.value === 'operations') {
    const opsList = operations.value
    filteredOperations.value = opsList.filter(op => {
      if (portfolioNames.length > 0 && !portfolioNames.includes(op.portfolio_name)) return false

      if (!matchesAnyTypeFilter(op.operation_type, typeFilters)) return false
      
      // Фильтр по активу (если указан)
      if (assetFilter && op.asset_name && op.asset_name !== assetFilter) return false
      if (assetFilter && !op.asset_name) return false // Если фильтр по активу, но у операции нет актива - исключаем

      // Период
      if (start || end) {
        const opDate = new Date(op.operation_date)
        if (start && opDate < start) return false
        if (end && opDate > end) return false
      }

      // Глобальный поиск по сумме как в БД (amount_rub / amount)
      if (hasTerm) {
        const opAmount = getOperationAmount(op)
        const searchableText = `${op.asset_name || ''} ${op.portfolio_name || ''} ${op.operation_type || ''} ${opAmount || ''} ${getOperationCurrency(op) || ''} ${formatDate(op.operation_date)}`.toLowerCase()
        if (!searchableText.includes(term)) return false
      }

      return true
    })
  }

  selectedTxIds.value = []
  allSelected.value = false
}

const resetFilters = () => {
  transactionsStore.resetFilters()
  applyFilter()
}

const parseQuarterRange = (quarterKey) => {
  const m = quarterKey.match(/^(\d{4})-Q([1-4])$/)
  if (!m) return null
  const year = parseInt(m[1], 10)
  const q = parseInt(m[2], 10)
  const startMonth = (q - 1) * 3
  return {
    start: new Date(year, startMonth, 1),
    end: new Date(year, startMonth + 3, 0)
  }
}

const firstQuery = (v) => (Array.isArray(v) ? v[0] : v)

/** Один или несколько opType в query (график выплат: дивиденды/купоны/погашение) */
const normalizeOpTypesFromQuery = (raw) => {
  if (raw == null || raw === '') return []
  if (Array.isArray(raw)) {
    return raw.map((x) => String(x).trim()).filter((s) => s.length > 0)
  }
  const s = String(raw).trim()
  return s.length > 0 ? [s] : []
}

/** Диплинк с графика выплат: view=operations, month|quarter, opType (строка или повторяющиеся ключи) */
const applyRouteFromQuery = () => {
  const q = route.query
  let touched = false

  const view = firstQuery(q.view)
  if (view === 'operations') {
    viewMode.value = 'operations'
    touched = true
  }

  const opTypes = normalizeOpTypesFromQuery(q.opType)
  if (opTypes.length > 0) {
    selectedType.value = opTypes
    touched = true
  }

  const month = firstQuery(q.month)
  if (typeof month === 'string' && /^\d{4}-\d{2}$/.test(month)) {
    const [y, mo] = month.split('-').map((n) => parseInt(n, 10))
    const start = new Date(y, mo - 1, 1)
    const end = new Date(y, mo, 0)
    periodPreset.value = 'custom'
    startDate.value = getLocalYMD(start)
    endDate.value = getLocalYMD(end)
    touched = true
  } else {
    const quarter = firstQuery(q.quarter)
    if (typeof quarter === 'string' && /^\d{4}-Q[1-4]$/.test(quarter)) {
      const range = parseQuarterRange(quarter)
      if (range) {
        periodPreset.value = 'custom'
        startDate.value = getLocalYMD(range.start)
        endDate.value = getLocalYMD(range.end)
        touched = true
      }
    } else {
      const year = firstQuery(q.year)
      if (typeof year === 'string' && /^\d{4}$/.test(year)) {
        const y = parseInt(year, 10)
        const start = new Date(y, 0, 1)
        const end = new Date(y, 11, 31)
        periodPreset.value = 'custom'
        startDate.value = getLocalYMD(start)
        endDate.value = getLocalYMD(end)
        touched = true
      }
    }
  }

  if (touched) {
    applyFilter()
  }
}

watch(
  () => route.query,
  () => applyRouteFromQuery(),
  { immediate: true, deep: true }
)

// следим за обновлением транзакций
watch(transactions, () => {
  // при первой загрузке ставим дефолтный пресет
  if (!startDate.value && !endDate.value && periodPreset.value !== 'all') {
    setPeriodPreset(periodPreset.value)
  }
  applyFilter()
  // Очищаем выделение при обновлении транзакций
  selectedTxIds.value = []
  allSelected.value = false
}, { immediate: true })

// следим за обновлением операций
watch(operations, () => {
  if (viewMode.value === 'operations') {
    applyFilter()
  }
}, { immediate: true })

// следим за изменением режима просмотра
watch(viewMode, () => {
  applyFilter()
})

// фильтры, которые сразу триггерят пересчёт
watch(
  [selectedPortfolio, selectedType, globalSearch, periodPreset],
  () => {
    applyFilter()
  }
)

watch([startDate, endDate], () => {
  if (periodPreset.value === 'custom') {
    applyFilter()
  }
})

// выбор всех транзакций
const toggleAll = () => {
  if (allSelected.value) {
    selectedTxIds.value = filteredTransactions.value.map(tx => tx.transaction_id)
  } else {
    selectedTxIds.value = []
  }
}

// выбор всех операций
const toggleAllOperations = () => {
  if (allOperationsSelected.value) {
    selectedOpIds.value = filteredOperations.value.map(op => op.cash_operation_id || op.id)
  } else {
    selectedOpIds.value = []
  }
}

watch(selectedTxIds, () => {
  allSelected.value =
    selectedTxIds.value.length > 0 &&
    selectedTxIds.value.length === filteredTransactions.value.length
})

watch(selectedOpIds, () => {
  allOperationsSelected.value =
    selectedOpIds.value.length > 0 &&
    selectedOpIds.value.length === filteredOperations.value.length
})

// удаление выбранных транзакций
const deleteSelected = () => {
  if (selectedTxIds.value.length &&
      confirm(`Вы уверены, что хотите удалить ${selectedTxIds.value.length} транзакций?`)) {
    deleteTransactions(selectedTxIds.value)
    selectedTxIds.value = []
    allSelected.value = false
  }
}

// удаление выбранных операций
const deleteSelectedOperations = () => {
  if (selectedOpIds.value.length &&
      confirm(`Вы уверены, что хотите удалить ${selectedOpIds.value.length} операций?`)) {
    deleteOperations(selectedOpIds.value)
    selectedOpIds.value = []
    allOperationsSelected.value = false
  }
}

// удалить одну транзакцию
const deleteOne = (txId) => {
  if (confirm('Удалить эту транзакцию?')) {
    deleteTransactions([txId])
  }
}

// удалить одну операцию
const deleteOneOperation = (opId) => {
  if (confirm('Удалить эту операцию?')) {
    deleteOperations([opId])
  }
}

// модалка
const openEditModal = (tx) => {
  // Копируем транзакцию и преобразуем дату в формат YYYY-MM-DD для DateInput
  const txCopy = { ...tx }
  if (txCopy.transaction_date) {
    const normalizedDate = normalizeDateToString(txCopy.transaction_date)
    if (normalizedDate) {
      txCopy.transaction_date = normalizedDate
    }
  }
  currentTransaction.value = txCopy
  showEditModal.value = true
}

const handleSaveEdit = async (newTx) => {
  const originalTx = transactions.value.find(t =>
    (t.transaction_id || t.id) === (newTx.transaction_id || newTx.id)
  )

  if (!originalTx) {
    console.error('Оригинальная транзакция не найдена')
    return
  }

  // Для обновления через operations/apply-updates нужен operation_id cash_operations,
  // который уже возвращается в get_transactions как cash_operation_id.
  const txOperationId = originalTx.cash_operation_id || originalTx.operation_id
  if (!txOperationId) {
    console.error('Не найден cash_operation_id у транзакции для update через operations')
    return
  }

  const newDate = normalizeDateToString(newTx.transaction_date || originalTx.transaction_date)
  if (!newDate) {
    console.error('Некорректная новая дата транзакции')
    return
  }

  // Для update_operations_batch.sql используется поле amount как "payment" (abs),
  // а знак cash_operation выставит apply_operations_batch.
  const newQuantity = parseFloat(newTx.quantity) || 0
  const newPrice = parseFloat(newTx.price) || 0
  const payment = Math.abs(newQuantity * newPrice)

  const updates = [
    {
      operation_id: txOperationId,
      operation_date: newDate,
      amount: payment,
      quantity: newQuantity,
      price: newPrice,
    }
  ]

  // Если в модалке пользователь включил обновление пополнения — обновляем deposit cash_operation в том же apply.
  if (newTx.updateRelatedDeposit && newTx.relatedDepositOperation?.id) {
    const dep = newTx.relatedDepositOperation
    updates.push({
      operation_id: dep.id,
      operation_date: normalizeDateToString(dep.operation_date) || newDate,
      amount: parseFloat(dep.amount) || 0,
    })
  }

  await operationsService.updateOperationsBatch(updates)

  await dashboardStore.reloadDashboard(false)
  await dashboardStore.fetchTransactionsAndOperationsInBackground()

  showEditModal.value = false
}

// --- SUMMARY по отфильтрованным ---
const summary = computed(() => {
  const res = {
    total: 0,
    byType: {}
  }

  if (viewMode.value === 'transactions') {
    for (const tx of filteredTransactions.value) {
      const value = Number(tx.quantity || 0) * Number(tx.price || 0)
      const slug = normalizeType(tx.transaction_type)

      res.total += value
      if (!res.byType[slug]) {
        res.byType[slug] = { label: tx.transaction_type, value: 0 }
      }
      res.byType[slug].value += value
    }
  } else {
    // Для операций суммируем по типам (рубли, amount_rub из БД)
    for (const op of filteredOperations.value) {
      const value = getOperationAmount(op, { rubOnly: true })
      const slug = normalizeType(op.operation_type)

      res.total += Math.abs(value)
      if (!res.byType[slug]) {
        res.byType[slug] = { label: op.operation_type, value: 0 }
      }
      res.byType[slug].value += Math.abs(value)
    }
  }

  // округляем
  res.total = Math.round(res.total * 100) / 100
  for (const k in res.byType) {
    res.byType[k].value = Math.round(res.byType[k].value * 100) / 100
  }

  return res
})

// --- КАЛЬКУЛЯТОР ДЛЯ ОПЕРАЦИЙ ---
const calculatorFormula = ref([]) // Массив элементов формулы: [{ type: 'operation'|'operator', value: 'Депозит'|'+'|'-', label: 'Депозит'|'+'|'-' }]

// Добавление элемента в формулу
const addToFormula = (type, value, label) => {
  calculatorFormula.value.push({ type, value, label })
}

// Удаление элемента из формулы
const removeFromFormula = (index) => {
  calculatorFormula.value.splice(index, 1)
}

// Очистка формулы
const clearFormula = () => {
  calculatorFormula.value = []
}

// Вычисление результата формулы
const calculatorResult = computed(() => {
  if (calculatorFormula.value.length === 0) return 0
  
  let result = null
  let nextOperator = '+'
  
  for (let i = 0; i < calculatorFormula.value.length; i++) {
    const item = calculatorFormula.value[i]
    
    if (item.type === 'operator') {
      // Сохраняем оператор для следующей операции
      nextOperator = item.value
    } else if (item.type === 'operation') {
      // Находим сумму для этого типа операции из отфильтрованных данных
      const typeSum = getOperationTypeSum(item.value)
      
      // Если это первая операция, просто присваиваем значение
      if (result === null) {
        result = typeSum
      } else {
        // Применяем сохраненный оператор
        if (nextOperator === '+') {
          result += typeSum
        } else if (nextOperator === '-') {
          result -= typeSum
        }
        // Сбрасываем оператор после применения
        nextOperator = '+'
      }
    }
  }
  
  return result !== null ? Math.round(result * 100) / 100 : 0
})

// Получение суммы по типу операции из отфильтрованных данных (рубли, amount_rub)
const getOperationTypeSum = (operationType) => {
  let sum = 0
  for (const op of filteredOperations.value) {
    if (op.operation_type === operationType) {
      sum += Math.abs(getOperationAmount(op, { rubOnly: true }))
    }
  }
  return sum
}

// Суммы покупок и продаж для транзакций
const transactionsSummary = computed(() => {
  let buySum = 0
  let sellSum = 0
  
  for (const tx of filteredTransactions.value) {
    const value = Number(tx.quantity || 0) * Number(tx.price || 0)
    const normalized = normalizeType(tx.transaction_type)
    
    if (normalized === 'buy') {
      buySum += value
    } else if (normalized === 'sell') {
      sellSum += value
    }
  }
  
  return {
    buy: Math.round(buySum * 100) / 100,
    sell: Math.round(sellSum * 100) / 100
  }
})

// Показывать блок сумм между фильтрами и таблицей
const showSumsSummary = ref(false)

const showMobileFilters = ref(false)

const activeFilterCount = computed(() => {
  let count = 0
  if (selectedAsset.value) count++
  if (normalizeFilterList(selectedPortfolio.value).length > 0) count++
  if (normalizeFilterList(selectedType.value).length > 0) count++
  if (periodPreset.value && periodPreset.value !== 'all') count++
  return count
})

const periodFilterLabel = computed(() => {
  const labels = { today: 'Сегодня', week: 'Неделя', month: 'Месяц', quarter: 'Квартал', year: 'Год' }
  if (periodPreset.value === 'custom') {
    return `${formatDate(startDate.value)} — ${formatDate(endDate.value)}`
  }
  return labels[periodPreset.value] || periodPreset.value
})

// ── вид страницы в стиле дашборда ──────────────────────────────────────────
const VIEW_OPTIONS = [
  { value: 'transactions', label: 'Сделки' },
  { value: 'operations', label: 'Движение денег' },
]
const isTx = computed(() => viewMode.value === 'transactions')

const txValue = (tx) => Number(tx.quantity || 0) * Number(tx.price || 0)
/** сумма сделки в ₽ по курсу справочника; без курса — в валюте сделки */
const txRub = (tx) => {
  const v = txValue(tx)
  return payoutAmountToRub(v, tx.currency_ticker || 'RUB', referenceData.value) ?? v
}
const ymOf = (raw) => (normalizeDateToString(raw) || '').slice(0, 7)

const activityRows = computed(() =>
  isTx.value
    ? filteredTransactions.value
        .map((tx) => ({ ym: ymOf(tx.transaction_date), group: groupOf(normalizeType(tx.transaction_type)), value: Math.abs(txRub(tx)) }))
        .filter((r) => r.group === 'buy' || r.group === 'sell')
    : filteredOperations.value.map((op) => ({
        ym: ymOf(op.operation_date),
        group: groupOf(normalizeType(op.operation_type)),
        value: Math.abs(getOperationAmount(op, { rubOnly: true })),
      })),
)

const groupStats = computed(() => {
  const s = {}
  for (const r of activityRows.value) {
    const g = (s[r.group] ||= { sum: 0, n: 0 })
    g.sum += r.value
    g.n += 1
  }
  return s
})

const realizedPnl = computed(() => filteredTransactions.value.reduce((s, tx) => s + (txSellRealizedPnlNumber(tx) || 0), 0))

const countTx = (n) => `${n} ${plural(n, 'сделка', 'сделки', 'сделок')}`
const countOp = (n) => `${n} ${plural(n, 'операция', 'операции', 'операций')}`

const kpis = computed(() => {
  const g = (k) => groupStats.value[k] || { sum: 0, n: 0 }
  const f = (v) => money(v)
  if (isTx.value) {
    const buy = g('buy')
    const sell = g('sell')
    const pnl = realizedPnl.value
    return [
      { key: 'buy', label: 'Куплено', value: buy.sum, format: f, note: countTx(buy.n) },
      { key: 'sell', label: 'Продано', value: sell.sum, format: f, note: countTx(sell.n) },
      { key: 'pnl', label: 'Результат продаж', value: pnl, format: (v) => money(v, { sign: true }), tone: pnl > 0 ? 'up' : pnl < 0 ? 'down' : '', note: 'по продажам' },
      { key: 'net', label: 'Чистые покупки', value: buy.sum - sell.sum, format: (v) => money(v, { sign: true }), note: `оборот ${money(buy.sum + sell.sum)}` },
    ]
  }
  const dep = g('deposit')
  const wd = g('withdraw')
  const pay = g('payout')
  const fee = g('fee')
  return [
    { key: 'dep', label: 'Пополнено', value: dep.sum, format: f, note: countOp(dep.n) },
    { key: 'wd', label: 'Выведено', value: wd.sum, format: f, note: `чистый приток ${money(dep.sum - wd.sum, { sign: true })}` },
    { key: 'pay', label: 'Получено выплат', value: pay.sum, format: f, note: countOp(pay.n) },
    { key: 'fee', label: 'Налоги и комиссии', value: fee.sum, format: f, note: countOp(fee.n) },
  ]
})

const pageEyebrow = computed(() => {
  const list = normalizeFilterList(selectedPortfolio.value)
  if (!list.length) return 'Все портфели'
  return list.length === 1 ? list[0] : `${list.length} ${plural(list.length, 'портфель', 'портфеля', 'портфелей')}`
})
const pageMeta = computed(() => {
  const n = isTx.value ? filteredTransactions.value.length : filteredOperations.value.length
  return [isTx.value ? countTx(n) : countOp(n), periodPreset.value === 'all' ? 'за всё время' : periodFilterLabel.value]
})

/** строки списка в одном виде для сделок и операций */
const listRows = computed(() =>
  isTx.value
    ? filteredTransactions.value.map((tx) => ({
        id: tx.transaction_id,
        kind: 'transaction',
        raw: tx,
        date: tx.transaction_date,
        type: tx.transaction_type,
        group: groupOf(normalizeType(tx.transaction_type)),
        asset: tx.asset_name,
        ticker: tx.ticker,
        portfolio: tx.portfolio_name,
        qty: tx.quantity,
        price: tx.price,
        currency: tx.currency_ticker,
        amount: txValue(tx),
        pnl: txSellRealizedPnlNumber(tx),
        tip: '',
      }))
    : filteredOperations.value.map((op) => ({
        id: op.cash_operation_id || op.id,
        kind: 'operation',
        raw: op,
        date: op.operation_date,
        type: op.operation_type,
        group: groupOf(normalizeType(op.operation_type)),
        asset: op.asset_name,
        ticker: op.ticker,
        portfolio: op.portfolio_name,
        qty: null,
        price: null,
        currency: getOperationCurrency(op),
        amount: Math.abs(getOperationAmount(op)),
        pnl: null,
        tip: getOperationCommissionTooltipContent(op),
      })),
)

const PAGE = 100
const limit = ref(PAGE)
watch([filteredTransactions, filteredOperations, viewMode], () => { limit.value = PAGE })
const shownRows = computed(() => listRows.value.slice(0, limit.value))

const selIds = computed({
  get: () => (isTx.value ? selectedTxIds.value : selectedOpIds.value),
  set: (v) => {
    if (isTx.value) selectedTxIds.value = v
    else selectedOpIds.value = v
  },
})
const allSel = computed({
  get: () => (isTx.value ? allSelected.value : allOperationsSelected.value),
  set: (v) => {
    if (isTx.value) { allSelected.value = v; toggleAll() } else { allOperationsSelected.value = v; toggleAllOperations() }
  },
})
const deleteSel = () => (isTx.value ? deleteSelected() : deleteSelectedOperations())

/** знак суммы в движении денег: приток «+», отток «−» */
const opSign = (r) => (r.kind === 'operation' ? OP_GROUPS[r.group].dir : 0)
const fmtAmount = (r) =>
  r.kind === 'operation'
    ? `${opSign(r) > 0 ? '+' : '−'}${formatOperationAmount(r.amount, r.currency)}`
    : moneyIn(r.amount, r.currency, { digits: 2 })
const fmtPrice = (r) => moneyIn(r.price, r.currency, { digits: 2 })
const fmtQty = (v) => Number(v || 0).toLocaleString('ru-RU', { maximumFractionDigits: 6 })

const assetOptions = computed(() => (isTx.value ? filteredAssetsList.value : filteredOperationsAssetsList.value))
// каскадное появление — только при первом показе
const intro = ref(true)
onMounted(() => setTimeout(() => { intro.value = false }, 1600))

const clearAsset = () => {
  assetSearch.value = ''
  selectedAsset.value = ''
  applyFilter()
}
</script>

<template>
  <div class="ops">
    <CvPageHead :eyebrow="pageEyebrow" title="Операции" :meta="pageMeta">
      <template #actions>
        <CvSegmented v-model="viewMode" :options="VIEW_OPTIONS" aria-label="Что показывать" />
      </template>
    </CvPageHead>

    <div class="cv-grid" :class="{ 'is-intro': intro }">
      <CvKpiStrip class="is-xl" :items="kpis" :style="{ '--i': 0 }" />

      <OpsActivityWidget
        :key="viewMode"
        class="is-xl"
        :style="{ '--i': 1 }"
        :title="isTx ? 'Сделки по месяцам' : 'Движение денег по месяцам'"
        :rows="activityRows"
        :order="isTx ? TX_ORDER : OP_ORDER"
        :net-label="isTx ? 'Чистые покупки' : 'Чистый поток'"
      />

      <section class="ops__panel cv-card is-xl" :style="{ '--i': 2 }">
        <!-- фильтры -->
        <div class="ops__filters">
          <button v-if="isCardView" type="button" class="ops__mtoggle" @click="showMobileFilters = !showMobileFilters">
            <SlidersHorizontal :size="15" />
            <span>Фильтры</span>
            <b v-if="activeFilterCount" class="ops__badge">{{ activeFilterCount }}</b>
            <ChevronDown :size="15" class="ops__chev" :class="{ 'is-open': showMobileFilters }" />
          </button>

          <div v-show="!isCardView || showMobileFilters" class="ops__fbody">
            <div class="ops__frow">
              <div class="ops__search">
                <Search :size="15" class="ops__search-ic" />
                <input v-model="assetSearch" type="text" placeholder="Поиск по активу" class="ops__input" />
                <button v-if="assetSearch" type="button" class="ops__clear" aria-label="Очистить" @click="clearAsset">×</button>
                <ul v-if="assetSearch && selectedAsset !== assetSearch" class="ops__dd">
                  <li v-for="a in assetOptions" :key="a" @click="selectAssetFilter(a)">
                    <span v-html="highlightMatch(a)" />
                    <small v-if="isTx && getAssetMeta(a)">{{ getAssetMeta(a).ticker }}</small>
                  </li>
                  <li v-if="!assetOptions.length" class="is-empty">Ничего не найдено</li>
                </ul>
              </div>

              <CustomSelect
                v-model="selectedPortfolio"
                :options="portfolios"
                label="Портфель"
                placeholder="Все портфели"
                empty-option-text="Все портфели"
                option-label="name"
                option-value="name"
                multiple
                min-width="190px"
                flex="0 0 auto"
                @change="applyFilter"
              />
              <CustomSelect
                v-model="selectedType"
                :options="(isTx ? txTypes : operationTypes).map((t) => ({ value: t, label: t }))"
                label="Тип"
                placeholder="Все типы"
                empty-option-text="Все типы"
                multiple
                min-width="190px"
                flex="0 0 auto"
                @change="applyFilter"
              />
              <CustomSelect
                v-if="!isTx"
                v-model="selectedCurrency"
                :options="[
                  { value: 'RUB', label: 'В рублях' },
                  { value: 'ORIGINAL', label: 'В валюте операции' },
                ]"
                label="Валюта"
                placeholder="Валюта"
                min-width="170px"
                flex="0 0 auto"
                @change="applyFilter"
              />
              <button type="button" class="cv-btn cv-btn--ghost cv-btn--icon ops__reset" title="Сбросить фильтры" aria-label="Сбросить фильтры" @click="resetFilters">
                <RotateCcw :size="15" />
              </button>
            </div>

            <PeriodFilter
              :preset="periodPreset"
              :start-date="startDate"
              :end-date="endDate"
              :track-min-date="earliestDataDate"
              :show-track="showPeriodTrack"
              @update:preset="(v) => { periodPreset = v }"
              @update:start-date="(v) => { startDate = v; applyFilter() }"
              @update:end-date="(v) => { endDate = v; applyFilter() }"
            >
              <template #controls-suffix>
                <ToggleSwitch v-model="showPeriodTrack" label="Шкала периода" active-color="#6474ff" hover-color="#7b8aff" />
              </template>
            </PeriodFilter>
          </div>
        </div>

        <!-- шапка списка: выбор и удаление -->
        <div class="ops__lhead" :class="{ 'has-sel': selIds.length }">
          <label class="ops__check">
            <input v-model="allSel" type="checkbox" class="ops__cb" :disabled="!listRows.length" />
            <span v-if="selIds.length">Выбрано: <b class="cv-num">{{ selIds.length }}</b></span>
            <span v-else>{{ isTx ? countTx(listRows.length) : countOp(listRows.length) }}</span>
          </label>
          <button v-if="selIds.length" type="button" class="cv-btn cv-btn--sm ops__del" @click="deleteSel">
            <Trash2 :size="14" /> Удалить
          </button>
        </div>

        <!-- таблица (десктоп) -->
        <div v-if="!isCardView && listRows.length" class="ops__tablewrap">
          <table class="ops__table">
            <thead>
              <tr>
                <th class="c-cb" />
                <th>Дата</th>
                <th>Тип</th>
                <th>Актив</th>
                <th class="c-pf">Портфель</th>
                <template v-if="isTx">
                  <th class="r">Кол-во</th>
                  <th class="r">Цена</th>
                </template>
                <th class="r">Сумма</th>
                <th class="c-act" />
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in shownRows" :key="`${r.kind}-${r.id}`" :class="{ 'is-sel': selIds.includes(r.id) }">
                <td class="c-cb"><input v-model="selIds" type="checkbox" :value="r.id" class="ops__cb" /></td>
                <td class="c-date cv-num">{{ formatDate(r.date) }}</td>
                <td>
                  <span class="ops__type"><i :style="{ background: OP_GROUPS[r.group].color }" />{{ r.type }}</span>
                </td>
                <td class="c-asset">
                  <b>{{ r.asset || '—' }}</b>
                  <small v-if="r.ticker && r.ticker !== r.asset">{{ r.ticker }}</small>
                  <small class="c-pf-inline">{{ r.portfolio }}</small>
                </td>
                <td class="c-pf">{{ r.portfolio }}</td>
                <template v-if="isTx">
                  <td class="r cv-num c-mut">{{ fmtQty(r.qty) }}</td>
                  <td class="r cv-num c-mut">{{ fmtPrice(r) }}</td>
                </template>
                <td class="r c-amt">
                  <Tooltip v-if="r.tip" :content="r.tip" position="top">
                    <b class="cv-num is-tip">{{ fmtAmount(r) }}</b>
                  </Tooltip>
                  <b v-else class="cv-num" :class="{ 'is-out': opSign(r) < 0 }">{{ fmtAmount(r) }}</b>
                  <small v-if="r.pnl != null" class="cv-num" :class="r.pnl > 0 ? 'cv-up' : r.pnl < 0 ? 'cv-down' : ''">
                    {{ money(r.pnl, { sign: true }) }}
                  </small>
                </td>
                <td class="c-act">
                  <button type="button" class="cv-btn cv-btn--ghost cv-btn--sm cv-btn--icon" aria-label="Действия" @click="openMenu($event, r.kind, r.raw)">
                    <MoreHorizontal :size="16" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- карточки (планшет и телефон) -->
        <ul v-else-if="listRows.length" class="ops__cards">
          <li v-for="r in shownRows" :key="`${r.kind}-${r.id}`" class="ops__card" :class="{ 'is-sel': selIds.includes(r.id) }">
            <input v-model="selIds" type="checkbox" :value="r.id" class="ops__cb" />
            <div class="ops__cmain">
              <b>{{ r.asset || r.type }}</b>
              <small>
                <i :style="{ background: OP_GROUPS[r.group].color }" />
                <span>{{ r.type }} · {{ formatDate(r.date) }}</span>
              </small>
              <small class="ops__cmeta">
                {{ r.portfolio }}<template v-if="isTx"> · {{ fmtQty(r.qty) }} × {{ fmtPrice(r) }}</template>
              </small>
            </div>
            <div class="ops__camt">
              <b class="cv-num" :class="{ 'is-out': opSign(r) < 0 }">{{ fmtAmount(r) }}</b>
              <small v-if="r.pnl != null" class="cv-num" :class="r.pnl > 0 ? 'cv-up' : r.pnl < 0 ? 'cv-down' : ''">
                {{ money(r.pnl, { sign: true }) }}
              </small>
            </div>
            <button type="button" class="cv-btn cv-btn--ghost cv-btn--sm cv-btn--icon" aria-label="Действия" @click="openMenu($event, r.kind, r.raw)">
              <MoreHorizontal :size="16" />
            </button>
          </li>
        </ul>

        <div v-if="!listRows.length" class="ops__empty">
          <b>{{ isTx ? 'Сделки не найдены' : 'Операции не найдены' }}</b>
          <p v-if="activeFilterCount">Попробуйте изменить или сбросить фильтры.</p>
          <button v-if="activeFilterCount" type="button" class="cv-btn cv-btn--sm" @click="resetFilters">Сбросить фильтры</button>
        </div>

        <div v-if="listRows.length > limit" class="ops__more">
          <button type="button" class="cv-btn cv-btn--sm" @click="limit += PAGE">
            Показать ещё {{ Math.min(PAGE, listRows.length - limit) }}
          </button>
          <span>показано {{ limit }} из {{ listRows.length }}</span>
        </div>
      </section>
    </div>

    <EditTransactionModal :visible="showEditModal" :transaction="currentTransaction" @close="showEditModal = false" @save="handleSaveEdit" />
    <ContextMenu
      @editTransaction="handleEditTransaction"
      @deleteTransaction="handleDeleteTransaction"
      @deleteOperation="handleDeleteOperation"
    />
  </div>
</template>

<style scoped>
.ops { padding-bottom: 8px; }

/* ── панель: фильтры + список ─────────────────────────────────────────── */
.ops__panel { display: flex; flex-direction: column; min-width: 0; padding: 0; }
.ops__filters { display: flex; flex-direction: column; gap: 14px; padding: 18px 20px; border-bottom: 1px solid var(--cv-line); }
.ops__fbody { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.ops__frow { display: flex; align-items: flex-end; gap: 10px; flex-wrap: wrap; min-width: 0; }
.ops__reset { flex: none; height: 42px; width: 42px; }

.ops__search { position: relative; flex: 1 1 240px; min-width: 200px; }
.ops__search-ic { position: absolute; left: 13px; top: 50%; transform: translateY(-50%); color: var(--cv-dim); pointer-events: none; }
.ops__search:focus-within .ops__search-ic { color: var(--cv-accent-ink, var(--cv-accent)); }
.ops__input {
  width: 100%; height: 42px; padding: 0 36px 0 38px; box-sizing: border-box;
  border: 0; border-radius: 11px; outline: none;
  background: rgba(255, 255, 255, .04); box-shadow: inset 0 0 0 1px var(--cv-line);
  color: var(--cv-ink); font-size: 13.5px; transition: box-shadow .2s, background .2s;
}
.ops__input::placeholder { color: var(--cv-dim); }
.ops__input:hover { box-shadow: inset 0 0 0 1px var(--cv-line-2); }
.ops__input:focus { background: rgba(255, 255, 255, .06); box-shadow: inset 0 0 0 1px var(--cv-accent-line), 0 0 0 3px rgba(100, 116, 255, .12); }
.ops__clear {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  width: 24px; height: 24px; border: 0; border-radius: 7px; background: transparent;
  color: var(--cv-mut); font-size: 17px; line-height: 1; cursor: pointer;
}
.ops__clear:hover { background: var(--cv-hover); color: var(--cv-ink); }
.ops__dd {
  position: absolute; z-index: 30; top: calc(100% + 6px); left: 0; right: 0;
  max-height: 300px; overflow-y: auto; margin: 0; padding: 6px; list-style: none;
  border-radius: 12px; background: #17181d; box-shadow: inset 0 0 0 1px var(--cv-line-2), 0 18px 40px -12px rgba(0, 0, 0, .7);
}
.ops__dd li {
  display: flex; justify-content: space-between; align-items: center; gap: 10px;
  padding: 8px 10px; border-radius: 8px; font-size: 13px; color: var(--cv-ink-2); cursor: pointer;
}
.ops__dd li:hover { background: var(--cv-hover); color: var(--cv-ink); }
.ops__dd li small { font-size: 11.5px; color: var(--cv-dim); }
.ops__dd li.is-empty { justify-content: center; color: var(--cv-dim); cursor: default; }
.ops__dd li.is-empty:hover { background: transparent; }
.ops__dd :deep(mark) { background: transparent; color: var(--cv-accent-ink, #aab3ff); font-weight: 600; }

.ops__mtoggle {
  display: inline-flex; align-items: center; gap: 8px; align-self: flex-start;
  height: 36px; padding: 0 12px; border: 0; border-radius: 10px;
  background: rgba(255, 255, 255, .04); box-shadow: inset 0 0 0 1px var(--cv-line);
  color: var(--cv-ink-2); font-size: 13px; font-weight: 550; cursor: pointer;
}
.ops__badge { display: inline-grid; place-items: center; min-width: 18px; height: 18px; padding: 0 5px; border-radius: 9px; background: var(--cv-accent); color: #fff; font-size: 11px; }
.ops__chev { color: var(--cv-dim); transition: transform .25s var(--cv-ease); }
.ops__chev.is-open { transform: rotate(180deg); }

/* ── шапка списка ─────────────────────────────────────────────────────── */
.ops__lhead { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 52px; padding: 8px 20px; }
.ops__lhead.has-sel { background: rgba(100, 116, 255, .06); }
.ops__check { display: inline-flex; align-items: center; gap: 12px; font-size: 12.5px; color: var(--cv-mut); cursor: pointer; }
.ops__check b { color: var(--cv-ink); font-weight: 600; }
.ops__del { gap: 6px; color: #ff8a8a; }
.ops__del:hover { color: #ffb0b0; background: rgba(255, 90, 90, .1); box-shadow: inset 0 0 0 1px rgba(255, 90, 90, .25); }

.ops__cb {
  appearance: none; flex: none; width: 16px; height: 16px; margin: 0; border-radius: 5px; cursor: pointer;
  background: rgba(255, 255, 255, .03); box-shadow: inset 0 0 0 1.5px var(--cv-line-2);
  display: inline-grid; place-items: center; transition: background .15s, box-shadow .15s;
}
.ops__cb:hover { box-shadow: inset 0 0 0 1.5px var(--cv-mut); }
.ops__cb:checked { background: var(--cv-accent); box-shadow: none; }
.ops__cb:checked::after { content: ''; width: 8px; height: 4px; margin-top: -2px; border-left: 2px solid #fff; border-bottom: 2px solid #fff; transform: rotate(-45deg); }
.ops__cb:disabled { opacity: .4; cursor: default; }

/* ── таблица ──────────────────────────────────────────────────────────── */
.ops__tablewrap { overflow-x: auto; }
.ops__table { width: 100%; border-collapse: collapse; font-size: 13px; }
.ops__table th {
  padding: 10px 12px; text-align: left; white-space: nowrap;
  font-size: 11px; font-weight: 550; letter-spacing: .06em; text-transform: uppercase; color: var(--cv-dim);
  border-top: 1px solid var(--cv-line); border-bottom: 1px solid var(--cv-line);
}
.ops__table td { padding: 11px 12px; color: var(--cv-ink-2); border-bottom: 1px solid var(--cv-line); vertical-align: middle; }
.ops__table tbody tr { transition: background .15s; }
.ops__table tbody tr:hover { background: var(--cv-hover); }
.ops__table tbody tr.is-sel { background: rgba(100, 116, 255, .07); }
.ops__table tbody tr:last-child td { border-bottom: 0; }
.ops__table .r { text-align: right; }
.ops__table th:first-child, .ops__table td:first-child { padding-left: 20px; }
.ops__table th:last-child, .ops__table td:last-child { padding-right: 14px; }
.c-cb { width: 16px; }
.c-act { width: 30px; }
.c-date { white-space: nowrap; color: var(--cv-mut) !important; }
.c-mut { color: var(--cv-mut) !important; white-space: nowrap; }
.c-asset b { display: block; max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 550; color: var(--cv-ink); }
.c-asset small { font-size: 11.5px; color: var(--cv-dim); }
.c-pf { color: var(--cv-mut) !important; white-space: nowrap; }
.c-asset small { display: block; }
.c-pf-inline { display: none !important; }
/* на узком экране портфель уходит под название актива */
@media (max-width: 1360px) {
  .ops__table .c-pf { display: none; }
  .c-pf-inline { display: block !important; }
  .ops__table th, .ops__table td { padding-left: 9px; padding-right: 9px; }
  .c-asset b, .c-asset small { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
}
.c-amt { white-space: nowrap; }
.c-amt b { display: block; font-weight: 600; color: var(--cv-ink); }
.c-amt b.is-out { color: var(--cv-ink-2); }
.c-amt b.is-tip { border-bottom: 1px dashed var(--cv-line-2); cursor: help; }
.c-amt small { display: block; margin-top: 2px; font-size: 11.5px; font-weight: 550; }
.c-amt :deep(.tooltip-wrapper), .c-amt :deep(.tooltip-container) { display: inline-block; }

.ops__type { display: inline-flex; align-items: center; gap: 7px; white-space: nowrap; color: var(--cv-ink-2); }
.ops__type i, .ops__cmain small i { width: 7px; height: 7px; flex: none; border-radius: 2px; }

/* ── карточки ─────────────────────────────────────────────────────────── */
.ops__cards { list-style: none; margin: 0; padding: 0 8px 8px; border-top: 1px solid var(--cv-line); }
.ops__card {
  display: grid; grid-template-columns: 16px minmax(0, 1fr) auto 30px; align-items: center; gap: 12px;
  padding: 11px 8px 11px 12px;
}
.ops__card + .ops__card { border-top: 1px solid var(--cv-line); }
.ops__card.is-sel { background: rgba(100, 116, 255, .07); }
.ops__cmain { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.ops__cmain b { font-size: 13.5px; font-weight: 550; color: var(--cv-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ops__cmain small { display: flex; align-items: center; gap: 6px; font-size: 11.5px; color: var(--cv-mut); white-space: nowrap; overflow: hidden; }
.ops__cmain small span { overflow: hidden; text-overflow: ellipsis; }
.ops__cmeta { color: var(--cv-dim) !important; display: block !important; text-overflow: ellipsis; }
.ops__camt { display: flex; flex-direction: column; align-items: flex-end; gap: 3px; white-space: nowrap; }
.ops__camt b { font-size: 13.5px; font-weight: 600; color: var(--cv-ink); }
.ops__camt b.is-out { color: var(--cv-ink-2); }
.ops__camt small { font-size: 11.5px; font-weight: 550; }

.ops__empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 48px 16px 56px; text-align: center; border-top: 1px solid var(--cv-line); }
.ops__empty b { color: var(--cv-ink); font-size: 14.5px; font-weight: 550; }
.ops__empty p { margin: 0; font-size: 13px; color: var(--cv-mut); }
.ops__empty .cv-btn { margin-top: 6px; }

.ops__more { display: flex; align-items: center; justify-content: center; gap: 14px; padding: 14px 20px 18px; border-top: 1px solid var(--cv-line); font-size: 12px; color: var(--cv-dim); }

@media (max-width: 768px) {
  .ops__filters { padding: 14px; }
  .ops__lhead { padding: 8px 14px; }
  .ops__search { flex-basis: 100%; min-width: 0; }
  .ops__frow > :deep(*) { flex: 1 1 100%; min-width: 0 !important; }
  .ops__frow > .ops__reset { flex: 0 0 42px; }
  .ops__cards { padding: 0 4px 4px; }
  .ops__card { gap: 10px; padding: 10px 4px 10px 10px; }
}
</style>
