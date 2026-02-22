<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { useAuthStore } from '../stores/auth.store'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import { useTransactionsStore } from '../stores/transactions.store'
import PortfolioSelector from '../components/PortfolioSelector.vue'
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
import { 
  PayoutsChartWidget,
  PayoutsByAssetChartWidget,
  PortfoliosDistributionChartWidget,
  AnalyticsAssetDistributionWidget,
  MonthlyFlowChartWidget,
  PortfolioChartWidget,
  AssetReturnsChartWidget,
  PortfolioProfitChartWidget
} from '../components/widgets/charts'
import { WidgetContainer } from '../components/widgets/base'

// Используем stores
const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const uiStore = useUIStore()
const transactionsStore = useTransactionsStore()

// Локальное состояние
const selectedPortfolioAnalytics = ref(null)
const isLoadingAnalytics = ref(false)

const portfolios = computed(() => dashboardStore.portfolios ?? [])

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

// Форматирование чисел
function formatMoney(value) {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  }).format(value || 0)
}

function formatPercent(value) {
  return new Intl.NumberFormat('ru-RU', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format((value || 0) / 100)
}

// Обновление выбранной аналитики
async function updateSelectedAnalytics() {
  const allAnalytics = dashboardStore.analytics ?? []
  selectedPortfolioAnalytics.value =
    allAnalytics.find(a => a.portfolio_id === uiStore.selectedPortfolioId) || null

  if (!selectedPortfolioAnalytics.value) {
    console.warn('⚠️ Аналитика не найдена для портфеля', uiStore.selectedPortfolioId)
    return
  }
}

// Расчет годовых дивидендов: процент доходности * сумма портфеля
const calculatedAnnualDividends = computed(() => {
  if (!selectedPortfolioAnalytics.value?.totals) return 0
  const returnPercent = selectedPortfolioAnalytics.value.totals.return_percent || 0
  const totalValue = selectedPortfolioAnalytics.value.totals.total_value || 0
  // return_percent уже в процентах, поэтому делим на 100
  return (returnPercent / 100) * totalValue
})

// Получаем данные для графика динамики капитала (в формате для PortfolioChartWidget)
const portfolioChartData = computed(() => {
  if (!uiStore.selectedPortfolioId) return { labels: [], data_value: [], data_invested: [] }
  const portfolio = portfolios.value.find(p => p.id === uiStore.selectedPortfolioId)
  if (!portfolio?.history) return { labels: [], data_value: [], data_invested: [] }
  
  // Если история уже в нужном формате
  if (portfolio.history.labels && portfolio.history.data_value) {
    return {
      labels: portfolio.history.labels || [],
      data_value: portfolio.history.data_value || [],
      data_invested: portfolio.history.data_invested || []
    }
  }
  
  // Если история в формате массива объектов, преобразуем
  if (Array.isArray(portfolio.history) && portfolio.history.length > 0) {
    return {
      labels: portfolio.history.map(h => h.date || h.month || ''),
      data_value: portfolio.history.map(h => h.value || h.total_value || 0),
      data_invested: portfolio.history.map(h => h.invested || h.total_invested || 0)
    }
  }
  
  return { labels: [], data_value: [], data_invested: [] }
})

// Получаем выбранный портфель
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

// Данные для PortfolioProfitWidget
const profitWidgetData = computed(() => {
  if (!selectedPortfolio.value) {
    return {
      totalAmount: 0,
      totalProfit: 0,
      monthlyChange: 0,
      investedAmount: 0,
      analytics: {}
    }
  }
  return {
    totalAmount: selectedPortfolio.value.total_value || 0,
    totalProfit: selectedPortfolio.value.analytics?.totals?.total_profit || selectedPortfolio.value.analytics?.total_profit || 0,
    monthlyChange: selectedPortfolio.value.monthly_change || 0,
    investedAmount: selectedPortfolio.value.total_invested || 0,
    analytics: selectedPortfolio.value.analytics || {}
  }
})

// Данные для PortfolioProfitChartWidget
const profitChartData = computed(() => {
  if (!selectedPortfolio.value?.history) {
    return { labels: [], data_pnl: [] }
  }
  
  const history = selectedPortfolio.value.history
  
  // Если история уже в нужном формате
  if (history.labels && history.data_pnl) {
    return {
      labels: history.labels || [],
      data_pnl: history.data_pnl || []
    }
  }
  
  // Если история в формате массива объектов, преобразуем
  if (Array.isArray(history) && history.length > 0) {
    return {
      labels: history.map(h => h.date || ''),
      data_pnl: history.map(h => Number(h.pnl || h.total_pnl || 0))
    }
  }
  
  return { labels: [], data_pnl: [] }
})
</script>

<template>
  <PageLayout v-if="!uiStore.loading">
    <PageHeader 
      title="Финансовая аналитика"
      subtitle="Сводные показатели"
    >
      <template #actions>
        <PortfolioSelector 
          :portfolios="portfolios"
          :modelValue="uiStore.selectedPortfolioId"
          @update:modelValue="uiStore.setSelectedPortfolioId"
        />
      </template>
    </PageHeader>

    <LoadingState v-if="isLoadingAnalytics" message="Загрузка аналитики..." />

    <div v-else-if="selectedPortfolioAnalytics" class="widgets-grid">
      <!-- 4 маленьких виджета вверху -->
      <WidgetContainer :gridColumn="3" minHeight="var(--widget-height-small)">
        <TotalCapitalWidget 
          :total-amount="selectedPortfolioAnalytics.totals?.total_value || 0"
          :invested-amount="selectedPortfolioAnalytics.totals?.total_invested || 0"
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
          :return-percent="selectedPortfolioAnalytics.totals?.return_percent || 0"
          :return-percent-on-invested="selectedPortfolioAnalytics.totals?.return_percent_on_invested || 0"
          :total-value="selectedPortfolioAnalytics.totals?.total_value || 0"
          :total-invested="selectedPortfolioAnalytics.totals?.total_invested || 0"
        />
      </WidgetContainer>

      <!-- Виджет распределения активов и виджет динамики прибыли -->
      <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-xlarge)">
        <PortfolioChartWidget 
          :chart-data="portfolioChartData"
        />
      </WidgetContainer>
      
      <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-large)">
        <AnalyticsAssetDistributionWidget 
          :asset-distribution="selectedPortfolioAnalytics.asset_distribution || []"
          layout="horizontal"
        />
      </WidgetContainer>

      <!-- Виджет динамики прибыли -->
      <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-xlarge)">
        <PortfolioProfitChartWidget 
          :chartData="profitChartData"
        />
      </WidgetContainer>

      <!-- Остальные графики -->
      <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-medium)">
        <AssetReturnsChartWidget 
          :asset-returns="selectedPortfolioAnalytics.asset_returns || []"
        />
      </WidgetContainer>

      <WidgetContainer :gridColumn="6" minHeight="var(--widget-height-medium)">
        <PayoutsChartWidget 
          title="Полученные выплаты по месяцам"
          :payouts="selectedPortfolioAnalytics.monthly_payouts || []"
          mode="past"
        />
      </WidgetContainer>

      <WidgetContainer :gridColumn="6" minHeight="var(--widget-height-medium)">
        <PayoutsChartWidget 
          title="График будущих выплат"
          :payouts="selectedPortfolioAnalytics.future_payouts || []"
          mode="future"
        />
      </WidgetContainer>

      <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-medium)">
        <MonthlyFlowChartWidget 
          :monthly-flow="selectedPortfolioAnalytics.monthly_flow || []"
        />
      </WidgetContainer>

      <WidgetContainer :gridColumn="6" minHeight="var(--widget-height-medium)">
        <PayoutsByAssetChartWidget 
          :payouts-by-asset="selectedPortfolioAnalytics.payouts_by_asset || []"
        />
      </WidgetContainer>

      <WidgetContainer :gridColumn="6" minHeight="var(--widget-height-medium)">
        <PortfoliosDistributionChartWidget 
          :portfolios="portfolios"
          :all-portfolios="dashboardStore.analytics || []"
          :selected-portfolio-id="uiStore.selectedPortfolioId"
        />
      </WidgetContainer>
    </div>

    <LoadingState v-else />
  </PageLayout>
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
