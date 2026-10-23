<script setup>
/**
 * Инсайты: короткие выводы по данным портфеля — выплаты, источник роста капитала,
 * концентрация и разброс доходности позиций. Каждый вывод — фраза и маленькая визуализация.
 * Вывод, для которого не хватает данных, просто не показывается.
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Coins, TrendingUp, Layers, Scale, CalendarClock, ArrowRight } from 'lucide-vue-next'
import CvWidget from '../ui/CvWidget.vue'
import { SERIES, NEUTRAL } from '../palette'
import { effectiveUnitPriceInCurrency } from '../../utils/effectiveAssetPrice'
import { money, moneyCompact, pct, plural } from '../format'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  assets: { type: Array, default: () => [] },
  analytics: { type: Object, default: null },
  /** expandPortfolioHistoryForCharts(...) */
  history: { type: Object, default: null },
  limit: { type: Number, default: 4 },
})
const router = useRouter()

const NOM = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь', 'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь']
const PREP = ['январе', 'феврале', 'марте', 'апреле', 'мае', 'июне', 'июле', 'августе', 'сентябре', 'октябре', 'ноябре', 'декабре']
const mk = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
const tone = (v) => (v > 0 ? 'up' : v < 0 ? 'down' : '')

/** позиции, сложенные по бумаге */
const positions = computed(() => {
  const map = new Map()
  for (const a of props.assets) {
    const lev = Number(a.leverage || 1) || 1
    const value = (Number(a.quantity || 0) * effectiveUnitPriceInCurrency(a) * Number(a.currency_rate_to_rub || 1)) / lev
    if (!(value > 0)) continue
    const key = a.asset_id ?? a.ticker ?? a.name
    const profit = Number(a.profit_rub ?? a.profit ?? 0) || 0
    const cur = map.get(key)
    if (cur) { cur.value += value; cur.profit += profit } else map.set(key, { name: a.name || a.ticker, value, profit })
  }
  return [...map.values()].map((p) => ({ ...p, ret: p.value - p.profit > 0 ? (p.profit / (p.value - p.profit)) * 100 : 0 }))
})

// 1. выплаты за прошлый месяц против того же месяца год назад (или среднего за полгода)
function payoutsInsight() {
  const rows = props.analytics?.monthly_payouts || []
  if (!rows.length) return null
  const income = (r) => (Number(r?.dividends) || 0) + (Number(r?.coupons) || 0)
  const byMonth = new Map(rows.map((r) => [r.month, income(r)]))
  const now = new Date()
  const last = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  const cur = byMonth.get(mk(last)) || 0
  if (!(cur > 0)) return null
  const ya = byMonth.get(mk(new Date(last.getFullYear() - 1, last.getMonth(), 1))) || 0
  let base = ya
  let vs = 'чем год назад'
  if (!(ya > 0)) {
    const prev = []
    for (let k = 1; k <= 6; k++) prev.push(byMonth.get(mk(new Date(last.getFullYear(), last.getMonth() - k, 1))) || 0)
    base = prev.reduce((s, v) => s + v, 0) / 6
    vs = 'чем в среднем за полгода'
  }
  const bars = []
  for (let k = 11; k >= 0; k--) bars.push(byMonth.get(mk(new Date(last.getFullYear(), last.getMonth() - k, 1))) || 0)
  const parts = [{ t: `Выплаты за ${NOM[last.getMonth()]} — ` }, { t: money(cur), b: true }]
  if (base > 0) {
    const ch = (cur / base - 1) * 100
    parts.push({ t: Math.abs(ch) < 1 ? ', столько же, ' : ', на ' })
    if (Math.abs(ch) >= 1) parts.push({ t: pct(Math.abs(ch), { sign: false, digits: 0 }), tone: tone(ch) }, { t: ch > 0 ? ' больше, ' : ' меньше, ' })
    parts.push({ t: vs })
  }
  return { key: 'payouts', icon: Coins, kicker: 'Выплаты', parts, viz: { kind: 'bars', values: bars }, to: '/dividends' }
}

// 2. откуда рост капитала за год: пополнения или доход
function paceInsight() {
  const h = props.history
  const labels = h?.labels || []
  if (labels.length < 30) return null
  const from = new Date()
  from.setFullYear(from.getFullYear() - 1)
  let i = labels.findIndex((l) => new Date(l) >= from)
  if (i < 0) return null
  const n = labels.length - 1
  if (n - i < 30) return null
  const dValue = (h.data_value[n] || 0) - (h.data_value[i] || 0)
  const dInv = (h.data_invested[n] || 0) - (h.data_invested[i] || 0)
  const income = dValue - dInv
  if (!dValue) return null
  const parts = [
    { t: `За год капитал ${dValue >= 0 ? 'вырос' : 'снизился'} на ` },
    { t: moneyCompact(Math.abs(dValue)), b: true },
    { t: ': пополнения ' },
    { t: moneyCompact(dInv, { sign: true }), b: true },
    { t: ', доход ' },
    { t: moneyCompact(income, { sign: true }), tone: tone(income) },
  ]
  const split = [
    { label: 'Пополнения', v: Math.max(0, dInv), color: NEUTRAL },
    { label: 'Доход', v: Math.max(0, income), color: SERIES[0] },
  ].filter((p) => p.v > 0)
  return { key: 'pace', icon: TrendingUp, kicker: 'Рост капитала', parts, viz: split.length ? { kind: 'split', parts: split } : null, to: '/analitics' }
}

// 3. концентрация: доля трёх крупнейших позиций
function concentrationInsight() {
  const list = [...positions.value].sort((a, b) => b.value - a.value)
  if (list.length < 4) return null
  const total = list.reduce((s, p) => s + p.value, 0)
  const top = list.slice(0, 3)
  const share = (top.reduce((s, p) => s + p.value, 0) / total) * 100
  const parts = [
    { t: 'Три крупнейшие позиции — ' },
    { t: pct(share, { sign: false, digits: 0 }), b: true },
    { t: ` портфеля. Больше всего в «${top[0].name}»: ` },
    { t: pct((top[0].value / total) * 100, { sign: false, digits: 0 }), b: true },
  ]
  const split = top.map((p, k) => ({ label: p.name, v: p.value, color: SERIES[[0, 1, 2][k]] }))
  split.push({ label: `Ещё ${list.length - 3}`, v: total - top.reduce((s, p) => s + p.value, 0), color: 'rgba(255,255,255,.12)' })
  return { key: 'concentration', icon: Layers, kicker: 'Концентрация', parts, viz: { kind: 'split', parts: split, legend: false }, to: '/assets' }
}

// 4. разброс доходности: лидер и аутсайдер с момента покупки
function spreadInsight() {
  const list = positions.value.filter((p) => p.value - p.profit > 0)
  if (list.length < 3) return null
  const sorted = [...list].sort((a, b) => b.ret - a.ret)
  const best = sorted[0]
  const worst = sorted[sorted.length - 1]
  if (best.ret <= 0 && worst.ret >= 0) return null
  const parts = [
    { t: 'Лидер с покупки — ' }, { t: best.name, b: true }, { t: ' ' }, { t: pct(best.ret), tone: tone(best.ret) },
  ]
  if (worst !== best && worst.ret < 0) parts.push({ t: ', аутсайдер — ' }, { t: worst.name, b: true }, { t: ' ' }, { t: pct(worst.ret), tone: 'down' })
  const lo = Math.min(0, worst.ret)
  const hi = Math.max(0, best.ret)
  const span = hi - lo || 1
  const dots = sorted.map((p) => ({ x: (p.ret - lo) / span, hl: p === best || p === worst }))
  return { key: 'spread', icon: Scale, kicker: 'Доходность позиций', parts, viz: { kind: 'dots', dots, zero: (0 - lo) / span }, to: '/assets' }
}

// запасной: выплаты в следующем месяце
function upcomingInsight() {
  const rows = props.analytics?.future_payouts || []
  const now = new Date()
  const next = new Date(now.getFullYear(), now.getMonth() + 1, 1)
  const r = rows.find((x) => x.month === mk(next))
  const total = Number(r?.total_amount) || 0
  if (!(total > 0)) return null
  const cnt = Number(r.payout_count) || 0
  const parts = [{ t: `В ${PREP[next.getMonth()]} ожидается ` }]
  if (cnt) parts.push({ t: `${cnt} ${plural(cnt, 'выплата', 'выплаты', 'выплат')}`, b: true }, { t: ' на ' })
  parts.push({ t: money(total), b: true })
  return { key: 'upcoming', icon: CalendarClock, kicker: 'Скоро', parts, viz: null, to: '/dividends' }
}

const insights = computed(() =>
  [payoutsInsight, paceInsight, concentrationInsight, spreadInsight, upcomingInsight]
    .map((f) => { try { return f() } catch { return null } })
    .filter(Boolean)
    .slice(0, props.limit),
)

const maxBar = (vals) => Math.max(1, ...vals)
const splitTotal = (parts) => parts.reduce((s, p) => s + p.v, 0) || 1
</script>

<template>
  <CvWidget v-bind="$attrs" title="Инсайты">
    <p v-if="!insights.length" class="ins-empty">Пока мало данных для выводов — они появятся по мере истории портфеля.</p>
    <div v-else class="ins-wrap">
    <ul class="ins" :style="{ '--n': insights.length }">
      <li v-for="(it, i) in insights" :key="it.key" class="ins__item" :style="{ '--i': i }">
        <button type="button" class="ins__btn" @click="router.push(it.to)">
          <span class="ins__kicker"><component :is="it.icon" :size="14" :stroke-width="1.75" />{{ it.kicker }}</span>
          <p class="ins__text">
            <template v-for="(p, k) in it.parts" :key="k">
              <b v-if="p.b" class="cv-num">{{ p.t }}</b>
              <b v-else-if="p.tone" class="cv-num" :class="`cv-${p.tone}`">{{ p.t }}</b>
              <template v-else>{{ p.t }}</template>
            </template>
          </p>

          <span v-if="it.viz?.kind === 'bars'" class="ins__bars" aria-hidden="true">
            <i
              v-for="(v, k) in it.viz.values"
              :key="k"
              :class="{ 'is-last': k === it.viz.values.length - 1 }"
              :style="{ '--h': v / maxBar(it.viz.values), '--k': k }"
            />
          </span>
          <span v-else-if="it.viz?.kind === 'split'" class="ins__split" aria-hidden="true">
            <span class="ins__split-bar">
              <i v-for="p in it.viz.parts" :key="p.label" :style="{ flexGrow: p.v / splitTotal(it.viz.parts), background: p.color }" />
            </span>
            <span v-if="it.viz.legend !== false" class="ins__split-legend">
              <span v-for="p in it.viz.parts" :key="p.label"><i :style="{ background: p.color }" />{{ p.label }}</span>
            </span>
          </span>
          <span v-else-if="it.viz?.kind === 'dots'" class="ins__dots" aria-hidden="true">
            <span class="ins__dots-zero" :style="{ left: `${it.viz.zero * 100}%` }" />
            <i v-for="(d, k) in it.viz.dots" :key="k" :class="{ 'is-hl': d.hl }" :style="{ left: `${d.x * 100}%` }" />
          </span>

          <span class="ins__go">Подробнее <ArrowRight :size="13" /></span>
        </button>
      </li>
    </ul>
    </div>
  </CvWidget>
</template>

<style scoped>
.ins-wrap { margin: 0 -24px -24px; container-type: inline-size; }
.ins {
  list-style: none; margin: 0; padding: 0;
  display: grid; grid-template-columns: repeat(var(--n), minmax(0, 1fr));
  border-top: 1px solid var(--cv-line);
}
.ins-empty { font-size: 13px; color: var(--cv-mut); }
.ins__item { min-width: 0; border-left: 1px solid var(--cv-line); }
.ins__item:first-child { border-left: 0; }
.ins__btn {
  display: flex; flex-direction: column; gap: 12px; width: 100%; height: 100%; padding: 20px 24px 22px;
  border: 0; background: transparent; text-align: left; cursor: pointer; color: inherit; font: inherit;
  transition: background .25s;
}
.ins__btn:hover { background: rgba(255, 255, 255, .02); }
.ins__btn:focus-visible { outline: 2px solid var(--cv-accent-line); outline-offset: -2px; }

.ins__kicker { display: inline-flex; align-items: center; gap: 7px; font-size: 12px; color: var(--cv-mut); }
.ins__kicker svg { color: var(--cv-dim); }
.ins__text { font-size: 14px; line-height: 1.55; color: var(--cv-ink-2); text-wrap: pretty; }
.ins__text b { font-weight: 550; color: var(--cv-ink); }
.ins__text b.cv-up { color: var(--cv-up); }
.ins__text b.cv-down { color: var(--cv-down); }

.ins__bars { display: flex; align-items: flex-end; gap: 2px; height: 28px; margin-top: auto; }
.ins__bars i {
  flex: 1; height: max(2px, calc(var(--h) * 100%)); border-radius: 2px 2px 1px 1px; background: rgba(255, 255, 255, .12);
  transform-origin: bottom; animation: ins-rise .8s var(--cv-ease) backwards calc(var(--k) * 25ms + 250ms);
}
.ins__bars i.is-last { background: var(--cv-s1); }
@keyframes ins-rise { from { transform: scaleY(0); } }

.ins__split { display: flex; flex-direction: column; gap: 8px; margin-top: auto; }
.ins__split-bar { display: flex; gap: 2px; height: 6px; }
.ins__split-bar i { flex-basis: 0; min-width: 3px; border-radius: 2px; transform-origin: left; animation: ins-grow .9s var(--cv-ease) backwards .25s; }
.ins__split-bar i:first-child { border-radius: 3px 2px 2px 3px; }
.ins__split-bar i:last-child { border-radius: 2px 3px 3px 2px; }
@keyframes ins-grow { from { transform: scaleX(0); } }
.ins__split-legend { display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: 11px; color: var(--cv-dim); }
.ins__split-legend span { display: inline-flex; align-items: center; gap: 5px; }
.ins__split-legend i { width: 6px; height: 6px; border-radius: 2px; }

.ins__dots { position: relative; height: 14px; margin-top: auto; }
.ins__dots::before { content: ''; position: absolute; left: 0; right: 0; top: 50%; height: 1px; background: rgba(255, 255, 255, .08); }
.ins__dots-zero { position: absolute; top: 0; bottom: 0; width: 1px; background: rgba(255, 255, 255, .22); }
.ins__dots i {
  position: absolute; top: 50%; width: 6px; height: 6px; margin: -3px 0 0 -3px; border-radius: 50%;
  background: rgba(255, 255, 255, .28); box-shadow: 0 0 0 1.5px var(--cv-surface-2);
}
.ins__dots i.is-hl { width: 8px; height: 8px; margin: -4px 0 0 -4px; background: var(--cv-s1); }

.ins__go {
  display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 550; color: var(--cv-accent-ink);
  opacity: 0; transform: translateY(2px); transition: opacity .2s, transform .25s var(--cv-ease);
}
.ins__btn:hover .ins__go, .ins__btn:focus-visible .ins__go { opacity: 1; transform: none; }

@container (max-width: 900px) {
  .ins { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .ins__item:nth-child(odd) { border-left: 0; }
  .ins__item:nth-child(n + 3) { border-top: 1px solid var(--cv-line); }
}
@container (max-width: 520px) {
  .ins { grid-template-columns: minmax(0, 1fr); }
  .ins__item { border-left: 0; }
  .ins__item + .ins__item { border-top: 1px solid var(--cv-line); }
  .ins__go { opacity: 1; transform: none; }
}
@media (hover: none) { .ins__go { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { .ins__bars i, .ins__split-bar i { animation: none; } }
</style>
