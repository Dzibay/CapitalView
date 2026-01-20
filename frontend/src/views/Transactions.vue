<script setup>
import { ref, computed, watch } from 'vue'
import { useDashboardStore } from '../stores/dashboard.store'
import { useTransactionsStore } from '../stores/transactions.store'
import { useContextMenu } from '../composables/useContextMenu'
import EditTransactionModal from '../components/modals/EditTransactionModal.vue'
import ContextMenu from '../components/ContextMenu.vue'

// Используем stores вместо inject
const dashboardStore = useDashboardStore()
const transactionsStore = useTransactionsStore()

const transactions = computed(() => dashboardStore.transactions || [])

// справочник активов (для доп. инфы в подсказках)
const referenceData = computed(() => dashboardStore.referenceData || {})
const referenceAssets = computed(() => referenceData.value.assets || [])

// Обертки для совместимости
const deleteTransactions = async (transaction_ids) => {
  await transactionsStore.deleteTransactions(transaction_ids)
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

const portfolios = computed(() => {
  const tx = transactions.value
  if (!tx.length) return []
  const portfolioMap = new Map()
  for (const t of tx) {
    if (t.portfolio_id && !portfolioMap.has(t.portfolio_id)) {
      portfolioMap.set(t.portfolio_id, { id: t.portfolio_id, name: t.portfolio_name })
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

// --- ФИЛЬТРЫ ---
const selectedAsset = ref('')
const assetSearch = ref('')
const recentAssets = ref([])

const selectedPortfolio = ref('')
const selectedType = ref('') // тип операции

const periodPreset = ref('month') // today | week | month | quarter | year | all | custom
const startDate = ref('')
const endDate = ref('')

const globalSearch = ref('')

// отфильтрованные транзакции
const filteredTransactions = ref([])

// выделенные транзакции
const selectedTxIds = ref([])

// главный чекбокс
const allSelected = ref(false)

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

// --- ВСПОМОГАТЕЛЬНОЕ: нормализация типа ---
const normalizeType = (type) => {
  const t = (type || '').toString().toLowerCase()
  if (t.includes('покуп') || t.includes('buy')) return 'buy'
  if (t.includes('прод') || t.includes('sell')) return 'sell'
  if (t.includes('див') || t.includes('div')) return 'dividend'
  if (t.includes('купон') || t.includes('coupon')) return 'coupon'
  if (t.includes('налог') || t.includes('tax')) return 'tax'
  if (t.includes('ввод') || t.includes('депозит') || t.includes('deposit')) return 'deposit'
  if (t.includes('вывод') || t.includes('withdraw')) return 'withdraw'
  return 'other'
}

// Функция для получения даты в формате YYYY-MM-DD по локальному времени пользователя
const getLocalYMD = (dateObj) => {
  if (!dateObj) return ''
  const year = dateObj.getFullYear()
  const month = String(dateObj.getMonth() + 1).padStart(2, '0') // Месяцы 0-11
  const day = String(dateObj.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
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
const formatDate = (date) => new Date(date).toLocaleDateString()

// --- фильтр активов для дропа ---
const filteredAssetsList = computed(() => {
  const base = assets.value
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

  selectedTxIds.value = []
  allSelected.value = false
}

// сброс фильтров
const resetFilters = () => {
  selectedAsset.value = ''
  assetSearch.value = ''
  selectedPortfolio.value = ''
  selectedType.value = ''
  globalSearch.value = ''
  periodPreset.value = 'all'
  startDate.value = ''
  endDate.value = ''
  applyFilter()
}

// следим за обновлением транзакций
watch(transactions, () => {
  // при первой загрузке ставим дефолтный пресет
  if (!startDate.value && !endDate.value && periodPreset.value !== 'all') {
    setPeriodPreset(periodPreset.value)
  }
  applyFilter()
}, { immediate: true })

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

// выбор всех
const toggleAll = () => {
  if (allSelected.value) {
    selectedTxIds.value = filteredTransactions.value.map(tx => tx.transaction_id)
  } else {
    selectedTxIds.value = []
  }
}

watch(selectedTxIds, () => {
  allSelected.value =
    selectedTxIds.value.length > 0 &&
    selectedTxIds.value.length === filteredTransactions.value.length
})

// удаление выбранных
const deleteSelected = () => {
  if (selectedTxIds.value.length &&
      confirm(`Вы уверены, что хотите удалить ${selectedTxIds.value.length} транзакций?`)) {
    deleteTransactions(selectedTxIds.value)
    selectedTxIds.value = []
    allSelected.value = false
  }
}

// удалить одну строку
const deleteOne = (txId) => {
  if (confirm('Удалить эту транзакцию?')) {
    deleteTransactions([txId])
  }
}

// модалка
const openEditModal = (tx) => {
  // Копируем транзакцию и преобразуем дату в формат YYYY-MM-DD для input[type="date"]
  const txCopy = { ...tx }
  if (txCopy.transaction_date) {
    // Если дата в формате ISO или timestamp, преобразуем в YYYY-MM-DD
    const date = new Date(txCopy.transaction_date)
    if (!isNaN(date.getTime())) {
      txCopy.transaction_date = date.toISOString().split('T')[0]
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
  
  // Преобразуем данные для API
  const txData = {
    transaction_id: newTx.transaction_id || newTx.id || originalTx.transaction_id || originalTx.id,
    portfolio_asset_id: newTx.portfolio_asset_id || originalTx.portfolio_asset_id,
    asset_id: newTx.asset_id || originalTx.asset_id,
    transaction_type: typeof newTx.transaction_type === 'string' 
      ? (newTx.transaction_type === 'Покупка' || newTx.transaction_type.toLowerCase().includes('buy') ? 1 : 2)
      : (newTx.transaction_type || 1),
    quantity: parseFloat(newTx.quantity) || 0,
    price: parseFloat(newTx.price) || 0,
    transaction_date: newTx.transaction_date || originalTx.transaction_date
  }
  
  // Преобразуем дату в ISO формат, если нужно
  if (txData.transaction_date && !txData.transaction_date.includes('T')) {
    const date = new Date(txData.transaction_date)
    if (!isNaN(date.getTime())) {
      txData.transaction_date = date.toISOString()
    }
  }
  
  await editTransaction(txData)
  showEditModal.value = false
}

// --- SUMMARY по отфильтрованным ---
const summary = computed(() => {
  const res = {
    total: 0,
    byType: {}
  }

  for (const tx of filteredTransactions.value) {
    const value = Number(tx.quantity || 0) * Number(tx.price || 0)
    const slug = normalizeType(tx.transaction_type)

    res.total += value
    if (!res.byType[slug]) {
      res.byType[slug] = { label: tx.transaction_type, value: 0 }
    }
    res.byType[slug].value += value
  }

  // округляем
  res.total = Math.round(res.total * 100) / 100
  for (const k in res.byType) {
    res.byType[k].value = Math.round(res.byType[k].value * 100) / 100
  }

  return res
})
</script>

<template>
  <div class="transactions-page">
    <div class="header-row">
      <h1 class="page-title">История транзакций</h1>
      <div v-if="selectedTxIds.length > 0" class="bulk-actions">
        <span class="selected-count">Выбрано: {{ selectedTxIds.length }}</span>
        <button @click="deleteSelected" class="btn btn-danger-soft">
          Удалить выбранные
        </button>
      </div>
    </div>

    <div class="card">
      
      <div class="toolbar">
        <div class="filters-top">
          <div class="input-wrapper asset-search-wrapper">
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
              <li v-if="filteredAssetsList.length === 0" class="asset-empty">Ничего не найдено</li>
            </ul>
          </div>

          <div class="select-group">
            <select v-model="selectedPortfolio" class="form-select">
              <option value="">Все портфели</option>
              <option v-for="p in portfolios" :key="p.id" :value="p.name">{{ p.name }}</option>
            </select>
            <select v-model="selectedType" class="form-select">
              <option value="">Все типы</option>
              <option v-for="t in txTypes" :key="t" :value="t">{{ t }}</option>
            </select>
          </div>
          
          <button @click="resetFilters" class="btn btn-ghost reset-btn" title="Сбросить фильтры">
             ↺
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
            <input type="date" v-model="startDate" class="form-input date-input" />
            <span class="separator">—</span>
            <input type="date" v-model="endDate" class="form-input date-input" />
          </div>
        </div>
      </div>

      <div class="table-container">
        <table class="transactions-table">
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
      </div>
      
      <div v-if="filteredTransactions.length > 0" class="card-footer">
         <div class="summary-block">
            <span class="summary-label">Оборот за период:</span>
            <span class="summary-value">{{ summary.total.toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' }) }}</span>
         </div>
      </div>
    </div>

    <EditTransactionModal :visible="showEditModal" :transaction="currentTransaction" @close="showEditModal = false" @save="handleSaveEdit" />
    
    <ContextMenu
      @editTransaction="handleEditTransaction"
      @deleteTransaction="handleDeleteTransaction"
    />
  </div>
</template>

<style scoped>
/* --- Layout & Typography --- */
.transactions-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 20px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #1f2937;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  color: #111827;
}

/* --- Bulk Actions --- */
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

/* --- Card & Structure --- */
.card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  border: 1px solid #e5e7eb;
  overflow: visible; /* allows dropdowns to overflow */
}

/* --- Toolbar --- */
.toolbar {
  padding: 20px;
  border-bottom: 1px solid #f3f4f6;
}

.filters-top {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.filters-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* Inputs */
.input-wrapper {
  position: relative;
  flex: 1;
  max-width: 300px;
}
.input-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: #9ca3af;
  font-size: 14px;
}
.form-input, .form-select {
  width: 100%;
  padding: 8px 12px 8px 32px; /* padding left for icon */
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}
.form-select {
  padding-left: 12px;
  cursor: pointer;
  background-color: #fff;
}
.form-input:focus, .form-select:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59,130,246,0.1);
}

.select-group {
  display: flex;
  gap: 12px;
}

.reset-btn {
  font-size: 18px;
  padding: 0 10px;
  color: #6b7280;
  background: transparent;
  border: none;
  cursor: pointer;
  border-radius: 4px;
}
.reset-btn:hover { background: #f3f4f6; color: #1f2937; }
.clear-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  font-size: 18px;
  color: #9ca3af;
  cursor: pointer;
}

/* Chips */
.chips-group {
  display: flex;
  gap: 8px;
}
.chip {
  background: #f3f4f6;
  border: none;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
  color: #4b5563;
  cursor: pointer;
  transition: all 0.2s;
}
.chip:hover { background: #e5e7eb; }
.chip.active {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 500;
  box-shadow: 0 0 0 1px #bfdbfe;
}

/* Date Range */
.date-range {
  display: flex;
  align-items: center;
  gap: 8px;
}
.date-input {
  padding-left: 12px;
  width: auto;
}
.separator { color: #9ca3af; }

/* --- Table --- */
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

/* Column Specifics */
.w-checkbox { width: 40px; text-align: center; }
.w-actions { width: 40px; }
.text-right { text-align: right !important; }
.font-medium { font-weight: 500; color: #111827; }
.font-semibold { font-weight: 600; color: #111827; }
.text-secondary { color: #6b7280; font-size: 13px; }
.td-date { color: #374151; white-space: nowrap; }
.num-font { font-family: 'SF Mono', 'Roboto Mono', Menlo, monospace; font-size: 13px; letter-spacing: -0.5px; }

/* Badges */
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
.badge-dividend { background: #dbeafe; color: #1e40af; }
.badge-coupon { background: #f3e8ff; color: #6b21a8; }
.badge-other { background: #f3f4f6; color: #4b5563; }
.badge-deposit { background: #ccfbf1; color: #0f766e; }
.badge-withdraw { background: #ffedd5; color: #9a3412; }

/* Actions Button */
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

/* Asset Dropdown (Search) */
.asset-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  width: 100%;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  margin-top: 4px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  list-style: none;
  padding: 0;
  max-height: 250px;
  overflow-y: auto;
  z-index: 50;
}
.asset-option {
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.asset-option:hover { background: #f9fafb; }
.meta-ticker {
  background: #f3f4f6;
  color: #6b7280;
  font-size: 11px;
  padding: 1px 4px;
  border-radius: 4px;
}
.asset-empty { padding: 12px; text-align: center; color: #9ca3af; font-size: 13px; }

/* Footer Summary */
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

/* Empty State */
.empty-cell { text-align: center; padding: 40px; }
.empty-state { color: #9ca3af; }
.empty-icon { font-size: 32px; display: block; margin-bottom: 8px; opacity: 0.5; }

/* Custom Checkbox */
.custom-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: #2563eb;
}
</style>
