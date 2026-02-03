<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../stores/auth.store'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import { usePortfoliosStore } from '../stores/portfolios.store'

// Компоненты
import LoadingState from '../components/LoadingState.vue'

// Виджеты
import TotalCapitalWidget from '../components/widgets/TotalCapitalWidget.vue'
import AssetAllocationWidget from '../components/widgets/AssetAllocationWidget.vue'
import GoalProgressWidget from '../components/widgets/GoalProgressWidget.vue'
import PortfolioChartWidget from '../components/widgets/PortfolioChartWidget.vue'
import RecentTransactionsWidget from '../components/widgets/RecentTransactionsWidget.vue'
import TopAssetsWidget from '../components/widgets/TopAssetsWidget.vue'
import TopMoversWidget from '../components/widgets/TopMoversWidget.vue'
import PortfolioProfitWidget from '../components/widgets/PortfolioProfitWidget.vue'
import PortfolioSelector from '../components/PortfolioSelector.vue'
import PortfolioProfitChartWidget from '../components/widgets/PortfolioProfitChartWidget.vue'

const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const uiStore = useUIStore()
const portfoliosStore = usePortfoliosStore()

const portfolios = computed(() => dashboardStore.portfolios)

const selectedPortfolio = computed(() => {
  return portfolios.value.find(p => p.id === uiStore.selectedPortfolioId) || null
})

// Функция для сбора всех id выбранного портфеля и его дочерних
function collectPortfolioIds(portfolio, allPortfolios) {
  let ids = [portfolio.id];
  const children = allPortfolios.filter(p => p.parent_portfolio_id === portfolio.id);

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
  const data = dashboardStore.data
  if (!data || !selectedPortfolio.value) return null

  const allPortfolios = portfolios.value

  const portfolioIds = collectPortfolioIds(selectedPortfolio.value, allPortfolios)
  const assets = collectAssets(selectedPortfolio.value, allPortfolios)

  // Фильтруем транзакции по всем id портфелей
  const transactions = (dashboardStore.transactions ?? []).filter(t => portfolioIds.includes(t.portfolio_id))

  return {
    totalAmount: Number(selectedPortfolio.value.total_value || 0),
    investedAmount: Number(selectedPortfolio.value.total_invested || 0),
    monthlyChange: selectedPortfolio.value.monthly_change || 0,
    assetAllocation: selectedPortfolio.value.asset_allocation ?? { labels: [], datasets: [{ backgroundColor: [], data: [] }] },
    portfolioChart: selectedPortfolio.value.history ?? { labels: [], data: [] },
    assets,
    transactions
  }
})

const goalData = computed(() => {
  if (!selectedPortfolio.value) return null

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
  <div v-if="!uiStore.loading && parsedDashboard">
    <div class="title" style="display: flex; align-items: center; justify-content: space-between;">
      <div>
        <h1>С возвращением, {{ authStore.user?.name }}</h1>
        <h2>Главная</h2>
      </div>
      
      <PortfolioSelector 
        :portfolios="portfolios"
        :modelValue="uiStore.selectedPortfolioId"
        @update:modelValue="uiStore.setSelectedPortfolioId"
      />
    </div>

    <div class="widgets-grid">
      <TotalCapitalWidget 
        :total-amount="parsedDashboard.totalAmount"
        :invested-amount="parsedDashboard.investedAmount" 
      />
      <PortfolioProfitWidget 
        :total-amount="parsedDashboard.totalAmount" 
        :total-profit="selectedPortfolio.analytics?.total_profit || 0" 
        :monthly-change="0" 
      />
      <GoalProgressWidget 
        :goal-data="goalData"
        :onSaveGoal="portfoliosStore.updatePortfolioGoal"
      />
      <AssetAllocationWidget :assetAllocation="parsedDashboard.assetAllocation" />
      <TopMoversWidget
        title="Топ роста за день"
        :assets="selectedPortfolio.combined_assets || []"
        direction="up"
      />
      <TopMoversWidget
        title="Топ падений за день"
        :assets="selectedPortfolio.combined_assets || []"
        direction="down"
      />
      <RecentTransactionsWidget :transactions="parsedDashboard.transactions" />

      <PortfolioChartWidget :chartData="parsedDashboard.portfolioChart" />
      <TopAssetsWidget :assets="parsedDashboard.assets" />
      <PortfolioProfitChartWidget :chartData="parsedDashboard.portfolioChart" />
    </div>
  </div>

  <LoadingState v-else />
</template>

<style scoped>
.title {
  margin-bottom: var(--spacing);
}

.widgets-grid {
  display: grid;
  gap: var(--spacing);
  grid-template-columns: repeat(auto-fit, minmax(clamp(350px, 20%, 400px), 1fr));
  grid-auto-rows: 150px;
}



</style>