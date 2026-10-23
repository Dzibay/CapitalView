<script setup>
/**
 * Крупнейшие позиции: доля в портфеле, доходность с покупки и цена за последний месяц.
 * Одна бумага из нескольких подпортфелей показывается одной строкой.
 */
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight } from 'lucide-vue-next'
import { scaleLinear } from 'd3-scale'
import { line as d3line, area as d3area, curveMonotoneX } from 'd3-shape'
import CvWidget from '../ui/CvWidget.vue'
import CvSegmented from '../ui/CvSegmented.vue'
import { usePriceTrail } from '../charts/usePriceTrail'
import { effectiveUnitPriceInCurrency } from '../../utils/effectiveAssetPrice'
import { money, pct } from '../format'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  assets: { type: Array, default: () => [] },
  limit: { type: Number, default: 6 },
})
const router = useRouter()

const sort = ref('share')
const SORTS = [
  { value: 'share', label: 'Доля' },
  { value: 'return', label: 'Доходность' },
]

const items = computed(() => {
  const map = new Map()
  for (const a of props.assets) {
    const lev = Number(a.leverage || 1) || 1
    const value = (Number(a.quantity || 0) * effectiveUnitPriceInCurrency(a) * Number(a.currency_rate_to_rub || 1)) / lev
    if (!(value > 0)) continue
    const key = a.asset_id ?? a.ticker ?? a.name
    const profit = Number(a.profit_rub ?? a.profit ?? 0) || 0
    const cur = map.get(key)
    if (cur) {
      cur.value += value
      cur.profit += profit
    } else {
      map.set(key, { key, id: a.asset_id, name: a.name || a.ticker || '—', ticker: a.ticker || '', custom: !!a.is_custom, value, profit })
    }
  }
  return [...map.values()]
})
const total = computed(() => items.value.reduce((s, i) => s + i.value, 0) || 1)

const rows = computed(() => {
  const list = items.value.map((i) => {
    const invested = i.value - i.profit
    return { ...i, share: (i.value / total.value) * 100, ret: invested > 0 ? (i.profit / invested) * 100 : 0 }
  })
  list.sort(sort.value === 'share' ? (a, b) => b.value - a.value : (a, b) => b.ret - a.ret)
  return list.slice(0, props.limit)
})
const maxShare = computed(() => Math.max(1, ...rows.value.map((r) => r.share)))
const coverage = computed(() => {
  const top = [...items.value].sort((a, b) => b.value - a.value).slice(0, props.limit)
  return (top.reduce((s, i) => s + i.value, 0) / total.value) * 100
})

// мини-графики цены за месяц
const { trails, ensure } = usePriceTrail()
watch(rows, (list) => ensure(list.filter((r) => !r.custom).map((r) => r.id)), { immediate: true })

const W = 76
const H = 26
function trail(r) {
  const v = trails[r.id]
  if (!v || v.length < 2) return null
  const x = scaleLinear().domain([0, v.length - 1]).range([1, W - 3])
  let lo = Math.min(...v)
  let hi = Math.max(...v)
  if (lo === hi) { lo -= 1; hi += 1 }
  const y = scaleLinear().domain([lo, hi]).range([H - 3, 3])
  return {
    line: d3line().x((_, i) => x(i)).y(y).curve(curveMonotoneX)(v),
    area: d3area().x((_, i) => x(i)).y0(H).y1(y).curve(curveMonotoneX)(v),
    end: { x: x(v.length - 1), y: y(v[v.length - 1]) },
    change: (v[v.length - 1] / v[0] - 1) * 100,
  }
}
const trailsByKey = computed(() => Object.fromEntries(rows.value.map((r) => [r.key, r.custom ? null : trail(r)])))

const initials = (r) => (r.ticker || r.name).replace(/[^A-Za-zА-Яа-я0-9]/g, '').slice(0, 4).toUpperCase()
const open = (r) => r.id != null && router.push(`/assets/${r.id}`)
</script>

<template>
  <CvWidget
    v-bind="$attrs"
    title="Крупнейшие позиции"
    :subtitle="items.length > limit ? `${limit} из ${items.length} · ${pct(coverage, { sign: false, digits: 0 })} портфеля` : ''"
  >
    <template #actions>
      <CvSegmented v-model="sort" :options="SORTS" size="sm" aria-label="Сортировка" />
    </template>

    <div class="tp">
      <div class="tp__head" aria-hidden="true">
        <span>Актив</span>
        <span class="tp__c-trail">Месяц</span>
        <span class="tp__c-share">Доля</span>
        <span class="tp__c-ret">С покупки</span>
      </div>
      <TransitionGroup tag="ul" name="tp-row" class="tp__list">
        <li v-for="(r, i) in rows" :key="r.key" :style="{ '--i': i }">
          <button type="button" class="tp__row" @click="open(r)">
            <span class="tp__asset">
              <span class="tp__ava">{{ initials(r) }}</span>
              <span class="tp__name">
                <b>{{ r.name }}</b>
                <small class="cv-num">{{ money(r.value) }}</small>
              </span>
            </span>

            <span class="tp__c-trail">
              <svg v-if="trailsByKey[r.key]" :width="W" :height="H" :viewBox="`0 0 ${W} ${H}`" class="tp__trail" role="img" :aria-label="`Цена за месяц ${pct(trailsByKey[r.key].change)}`">
                <path :d="trailsByKey[r.key].area" class="tp__trail-area" />
                <path :d="trailsByKey[r.key].line" class="tp__trail-line" />
                <circle :cx="trailsByKey[r.key].end.x" :cy="trailsByKey[r.key].end.y" r="2.25" class="tp__trail-end" />
              </svg>
              <i v-else-if="!r.custom && !(r.id in trails)" class="tp__trail-skel" />
              <span v-else class="tp__trail-none">—</span>
            </span>

            <span class="tp__c-share">
              <b class="cv-num">{{ pct(r.share, { sign: false }) }}</b>
              <span class="tp__share-bar"><i :style="{ '--w': r.share / maxShare }" /></span>
            </span>

            <span class="tp__c-ret cv-num" :class="r.ret > 0 ? 'cv-up' : r.ret < 0 ? 'cv-down' : ''">
              {{ pct(r.ret) }}
            </span>
          </button>
        </li>
      </TransitionGroup>

      <button type="button" class="tp__more" @click="router.push('/assets')">
        Все активы <ArrowRight :size="14" />
      </button>
    </div>
  </CvWidget>
</template>

<style scoped>
.tp { display: flex; flex-direction: column; height: 100%; min-width: 0; container-type: inline-size; }

.tp__head, .tp__row {
  display: grid; grid-template-columns: minmax(0, 1fr) 76px 64px 68px; align-items: center; gap: 12px;
}
.tp__head { padding: 0 8px 10px; border-bottom: 1px solid var(--cv-line); font-size: 11px; color: var(--cv-dim); }
.tp__head > span { font-size: 11px; font-weight: 500; color: var(--cv-dim); }
.tp__head .tp__c-share, .tp__head .tp__c-ret { text-align: right; }
.tp__head .tp__c-trail { height: auto; }

.tp__list { list-style: none; margin: 4px 0 0; padding: 0; display: flex; flex-direction: column; }
.tp__row {
  width: 100%; padding: 9px 8px; border: 0; border-radius: 10px; background: transparent; text-align: left; cursor: pointer;
  transition: background .2s;
}
.tp__row:hover { background: var(--cv-hover); }

.tp__asset { display: flex; align-items: center; gap: 11px; min-width: 0; }
.tp__ava {
  display: grid; place-items: center; width: 32px; height: 32px; flex: none; border-radius: 9px;
  font-size: 9.5px; font-weight: 650; letter-spacing: .03em; color: var(--cv-ink-2);
  background: rgba(255, 255, 255, .035); box-shadow: inset 0 0 0 1px var(--cv-line-2);
}
.tp__name { display: flex; flex-direction: column; min-width: 0; }
.tp__name b { font-size: 13px; font-weight: 550; color: var(--cv-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tp__name small { font-size: 11.5px; color: var(--cv-dim); }

.tp__c-trail { display: flex; align-items: center; height: 26px; }
.tp__trail { display: block; overflow: visible; }
.tp__trail-line { fill: none; stroke: var(--cv-s1); stroke-width: 1.5; stroke-linejoin: round; stroke-linecap: round; }
.tp__trail-area { fill: var(--cv-s1); opacity: .08; }
.tp__trail-end { fill: var(--cv-s2); stroke: var(--cv-surface-2); stroke-width: 1.5; }
.tp__trail-skel { display: block; width: 76px; height: 2px; border-radius: 2px; background: rgba(255, 255, 255, .06); animation: tp-pulse 1.4s ease-in-out infinite; }
@keyframes tp-pulse { 50% { opacity: .4; } }
.tp__trail-none { font-size: 12px; color: var(--cv-dim); }

.tp__c-share { display: flex; flex-direction: column; align-items: flex-end; gap: 5px; }
.tp__c-share b { font-size: 13px; font-weight: 550; color: var(--cv-ink); }
.tp__share-bar { position: relative; width: 100%; height: 2px; border-radius: 2px; background: rgba(255, 255, 255, .05); overflow: hidden; }
.tp__share-bar i {
  position: absolute; inset: 0; border-radius: inherit; background: rgba(255, 255, 255, .32);
  transform-origin: right center; transform: scaleX(var(--w));
  animation: tp-bar .9s var(--cv-ease) backwards calc(var(--i) * 50ms + 150ms);
  transition: transform .5s var(--cv-ease);
}
@keyframes tp-bar { from { transform: scaleX(0); } }
.tp__c-ret { text-align: right; font-size: 13px; font-weight: 550; color: var(--cv-ink-2); }

.tp__more {
  display: inline-flex; align-items: center; gap: 6px; align-self: flex-start; margin-top: auto; padding: 14px 8px 0;
  border: 0; background: none; color: var(--cv-mut); font-size: 12.5px; font-weight: 550; cursor: pointer;
  transition: color .2s;
}
.tp__more:hover { color: var(--cv-ink); }
.tp__more svg { transition: transform .2s var(--cv-ease); }
.tp__more:hover svg { transform: translateX(2px); }

.tp-row-move { transition: transform .45s var(--cv-ease); }
.tp-row-enter-active { transition: opacity .3s; }
.tp-row-enter-from, .tp-row-leave-to { opacity: 0; }
.tp-row-leave-active { position: absolute; transition: opacity .2s; }

@container (max-width: 420px) {
  .tp__head, .tp__row { grid-template-columns: minmax(0, 1fr) 64px 68px; }
  .tp__c-trail { display: none; }
}
@container (max-width: 340px) {
  .tp__head, .tp__row { grid-template-columns: minmax(0, 1fr) 64px; }
  .tp__c-share { display: none; }
}
</style>
