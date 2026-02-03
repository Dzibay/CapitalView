<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { useAuthStore } from '../stores/auth.store'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import { useTransactionsStore } from '../stores/transactions.store'
import PortfolioSelector from '../components/PortfolioSelector.vue'
import LoadingState from '../components/LoadingState.vue'

// Виджеты
import MonthlyPayoutsChartWidget from '../components/widgets/MonthlyPayoutsChartWidget.vue'
import PayoutsByAssetChartWidget from '../components/widgets/PayoutsByAssetChartWidget.vue'
import FuturePayoutsChartWidget from '../components/widgets/FuturePayoutsChartWidget.vue'
import PortfoliosDistributionChartWidget from '../components/widgets/PortfoliosDistributionChartWidget.vue'
import AnalyticsAssetDistributionWidget from '../components/widgets/AnalyticsAssetDistributionWidget.vue'

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
</script>

<template>
  <div v-if="!uiStore.loading" class="analytics-container">
    <div class="title" style="display: flex; align-items: center; justify-content: space-between;">
      <div>
        <h1>Финансовая аналитика</h1>
        <h2>Сводные показатели</h2>
      </div>

      <PortfolioSelector 
        :portfolios="portfolios"
        :modelValue="uiStore.selectedPortfolioId"
        @update:modelValue="uiStore.setSelectedPortfolioId"
      />
    </div>

    <LoadingState v-if="isLoadingAnalytics" message="Загрузка аналитики..." />

    <div v-else-if="selectedPortfolioAnalytics" class="analytics-content">
      <!-- Метрики -->
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-label">Доходность портфеля</div>
          <div class="metric-value" :class="(selectedPortfolioAnalytics.totals?.return_percent || 0) >= 0 ? 'positive' : 'negative'">
            {{ formatPercent(selectedPortfolioAnalytics.totals?.return_percent || 0) }}
          </div>
        </div>
        
        <div class="metric-card">
          <div class="metric-label">Дивиденды в год</div>
          <div class="metric-value positive">
            {{ formatMoney(selectedPortfolioAnalytics.totals?.dividends_per_year || 0) }}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-label">Инвестировано</div>
          <div class="metric-value">
            {{ formatMoney(selectedPortfolioAnalytics.totals?.total_invested || 0) }}
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-label">Текущая стоимость</div>
          <div class="metric-value">
            {{ formatMoney(selectedPortfolioAnalytics.totals?.total_value || 0) }}
          </div>
        </div>
      </div>

      <!-- Графики -->
      <div class="charts-grid">
        <!-- График полученных выплат по месяцам -->
        <MonthlyPayoutsChartWidget 
          :monthly-payouts="selectedPortfolioAnalytics.monthly_payouts || []"
        />

        <!-- Распределение по активам -->
        <AnalyticsAssetDistributionWidget 
          :asset-distribution="selectedPortfolioAnalytics.asset_distribution || []"
        />

        <!-- График будущих выплат -->
        <FuturePayoutsChartWidget 
          :future-payouts="selectedPortfolioAnalytics.future_payouts || []"
        />

        <!-- График полученных выплат по активам -->
        <PayoutsByAssetChartWidget 
          :payouts-by-asset="selectedPortfolioAnalytics.payouts_by_asset || []"
        />

        <!-- Круговая диаграмма портфелей -->
        <PortfoliosDistributionChartWidget 
          :portfolios="portfolios"
          :all-portfolios="dashboardStore.analytics || []"
          :selected-portfolio-id="uiStore.selectedPortfolioId"
        />
      </div>
    </div>

    <LoadingState v-else />
  </div>
</template>

<style scoped>
.analytics-container {
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.title {
  margin-bottom: var(--spacing);
}

.analytics-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--spacing);
}

.metric-card {
  background: white;
  padding: 24px;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-label {
  font-size: 0.9rem;
  color: #6b7280;
  font-weight: 500;
}

.metric-value {
  font-size: 1.8rem;
  font-weight: 600;
  color: #111827;
}

.metric-value.positive {
  color: #10b981;
}

.metric-value.negative {
  color: #ef4444;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: var(--spacing);
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
