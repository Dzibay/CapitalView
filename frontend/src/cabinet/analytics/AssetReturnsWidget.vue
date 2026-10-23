<script setup>
/**
 * Доходность по активам: расходящиеся полосы от нуля (рост — акцент, падение — красный),
 * период «всё время / год / месяц», единицы «% / ₽». В подсказке — из чего сложился результат.
 */
import { computed, ref } from 'vue'
import CvWidget from '../ui/CvWidget.vue'
import CvSegmented from '../ui/CvSegmented.vue'
import { money, pct, plural } from '../format'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  assetReturns: { type: Array, default: () => [] },
})

const PERIODS = [
  { value: 'all', label: 'Всё время' },
  { value: 'year', label: 'Год' },
  { value: 'month', label: 'Месяц' },
]
const UNITS = [
  { value: 'pct', label: '%' },
  { value: 'rub', label: '₽' },
]
const period = ref('all')
const unit = ref('pct')
const expanded = ref(false)
const LIMIT = 10

const n = (v) => Number(v) || 0

function pick(a, p) {
  if (p === 'all') {
    return {
      pct: n(a.return_percent),
      rub: n(a.total_return),
      price: n(a.price_change),
      realized: n(a.realized_profit),
      payouts: n(a.total_payouts),
      costs: n(a.total_commissions) + n(a.total_taxes),
      base: n(a.invested_amount),
      baseLabel: 'Вложено',
    }
  }
  const s = p === 'year' ? '_year' : '_month'
  return {
    pct: n(a[`return_percent${s}`]),
    rub: n(a[`total_return${s}`]),
    price: n(a[`price_change${s}`]),
    realized: n(a[`realized_profit${s}`]),
    payouts: n(a[`total_payouts${s}`]),
    costs: n(a[`total_commissions${s}`]) + n(a[`total_taxes${s}`]),
    base: n(a[p === 'year' ? 'value_year_ago' : 'value_month_ago']),
    baseLabel: p === 'year' ? 'Стоимость год назад' : 'Стоимость месяц назад',
  }
}

const rows = computed(() =>
  props.assetReturns
    .map((a) => ({ id: a.asset_id ?? a.asset_ticker, name: a.asset_name || a.asset_ticker, ticker: a.asset_ticker, ...pick(a, period.value) }))
    .filter((r) => r.base > 0 || r.rub !== 0)
    .map((r) => ({ ...r, v: unit.value === 'pct' ? r.pct : r.rub }))
    .sort((a, b) => b.v - a.v),
)

const shown = computed(() => {
  const list = rows.value
  if (expanded.value || list.length <= LIMIT) return list
  // лучшие и худшие: половина сверху, половина снизу
  const half = LIMIT / 2
  return [...list.slice(0, half), ...list.slice(-half)]
})
const hiddenCount = computed(() => rows.value.length - shown.value.length)

const maxPos = computed(() => Math.max(0, ...rows.value.map((r) => r.v)))
const maxNeg = computed(() => Math.max(0, ...rows.value.map((r) => -r.v)))
/** доля ширины дорожки слева от нуля */
const zero = computed(() => {
  const span = maxPos.value + maxNeg.value
  if (!span) return 0
  return Math.min(0.5, maxNeg.value / span)
})
function bar(r) {
  const span = maxPos.value + maxNeg.value || 1
  const w = (Math.abs(r.v) / span) * 100
  return r.v >= 0
    ? { left: `${zero.value * 100}%`, width: `${w}%` }
    : { left: `${zero.value * 100 - w}%`, width: `${w}%` }
}

const summary = computed(() => {
  const up = rows.value.filter((r) => r.v > 0).length
  return { up, down: rows.value.filter((r) => r.v < 0).length }
})

const fmtV = (v) => (unit.value === 'pct' ? pct(v) : money(v, { sign: true }))

// ── подсказка ──────────────────────────────────────────────────────────────
const hover = ref(null)
const tip = ref({ top: 0, left: 0 })
const TIP_W = 240
function onEnter(r, e) {
  hover.value = r
  const row = e.currentTarget
  const wrap = row.offsetParent
  const b = row.querySelector('.ar__bar')?.getBoundingClientRect()
  const w = wrap.getBoundingClientRect()
  const anchor = b ? (r.v >= 0 ? b.right : b.left) - w.left : w.width / 2
  tip.value = {
    top: row.offsetTop + row.offsetHeight + 4,
    left: Math.max(0, Math.min(w.width - TIP_W, anchor - TIP_W / 2)),
  }
}
</script>

<template>
  <CvWidget v-bind="$attrs" title="Доходность по активам">
    <template #actions>
      <CvSegmented v-model="unit" :options="UNITS" size="sm" aria-label="Единицы" />
      <CvSegmented v-model="period" :options="PERIODS" size="sm" aria-label="Период доходности" />
    </template>

    <div class="ar">
      <p class="ar__summary">
        <span><i class="ar__dot is-up" />{{ summary.up }} в плюсе</span>
        <span><i class="ar__dot is-down" />{{ summary.down }} в минусе</span>
        <span v-if="rows.length > LIMIT && !expanded" class="ar__note">5 лучших и 5 худших</span>
      </p>

      <div v-if="rows.length" class="ar__wrap" @pointerleave="hover = null">
      <ol class="ar__list">
        <template v-for="(r, i) in shown" :key="r.id">
        <li v-if="!expanded && rows.length > LIMIT && i === LIMIT / 2" class="ar__sep" aria-hidden="true"><span>{{ hiddenCount }} {{ plural(hiddenCount, 'актив', 'актива', 'активов') }} между ними</span></li>
        <li
          class="ar__row"
          :class="{ 'is-dim': hover && hover.id !== r.id }"
          :style="{ '--i': i }"
          @pointerenter="onEnter(r, $event)"
        >
          <span class="ar__name">
            <b>{{ r.name }}</b>
            <small v-if="r.ticker && r.ticker !== r.name">{{ r.ticker }}</small>
          </span>
          <span class="ar__track">
            <i v-if="zero > 0" class="ar__zero" :style="{ left: `${zero * 100}%` }" />
            <i class="ar__bar" :class="r.v >= 0 ? 'is-up' : 'is-down'" :style="bar(r)" />
          </span>
          <span class="ar__val cv-num" :class="r.v > 0 ? 'cv-up' : r.v < 0 ? 'cv-down' : ''">{{ fmtV(r.v) }}</span>
        </li>
        </template>
      </ol>

        <div v-if="hover" class="cv-tip ar__tip" :style="{ top: `${tip.top}px`, left: `${tip.left}px`, width: `${TIP_W}px` }">
          <div class="cv-tip__date">{{ hover.name }}</div>
          <div class="cv-tip__row"><span>Изменение цены</span><b>{{ money(hover.price, { sign: true }) }}</b></div>
          <div v-if="hover.realized" class="cv-tip__row"><span>Зафиксировано</span><b>{{ money(hover.realized, { sign: true }) }}</b></div>
          <div v-if="hover.payouts" class="cv-tip__row"><span>Выплаты</span><b>{{ money(hover.payouts, { sign: true }) }}</b></div>
          <div v-if="hover.costs" class="cv-tip__row"><span>Комиссии и налоги</span><b>{{ money(hover.costs, { sign: true }) }}</b></div>
          <div class="cv-tip__sep" />
          <div class="cv-tip__row">
            <span>Итого</span>
            <b :class="hover.rub > 0 ? 'cv-up' : hover.rub < 0 ? 'cv-down' : ''">{{ money(hover.rub, { sign: true }) }} · {{ pct(hover.pct) }}</b>
          </div>
          <div class="cv-tip__row"><span>{{ hover.baseLabel }}</span><b>{{ money(hover.base) }}</b></div>
        </div>
      </div>
      <p v-else class="ar__empty">Нет данных о доходности за этот период</p>

      <button v-if="rows.length > LIMIT" type="button" class="cv-btn cv-btn--ghost cv-btn--sm ar__more" @click="expanded = !expanded">
        {{ expanded ? 'Свернуть' : `Показать все ${rows.length} ${plural(rows.length, 'актив', 'актива', 'активов')}` }}
        <small v-if="!expanded">+{{ hiddenCount }}</small>
      </button>
    </div>
  </CvWidget>
</template>

<style scoped>
.ar { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.ar__summary { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin: 0; font-size: 12.5px; color: var(--cv-mut); }
.ar__summary span { display: inline-flex; align-items: center; gap: 7px; }
.ar__dot { width: 7px; height: 7px; border-radius: 50%; }
.ar__dot.is-up { background: var(--cv-accent); }
.ar__dot.is-down { background: var(--cv-down); }
.ar__note { color: var(--cv-dim); }

.ar__wrap { position: relative; }
.ar__list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
.ar__row {
  display: grid; grid-template-columns: minmax(120px, 220px) minmax(0, 1fr) 104px; align-items: center; gap: 16px;
  height: 36px; padding: 0 10px; margin: 0 -10px; border-radius: 10px;
  transition: opacity .2s, background .2s;
  animation: ar-in .6s var(--cv-ease) backwards; animation-delay: calc(var(--i) * 24ms + 60ms);
}
.ar__row:hover { background: var(--cv-hover); }
.ar__row.is-dim { opacity: .45; }
.ar__sep { display: flex; align-items: center; gap: 12px; height: 30px; font-size: 11.5px; color: var(--cv-dim); }
.ar__sep::before, .ar__sep::after { content: ''; flex: 1; height: 1px; background: repeating-linear-gradient(90deg, var(--cv-line-2) 0 3px, transparent 3px 7px); }
.ar__name { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
.ar__name b { font-size: 13px; font-weight: 550; color: var(--cv-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ar__name small { font-size: 11.5px; color: var(--cv-dim); flex: none; }

.ar__track { position: relative; height: 14px; }
.ar__zero { position: absolute; top: -6px; bottom: -6px; width: 1px; background: var(--cv-line-2); }
.ar__bar {
  position: absolute; top: 2px; bottom: 2px; min-width: 2px;
  transform-origin: left center;
  animation: ar-grow .8s var(--cv-ease) backwards; animation-delay: calc(var(--i) * 24ms + 120ms);
}
.ar__bar.is-up { background: var(--cv-accent); border-radius: 0 4px 4px 0; }
.ar__bar.is-down { background: var(--cv-down); border-radius: 4px 0 0 4px; transform-origin: right center; opacity: .85; }
.ar__val { text-align: right; font-size: 13px; font-weight: 550; color: var(--cv-ink-2); white-space: nowrap; }

.ar__tip { transition: top .12s var(--cv-ease), left .12s var(--cv-ease); }

.ar__more { align-self: flex-start; gap: 6px; }
.ar__more small { color: var(--cv-dim); font-size: 11.5px; }
.ar__empty { margin: 0; padding: 40px 0; text-align: center; color: var(--cv-mut); font-size: 13px; }

@keyframes ar-in { from { opacity: 0; transform: translateY(4px); } }
@keyframes ar-grow { from { transform: scaleX(0); } }

@media (max-width: 768px) {
  .ar__row { grid-template-columns: minmax(0, 1fr) 84px; grid-template-rows: auto auto; height: auto; padding: 8px 10px; row-gap: 6px; }
  .ar__name { grid-column: 1; grid-row: 1; }
  .ar__val { grid-column: 2; grid-row: 1; }
  .ar__track { grid-column: 1 / -1; grid-row: 2; height: 10px; }
  .ar__tip { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .ar__row, .ar__bar { animation: none; }
}
</style>
