<script setup>
/**
 * Кто платит: выплаты по активам за всё время, полоса на актив — дивиденды/купоны/амортизация.
 */
import { computed, ref } from 'vue'
import CvWidget from '../ui/CvWidget.vue'
import CvNumber from '../ui/CvNumber.vue'
import { PAYOUT_COLORS } from '../palette'
import { money, pct, plural } from '../format'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  payouts: { type: Array, default: () => [] },
})

const KEYS = [
  { key: 'dividends', field: 'total_dividends', label: 'Дивиденды' },
  { key: 'coupons', field: 'total_coupons', label: 'Купоны' },
  { key: 'amortizations', field: 'total_amortizations', label: 'Амортизация' },
]
const LIMIT = 7
const expanded = ref(false)

const rows = computed(() =>
  props.payouts
    .map((a) => {
      const parts = KEYS.map((k) => ({ ...k, value: Math.max(0, Number(a[k.field]) || 0) }))
      const total = parts.reduce((s, p) => s + p.value, 0) || Math.max(0, Number(a.total_payouts) || 0)
      return { id: a.asset_id ?? a.asset_ticker, name: a.asset_name || a.asset_ticker, ticker: a.asset_ticker, parts, total }
    })
    .filter((r) => r.total > 0)
    .sort((a, b) => b.total - a.total),
)
const total = computed(() => rows.value.reduce((s, r) => s + r.total, 0))
const max = computed(() => rows.value[0]?.total || 1)
const shown = computed(() => (expanded.value ? rows.value : rows.value.slice(0, LIMIT)))
const usedKeys = computed(() => KEYS.filter((k) => rows.value.some((r) => r.parts.find((p) => p.key === k.key).value > 0)))
const topShare = computed(() => {
  const top3 = rows.value.slice(0, 3).reduce((s, r) => s + r.total, 0)
  return total.value ? (top3 / total.value) * 100 : 0
})

const hover = ref(null)
const fmt = (v) => money(v)
</script>

<template>
  <CvWidget v-bind="$attrs" title="Выплаты по активам">
    <div class="pa">
      <div class="pa__head">
        <div>
          <span>Всего получено</span>
          <b><CvNumber :value="total" :format="fmt" /></b>
        </div>
        <p v-if="rows.length > 3" class="pa__note">
          Три крупнейших плательщика — {{ pct(topShare, { sign: false, digits: 0 }) }} выплат
        </p>
      </div>

      <ol v-if="rows.length" class="pa__list" @pointerleave="hover = null">
        <li
          v-for="(r, i) in shown"
          :key="r.id"
          class="pa__row"
          :class="{ 'is-dim': hover != null && hover !== r.id }"
          :style="{ '--i': i }"
          @pointerenter="hover = r.id"
        >
          <div class="pa__line">
            <span class="pa__name"><b>{{ r.name }}</b><small v-if="r.ticker && r.ticker !== r.name">{{ r.ticker }}</small></span>
            <span class="pa__val cv-num">{{ money(r.total) }}</span>
          </div>
          <div class="pa__track" :title="r.parts.filter((p) => p.value).map((p) => `${p.label}: ${money(p.value)}`).join(' · ')">
            <div class="pa__rail">
              <div class="pa__fill" :style="{ width: `${(r.total / max) * 100}%` }">
                <i
                  v-for="p in r.parts.filter((p) => p.value > 0)"
                  :key="p.key"
                  :style="{ flexGrow: p.value, background: PAYOUT_COLORS[p.key] }"
                />
              </div>
            </div>
            <span class="pa__share">{{ pct((r.total / (total || 1)) * 100, { sign: false }) }}</span>
          </div>
        </li>
      </ol>
      <p v-else class="pa__empty">Выплат пока не было</p>

      <div class="pa__foot">
        <div v-if="usedKeys.length > 1" class="cv-legend">
          <span v-for="k in usedKeys" :key="k.key" class="cv-legend__item">
            <i class="cv-legend__sw" :style="{ background: PAYOUT_COLORS[k.key] }" />{{ k.label }}
          </span>
        </div>
        <button v-if="rows.length > LIMIT" type="button" class="cv-btn cv-btn--ghost cv-btn--sm" @click="expanded = !expanded">
          {{ expanded ? 'Свернуть' : `Все ${rows.length} ${plural(rows.length, 'актив', 'актива', 'активов')}` }}
        </button>
      </div>
    </div>
  </CvWidget>
</template>

<style scoped>
.pa { display: flex; flex-direction: column; gap: 14px; min-width: 0; height: 100%; }
.pa__head { display: flex; align-items: flex-end; justify-content: space-between; gap: 8px 16px; flex-wrap: wrap; }
.pa__head div { display: flex; flex-direction: column; gap: 4px; }
.pa__head div > span { font-size: 12px; color: var(--cv-mut); }
.pa__head b { font-family: var(--cv-display); font-size: 22px; font-weight: 600; letter-spacing: -0.02em; color: var(--cv-ink); }
.pa__note { margin: 0; font-size: 12px; color: var(--cv-dim); }

.pa__list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.pa__row {
  padding: 7px 10px; margin: 0 -10px; border-radius: 10px; transition: opacity .2s, background .2s;
  animation: pa-in .6s var(--cv-ease) backwards; animation-delay: calc(var(--i) * 30ms + 60ms);
}
.pa__row:hover { background: var(--cv-hover); }
.pa__row.is-dim { opacity: .45; }
.pa__line { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 7px; }
.pa__name { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
.pa__name b { font-size: 13px; font-weight: 550; color: var(--cv-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pa__name small { font-size: 11.5px; color: var(--cv-dim); flex: none; }
.pa__val { font-size: 13px; font-weight: 550; color: var(--cv-ink); white-space: nowrap; }
.pa__track { display: flex; align-items: center; gap: 10px; }
.pa__rail { flex: 1; min-width: 0; }
.pa__fill {
  display: flex; gap: 2px; height: 6px; min-width: 4px; border-radius: 99px; overflow: hidden;
  transform-origin: left; animation: pa-grow .8s var(--cv-ease) backwards; animation-delay: calc(var(--i) * 30ms + 140ms);
}
.pa__fill i { display: block; flex-basis: 0; min-width: 2px; }
.pa__share { flex: none; width: 44px; text-align: right; font-size: 11.5px; color: var(--cv-dim); font-variant-numeric: tabular-nums; }

.pa__foot { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-top: auto; }
.pa__empty { margin: 0; padding: 40px 0; text-align: center; color: var(--cv-mut); font-size: 13px; }

@keyframes pa-in { from { opacity: 0; transform: translateY(4px); } }
@keyframes pa-grow { from { transform: scaleX(0); } }
@media (prefers-reduced-motion: reduce) {
  .pa__row, .pa__fill { animation: none; }
}
</style>
