<script setup>
/**
 * Главный виджет: стоимость портфеля «живым» числом и интерактивный график.
 * Наведение — число и изменение показывают значение в точке; выделение — изменение за выбранный отрезок.
 * Изменение считается по прибыли (без учёта пополнений), процент — к капиталу на начало отрезка
 * плюс половине чистых пополнений (упрощённый метод Дитца).
 */
import { computed, reactive, ref, watch } from 'vue'
import { bisectLeft, bisectRight } from 'd3-array'
import { Info, MousePointerClick } from 'lucide-vue-next'
import CvWidget from '../ui/CvWidget.vue'
import CvNumber from '../ui/CvNumber.vue'
import CvDelta from '../ui/CvDelta.vue'
import CvSegmented from '../ui/CvSegmented.vue'
import CapitalChart from '../charts/CapitalChart.vue'
import { useElementSize } from '../charts/useElementSize'
import { money, dateLong, dateShort, pct, trendClass } from '../format'
import { SERIES, NEUTRAL } from '../palette'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  /** expandPortfolioHistoryForCharts(...) */
  history: { type: Object, required: true },
  totalAmount: { type: Number, default: 0 },
  investedAmount: { type: Number, default: 0 },
  balance: { type: Number, default: 0 },
  inflationRate: { type: Number, default: 7.5 },
})

const DAY = 86400000
const STORE_KEY = 'cv:capital-chart:v1'
const COLORS = { value: SERIES[0], invested: NEUTRAL, inflation: SERIES[1] }

const PERIODS = [
  { value: '1m', label: '1М' },
  { value: '3m', label: '3М' },
  { value: '6m', label: '6М' },
  { value: 'ytd', label: 'YTD' },
  { value: '1y', label: '1Г' },
  { value: 'all', label: 'Всё' },
]
const PERIOD_TEXT = {
  '1m': 'за месяц', '3m': 'за 3 месяца', '6m': 'за полгода', ytd: 'с начала года', '1y': 'за год', all: 'за всё время',
}

function loadPrefs() {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY) || '{}')
  } catch {
    return {}
  }
}
const prefs = loadPrefs()
const period = ref(PERIOD_TEXT[prefs.period] ? prefs.period : '1y')
const compare = reactive({ invested: prefs.invested ?? true, inflation: prefs.inflation ?? false })
watch([period, compare], () => {
  localStorage.setItem(STORE_KEY, JSON.stringify({ period: period.value, ...compare }))
}, { deep: true })

// ── данные ─────────────────────────────────────────────────────────────────
const dates = computed(() => (props.history.labels || []).map((l) => Date.parse(l)))
const value = computed(() => props.history.data_value || [])
const invested = computed(() => props.history.data_invested || [])
const pnl = computed(() => {
  const p = props.history.data_pnl
  if (p?.length === value.value.length) return p
  return value.value.map((v, i) => v - (invested.value[i] || 0))
})
const hasData = computed(() => dates.value.length > 1)

/** Вложенные деньги, проиндексированные на инфляцию с даты каждого пополнения. */
const inflation = computed(() => {
  const d = dates.value
  const inv = invested.value
  const out = new Array(d.length)
  if (!d.length) return out
  const k = Math.log(1 + (props.inflationRate || 0) / 100) / (365 * DAY)
  out[0] = inv[0] || 0
  for (let i = 1; i < d.length; i++) {
    out[i] = out[i - 1] * Math.exp(k * (d[i] - d[i - 1])) + ((inv[i] || 0) - (inv[i - 1] || 0))
  }
  return out
})

const inflationLabel = computed(() => `Инфляция ${pct(props.inflationRate, { sign: false })}`)

const series = computed(() => {
  const list = [{ key: 'value', label: 'Стоимость', values: value.value, color: COLORS.value, kind: 'area' }]
  if (compare.invested) list.push({ key: 'invested', label: 'Вложено', values: invested.value, color: COLORS.invested, kind: 'dash' })
  if (compare.inflation) list.push({ key: 'inflation', label: inflationLabel.value, values: inflation.value, color: COLORS.inflation, kind: 'dot' })
  return list
})

// ── период и зум ────────────────────────────────────────────────────────────
const zoom = ref(null)
const selection = ref(null)
const hoverIdx = ref(null)

const range = computed(() => {
  const d = dates.value
  if (!d.length) return [0, 1]
  if (zoom.value) return zoom.value
  const first = d[0]
  const last = d[d.length - 1]
  const end = new Date(last)
  const back = (months) => Date.UTC(end.getUTCFullYear(), end.getUTCMonth() - months, end.getUTCDate())
  const t0 = {
    '1m': back(1), '3m': back(3), '6m': back(6), '1y': back(12),
    ytd: Date.UTC(end.getUTCFullYear(), 0, 1), all: first,
  }[period.value] ?? first
  const start = Math.max(first, t0)
  return [Math.min(start, last - DAY), last]
})

const segValue = computed({
  get: () => (zoom.value ? '' : period.value),
  set: (v) => {
    zoom.value = null
    period.value = v
  },
})

watch([period, zoom, () => props.history], () => {
  selection.value = null
})

const startIdx = computed(() => Math.min(dates.value.length - 1, bisectLeft(dates.value, range.value[0])))
const endIdx = computed(() => Math.max(startIdx.value, bisectRight(dates.value, range.value[1]) - 1))

function change(a, b) {
  const p = pnl.value
  const dp = (p[b] || 0) - (p[a] || 0)
  const base = (value.value[a] || 0) + 0.5 * ((invested.value[b] || 0) - (invested.value[a] || 0))
  return { abs: dp, pct: base > 0 ? (dp / base) * 100 : 0 }
}

function rangeText(a, b) {
  const da = new Date(a)
  const db = new Date(b)
  const y = (d) => d.getFullYear()
  return y(da) === y(db)
    ? `${dateShort(da)} — ${dateShort(db)} ${y(db)}`
    : `${dateShort(da)} ${y(da)} — ${dateShort(db)} ${y(db)}`
}

const state = computed(() => {
  const d = dates.value
  if (!hasData.value) return { mode: 'now', label: 'Стоимость портфеля', value: props.totalAmount, abs: 0, pct: 0, suffix: '' }
  if (selection.value) {
    const { i0, i1 } = selection.value
    return { mode: 'sel', label: 'Выделенный период', value: value.value[i1], ...change(i0, i1), suffix: rangeText(d[i0], d[i1]) }
  }
  if (hoverIdx.value != null) {
    const i = hoverIdx.value
    return { mode: 'hover', label: dateLong(d[i]), value: value.value[i], ...change(startIdx.value, i), suffix: `с ${dateShort(d[startIdx.value])}` }
  }
  return {
    mode: 'now',
    label: 'Стоимость портфеля',
    value: props.totalAmount,
    ...change(startIdx.value, endIdx.value),
    suffix: zoom.value ? rangeText(range.value[0], range.value[1]) : PERIOD_TEXT[period.value],
  }
})

const extremes = computed(() => {
  const v = value.value
  let hi = -Infinity
  let lo = Infinity
  let hiI = startIdx.value
  let loI = startIdx.value
  for (let i = startIdx.value; i <= endIdx.value; i++) {
    if (v[i] > hi) { hi = v[i]; hiI = i }
    if (v[i] < lo) { lo = v[i]; loI = i }
  }
  return { hi, lo, hiI, loI }
})

const stats = computed(() => {
  const d = dates.value
  const e = extremes.value
  return [
    { key: 'inv', label: 'Вложено', value: money(props.investedAmount) },
    { key: 'bal', label: 'Свободные средства', value: money(props.balance) },
    { key: 'hi', label: 'Максимум', value: hasData.value ? money(e.hi) : '—', note: hasData.value ? dateShort(d[e.hiI]) : '' },
    { key: 'lo', label: 'Минимум', value: hasData.value ? money(e.lo) : '—', note: hasData.value ? dateShort(d[e.loI]) : '' },
  ]
})

// высота графика под ширину виджета
const bodyEl = ref(null)
const { width: bodyW } = useElementSize(bodyEl)
const chartH = computed(() => (bodyW.value && bodyW.value < 560 ? 230 : 300))

const fmtValue = (v) => money(v, { digits: 2 })
</script>

<template>
  <CvWidget v-bind="$attrs" glow class="cap">
    <div ref="bodyEl" class="cap__body">
      <div class="cap__top">
        <div class="cap__headline">
          <div class="cap__label cv-eyebrow">
            <Transition name="cap-swap" mode="out-in">
              <span :key="state.mode">{{ state.label }}</span>
            </Transition>
          </div>
          <div class="cap__value">
            <CvNumber
              :value="state.value"
              :format="fmtValue"
              :duration="state.mode === 'now' ? 1100 : 300"
              :stagger="state.mode === 'now' ? 28 : 3"
              dim
            />
          </div>
          <div class="cap__change">
            <CvDelta :value="state.abs" kind="money" />
            <CvDelta :value="state.pct" kind="pct" :pill="false" />
            <span class="cap__suffix">{{ state.suffix }}</span>
            <span class="cap__hint" title="Изменение прибыли — пополнения и выводы не учитываются">
              <Info :size="13" />
            </span>
          </div>
        </div>
        <div class="cap__controls">
          <CvSegmented v-model="segValue" :options="PERIODS" size="sm" aria-label="Период графика" />
          <button v-if="zoom" type="button" class="cv-btn cv-btn--sm cv-btn--ghost cap__reset" @click="zoom = null">
            Сбросить зум
          </button>
        </div>
      </div>

      <div class="cap__legend">
        <span class="cap__key">
          <i class="cap__sw" :style="{ background: COLORS.value }" />Стоимость
        </span>
        <button
          type="button"
          class="cap__toggle"
          :class="{ 'is-on': compare.invested }"
          :aria-pressed="compare.invested"
          @click="compare.invested = !compare.invested"
        >
          <i class="cap__sw cap__sw--dash" :style="{ color: COLORS.invested }" />Вложено
        </button>
        <button
          type="button"
          class="cap__toggle"
          :class="{ 'is-on': compare.inflation }"
          :aria-pressed="compare.inflation"
          title="Вложенные деньги, растущие вместе с инфляцией: линия, которую капитал должен обгонять"
          @click="compare.inflation = !compare.inflation"
        >
          <i class="cap__sw cap__sw--dot" :style="{ color: COLORS.inflation }" />{{ inflationLabel }}
        </button>
        <span class="cap__tip"><MousePointerClick :size="13" /> Потяните по графику, чтобы сравнить период</span>
      </div>

      <div v-if="hasData" class="cap__chart">
        <CapitalChart
          v-model:selection="selection"
          :dates="dates"
          :series="series"
          :range="range"
          :height="chartH"
          aria-label="График стоимости портфеля. Стрелки влево и вправо перемещают курсор."
          @hover="hoverIdx = $event"
          @zoom="zoom = $event"
        >
          <template #tooltip="{ index }">
            <div class="cv-tip__date">{{ dateLong(dates[index]) }}</div>
            <div class="cv-tip__row">
              <span><i class="cv-tip__sw" :style="{ background: COLORS.value }" />Стоимость</span>
              <b>{{ money(value[index]) }}</b>
            </div>
            <div v-if="compare.invested" class="cv-tip__row">
              <span><i class="cv-tip__sw" :style="{ background: COLORS.invested }" />Вложено</span>
              <b>{{ money(invested[index]) }}</b>
            </div>
            <div v-if="compare.inflation" class="cv-tip__row">
              <span><i class="cv-tip__sw" :style="{ background: COLORS.inflation }" />С инфляцией</span>
              <b>{{ money(inflation[index]) }}</b>
            </div>
            <div class="cv-tip__sep" />
            <div class="cv-tip__row">
              <span>Прибыль</span>
              <b :class="trendClass(pnl[index]) === 'is-up' ? 'cv-up' : trendClass(pnl[index]) === 'is-down' ? 'cv-down' : ''">
                {{ money(pnl[index], { sign: true }) }}
              </b>
            </div>
          </template>
        </CapitalChart>
      </div>
      <div v-else class="cap__empty" :style="{ height: `${chartH}px` }">
        <svg viewBox="0 0 400 120" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0 96 C 60 90, 90 70, 140 74 S 230 40, 280 48 S 360 20, 400 18" />
        </svg>
        <p>График появится, когда в портфеле накопится история — хотя бы пара дней.</p>
      </div>

      <dl class="cap__stats">
        <div v-for="s in stats" :key="s.key" class="cap__stat">
          <dt>{{ s.label }}<small v-if="s.note"> · {{ s.note }}</small></dt>
          <dd class="cv-num">{{ s.value }}</dd>
        </div>
      </dl>
    </div>
  </CvWidget>
</template>

<style scoped>
.cap__body { display: flex; flex-direction: column; gap: 14px; min-width: 0; container-type: inline-size; }

.cap__top { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.cap__headline { min-width: 0; }
.cap__label { height: 18px; padding-top: 8px; box-sizing: content-box; }
.cap__value {
  margin-top: 14px;
  font-family: var(--cv-display);
  font-size: clamp(34px, 4.2vw, 50px);
  font-weight: 500;
  letter-spacing: -0.04em;
  color: var(--cv-ink);
}
.cap__change { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 10px; font-size: 13px; }
.cap__suffix { color: var(--cv-mut); }
.cap__hint { display: inline-flex; color: var(--cv-dim); cursor: help; }
.cap__controls { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.cap__reset { color: var(--cv-accent-ink); }

.cap__legend { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; font-size: 12.5px; color: var(--cv-mut); }
.cap__key, .cap__toggle {
  display: inline-flex; align-items: center; gap: 8px; height: 28px; padding: 0 10px;
  border-radius: 99px; font-size: 12.5px; font-weight: 500;
}
.cap__key { color: var(--cv-ink-2); padding-left: 2px; }
.cap__toggle {
  border: 0; cursor: pointer; color: var(--cv-dim);
  background: transparent; box-shadow: inset 0 0 0 1px var(--cv-line);
  transition: color .2s, background .2s, box-shadow .2s;
}
.cap__toggle:hover { color: var(--cv-ink-2); box-shadow: inset 0 0 0 1px var(--cv-line-3); }
.cap__toggle.is-on { color: var(--cv-ink); background: rgba(255, 255, 255, .05); box-shadow: inset 0 0 0 1px var(--cv-line-2); }
.cap__toggle:not(.is-on) .cap__sw { opacity: .45; }
.cap__sw { width: 14px; height: 3px; border-radius: 2px; flex: none; }
.cap__sw--dash { height: 0; border-top: 2px dashed currentColor; border-radius: 0; }
.cap__sw--dot { height: 0; border-top: 2px dotted currentColor; border-radius: 0; }
.cap__tip { display: inline-flex; align-items: center; gap: 6px; margin-left: auto; font-size: 12px; color: var(--cv-dim); }

.cap__chart { margin: 0 -6px 0 -2px; }

.cap__empty {
  position: relative; display: grid; place-items: center; border-radius: 14px;
  background: rgba(255, 255, 255, .02); box-shadow: inset 0 0 0 1px var(--cv-line);
  overflow: hidden;
}
.cap__empty svg { position: absolute; inset: 20% 0 10%; width: 100%; height: 70%; }
.cap__empty path { fill: none; stroke: rgba(115, 129, 255, .25); stroke-width: 2; stroke-dasharray: 6 6; }
.cap__empty p { position: relative; max-width: 300px; text-align: center; color: var(--cv-mut); font-size: 13px; }

.cap__stats {
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 2px 0 0;
  border-top: 1px solid var(--cv-line);
}
.cap__stat { padding: 14px 16px 0; min-width: 0; }
.cap__stat + .cap__stat { border-left: 1px solid var(--cv-line); }
.cap__stat:first-child { padding-left: 0; }
.cap__stat dt { font-size: 12px; color: var(--cv-mut); margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cap__stat dd { margin: 0; font-size: 15px; font-weight: 550; color: var(--cv-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cap__stat small { font-size: inherit; color: var(--cv-dim); }

.cap-swap-enter-active, .cap-swap-leave-active { transition: opacity .18s var(--cv-ease), transform .22s var(--cv-ease); }
.cap-swap-enter-from { opacity: 0; transform: translateY(4px); }
.cap-swap-leave-to { opacity: 0; transform: translateY(-4px); }

@container (max-width: 760px) {
  .cap__tip { display: none; }
}
@container (max-width: 620px) {
  .cap__stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .cap__stat:nth-child(3) { border-left: 0; padding-left: 0; }
  .cap__stat:nth-child(n + 3) { margin-top: 2px; }
  .cap__controls { width: 100%; justify-content: flex-start; }
}
@media (hover: none) {
  .cap__tip { display: none; }
}
</style>
