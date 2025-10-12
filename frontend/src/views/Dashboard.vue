<script setup>
import { inject, computed } from 'vue'
import { mockData } from '../data/mockData.js'
import generatePortfolioData from '../data/generatePortfolioData.js'

// Виджеты
import TotalCapitalWidget from '../components/widgets/TotalCapitalWidget.vue'
import AssetAllocationWidget from '../components/widgets/AssetAllocationWidget.vue'
import GoalProgressWidget from '../components/widgets/GoalProgressWidget.vue'
import PortfolioChartWidget from '../components/widgets/PortfolioChartWidget.vue'
import RecentTransactionsWidget from '../components/widgets/RecentTransactionsWidget.vue'
import TopAssetsWidget from '../components/widgets/TopAssetsWidget.vue'

const user = inject('user')
const dashboardData = inject('dashboardData')

const totalAmount = computed(() => {
  return dashboardData.value?.totalCapital
    ? Number(dashboardData.value.totalCapital.totalAmount)
    : 0
})
const investedAmount = computed(() => {
  return dashboardData.value?.totalCapital
    ? Number(dashboardData.value.totalCapital.investedAmount)
    : 0
})
const monthlyChange = computed(() => {
  return dashboardData.value?.totalCapital?.monthlyChange ?? { absolute: 0, percentage: 0 }
})
const assetAllocation = computed(() => {
  return dashboardData.value?.assetAllocation ?? { labels: [], datasets: [{ backgroundColor: [], data: [] }] }
})
const portfolioChart = computed(() => {
  return dashboardData.value?.portfolioChart ?? { labels: [], data: [] }
})
</script>

<template>
  <div class="title-text">
    <h1>С возвращением, {{ user?.name }}</h1>
    <h2>Главная</h2>
  </div>

  <div class="widgets-grid">
    <TotalCapitalWidget 
      :total-amount="totalAmount" 
      :monthly-change="monthlyChange" 
      :invested-amount="investedAmount" 
    />

    <TopAssetsWidget :assets="mockData.topAssets" />
    <RecentTransactionsWidget :transactions="mockData.recentTransactions" />
    <AssetAllocationWidget :assetAllocation="assetAllocation" />
    <GoalProgressWidget :goal-data="mockData.investmentGoal" />
    <PortfolioChartWidget :chartData="portfolioChart" />

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
</style>
