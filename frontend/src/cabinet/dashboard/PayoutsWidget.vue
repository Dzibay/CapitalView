<script setup>
/**
 * Выплаты по месяцам: полученные (сплошные) и прогноз (штриховка), стек дивиденды/купоны/амортизация.
 * Клик по прошедшему месяцу открывает операции за этот месяц.
 */
import { computed, ref, useId } from 'vue'
import { useRouter } from 'vue-router'
import { scaleBand, scaleLinear } from 'd3-scale'
import { HandCoins } from 'lucide-vue-next'
import CvWidget from '../ui/CvWidget.vue'
import CvSegmented from '../ui/CvSegmented.vue'
import CvNumber from '../ui/CvNumber.vue'
import { useElementSize } from '../charts/useElementSize'
import { PAYOUT_COLORS } from '../palette'
import { axisMoney, money, monthLong, plural } from '../format'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  past: { type: Array, default: () => [] },
  future: { type: Array, default: () => [] },
})
const router = useRouter()
const uid = useId()

const KEYS = [
  { key: 'dividends', label: 'Дивиденды', op: 'Дивиденды' },
  { key: 'coupons', label: 'Купоны', op: 'Купоны' },
  { key: 'amortizations', label: 'Амортизация', op: 'Амортизация' },
]
const MODES = [
  { value: 'both', label: 'Год ± прогноз' },
  { value: 'past', label: 'Получено' },
  { value: 'future', label: 'Прогноз' },
]
const mode = ref('both')

const monthIdx = (m) => {
  const [y, mm] = String(m).split('-').map(Number)
  return y * 12 + (mm - 1)
}
const nowIdx = (() => {
  const d = new Date()
  return d.getFullYear() * 12 + d.getMonth()
})()

const norm = (row, forecast) => {
  const r = { month: row.month, forecast, count: Number(row.payout_count) || 0 }
  let t = 0
  for (const k of KEYS) {
    r[k.key] = Math.max(0, Number(row[k.key]) || 0)
    t += r[k.key]
  }
  r.total = t
  return r
}

const pastRows = computed(() =>
  props.past
    .filter((p) => /^\d{4}-\d{2}$/.test(p?.month || '') && monthIdx(p.month) <= nowIdx)
    .sort((a, b) => a.month.localeCompare(b.month))
    .slice(-12)
    .map((p) => norm(p, false)),
)
const futureRows = computed(() =>
  props.future
    .filter((p) => /^\d{4}-\d{2}$/.test(p?.month || '') && monthIdx(p.month) >= nowIdx)
    .sort((a, b) => a.month.localeCompare(b.month))
    .filter((p) => !pastRows.value.some((r) => r.month === p.month))
    .slice(0, 12)
    .map((p) => norm(p, true)),
)

const rows = computed(() => {
  if (mode.value === 'past') return pastRows.value
  if (mode.value === 'future') return futureRows.value
  return [...pastRows.value, ...futureRows.value]
})

const receivedTotal = computed(() => pastRows.value.reduce((s, r) => s + r.total, 0))
const expectedTotal = computed(() => futureRows.value.reduce((s, r) => s + r.total, 0))

// ── геометрия ──────────────────────────────────────────────────────────────
const PAD = { top: 10, right: 50, bottom: 26, left: 0 }
const H = 230
const box = ref(null)
const { width } = useElementSize(box)
const plotW = computed(() => Math.max(0, width.value - PAD.left - PAD.right))
const plotH = H - PAD.top - PAD.bottom

const x = computed(() => scaleBand().domain(rows.value.map((r) => r.month)).range([0, plotW.value]).paddingInner(0.3).paddingOuter(0.1))
const y = computed(() => {
  const max = Math.max(1, ...rows.value.map((r) => r.total))
  return scaleLinear().domain([0, max * 1.08]).range([plotH, 0]).nice(3)
})
const yTicks = computed(() => y.value.ticks(3).filter((v) => v > 0).map((v) => ({ v, y: y.value(v), label: axisMoney(v) })))

/** прямоугольник со скруглённым верхом — «данные растут от базовой линии» */
function topRounded(x0, y0, w, h, r) {
  const rr = Math.min(r, w / 2, h)
  return `M${x0},${y0 + h}V${y0 + rr}Q${x0},${y0} ${x0 + rr},${y0}H${x0 + w - rr}Q${x0 + w},${y0} ${x0 + w},${y0 + rr}V${y0 + h}Z`
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
  const every = Math.max(1, Math.ceil(rows.value.length / Math.max(1, Math.floor(plotW.value / 46))))
  return rows.value.map((r, i) => {
    const segs = []
    let acc = 0
    const nonZero = KEYS.filter((k) => r[k.key] > 0)
    const top = nonZero[nonZero.length - 1]?.key
    for (const k of KEYS) {
      const v = r[k.key]
      if (!(v > 0)) continue
      const y1 = by(acc)
      const y0 = by(acc + v)
      acc += v
      const gap = k.key === top ? 0 : 2
      const h = Math.max(0, y1 - y0 - gap)
      const x0 = bx(r.month)
      segs.push({
        key: k.key,
        d: k.key === top ? topRounded(x0, y0, bw, Math.max(h, 1), 4) : `M${x0},${y0 + gap}h${bw}v${h}h${-bw}Z`,
      })
    }
    return {
      ...r,
      i,
      x: bx(r.month),
      w: bw,
      top: by(r.total),
      segs,
      label: i % every === 0 ? monLabel(r.month) : '',
    }
  })
})

const divider = computed(() => {
  if (mode.value !== 'both' || !pastRows.value.length || !futureRows.value.length) return null
  const last = bars.value[pastRows.value.length - 1]
  const next = bars.value[pastRows.value.length]
  if (!last || !next) return null
  return (last.x + last.w + next.x) / 2
})

// ── наведение ──────────────────────────────────────────────────────────────
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

function openMonth(b) {
  if (b.forecast || !b.total) return
  const types = KEYS.filter((k) => b[k.key] > 0).map((k) => k.op)
  const query = { view: 'operations', month: b.month }
  if (types.length === 1) query.opType = types[0]
  else if (types.length > 1) query.opType = types
  router.push({ path: '/transactions', query })
}

const fmt = (v) => money(v)
</script>

<template>
  <CvWidget v-bind="$attrs" title="Выплаты" :icon="HandCoins">
    <template #actions>
      <CvSegmented v-model="mode" :options="MODES" size="sm" aria-label="Период выплат" />
    </template>

    <div class="po">
      <div class="po__totals">
        <div>
          <span>Получено за 12 мес</span>
          <b><CvNumber :value="receivedTotal" :format="fmt" /></b>
        </div>
        <div>
          <span>Ожидается за 12 мес</span>
          <b class="is-dim"><CvNumber :value="expectedTotal" :format="fmt" /></b>
        </div>
      </div>

      <div ref="box" class="po__chart" :style="{ height: `${H}px` }" @pointerleave="hover = null">
        <svg v-if="width" :width="width" :height="H" class="po__svg" role="img" aria-label="Выплаты по месяцам">
          <defs>
            <pattern
              v-for="k in KEYS"
              :id="`${uid}-h-${k.key}`"
              :key="k.key"
              width="6"
              height="6"
              patternUnits="userSpaceOnUse"
              patternTransform="rotate(45)"
            >
              <rect width="6" height="6" :fill="PAYOUT_COLORS[k.key]" fill-opacity=".22" />
              <line x1="0" y1="0" x2="0" y2="6" :stroke="PAYOUT_COLORS[k.key]" stroke-width="2.4" stroke-opacity=".85" />
            </pattern>
          </defs>
          <g :transform="`translate(${PAD.left},${PAD.top})`">
            <g class="po__grid" aria-hidden="true">
              <line v-for="t in yTicks" :key="t.v" x1="0" :x2="plotW" :y1="t.y" :y2="t.y" />
              <text v-for="t in yTicks" :key="`l${t.v}`" :x="plotW + 10" :y="t.y" dy="0.32em">{{ t.label }}</text>
              <line class="is-base" x1="0" :x2="plotW" :y1="plotH" :y2="plotH" />
            </g>

            <g v-if="divider != null" class="po__now" aria-hidden="true">
              <line :x1="divider" :x2="divider" y1="-4" :y2="plotH" />
              <text :x="divider + 6" y="4">прогноз →</text>
            </g>

            <g
              v-for="b in bars"
              :key="`${mode}-${b.month}`"
              class="po__bar"
              :class="{ 'is-dim': hover != null && hover !== b.i, 'is-forecast': b.forecast, 'is-link': !b.forecast && b.total > 0 }"
              :style="{ '--i': b.i }"
              @pointerenter="hover = b.i"
              @click="openMonth(b)"
            >
              <rect class="po__hit" :x="b.x - 3" y="0" :width="b.w + 6" :height="plotH" />
              <g class="po__stack">
                <path
                  v-for="s in b.segs"
                  :key="s.key"
                  :d="s.d"
                  :fill="b.forecast ? `url(#${uid}-h-${s.key})` : PAYOUT_COLORS[s.key]"
                />
              </g>
              <text v-if="b.label" class="po__x" :x="b.x + b.w / 2" :y="plotH + 18" text-anchor="middle">{{ b.label }}</text>
            </g>
          </g>
        </svg>

        <div v-if="hovered" class="cv-tip po__tip" :style="tipStyle">
          <div class="cv-tip__date">{{ monthLong(`${hovered.month}-01`) }}{{ hovered.forecast ? ' · прогноз' : '' }}</div>
          <template v-for="k in KEYS" :key="k.key">
            <div v-if="hovered[k.key] > 0" class="cv-tip__row">
              <span><i class="cv-tip__sw" :style="{ background: PAYOUT_COLORS[k.key] }" />{{ k.label }}</span>
              <b>{{ money(hovered[k.key]) }}</b>
            </div>
          </template>
          <div class="cv-tip__sep" />
          <div class="cv-tip__row"><span>Итого</span><b>{{ money(hovered.total) }}</b></div>
          <div v-if="hovered.forecast && hovered.count" class="po__tip-note">
            {{ hovered.count }} {{ plural(hovered.count, 'выплата', 'выплаты', 'выплат') }} по графику эмитентов
          </div>
          <div v-else-if="!hovered.forecast && hovered.total" class="po__tip-note is-link">Нажмите, чтобы открыть операции</div>
        </div>

        <div v-if="!rows.length" class="po__empty">Выплат за этот период нет</div>
      </div>

      <div class="cv-legend po__legend">
        <span v-for="k in KEYS" :key="k.key" class="cv-legend__item">
          <i class="cv-legend__sw" :style="{ background: PAYOUT_COLORS[k.key] }" />{{ k.label }}
        </span>
        <span v-if="mode !== 'past'" class="cv-legend__item">
          <i class="cv-legend__sw po__sw-hatch" />Прогноз
        </span>
      </div>
    </div>
  </CvWidget>
</template>

<style scoped>
.po { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.po__totals { display: flex; gap: 28px; flex-wrap: wrap; }
.po__totals div { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.po__totals div > span { font-size: 12px; color: var(--cv-mut); }
.po__totals b { font-family: var(--cv-display); font-size: 22px; font-weight: 600; letter-spacing: -0.02em; color: var(--cv-ink); }
.po__totals b.is-dim { color: var(--cv-ink-2); }

.po__chart { position: relative; }
.po__svg { display: block; overflow: visible; }
.po__grid line { stroke: rgba(255, 255, 255, .04); }
.po__grid line.is-base { stroke: rgba(255, 255, 255, .08); }
.po__grid text, .po__x { font-size: 11px; fill: var(--cv-dim); font-variant-numeric: tabular-nums; }

.po__now line { stroke: rgba(180, 188, 255, .3); stroke-dasharray: 2 4; }
.po__now text { font-size: 10.5px; fill: var(--cv-accent-ink); opacity: .75; }

.po__hit { fill: transparent; }
.po__bar { transition: opacity .2s; }
.po__bar.is-link { cursor: pointer; }
.po__bar.is-dim { opacity: .35; }
.po__stack {
  transform-box: fill-box; transform-origin: 50% 100%;
  animation: po-grow .8s var(--cv-ease) backwards;
  animation-delay: calc(var(--i) * 22ms + 80ms);
}
@keyframes po-grow { from { transform: scaleY(0); } }

.po__tip { min-width: 190px; transition: left .12s var(--cv-ease), top .12s var(--cv-ease); }
.po__tip-note { margin-top: 6px; font-size: 11.5px; color: var(--cv-mut); }
.po__tip-note.is-link { color: var(--cv-accent-ink); }

.po__empty { position: absolute; inset: 0; display: grid; place-items: center; color: var(--cv-mut); font-size: 13px; }

.po__sw-hatch {
  background: repeating-linear-gradient(135deg, rgba(139, 145, 161, .9) 0 2px, rgba(139, 145, 161, .25) 2px 5px);
}
</style>
