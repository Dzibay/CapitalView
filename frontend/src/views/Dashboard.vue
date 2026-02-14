<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { useAuthStore } from '../stores/auth.store'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import { usePortfoliosStore } from '../stores/portfolios.store'
import { useTransactionsStore } from '../stores/transactions.store'

// Компоненты
import LoadingState from '../components/base/LoadingState.vue'
import PageLayout from '../components/PageLayout.vue'
import PageHeader from '../components/PageHeader.vue'

// Виджеты
import { 
  TotalCapitalWidget, 
  PortfolioProfitWidget, 
  DividendsWidget, 
  ReturnWidget 
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

// Безопасная загрузка аналитики (теперь аналитика приходит вместе с dashboard)
async function safeLoadAnalytics() {
  if (isLoadingAnalytics.value) return
  try {
    isLoadingAnalytics.value = true
    // Аналитика уже загружена вместе с dashboard, просто обновляем выбранную
    await updateSelectedAnalytics()
  } catch (err) {
    console.error('❌ Ошибка при обработке аналитики:', err)
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

// Данные для AssetAllocationWidget
const assetAllocationData = computed(() => {
  if (!selectedPortfolio.value) {
    return { labels: [], datasets: [{ backgroundColor: [], data: [] }] }
  }
  return selectedPortfolio.value.asset_allocation ?? { labels: [], datasets: [{ backgroundColor: [], data: [] }] }
})

// Данные для ReturnWidget
const returnData = computed(() => {
  // Используем данные из аналитики, если доступны
  if (selectedPortfolioAnalytics.value?.totals) {
    return {
      returnPercent: selectedPortfolioAnalytics.value.totals.return_percent || 0,
      returnPercentOnInvested: selectedPortfolioAnalytics.value.totals.return_percent_on_invested || 0,
      totalValue: selectedPortfolioAnalytics.value.totals.total_value || 0,
      totalInvested: selectedPortfolioAnalytics.value.totals.total_invested || 0
    }
  }
  // Иначе используем данные из selectedPortfolio.analytics
  if (selectedPortfolio.value?.analytics) {
    return {
      returnPercent: selectedPortfolio.value.analytics.return_percent || 0,
      returnPercentOnInvested: selectedPortfolio.value.analytics.return_percent_on_invested || 0,
      totalValue: selectedPortfolio.value.analytics.total_value || selectedPortfolio.value.total_value || 0,
      totalInvested: selectedPortfolio.value.analytics.total_invested || selectedPortfolio.value.total_invested || 0
    }
  }
  return {
    returnPercent: 0,
    returnPercentOnInvested: 0,
    totalValue: parsedDashboard.value?.totalAmount || 0,
    totalInvested: parsedDashboard.value?.investedAmount || 0
  }
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
      <!-- 4 маленьких виджета вверху -->
      <WidgetContainer :gridColumn="3" minHeight="var(--widget-height-small)">
        <TotalCapitalWidget 
          :total-amount="parsedDashboard.totalAmount"
          :invested-amount="parsedDashboard.investedAmount"
        />
      </WidgetContainer>
      <WidgetContainer :gridColumn="3" minHeight="var(--widget-height-small)">
        <PortfolioProfitWidget 
          :total-amount="parsedDashboard.totalAmount" 
          :total-profit="selectedPortfolio.analytics?.totals?.total_profit || selectedPortfolio.analytics?.total_profit || 0" 
          :monthly-change="parsedDashboard.monthlyChange"
          :invested-amount="parsedDashboard.investedAmount"
          :analytics="selectedPortfolio.analytics || {}"
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
      
      <!-- Большой виджет PortfolioChartWidget -->
      <WidgetContainer :gridColumn="8" minHeight="var(--widget-height-xlarge)">
        <PortfolioChartWidget 
          :chartData="parsedDashboard.portfolioChart"
        />
      </WidgetContainer>
      <WidgetContainer :gridColumn="4" minHeight="var(--widget-height-medium)">
        <AssetAllocationWidget
          :assetAllocation="assetAllocationData"
        />
      </WidgetContainer>
      
      <WidgetContainer :gridColumn="4" minHeight="var(--widget-height-medium)">
        <TopMoversWidget
          title="Топ роста за день"
          :assets="selectedPortfolio.combined_assets || []"
          direction="up"
        />
      </WidgetContainer>
      <WidgetContainer :gridColumn="4" minHeight="var(--widget-height-medium)">
        <TopMoversWidget
          title="Топ падений за день"
          :assets="selectedPortfolio.combined_assets || []"
          direction="down"
        />
      </WidgetContainer>
      <WidgetContainer :gridColumn="4" minHeight="var(--widget-height-medium)">
        <RecentTransactionsWidget
          :transactions="recentTransactions"
        />
      </WidgetContainer>
      <WidgetContainer :gridColumn="6" minHeight="var(--widget-height-medium)">
        <PayoutsChartWidget 
          title="Полученные выплаты по месяцам"
          :payouts="monthlyPayouts"
          mode="past"
        />
      </WidgetContainer>
      <WidgetContainer :gridColumn="6" minHeight="var(--widget-height-medium)">
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
}

/* Адаптивность для планшетов */
@media (max-width: 1200px) {
  .widgets-grid {
    grid-template-columns: repeat(6, 1fr);
  }
}

/* Адаптивность для мобильных */
@media (max-width: 768px) {
  .widgets-grid {
    grid-template-columns: 1fr;
  }
}
</style>