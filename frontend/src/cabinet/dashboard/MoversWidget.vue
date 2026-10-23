<script setup>
/** Лидеры роста и падения за день + итог дня по портфелю и соотношение растущих/падающих позиций. */
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Activity, ChevronRight } from 'lucide-vue-next'
import CvWidget from '../ui/CvWidget.vue'
import CvSegmented from '../ui/CvSegmented.vue'
import CvDelta from '../ui/CvDelta.vue'
import { moneyIn, pct } from '../format'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  assets: { type: Array, default: () => [] },
  limit: { type: Number, default: 5 },
})

const router = useRouter()
const dir = ref('up')

const rows = computed(() => {
  const byId = new Map()
  for (const a of props.assets || []) {
    const qty = Number(a?.quantity) || 0
    const price = Number(a?.last_price) || 0
    const ch = Number(a?.daily_change)
    if (!price || qty <= 0 || !Number.isFinite(ch) || ch === 0) continue
    const key = a.asset_id ?? a.ticker ?? a.name
    const rate = Number(a.currency_rate_to_rub || 1) || 1
    const lev = Number(a.leverage || 1) || 1
    const prev = byId.get(key)
    if (prev) {
      prev.qty += qty
      prev.change += ch * qty
      prev.changeRub += (ch * qty * rate) / lev
      continue
    }
    byId.set(key, {
      key,
      id: a.asset_id,
      name: a.name || a.ticker || '—',
      ticker: a.ticker || '',
      type: a.type,
      currency: a.currency_ticker || 'RUB',
      qty,
      pct: (ch / price) * 100,
      change: ch * qty,
      changeRub: (ch * qty * rate) / lev,
    })
  }
  return [...byId.values()]
})

const ups = computed(() => rows.value.filter((r) => r.pct > 0).sort((a, b) => b.pct - a.pct))
const downs = computed(() => rows.value.filter((r) => r.pct < 0).sort((a, b) => a.pct - b.pct))
const list = computed(() => (dir.value === 'up' ? ups.value : downs.value).slice(0, props.limit))
const maxAbs = computed(() => Math.max(0.01, ...list.value.map((r) => Math.abs(r.pct))))

const dayTotal = computed(() => rows.value.reduce((s, r) => s + r.changeRub, 0))
const breadth = computed(() => {
  const u = ups.value.length
  const d = downs.value.length
  const t = u + d || 1
  return { u, d, up: (u / t) * 100 }
})

const options = computed(() => [
  { value: 'up', label: `Рост · ${ups.value.length}` },
  { value: 'down', label: `Падение · ${downs.value.length}` },
])

const initials = (r) => (r.ticker || r.name).replace(/[^A-Za-zА-Яа-я0-9]/g, '').slice(0, 4).toUpperCase()
const open = (r) => r.id != null && router.push(`/assets/${r.id}`)
</script>

<template>
  <CvWidget v-bind="$attrs" title="Движение за день" :icon="Activity">
    <div class="mv">
      <div class="mv__day">
        <CvDelta :value="dayTotal" kind="money" :pill="false" class="mv__day-val" />
        <p class="mv__day-meta">
          Портфель за день<template v-if="breadth.u + breadth.d"> · растут {{ breadth.u }}, падают {{ breadth.d }}</template>
        </p>
      </div>

      <CvSegmented v-model="dir" :options="options" size="sm" aria-label="Направление" class="mv__seg" />

      <TransitionGroup v-if="list.length" :key="dir" tag="ul" name="mv-row" class="mv__list" appear>
        <li v-for="(r, i) in list" :key="r.key" :style="{ '--i': i }">
          <button type="button" class="mv__row" :class="dir === 'up' ? 'is-up' : 'is-down'" @click="open(r)">
            <span class="mv__ava">{{ initials(r) }}</span>
            <span class="mv__name">
              <b>{{ r.name }}</b>
              <small>{{ r.ticker }}</small>
            </span>
            <span class="mv__bar" aria-hidden="true"><i :style="{ '--w': Math.abs(r.pct) / maxAbs }" /></span>
            <span class="mv__val">
              <b class="cv-num">{{ pct(r.pct, { digits: 2 }) }}</b>
              <small class="cv-num">{{ moneyIn(r.change, r.currency, { sign: true, digits: Math.abs(r.change) < 100 ? 2 : 0 }) }}</small>
            </span>
            <ChevronRight :size="15" class="mv__chev" />
          </button>
        </li>
      </TransitionGroup>
      <div v-else class="mv__empty">
        {{ dir === 'up' ? 'Сегодня ни одна позиция не выросла' : 'Сегодня ни одна позиция не упала' }}
      </div>
    </div>
  </CvWidget>
</template>

<style scoped>
.mv { display: flex; flex-direction: column; gap: 14px; min-width: 0; height: 100%; container-type: inline-size; }

.mv__day { padding-bottom: 16px; border-bottom: 1px solid var(--cv-line); }
.mv__day-val { font-family: var(--cv-display); font-size: 24px; font-weight: 500; letter-spacing: -0.03em; }
.mv__day-val :deep(svg) { width: 18px; height: 18px; }
.mv__day-meta { margin-top: 6px; font-size: 12.5px; color: var(--cv-mut); }

.mv__seg { align-self: flex-start; }

.mv__list { list-style: none; margin: -4px -8px 0; padding: 0; display: flex; flex-direction: column; }
.mv__row {
  display: grid; grid-template-columns: 34px minmax(0, 1fr) 56px auto 14px; align-items: center; gap: 11px;
  width: 100%; padding: 8px; border: 0; border-radius: 11px; background: transparent; text-align: left; cursor: pointer;
  transition: background .2s;
}
.mv__row:hover { background: var(--cv-hover); }
.mv__ava {
  display: grid; place-items: center; width: 34px; height: 34px; border-radius: 10px;
  font-size: 10px; font-weight: 650; letter-spacing: .03em;
  color: var(--cv-ink-2);
  background: rgba(255, 255, 255, .035);
  box-shadow: inset 0 0 0 1px var(--cv-line-2);
}
.mv__name { display: flex; flex-direction: column; min-width: 0; }
.mv__name b { font-size: 13px; font-weight: 550; color: var(--cv-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mv__name small { font-size: 11.5px; color: var(--cv-dim); }
.mv__bar { position: relative; height: 3px; border-radius: 99px; background: rgba(255, 255, 255, .04); overflow: hidden; }
.mv__bar i {
  position: absolute; inset: 0; border-radius: inherit; transform-origin: left center; transform: scaleX(var(--w));
  animation: mv-bar .9s var(--cv-ease) backwards calc(var(--i) * 60ms + 120ms);
}
@keyframes mv-bar { from { transform: scaleX(0); } }
.mv__bar i { background: rgba(255, 255, 255, .3); }
.mv__val { display: flex; flex-direction: column; align-items: flex-end; min-width: 74px; }
.mv__val b { font-size: 13px; font-weight: 550; }
.is-up .mv__val b { color: var(--cv-up); }
.is-down .mv__val b { color: var(--cv-down); }
.mv__val small { font-size: 11.5px; color: var(--cv-mut); white-space: nowrap; }
.mv__chev { color: var(--cv-dim); opacity: 0; transform: translateX(-4px); transition: opacity .2s, transform .2s var(--cv-ease); }
.mv__row:hover .mv__chev { opacity: 1; transform: none; }

.mv__empty {
  flex: 1; display: grid; place-items: center; min-height: 120px; padding: 12px; text-align: center;
  font-size: 13px; color: var(--cv-mut);
  border-radius: 12px; border: 1px dashed var(--cv-line-2);
}

.mv-row-enter-active { transition: opacity .4s var(--cv-ease), transform .5s var(--cv-ease); transition-delay: calc(var(--i) * 45ms); }
.mv-row-enter-from { opacity: 0; transform: translateY(8px); }

@container (max-width: 340px) {
  .mv__row { grid-template-columns: 34px minmax(0, 1fr) auto; }
  .mv__bar, .mv__chev { display: none; }
}
</style>
