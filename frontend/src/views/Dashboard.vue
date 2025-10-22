<script setup>
import { inject, computed, ref, watch } from 'vue'
import { mockData } from '../data/mockData.js'

// Виджеты
import TotalCapitalWidget from '../components/widgets/TotalCapitalWidget.vue'
import AssetAllocationWidget from '../components/widgets/AssetAllocationWidget.vue'
import GoalProgressWidget from '../components/widgets/GoalProgressWidget.vue'
import PortfolioChartWidget from '../components/widgets/PortfolioChartWidget.vue'
import RecentTransactionsWidget from '../components/widgets/RecentTransactionsWidget.vue'
import TopAssetsWidget from '../components/widgets/TopAssetsWidget.vue'

const user = inject('user')
const dashboardData = inject('dashboardData')
const updatePortfolioGoal = inject('updatePortfolioGoal')
const loading = inject('loading')

// Состояние выбранного портфеля
const selectedPortfolioId = ref(null)

// Автоматически выбираем первый портфель при загрузке
watch(dashboardData, () => {
  if (dashboardData.value?.data?.portfolios?.length) {
    selectedPortfolioId.value = dashboardData.value.data.portfolios[0].id
  }
}, { immediate: true })

const portfolios = computed(() => dashboardData.value?.data?.portfolios ?? [])

const selectedPortfolio = computed(() => {
  return portfolios.value.find(p => p.id === selectedPortfolioId.value) || null
})

// Функция для сбора всех id выбранного портфеля и его дочерних
function collectPortfolioIds(portfolio, allPortfolios) {
  let ids = [portfolio.id];
  const children = allPortfolios.filter(p => p.parent_portfolio_id === portfolio.id);
  console.log('children', children)

  for (const child of children) {
    ids = ids.concat(collectPortfolioIds(child, allPortfolios));
  }

  return ids;
}

// Функция для сбора всех активов выбранного портфеля и его дочерних
function collectAssets(portfolio, allPortfolios) {
  let assets = [...(portfolio.assets || [])];
  const children = allPortfolios.filter(p => p.parent_portfolio_id === portfolio.id);

  for (const child of children) {
    assets = assets.concat(collectAssets(child, allPortfolios));
  }

  return assets;
}

const parsedDashboard = computed(() => {
  const data = dashboardData.value?.data;
  if (!data || !selectedPortfolio.value) return null;

  const allPortfolios = portfolios.value;

  const portfolioIds = collectPortfolioIds(selectedPortfolio.value, allPortfolios);
  const assets = collectAssets(selectedPortfolio.value, allPortfolios);

  // Фильтруем транзакции по всем id портфелей
  const transactions = (data.transactions ?? []).filter(t => portfolioIds.includes(t.portfolio_id));

  return {
    totalAmount: Number(selectedPortfolio.value.total_value || 0),
    investedAmount: Number(selectedPortfolio.value.invested_amount || 0),
    monthlyChange: {
      absolute: selectedPortfolio.value.total_profit || 0,
      percentage: selectedPortfolio.value.profit_percent || 0
    },
    assetAllocation: selectedPortfolio.value.asset_allocation ?? { labels: [], datasets: [{ backgroundColor: [], data: [] }] },
    portfolioChart: selectedPortfolio.value.history ?? { labels: [], data: [] },
    assets,
    transactions
  };
});

const goalData = computed(() => {
  const data = dashboardData.value?.data
  if (!data || !selectedPortfolio.value) return null

  const desc = selectedPortfolio.value.description || {} // если пустой, используем пустой объект
  return {
    portfolioId: selectedPortfolio.value.id,
    title: desc.capital_target_name || desc.text || 'Цель не задана',
    targetAmount: desc.capital_target_value || 0,
    currentAmount: selectedPortfolio.value.total_value || 0,
    deadline: desc.capital_target_deadline || null,
    currency: desc.capital_target_currency || 'RUB'
  }
})
</script>

<template>
  <div v-if="!loading">
    <div class="title-text" style="display: flex; align-items: center; justify-content: space-between;">
      <h1>С возвращением, {{ user?.name }}</h1>

      <!-- Селектор портфеля -->
      <select v-model="selectedPortfolioId">
        <option v-for="p in portfolios" :key="p.id" :value="p.id">
          {{ p.name }}
        </option>
      </select>
    </div>

    <h2>Главная</h2>

    <div class="widgets-grid">
      <TotalCapitalWidget 
        :total-amount="parsedDashboard.totalAmount" 
        :monthly-change="parsedDashboard.monthlyChange" 
        :invested-amount="parsedDashboard.investedAmount" 
      />
      <TopAssetsWidget :assets="parsedDashboard.assets" />
      <RecentTransactionsWidget :transactions="parsedDashboard.transactions" />
      <AssetAllocationWidget :assetAllocation="parsedDashboard.assetAllocation" />
      <GoalProgressWidget 
        :goal-data="goalData"
        :onSaveGoal="updatePortfolioGoal"
      />
      <PortfolioChartWidget :chartData="parsedDashboard.portfolioChart" />
    </div>
  </div>

  <div v-else class="loading-screen">
    <p>Загрузка данных...</p>
  </div>
</template>

<style scoped>
.title-text {
  margin-bottom: var(--spacing);
}

.widgets-grid {
  display: grid;
  gap: var(--spacing);
  grid-template-columns: repeat(auto-fit, minmax(clamp(350px, 20%, 400px), 1fr));
  grid-auto-rows: 150px;
}

.loading-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  font-size: 1.5rem;
}
</style>