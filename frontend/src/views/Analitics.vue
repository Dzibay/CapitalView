<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import { usePortfolioAnalytics } from '../composables/usePortfolioAnalytics'
import { collectSubtreeAssets } from '../utils/collectSubtreeAssets'
import { expandPortfolioHistoryForCharts } from '../utils/portfolioHistory'
import { money, moneyCompact, pct, plural, dateShort } from '../cabinet/format'

import CvPageHead from '../cabinet/ui/CvPageHead.vue'
import CvKpiStrip from '../cabinet/ui/CvKpiStrip.vue'
import DashboardSkeleton from '../cabinet/dashboard/DashboardSkeleton.vue'
import CapitalWidget from '../cabinet/dashboard/CapitalWidget.vue'
import ProfitWidget from '../cabinet/dashboard/ProfitWidget.vue'
import AllocationWidget from '../cabinet/dashboard/AllocationWidget.vue'
import PayoutsWidget from '../cabinet/dashboard/PayoutsWidget.vue'
import ProfitChartWidget from '../cabinet/analytics/ProfitChartWidget.vue'
import AssetReturnsWidget from '../cabinet/analytics/AssetReturnsWidget.vue'
import FlowWidget from '../cabinet/analytics/FlowWidget.vue'
import PayoutsByAssetWidget from '../cabinet/analytics/PayoutsByAssetWidget.vue'
import PortfolioShareWidget from '../cabinet/analytics/PortfolioShareWidget.vue'

const dashboardStore = useDashboardStore()
const uiStore = useUIStore()

const {
  portfolios,
  selectedPortfolio,
  selectedPortfolioAnalytics,
  isLoadingAnalytics,
  balance,
  totalCapitalWidgetData,
  profitWidgetData,
  calculatedAnnualDividends,
  returnData,
  safeLoadAnalytics,
} = usePortfolioAnalytics()

// При прямом переходе на /analitics данные могут ещё не загрузиться — подстраховка
onMounted(async () => {
  if (!portfolios.value?.length) {
    await dashboardStore.fetchDashboard(false, false)
    await safeLoadAnalytics()
  }
})

const analytics = computed(() => selectedPortfolioAnalytics.value || {})
const capitalHistory = computed(() => expandPortfolioHistoryForCharts(selectedPortfolio.value?.history))
const subtreeAssets = computed(() => (selectedPortfolio.value ? collectSubtreeAssets(selectedPortfolio.value, portfolios.value) : []))
const positionsCount = computed(() => new Set(subtreeAssets.value.filter((a) => Number(a.quantity) > 0).map((a) => a.asset_id)).size)

// ── шапка ──────────────────────────────────────────────────────────────────
const meta = computed(() => {
  const list = [`${positionsCount.value} ${plural(positionsCount.value, 'позиция', 'позиции', 'позиций')}`]
  const first = capitalHistory.value.labels?.[0]
  if (first) list.push(`история с ${dateShort(first)} ${new Date(first).getFullYear()}`)
  return list
})

// ── ключевые показатели ────────────────────────────────────────────────────
const kpis = computed(() => {
  const total = totalCapitalWidgetData.value.totalAmount
  const invested = profitWidgetData.value.investedAmount
  const profit = profitWidgetData.value.totalProfit
  const month = profitWidgetData.value.monthlyChange
  const monthBase = total - month
  const annual = calculatedAnnualDividends.value
  return [
    { key: 'capital', label: 'Капитал', value: total, format: (v) => money(v), note: `вложено ${moneyCompact(totalCapitalWidgetData.value.investedAmount)}` },
    {
      key: 'profit', label: 'Прибыль за всё время', value: profit, format: (v) => money(v, { sign: true }),
      tone: profit > 0 ? 'up' : profit < 0 ? 'down' : '', delta: invested ? (profit / invested) * 100 : 0, note: 'к вложенному',
    },
    {
      key: 'month', label: 'Изменение за месяц', value: month, format: (v) => money(v, { sign: true }),
      delta: monthBase > 0 ? (month / monthBase) * 100 : 0, note: 'без пополнений',
    },
    {
      key: 'income', label: 'Пассивный доход в год', value: annual, format: (v) => money(v),
      note: `${pct(returnData.value.returnPercent, { sign: false })} годовых · ${moneyCompact(annual / 12)} в месяц`,
    },
  ]
})

// ── доли подпортфелей ──────────────────────────────────────────────────────
const shareItems = computed(() => {
  const root = selectedPortfolio.value
  if (!root) return []
  const children = portfolios.value.filter((p) => p.parent_portfolio_id === root.id)
  if (!children.length) return []
  const valueOf = (id, fallback) => {
    const a = (dashboardStore.analytics || []).find((x) => x.portfolio_id === id)
    return Number(a?.totals?.total_value ?? fallback) || 0
  }
  const items = children.map((c) => ({ id: c.id, name: c.name, value: valueOf(c.id, c.total_value) }))
  const own = valueOf(root.id, root.total_value) - items.reduce((s, i) => s + i.value, 0)
  if (own > 1) items.push({ id: `own-${root.id}`, name: 'Свободные средства и активы без подпортфеля', value: own })
  return items
})
const hasShares = computed(() => shareItems.value.length > 1)

const ready = computed(() => !uiStore.loading && !!selectedPortfolio.value)

// каскадное появление — только при первом показе
const intro = ref(true)
watch(ready, (r) => { if (r) setTimeout(() => { intro.value = false }, 1600) }, { immediate: true })
</script>

<template>
  <div class="an">
    <Transition name="an-swap" mode="out-in">
      <DashboardSkeleton v-if="!ready || (isLoadingAnalytics && !selectedPortfolioAnalytics)" key="skel" />

      <div v-else-if="!portfolios.length" key="none" class="an__empty cv-card">
        <b>Портфелей пока нет</b>
        <p>Создайте портфель или импортируйте операции из брокера — аналитика появится здесь.</p>
      </div>

      <div v-else key="ready">
        <CvPageHead :eyebrow="selectedPortfolio.name" title="Аналитика портфеля" :meta="meta" />

        <div class="cv-grid" :class="{ 'is-intro': intro }">
          <CvKpiStrip class="is-xl" :items="kpis" :style="{ '--i': 0 }" />

          <CapitalWidget
            class="is-xl"
            :style="{ '--i': 1 }"
            :history="capitalHistory"
            :total-amount="totalCapitalWidgetData.totalAmount"
            :invested-amount="totalCapitalWidgetData.investedAmount"
            :balance="Number(balance) || 0"
            :inflation-rate="Number(selectedPortfolio.description?.inflation_rate) || 7.5"
          />

          <ProfitChartWidget class="is-l" :style="{ '--i': 2 }" :history="capitalHistory" />
          <ProfitWidget
            class="is-s is-full-md"
            :style="{ '--i': 3 }"
            :total-profit="profitWidgetData.totalProfit"
            :monthly-change="profitWidgetData.monthlyChange"
            :invested-amount="profitWidgetData.investedAmount"
            :analytics="profitWidgetData.analytics"
            :history="capitalHistory"
          />

          <AssetReturnsWidget class="is-xl" :style="{ '--i': 4 }" :asset-returns="analytics.asset_returns || []" />

          <AllocationWidget :class="hasShares ? 'is-l' : 'is-xl'" :style="{ '--i': 5 }" :assets="subtreeAssets" />
          <PortfolioShareWidget v-if="hasShares" class="is-s is-full-md" :style="{ '--i': 6 }" :items="shareItems" />

          <PayoutsWidget class="is-l" :style="{ '--i': 7 }" :past="analytics.monthly_payouts || []" :future="analytics.future_payouts || []" />
          <PayoutsByAssetWidget class="is-s is-full-md" :style="{ '--i': 8 }" :payouts="analytics.payouts_by_asset || []" />

          <FlowWidget class="is-xl" :style="{ '--i': 9 }" :flow="analytics.monthly_flow || []" />
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.an { padding-bottom: 8px; }
.an__empty { display: flex; flex-direction: column; align-items: center; gap: 8px; margin-top: 32px; padding: 48px 16px; text-align: center; color: var(--cv-mut); }
.an__empty b { color: var(--cv-ink); font-size: 15px; }
.an__empty p { margin: 0; max-width: 420px; font-size: 13.5px; }

.an-swap-enter-active { transition: opacity .35s var(--cv-ease); }
.an-swap-leave-active { transition: opacity .15s ease; }
.an-swap-enter-from, .an-swap-leave-to { opacity: 0; }
</style>
