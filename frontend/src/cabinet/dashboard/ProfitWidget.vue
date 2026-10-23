<script setup>
/**
 * Прибыль: итог, одна строка контекста, из чего сложилась (сегментная полоса) и тренд за год.
 * Суммы по источникам — при наведении на сегмент или пункт легенды.
 */
import { computed, onMounted, ref } from 'vue'
import CvWidget from '../ui/CvWidget.vue'
import CvNumber from '../ui/CvNumber.vue'
import CvDelta from '../ui/CvDelta.vue'
import Sparkline from '../charts/Sparkline.vue'
import { SERIES } from '../palette'
import { money, pct, dateLong } from '../format'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  totalProfit: { type: Number, default: 0 },
  monthlyChange: { type: Number, default: 0 },
  investedAmount: { type: Number, default: 0 },
  analytics: { type: Object, default: null },
  /** expandPortfolioHistoryForCharts(...) — для тренда прибыли за год */
  history: { type: Object, default: null },
})

const profitPct = computed(() => (props.investedAmount ? (props.totalProfit / props.investedAmount) * 100 : 0))

/** источники прибыли; цвет закреплён за источником, расходы и убытки в полосу не входят */
const SOURCES = [
  { key: 'unrealized', label: 'Рост стоимости', color: SERIES[0], pick: (t) => Number(t.unrealized_pl) || 0, always: true },
  { key: 'realized', label: 'Зафиксировано', color: SERIES[2], pick: (t) => Number(t.realized_pl) || 0, always: true },
  { key: 'dividends', label: 'Дивиденды', color: SERIES[1], pick: (t) => Number(t.dividends) || 0 },
  { key: 'coupons', label: 'Купоны', color: SERIES[3], pick: (t) => Number(t.coupons) || 0 },
  { key: 'commissions', label: 'Комиссии', pick: (t) => -Math.abs(Number(t.commissions) || 0) },
  { key: 'taxes', label: 'Налоги', pick: (t) => -Math.abs(Number(t.taxes) || 0) },
]

const parts = computed(() => {
  const t = props.analytics?.totals || props.analytics || {}
  return SOURCES.map((s) => ({ ...s, value: s.pick(t) })).filter((s) => s.always || s.value !== 0)
})
const gross = computed(() => parts.value.reduce((sum, p) => sum + Math.max(0, p.value), 0))
const segments = computed(() =>
  parts.value.filter((p) => p.value > 0).map((p) => ({ ...p, share: (p.value / (gross.value || 1)) * 100 })),
)
const costsTotal = computed(() => parts.value.reduce((s, p) => s + Math.min(0, p.value), 0))

const active = ref(null)
const activePart = computed(() => parts.value.find((p) => p.key === active.value) || null)
const barLabel = computed(() => segments.value.map((s) => `${s.label} ${pct(s.share, { sign: false })}`).join(', '))

// прибыль за последние 12 месяцев (не больше ~120 точек)
const trend = computed(() => {
  const labels = props.history?.labels || []
  const pnl = props.history?.data_pnl || []
  if (labels.length < 2) return null
  const from = new Date()
  from.setFullYear(from.getFullYear() - 1)
  let start = labels.findIndex((l) => new Date(l) >= from)
  if (start < 0) return null
  start = Math.max(0, start - 1)
  const step = Math.max(1, Math.ceil((labels.length - start) / 120))
  const idx = []
  for (let i = start; i < labels.length; i += step) idx.push(i)
  if (idx[idx.length - 1] !== labels.length - 1) idx.push(labels.length - 1)
  if (idx.length < 2) return null
  const values = idx.map((i) => Number(pnl[i]) || 0)
  return { labels: idx.map((i) => labels[i]), values, change: values[values.length - 1] - values[0] }
})

// сегменты «вырастают» после монтирования
const grown = ref(false)
onMounted(() => requestAnimationFrame(() => requestAnimationFrame(() => { grown.value = true })))

const fmt = (v) => money(v, { sign: true })
const legendValue = (p) => (p.value < 0 ? money(p.value) : pct((p.value / (gross.value || 1)) * 100, { sign: false, digits: 0 }))
</script>

<template>
  <CvWidget v-bind="$attrs" title="Прибыль">
    <div class="pf">
      <div class="pf__value">
        <CvNumber :value="totalProfit" :format="fmt" dim />
      </div>
      <dl class="pf__meta">
        <div><dt>От вложенного</dt><dd><CvDelta :value="profitPct" kind="pct" :pill="false" /></dd></div>
        <div><dt>За месяц</dt><dd><CvDelta :value="monthlyChange" kind="money" :pill="false" /></dd></div>
      </dl>

      <div class="pf__mix" @pointerleave="active = null">
        <div class="pf__mix-head">
          <span>Из чего сложилась</span>
          <Transition name="pf-swap" mode="out-in">
            <span v-if="activePart" :key="activePart.key" class="pf__mix-now cv-num">
              <b :class="{ 'cv-down': activePart.value < 0 }">{{ money(activePart.value, { sign: true }) }}</b>
            </span>
          </Transition>
        </div>
        <div class="pf__bar" :class="{ 'is-grown': grown, 'has-active': active }" role="img" :aria-label="barLabel">
          <i
            v-for="(s, i) in segments"
            :key="s.key"
            :class="{ 'is-on': active === s.key }"
            :style="{ flexGrow: s.share, background: s.color, '--i': i }"
            @pointerenter="active = s.key"
          />
        </div>
        <ul class="pf__legend">
          <li
            v-for="p in parts"
            :key="p.key"
            :class="{ 'is-on': active === p.key, 'is-cost': p.value < 0 }"
            @pointerenter="active = p.key"
          >
            <i :style="p.value > 0 ? { background: p.color } : null" />
            <span>{{ p.label }}</span>
            <b class="cv-num">{{ legendValue(p) }}</b>
          </li>
        </ul>
        <p v-if="costsTotal < 0 && gross > 0" class="pf__costs">
          Комиссии и налоги забрали {{ pct((Math.abs(costsTotal) / gross) * 100, { sign: false }) }} заработанного
        </p>
      </div>

      <div v-if="trend" class="pf__trend">
        <div class="pf__trend-head">
          <span>12 месяцев</span>
          <CvDelta :value="trend.change" kind="money" :pill="false" />
        </div>
        <Sparkline
          :values="trend.values"
          :labels="trend.labels"
          :format="fmt"
          :label-format="dateLong"
          :color="SERIES[0]"
          :min-height="72"
          aria-label="Динамика прибыли за 12 месяцев"
        />
      </div>
    </div>
  </CvWidget>
</template>

<style scoped>
.pf { display: flex; flex-direction: column; min-width: 0; height: 100%; }
.pf__value {
  font-family: var(--cv-display); font-size: 34px; font-weight: 500; letter-spacing: -0.04em; color: var(--cv-ink);
}
.pf__meta { display: flex; flex-direction: column; gap: 6px; margin: 12px 0 0; font-size: 12.5px; }
.pf__meta > div { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.pf__meta dt { color: var(--cv-mut); }
.pf__meta dd { margin: 0; }
.pf__meta :deep(.cv-delta-inline) { font-weight: 550; }

.pf__mix { margin-top: 28px; }
.pf__mix-head { display: flex; justify-content: space-between; gap: 10px; min-height: 18px; font-size: 12px; color: var(--cv-mut); }
.pf__mix-now b { font-weight: 550; color: var(--cv-ink); }
.pf__bar { display: flex; gap: 2px; height: 8px; margin-top: 10px; }
.pf__bar i {
  display: block; flex-basis: 0; min-width: 3px; height: 100%; border-radius: 2px;
  transform-origin: left center; transform: scaleX(0);
  transition: transform .9s var(--cv-ease) calc(var(--i) * 80ms + 150ms), opacity .2s;
}
.pf__bar i:first-child { border-top-left-radius: 4px; border-bottom-left-radius: 4px; }
.pf__bar i:last-child { border-top-right-radius: 4px; border-bottom-right-radius: 4px; }
.pf__bar.is-grown i { transform: none; }
.pf__bar.has-active i:not(.is-on) { opacity: .35; }

.pf__legend { list-style: none; margin: 14px 0 0; padding: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px 18px; }
.pf__legend li { display: flex; align-items: center; gap: 7px; min-width: 0; font-size: 12px; color: var(--cv-mut); transition: color .2s; }
.pf__legend li.is-on { color: var(--cv-ink); }
.pf__legend i { width: 8px; height: 8px; flex: none; border-radius: 2px; }
.pf__legend li.is-cost i { box-shadow: inset 0 0 0 1px var(--cv-line-3); }
.pf__legend span { min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pf__legend b { margin-left: auto; font-weight: 550; color: var(--cv-ink-2); white-space: nowrap; }
.pf__costs { margin-top: 14px; font-size: 11.5px; color: var(--cv-dim); }

.pf__trend { flex: 1; display: flex; flex-direction: column; gap: 10px; min-height: 110px; margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--cv-line); }
.pf__trend-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; font-size: 12px; color: var(--cv-mut); }
.pf__trend-head :deep(.cv-delta-inline) { font-size: 12.5px; font-weight: 550; }

.pf-swap-enter-active, .pf-swap-leave-active { transition: opacity .15s, transform .2s var(--cv-ease); }
.pf-swap-enter-from { opacity: 0; transform: translateY(3px); }
.pf-swap-leave-to { opacity: 0; transform: translateY(-3px); }
</style>
