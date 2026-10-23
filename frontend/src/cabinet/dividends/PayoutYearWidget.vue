<script setup>
/**
 * Выплаты за год по месяцам: столбик — стопка типов выплат, полученное сплошным цветом,
 * ожидаемое — приглушённым. Клик по месяцу открывает его в календаре.
 */
import { computed, ref } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { scaleBand, scaleLinear } from 'd3-scale'
import CvWidget from '../ui/CvWidget.vue'
import CvNumber from '../ui/CvNumber.vue'
import { useElementSize } from '../charts/useElementSize'
import { axisMoney, money } from '../format'
import { PAYOUT_KINDS, KIND_ORDER, MONTHS, MONTHS_SHORT } from './payoutTypes'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  /** события всех лет: { date, kind, received, rub } */
  events: { type: Array, default: () => [] },
  year: { type: Number, required: true },
  month: { type: Number, required: true },
})
const emit = defineEmits(['select', 'year'])

const now = new Date()
const currentMonthKey = now.getFullYear() * 12 + now.getMonth()

const months = computed(() => {
  const list = MONTHS_SHORT.map((label, m) => ({ m, label, total: 0, received: 0, parts: {} }))
  for (const e of props.events) {
    if (e.date.getFullYear() !== props.year || e.rub == null) continue
    const row = list[e.date.getMonth()]
    row.total += e.rub
    if (e.received) row.received += e.rub
    const key = `${e.kind}|${e.received ? 'r' : 'e'}`
    row.parts[key] = (row.parts[key] || 0) + e.rub
  }
  return list
})
const totals = computed(() => {
  const t = months.value.reduce((s, r) => ({ total: s.total + r.total, received: s.received + r.received }), { total: 0, received: 0 })
  return { ...t, expected: t.total - t.received, avg: t.total / 12 }
})
const usedKinds = computed(() => KIND_ORDER.filter((k) => props.events.some((e) => e.kind === k && e.date.getFullYear() === props.year)))
const hasYear = (y) => props.events.some((e) => e.date.getFullYear() === y)

// ── геометрия ──────────────────────────────────────────────────────────────
const PAD = { top: 10, right: 50, bottom: 26, left: 0 }
const H = 220
const box = ref(null)
const { width } = useElementSize(box)
const plotW = computed(() => Math.max(0, width.value - PAD.left - PAD.right))
const plotH = H - PAD.top - PAD.bottom

const x = computed(() => scaleBand().domain(MONTHS_SHORT).range([0, plotW.value]).paddingInner(0.3).paddingOuter(0.12))
const y = computed(() => scaleLinear().domain([0, Math.max(1, ...months.value.map((r) => r.total)) * 1.08]).range([plotH, 0]).nice(4))
const yTicks = computed(() => y.value.ticks(4).map((v) => ({ v, y: y.value(v), label: axisMoney(v) })))

const GAP = 2
const bars = computed(() => {
  const bx = x.value
  const by = y.value
  const bw = bx.bandwidth()
  return months.value.map((r) => {
    let base = plotH
    const segs = []
    // снизу полученное, сверху ожидаемое; внутри — типы в фиксированном порядке
    for (const status of ['r', 'e']) {
      for (const k of KIND_ORDER) {
        const v = r.parts[`${k}|${status}`]
        if (!v) continue
        const h = Math.max(2, plotH - by(v) - (segs.length ? GAP : 0))
        base -= h + (segs.length ? GAP : 0)
        segs.push({ key: `${k}${status}`, y: base, h, color: PAYOUT_KINDS[k].color, expected: status === 'e' })
      }
    }
    if (segs.length) segs[segs.length - 1].top = true
    const key = props.year * 12 + r.m
    return { ...r, x: bx(r.label), w: bw, top: base, segs, isNow: key === currentMonthKey, isPast: key < currentMonthKey }
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

/** путь со скруглёнными верхними углами */
const roundTop = (x0, y0, w, h, r = 4) => {
  const rr = Math.min(r, w / 2, h)
  return `M${x0},${y0 + h}V${y0 + rr}Q${x0},${y0} ${x0 + rr},${y0}H${x0 + w - rr}Q${x0 + w},${y0} ${x0 + w},${y0 + rr}V${y0 + h}Z`
}

const fmt = (v) => money(v)
</script>

<template>
  <CvWidget v-bind="$attrs" title="Выплаты по месяцам">
    <template #actions>
      <div class="py__year">
        <button type="button" class="cv-btn cv-btn--ghost cv-btn--sm cv-btn--icon" aria-label="Предыдущий год" @click="emit('year', year - 1)">
          <ChevronLeft :size="16" />
        </button>
        <span class="cv-num">{{ year }}</span>
        <button type="button" class="cv-btn cv-btn--ghost cv-btn--sm cv-btn--icon" aria-label="Следующий год" :disabled="!hasYear(year + 1) && year >= now.getFullYear() + 1" @click="emit('year', year + 1)">
          <ChevronRight :size="16" />
        </button>
      </div>
    </template>

    <div class="py">
      <dl class="py__totals">
        <div>
          <dt>За {{ year }} год</dt>
          <dd><CvNumber :value="totals.total" :format="fmt" /></dd>
        </div>
        <div>
          <dt><i class="py__sw" />Получено</dt>
          <dd class="is-dim"><CvNumber :value="totals.received" :format="fmt" /></dd>
        </div>
        <div>
          <dt><i class="py__sw is-exp" />Ожидается</dt>
          <dd class="is-dim"><CvNumber :value="totals.expected" :format="fmt" /></dd>
        </div>
        <div>
          <dt>В среднем за месяц</dt>
          <dd class="is-dim"><CvNumber :value="totals.avg" :format="fmt" /></dd>
        </div>
      </dl>

      <div ref="box" class="py__chart" :style="{ height: `${H}px` }" @pointerleave="hover = null">
        <svg v-if="width" :width="width" :height="H" class="py__svg" role="img" :aria-label="`Выплаты по месяцам ${year} года`">
          <g :transform="`translate(${PAD.left},${PAD.top})`">
            <g class="py__grid" aria-hidden="true">
              <line v-for="t in yTicks" :key="t.v" x1="0" :x2="plotW" :y1="t.y" :y2="t.y" :class="{ 'is-zero': t.v === 0 }" />
              <text v-for="t in yTicks" :key="`l${t.v}`" :x="plotW + 10" :y="t.y" dy="0.32em">{{ t.label }}</text>
            </g>

            <g
              v-for="(b, i) in bars"
              :key="`${year}-${b.m}`"
              class="py__bar"
              :class="{ 'is-dim': hover != null && hover !== i, 'is-sel': b.m === month }"
              :style="{ '--i': i }"
              role="button"
              :aria-label="`${MONTHS[b.m]}: ${money(b.total)}`"
              tabindex="0"
              @pointerenter="hover = i"
              @click="emit('select', b.m)"
              @keydown.enter.prevent="emit('select', b.m)"
            >
              <rect class="py__hit" :x="b.x - 4" y="0" :width="b.w + 8" :height="plotH + 22" rx="8" />
              <g class="py__stack" :style="{ transformOrigin: `0 ${plotH}px` }">
                <template v-for="s in b.segs" :key="s.key">
                  <path v-if="s.top" :d="roundTop(b.x, s.y, b.w, s.h)" :fill="s.color" :fill-opacity="s.expected ? 0.38 : 1" />
                  <rect v-else :x="b.x" :y="s.y" :width="b.w" :height="s.h" :fill="s.color" :fill-opacity="s.expected ? 0.38 : 1" />
                </template>
              </g>
              <text class="py__x" :class="{ 'is-now': b.isNow }" :x="b.x + b.w / 2" :y="plotH + 18" text-anchor="middle">{{ b.label }}</text>
            </g>
          </g>
        </svg>

        <div v-if="hovered" class="cv-tip py__tip" :style="tipStyle">
          <div class="cv-tip__date">{{ MONTHS[hovered.m] }} {{ year }}</div>
          <div v-for="p in hoveredKinds" :key="p.k" class="cv-tip__row">
            <span><i class="cv-tip__sw" :style="{ background: PAYOUT_KINDS[p.k].color }" />{{ PAYOUT_KINDS[p.k].label }}</span><b>{{ money(p.v) }}</b>
          </div>
          <div v-if="hoveredKinds.length" class="cv-tip__sep" />
          <div class="cv-tip__row"><span>Получено</span><b>{{ money(hovered.received) }}</b></div>
          <div class="cv-tip__row"><span>Ожидается</span><b>{{ money(hovered.total - hovered.received) }}</b></div>
        </div>

        <div v-if="!totals.total" class="py__empty">В {{ year }} году выплат нет</div>
      </div>

      <div class="py__foot">
        <div class="cv-legend">
          <span v-for="k in usedKinds" :key="k" class="cv-legend__item">
            <i class="cv-legend__sw" :style="{ background: PAYOUT_KINDS[k].color }" />{{ PAYOUT_KINDS[k].label }}
          </span>
          <span class="cv-legend__item"><i class="cv-legend__sw py__sw-exp" />ожидается — светлее</span>
        </div>
        <span class="py__hint">Нажмите на месяц, чтобы открыть его в календаре</span>
      </div>
    </div>
  </CvWidget>
</template>

<style scoped>
.py { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.py__year { display: flex; align-items: center; gap: 2px; }
.py__year span { min-width: 44px; text-align: center; font-size: 13px; font-weight: 600; color: var(--cv-ink); }
.py__year button:disabled { opacity: .35; pointer-events: none; }

.py__totals { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px 24px; margin: 0; }
.py__totals div { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.py__totals dt { display: flex; align-items: center; gap: 7px; font-size: 12px; color: var(--cv-mut); white-space: nowrap; }
.py__totals dd { margin: 0; font-family: var(--cv-display); font-size: 20px; font-weight: 600; letter-spacing: -0.02em; color: var(--cv-ink); white-space: nowrap; }
.py__totals dd.is-dim { color: var(--cv-ink-2); }
.py__sw { width: 8px; height: 8px; border-radius: 3px; background: var(--cv-accent); flex: none; }
.py__sw.is-exp, .py__sw-exp { background: rgba(115, 129, 255, .38) !important; }

.py__chart { position: relative; }
.py__svg { display: block; overflow: visible; }
.py__grid line { stroke: rgba(255, 255, 255, .04); }
.py__grid line.is-zero { stroke: rgba(255, 255, 255, .14); }
.py__grid text, .py__x { font-size: 11px; fill: var(--cv-dim); font-variant-numeric: tabular-nums; }
.py__x.is-now { fill: var(--cv-ink-2); }
.py__hit { fill: transparent; transition: fill .2s; }
.py__bar { cursor: pointer; outline: none; transition: opacity .2s; }
.py__bar.is-dim { opacity: .4; }
.py__bar.is-sel .py__hit { fill: rgba(115, 129, 255, .09); }
.py__bar.is-sel .py__x { fill: var(--cv-ink); font-weight: 600; }
.py__bar:focus-visible .py__hit { stroke: var(--cv-accent-line); }
.py__stack { animation: py-grow .8s var(--cv-ease) backwards; animation-delay: calc(var(--i) * 30ms + 80ms); }
.py__tip { min-width: 200px; transition: left .12s var(--cv-ease), top .12s var(--cv-ease); }
.py__empty { position: absolute; inset: 0 50px 26px 0; display: grid; place-items: center; color: var(--cv-mut); font-size: 13px; pointer-events: none; }

.py__foot { display: flex; align-items: center; justify-content: space-between; gap: 8px 16px; flex-wrap: wrap; }
.py__hint { font-size: 11.5px; color: var(--cv-dim); }

@keyframes py-grow { from { transform: scaleY(0); } }
@media (max-width: 768px) {
  .py__totals { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .py__hint { display: none; }
}
@media (prefers-reduced-motion: reduce) { .py__stack { animation: none; } }
</style>
