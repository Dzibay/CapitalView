<script setup>
import { inject, ref, computed, watch } from 'vue'
import EditTransactionModal from '../components/modals/EditTransactionModal.vue'

// получаем данные и функции от родителя
const dashboardData = inject('dashboardData')
const deleteTransactions = inject('deleteTransactions') // принимает массив id
const editTransaction = inject('editTransaction') // обновляет транзакцию в Supabase

// доступ к последним 20 транзакциям
const transactions = computed(() => dashboardData.value?.data?.transactions || [])

// списки для фильтров
const assets = computed(() => [...new Set(transactions.value.map(t => t.asset_name))])
const portfolios = computed(() => [
  ...new Map(transactions.value.map(t => [t.portfolio_id, { id: t.portfolio_id, name: t.portfolio_name }])).values()
])

// фильтры
const selectedAsset = ref('')
const selectedPortfolio = ref('')
const startDate = ref('')
const endDate = ref('')

// отфильтрованные транзакции
const filteredTransactions = ref([])

// выделенные транзакции
const selectedTxIds = ref([])

// главный чекбокс
const allSelected = ref(false)

// модальное окно
const showEditModal = ref(false)
const currentTransaction = ref(null)

// применяем фильтр
const applyFilter = () => {
  filteredTransactions.value = transactions.value.filter(tx => {
    const matchAsset = selectedAsset.value ? tx.asset_name === selectedAsset.value : true
    const matchPortfolio = selectedPortfolio.value ? tx.portfolio_name === selectedPortfolio.value : true
    const txDate = new Date(tx.transaction_date)
    const matchStart = startDate.value ? txDate >= new Date(startDate.value) : true
    const matchEnd = endDate.value ? txDate <= new Date(endDate.value) : true
    return matchAsset && matchPortfolio && matchStart && matchEnd
  })
  selectedTxIds.value = []
  allSelected.value = false
}

// формат даты
const formatDate = date => new Date(date).toLocaleDateString()

watch(transactions, applyFilter, { immediate: true })

// переключение всех
const toggleAll = () => {
  if (allSelected.value) {
    selectedTxIds.value = filteredTransactions.value.map(tx => tx.transaction_id)
  } else {
    selectedTxIds.value = []
  }
}

// синхронизация главного чекбокса
watch(selectedTxIds, () => {
  allSelected.value =
    selectedTxIds.value.length > 0 &&
    selectedTxIds.value.length === filteredTransactions.value.length
})

// удаление выделенных
const deleteSelected = () => {
  if (selectedTxIds.value.length) {
    deleteTransactions(selectedTxIds.value)
    selectedTxIds.value = []
    allSelected.value = false
  }
}

// открыть модалку редактирования
const openEditModal = tx => {
  currentTransaction.value = { ...tx }
  showEditModal.value = true
}

// сохранить изменения из модалки
const handleSaveEdit = async newTx => {
  await editTransaction(newTx)
  showEditModal.value = false
}
</script>

<template>
  <div class="transactions-page">
    <h1 class="page-title">История транзакций</h1>

    <div class="filters">
      <select v-model="selectedPortfolio" @change="applyFilter">
        <option value="">Все портфели</option>
        <option v-for="p in portfolios" :key="p.id" :value="p.name">{{ p.name }}</option>
      </select>

      <select v-model="selectedAsset" @change="applyFilter">
        <option value="">Все активы</option>
        <option v-for="a in assets" :key="a" :value="a">{{ a }}</option>
      </select>

      <input type="date" v-model="startDate" @change="applyFilter" />
      <input type="date" v-model="endDate" @change="applyFilter" />
    </div>

    <button @click="deleteSelected" :disabled="selectedTxIds.length === 0">
      Удалить выбранные {{ selectedTxIds.size }}
    </button>

    <table class="transactions-table">
      <thead>
        <tr>
          <th><input type="checkbox" v-model="allSelected" @change="toggleAll" /></th>
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
        <tr v-for="tx in filteredTransactions" :key="tx.transaction_id">
          <td><input type="checkbox" :value="tx.transaction_id" v-model="selectedTxIds" /></td>
          <td>{{ formatDate(tx.transaction_date) }}</td>
          <td>{{ tx.transaction_type }}</td>
          <td>{{ tx.asset_name }}</td>
          <td>{{ tx.portfolio_name }}</td>
          <td>{{ tx.quantity }}</td>
          <td>{{ tx.price.toLocaleString() }}</td>
          <td>{{ (tx.quantity * tx.price).toFixed(2) }}</td>
          <td>
            <button @click="openEditModal(tx)">Редактировать</button>
          </td>
        </tr>
      </tbody>
    </table>

    <p v-if="filteredTransactions.length === 0" class="empty-state">
      Нет транзакций за выбранный период.
    </p>

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
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}

.page-title {
  font-size: 1.8rem;
  font-weight: 600;
  margin-bottom: 20px;
}

.filters {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

select,
input[type="date"] {
  padding: 6px 10px;
  border: 1px solid #ccc;
  border-radius: 6px;
  background: #fff;
}

.transactions-table {
  width: 100%;
  border-collapse: collapse;
}

.transactions-table th,
.transactions-table td {
  border-bottom: 1px solid #eee;
  padding: 10px 12px;
  text-align: left;
}

.transactions-table th {
  background-color: #f5f7fa;
  font-weight: 600;
}

.empty-state {
  text-align: center;
  margin-top: 20px;
  color: #888;
}
</style>
