<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { VueDraggable } from 'vue-draggable-plus'
import { SlidersHorizontal, Check, RotateCcw, Plus, GripVertical } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth.store'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import { usePortfoliosStore } from '../stores/portfolios.store'
import { useDividendsStore } from '../stores/dividends.store'
import { usePortfolioAnalytics } from '../composables/usePortfolioAnalytics'
import { collectSubtreeAssets } from '../utils/collectSubtreeAssets'
import { expandPortfolioHistoryForCharts } from '../utils/portfolioHistory'
import { dashboardEditing } from '../cabinet/state'
import { plural } from '../cabinet/format'
import { useDashboardLayout, WIDGETS } from '../cabinet/dashboard/useDashboardLayout'

import DashboardSkeleton from '../cabinet/dashboard/DashboardSkeleton.vue'
import CapitalWidget from '../cabinet/dashboard/CapitalWidget.vue'
import ProfitWidget from '../cabinet/dashboard/ProfitWidget.vue'
import AllocationWidget from '../cabinet/dashboard/AllocationWidget.vue'
import PayoutsWidget from '../cabinet/dashboard/PayoutsWidget.vue'
import MoversWidget from '../cabinet/dashboard/MoversWidget.vue'
import GoalWidget from '../cabinet/dashboard/GoalWidget.vue'
import IncomeWidget from '../cabinet/dashboard/IncomeWidget.vue'
import TransactionsWidget from '../cabinet/dashboard/TransactionsWidget.vue'
import InsightsWidget from '../cabinet/dashboard/InsightsWidget.vue'
import TopPositionsWidget from '../cabinet/dashboard/TopPositionsWidget.vue'
import CalendarWidget from '../cabinet/dashboard/CalendarWidget.vue'

const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const uiStore = useUIStore()
const portfoliosStore = usePortfoliosStore()
const dividendsStore = useDividendsStore()

const {
  portfolios,
  selectedPortfolio,
  selectedPortfolioAnalytics,
  balance,
  totalCapitalWidgetData,
  profitWidgetData,
  calculatedAnnualDividends,
  returnData,
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
  return (dashboardStore.transactions ?? []).filter((t) => ids.has(t.portfolio_id))
})

const goalData = computed(() => {
  if (!selectedPortfolio.value) return null
  const desc = selectedPortfolio.value.description || {}
  return {
    portfolioId: selectedPortfolio.value.id,
    title: desc.capital_target_name || desc.text || 'Цель не задана',
    targetAmount: desc.capital_target_value || 0,
    currentAmount: selectedPortfolio.value.total_value || 0, // total_value уже включает баланс на бэкенде
    deadline: desc.capital_target_deadline || null,
    currency: desc.capital_target_currency || 'RUB',
    monthlyContribution: desc.monthly_contribution || 0,
    annualReturn: desc.annual_return || 0,
    useInflation: desc.use_inflation || false,
    inflationRate: desc.inflation_rate || 7.5,
  }
})

// Позиции выбранной ветки (родитель + дочерние) — у узла в store только прямые assets
const selectedSubtreeAssets = computed(() => {
  if (!selectedPortfolio.value) return []
  return collectSubtreeAssets(selectedPortfolio.value, portfolios.value)
})

// Выплаты по позициям для календаря: один запрос на корневой портфель, фильтр ветки — на клиенте
const selectedPayoutPositions = computed(() => {
  const ids = selectedPortfolioIds.value
  return (dividendsStore.payoutPositionsFlat || []).filter((p) => ids.has(p.portfolio_id))
})

const capitalHistory = computed(() => expandPortfolioHistoryForCharts(selectedPortfolio.value?.history))
const monthlyPayouts = computed(() => selectedPortfolioAnalytics.value?.monthly_payouts || [])
const futurePayouts = computed(() => selectedPortfolioAnalytics.value?.future_payouts || [])

// Последние 10 операций по дате
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

// ── Шапка ──────────────────────────────────────────────
const greeting = computed(() => {
  const h = new Date().getHours()
  const hello = h >= 5 && h < 12 ? 'Доброе утро' : h >= 12 && h < 18 ? 'Добрый день' : h >= 18 && h < 23 ? 'Добрый вечер' : 'Доброй ночи'
  const name = String(authStore.user?.name || '').trim().split(/\s+/)[0]
  return name ? `${hello}, ${name}` : hello
})
const today = (() => {
  const s = new Intl.DateTimeFormat('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date())
  return s.charAt(0).toUpperCase() + s.slice(1)
})()
const positionsCount = computed(() => new Set(selectedSubtreeAssets.value.filter((a) => Number(a.quantity) > 0).map((a) => a.asset_id)).size)

// ── Раскладка ──────────────────────────────────────────
const { state: layout, visible, hiddenList, isCustom, resize, hide, show, reset } = useDashboardLayout()
const editing = dashboardEditing
const setEditing = (v) => { dashboardEditing.value = v }

const widgets = computed(() => ({
  capital: {
    is: CapitalWidget,
    props: {
      history: capitalHistory.value,
      totalAmount: totalCapitalWidgetData.value.totalAmount,
      investedAmount: totalCapitalWidgetData.value.investedAmount,
      balance: Number(balance.value) || 0,
      inflationRate: Number(selectedPortfolio.value?.description?.inflation_rate) || 7.5,
    },
  },
  profit: {
    is: ProfitWidget,
    props: {
      totalProfit: profitWidgetData.value.totalProfit,
      monthlyChange: profitWidgetData.value.monthlyChange,
      investedAmount: profitWidgetData.value.investedAmount,
      analytics: profitWidgetData.value.analytics,
      history: capitalHistory.value,
    },
  },
  insights: {
    is: InsightsWidget,
    props: { assets: selectedSubtreeAssets.value, analytics: selectedPortfolioAnalytics.value, history: capitalHistory.value },
  },
  allocation: { is: AllocationWidget, props: { assets: selectedSubtreeAssets.value } },
  top: { is: TopPositionsWidget, props: { assets: selectedSubtreeAssets.value } },
  calendar: {
    is: CalendarWidget,
    props: {
      positions: selectedPayoutPositions.value,
      referenceData: dashboardStore.referenceData,
      loading: dividendsStore.payoutPositionsLoading,
    },
  },
  payouts: { is: PayoutsWidget, props: { past: monthlyPayouts.value, future: futurePayouts.value } },
  movers: { is: MoversWidget, props: { assets: selectedSubtreeAssets.value } },
  goal: {
    is: GoalWidget,
    props: { goal: goalData.value, defaultReturn: returnData.value.returnPercent, onSave: portfoliosStore.updatePortfolioGoal },
  },
  income: {
    is: IncomeWidget,
    props: {
      annual: calculatedAnnualDividends.value,
      yieldPercent: returnData.value.returnPercent,
      yieldOnInvested: returnData.value.returnPercentOnInvested,
      future: futurePayouts.value,
    },
  },
  transactions: { is: TransactionsWidget, props: { transactions: recentTransactions.value, assets: selectedSubtreeAssets.value } },
}))

const ready = computed(() => !uiStore.loading && !!selectedPortfolio.value)

// каскадное появление — только при первом показе, чтобы перетаскивание не перезапускало анимацию
const intro = ref(true)
let introTimer
watch(ready, (r) => {
  if (!r) return
  clearTimeout(introTimer)
  introTimer = setTimeout(() => { intro.value = false }, 1400)
}, { immediate: true })

// календарь выплат грузит позиции с выплатами, только когда он виден
watch(
  () => ready.value && visible.value.includes('calendar'),
  (need) => {
    if (need && dividendsStore.payoutPositionsCacheIsEmpty && !dividendsStore.payoutPositionsLoading) {
      dividendsStore.fetchPayoutPositionsForAllPortfolios()
    }
  },
  { immediate: true },
)

const dragging = ref(false)

function onKey(e) {
  if (e.key === 'Escape' && editing.value) editing.value = false
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  clearTimeout(introTimer)
  editing.value = false
})
</script>

<template>
  <div class="dash" :class="{ 'is-editing': editing, 'is-dragging': dragging }">
    <Transition name="dash-swap" mode="out-in">
      <DashboardSkeleton v-if="!ready" key="skel" />

      <div v-else key="ready">
        <header class="dash__head">
          <div class="dash__titles">
            <p class="dash__date cv-eyebrow">{{ today }}</p>
            <h1 class="dash__title">{{ greeting }}</h1>
            <p class="dash__sub">
              {{ selectedPortfolio.name }}
              <span class="dash__dot" />
              {{ positionsCount }} {{ plural(positionsCount, 'позиция', 'позиции', 'позиций') }}
            </p>
          </div>
          <div class="dash__actions">
            <template v-if="editing">
              <button v-if="isCustom" type="button" class="cv-btn cv-btn--ghost" @click="reset">
                <RotateCcw :size="15" /> Сбросить
              </button>
              <button type="button" class="cv-btn cv-btn--primary" @click="setEditing(false)">
                <Check :size="16" /> Готово
              </button>
            </template>
            <button v-else type="button" class="cv-btn" @click="setEditing(true)">
              <SlidersHorizontal :size="15" /> Настроить
            </button>
          </div>
        </header>

        <Transition name="dash-tray">
          <div v-if="editing" class="dash__tray">
            <p class="dash__hint">
              <GripVertical :size="15" />
              Перетаскивайте виджеты за ручку, меняйте ширину и скрывайте лишнее. Раскладка сохранится.
            </p>
            <div v-if="hiddenList.length" class="dash__hidden">
              <span>Скрыты:</span>
              <button v-for="id in hiddenList" :key="id" type="button" class="dash__chip" @click="show(id)">
                <Plus :size="13" /> {{ WIDGETS[id].title }}
              </button>
            </div>
          </div>
        </Transition>

        <VueDraggable
          v-model="visible"
          class="dash__grid"
          :class="{ 'is-intro': intro }"
          handle=".cv-drag-handle"
          :disabled="!editing"
          :animation="260"
          easing="cubic-bezier(.22, 1, .36, 1)"
          ghost-class="is-ghost"
          chosen-class="is-chosen"
          drag-class="is-drag"
          @start="dragging = true"
          @end="dragging = false"
        >
          <div
            v-for="(id, i) in visible"
            :key="id"
            class="dash__item"
            :class="`is-${layout.sizes[id]}`"
            :style="{ '--i': i }"
          >
            <component
              :is="widgets[id].is"
              v-bind="widgets[id].props"
              :editing="editing"
              :size="layout.sizes[id]"
              :sizes="WIDGETS[id].sizes"
              @resize="(s) => resize(id, s)"
              @hide="hide(id)"
            />
          </div>
        </VueDraggable>

        <div v-if="!visible.length" class="dash__nothing cv-card">
          <b>Все виджеты скрыты</b>
          <p>Верните нужные из списка выше или сбросьте раскладку.</p>
          <button type="button" class="cv-btn cv-btn--primary cv-btn--sm" @click="reset">Сбросить раскладку</button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.dash { padding-bottom: 8px; }

.dash__head {
  display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap;
  padding: 26px 0 30px;
}
.dash__date { color: var(--cv-dim); animation: dash-rise .7s var(--cv-ease) backwards; }
.dash__title {
  margin-top: 10px;
  font-family: var(--cv-display); font-size: clamp(26px, 2.5vw, 34px); font-weight: 550; line-height: 1.12; letter-spacing: -0.035em;
  color: var(--cv-ink);
  animation: dash-rise .7s var(--cv-ease) backwards .04s;
}
.dash__sub {
  display: flex; align-items: center; gap: 9px; flex-wrap: wrap; margin-top: 8px;
  font-size: 13.5px; color: var(--cv-mut);
  animation: dash-rise .7s var(--cv-ease) backwards .08s;
}
.dash__dot { width: 3px; height: 3px; border-radius: 50%; background: var(--cv-dim); }
.dash__actions { display: flex; gap: 8px; animation: dash-rise .7s var(--cv-ease) backwards .1s; }
.dash__actions .cv-btn { gap: 7px; }

.dash__tray {
  display: flex; align-items: center; justify-content: space-between; gap: 12px 20px; flex-wrap: wrap;
  margin-bottom: 16px; padding: 12px 14px; border-radius: 14px;
  background: rgba(100, 116, 255, .06);
  box-shadow: inset 0 0 0 1px var(--cv-accent-line);
}
.dash__hint { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--cv-ink-2); }
.dash__hint svg { color: var(--cv-accent-ink); flex: none; }
.dash__hidden { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; font-size: 12.5px; color: var(--cv-mut); }
.dash__chip {
  display: inline-flex; align-items: center; gap: 5px; height: 28px; padding: 0 10px; border: 0; border-radius: 99px;
  background: rgba(255, 255, 255, .06); box-shadow: inset 0 0 0 1px var(--cv-line-2);
  color: var(--cv-ink); font-size: 12.5px; font-weight: 550; cursor: pointer;
  transition: background .2s, box-shadow .2s, transform .2s var(--cv-ease);
}
.dash__chip:hover { background: var(--cv-accent-soft); box-shadow: inset 0 0 0 1px var(--cv-accent-line); }
.dash__chip:active { transform: scale(.96); }

.dash__grid {
  display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: var(--cv-gap);
  align-items: stretch;
}
.dash__item { min-width: 0; grid-column: span 6; }
.dash__item.is-s { grid-column: span 4; }
.dash__item.is-m { grid-column: span 6; }
.dash__item.is-l { grid-column: span 8; }
.dash__item.is-xl { grid-column: span 12; }

.dash__grid.is-intro .dash__item { animation: dash-rise .75s var(--cv-ease) backwards; animation-delay: calc(var(--i) * 70ms + 120ms); }
@keyframes dash-rise {
  from { opacity: 0; transform: translateY(14px); filter: blur(4px); }
}

/* перетаскивание */
.dash__item.is-ghost > * { opacity: .35; box-shadow: 0 0 0 1px var(--cv-accent-line), 0 0 0 3px rgba(100, 116, 255, .18); }
.dash__item.is-ghost > * :deep(*) { visibility: hidden; }
.dash__item.is-drag > * { transform: rotate(1.2deg); box-shadow: var(--cv-pop-shadow); }
.dash.is-dragging { cursor: grabbing; user-select: none; }

.dash__nothing { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 40px 16px; text-align: center; color: var(--cv-mut); }
.dash__nothing b { color: var(--cv-ink); font-size: 15px; }

.dash-swap-enter-active { transition: opacity .35s var(--cv-ease); }
.dash-swap-leave-active { transition: opacity .15s ease; }
.dash-swap-enter-from, .dash-swap-leave-to { opacity: 0; }

.dash-tray-enter-active, .dash-tray-leave-active { transition: opacity .25s var(--cv-ease), transform .3s var(--cv-ease), margin .3s var(--cv-ease); }
.dash-tray-enter-from, .dash-tray-leave-to { opacity: 0; transform: translateY(-6px); }

@media (max-width: 1200px) {
  /* малые блоки становятся половинными — dense закрывает дыры рядом с широкими */
  .dash__grid { grid-auto-flow: row dense; }
  .dash__item.is-s, .dash__item.is-m { grid-column: span 6; }
  .dash__item.is-l, .dash__item.is-xl { grid-column: span 12; }
}
@media (max-width: 768px) {
  .dash__head { padding: 14px 0 20px; align-items: flex-start; }
  .dash__grid { gap: 12px; }
  .dash__item { grid-column: span 12 !important; }
}
@media (prefers-reduced-motion: reduce) {
  .dash__grid.is-intro .dash__item, .dash__date, .dash__title, .dash__sub, .dash__actions { animation: none; }
}
</style>
