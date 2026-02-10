<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { useAuthStore } from '../stores/auth.store'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import { useTransactionsStore } from '../stores/transactions.store'
import PortfolioSelector from '../components/PortfolioSelector.vue'
import LoadingState from '../components/LoadingState.vue'
import PageLayout from '../components/PageLayout.vue'
import PageHeader from '../components/PageHeader.vue'

// Виджеты
import MonthlyPayoutsChartWidget from '../components/widgets/MonthlyPayoutsChartWidget.vue'
import PayoutsByAssetChartWidget from '../components/widgets/PayoutsByAssetChartWidget.vue'
import FuturePayoutsChartWidget from '../components/widgets/FuturePayoutsChartWidget.vue'
import PortfoliosDistributionChartWidget from '../components/widgets/PortfoliosDistributionChartWidget.vue'
import AnalyticsAssetDistributionWidget from '../components/widgets/AnalyticsAssetDistributionWidget.vue'
import MonthlyFlowChartWidget from '../components/widgets/MonthlyFlowChartWidget.vue'
import PortfolioChartWidget from '../components/widgets/PortfolioChartWidget.vue'
import TotalCapitalWidget from '../components/widgets/TotalCapitalWidget.vue'
import ReturnWidget from '../components/widgets/ReturnWidget.vue'
import DividendsWidget from '../components/widgets/DividendsWidget.vue'
import AssetReturnsChartWidget from '../components/widgets/AssetReturnsChartWidget.vue'

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

    <div v-else-if="selectedPortfolioAnalytics" class="analytics-content">
      <!-- Виджеты -->
      <div class="widgets-grid">
        <TotalCapitalWidget 
          :total-amount="selectedPortfolioAnalytics.totals?.total_value || 0"
          :invested-amount="selectedPortfolioAnalytics.totals?.total_invested || 0"
        />
        <ReturnWidget 
          :return-percent="selectedPortfolioAnalytics.totals?.return_percent || 0"
          :total-value="selectedPortfolioAnalytics.totals?.total_value || 0"
          :total-invested="selectedPortfolioAnalytics.totals?.total_invested || 0"
        />
        <DividendsWidget 
          :annual-dividends="calculatedAnnualDividends"
        />
      </div>

      <!-- Графики -->
      <div class="charts-grid">
        <!-- 1) График стоимости портфеля -->
        <PortfolioChartWidget 
          :chart-data="portfolioChartData"
        />

        <!-- 2) График распределения активов -->
        <AnalyticsAssetDistributionWidget 
          class="full-width-chart"
          :asset-distribution="selectedPortfolioAnalytics.asset_distribution || []"
          layout="horizontal"
        />

        <!-- 2.5) График доходности активов -->
        <AssetReturnsChartWidget 
          class="full-width-chart"
          :asset-returns="selectedPortfolioAnalytics.asset_returns || []"
        />

        <!-- 3) График полученных выплат по месяцам и график будущих выплат -->
        <MonthlyPayoutsChartWidget 
          class="half-width-chart"
          :monthly-payouts="selectedPortfolioAnalytics.monthly_payouts || []"
        />

        <FuturePayoutsChartWidget 
          class="half-width-chart"
          :future-payouts="selectedPortfolioAnalytics.future_payouts || []"
        />

        <!-- 4) График месячных потоков и график выплат по активам -->
        <MonthlyFlowChartWidget 
          class="full-width-chart"
          :monthly-flow="selectedPortfolioAnalytics.monthly_flow || []"
        />

        <PayoutsByAssetChartWidget 
          class="half-width-chart"
          :payouts-by-asset="selectedPortfolioAnalytics.payouts_by_asset || []"
        />

        <!-- 5) График распределения портфелей -->
        <PortfoliosDistributionChartWidget 
          class="half-width-chart"
          :portfolios="portfolios"
          :all-portfolios="dashboardStore.analytics || []"
          :selected-portfolio-id="uiStore.selectedPortfolioId"
        />
      </div>
    </div>

    <LoadingState v-else />
  </PageLayout>
</template>

<style scoped>
.analytics-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.widgets-grid {
  display: grid;
  gap: var(--spacing);
  grid-template-columns: repeat(auto-fit, minmax(clamp(350px, 20%, 400px), 1fr));
  grid-auto-rows: 150px;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing);
}

.charts-grid > :first-child {
  min-height: 450px;
}

.charts-grid > *:first-child {
  grid-column: 1 / -1;
}

.charts-grid > .full-width-chart {
  grid-column: 1 / -1;
}

.charts-grid > .half-width-chart {
  grid-column: span 1;
}

@media (max-width: 800px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
  
  .charts-grid > .half-width-chart {
    grid-column: span 1;
  }
}



@media (max-width: 768px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
  
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
