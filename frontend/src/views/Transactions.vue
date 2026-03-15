<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useDashboardStore } from '../stores/dashboard.store'
import { useTransactionsStore } from '../stores/transactions.store'
import { useContextMenu } from '../composables/useContextMenu'
import EditTransactionModal from '../components/modals/EditTransactionModal.vue'
import ContextMenu from '../components/base/ContextMenu.vue'
import CustomSelect from '../components/base/CustomSelect.vue'
import { DateInput } from '../components/base'
import PageLayout from '../layouts/PageLayout.vue'
import PageHeader from '../layouts/PageHeader.vue'
import { formatOperationAmount } from '../utils/formatCurrency'
import { normalizeDateToString, formatDateForDisplay } from '../utils/date'

const dashboardStore = useDashboardStore()
const transactionsStore = useTransactionsStore()

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
} = storeToRefs(transactionsStore)

// Lazy-load: загружаем полные списки при первом открытии страницы
onMounted(() => {
  if (!dashboardStore.operationsLoaded) {
    dashboardStore.fetchTransactionsAndOperationsInBackground()
  }
})

// Транзакции и операции — единственный источник: dashboard store
const transactions = computed(() => dashboardStore.transactions || [])
const operations = computed(() => dashboardStore.operations || [])

// справочник активов (для доп. инфы в подсказках)
const referenceData = computed(() => dashboardStore.referenceData || {})
const referenceAssets = computed(() => referenceData.value.assets || [])

// Обертки для совместимости
const deleteTransactions = async (transaction_ids) => {
  await transactionsStore.deleteTransactions(transaction_ids)
}

const deleteOperations = async (operation_ids) => {
  await transactionsStore.deleteOperations(operation_ids)
}

const editTransaction = async (updated_transaction) => {
  await transactionsStore.editTransaction(updated_transaction)
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

// поиск доп. инфы по активу (для подсказки)
const getAssetMeta = (name) => {
  if (!name) return null
  const meta = referenceAssets.value.find(a => a.name === name || a.ticker === name)
  return meta || null
}

// подсветка совпадения в названии актива
const highlightMatch = (text) => {
  if (!assetSearch.value) return text
  const t = text || ''
  const q = assetSearch.value
  const idx = t.toLowerCase().indexOf(q.toLowerCase())
  if (idx === -1) return t
  const before = t.slice(0, idx)
  const match = t.slice(idx, idx + q.length)
  const after = t.slice(idx + q.length)
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

// --- ГЛАВНЫЙ ФИЛЬТР ---
// Оптимизировано: ранний выход из проверок для лучшей производительности
const applyFilter = () => {
  const assetFilter = selectedAsset.value
  const portfolioFilter = selectedPortfolio.value
  const typeFilter = selectedType.value
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
    if (portfolioFilter && tx.portfolio_name !== portfolioFilter) return false
    if (typeFilter && tx.transaction_type !== typeFilter) return false

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
      // Фильтр по портфелю
      if (portfolioFilter && op.portfolio_name !== portfolioFilter) return false
      
      // Фильтр по типу операции
      if (typeFilter && op.operation_type !== typeFilter) return false
      
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
    if (periodPreset.value !== 'custom') {
      setPeriodPreset(periodPreset.value)
    }
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
  // Получаем оригинальную транзакцию для получения недостающих полей
  const originalTx = transactions.value.find(t => 
    (t.transaction_id || t.id) === (newTx.transaction_id || newTx.id)
  )
  
  if (!originalTx) {
    console.error('Оригинальная транзакция не найдена')
    return
  }
  
  const txData = {
    transaction_id: newTx.transaction_id || newTx.id || originalTx.transaction_id || originalTx.id,
    portfolio_asset_id: newTx.portfolio_asset_id || originalTx.portfolio_asset_id,
    asset_id: newTx.asset_id || originalTx.asset_id,
    transaction_type: typeof newTx.transaction_type === 'string' 
      ? (newTx.transaction_type === 'Покупка' || newTx.transaction_type.toLowerCase().includes('buy') ? 1 
        : (newTx.transaction_type === 'Погашение' || newTx.transaction_type.toLowerCase().includes('redemption') || newTx.transaction_type.toLowerCase().includes('погаш') || newTx.transaction_type.toLowerCase().includes('амортиз') ? 3 : 2))
      : (newTx.transaction_type || 1),
    quantity: parseFloat(newTx.quantity) || 0,
    price: parseFloat(newTx.price) || 0,
    transaction_date: newTx.transaction_date || originalTx.transaction_date,
    update_related_deposit: !!(newTx.updateRelatedDeposit && newTx.relatedDepositOperation?.id),
    related_deposit_operation_id: newTx.updateRelatedDeposit ? (newTx.relatedDepositOperation?.id ?? null) : null,
    related_deposit_amount: newTx.updateRelatedDeposit ? (newTx.relatedDepositOperation?.amount ?? null) : null,
    related_deposit_date: newTx.updateRelatedDeposit
      ? (newTx.relatedDepositOperation?.operation_date
          ? normalizeDateToString(newTx.relatedDepositOperation.operation_date)
          : null)
      : null,
  }
  
  if (txData.transaction_date) {
    const normalizedDate = normalizeDateToString(txData.transaction_date)
    if (normalizedDate) {
      txData.transaction_date = normalizedDate
    }
  }

  await editTransaction(txData)

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
</script>

<template>
  <PageLayout>
    <PageHeader title="История транзакций">
      <template #actions>
        <div class="header-actions">
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
          <div v-if="selectedTxIds.length > 0 && viewMode === 'transactions'" class="bulk-actions">
            <span class="selected-count">Выбрано: {{ selectedTxIds.length }}</span>
            <button @click="deleteSelected" class="btn btn-danger-soft" :disabled="selectedTxIds.length === 0">
              Удалить выбранные ({{ selectedTxIds.length }})
            </button>
          </div>
          <div v-if="selectedOpIds.length > 0 && viewMode === 'operations'" class="bulk-actions">
            <span class="selected-count">Выбрано: {{ selectedOpIds.length }}</span>
            <button @click="deleteSelectedOperations" class="btn btn-danger-soft" :disabled="selectedOpIds.length === 0">
              Удалить выбранные ({{ selectedOpIds.length }})
            </button>
          </div>
        </div>
      </template>
    </PageHeader>

    <div class="transactions-content">
      <div class="main-content">

        <div style="display: flex; gap: 20px;">
          <div class="card">
          <div class="toolbar">
            <div class="filters-top">
          <!-- Поиск по активу -->
          <div v-if="viewMode === 'transactions'" class="asset-search-wrapper">
            <span class="select-label">Актив</span>
            <span class="input-icon">🔍</span>
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
                <span style="display: block; margin-bottom: 4px;">🔍</span>
                Ничего не найдено
              </li>
            </ul>
          </div>
          
          <div v-if="viewMode === 'operations'" class="asset-search-wrapper">
            <span class="select-label">Актив</span>
            <span class="input-icon">🔍</span>
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
                <span style="display: block; margin-bottom: 4px;">🔍</span>
                Ничего не найдено
              </li>
            </ul>
          </div>

          <div class="select-group">
            <CustomSelect
              v-model="selectedPortfolio"
              :options="portfolios"
              label="Портфель"
              placeholder="Все портфели"
              empty-option-text="Все портфели"
              option-label="name"
              option-value="name"
              @change="applyFilter"
            />
            <CustomSelect
              v-model="selectedType"
              :options="viewMode === 'transactions' ? txTypes.map(t => ({ value: t, label: t })) : operationTypes.map(t => ({ value: t, label: t }))"
              label="Тип"
              placeholder="Все типы"
              empty-option-text="Все типы"
              @change="applyFilter"
            />
            <CustomSelect
              v-if="viewMode === 'operations'"
              v-model="selectedCurrency"
              :options="[
                { value: 'RUB', label: 'Рубли (RUB)' },
                { value: 'ORIGINAL', label: 'Оригинальная валюта' }
              ]"
              label="Валюта отображения"
              placeholder="Выберите валюту"
              @change="applyFilter"
            />
          </div>
          
          <button @click="resetFilters" class="btn btn-ghost reset-btn" title="Сбросить фильтры">
            <span class="reset-icon">↺</span>
          </button>
            </div>

            <div class="filters-bottom">
           <div class="chips-group">
            <button v-for="p in ['today', 'week', 'month', 'year', 'all']" 
                    :key="p" 
                    class="chip" 
                    :class="{ active: periodPreset === p }"
                    @click="setPeriodPreset(p); periodPreset = p">
              {{ {today:'Сегодня', week:'Неделя', month:'Месяц', year:'Год', all:'Всё время'}[p] }}
            </button>
            <button class="chip" :class="{ active: periodPreset === 'custom' }" @click="periodPreset = 'custom'">
              Период...
            </button>
          </div>
          
           <div v-if="periodPreset === 'custom'" class="date-range">
            <DateInput v-model="startDate" class="date-input" />
            <span class="separator">—</span>
            <DateInput v-model="endDate" class="date-input" />
          </div>
            </div>
          </div>
          
          <div class="table-container">
          <!-- Таблица транзакций -->
          <table v-if="viewMode === 'transactions'" class="transactions-table">
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
                <td class="text-right num-font">{{ tx.price.toLocaleString() }}</td>
                <td class="text-right num-font font-semibold">
                  {{ (tx.quantity * tx.price).toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) }}
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

          <!-- Таблица операций -->
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
                <td class="text-right num-font font-semibold" :class="getOperationAmount(op) >= 0 ? 'text-green' : 'text-red'">
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

          <!-- Правый блок с калькулятором -->
          <div class="calculator-sidebar">
          <div class="calculator-card">
            <h3 class="calculator-title">
              {{ viewMode === 'transactions' ? 'Суммы транзакций' : 'Калькулятор операций' }}
            </h3>
            
            <!-- Для транзакций: сумма покупок и продаж -->
            <div v-if="viewMode === 'transactions'" class="transactions-summary">
              <div class="summary-item">
                <span class="summary-item-label">Покупки:</span>
                <span class="summary-item-value text-green">
                  {{ transactionsSummary.buy.toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' }) }}
                </span>
              </div>
              <div class="summary-item">
                <span class="summary-item-label">Продажи:</span>
                <span class="summary-item-value text-red">
                  {{ transactionsSummary.sell.toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' }) }}
                </span>
              </div>
              <div class="summary-item">
                <span class="summary-item-label">Оборот:</span>
                <span class="summary-item-value text-red">
                  {{ (transactionsSummary.buy + transactionsSummary.sell).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' }) }}
                </span>
              </div>
            </div>

            <!-- Для операций: калькулятор -->
            <div v-else class="operations-calculator">
              <!-- Формула -->
              <div class="formula-display">
                <div v-if="calculatorFormula.length === 0" class="formula-empty">
                  Добавьте элементы формулы
                </div>
                <div v-else class="formula-items">
                  <div 
                    v-for="(item, index) in calculatorFormula" 
                    :key="index"
                    class="formula-item"
                    :class="{ 'formula-operator': item.type === 'operator' }"
                  >
                    <span class="formula-item-text">{{ item.label }}</span>
                    <button 
                      @click="removeFromFormula(index)" 
                      class="formula-remove-btn"
                      title="Удалить"
                    >
                      ×
                    </button>
                  </div>
                </div>
              </div>

              <!-- Результат -->
              <div class="calculator-result">
                <span class="result-label">Результат:</span>
                <span class="result-value" :class="calculatorResult >= 0 ? 'text-green' : 'text-red'">
                  {{ calculatorResult.toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' }) }}
                </span>
              </div>

              <!-- Кнопки операторов -->
              <div class="calculator-operators">
                <button 
                  @click="addToFormula('operator', '+', '+')" 
                  class="calc-btn calc-operator"
                  :disabled="calculatorFormula.length === 0 || calculatorFormula[calculatorFormula.length - 1]?.type === 'operator'"
                >
                  +
                </button>
                <button 
                  @click="addToFormula('operator', '-', '-')" 
                  class="calc-btn calc-operator"
                  :disabled="calculatorFormula.length === 0 || calculatorFormula[calculatorFormula.length - 1]?.type === 'operator'"
                >
                  −
                </button>
                <button 
                  @click="clearFormula()" 
                  class="calc-btn calc-clear"
                  :disabled="calculatorFormula.length === 0"
                >
                  Очистить
                </button>
              </div>

              <!-- Доступные типы операций -->
              <div class="calculator-operations">
                <div class="operations-label">Добавить в формулу:</div>
                <div class="operations-buttons">
                  <button 
                    v-for="opType in operationTypes" 
                    :key="opType"
                    @click="addToFormula('operation', opType, opType)"
                    class="calc-btn calc-operation"
                    :disabled="calculatorFormula.length > 0 && calculatorFormula[calculatorFormula.length - 1]?.type === 'operation'"
                  >
                    {{ opType }}
                  </button>
                </div>
              </div>

              <!-- Суммы по типам операций -->
              <div class="operations-sums">
                <div class="sums-label">Суммы по типам:</div>
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
            </div>
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
/* --- Разметка и типографика --- */
.transactions-content {
  display: flex;
  gap: 24px;
  align-items: flex-start;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #1f2937;
}

.main-content {
  flex: 1;
  min-width: 0;
}

.calculator-sidebar {
  width: 360px;
  flex-shrink: 0;
  position: sticky;
  top: 24px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.view-mode-switcher {
  display: flex;
  gap: 4px;
  background: #f3f4f6;
  padding: 4px;
  border-radius: 8px;
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

/* --- Массовые действия --- */
.bulk-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fef2f2;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid #fee2e2;
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

/* --- Карточка и структура --- */
.card {
  background: #fff;
  width: 100%;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  border: 1px solid #e5e7eb;
  overflow: visible; /* позволяет выпадающим спискам выходить за границы */
}

/* --- Панель инструментов --- */
.toolbar {
  padding: 20px;
  border-bottom: 1px solid #f3f4f6;
}

.filters-top {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.filters-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* Поля ввода */
.input-wrapper {
  position: relative;
  flex: 1;
  max-width: 300px;
}

.asset-search-wrapper {
  position: relative;
  flex: 1;
  max-width: 300px;
  min-width: 180px;
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
  letter-spacing: 0.5px;
  z-index: 2;
  pointer-events: none;
}

.input-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #6b7280;
  font-size: 16px;
  z-index: 1;
  pointer-events: none;
  transition: color 0.2s ease;
}

.asset-search-wrapper:focus-within .input-icon {
  color: #3b82f6;
}

.form-input, .form-select {
  width: 100%;
  padding: 10px 40px 10px 36px;
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: all 0.2s ease;
  background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
  color: #111827;
  font-weight: 400;
  min-height: 42px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.form-input::placeholder {
  color: #9ca3af;
}

.form-input:hover {
  border-color: #d1d5db;
  background: linear-gradient(180deg, #fafafa 0%, #f5f5f5 100%);
  box-shadow: 0 2px 4px rgba(0,0,0,0.08);
  transform: translateY(-1px);
}

.form-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.1), 0 4px 12px rgba(59,130,246,0.15);
  background: #fff;
  transform: translateY(0);
}
.form-select {
  padding-left: 12px;
  padding-right: 36px;
  cursor: pointer;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236b7280' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  background-size: 12px;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
}

/* Скрываем старые select элементы, если они еще используются */
.form-select {
  display: none;
}
.form-input:hover, .form-select:hover {
  border-color: #d1d5db;
  background-color: #fafafa;
}
.form-input:focus, .form-select:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
  background-color: #fff;
}
.form-select option {
  padding: 10px;
  background-color: #fff;
  color: #111827;
}

.select-group {
  display: flex;
  gap: 12px;
  flex: 1;
}


.reset-btn {
  font-size: 18px;
  padding: 8px 12px;
  color: #6b7280;
  background: #f9fafb;
  border: 1.5px solid #e5e7eb;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  height: 42px;
}
.reset-btn:hover {
  background: #f3f4f6;
  color: #1f2937;
  border-color: #d1d5db;
}
.reset-btn:active {
  transform: scale(0.95);
}
.reset-icon {
  display: inline-block;
  transition: transform 0.2s ease;
}
.reset-btn:hover .reset-icon {
  transform: rotate(-90deg);
}
.clear-btn {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: #f3f4f6;
  border: 1.5px solid transparent;
  font-size: 18px;
  color: #6b7280;
  cursor: pointer;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  z-index: 2;
  line-height: 1;
  padding: 0;
  font-weight: 300;
}
.clear-btn:hover {
  background: #fee2e2;
  border-color: #fca5a5;
  color: #dc2626;
  transform: translateY(-50%) scale(1.1);
  box-shadow: 0 2px 4px rgba(220,38,38,0.2);
}
.clear-btn:active {
  transform: translateY(-50%) scale(0.95);
}

/* Фильтры-чипсы */
.chips-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
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
  transition: all 0.2s ease;
  white-space: nowrap;
  position: relative;
  overflow: hidden;
}
.chip::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
  transition: left 0.5s;
}
.chip:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.chip:hover::before {
  left: 100%;
}
.chip.active {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  color: #2563eb;
  font-weight: 600;
  border-color: #3b82f6;
  box-shadow: 0 2px 8px rgba(59,130,246,0.2);
  transform: translateY(-1px);
}
.chip.active::before {
  display: none;
}

/* Диапазон дат */
.date-range {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1.5px solid #e5e7eb;
}
.date-input {
  padding: 8px 12px;
  width: auto;
  min-width: 140px;
  border: 1.5px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
  transition: all 0.2s ease;
}
.date-input:hover {
  border-color: #9ca3af;
  background: #fff;
}
.date-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
  outline: none;
}
.separator {
  color: #6b7280;
  font-weight: 500;
  font-size: 14px;
  user-select: none;
}

/* --- Таблица --- */
.table-container {
  overflow-x: auto;
}
.transactions-table {
  width: 100%;
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
.transactions-table tr:last-child td { border-bottom: none; }
.transactions-table tr:hover { background: #f9fafb; }

/* Настройки колонок */
.w-checkbox { width: 40px; text-align: center; }
.w-actions { width: 40px; }
.text-right { text-align: right !important; }
.font-medium { font-weight: 500; color: #111827; }
.font-semibold { font-weight: 600; color: #111827; }
.text-secondary { color: #6b7280; font-size: 13px; }
.td-date { color: #374151; white-space: nowrap; }
.num-font { font-family: 'SF Mono', 'Roboto Mono', Menlo, monospace; font-size: 13px; letter-spacing: -0.5px; }

/* Бейджи */
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}
.badge-buy { background: #dcfce7; color: #166534; }
.badge-sell { background: #fee2e2; color: #991b1b; }
.badge-dividend { 
  background: rgba(37, 99, 235, 0.1); 
  color: var(--payout-dividends, #2563eb); 
}
.badge-coupon { 
  background: rgba(6, 182, 212, 0.1); 
  color: var(--payout-coupons, #06b6d4); 
}
.badge-amortization {
  background: rgba(251, 146, 60, 0.1);
  color: var(--payout-amortizations, #fb923c);
}
.badge-other { background: #f3f4f6; color: #4b5563; }
.badge-deposit { background: #ccfbf1; color: #0f766e; }
.badge-withdraw { background: #ffedd5; color: #9a3412; }
.badge-tax { background: #fee2e2; color: #991b1b; }
.badge-commission { background: #fef3c7; color: #92400e; }
.badge-tax { background: #fee2e2; color: #991b1b; }
.badge-commission { background: #fef3c7; color: #92400e; }

/* Кнопка действий */
.icon-btn {
  background: none;
  border: none;
  color: #9ca3af;
  font-size: 16px;
  cursor: pointer;
  padding: 4px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}
.icon-btn:hover { 
  color: #374151; 
  background: #f3f4f6;
}

/* Выпадающий список активов (поиск) */
.asset-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  width: 100%;
  background: white;
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  margin-top: 4px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.1), 0 4px 10px rgba(0,0,0,0.05);
  list-style: none;
  padding: 6px 0;
  max-height: 300px;
  overflow-y: auto;
  z-index: 100;
  animation: slideDown 0.2s ease;
}
@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.asset-dropdown::-webkit-scrollbar {
  width: 6px;
}
.asset-dropdown::-webkit-scrollbar-track {
  background: #f9fafb;
  border-radius: 3px;
}
.asset-dropdown::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}
.asset-dropdown::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
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
  padding-left: 13px;
}
.asset-option:active {
  background: #e5e7eb;
}
.asset-option mark {
  background: #fef3c7;
  color: #92400e;
  padding: 0 2px;
  border-radius: 2px;
  font-weight: 600;
}
.meta-ticker {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  color: #1e40af;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 12px;
  letter-spacing: 0.3px;
  white-space: nowrap;
}
.asset-empty {
  padding: 20px;
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
  font-style: italic;
}

/* Итоги в подвале */
.card-footer {
  padding: 16px 20px;
  border-top: 1px solid #e5e7eb;
  background: #fafafa;
  border-radius: 0 0 12px 12px;
}
.summary-block {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  align-items: baseline;
}
.summary-label { color: #6b7280; font-size: 14px; }
.summary-value { font-size: 18px; font-weight: 700; color: #111827; }

/* Пустое состояние */
.empty-cell { text-align: center; padding: 40px; }
.empty-state { color: #9ca3af; }
.empty-icon { font-size: 32px; display: block; margin-bottom: 8px; opacity: 0.5; }

/* Чекбокс */
.custom-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: #2563eb;
}

/* --- Калькулятор --- */
.calculator-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.calculator-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: #111827;
  border-bottom: 2px solid #e5e7eb;
  padding-bottom: 8px;
}

/* Суммы транзакций */
.transactions-summary {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: #f9fafb;
  border-radius: 6px;
}

.summary-item-label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.summary-item-value {
  font-size: 15px;
  font-weight: 700;
}

/* Калькулятор операций */
.operations-calculator {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.formula-display {
  min-height: 50px;
  padding: 10px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.formula-empty {
  color: #9ca3af;
  font-size: 12px;
  text-align: center;
  padding: 8px 0;
}

.formula-items {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.formula-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 12px;
}

.formula-item.formula-operator {
  background: #eff6ff;
  border-color: #3b82f6;
  font-weight: 600;
  font-size: 14px;
}

.formula-item-text {
  color: #111827;
}

.formula-remove-btn {
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  padding: 0;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
  transition: all 0.2s;
}

.formula-remove-btn:hover {
  background: #fee2e2;
  color: #dc2626;
}

.calculator-result {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: #f0fdf4;
  border: 2px solid #86efac;
  border-radius: 6px;
}

.result-label {
  font-size: 12px;
  font-weight: 600;
  color: #166534;
}

.result-value {
  font-size: 16px;
  font-weight: 700;
}

.calculator-operators {
  display: flex;
  gap: 6px;
}

.calc-btn {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
  color: #111827;
}

.calc-btn:hover:not(:disabled) {
  background: #f3f4f6;
  border-color: #9ca3af;
}

.calc-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.calc-operator {
  flex: 1;
  font-size: 16px;
  font-weight: 600;
  background: #eff6ff;
  border-color: #3b82f6;
  color: #2563eb;
}

.calc-operator:hover:not(:disabled) {
  background: #dbeafe;
}

.calc-clear {
  flex: 1;
  background: #fee2e2;
  border-color: #fca5a5;
  color: #dc2626;
}

.calc-clear:hover:not(:disabled) {
  background: #fecaca;
}

.calculator-operations {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.operations-label {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.operations-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.calc-operation {
  text-align: center;
  justify-content: center;
  background: #f9fafb;
  font-size: 12px;
  padding: 6px 8px;
}

.calc-operation:hover:not(:disabled) {
  background: #f3f4f6;
  border-color: #3b82f6;
}

.operations-sums {
  margin-top: 4px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}

.sums-label {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sums-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.sum-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 10px;
  background: #f9fafb;
  border-radius: 4px;
  font-size: 12px;
}

.sum-type {
  color: #6b7280;
  font-weight: 500;
}

.sum-value {
  color: #111827;
  font-weight: 600;
}

/* Адаптивность */
@media (max-width: 1024px) {
  .page-layout {
    flex-direction: column;
  }
  
  .calculator-sidebar {
    width: 100%;
    position: static;
  }
}
</style>
