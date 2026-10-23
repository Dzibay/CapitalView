<script setup>
/**
 * Календарь событий на 60 дней: дивиденды, купоны и амортизация по позициям выбранной ветки портфелей.
 * Сверху — шкала дней со столбиками сумм (наведение показывает день), ниже — ближайшие выплаты списком.
 */
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight } from 'lucide-vue-next'
import { scaleLinear } from 'd3-scale'
import CvWidget from '../ui/CvWidget.vue'
import CvNumber from '../ui/CvNumber.vue'
import { useElementSize } from '../charts/useElementSize'
import { PAYOUT_COLORS } from '../palette'
import { payoutAmountToRub } from '../../utils/currencyRatesToRub'
import { dateShort, money, plural } from '../format'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  /** позиции с выплатами (portfolioService.getPayoutPositions), уже отфильтрованные по ветке */
  positions: { type: Array, default: () => [] },
  referenceData: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  days: { type: Number, default: 60 },
  limit: { type: Number, default: 5 },
})
const router = useRouter()

const TYPES = {
  dividend: { key: 'dividends', label: 'Дивиденды', one: 'Дивиденд' },
  coupon: { key: 'coupons', label: 'Купоны', one: 'Купон' },
  amortization: { key: 'amortizations', label: 'Амортизация', one: 'Амортизация' },
}
const kindOf = (p) => (TYPES[p.type] ? p.type : 'dividend') // прогноз дивиденда — тоже дивиденд

const DAY = 86400000
const today = (() => {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  return d
})()
const dayIndex = (s) => {
  const d = new Date(s)
  d.setHours(0, 0, 0, 0)
  return Math.round((d - today) / DAY)
}

const events = computed(() => {
  const map = new Map()
  for (const pos of props.positions || []) {
    for (const p of pos.payouts || []) {
      if (p.status === 'received') continue
      const dateStr = p.payment_date || p.record_date || p.last_buy_date
      if (!dateStr) continue
      const day = dayIndex(dateStr)
      if (day < 0 || day > props.days) continue
      const qty = Number(p.basis_quantity ?? pos.quantity) || 0
      const total = p.expected_total != null && p.expected_total !== '' ? Number(p.expected_total) : Number(p.value) * qty
      if (!(total > 0)) continue
      const rub = payoutAmountToRub(total, pos.currency_ticker || 'RUB', props.referenceData) ?? total
      const kind = kindOf(p)
      const forecast = p.type === 'forecast' || p.status === 'forecast' || p.status === 'recommended'
      // одна бумага из нескольких подпортфелей — одним событием
      const key = `${pos.asset_id ?? pos.ticker}|${kind}|${day}`
      const cur = map.get(key)
      if (cur) {
        cur.amount += rub
        continue
      }
      map.set(key, {
        key,
        day,
        date: new Date(today.getTime() + day * DAY),
        kind,
        forecast,
        assetId: pos.asset_id,
        name: pos.name || pos.ticker,
        ticker: pos.ticker,
        amount: rub,
      })
    }
  }
  return [...map.values()].sort((a, b) => a.day - b.day || b.amount - a.amount)
})

const total = computed(() => events.value.reduce((s, e) => s + e.amount, 0))
const shownKinds = computed(() => Object.keys(TYPES).filter((k) => events.value.some((e) => e.kind === k)))

// ── шкала ─────────────────────────────────────────────
const box = ref(null)
const { width } = useElementSize(box)
const H = 64
const BASE = H - 18

const byDay = computed(() => {
  const map = new Map()
  for (const e of events.value) {
    if (!map.has(e.day)) map.set(e.day, { day: e.day, date: e.date, total: 0, items: [] })
    const d = map.get(e.day)
    d.total += e.amount
    d.items.push(e)
  }
  return [...map.values()]
})
const x = computed(() => scaleLinear().domain([0, props.days]).range([6, Math.max(7, width.value - 6)]))
const maxDay = computed(() => Math.max(1, ...byDay.value.map((d) => d.total)))
const barH = (v) => Math.max(4, Math.sqrt(v / maxDay.value) * (BASE - 6))

/** столбик дня — стопка сегментов по типам выплат с зазором 1.5px */
const columns = computed(() =>
  byDay.value.map((d) => {
    const h = barH(d.total)
    const parts = []
    let y = BASE
    const kinds = Object.keys(TYPES)
      .map((k) => ({ k, v: d.items.filter((e) => e.kind === k).reduce((s, e) => s + e.amount, 0), f: d.items.every((e) => e.kind !== k || e.forecast) }))
      .filter((p) => p.v > 0)
    kinds.forEach((p, i) => {
      const ph = Math.max(2, (p.v / d.total) * h - (i ? 1.5 : 0))
      y -= ph + (i ? 1.5 : 0)
      parts.push({ k: p.k, y, h: ph, color: PAYOUT_COLORS[TYPES[p.k].key], forecast: p.f })
    })
    return { ...d, x: x.value(d.day), parts }
  }),
)

const ticks = computed(() => {
  const list = []
  for (let i = 0; i <= props.days; i++) {
    const d = new Date(today.getTime() + i * DAY)
    if (d.getDate() === 1) list.push({ x: x.value(i), label: dateShort(d).replace(/^1\s/, ''), month: true })
    else if (i % 7 === 0) list.push({ x: x.value(i), month: false })
  }
  return list
})

const hover = ref(null)
function onMove(e) {
  if (!byDay.value.length) return
  const r = box.value.getBoundingClientRect()
  const day = x.value.invert(e.clientX - r.left)
  let best = null
  for (const c of columns.value) if (!best || Math.abs(c.day - day) < Math.abs(best.day - day)) best = c
  hover.value = best && Math.abs(best.day - day) <= 3 ? best : null
}
const tipFlip = computed(() => hover.value && hover.value.x > width.value * 0.6)

// ── список ────────────────────────────────────────────
const list = computed(() => events.value.slice(0, props.limit))
const rest = computed(() => events.value.slice(props.limit))
const restTotal = computed(() => rest.value.reduce((s, e) => s + e.amount, 0))

const when = (e) => (e.day === 0 ? 'Сегодня' : e.day === 1 ? 'Завтра' : `через ${e.day} ${plural(e.day, 'день', 'дня', 'дней')}`)
const fmt = (v) => money(v)
const open = (e) => e.assetId != null && router.push(`/assets/${e.assetId}`)
</script>

<template>
  <CvWidget v-bind="$attrs" title="Календарь выплат">
    <template #actions>
      <button type="button" class="cv-btn cv-btn--ghost cv-btn--sm cal__all" @click="router.push('/dividends')">
        Все <ArrowRight :size="14" />
      </button>
    </template>

    <div class="cal">
      <div class="cal__sum">
        <div class="cal__sum-val"><CvNumber :value="total" :format="fmt" dim /></div>
        <p>
          {{ events.length ? `${events.length} ${plural(events.length, 'выплата', 'выплаты', 'выплат')} за ${days} дней` : `за ${days} дней` }}
        </p>
      </div>

      <div
        ref="box"
        class="cal__line"
        role="img"
        :aria-label="`Выплаты по дням на ${days} дней вперёд`"
        @pointermove="onMove"
        @pointerleave="hover = null"
      >
        <svg v-if="width" :width="width" :height="H" aria-hidden="true">
          <line :x1="0" :x2="width" :y1="BASE + 0.5" :y2="BASE + 0.5" class="cal__base" />
          <template v-for="(t, i) in ticks" :key="i">
            <line :x1="t.x" :x2="t.x" :y1="BASE + 3" :y2="BASE + (t.month ? 8 : 5)" class="cal__tick" :class="{ 'is-month': t.month }" />
            <text v-if="t.month" :x="t.x + 4" :y="H - 2" class="cal__tick-label">{{ t.label }}</text>
          </template>
          <text :x="x(0)" :y="H - 2" class="cal__tick-label is-today">сегодня</text>

          <g
            v-for="(c, ci) in columns"
            :key="c.day"
            class="cal__col"
            :class="{ 'is-dim': hover && hover.day !== c.day }"
            :style="{ '--i': ci }"
          >
            <rect
              v-for="p in c.parts"
              :key="p.k"
              :x="c.x - 2.5"
              :y="p.y"
              width="5"
              :height="p.h"
              rx="2"
              :fill="p.color"
              :fill-opacity="p.forecast ? 0.45 : 1"
            />
          </g>
        </svg>

        <div v-if="hover" class="cv-tip cal__tip" :class="{ 'is-flip': tipFlip }" :style="{ left: `${hover.x}px` }">
          <div class="cv-tip__date">{{ dateShort(hover.date) }}</div>
          <div v-for="e in hover.items.slice(0, 4)" :key="e.key" class="cv-tip__row">
            <span><i class="cal__sw" :style="{ background: PAYOUT_COLORS[TYPES[e.kind].key] }" />{{ e.name }}</span>
            <b>{{ money(e.amount) }}</b>
          </div>
          <div v-if="hover.items.length > 4" class="cv-tip__row"><span>ещё {{ hover.items.length - 4 }}</span></div>
        </div>
      </div>

      <ul v-if="shownKinds.length > 1" class="cal__legend">
        <li v-for="k in shownKinds" :key="k"><i :style="{ background: PAYOUT_COLORS[TYPES[k].key] }" />{{ TYPES[k].label }}</li>
      </ul>

      <ul v-if="list.length" class="cal__list">
        <li v-for="e in list" :key="e.key">
          <button type="button" class="cal__row" :class="{ 'is-on': hover?.day === e.day }" @click="open(e)">
            <span class="cal__date">
              <b class="cv-num">{{ e.date.getDate() }}</b>
              <small>{{ dateShort(e.date).replace(/^\d+\s/, '') }}</small>
            </span>
            <span class="cal__what">
              <b>{{ e.name }}</b>
              <small>
                <i class="cal__sw" :style="{ background: PAYOUT_COLORS[TYPES[e.kind].key] }" />
                {{ TYPES[e.kind].one }}{{ e.forecast ? ' · прогноз' : '' }} · {{ when(e) }}
              </small>
            </span>
            <b class="cal__amount cv-num">{{ money(e.amount) }}</b>
          </button>
        </li>
      </ul>
      <div v-else-if="loading" class="cal__skel" aria-hidden="true"><i /><i /><i /></div>
      <p v-else class="cal__empty">В ближайшие {{ days }} дней выплат не ожидается</p>

      <p v-if="rest.length" class="cal__rest">
        и ещё {{ rest.length }} {{ plural(rest.length, 'выплата', 'выплаты', 'выплат') }} на <span class="cv-num">{{ money(restTotal) }}</span>
      </p>
    </div>
  </CvWidget>
</template>

<style scoped>
.cal { display: flex; flex-direction: column; height: 100%; min-width: 0; }
.cal__all { gap: 5px; }

.cal__sum-val { font-family: var(--cv-display); font-size: 28px; font-weight: 500; letter-spacing: -0.035em; color: var(--cv-ink); }
.cal__sum p { margin-top: 6px; font-size: 12.5px; color: var(--cv-mut); }

.cal__line { position: relative; height: 64px; margin-top: 20px; cursor: crosshair; touch-action: pan-y; }
.cal__line svg { display: block; overflow: visible; }
.cal__base { stroke: rgba(255, 255, 255, .08); }
.cal__tick { stroke: rgba(255, 255, 255, .12); }
.cal__tick.is-month { stroke: rgba(255, 255, 255, .22); }
.cal__tick-label { font-size: 10.5px; fill: var(--cv-dim); }
.cal__tick-label.is-today { fill: var(--cv-mut); }
.cal__col { transition: opacity .2s; animation: cal-rise .7s var(--cv-ease) backwards calc(var(--i) * 40ms + 200ms); transform-box: fill-box; transform-origin: bottom; }
.cal__col.is-dim { opacity: .3; }
@keyframes cal-rise { from { transform: scaleY(0); } }
.cal__tip { position: absolute; bottom: calc(100% - 8px); transform: translateX(-12px); pointer-events: none; z-index: 5; white-space: nowrap; }
.cal__tip.is-flip { transform: translateX(calc(-100% + 12px)); }
.cal__tip .cv-tip__row span { display: inline-flex; align-items: center; gap: 6px; }

.cal__sw { display: inline-block; width: 7px; height: 7px; flex: none; border-radius: 2px; }
.cal__legend { list-style: none; display: flex; flex-wrap: wrap; gap: 6px 14px; margin: 12px 0 0; padding: 0; font-size: 11.5px; color: var(--cv-mut); }
.cal__legend li { display: inline-flex; align-items: center; gap: 6px; }
.cal__legend i { width: 7px; height: 7px; border-radius: 2px; }

.cal__list { list-style: none; margin: 16px 0 0; padding: 12px 0 0; border-top: 1px solid var(--cv-line); display: flex; flex-direction: column; }
.cal__row {
  display: grid; grid-template-columns: 38px minmax(0, 1fr) auto; align-items: center; gap: 12px;
  width: calc(100% + 16px); padding: 7px 8px; margin: 0 -8px;
  border: 0; border-radius: 10px; background: transparent; text-align: left; cursor: pointer;
  transition: background .2s;
}
.cal__row:hover, .cal__row.is-on { background: var(--cv-hover); }
.cal__date { display: flex; flex-direction: column; align-items: center; line-height: 1.1; }
.cal__date b { font-family: var(--cv-display); font-size: 17px; font-weight: 500; color: var(--cv-ink); }
.cal__date small { font-size: 10.5px; color: var(--cv-dim); }
.cal__what { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.cal__what b { font-size: 13px; font-weight: 550; color: var(--cv-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cal__what small { display: flex; align-items: center; gap: 6px; font-size: 11.5px; color: var(--cv-dim); white-space: nowrap; overflow: hidden; }
.cal__amount { font-size: 13px; font-weight: 550; color: var(--cv-ink); white-space: nowrap; }

.cal__rest { margin-top: auto; padding-top: 12px; font-size: 12px; color: var(--cv-dim); }
.cal__empty { flex: 1; display: grid; place-items: center; min-height: 100px; margin-top: 16px; font-size: 13px; color: var(--cv-mut); border-radius: 12px; border: 1px dashed var(--cv-line-2); }
.cal__skel { display: flex; flex-direction: column; gap: 12px; margin-top: 20px; }
.cal__skel i { height: 30px; border-radius: 8px; background: rgba(255, 255, 255, .04); animation: cal-pulse 1.4s ease-in-out infinite; }
@keyframes cal-pulse { 50% { opacity: .45; } }

@media (prefers-reduced-motion: reduce) { .cal__col { animation: none; } }
</style>
