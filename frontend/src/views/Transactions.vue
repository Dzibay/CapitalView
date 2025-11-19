<script setup>
import { inject, ref, computed, watch } from 'vue'
import EditTransactionModal from '../components/modals/EditTransactionModal.vue'

// данные и функции от родителя
const dashboardData = inject('dashboardData')
const deleteTransactions = inject('deleteTransactions')
const editTransaction = inject('editTransaction')

const transactions = computed(() => dashboardData.value?.data?.transactions || [])

// справочник активов (для доп. инфы в подсказках)
const referenceData = computed(() => dashboardData.value?.data?.referenceData || {})
const referenceAssets = computed(() => referenceData.value.assets || [])

// --- списки для фильтров ---
const assets = computed(() => [...new Set(transactions.value.map(t => t.asset_name))])

const portfolios = computed(() => [
  ...new Map(
    transactions.value.map(t => [
      t.portfolio_id,
      { id: t.portfolio_id, name: t.portfolio_name }
    ])
  ).values()
])

const txTypes = computed(() => [...new Set(transactions.value.map(t => t.transaction_type))])

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

// --- ВСПОМОГАТЕЛЬНОЕ: нормализация типа ---
const normalizeType = (type) => {
  const t = (type || '').toString().toLowerCase()
  if (t.includes('покуп') || t.includes('buy')) return 'buy'
  if (t.includes('прод') || t.includes('sell')) return 'sell'
  if (t.includes('див') || t.includes('div')) return 'dividend'
  if (t.includes('купон') || t.includes('coupon')) return 'coupon'
  if (t.includes('комис') || t.includes('commission')) return 'commission'
  if (t.includes('налог') || t.includes('tax')) return 'tax'
  if (t.includes('ввод') || t.includes('депозит') || t.includes('deposit')) return 'deposit'
  if (t.includes('вывод') || t.includes('withdraw')) return 'withdraw'
  return 'other'
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
    startDate.value = start.toISOString().slice(0, 10)
    endDate.value = now.toISOString().slice(0, 10)
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
const applyFilter = () => {
  const assetFilter = selectedAsset.value
  const portfolioFilter = selectedPortfolio.value
  const typeFilter = selectedType.value
  const term = globalSearch.value.trim().toLowerCase()

  let start = null
  let end = null

  if (periodPreset.value === 'custom') {
    start = startDate.value ? new Date(startDate.value) : null
    end = endDate.value ? new Date(endDate.value) : null
  } else {
    if (startDate.value) start = new Date(startDate.value)
    if (endDate.value) end = new Date(endDate.value)
  }

  filteredTransactions.value = transactions.value.filter(tx => {
    // актив
    const matchAsset = assetFilter ? tx.asset_name === assetFilter : true

    // портфель
    const matchPortfolio = portfolioFilter ? tx.portfolio_name === portfolioFilter : true

    // тип
    const matchType = typeFilter ? tx.transaction_type === typeFilter : true

    // период
    const txDate = new Date(tx.transaction_date)
    const matchStart = start ? txDate >= start : true
    const matchEnd = end ? txDate <= end : true

    // глобальный поиск
    let matchGlobal = true
    if (term) {
      const haystack = [
        tx.asset_name,
        tx.portfolio_name,
        tx.transaction_type,
        tx.quantity,
        tx.price,
        formatDate(tx.transaction_date)
      ].join(' ').toLowerCase()
      matchGlobal = haystack.includes(term)
    }

    return matchAsset && matchPortfolio && matchType && matchStart && matchEnd && matchGlobal
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
  currentTransaction.value = { ...tx }
  showEditModal.value = true
}

const handleSaveEdit = async (newTx) => {
  await editTransaction(newTx)
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
    <h1 class="page-title">История транзакций</h1>

    <!-- ФИЛЬТРЫ -->
    <div class="filters">
      <div class="filters-left">
        <select v-model="selectedPortfolio">
          <option value="">Все портфели</option>
          <option v-for="p in portfolios" :key="p.id" :value="p.name">
            {{ p.name }}
          </option>
        </select>

        <!-- Тип операции -->
        <select v-model="selectedType">
          <option value="">Все типы</option>
          <option v-for="t in txTypes" :key="t" :value="t">
            {{ t }}
          </option>
        </select>

        <!-- Поиск по активам -->
        <div class="asset-search-wrapper">
          <div class="search-input-group">
            <input
              type="text"
              v-model="assetSearch"
              placeholder="Поиск актива..."
              class="asset-search-input"
            />
            <button
              v-if="assetSearch"
              @click="assetSearch = ''; selectedAsset = ''; applyFilter()"
              class="clear-search-btn"
              title="Очистить поиск"
            >
              &times;
            </button>
          </div>

          <ul
            v-if="assetSearch && selectedAsset !== assetSearch"
            class="asset-dropdown"
          >
            <li
              v-for="a in filteredAssetsList"
              :key="a"
              @click="selectAssetFilter(a)"
              class="asset-option"
            >
              <div class="asset-option-main">
                <span v-html="highlightMatch(a)" />
              </div>
              <div v-if="getAssetMeta(a)" class="asset-option-meta">
                <span class="ticker">
                  {{ getAssetMeta(a).ticker }}
                </span>
                <span class="price" v-if="getAssetMeta(a).last_price">
                  · {{ getAssetMeta(a).last_price }} {{ getAssetMeta(a).currency_ticker || '' }}
                </span>
              </div>
            </li>

            <li v-if="filteredAssetsList.length === 0" class="asset-empty">
              Ничего не найдено
            </li>

            <li v-if="recentAssets.length" class="recent-label">
              Недавние:
            </li>
            <li
              v-for="ra in recentAssets"
              :key="'recent-' + ra"
              class="asset-recent-chip"
              @click="selectAssetFilter(ra)"
            >
              {{ ra }}
            </li>
          </ul>
        </div>

        <!-- Быстрые периоды -->
        <div class="quick-periods">
          <button
            type="button"
            class="chip"
            :class="{ active: periodPreset === 'today' }"
            @click="setPeriodPreset('today'); periodPreset = 'today'"
          >
            Сегодня
          </button>
          <button
            type="button"
            class="chip"
            :class="{ active: periodPreset === 'week' }"
            @click="setPeriodPreset('week'); periodPreset = 'week'"
          >
            Неделя
          </button>
          <button
            type="button"
            class="chip"
            :class="{ active: periodPreset === 'month' }"
            @click="setPeriodPreset('month'); periodPreset = 'month'"
          >
            Месяц
          </button>
          <button
            type="button"
            class="chip"
            :class="{ active: periodPreset === 'year' }"
            @click="setPeriodPreset('year'); periodPreset = 'year'"
          >
            Год
          </button>
          <button
            type="button"
            class="chip"
            :class="{ active: periodPreset === 'all' }"
            @click="setPeriodPreset('all'); periodPreset = 'all'"
          >
            Всё время
          </button>
          <button
            type="button"
            class="chip"
            :class="{ active: periodPreset === 'custom' }"
            @click="periodPreset = 'custom'"
          >
            Свой период
          </button>
        </div>

        <!-- Ручной выбор дат только для custom -->
        <div v-if="periodPreset === 'custom'" class="custom-dates">
          <input type="date" v-model="startDate" />
          <input type="date" v-model="endDate" />
        </div>
      </div>

      <!-- Глобальный поиск -->
      <div class="filters-right">
        <button @click="resetFilters" class="reset-filter-btn">
          Сбросить 🔄
        </button>
      </div>
    </div>

    <!-- ПАНЕЛЬ ДЕЙСТВИЙ -->
    <div class="actions-bar">
      <button
        @click="deleteSelected"
        :disabled="selectedTxIds.length === 0"
        class="delete-selected-btn"
      >
        Удалить выбранные ({{ selectedTxIds.length }})
      </button>
    </div>

    <!-- ТАБЛИЦА -->
    <table class="transactions-table">
      <thead>
        <tr>
          <th>
            <input type="checkbox" v-model="allSelected" @change="toggleAll" />
          </th>
          <th>Дата</th>
          <th>Тип</th>
          <th>Актив</th>
          <th>Портфель</th>
          <th>Количество</th>
          <th>Цена</th>
          <th>Стоимость</th>
          <th>Действия</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="tx in filteredTransactions"
          :key="tx.transaction_id"
          :class="['tx-row', 'tx-type-' + normalizeType(tx.transaction_type)]"
        >
          <td>
            <input
              type="checkbox"
              :value="tx.transaction_id"
              v-model="selectedTxIds"
            />
          </td>
          <td>{{ formatDate(tx.transaction_date) }}</td>
          <td>
            <span :class="['tx-badge', 'tx-' + normalizeType(tx.transaction_type)]">
              {{ tx.transaction_type }}
            </span>
          </td>
          <td>{{ tx.asset_name }}</td>
          <td>{{ tx.portfolio_name }}</td>
          <td>{{ tx.quantity }}</td>
          <td>{{ tx.price.toLocaleString() }}</td>
          <td>{{ (tx.quantity * tx.price).toFixed(2) }}</td>

          <td class="tx-actions">
            <div class="actions-dropdown" @click.stop="tx.showMenu = !tx.showMenu">
              ⋮
            </div>

            <div v-if="tx.showMenu" class="dropdown-menu" @click.stop>
              <button @click="openEditModal(tx)">✏️ Редактировать</button>
              <button @click="deleteOne(tx.transaction_id)">🗑 Удалить</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>

    <p v-if="filteredTransactions.length === 0" class="empty-state">
      Нет транзакций по заданным фильтрам.
    </p>

    <!-- SUMMARY -->
    <div v-else class="summary-card">
      <div class="summary-total">
        Итого за период: <span>{{ summary.total.toLocaleString() }}</span>
      </div>
      <div class="summary-types">
        <div
          v-for="(item, key) in summary.byType"
          :key="key"
          class="summary-type-item"
        >
          <span class="label">{{ item.label }}</span>
          <span class="value">{{ item.value.toLocaleString() }}</span>
        </div>
      </div>
    </div>

    <EditTransactionModal
      :visible="showEditModal"
      :transaction="currentTransaction"
      @close="showEditModal = false"
      @save="handleSaveEdit"
    />
  </div>
</template>

<style scoped>
.transactions-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 20px;
}

.page-title {
  font-size: 1.8rem;
  font-weight: 600;
  margin-bottom: 16px;
}

/* Фильтры */
.filters {
  position: sticky;
  top: 0;
  z-index: 10;
  background: #fff;
  padding: 10px 0 12px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid #eee;
  margin-bottom: 16px;
}

.filters-left {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

select,
input[type="date"] {
  padding: 6px 10px;
  border: 1px solid #ccc;
  border-radius: 6px;
  background: #fff;
}

.asset-search-wrapper {
  position: relative;
}

/* поле + кнопка очистки */
.search-input-group {
  display: flex;
  align-items: center;
  position: relative;
}

.asset-search-input {
  padding: 6px 30px 6px 10px;
  border: 1px solid #ccc;
  border-radius: 6px;
  width: 180px;
}

.clear-search-btn {
  position: absolute;
  right: 1px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 18px;
  padding: 0 8px;
  line-height: 1;
  height: 100%;
  border-radius: 0 6px 6px 0;
  transition: color 0.2s;
}

.clear-search-btn:hover {
  color: #333;
}

/* дроп с активами */
.asset-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  width: 260px;
  background: white;
  border: 1px solid #ccc;
  border-top: none;
  border-radius: 0 0 6px 6px;
  max-height: 260px;
  overflow-y: auto;
  z-index: 20;
  list-style: none;
  padding: 0;
  margin-top: 0;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.08);
}

.asset-option {
  padding: 6px 10px;
  cursor: pointer;
}

.asset-option:hover {
  background: #f4f4f4;
}

.asset-option-main mark {
  background: #ffeb3b;
  padding: 0 1px;
}

.asset-option-meta {
  font-size: 12px;
  color: #777;
}

.asset-option-meta .ticker {
  font-weight: 500;
}

.asset-option-meta .price {
  margin-left: 4px;
}

.asset-empty {
  padding: 8px 10px;
  color: #999;
}

.recent-label {
  padding: 6px 10px 4px;
  font-size: 11px;
  text-transform: uppercase;
  color: #999;
}

.asset-recent-chip {
  display: inline-block;
  margin: 0 4px 6px;
  padding: 4px 8px;
  font-size: 12px;
  border-radius: 999px;
  border: 1px solid #ddd;
  cursor: pointer;
  background: #fafafa;
}

.asset-recent-chip:hover {
  background: #f0f0f0;
}

/* быстрые периоды */
.quick-periods {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.chip {
  border: 1px solid #ddd;
  border-radius: 999px;
  padding: 4px 10px;
  background: #fafafa;
  cursor: pointer;
  font-size: 12px;
}

.chip.active {
  background: #007bff;
  color: #fff;
  border-color: #007bff;
}

.custom-dates {
  display: flex;
  gap: 6px;
}

/* панель действий */
.actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.delete-selected-btn,
.export-btn {
  padding: 8px 15px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
}

.delete-selected-btn {
  background-color: #dc3545;
  color: white;
}

.delete-selected-btn:disabled {
  background-color: #e9ecef;
  color: #6c757d;
  cursor: not-allowed;
}

.export-btn {
  background-color: #17a2b8;
  color: white;
}

.export-btn:disabled {
  background-color: #e9ecef;
  color: #6c757d;
  cursor: not-allowed;
}

/* сброс фильтров */
.reset-filter-btn {
  padding: 6px 10px;
  background-color: #f0ad4e;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
}

.reset-filter-btn:hover {
  background-color: #ec971f;
}

/* таблица */
.transactions-table {
  width: 100%;
  border-collapse: collapse;
}

.transactions-table th,
.transactions-table td {
  border-bottom: 1px solid #eee;
  padding: 8px 10px;
  text-align: left;
  font-size: 14px;
}

.transactions-table th {
  background-color: #f5f7fa;
  font-weight: 600;
}

/* строки по типу */
.tx-row.tx-type-buy {
  background: #e8f5e9;
}

.tx-row.tx-type-sell {
  background: #ffebee;
}

.tx-row.tx-type-dividend,
.tx-row.tx-type-coupon {
  background: #e3f2fd;
}

.tx-row.tx-type-commission,
.tx-row.tx-type-tax {
  background: #f9f9f9;
}

/* действия в строке */
.row-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.15s;
}

.tx-row:hover .row-actions {
  opacity: 1;
}

.row-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
}

.row-btn.edit:hover {
  background: #e3f2fd;
}

.row-btn.delete:hover {
  background: #ffebee;
}

/* пустое состояние */
.empty-state {
  text-align: center;
  margin-top: 20px;
  color: #888;
}

/* summary */
.summary-card {
  margin-top: 16px;
  padding: 12px 14px;
  border-radius: 8px;
  background: #f8f9fa;
  border: 1px solid #e2e3e5;
}

.summary-total {
  font-weight: 600;
  margin-bottom: 8px;
}

.summary-total span {
  font-weight: 700;
}

.summary-types {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.summary-type-item {
  background: #fff;
  border-radius: 999px;
  padding: 4px 10px;
  border: 1px solid #ddd;
  font-size: 12px;
}

.summary-type-item .label {
  margin-right: 6px;
  color: #555;
}

.summary-type-item .value {
  font-weight: 600;
}

.tx-badge {
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
}

.tx-buy       { background: #2ecc71; } /* зеленый */
.tx-sell      { background: #e74c3c; } /* красный */
.tx-dividend  { background: #3498db; }
.tx-coupon    { background: #9b59b6; }
.tx-commission{ background: #7f8c8d; }
.tx-tax       { background: #95a5a6; }
.tx-deposit   { background: #1abc9c; }
.tx-withdraw  { background: #e67e22; }
.tx-other     { background: #bdc3c7; }

</style>
