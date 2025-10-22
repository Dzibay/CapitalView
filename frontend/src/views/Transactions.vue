<script setup>
import { inject, ref, computed, watch } from 'vue'

// получаем данные от родителя
const dashboardData = inject('dashboardData')
// const preloadTransactions = inject('preloadTransactions')

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

// функция фильтрации
const applyFilter = () => {
  filteredTransactions.value = transactions.value.filter(tx => {
    const matchAsset = selectedAsset.value ? tx.asset_name === selectedAsset.value : true
    const matchPortfolio = selectedPortfolio.value ? tx.portfolio_name === selectedPortfolio.value : true
    const txDate = new Date(tx.transaction_date)
    const matchStart = startDate.value ? txDate >= new Date(startDate.value) : true
    const matchEnd = endDate.value ? txDate <= new Date(endDate.value) : true
    return matchAsset && matchPortfolio && matchStart && matchEnd
  })
}

// формат даты
const formatDate = date => new Date(date).toLocaleDateString()

// применяем фильтр при изменении dashboardData
watch(
  transactions,
  () => applyFilter(),
  { immediate: true }
)

// watch(
//   () => dashboardData.value,
//   async (newVal) => {
//     if (newVal) {
//       await preloadTransactions() // вызываем функцию родителя
//     }
//   },
//   { immediate: true }
// )

</script>

<template>
  <div class="transactions-page">
    <h1 class="page-title">История транзакций</h1>

    <!-- Фильтры -->
    <div class="filters">
      <select v-model="selectedPortfolio" @change="applyFilter">
        <option value="">Все портфели</option>
        <option v-for="p in portfolios" :key="p.id" :value="p.name">
          {{ p.name }}
        </option>
      </select>

      <select v-model="selectedAsset" @change="applyFilter">
        <option value="">Все активы</option>
        <option v-for="a in assets" :key="a" :value="a">{{ a }}</option>
      </select>

      <input type="date" v-model="startDate" @change="applyFilter" />
      <input type="date" v-model="endDate" @change="applyFilter" />
    </div>

    <!-- Таблица транзакций -->
    <table class="transactions-table">
      <thead>
        <tr>
          <th>Дата</th>
          <th>Тип</th>
          <th>Актив</th>
          <th>Портфель</th>
          <th>Количество</th>
          <th>Цена</th>
          <th>Стоимость</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="tx in filteredTransactions" :key="tx.id">
          <td>{{ formatDate(tx.transaction_date) }}</td>
          <td>{{ tx.transaction_type }}</td>
          <td>{{ tx.asset_name }}</td>
          <td>{{ tx.portfolio_name }}</td>
          <td>{{ tx.quantity }}</td>
          <td>{{ tx.price.toLocaleString() }}</td>
          <td>{{ (tx.quantity * tx.price).toFixed(2) }}</td>
        </tr>
      </tbody>
    </table>

    <p v-if="filteredTransactions.length === 0" class="empty-state">
      Нет транзакций за выбранный период.
    </p>
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
