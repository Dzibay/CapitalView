<script setup>
import { computed, inject, onUnmounted, ref, unref, watch } from 'vue'
import { BarChart2 } from 'lucide-vue-next'
import Widget from '../base/Widget.vue'
import ValueChangePill from '../base/ValueChangePill.vue'
import Tooltip from '../../base/Tooltip.vue'
import { formatCurrency } from '../../../utils/formatCurrency'
import { LANDING_DASH_REVEAL_KEY } from '../../../constants/landingDashboardReveal'

const props = defineProps({
  totalAmount: { type: Number, required: true },
  investedAmount: { type: Number, required: true },
  totalProfit: { type: Number, default: 0 },
  monthlyChange: { type: Number, default: 0 },
  analytics: { type: Object, default: () => ({}) },
  annualDividends: { type: Number, default: 0 },
  returnPercent: { type: Number, default: 0 },
  returnPercentOnInvested: { type: Number, default: 0 },
  scrollReveal: { type: Boolean, default: false },
  landingRevealRef: { type: [Object, Boolean], default: null }
})

const injectedLandingReveal = inject(LANDING_DASH_REVEAL_KEY, null)

function revealSource() {
  return props.landingRevealRef ?? injectedLandingReveal
}

function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3)
}

const revealT = ref(1)
const popScale = ref(1)
let consRaf = null

function applyStaticReveal() {
  revealT.value = 1
  popScale.value = 1
}

function runRevealAnim() {
  const duration = 920
  if (prefersReducedMotion()) {
    applyStaticReveal()
    return
  }
  const start = performance.now()
  if (consRaf) cancelAnimationFrame(consRaf)
  function frame(now) {
    const u = Math.min(1, (now - start) / duration)
    const t = easeOutCubic(u)
    revealT.value = t
    popScale.value = 0.92 + 0.08 * t
    if (u < 1) consRaf = requestAnimationFrame(frame)
    else {
      consRaf = null
      applyStaticReveal()
    }
  }
  revealT.value = 0
  popScale.value = 0.92
  consRaf = requestAnimationFrame(frame)
}

function syncConsolidatedReveal() {
  if (!props.scrollReveal) {
    applyStaticReveal()
    return
  }
  const src = revealSource()
  if (src == null) {
    applyStaticReveal()
    return
  }
  const revealed = unref(src)
  if (!revealed) {
    revealT.value = 0
    popScale.value = 0.92
    return
  }
  runRevealAnim()
}

watch(
  () => {
    if (!props.scrollReveal) return true
    const src = revealSource()
    if (src == null) return true
    return unref(src)
  },
  () => syncConsolidatedReveal(),
  { immediate: true }
)

onUnmounted(() => {
  if (consRaf) cancelAnimationFrame(consRaf)
})

const capitalProfitPercent = computed(() => {
  if (!props.investedAmount || props.investedAmount === 0) return 0
  return ((props.totalAmount - props.investedAmount) / props.investedAmount) * 100
})

const capitalProfitAmount = computed(() => props.totalAmount - props.investedAmount)

const capitalTooltip = computed(() => {
  const fmt = formatCurrency(capitalProfitAmount.value)
  return `Разница между текущей стоимостью активов и суммой инвестиций составляет ${Math.abs(capitalProfitPercent.value).toFixed(2)}% (${fmt})`
})

const profitToInvestedPercent = computed(() => {
  if (!props.investedAmount || props.investedAmount === 0) return 0
  return (props.totalProfit / props.investedAmount) * 100
})

const formatForTooltip = (value) =>
  new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(value || 0)

const profitBreakdown = computed(() => {
  const a = props.analytics || {}
  const t = a.totals || {}
  return {
    realized: t.realized_pl ?? a.realized_pl ?? 0,
    unrealized: t.unrealized_pl ?? a.unrealized_pl ?? 0,
    dividends: t.dividends ?? a.dividends ?? 0,
    coupons: t.coupons ?? a.coupons ?? 0,
    commissions: Math.abs(t.commissions ?? a.commissions ?? 0),
    taxes: Math.abs(t.taxes ?? a.taxes ?? 0),
    total: props.totalProfit
  }
})

const profitBreakdownTooltip = computed(() => {
  const b = profitBreakdown.value
  const parts = []
  if (b.realized !== 0) parts.push(`Реализованная прибыль: ${formatForTooltip(b.realized)}`)
  if (b.unrealized !== 0) parts.push(`Нереализованная прибыль: ${formatForTooltip(b.unrealized)}`)
  if (b.dividends !== 0) parts.push(`Дивиденды: ${formatForTooltip(b.dividends)}`)
  if (b.coupons !== 0) parts.push(`Купоны: ${formatForTooltip(b.coupons)}`)
  if (b.commissions !== 0) parts.push(`Комиссии: ${formatForTooltip(-b.commissions)}`)
  if (b.taxes !== 0) parts.push(`Налоги: ${formatForTooltip(-b.taxes)}`)
  if (parts.length === 0) return 'Прибыль: 0 ₽'
  return `Состав прибыли:\n${parts.join('\n')}\n\nИтого: ${formatForTooltip(b.total)}`
})

const dividendsMonthly = computed(() => (props.annualDividends || 0) / 12)

const formattedPercent = (value) =>
  new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value) + '%'

const displayTotalAmount = computed(() => Math.round(props.totalAmount * revealT.value))
const displayInvestedAmount = computed(() => Math.round(props.investedAmount * revealT.value))
const displayCapitalProfitPercent = computed(() => capitalProfitPercent.value * revealT.value)
const displayTotalProfit = computed(() => props.totalProfit * revealT.value)
const displayProfitToInvestedPercent = computed(() => profitToInvestedPercent.value * revealT.value)
const displayAnnualDividends = computed(() => Math.round(props.annualDividends * revealT.value))
const displayDividendsMonthly = computed(() => Math.round(dividendsMonthly.value * revealT.value))
const displayReturnPercent = computed(() => props.returnPercent * revealT.value)
const displayReturnOnInvested = computed(() => props.returnPercentOnInvested * revealT.value)

const topSectionStyle = computed(() =>
  props.scrollReveal
    ? { transform: `scale(${popScale.value})`, transformOrigin: 'left center', willChange: 'transform' }
    : undefined
)
</script>

<template>
  <Widget title="Показатели" :icon="BarChart2" :compact="true">
    <div class="consolidated-content">
      <!-- 1. Общий капитал: слева сумма и «Инвестировано», справа value-change по центру по высоте -->
      <div class="top-section">
        <div class="top-section-left" :style="topSectionStyle">
          <Tooltip :content="capitalTooltip" position="top">
            <div class="main-value">
              {{ formatCurrency(displayTotalAmount, { minimumFractionDigits: 0, maximumFractionDigits: 0 }) }}
            </div>
          </Tooltip>
          <p class="secondary-text invested-line">
            Инвестировано: {{ formatCurrency(displayInvestedAmount, { maximumFractionDigits: 0 }) }}
          </p>
        </div>
        <div class="top-section-right">
          <ValueChangePill
            :value="displayCapitalProfitPercent"
            :is-positive="capitalProfitPercent >= 0"
            format="percent"
          />
        </div>
      </div>

      <!-- 2. Прибыль: отступ сверху, подпись не жирная -->
      <div class="profit-section">
        <div class="profit-row">
          <span class="profit-label">Прибыль</span>
          <div class="profit-right">
            <Tooltip :content="profitBreakdownTooltip" position="top">
              <span class="profit-value" :class="totalProfit >= 0 ? 'positive' : 'negative'">
                {{ totalProfit >= 0 ? '+' : '' }}{{ formatCurrency(displayTotalProfit, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
              </span>
            </Tooltip>
            <ValueChangePill
              :value="displayProfitToInvestedPercent"
              :is-positive="profitToInvestedPercent >= 0"
              format="percent"
            />
          </div>
        </div>
      </div>

      <div class="separator" />

      <!-- 3. Нижний блок: слева дивиденды, справа доходность (без иконок, уменьшенный шрифт) -->
      <div class="bottom-grid">
        <div class="bottom-block">
          <span class="bottom-label">Дивиденды</span>
          <Tooltip content="Среднегодовые дивиденды всех активов в портфеле" position="top">
            <div class="bottom-value">{{ formatCurrency(displayAnnualDividends, { maximumFractionDigits: 0 }) }} в год</div>
          </Tooltip>
          <p class="secondary-text">{{ formatCurrency(displayDividendsMonthly, { maximumFractionDigits: 0 }) }} в месяц</p>
        </div>
        <div class="bottom-block">
          <span class="bottom-label">Доходность</span>
          <Tooltip
            content="Средневзвешенная годовая доходность всех активов в портфеле (на основе текущей стоимости активов и средней дивидендной доходности за 5 лет). Учитывается только дивидендная и купонная доходность"
            position="top"
          >
            <div class="bottom-value">{{ formattedPercent(displayReturnPercent) }}</div>
          </Tooltip>
          <p class="secondary-text">
            <Tooltip content="Средневзвешенная годовая доходность на основе средней цены покупки активов" position="top">
              <span>на вложенный капитал: {{ formattedPercent(displayReturnOnInvested) }}</span>
            </Tooltip>
          </p>
        </div>
      </div>
    </div>
  </Widget>
</template>

<style scoped>
.consolidated-content {
  margin-top: 0.25rem;
  display: flex;
  flex-direction: column;
}

.top-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0;
}
.top-section-left {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.top-section-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.main-value {
  font-size: var(--widget-font-main, 1.5rem);
  font-weight: var(--widget-font-main-weight, 600);
  color: var(--text-primary, #111827);
  line-height: 1.2;
  margin: 0;
}
.invested-line {
  margin: 0;
}
.secondary-text {
  margin: 0;
  font-size: var(--widget-font-secondary, 1rem);
  color: var(--text-tertiary, #6b7280);
  line-height: 1.2;
}

.profit-section {
  margin-top: 1rem;
}
.profit-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}
.profit-label {
  font-size: var(--widget-font-secondary, 1rem);
  color: var(--text-tertiary, #6b7280);
  font-weight: var(--text-body-secondary-weight);
}
.profit-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.profit-value {
  font-size: var(--widget-font-secondary, 1rem);
  font-weight: var(--text-value-weight);
}
.profit-value.positive {
  color: var(--positiveColor, #1CBD88);
}
.profit-value.negative {
  color: var(--negativeColor, #EF4444);
}

.separator {
  height: 1px;
  background: #e2e8f0;
  margin: 0.5rem 0;
}

.bottom-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
.bottom-block {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.bottom-label {
  font-size: var(--widget-font-label, 0.95rem);
  font-weight: var(--widget-font-label-weight, 500);
  color: var(--text-tertiary, #6b7280);
}
.bottom-value {
  font-size: var(--widget-font-main, 1.5rem);
  font-weight: var(--widget-font-main-weight, 600);
  color: var(--text-primary, #111827);
  line-height: 1.2;
}
</style>
