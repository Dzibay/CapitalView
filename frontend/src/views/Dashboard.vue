<script setup>
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth.store'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import { usePortfoliosStore } from '../stores/portfolios.store'
import { usePortfolioAnalytics } from '../composables/usePortfolioAnalytics'
import { assetAllocationFromPositions } from '../utils/assetAllocationFromPositions'
import { collectSubtreeAssets } from '../utils/collectSubtreeAssets'

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
const phase2Ready = ref(false)
const phase3Ready = ref(false)

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
  portfolioChartData
} = usePortfolioAnalytics()

const childrenByParent = computed(() => {
  const map = new Map()
  for (const p of portfolios.value) {
    const parentId = p.parent_portfolio_id ?? '__root__'
    if (!map.has(parentId)) map.set(parentId, [])
    map.get(parentId).push(p.id)
  }
  return map
})

const selectedPortfolioIds = computed(() => {
  const root = selectedPortfolio.value
  if (!root) return new Set()

  const ids = new Set()
  const stack = [root.id]
  const tree = childrenByParent.value

  while (stack.length) {
    const id = stack.pop()
    if (ids.has(id)) continue
    ids.add(id)
    const children = tree.get(id) || []
    for (const childId of children) stack.push(childId)
  }

  return ids
})

const selectedTransactions = computed(() => {
  const ids = selectedPortfolioIds.value
  if (ids.size === 0) return []
  return (dashboardStore.transactions ?? []).filter(t => ids.has(t.portfolio_id))
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

// Позиции выбранной ветки (родитель + дочерние) — для графиков, т.к. у узла в store только прямые assets
const selectedSubtreeAssets = computed(() => {
  if (!selectedPortfolio.value) return []
  return collectSubtreeAssets(selectedPortfolio.value, portfolios.value)
})

const assetAllocationData = computed(() => {
  if (!selectedPortfolio.value) {
    return { labels: [], datasets: [{ backgroundColor: [], data: [] }] }
  }
  return assetAllocationFromPositions(selectedSubtreeAssets.value)
})

// Данные для MonthlyPayoutsChartWidget
const monthlyPayouts = computed(() => {
  return selectedPortfolioAnalytics.value?.monthly_payouts || []
})

// Данные для RecentTransactionsWidget - последние транзакции, отсортированные по дате
const recentTransactions = computed(() => {
  const top = []
  for (const tx of selectedTransactions.value) {
    const ts = new Date(tx.transaction_date || 0).getTime()
    if (!Number.isFinite(ts)) continue
    let inserted = false
    for (let i = 0; i < top.length; i++) {
      const cur = new Date(top[i].transaction_date || 0).getTime()
      if (ts > cur) {
        top.splice(i, 0, tx)
        inserted = true
        break
      }
    }
    if (!inserted) top.push(tx)
    if (top.length > 10) top.pop()
  }
  return top
})

onMounted(() => {
  // Фаза 2: после первого кадра подключаем основной график.
  requestAnimationFrame(() => {
    phase2Ready.value = true
  })

  // Фаза 3: второстепенные тяжёлые виджеты рендерим в idle-время.
  if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
    window.requestIdleCallback(() => {
      phase3Ready.value = true
    }, { timeout: 250 })
  } else {
    setTimeout(() => {
      phase3Ready.value = true
    }, 80)
  }
})

</script>

<template>
  <PageLayout v-if="!uiStore.loading && selectedPortfolio">
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
        <PortfolioChartWidget v-if="phase2Ready" :chartData="portfolioChartData" />
      </WidgetContainer>

      <!-- 2. Рост и падение за день (на планшете в одну строку) -->
      <WidgetContainer class="top-up-widget" :gridColumn="4" minHeight="var(--widget-height-medium)">
        <TopMoversWidget v-if="phase3Ready"
          title="Топ роста за день"
          :assets="selectedSubtreeAssets"
          direction="up"
        />
      </WidgetContainer>
      <WidgetContainer class="top-down-widget" :gridColumn="4" minHeight="var(--widget-height-medium)">
        <TopMoversWidget v-if="phase3Ready"
          title="Топ падений за день"
          :assets="selectedSubtreeAssets"
          direction="down"
        />
      </WidgetContainer>

      <!-- 3. Распределение активов и последние операции (на планшете в одну строку) -->
      <WidgetContainer class="allocation-widget" :gridColumn="4" minHeight="var(--widget-height-medium)">
        <AssetAllocationWidget v-if="phase3Ready"
          :assetAllocation="assetAllocationData"
        />
      </WidgetContainer>
      <WidgetContainer class="recent-tx-widget" :gridColumn="4" minHeight="var(--widget-height-medium)">
        <RecentTransactionsWidget v-if="phase3Ready"
          :transactions="recentTransactions"
        />
      </WidgetContainer>

      <!-- 4. Выплаты по месяцам — на планшете на всю ширину -->
      <WidgetContainer class="payouts-chart-widget" :gridColumn="6" minHeight="var(--widget-height-medium)">
        <PayoutsChartWidget v-if="phase3Ready"
          title="Полученные выплаты по месяцам"
          :payouts="monthlyPayouts"
          mode="past"
          enable-bar-navigation
        />
      </WidgetContainer>

      <!-- 5. Достижение цели — на планшете на всю ширину -->
      <WidgetContainer class="goal-progress-widget" :gridColumn="6" minHeight="var(--widget-height-medium)">
        <GoalProgressWidget v-if="phase3Ready"
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