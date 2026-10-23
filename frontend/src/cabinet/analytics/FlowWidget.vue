<script setup>
/**
 * Движение денег по месяцам: пополнения вверх от нуля, выводы вниз, засечка — чистый приток.
 */
import { computed, ref } from 'vue'
import { scaleBand, scaleLinear } from 'd3-scale'
import CvWidget from '../ui/CvWidget.vue'
import CvSegmented from '../ui/CvSegmented.vue'
import CvNumber from '../ui/CvNumber.vue'
import { useElementSize } from '../charts/useElementSize'
import { SERIES, NEUTRAL } from '../palette'
import { axisMoney, money, monthLong } from '../format'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  /** [{ month: 'YYYY-MM', inflow, outflow (≤ 0) }] */
  flow: { type: Array, default: () => [] },
})

const COLORS = { inflow: SERIES[0], outflow: NEUTRAL }
const PERIODS = [
  { value: 6, label: '6М' },
  { value: 12, label: '12М' },
  { value: 0, label: 'Всё' },
]
const period = ref(12)

const rows = computed(() => {
  const list = props.flow
    .filter((r) => /^\d{4}-\d{2}/.test(r?.month || ''))
    .map((r) => {
      const inflow = Math.max(0, Number(r.inflow) || 0)
      const outflow = -Math.abs(Number(r.outflow) || 0)
      return { month: String(r.month).slice(0, 7), inflow, outflow, net: inflow + outflow }
    })
    .sort((a, b) => a.month.localeCompare(b.month))
  return period.value ? list.slice(-period.value) : list
})

const totals = computed(() => {
  const t = { inflow: 0, outflow: 0 }
  for (const r of rows.value) { t.inflow += r.inflow; t.outflow += r.outflow }
  return { ...t, net: t.inflow + t.outflow, avg: rows.value.length ? (t.inflow + t.outflow) / rows.value.length : 0 }
})

// ── геометрия ──────────────────────────────────────────────────────────────
const PAD = { top: 10, right: 50, bottom: 26, left: 0 }
const H = 240
const box = ref(null)
const { width } = useElementSize(box)
const plotW = computed(() => Math.max(0, width.value - PAD.left - PAD.right))
const plotH = H - PAD.top - PAD.bottom

const x = computed(() => scaleBand().domain(rows.value.map((r) => r.month)).range([0, plotW.value]).paddingInner(0.32).paddingOuter(0.1))
const y = computed(() => {
  const hi = Math.max(1, ...rows.value.map((r) => r.inflow))
  const lo = Math.min(0, ...rows.value.map((r) => r.outflow))
  return scaleLinear().domain([lo * 1.08, hi * 1.08]).range([plotH, 0]).nice(4)
})
const yTicks = computed(() => y.value.ticks(4).map((v) => ({ v, y: y.value(v), label: axisMoney(v) })))

function rounded(x0, y0, w, h, r, up) {
  const rr = Math.min(r, w / 2, h)
  if (h <= 0) return ''
  return up
    ? `M${x0},${y0 + h}V${y0 + rr}Q${x0},${y0} ${x0 + rr},${y0}H${x0 + w - rr}Q${x0 + w},${y0} ${x0 + w},${y0 + rr}V${y0 + h}Z`
    : `M${x0},${y0}V${y0 + h - rr}Q${x0},${y0 + h} ${x0 + rr},${y0 + h}H${x0 + w - rr}Q${x0 + w},${y0 + h} ${x0 + w},${y0 + h - rr}V${y0}Z`
}

const MON = new Intl.DateTimeFormat('ru-RU', { month: 'short' })
const monLabel = (m) => {
  const [yy, mm] = m.split('-').map(Number)
  const s = MON.format(new Date(yy, mm - 1, 1)).replace('.', '')
  return mm === 1 ? `${s} ${String(yy).slice(2)}` : s
}

const bars = computed(() => {
  const bx = x.value
  const by = y.value
  const bw = bx.bandwidth()
  const z = by(0)
  const every = Math.max(1, Math.ceil(rows.value.length / Math.max(1, Math.floor(plotW.value / 46))))
  return rows.value.map((r, i) => {
    const x0 = bx(r.month)
    const top = by(r.inflow)
    const bottom = by(r.outflow)
    return {
      ...r,
      i,
      x: x0,
      w: bw,
      top,
      // зазор 2px между столбиками у нуля
      up: rounded(x0, top, bw, Math.max(0, z - top - (r.outflow ? 1 : 0)), 4, true),
      down: rounded(x0, z + 1, bw, Math.max(0, bottom - z - 1), 4, false),
      netY: by(r.net),
      label: i % every === 0 ? monLabel(r.month) : '',
    }
  })
})
const zeroY = computed(() => y.value(0))

const hover = ref(null)
const hovered = computed(() => (hover.value == null ? null : bars.value[hover.value] || null))
const tipStyle = computed(() => {
  const b = hovered.value
  if (!b) return null
  const cx = PAD.left + b.x + b.w / 2
  const flip = cx > width.value * 0.6
  return {
    left: `${cx}px`,
    top: `${PAD.top + Math.max(0, b.top - 8)}px`,
    transform: `translate(${flip ? 'calc(-100% - 10px)' : '10px'}, -100%)`,
  }
})

const fmt = (v) => money(v)
const fmtSigned = (v) => money(v, { sign: true })
</script>

<template>
  <CvWidget v-bind="$attrs" title="Движение денег">
    <template #actions>
      <CvSegmented v-model="period" :options="PERIODS" size="sm" aria-label="Период" />
    </template>

    <div class="fl">
      <dl class="fl__totals">
        <div>
          <dt><i :style="{ background: COLORS.inflow }" />Пополнено</dt>
          <dd><CvNumber :value="totals.inflow" :format="fmt" /></dd>
        </div>
        <div>
          <dt><i :style="{ background: COLORS.outflow }" />Выведено</dt>
          <dd class="is-dim"><CvNumber :value="totals.outflow" :format="fmt" /></dd>
        </div>
        <div>
          <dt><i class="fl__tick" />Чистый приток</dt>
          <dd><CvNumber :value="totals.net" :format="fmtSigned" /></dd>
        </div>
        <div>
          <dt>В среднем за месяц</dt>
          <dd class="is-dim"><CvNumber :value="totals.avg" :format="fmtSigned" /></dd>
        </div>
      </dl>

      <div ref="box" class="fl__chart" :style="{ height: `${H}px` }" @pointerleave="hover = null">
        <svg v-if="width && rows.length" :width="width" :height="H" class="fl__svg" role="img" aria-label="Пополнения и выводы по месяцам">
          <g :transform="`translate(${PAD.left},${PAD.top})`">
            <g class="fl__grid" aria-hidden="true">
              <line v-for="t in yTicks" :key="t.v" x1="0" :x2="plotW" :y1="t.y" :y2="t.y" :class="{ 'is-zero': t.v === 0 }" />
              <text v-for="t in yTicks" :key="`l${t.v}`" :x="plotW + 10" :y="t.y" dy="0.32em">{{ t.label }}</text>
            </g>

            <g
              v-for="b in bars"
              :key="`${period}-${b.month}`"
              class="fl__bar"
              :class="{ 'is-dim': hover != null && hover !== b.i }"
              :style="{ '--i': b.i }"
              @pointerenter="hover = b.i"
            >
              <rect class="fl__hit" :x="b.x - 3" y="0" :width="b.w + 6" :height="plotH" />
              <g class="fl__stack" :style="{ transformOrigin: `0 ${zeroY}px` }">
                <path v-if="b.up" :d="b.up" :fill="COLORS.inflow" />
                <path v-if="b.down" :d="b.down" :fill="COLORS.outflow" fill-opacity=".7" />
              </g>
              <line v-if="b.outflow" class="fl__net" :x1="b.x - 3" :x2="b.x + b.w + 3" :y1="b.netY" :y2="b.netY" />
              <text v-if="b.label" class="fl__x" :x="b.x + b.w / 2" :y="plotH + 18" text-anchor="middle">{{ b.label }}</text>
            </g>
          </g>
        </svg>

        <div v-if="hovered" class="cv-tip fl__tip" :style="tipStyle">
          <div class="cv-tip__date">{{ monthLong(`${hovered.month}-01`) }}</div>
          <div class="cv-tip__row"><span><i class="cv-tip__sw" :style="{ background: COLORS.inflow }" />Пополнено</span><b>{{ money(hovered.inflow) }}</b></div>
          <div class="cv-tip__row"><span><i class="cv-tip__sw" :style="{ background: COLORS.outflow }" />Выведено</span><b>{{ money(hovered.outflow) }}</b></div>
          <div class="cv-tip__sep" />
          <div class="cv-tip__row"><span>Чистый приток</span><b>{{ money(hovered.net, { sign: true }) }}</b></div>
        </div>

        <div v-if="!rows.length" class="fl__empty">Пополнений и выводов за этот период не было</div>
      </div>
    </div>
  </CvWidget>
</template>

<style scoped>
.fl { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.fl__totals { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px 24px; margin: 0; }
.fl__totals div { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.fl__totals dt { display: flex; align-items: center; gap: 7px; font-size: 12px; color: var(--cv-mut); white-space: nowrap; }
.fl__totals dt i { width: 8px; height: 8px; border-radius: 3px; flex: none; }
.fl__totals dt i.fl__tick { width: 10px; height: 2px; border-radius: 1px; background: var(--cv-ink); }
.fl__totals dd { margin: 0; font-family: var(--cv-display); font-size: 20px; font-weight: 600; letter-spacing: -0.02em; color: var(--cv-ink); white-space: nowrap; }
.fl__totals dd.is-dim { color: var(--cv-ink-2); }

.fl__chart { position: relative; }
.fl__svg { display: block; overflow: visible; }
.fl__grid line { stroke: rgba(255, 255, 255, .04); }
.fl__grid line.is-zero { stroke: rgba(255, 255, 255, .14); }
.fl__grid text, .fl__x { font-size: 11px; fill: var(--cv-dim); font-variant-numeric: tabular-nums; }
.fl__hit { fill: transparent; }
.fl__bar { transition: opacity .2s; }
.fl__bar.is-dim { opacity: .35; }
.fl__stack { animation: fl-grow .8s var(--cv-ease) backwards; animation-delay: calc(var(--i) * 26ms + 80ms); }
.fl__net { stroke: var(--cv-ink); stroke-width: 2; stroke-linecap: round; }
.fl__tip { min-width: 190px; transition: left .12s var(--cv-ease), top .12s var(--cv-ease); }
.fl__empty { position: absolute; inset: 0; display: grid; place-items: center; color: var(--cv-mut); font-size: 13px; }

@keyframes fl-grow { from { transform: scaleY(0); } }

@media (max-width: 768px) {
  .fl__totals { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (prefers-reduced-motion: reduce) {
  .fl__stack { animation: none; }
}
</style>
