<script setup>
/**
 * Выплаты на одну бумагу по годам: столбик — стопка типов выплат,
 * объявленные и прошедшие сплошным цветом, прогноз — приглушённым.
 */
import { computed, ref } from 'vue'
import { scaleBand, scaleLinear } from 'd3-scale'
import { useElementSize } from '../charts/useElementSize'
import { PAYOUT_KINDS, KIND_ORDER } from '../dividends/payoutTypes'

const props = defineProps({
  /** [{ date: Date, kind, value, forecast }] */
  rows: { type: Array, default: () => [] },
  /** формат суммы в валюте бумаги */
  format: { type: Function, required: true },
})

const years = computed(() => {
  const map = new Map()
  for (const r of props.rows) {
    const y = r.date.getFullYear()
    if (!map.has(y)) map.set(y, { year: y, total: 0, forecast: 0, count: 0, parts: {} })
    const row = map.get(y)
    row.total += r.value
    row.count += 1
    if (r.forecast) row.forecast += r.value
    const key = `${r.kind}|${r.forecast ? 'e' : 'r'}`
    row.parts[key] = (row.parts[key] || 0) + r.value
  }
  const list = [...map.values()].sort((a, b) => a.year - b.year)
  // не больше 12 последних лет — иначе столбики становятся нитками
  return list.slice(-12)
})
const usedKinds = computed(() => KIND_ORDER.filter((k) => props.rows.some((r) => r.kind === k)))
const hasForecast = computed(() => props.rows.some((r) => r.forecast))

const PAD = { top: 10, right: 64, bottom: 26, left: 0 }
const H = 220
const box = ref(null)
const { width } = useElementSize(box)
const plotW = computed(() => Math.max(0, width.value - PAD.left - PAD.right))
const plotH = H - PAD.top - PAD.bottom

const x = computed(() => scaleBand().domain(years.value.map((r) => r.year)).range([0, plotW.value]).paddingInner(0.32).paddingOuter(0.14))
const y = computed(() => scaleLinear().domain([0, Math.max(1e-9, ...years.value.map((r) => r.total)) * 1.08]).range([plotH, 0]).nice(4))
const yTicks = computed(() => y.value.ticks(4).map((v) => ({ v, y: y.value(v), label: props.format(v) })))

const GAP = 2
const bars = computed(() => {
  const bx = x.value
  const by = y.value
  const bw = Math.min(56, bx.bandwidth())
  return years.value.map((r) => {
    let base = plotH
    const segs = []
    for (const status of ['r', 'e']) {
      for (const k of KIND_ORDER) {
        const v = r.parts[`${k}|${status}`]
        if (!v) continue
        const gap = segs.length ? GAP : 0
        const h = Math.max(2, plotH - by(v) - gap)
        base -= h + gap
        segs.push({ key: `${k}${status}`, y: base, h, color: PAYOUT_KINDS[k].color, expected: status === 'e' })
      }
    }
    if (segs.length) segs[segs.length - 1].top = true
    return { ...r, x: bx(r.year) + (bx.bandwidth() - bw) / 2, w: bw, top: base, segs }
  })
})

const hover = ref(null)
const hovered = computed(() => (hover.value == null ? null : bars.value[hover.value]))
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
const hoveredKinds = computed(() => {
  const b = hovered.value
  if (!b) return []
  return KIND_ORDER.map((k) => ({ k, v: (b.parts[`${k}|r`] || 0) + (b.parts[`${k}|e`] || 0) })).filter((p) => p.v > 0)
})

const roundTop = (x0, y0, w, h, r = 4) => {
  const rr = Math.min(r, w / 2, h)
  return `M${x0},${y0 + h}V${y0 + rr}Q${x0},${y0} ${x0 + rr},${y0}H${x0 + w - rr}Q${x0 + w},${y0} ${x0 + w},${y0 + rr}V${y0 + h}Z`
}
</script>

<template>
  <div class="pyc">
    <div ref="box" class="pyc__chart" :style="{ height: `${H}px` }" @pointerleave="hover = null">
      <svg v-if="width" :width="width" :height="H" class="pyc__svg" role="img" aria-label="Выплаты на одну бумагу по годам">
        <g :transform="`translate(${PAD.left},${PAD.top})`">
          <g class="pyc__grid" aria-hidden="true">
            <line v-for="t in yTicks" :key="t.v" x1="0" :x2="plotW" :y1="t.y" :y2="t.y" :class="{ 'is-zero': t.v === 0 }" />
            <text v-for="t in yTicks" :key="`l${t.v}`" :x="plotW + 10" :y="t.y" dy="0.32em">{{ t.label }}</text>
          </g>
          <g
            v-for="(b, i) in bars"
            :key="b.year"
            class="pyc__bar"
            :class="{ 'is-dim': hover != null && hover !== i }"
            :style="{ '--i': i }"
            tabindex="0"
            :aria-label="`${b.year}: ${format(b.total)}`"
            @pointerenter="hover = i"
            @focus="hover = i"
            @blur="hover = null"
          >
            <rect class="pyc__hit" :x="b.x - 6" y="0" :width="b.w + 12" :height="plotH + 22" rx="8" />
            <g class="pyc__stack" :style="{ transformOrigin: `0 ${plotH}px` }">
              <template v-for="s in b.segs" :key="s.key">
                <path v-if="s.top" :d="roundTop(b.x, s.y, b.w, s.h)" :fill="s.color" :fill-opacity="s.expected ? 0.38 : 1" />
                <rect v-else :x="b.x" :y="s.y" :width="b.w" :height="s.h" :fill="s.color" :fill-opacity="s.expected ? 0.38 : 1" />
              </template>
            </g>
            <text class="pyc__x" :x="b.x + b.w / 2" :y="plotH + 18" text-anchor="middle">{{ b.year }}</text>
          </g>
        </g>
      </svg>

      <div v-if="hovered" class="cv-tip pyc__tip" :style="tipStyle">
        <div class="cv-tip__date">{{ hovered.year }} · выплат: {{ hovered.count }}</div>
        <div v-for="p in hoveredKinds" :key="p.k" class="cv-tip__row">
          <span><i class="cv-tip__sw" :style="{ background: PAYOUT_KINDS[p.k].color }" />{{ PAYOUT_KINDS[p.k].label }}</span><b>{{ format(p.v) }}</b>
        </div>
        <template v-if="hovered.forecast">
          <div class="cv-tip__sep" />
          <div class="cv-tip__row"><span>Из них прогноз</span><b>{{ format(hovered.forecast) }}</b></div>
        </template>
      </div>
    </div>

    <div class="cv-legend">
      <span v-for="k in usedKinds" :key="k" class="cv-legend__item">
        <i class="cv-legend__sw" :style="{ background: PAYOUT_KINDS[k].color }" />{{ PAYOUT_KINDS[k].label }}
      </span>
      <span v-if="hasForecast" class="cv-legend__item"><i class="cv-legend__sw pyc__sw-exp" />прогноз — светлее</span>
    </div>
  </div>
</template>

<style scoped>
.pyc { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.pyc__chart { position: relative; }
.pyc__svg { display: block; overflow: visible; }
.pyc__grid line { stroke: rgba(255, 255, 255, .04); }
.pyc__grid line.is-zero { stroke: rgba(255, 255, 255, .14); }
.pyc__grid text, .pyc__x { font-size: 11px; fill: var(--cv-dim); font-variant-numeric: tabular-nums; }
.pyc__hit { fill: transparent; }
.pyc__bar { outline: none; transition: opacity .2s; }
.pyc__bar.is-dim { opacity: .4; }
.pyc__bar:focus-visible .pyc__hit { stroke: var(--cv-accent-line); }
.pyc__stack { animation: pyc-grow .8s var(--cv-ease) backwards; animation-delay: calc(var(--i) * 40ms + 80ms); }
.pyc__tip { min-width: 190px; transition: left .12s var(--cv-ease), top .12s var(--cv-ease); }
.pyc__sw-exp { background: rgba(115, 129, 255, .38); }
@keyframes pyc-grow { from { transform: scaleY(0); } }
@media (prefers-reduced-motion: reduce) { .pyc__stack { animation: none; } }
</style>
