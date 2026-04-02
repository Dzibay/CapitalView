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
import { DateInput, ToggleSwitch, PeriodFilter } from '../components/base'
import { Search } from 'lucide-vue-next'
import PageLayout from '../layouts/PageLayout.vue'
import PageHeader from '../layouts/PageHeader.vue'
import { formatOperationAmount } from '../utils/formatCurrency'
import { normalizeDateToString, formatDateForDisplay } from '../utils/date'
import { getCurrencySymbol } from '../utils/currencySymbols'
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

// Загружаем полные списки транзакций и операций при открытии страницы
onMounted(() => {
  if (!dashboardStore.fullListsLoaded) {
    dashboardStore.fetchTransactionsAndOperationsInBackground()
  }
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
const normalizeType = (type) => {
  const t = (type || '').toString().toLowerCase()
  if (t.includes('покуп') || t.includes('buy')) return 'buy'
  if (t.includes('прод') || t.includes('sell')) return 'sell'
  if (t.includes('див') || t.includes('div')) return 'dividend'
  if (t.includes('купон') || t.includes('coupon')) return 'coupon'
  if (t.includes('налог') || t.includes('tax')) return 'tax'
  if (t.includes('комисс') || t.includes('commission') || t.includes('commision')) return 'commission'
  if (t.includes('ввод') || t.includes('депозит') || t.includes('deposit')) return 'deposit'
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

// --- функции для отображения операций в выбранной валюте ---
// Получаем сумму операции в выбранной валюте
const getOperationAmount = (op) => {
  if (selectedCurrency.value === 'RUB') {
    // Используем amount_rub (уже переведено в рубли по курсу на дату операции)
    const amountRub = Number(op.amount_rub ?? op.amountRub ?? op.amount) || 0
    return amountRub
  } else {
    // Используем оригинальную сумму в исходной валюте
    return Number(op.amount) || 0
  }
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
    if (typeFilters.length > 0 && !typeFilters.includes(tx.transaction_type)) return false

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

      if (typeFilters.length > 0 && !typeFilters.includes(op.operation_type)) return false
      
      // Фильтр по активу (если указан)
      if (assetFilter && op.asset_name && op.asset_name !== assetFilter) return false
      if (assetFilter && !op.asset_name) return false // Если фильтр по активу, но у операции нет актива - исключаем

      // Период
      if (start || end) {
        const opDate = new Date(op.operation_date)
        if (start && opDate < start) return false
        if (end && opDate > end) return false
      }

      // Глобальный поиск (используем amount_rub для поиска)
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
    // Для операций суммируем по типам (ВСЕГДА используем amount_rub в рублях для статистики)
    for (const op of filteredOperations.value) {
      // Для статистики всегда используем amount_rub (в рублях)
      const amountRub = Number(op.amount_rub ?? op.amountRub ?? op.amount) || 0
      const value = amountRub
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

// Получение суммы по типу операции из отфильтрованных данных
// ВСЕГДА использует amount_rub (в рублях) для статистики
const getOperationTypeSum = (operationType) => {
  let sum = 0
  for (const op of filteredOperations.value) {
    if (op.operation_type === operationType) {
      // Для статистики всегда используем amount_rub (в рублях)
      const amountRub = Number(op.amount_rub ?? op.amountRub ?? op.amount) || 0
      sum += Math.abs(amountRub)
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
</script>

<template>
  <PageLayout>
    <PageHeader title="История транзакций">
      <template #actions>
        <div class="header-actions">
          <div v-if="selectedTxIds.length > 0 && viewMode === 'transactions'" class="bulk-actions bulk-actions-desktop">
            <span class="selected-count">Выбрано: {{ selectedTxIds.length }}</span>
            <button @click="deleteSelected" class="btn btn-danger-soft" :disabled="selectedTxIds.length === 0">
              Удалить выбранные ({{ selectedTxIds.length }})
            </button>
          </div>
          <div v-if="selectedOpIds.length > 0 && viewMode === 'operations'" class="bulk-actions bulk-actions-desktop">
            <span class="selected-count">Выбрано: {{ selectedOpIds.length }}</span>
            <button @click="deleteSelectedOperations" class="btn btn-danger-soft" :disabled="selectedOpIds.length === 0">
              Удалить выбранные ({{ selectedOpIds.length }})
            </button>
          </div>
          <div class="view-mode-switcher">
            <button 
              class="btn btn-ghost" 
              :class="{ active: viewMode === 'transactions' }"
              @click="viewMode = 'transactions'"
            >
              Транзакции
            </button>
            <button 
              class="btn btn-ghost" 
              :class="{ active: viewMode === 'operations' }"
              @click="viewMode = 'operations'"
            >
              Операции
            </button>
          </div>
        </div>
      </template>
    </PageHeader>

    <div class="transactions-content">
      <div class="main-content">

        <div class="transactions-main">
          <div class="card">
          <div class="toolbar">
            <div class="filters-top">
              <!-- Строка 1: поиск по активу + сброс (всегда вместе при сужении) -->
              <div class="filters-row filters-row--primary">
                <div v-if="viewMode === 'transactions'" class="asset-search-wrapper">
                  <span class="select-label">Актив</span>
                  <span class="input-icon"><Search :size="16" /></span>
                  <input
                    type="text"
                    v-model="assetSearch"
                    placeholder="Поиск актива"
                    class="form-input"
                  />
                  <button v-if="assetSearch" @click="assetSearch=''; selectedAsset=''; applyFilter()" class="clear-btn">×</button>

                  <ul v-if="assetSearch && selectedAsset !== assetSearch" class="asset-dropdown">
                    <li v-for="a in filteredAssetsList" :key="a" @click="selectAssetFilter(a)" class="asset-option">
                      <span v-html="highlightMatch(a)" />
                      <span v-if="getAssetMeta(a)" class="meta-ticker">{{ getAssetMeta(a).ticker }}</span>
                    </li>
                    <li v-if="filteredAssetsList.length === 0" class="asset-empty">
                      <span class="asset-empty-icon"><Search :size="20" /></span>
                      Ничего не найдено
                    </li>
                  </ul>
                </div>

                <div v-else class="asset-search-wrapper">
                  <span class="select-label">Актив</span>
                  <span class="input-icon"><Search :size="16" /></span>
                  <input
                    type="text"
                    v-model="assetSearch"
                    placeholder="Поиск актива"
                    class="form-input"
                  />
                  <button v-if="assetSearch" @click="assetSearch=''; selectedAsset=''; applyFilter()" class="clear-btn">×</button>

                  <ul v-if="assetSearch && selectedAsset !== assetSearch" class="asset-dropdown">
                    <li v-for="a in filteredOperationsAssetsList" :key="a" @click="selectAssetFilter(a)" class="asset-option">
                      <span v-html="highlightMatch(a)" />
                    </li>
                    <li v-if="filteredOperationsAssetsList.length === 0" class="asset-empty">
                      <span class="asset-empty-icon"><Search :size="20" /></span>
                      Ничего не найдено
                    </li>
                  </ul>
                </div>

                <button
                  type="button"
                  @click="resetFilters"
                  class="btn btn-ghost reset-btn"
                  title="Сбросить фильтры"
                >
                  <span class="reset-icon">↺</span>
                </button>
              </div>

              <!-- Строка 2: портфель, тип, валюта — переносятся только внутри этой строки -->
              <div class="filters-row filters-row--secondary select-group">
                <CustomSelect
                  v-model="selectedPortfolio"
                  :options="portfolios"
                  label="Портфель"
                  placeholder="Все портфели"
                  empty-option-text="Все портфели"
                  option-label="name"
                  option-value="name"
                  multiple
                  min-width="200px"
                  @change="applyFilter"
                />
                <CustomSelect
                  v-model="selectedType"
                  :options="viewMode === 'transactions' ? txTypes.map(t => ({ value: t, label: t })) : operationTypes.map(t => ({ value: t, label: t }))"
                  label="Тип"
                  placeholder="Все типы"
                  empty-option-text="Все типы"
                  multiple
                  min-width="220px"
                  @change="applyFilter"
                />
                <CustomSelect
                  v-if="viewMode === 'operations'"
                  v-model="selectedCurrency"
                  :options="[
                    { value: 'RUB', label: 'Рубли (RUB)' },
                    { value: 'ORIGINAL', label: 'Оригинальная валюта' }
                  ]"
                  label="Валюта"
                  placeholder="Выберите валюту"
                  @change="applyFilter"
                />
              </div>
            </div>

        <div class="filters-bottom">
          <PeriodFilter
            :preset="periodPreset"
            :start-date="startDate"
            :end-date="endDate"
            :track-min-date="earliestDataDate"
            :show-track="showPeriodTrack"
            @update:preset="v => { periodPreset = v }"
            @update:start-date="v => { startDate = v; applyFilter() }"
            @update:end-date="v => { endDate = v; applyFilter() }"
          >
            <template #controls-suffix>
              <ToggleSwitch
                v-model="showPeriodTrack"
                label="Отображать трек"
                active-color="#2563eb"
                hover-color="#1d4ed8"
              />
            </template>
          </PeriodFilter>
        </div>

            <div class="sums-toggle-row">
              <ToggleSwitch
                v-model="showSumsSummary"
                :label="viewMode === 'transactions' ? 'Показывать суммы по транзакциям' : 'Показывать суммы по операциям'"
                active-color="#2563eb"
                hover-color="#1d4ed8"
              />
            </div>
          </div>

          <!-- Блок сумм между фильтрами и таблицей -->
          <div v-if="showSumsSummary" class="sums-summary-block">
            <template v-if="viewMode === 'transactions'">
              <h3 class="sums-block-title">Суммы по транзакциям</h3>
              <div class="transactions-summary">
                <div class="summary-item">
                  <span class="summary-item-label">Покупки:</span>
                  <span class="summary-item-value">
                    {{ transactionsSummary.buy.toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' }) }}
                  </span>
                </div>
                <div class="summary-item">
                  <span class="summary-item-label">Продажи:</span>
                  <span class="summary-item-value">
                    {{ transactionsSummary.sell.toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' }) }}
                  </span>
                </div>
                <div class="summary-item">
                  <span class="summary-item-label">Оборот:</span>
                  <span class="summary-item-value">
                    {{ (transactionsSummary.buy + transactionsSummary.sell).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' }) }}
                  </span>
                </div>
              </div>
            </template>
            <template v-else>
              <h3 class="sums-block-title">Суммы по операциям</h3>
              <div class="operations-sums">
                <div class="sums-list">
                  <div
                    v-for="opType in operationTypes"
                    :key="opType"
                    class="sum-item"
                  >
                    <span class="sum-type">{{ opType }}:</span>
                    <span class="sum-value">
                      {{ getOperationTypeSum(opType).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' }) }}
                    </span>
                  </div>
                </div>
              </div>
            </template>
          </div>

          <!-- Кнопка удаления выбранных — на мобильных показывается здесь, чтобы не сдвигать переключатель в шапке -->
          <div v-if="(selectedTxIds.length > 0 && viewMode === 'transactions') || (selectedOpIds.length > 0 && viewMode === 'operations')" class="bulk-actions-mobile">
            <span class="selected-count">Выбрано: {{ viewMode === 'transactions' ? selectedTxIds.length : selectedOpIds.length }}</span>
            <button
              v-if="viewMode === 'transactions'"
              @click="deleteSelected"
              class="btn btn-danger-soft"
              :disabled="selectedTxIds.length === 0"
            >
              Удалить ({{ selectedTxIds.length }})
            </button>
            <button
              v-else
              @click="deleteSelectedOperations"
              class="btn btn-danger-soft"
              :disabled="selectedOpIds.length === 0"
            >
              Удалить ({{ selectedOpIds.length }})
            </button>
          </div>

          <div class="table-container">
          <!-- Карточки транзакций (планшет/мобильные) -->
          <div v-if="isCardView && viewMode === 'transactions'" class="transactions-cards-wrapper">
            <div class="cards-select-all">
              <label class="select-all-label">
                <input type="checkbox" v-model="allSelected" @change="toggleAll" class="custom-checkbox" />
                <span>Выбрать все</span>
              </label>
            </div>
            <div class="transactions-cards">
            <div
              v-for="tx in filteredTransactions"
              :key="tx.transaction_id"
              class="transaction-card"
            >
              <div class="transaction-card-header">
                <span class="card-date">{{ formatDate(tx.transaction_date) }}</span>
                <span :class="['badge', 'badge-' + normalizeType(tx.transaction_type)]">{{ tx.transaction_type }}</span>
              </div>
              <div class="transaction-card-actions">
                <input type="checkbox" :value="tx.transaction_id" v-model="selectedTxIds" class="custom-checkbox" />
                <button class="icon-btn" @click="openMenu($event, 'transaction', tx)">⋯</button>
              </div>
              <div class="transaction-card-body">
                <div class="transaction-card-row">
                  <span class="card-label">Актив</span>
                  <span class="card-value font-medium">{{ tx.asset_name }}</span>
                </div>
                <div class="transaction-card-row">
                  <span class="card-label">Портфель</span>
                  <span class="card-value text-secondary">{{ tx.portfolio_name }}</span>
                </div>
                <div class="transaction-card-row">
                  <span class="card-label">Кол-во</span>
                  <span class="card-value num-font">{{ tx.quantity }}</span>
                </div>
                <div class="transaction-card-row">
                  <span class="card-label">Цена</span>
                  <span class="card-value num-font">{{ tx.price.toLocaleString() }} {{ getCurrencySymbol(tx.currency_ticker) }}</span>
                </div>
                <div class="transaction-card-row">
                  <span class="card-label">Сумма</span>
                  <span class="card-value num-font font-semibold">
                    {{ (tx.quantity * tx.price).toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) }} {{ getCurrencySymbol(tx.currency_ticker) }}
                  </span>
                </div>
              </div>
            </div>
            <div v-if="filteredTransactions.length === 0" class="empty-cell">
              <div class="empty-state">
                <span class="empty-icon">🔍</span>
                <p>Транзакции не найдены</p>
              </div>
            </div>
            </div>
          </div>
          <!-- Карточки операций (планшет/мобильные) -->
          <div v-else-if="isCardView && viewMode === 'operations'" class="transactions-cards-wrapper">
            <div class="cards-select-all">
              <label class="select-all-label">
                <input type="checkbox" v-model="allOperationsSelected" @change="toggleAllOperations" class="custom-checkbox" />
                <span>Выбрать все</span>
              </label>
            </div>
            <div class="transactions-cards">
            <div
              v-for="op in filteredOperations"
              :key="op.cash_operation_id || op.id"
              class="transaction-card"
            >
              <div class="transaction-card-header">
                <span class="card-date">{{ formatDate(op.operation_date) }}</span>
                <span :class="['badge', 'badge-' + normalizeType(op.operation_type)]">{{ op.operation_type }}</span>
              </div>
              <div class="transaction-card-actions">
                <input type="checkbox" :value="op.cash_operation_id || op.id" v-model="selectedOpIds" class="custom-checkbox" />
                <button class="icon-btn" @click="openMenu($event, 'operation', op)">⋯</button>
              </div>
              <div class="transaction-card-body">
                <div class="transaction-card-row">
                  <span class="card-label">Актив</span>
                  <span class="card-value font-medium">{{ op.asset_name || '—' }}</span>
                </div>
                <div class="transaction-card-row">
                  <span class="card-label">Портфель</span>
                  <span class="card-value text-secondary">{{ op.portfolio_name }}</span>
                </div>
                <div class="transaction-card-row">
                  <span class="card-label">Сумма</span>
                  <span class="card-value num-font font-semibold">
                    {{ formatOperationAmount(Math.abs(getOperationAmount(op)), getOperationCurrency(op)) }}
                  </span>
                </div>
              </div>
            </div>
            <div v-if="filteredOperations.length === 0" class="empty-cell">
              <div class="empty-state">
                <span class="empty-icon">🔍</span>
                <p>Операции не найдены</p>
              </div>
            </div>
            </div>
          </div>
          <!-- Таблица транзакций (десктоп) -->
          <table v-else-if="viewMode === 'transactions'" class="transactions-table">
            <thead>
              <tr>
                <th class="w-checkbox">
                  <input type="checkbox" v-model="allSelected" @change="toggleAll" class="custom-checkbox" />
                </th>
                <th>Дата</th>
                <th>Тип</th>
                <th>Актив</th>
                <th>Портфель</th>
                <th class="text-right">Кол-во</th>
                <th class="text-right">Цена</th>
                <th class="text-right">Сумма</th>
                <th class="w-actions"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="tx in filteredTransactions" :key="tx.transaction_id" class="tx-row">
                <td class="w-checkbox">
                  <input type="checkbox" :value="tx.transaction_id" v-model="selectedTxIds" class="custom-checkbox" />
                </td>
                <td class="td-date">{{ formatDate(tx.transaction_date) }}</td>
                <td>
                  <span :class="['badge', 'badge-' + normalizeType(tx.transaction_type)]">
                    {{ tx.transaction_type }}
                  </span>
                </td>
                <td class="font-medium">{{ tx.asset_name }}</td>
                <td class="text-secondary">{{ tx.portfolio_name }}</td>
                <td class="text-right num-font">{{ tx.quantity }}</td>
                <td class="text-right num-font">{{ tx.price.toLocaleString() }} {{ getCurrencySymbol(tx.currency_ticker) }}</td>
                <td class="text-right num-font font-semibold">
                  {{ (tx.quantity * tx.price).toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) }} {{ getCurrencySymbol(tx.currency_ticker) }}
                </td>
                <td class="w-actions">
                  <button class="icon-btn" @click="openMenu($event, 'transaction', tx)">⋯</button>
                </td>
              </tr>
              <tr v-if="filteredTransactions.length === 0">
                <td colspan="9" class="empty-cell">
                  <div class="empty-state">
                    <span class="empty-icon">🔍</span>
                    <p>Транзакции не найдены</p>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- Таблица операций (десктоп) -->
          <table v-else class="transactions-table">
            <thead>
              <tr>
                <th class="w-checkbox">
                  <input type="checkbox" v-model="allOperationsSelected" @change="toggleAllOperations" class="custom-checkbox" />
                </th>
                <th>Дата</th>
                <th>Тип</th>
                <th>Актив</th>
                <th>Портфель</th>
                <th class="text-right">Сумма</th>
                <th class="text-right">Валюта</th>
                <th class="w-actions"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="op in filteredOperations" :key="op.cash_operation_id || op.id" class="tx-row">
                <td class="w-checkbox">
                  <input type="checkbox" :value="op.cash_operation_id || op.id" v-model="selectedOpIds" class="custom-checkbox" />
                </td>
                <td class="td-date">{{ formatDate(op.operation_date) }}</td>
                <td>
                  <span :class="['badge', 'badge-' + normalizeType(op.operation_type)]">
                    {{ op.operation_type }}
                  </span>
                </td>
                <td class="font-medium">{{ op.asset_name || '—' }}</td>
                <td class="text-secondary">{{ op.portfolio_name }}</td>
                <td class="text-right num-font font-semibold">
                  {{ formatOperationAmount(Math.abs(getOperationAmount(op)), getOperationCurrency(op)) }}
                </td>
                <td class="text-right num-font">{{ getOperationCurrency(op) }}</td>
                <td class="w-actions">
                  <button class="icon-btn" @click="openMenu($event, 'operation', op)">⋯</button>
                </td>
              </tr>
              <tr v-if="filteredOperations.length === 0">
                <td colspan="8" class="empty-cell">
                  <div class="empty-state">
                    <span class="empty-icon">🔍</span>
                    <p>Операции не найдены</p>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          </div>
        </div>
        </div>
      </div>
    </div>

    <EditTransactionModal :visible="showEditModal" :transaction="currentTransaction" @close="showEditModal = false" @save="handleSaveEdit" />
    
    <ContextMenu
      @editTransaction="handleEditTransaction"
      @deleteTransaction="handleDeleteTransaction"
      @deleteOperation="handleDeleteOperation"
    />
  </PageLayout>
</template>

<style scoped>
/* =========================================
   1. БАЗОВАЯ РАЗМЕТКА И ТИПОГРАФИКА
   ========================================= */
.transactions-content {
  display: flex;
  gap: 24px;
  align-items: flex-start;
  min-width: 0;
  width: 100%;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #1f2937;
}

.main-content {
  flex: 1;
  min-width: 0;
}

.transactions-main {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 0;
  width: 100%;
}

.card {
  background: #fff;
  width: 100%;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e5e7eb;
  overflow: visible;
  box-sizing: border-box;
}

/* =========================================
   2. ШАПКА И ПЕРЕКЛЮЧАТЕЛИ
   ========================================= */
.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 40px;
  flex-wrap: wrap;
}

.view-mode-switcher {
  display: flex;
  gap: 4px;
  background: #f3f4f6;
  padding: 4px;
  border-radius: 8px;
  margin-left: auto;
}

.view-mode-switcher .btn {
  padding: 8px 16px;
  border-radius: 6px;
  transition: all 0.2s;
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
}

.view-mode-switcher .btn:hover {
  color: #374151;
}

.view-mode-switcher .btn.active {
  background: white;
  color: #2563eb;
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* Массовые действия (Bulk Actions) */
.bulk-actions, .bulk-actions-mobile {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fef2f2;
  border-radius: 8px;
  border: 1px solid #fee2e2;
}

.bulk-actions {
  padding: 6px 12px;
}

.bulk-actions-mobile {
  display: none;
  padding: 8px 12px;
  margin-bottom: 12px;
}

.selected-count {
  font-size: 13px;
  font-weight: 600;
  color: #b91c1c;
}

.btn-danger-soft {
  background: #fff;
  border: 1px solid #fca5a5;
  color: #b91c1c;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-danger-soft:hover {
  background: #ef4444;
  color: #fff;
}

/* =========================================
   3. ПАНЕЛЬ ИНСТРУМЕНТОВ И ФИЛЬТРЫ
   ========================================= */
.toolbar {
  padding: 20px;
  border-bottom: 1px solid #f3f4f6;
  box-sizing: border-box;
}

.filters-top {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
  width: 100%;
}

.filters-row {
  display: flex;
  align-items: flex-end;
  width: 100%;
  min-width: 0;
}

.filters-row--primary {
  flex-wrap: nowrap;
  gap: 12px;
}

.filters-row--primary .asset-search-wrapper {
  flex: 1 1 auto;
  min-width: 0;
}

.filters-row--primary .reset-btn {
  flex: 0 0 42px;
}

.filters-row--secondary {
  flex-wrap: wrap;
  gap: 10px;
}

.filters-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

/* Поиск актива (ширина задаётся в .filters-row--primary) */
.asset-search-wrapper {
  position: relative;
  min-width: 0;
}

.asset-search-wrapper .select-label {
  position: absolute;
  top: -8px;
  left: 12px;
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  background: #fff;
  padding: 0 4px;
  text-transform: uppercase;
  z-index: 2;
  pointer-events: none;
}

.input-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #6b7280;
  z-index: 1;
}

.asset-search-wrapper:focus-within .input-icon {
  color: #3b82f6;
}

.form-input {
  width: 100%;
  padding: 10px 40px 10px 36px;
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: all 0.2s ease;
  background: #fff;
  color: #111827;
  min-height: 42px;
  box-sizing: border-box;
}

.form-input:hover {
  border-color: #d1d5db;
}

.form-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* Выпадающий список поиска (Dropdown) */
.asset-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  width: 100%;
  background: white;
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  list-style: none;
  padding: 6px 0;
  max-height: 300px;
  overflow-y: auto;
  z-index: 100;
  margin: 0;
}

.asset-option {
  padding: 10px 16px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.15s ease;
  border-left: 3px solid transparent;
}

.asset-option:hover {
  background: #f3f4f6;
  border-left-color: #3b82f6;
}

.asset-option mark {
  background: #fef3c7;
  color: #92400e;
  font-weight: 600;
  padding: 0 2px;
  border-radius: 2px;
}

.meta-ticker {
  background: #eff6ff;
  color: #1e40af;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 12px;
}

.asset-empty {
  padding: 20px;
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
  font-style: italic;
}

.clear-btn {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: #f3f4f6;
  border: none;
  font-size: 18px;
  color: #6b7280;
  cursor: pointer;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}

.clear-btn:hover {
  background: #fee2e2;
  color: #dc2626;
}

/* Селекты второй строки */
.select-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  min-width: 0;
}

.select-group :deep(.custom-select-wrapper) {
  flex: 1 1 130px; /* Гибкая ширина с базой 130px */
  min-width: 120px;
}

.reset-btn {
  flex: 0 0 42px;
  height: 42px;
  font-size: 18px;
  color: #6b7280;
  background: #f9fafb;
  border: 1.5px solid #e5e7eb;
  cursor: pointer;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.reset-btn:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}

/* Чипсы периода */
.chips-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  background: #f9fafb;
  border: 1.5px solid #e5e7eb;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  color: #4b5563;
  cursor: pointer;
  transition: all 0.2s;
}

.chip:hover {
  background: #f3f4f6;
}

.chip.active {
  background: #eff6ff;
  color: #2563eb;
  border-color: #3b82f6;
  font-weight: 600;
}

.date-range {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1.5px solid #e5e7eb;
  flex-wrap: wrap;
}

.date-input {
  padding: 8px;
  border: 1.5px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
}

/* =========================================
   4. БЛОК СУММ И ИТОГОВ
   ========================================= */
.sums-toggle-row {
  padding: 10px 0 0;
  margin-top: 8px;
  border-top: 1px solid #f3f4f6;
}

.sums-summary-block {
  margin-top: 16px;
  padding: 16px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  box-sizing: border-box;
}

.sums-block-title {
  margin: 0 0 12px 0;
  font-size: 15px;
  font-weight: 600;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e7eb;
}

.summary-item, .sum-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: #fff;
  border-radius: 6px;
  margin-bottom: 6px;
  border: 1px solid #e5e7eb;
  font-size: 13px;
}

.summary-item-label, .sum-type {
  color: #6b7280;
  font-weight: 500;
}

.summary-item-value, .sum-value {
  font-weight: 600;
}

/* =========================================
   5. ТАБЛИЦЫ (Десктоп)
   ========================================= */
.table-container {
  overflow-x: auto;
  width: 100%;
}

.transactions-table {
  width: 100%;
  min-width: 800px;
  border-collapse: collapse;
  font-size: 14px;
}

.transactions-table th {
  text-align: left;
  padding: 12px 16px;
  background: #f9fafb;
  color: #6b7280;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  border-bottom: 1px solid #e5e7eb;
}

.transactions-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f3f4f6;
  vertical-align: middle;
}

.transactions-table tr:hover {
  background: #f9fafb;
}

/* =========================================
   6. КАРТОЧКИ (Планшет и Мобильные)
   ========================================= */
.transactions-cards-wrapper {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

.cards-select-all {
  padding: 8px 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.select-all-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: 500;
}

.transactions-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
}

.transaction-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.transaction-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.transaction-card-actions {
  display: flex;
  gap: 8px;
}

.transaction-card-body {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 16px;
  font-size: 12px;
}

.transaction-card-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.card-label { color: #6b7280; }
.card-value { color: #111827; text-align: right; }

/* =========================================
   7. УТИЛИТЫ И БЕЙДЖИ
   ========================================= */
.w-checkbox { width: 40px; text-align: center; }
.w-actions { width: 40px; }
.text-right { text-align: right !important; }
.font-medium { font-weight: 500; }
.font-semibold { font-weight: 600; }
.text-secondary { color: #6b7280; font-size: 13px; }
.num-font { font-family: 'SF Mono', 'Roboto Mono', monospace; }

.badge {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}
.badge-buy { background: #dcfce7; color: #166534; }
.badge-sell { background: #fee2e2; color: #991b1b; }
.badge-dividend { background: #eff6ff; color: #2563eb; }
.badge-coupon { background: #ecfeff; color: #06b6d4; }
.badge-deposit { background: #ccfbf1; color: #0f766e; }
.badge-withdraw { background: #ffedd5; color: #9a3412; }
.badge-tax, .badge-commission { background: #fef3c7; color: #92400e; }
.badge-other { background: #f3f4f6; color: #4b5563; }

.icon-btn {
  background: none;
  border: none;
  color: #9ca3af;
  font-size: 16px;
  cursor: pointer;
  border-radius: 4px;
}

.icon-btn:hover { color: #374151; background: #f3f4f6; }
.custom-checkbox { width: 16px; height: 16px; cursor: pointer; accent-color: #2563eb; }

.empty-cell { text-align: center; padding: 40px; }
.empty-state { color: #9ca3af; }
.empty-icon { font-size: 32px; display: block; opacity: 0.5; }

/* =========================================
   8. АДАПТИВ (MEDIA QUERIES)
   ========================================= */
@media (max-width: 1024px) {
  .transactions-content {
    flex-direction: column;
  }
  .chips-group { gap: 6px; }
  .chip { padding: 6px 12px; font-size: 12px; }
}

@media (max-width: 768px) {
  .toolbar {
    padding: 12px;
  }

  .select-group :deep(.custom-select-wrapper) {
    flex: 1 1 calc(50% - 10px);
    min-width: 100px;
  }

  .bulk-actions-desktop { display: none !important; }
  .bulk-actions-mobile { display: flex; }
  
  .filters-bottom {
    flex-direction: column;
    align-items: stretch;
  }
}

@media (max-width: 480px) {
  .select-group {
    flex-direction: column;
  }
  .select-group :deep(.custom-select-wrapper) {
    width: 100%;
  }

  .transactions-cards { padding: 8px; }
  .transaction-card-body { grid-template-columns: 1fr; }
}
</style>
