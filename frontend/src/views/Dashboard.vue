<script setup>
import { mockData } from '../data/mockData.js'
import generatePortfolioData from '../data/generatePortfolioData.js'

// Виджеты
import TotalCapitalWidget from '../components/widgets/TotalCapitalWidget.vue'
import AssetAllocationWidget from '../components/widgets/AssetAllocationWidget.vue'
import GoalProgressWidget from '../components/widgets/GoalProgressWidget.vue'
import PortfolioChartWidget from '../components/widgets/PortfolioChartWidget.vue'
import RecentTransactionsWidget from '../components/widgets/RecentTransactionsWidget.vue'
import TopAssetsWidget from '../components/widgets/TopAssetsWidget.vue'
</script>

<template>
  <div class="title-text">
    <h1>С возвращением, {{ mockData.user.firstName }}</h1>
    <h2>Главная</h2>
  </div>

  <div class="widgets-grid">
    <TotalCapitalWidget 
      :total-amount="mockData.totalCapital.totalAmount" 
      :monthly-change="mockData.totalCapital.monthlyChange" 
    />
    <TopAssetsWidget :assets="mockData.topAssets" />
    <RecentTransactionsWidget :transactions="mockData.recentTransactions" />
    <AssetAllocationWidget :assetAllocation="mockData.assetAllocation" />
    <GoalProgressWidget :goal-data="mockData.investmentGoal" />
    <PortfolioChartWidget :chartData="generatePortfolioData.data().portfolioChart" />
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
