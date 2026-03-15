<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../stores/auth.store'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import { usePortfoliosStore } from '../stores/portfolios.store'
import { usePortfolioAnalytics } from '../composables/usePortfolioAnalytics'

// Компоненты
import LoadingState from '../components/base/LoadingState.vue'
import PageLayout from '../layouts/PageLayout.vue'
import PageHeader from '../layouts/PageHeader.vue'

// Виджеты
import { 
  TotalCapitalWidget, 
  PortfolioProfitWidget, 
  DividendsWidget, 
  ReturnWidget,
  ConsolidatedStatsWidget
} from '../components/widgets/stats'
import { GoalProgressWidget } from '../components/widgets/composite'
import { 
  PortfolioChartWidget, 
  AssetAllocationWidget, 
  PayoutsChartWidget 
} from '../components/widgets/charts'
import { 
  TopMoversWidget, 
  RecentTransactionsWidget 
} from '../components/widgets/lists'
import { WidgetContainer } from '../components/widgets/base'
import PortfolioSelector from '../components/PortfolioSelector.vue'

const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const uiStore = useUIStore()
const portfoliosStore = usePortfoliosStore()

// Используем composable для аналитики портфеля
const {
  portfolios,
  selectedPortfolio,
  selectedPortfolioAnalytics,
  isLoadingAnalytics,
  totalCapitalWidgetData,
  profitWidgetData,
  calculatedAnnualDividends,
  returnData,
  portfolioChartData,
  collectPortfolioIds
} = usePortfolioAnalytics()

// Функция для сбора всех активов выбранного портфеля и его дочерних
function collectAssets(portfolio, allPortfolios) {
  let assets = [...(portfolio.assets || [])]
  const children = allPortfolios.filter(p => p.parent_portfolio_id === portfolio.id)

  for (const child of children) {
    assets = assets.concat(collectAssets(child, allPortfolios))
  }

  return assets
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
    totalAmount: totalCapitalWidgetData.value.totalAmount,
    investedAmount: totalCapitalWidgetData.value.investedAmount,
    monthlyChange: selectedPortfolio.value.monthly_change || 0,
    assetAllocation: selectedPortfolio.value.asset_allocation ?? { labels: [], datasets: [{ backgroundColor: [], data: [] }] },
    portfolioChart: portfolioChartData.value,
    assets,
    transactions
  }
})

const goalData = computed(() => {
  if (!selectedPortfolio.value) return null

    const desc = selectedPortfolio.value.description || {} // если пустой, используем пустой объект
    
    const result = {
      portfolioId: selectedPortfolio.value.id,
      title: desc.capital_target_name || desc.text || 'Цель не задана',
      targetAmount: desc.capital_target_value || 0,
      currentAmount: selectedPortfolio.value.total_value || 0, // total_value уже включает баланс на бэкенде
      deadline: desc.capital_target_deadline || null,
      currency: desc.capital_target_currency || 'RUB',
      monthlyContribution: desc.monthly_contribution || 0,
      annualReturn: desc.annual_return || 0,
      useInflation: desc.use_inflation || false,
      inflationRate: desc.inflation_rate || 7.5
    }
  
  return result
})

// Данные для AssetAllocationWidget
const assetAllocationData = computed(() => {
  if (!selectedPortfolio.value) {
    return { labels: [], datasets: [{ backgroundColor: [], data: [] }] }
  }
  return selectedPortfolio.value.asset_allocation ?? { labels: [], datasets: [{ backgroundColor: [], data: [] }] }
})

// Данные для MonthlyPayoutsChartWidget
const monthlyPayouts = computed(() => {
  return selectedPortfolioAnalytics.value?.monthly_payouts || []
})

// Данные для RecentTransactionsWidget - последние транзакции, отсортированные по дате
const recentTransactions = computed(() => {
  const transactions = parsedDashboard.value?.transactions || []
  // Сортируем по дате (новые первыми) и берем последние
  return [...transactions]
    .sort((a, b) => {
      const dateA = new Date(a.transaction_date || 0)
      const dateB = new Date(b.transaction_date || 0)
      return dateB - dateA
    })
    .slice(0, 10)
})

</script>

<template>
  <PageLayout v-if="!uiStore.loading && parsedDashboard">
    <PageHeader 
      :title="`С возвращением, ${authStore.user?.name}`"
      subtitle="Главная"
    >
      <template #actions>
        <PortfolioSelector 
          :portfolios="portfolios"
          :modelValue="uiStore.selectedPortfolioId"
          @update:modelValue="uiStore.setSelectedPortfolioId"
        />
      </template>
    </PageHeader>

    <div class="widgets-grid">
      <!-- Статы: на десктопе — 4 виджета, на мобильном — один сводный -->
      <div class="stats-desktop">
        <WidgetContainer :gridColumn="3" minHeight="var(--widget-height-small)">
          <TotalCapitalWidget 
            :total-amount="totalCapitalWidgetData.totalAmount"
            :invested-amount="totalCapitalWidgetData.investedAmount"
          />
        </WidgetContainer>
        <WidgetContainer :gridColumn="3" minHeight="var(--widget-height-small)">
          <PortfolioProfitWidget 
            :total-amount="profitWidgetData.totalAmount"
            :total-profit="profitWidgetData.totalProfit"
            :monthly-change="profitWidgetData.monthlyChange"
            :invested-amount="profitWidgetData.investedAmount"
            :analytics="profitWidgetData.analytics"
          />
        </WidgetContainer>
        <WidgetContainer :gridColumn="3" minHeight="var(--widget-height-small)">
          <DividendsWidget 
            :annual-dividends="calculatedAnnualDividends"
          />
        </WidgetContainer>
        <WidgetContainer :gridColumn="3" minHeight="var(--widget-height-small)">
          <ReturnWidget 
            :return-percent="returnData.returnPercent"
            :return-percent-on-invested="returnData.returnPercentOnInvested"
            :total-value="returnData.totalValue"
            :total-invested="returnData.totalInvested"
          />
        </WidgetContainer>
      </div>
      <div class="stats-mobile">
        <WidgetContainer gridColumn="1" minHeight="var(--widget-height-small)">
          <ConsolidatedStatsWidget
            :total-amount="totalCapitalWidgetData.totalAmount"
            :invested-amount="totalCapitalWidgetData.investedAmount"
            :total-profit="profitWidgetData.totalProfit"
            :monthly-change="profitWidgetData.monthlyChange"
            :analytics="profitWidgetData.analytics"
            :annual-dividends="calculatedAnnualDividends"
            :return-percent="returnData.returnPercent"
            :return-percent-on-invested="returnData.returnPercentOnInvested"
          />
        </WidgetContainer>
      </div>

      <!-- 1. Динамика капитала — на планшете на всю ширину -->
      <WidgetContainer class="chart-dynamics-widget" :gridColumn="8" minHeight="var(--widget-height-xlarge)">
        <PortfolioChartWidget 
          :chartData="portfolioChartData"
        />
      </WidgetContainer>

      <!-- 2. Рост и падение за день (на планшете в одну строку) -->
      <WidgetContainer class="top-up-widget" :gridColumn="4" minHeight="var(--widget-height-medium)">
        <TopMoversWidget
          title="Топ роста за день"
          :assets="selectedPortfolio.combined_assets || []"
          direction="up"
        />
      </WidgetContainer>
      <WidgetContainer class="top-down-widget" :gridColumn="4" minHeight="var(--widget-height-medium)">
        <TopMoversWidget
          title="Топ падений за день"
          :assets="selectedPortfolio.combined_assets || []"
          direction="down"
        />
      </WidgetContainer>

      <!-- 3. Распределение активов и последние операции (на планшете в одну строку) -->
      <WidgetContainer class="allocation-widget" :gridColumn="4" minHeight="var(--widget-height-medium)">
        <AssetAllocationWidget
          :assetAllocation="assetAllocationData"
        />
      </WidgetContainer>
      <WidgetContainer class="recent-tx-widget" :gridColumn="4" minHeight="var(--widget-height-medium)">
        <RecentTransactionsWidget
          :transactions="recentTransactions"
        />
      </WidgetContainer>

      <!-- 4. Выплаты по месяцам — на планшете на всю ширину -->
      <WidgetContainer class="payouts-chart-widget" :gridColumn="6" minHeight="var(--widget-height-medium)">
        <PayoutsChartWidget 
          title="Полученные выплаты по месяцам"
          :payouts="monthlyPayouts"
          mode="past"
        />
      </WidgetContainer>

      <!-- 5. Достижение цели — на планшете на всю ширину -->
      <WidgetContainer class="goal-progress-widget" :gridColumn="6" minHeight="var(--widget-height-medium)">
        <GoalProgressWidget 
          :goal-data="goalData"
          :onSaveGoal="portfoliosStore.updatePortfolioGoal"
          :default-return-percent="returnData.returnPercent"
        />
      </WidgetContainer>
    </div>
  </PageLayout>

  <LoadingState v-else />
</template>

<style scoped>
.widgets-grid {
  display: grid;
  gap: var(--spacing);
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: min-content;
  width: 100%;
  min-width: 0;
}

/* Блок из 4 стат-виджетов (десктоп) */
.stats-desktop {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: var(--spacing);
  order: 1;
}
/* Сводный стат-виджет (мобильный) */
.stats-mobile {
  display: none;
  grid-column: 1 / -1;
  order: 1;
}

/* ПК и мобильная: распределение активов сразу после графика капитала */
.widgets-grid :deep(.chart-dynamics-widget) { order: 2; }
.widgets-grid :deep(.allocation-widget) { order: 3; }
.widgets-grid :deep(.top-up-widget) { order: 4; }
.widgets-grid :deep(.top-down-widget) { order: 5; }
.widgets-grid :deep(.recent-tx-widget) { order: 6; }
.widgets-grid :deep(.payouts-chart-widget) { order: 7; }
.widgets-grid :deep(.goal-progress-widget) { order: 8; }

/* Планшет: порядок по DOM — динамика (вся ширина), рост/падение (2), распределение и операции (2), выплаты (вся ширина), цель (вся ширина). Распределение активов «переезжает» сюда только на планшете */
@media (max-width: 1200px) {
  .widgets-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  .stats-desktop {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  .stats-desktop :deep(.widget-container) {
    grid-column: span 1 !important;
  }
  .widgets-grid :deep(.widget-container) {
    grid-column: span 1 !important;
  }
  .widgets-grid :deep(.chart-dynamics-widget),
  .widgets-grid :deep(.payouts-chart-widget),
  .widgets-grid :deep(.goal-progress-widget) {
    grid-column: 1 / -1 !important;
  }
  /* Статы остаются сверху (order: 0), остальные по разметке: график, топы, распределение, операции, выплаты, цель */
  .stats-desktop {
    order: 0;
  }
  .widgets-grid :deep(.chart-dynamics-widget) { order: 1; }
  .widgets-grid :deep(.top-up-widget) { order: 2; }
  .widgets-grid :deep(.top-down-widget) { order: 3; }
  .widgets-grid :deep(.allocation-widget) { order: 4; }
  .widgets-grid :deep(.recent-tx-widget) { order: 5; }
  .widgets-grid :deep(.payouts-chart-widget) { order: 6; }
  .widgets-grid :deep(.goal-progress-widget) { order: 7; }
}

/* Мобильный: одна колонка, порядок как на ПК (распределение после графика) */
@media (max-width: 768px) {
  .widgets-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }
  .stats-desktop {
    display: none;
  }
  .stats-mobile {
    display: block;
  }
  .widgets-grid :deep(.widget-container) {
    grid-column: 1 / -1 !important;
  }
  /* Восстанавливаем порядок ПК: график, затем распределение активов */
  .widgets-grid :deep(.chart-dynamics-widget) { order: 2; }
  .widgets-grid :deep(.allocation-widget) { order: 3; }
  .widgets-grid :deep(.top-up-widget) { order: 4; }
  .widgets-grid :deep(.top-down-widget) { order: 5; }
  .widgets-grid :deep(.recent-tx-widget) { order: 6; }
  .widgets-grid :deep(.payouts-chart-widget) { order: 7; }
  .widgets-grid :deep(.goal-progress-widget) { order: 8; }
}
</style>