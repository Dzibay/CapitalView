<script setup>
/**
 * Активность по месяцам для отфильтрованных операций: группы с dir = 1 складываются вверх от нуля,
 * с dir = -1 — вниз; засечка — чистый итог месяца. Месяцы без операций остаются пустыми.
 */
import { computed, ref } from 'vue'
import { scaleBand, scaleLinear } from 'd3-scale'
import CvWidget from '../ui/CvWidget.vue'
import CvSegmented from '../ui/CvSegmented.vue'
import { useElementSize } from '../charts/useElementSize'
import { axisMoney, money, monthLong } from '../format'
import { OP_GROUPS } from './opKinds'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  title: { type: String, default: 'Активность по месяцам' },
  /** [{ ym: 'YYYY-MM', group, value (₽, > 0) }] */
  rows: { type: Array, default: () => [] },
  /** порядок групп — он же порядок в стопке и легенде */
  order: { type: Array, required: true },
  netLabel: { type: String, default: 'Итог' },
})

const PERIODS = [
  { value: 12, label: '12М' },
  { value: 36, label: '3Г' },
  { value: 0, label: 'Всё' },
]
const period = ref(12)

const groups = computed(() => props.order.map((key) => ({ key, ...OP_GROUPS[key] })))

const ymAdd = (ym, n) => {
  const [y, m] = ym.split('-').map(Number)
  const d = new Date(y, m - 1 + n, 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

const months = computed(() => {
  const by = new Map()
  for (const r of props.rows) {
    if (!r.ym || !(r.value > 0)) continue
    if (!by.has(r.ym)) by.set(r.ym, {})
    const m = by.get(r.ym)
    m[r.group] = (m[r.group] || 0) + r.value
  }
  if (!by.size) return []
  const keys = [...by.keys()].sort()
  let from = keys[0]
  const to = keys[keys.length - 1]
  if (period.value) {
    const lim = ymAdd(to, -(period.value - 1))
    if (lim > from) from = lim
  }
  const list = []
  for (let ym = from; ym <= to; ym = ymAdd(ym, 1)) {
    const v = by.get(ym) || {}
    let up = 0
    let down = 0
    for (const g of groups.value) {
      const x = v[g.key] || 0
      if (g.dir > 0) up += x
      else down += x
    }
    list.push({ ym, v, up, down, net: up - down })
  }
  return list
})

const totals = computed(() => {
  const t = Object.fromEntries(props.order.map((k) => [k, 0]))
  for (const m of months.value) for (const k of props.order) t[k] += m.v[k] || 0
  return t
})
/** «Прочее» показываем, только если там что-то есть */
const legendGroups = computed(() => groups.value.filter((g) => g.key !== 'other' || totals.value[g.key] > 0))
const totalNet = computed(() => months.value.reduce((s, m) => s + m.net, 0))
const hasDown = computed(() => groups.value.some((g) => g.dir < 0 && totals.value[g.key] > 0))

// ── геометрия ──────────────────────────────────────────────────────────────
const PAD = { top: 10, right: 50, bottom: 26, left: 0 }
const H = 220
const box = ref(null)
const { width } = useElementSize(box)
const plotW = computed(() => Math.max(0, width.value - PAD.left - PAD.right))
const plotH = H - PAD.top - PAD.bottom

const x = computed(() => scaleBand().domain(months.value.map((m) => m.ym)).range([0, plotW.value]).paddingInner(0.3).paddingOuter(0.1))
const y = computed(() => {
  const hi = Math.max(1, ...months.value.map((m) => m.up))
  const lo = -Math.max(0, ...months.value.map((m) => m.down))
  return scaleLinear().domain([lo * 1.06, hi * 1.06]).range([plotH, 0]).nice(4)
})
const yTicks = computed(() => y.value.ticks(4).map((v) => ({ v, y: y.value(v), label: axisMoney(v) })))

/** прямоугольник со скруглением только на внешнем конце */
function seg(x0, y0, w, h, r, end) {
  if (h <= 0.5) return ''
  const rr = Math.min(r, w / 2, h)
  if (end === 'top') return `M${x0},${y0 + h}V${y0 + rr}Q${x0},${y0} ${x0 + rr},${y0}H${x0 + w - rr}Q${x0 + w},${y0} ${x0 + w},${y0 + rr}V${y0 + h}Z`
  if (end === 'bottom') return `M${x0},${y0}V${y0 + h - rr}Q${x0},${y0 + h} ${x0 + rr},${y0 + h}H${x0 + w - rr}Q${x0 + w},${y0 + h} ${x0 + w},${y0 + h - rr}V${y0}Z`
  return `M${x0},${y0}h${w}v${h}h${-w}Z`
}

const MON = new Intl.DateTimeFormat('ru-RU', { month: 'short' })
const monLabel = (ym) => {
  const [yy, mm] = ym.split('-').map(Number)
  const s = MON.format(new Date(yy, mm - 1, 1)).replace('.', '')
  return mm === 1 || ym === months.value[0]?.ym ? `${s} ${String(yy).slice(2)}` : s
}

const GAP = 2
const bars = computed(() => {
  const bx = x.value
  const by = y.value
  const bw = bx.bandwidth()
  const z = by(0)
  const every = Math.max(1, Math.ceil(months.value.length / Math.max(1, Math.floor(plotW.value / 46))))
  return months.value.map((m, i) => {
    const x0 = bx(m.ym)
    const segs = []
    for (const dir of [1, -1]) {
      const list = groups.value.filter((g) => g.dir === dir && m.v[g.key] > 0)
      let acc = 0
      list.forEach((g, j) => {
        const v = m.v[g.key]
        const a = by(dir * acc)
        const b = by(dir * (acc + v))
        acc += v
        const last = j === list.length - 1
        // зазор 2px у нуля и между сегментами
        const inner = j === 0 ? 1 : GAP / 2
        const outer = last ? 0 : GAP / 2
        const top = dir > 0 ? b + outer : a + inner
        const h = Math.abs(b - a) - inner - outer
        segs.push({ key: g.key, color: g.color, d: seg(x0, top, bw, h, 4, last ? (dir > 0 ? 'top' : 'bottom') : null) })
      })
    }
    return {
      ...m,
      i,
      x: x0,
      w: bw,
      top: by(m.up),
      segs,
      netY: by(m.net),
      label: i % every === 0 ? monLabel(m.ym) : '',
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
</script>

<template>
  <CvWidget v-bind="$attrs" :title="title">
    <template #actions>
      <CvSegmented v-model="period" :options="PERIODS" size="sm" aria-label="Период графика" />
    </template>

    <div class="oa">
      <dl class="oa__totals">
        <div v-for="g in legendGroups" :key="g.key" :class="{ 'is-zero': !totals[g.key] }">
          <dt><i :style="{ background: g.color }" />{{ g.label }}</dt>
          <dd class="cv-num">{{ money(totals[g.key]) }}</dd>
        </div>
        <div v-if="hasDown">
          <dt><i class="oa__tick" />{{ netLabel }}</dt>
          <dd class="cv-num">{{ money(totalNet, { sign: true }) }}</dd>
        </div>
      </dl>

      <div ref="box" class="oa__chart" :style="{ height: `${H}px` }" @pointerleave="hover = null">
        <svg v-if="width && months.length" :width="width" :height="H" class="oa__svg" role="img" :aria-label="title">
          <g :transform="`translate(${PAD.left},${PAD.top})`">
            <g class="oa__grid" aria-hidden="true">
              <line v-for="t in yTicks" :key="t.v" x1="0" :x2="plotW" :y1="t.y" :y2="t.y" :class="{ 'is-zero': t.v === 0 }" />
              <text v-for="t in yTicks" :key="`l${t.v}`" :x="plotW + 10" :y="t.y" dy="0.32em">{{ t.label }}</text>
            </g>

            <g
              v-for="b in bars"
              :key="`${period}-${b.ym}`"
              class="oa__bar"
              :class="{ 'is-dim': hover != null && hover !== b.i }"
              :style="{ '--i': b.i }"
              @pointerenter="hover = b.i"
            >
              <rect class="oa__hit" :x="b.x - 3" y="0" :width="b.w + 6" :height="plotH" />
              <g class="oa__stack" :style="{ transformOrigin: `0 ${zeroY}px` }">
                <path v-for="s in b.segs" :key="s.key" :d="s.d" :fill="s.color" />
              </g>
              <line v-if="hasDown && b.down && b.up" class="oa__net" :x1="b.x - 3" :x2="b.x + b.w + 3" :y1="b.netY" :y2="b.netY" />
              <text v-if="b.label" class="oa__x" :x="b.x + b.w / 2" :y="plotH + 18" text-anchor="middle">{{ b.label }}</text>
            </g>
          </g>
        </svg>

        <div v-if="hovered" class="cv-tip oa__tip" :style="tipStyle">
          <div class="cv-tip__date">{{ monthLong(`${hovered.ym}-01`) }}</div>
          <template v-for="g in groups" :key="g.key">
            <div v-if="hovered.v[g.key]" class="cv-tip__row">
              <span><i class="cv-tip__sw" :style="{ background: g.color }" />{{ g.label }}</span>
              <b>{{ money(hovered.v[g.key]) }}</b>
            </div>
          </template>
          <template v-if="hasDown">
            <div class="cv-tip__sep" />
            <div class="cv-tip__row"><span>{{ netLabel }}</span><b>{{ money(hovered.net, { sign: true }) }}</b></div>
          </template>
        </div>

        <div v-if="!months.length" class="oa__empty">За выбранный период операций нет</div>
      </div>
    </div>
  </CvWidget>
</template>

<style scoped>
.oa { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.oa__totals { display: flex; flex-wrap: wrap; gap: 12px 32px; margin: 0; }
.oa__totals div { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.oa__totals div.is-zero { opacity: .5; }
.oa__totals dt { display: flex; align-items: center; gap: 7px; font-size: 12px; color: var(--cv-mut); white-space: nowrap; }
.oa__totals dt i { width: 8px; height: 8px; border-radius: 3px; flex: none; }
.oa__totals dt i.oa__tick { width: 10px; height: 2px; border-radius: 1px; background: var(--cv-ink); }
.oa__totals dd { margin: 0; font-family: var(--cv-display); font-size: 18px; font-weight: 600; letter-spacing: -0.02em; color: var(--cv-ink); white-space: nowrap; }

.oa__chart { position: relative; }
.oa__svg { display: block; overflow: visible; }
.oa__grid line { stroke: rgba(255, 255, 255, .04); }
.oa__grid line.is-zero { stroke: rgba(255, 255, 255, .14); }
.oa__grid text, .oa__x { font-size: 11px; fill: var(--cv-dim); font-variant-numeric: tabular-nums; }
.oa__hit { fill: transparent; }
.oa__bar { transition: opacity .2s; }
.oa__bar.is-dim { opacity: .35; }
.oa__stack { animation: oa-grow .8s var(--cv-ease) backwards; animation-delay: calc(var(--i) * 22ms + 80ms); }
.oa__net { stroke: var(--cv-ink); stroke-width: 2; stroke-linecap: round; pointer-events: none; }
.oa__tip { min-width: 200px; transition: left .12s var(--cv-ease), top .12s var(--cv-ease); }
.oa__empty { position: absolute; inset: 0; display: grid; place-items: center; color: var(--cv-mut); font-size: 13px; }

@keyframes oa-grow { from { transform: scaleY(0); } }

@media (max-width: 768px) {
  .oa__totals { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .oa__totals dd { font-size: 16px; }
}
@media (prefers-reduced-motion: reduce) { .oa__stack { animation: none; } }
</style>
