<script setup>
import { inject, computed } from 'vue'
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
const updatePortfolioGoal = inject('updatePortfolioGoal');
const loading = inject('loading')

const parsedDashboard = computed(() => {
  const data = dashboardData.value?.data
  if (!data) return null

  return {
    totalAmount: Number(data.summary?.total_value || 0),
    investedAmount: Number(dashboardData.value?.totalCapital?.investedAmount || 0),
    monthlyChange: {
      absolute: data.summary?.total_profit || 0,
      percentage: data.summary?.profit_percent || 0
    },
    assetAllocation: data.asset_allocation ?? { labels: [], datasets: [{ backgroundColor: [], data: [] }] },
    portfolioChart: data.combined_history ?? { labels: [], data: [] },
    assets: data.assets ?? [],
    transactions: data.transactions ?? []
  }
})

const goalData = computed(() => {
  const data = dashboardData.value?.data;
  if (!data) return null;

  const mainPortfolio = data.portfolios?.find(p => !p.parent_portfolio_id);
  const desc = data.main_portfolio_description || {}; // если пустой, используем пустой объект

  return {
    portfolioId: mainPortfolio?.id || null,
    title: desc.capital_target_name || desc.text || 'Цель не задана',
    targetAmount: desc.capital_target_value || 0,
    currentAmount: data.summary?.total_value || 0,
    deadline: desc.capital_target_deadline || null,
    currency: desc.capital_target_currency || 'RUB'
  };
});


</script>

<template>
  <div v-if="!loading">
    <div class="title-text">
      <h1>С возвращением, {{ user?.name }}</h1>
      <h2>Главная</h2>
    </div>

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
