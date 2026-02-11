<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { useAuthStore } from '../stores/auth.store'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import { usePortfoliosStore } from '../stores/portfolios.store'
import { useTransactionsStore } from '../stores/transactions.store'

// Компоненты
import LoadingState from '../components/LoadingState.vue'
import PageLayout from '../components/PageLayout.vue'
import PageHeader from '../components/PageHeader.vue'

// Виджеты
import TotalCapitalWidget from '../components/widgets/TotalCapitalWidget.vue'
import GoalProgressWidget from '../components/widgets/GoalProgressWidget.vue'
import PortfolioChartWidget from '../components/widgets/PortfolioChartWidget.vue'
import TopAssetsWidget from '../components/widgets/TopAssetsWidget.vue'
import TopMoversWidget from '../components/widgets/TopMoversWidget.vue'
import PortfolioProfitWidget from '../components/widgets/PortfolioProfitWidget.vue'
import PortfolioSelector from '../components/PortfolioSelector.vue'
import DividendsWidget from '../components/widgets/DividendsWidget.vue'
import ReturnWidget from '../components/widgets/ReturnWidget.vue'

const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const uiStore = useUIStore()
const portfoliosStore = usePortfoliosStore()
const transactionsStore = useTransactionsStore()

const portfolios = computed(() => dashboardStore.portfolios)

// Локальное состояние для аналитики
const selectedPortfolioAnalytics = ref(null)
const isLoadingAnalytics = ref(false)

// Автозагрузка аналитики
watch(
  () => dashboardStore.portfolios,
  async (portfolios) => {
    if (portfolios?.length) {
      await safeLoadAnalytics()
    }
  },
  { immediate: true }
)

// Безопасная загрузка аналитики
async function safeLoadAnalytics() {
  if (isLoadingAnalytics.value) return
  try {
    isLoadingAnalytics.value = true
    await transactionsStore.loadAnalytics()

    await nextTick()
    watch(
      () => dashboardStore.analytics,
      async (newAnalytics) => {
        if (Array.isArray(newAnalytics) && newAnalytics.length > 0) {
          await updateSelectedAnalytics()
        }
      },
      { immediate: true, once: true, deep: true }
    )
  } catch (err) {
    console.error('❌ Ошибка при загрузке аналитики:', err)
  } finally {
    isLoadingAnalytics.value = false
  }
}

// Перерисовка при смене портфеля
watch(
  () => uiStore.selectedPortfolioId,
  async () => {
    await updateSelectedAnalytics()
  }
)

// Обновление выбранной аналитики
async function updateSelectedAnalytics() {
  const allAnalytics = dashboardStore.analytics ?? []
  selectedPortfolioAnalytics.value =
    allAnalytics.find(a => a.portfolio_id === uiStore.selectedPortfolioId) || null
}

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
  
  const result = {
    portfolioId: selectedPortfolio.value.id,
    title: desc.capital_target_name || desc.text || 'Цель не задана',
    targetAmount: desc.capital_target_value || 0,
    currentAmount: selectedPortfolio.value.total_value || 0,
    deadline: desc.capital_target_deadline || null,
    currency: desc.capital_target_currency || 'RUB',
    monthlyContribution: desc.monthly_contribution || 0,
    annualReturn: desc.annual_return || 0,
    useInflation: desc.use_inflation || desc.useInflation || false,
    use_inflation: desc.use_inflation || desc.useInflation || false,
    inflationRate: desc.inflation_rate || desc.inflationRate || 7.5,
    inflation_rate: desc.inflation_rate || desc.inflationRate || 7.5
  }
  
  // Отладочная информация
  if (import.meta.env.DEV) {
    console.log('[GoalProgressWidget] goalData computed:', {
      description: desc,
      result: result,
      useInflation: result.useInflation,
      inflationRate: result.inflationRate
    })
  }
  
  return result
})

// Расчет годовых дивидендов: процент доходности * сумма портфеля
const calculatedAnnualDividends = computed(() => {
  // Используем данные из аналитики, если доступны
  if (selectedPortfolioAnalytics.value?.totals) {
    const returnPercent = selectedPortfolioAnalytics.value.totals.return_percent || 0
    const totalValue = selectedPortfolioAnalytics.value.totals.total_value || 0
    return (returnPercent / 100) * totalValue
  }
  // Иначе используем данные из selectedPortfolio.analytics
  if (selectedPortfolio.value?.analytics) {
    const returnPercent = selectedPortfolio.value.analytics.return_percent || 0
    const totalValue = selectedPortfolio.value.analytics.total_value || selectedPortfolio.value.total_value || 0
    return (returnPercent / 100) * totalValue
  }
  return 0
})

// Данные для ReturnWidget
const returnData = computed(() => {
  // Используем данные из аналитики, если доступны
  if (selectedPortfolioAnalytics.value?.totals) {
    return {
      returnPercent: selectedPortfolioAnalytics.value.totals.return_percent || 0,
      totalValue: selectedPortfolioAnalytics.value.totals.total_value || 0,
      totalInvested: selectedPortfolioAnalytics.value.totals.total_invested || 0
    }
  }
  // Иначе используем данные из selectedPortfolio.analytics
  if (selectedPortfolio.value?.analytics) {
    return {
      returnPercent: selectedPortfolio.value.analytics.return_percent || 0,
      totalValue: selectedPortfolio.value.analytics.total_value || selectedPortfolio.value.total_value || 0,
      totalInvested: selectedPortfolio.value.analytics.total_invested || selectedPortfolio.value.total_invested || 0
    }
  }
  return {
    returnPercent: 0,
    totalValue: parsedDashboard.value?.totalAmount || 0,
    totalInvested: parsedDashboard.value?.investedAmount || 0
  }
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
      <!-- 4 маленьких виджета вверху -->
      <TotalCapitalWidget 
        class="small-widget"
        :total-amount="parsedDashboard.totalAmount"
        :invested-amount="parsedDashboard.investedAmount" 
      />
      <PortfolioProfitWidget 
        class="small-widget"
        :total-amount="parsedDashboard.totalAmount" 
        :total-profit="selectedPortfolio.analytics?.total_profit || 0" 
        :monthly-change="parsedDashboard.monthlyChange"
        :invested-amount="parsedDashboard.investedAmount"
        :analytics="selectedPortfolio.analytics || {}"
      />
      <DividendsWidget 
        class="small-widget"
        :annual-dividends="calculatedAnnualDividends"
      />
      <ReturnWidget 
        class="small-widget"
        :return-percent="returnData.returnPercent"
        :total-value="returnData.totalValue"
        :total-invested="returnData.totalInvested"
      />
      
      <!-- Большой виджет PortfolioChartWidget -->
      <PortfolioChartWidget 
        class="large-chart"
        :chartData="parsedDashboard.portfolioChart" 
      />
      
      <!-- Два виджета в ряд: Топ роста и Топ падений -->
      <TopMoversWidget
        class="movers-widget"
        title="Топ роста за день"
        :assets="selectedPortfolio.combined_assets || []"
        direction="up"
      />
      <TopMoversWidget
        class="movers-widget"
        title="Топ падений за день"
        :assets="selectedPortfolio.combined_assets || []"
        direction="down"
      />
      
      <!-- Два виджета в ряд: TopAssetsWidget и GoalProgressWidget -->
      <TopAssetsWidget 
        class="assets-widget"
        :assets="parsedDashboard.assets" 
      />
      <GoalProgressWidget 
        class="goal-widget"
        :goal-data="goalData"
        :onSaveGoal="portfoliosStore.updatePortfolioGoal"
        :default-return-percent="returnData.returnPercent"
      />
    </div>
  </PageLayout>

  <LoadingState v-else />
</template>

<style scoped>
.widgets-grid {
  display: grid;
  gap: var(--spacing);
  grid-template-columns: repeat(4, 1fr);
  grid-auto-rows: min-content;
}

/* 4 маленьких виджета вверху */
.small-widget {
  grid-column: span 1;
  min-height: 150px;
}

/* Большой виджет PortfolioChartWidget */
.large-chart {
  grid-column: 1 / -1;
  min-height: 500px;
}

/* Два виджета в ряд: Топ роста и Топ падений */
.movers-widget {
  grid-column: span 2;
  min-height: 300px;
}

/* Два виджета в ряд: TopAssetsWidget и GoalProgressWidget */
.assets-widget,
.goal-widget {
  grid-column: span 2;
  min-height: 300px;
}

/* Адаптивность для планшетов */
@media (max-width: 1200px) {
  .widgets-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .small-widget {
    grid-column: span 1;
  }
  
  .large-chart {
    grid-column: 1 / -1;
  }
  
  .movers-widget,
  .assets-widget,
  .goal-widget {
    grid-column: span 1;
  }
}

/* Адаптивность для мобильных */
@media (max-width: 768px) {
  .widgets-grid {
    grid-template-columns: 1fr;
  }
  
  .small-widget,
  .large-chart,
  .movers-widget,
  .assets-widget,
  .goal-widget {
    grid-column: span 1;
  }
}
</style>