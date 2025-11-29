<script setup>
import { inject, computed, ref, watch } from 'vue'

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

const user = inject('user')
const dashboardData = inject('dashboardData')
const updatePortfolioGoal = inject('updatePortfolioGoal')
const loading = inject('loading')

const selectedPortfolioId = inject('globalSelectedPortfolioId')
const setPortfolioId = inject('setPortfolioId')

const portfolios = computed(() => dashboardData.value?.data?.portfolios ?? [])

const selectedPortfolio = computed(() => {
  return portfolios.value.find(p => p.id === selectedPortfolioId.value) || null
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
  const data = dashboardData.value?.data;
  if (!data || !selectedPortfolio.value) return null;

  const allPortfolios = portfolios.value;

  const portfolioIds = collectPortfolioIds(selectedPortfolio.value, allPortfolios);
  const assets = collectAssets(selectedPortfolio.value, allPortfolios);

  // Фильтруем транзакции по всем id портфелей
  const transactions = (data.transactions ?? []).filter(t => portfolioIds.includes(t.portfolio_id));

  return {
    totalAmount: Number(selectedPortfolio.value.total_value || 0),
    investedAmount: Number(selectedPortfolio.value.total_invested || 0),
    monthlyChange: selectedPortfolio.value.monthly_change || 0,
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
  <div v-if="!loading && parsedDashboard">
    <div class="title" style="display: flex; align-items: center; justify-content: space-between;">
      <div>
        <h1>С возвращением, {{ user?.name }}</h1>
        <h2>Главная</h2>
      </div>
      
      <PortfolioSelector 
        :portfolios="portfolios"
        :modelValue="selectedPortfolioId"
        @update:modelValue="setPortfolioId"
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
        :onSaveGoal="updatePortfolioGoal"
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

  <div v-else class="loading-screen">
    <p>Загрузка данных...</p>
  </div>
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

.loading-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  font-size: 1.5rem;
}


.portfolio-selector {
  position: relative;
  display: inline-block;
  min-width: 200px;
}

.portfolio-select {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  width: 100%;
  padding: 10px 16px;
  padding-right: 40px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #1a1a1a);
  background: var(--bg-secondary, #f8f9fa);
  border: 2px solid var(--border-color, #e1e5e9);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  outline: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.portfolio-select:hover {
  border-color: var(--primary-color, #007bff);
  background: var(--bg-primary, #ffffff);
  box-shadow: 0 4px 8px rgba(0, 123, 255, 0.15);
}

.portfolio-select:focus {
  border-color: var(--primary-color, #007bff);
  background: var(--bg-primary, #ffffff);
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.select-arrow {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: var(--text-secondary, #6c757d);
  font-size: 12px;
  transition: transform 0.2s ease;
}

.portfolio-select:focus + .select-arrow {
  transform: translateY(-50%) rotate(180deg);
  color: var(--primary-color, #007bff);
}

/* Стили для опций */
.portfolio-select option {
  padding: 12px;
  background: var(--bg-primary, #ffffff);
  color: var(--text-primary, #1a1a1a);
  font-size: 14px;
}

.portfolio-select option:hover {
  background: var(--primary-color, #007bff);
  color: white;
}
</style>