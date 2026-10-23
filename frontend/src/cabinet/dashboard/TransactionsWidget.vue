<script setup>
/** Последние операции выбранного портфеля (включая дочерние), сгруппированные по дням. */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { History, ArrowRight, ArrowDownLeft, ArrowUpRight, Layers } from 'lucide-vue-next'
import CvWidget from '../ui/CvWidget.vue'
import { dateShort, moneyIn, num } from '../format'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  transactions: { type: Array, default: () => [] },
  assets: { type: Array, default: () => [] },
  limit: { type: Number, default: 6 },
})

const router = useRouter()

const TYPES = {
  'Покупка': { label: 'Покупка', icon: ArrowDownLeft, out: true },
  'Продажа': { label: 'Продажа', icon: ArrowUpRight, out: false },
  'Амортизация': { label: 'Амортизация', icon: Layers, out: false },
}

function dayLabel(d) {
  const date = new Date(d)
  if (Number.isNaN(date.getTime())) return '—'
  const today = new Date()
  const start = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()
  const diff = Math.round((start(today) - start(date)) / 864e5)
  if (diff === 0) return 'Сегодня'
  if (diff === 1) return 'Вчера'
  const s = dateShort(date)
  return date.getFullYear() === today.getFullYear() ? s : `${s} ${date.getFullYear()}`
}

const rows = computed(() =>
  (props.transactions || []).slice(0, props.limit).map((tx, i) => {
    const t = TYPES[tx.transaction_type] || { label: tx.transaction_type || 'Операция', icon: History, out: false }
    const qty = Number(tx.quantity) || 0
    const price = Number(tx.price) || 0
    const cur = tx.currency_ticker || 'RUB'
    const total = qty * price
    return {
      i,
      key: tx.transaction_id ?? tx.id ?? i,
      assetId: tx.asset_id,
      name: tx.asset_name || tx.ticker || '—',
      ticker: tx.ticker || '',
      day: dayLabel(tx.transaction_date),
      type: t,
      qty,
      price: moneyIn(price, cur, { digits: price < 100 ? 2 : 0 }),
      amount: moneyIn(t.out ? -total : total, cur, { sign: true, digits: total < 100 ? 2 : 0 }),
    }
  }),
)

/** операции уже отсортированы по дате — соседние с одной датой образуют группу */
const groups = computed(() => {
  const out = []
  for (const r of rows.value) {
    const last = out[out.length - 1]
    if (last && last.day === r.day) last.rows.push(r)
    else out.push({ day: r.day, rows: [r] })
  }
  return out
})

const initials = (r) => (r.ticker || r.name).replace(/[^A-Za-zА-Яа-я0-9]/g, '').slice(0, 4).toUpperCase()
const openAsset = (r) => r.assetId != null && router.push(`/assets/${r.assetId}`)
</script>

<template>
  <CvWidget v-bind="$attrs" title="Последние операции">
    <template #actions>
      <RouterLink to="/transactions" class="cv-btn cv-btn--ghost cv-btn--sm tx__all">
        Все операции <ArrowRight :size="14" />
      </RouterLink>
    </template>

    <div class="tx">
      <div v-if="groups.length" class="tx__list">
        <section v-for="g in groups" :key="g.day" class="tx__group">
          <h4 class="tx__day">{{ g.day }}</h4>
          <button
            v-for="r in g.rows"
            :key="r.key"
            type="button"
            class="tx__row"
            :style="{ '--i': r.i }"
            @click="openAsset(r)"
          >
            <span class="tx__asset">
              <span class="tx__ava">{{ initials(r) }}</span>
              <span class="tx__name">
                <b>{{ r.name }}</b>
                <small>{{ r.ticker }}<span class="tx__type-inline"> · {{ r.type.label }}</span></small>
              </span>
            </span>
            <span class="tx__type">
              <component :is="r.type.icon" :size="13" :stroke-width="2" />
              {{ r.type.label }}
            </span>
            <span class="tx__qty cv-num">{{ num(r.qty, 4) }} × {{ r.price }}</span>
            <span class="tx__sum cv-num">{{ r.amount }}</span>
          </button>
        </section>
      </div>

      <div v-else class="tx__empty">
        <History :size="22" />
        <b>Операций пока нет</b>
        <p>Добавьте сделку или импортируйте отчёт брокера — она появится здесь.</p>
      </div>
    </div>
  </CvWidget>
</template>

<style scoped>
.tx { container-type: inline-size; min-width: 0; }
.tx__all { gap: 6px; text-decoration: none; }

.tx__list { display: flex; flex-direction: column; gap: 14px; }
.tx__group { display: flex; flex-direction: column; }
.tx__day {
  padding-bottom: 8px; margin-bottom: 2px; border-bottom: 1px solid var(--cv-line);
  font-size: 11px; font-weight: 550; letter-spacing: .08em; text-transform: uppercase; color: var(--cv-dim);
}
.tx__row {
  display: grid; grid-template-columns: minmax(0, 1.7fr) 140px minmax(0, 1fr) 150px; align-items: center; gap: 16px;
  width: calc(100% + 20px); margin: 0 -10px; padding: 9px 10px; border: 0; border-radius: 10px; background: transparent; text-align: left;
  font-size: 13px; color: var(--cv-ink-2); cursor: pointer;
  transition: background .2s;
  animation: tx-in .5s var(--cv-ease) backwards calc(var(--i, 0) * 35ms + 100ms);
}
.tx__row:hover { background: var(--cv-hover); }
@keyframes tx-in { from { opacity: 0; transform: translateY(6px); } }

.tx__asset { display: flex; align-items: center; gap: 12px; min-width: 0; }
.tx__ava {
  display: grid; place-items: center; width: 32px; height: 32px; flex: none; border-radius: 10px;
  font-size: 9.5px; font-weight: 650; letter-spacing: .03em;
  color: var(--cv-ink-2); background: rgba(255, 255, 255, .035); box-shadow: inset 0 0 0 1px var(--cv-line-2);
}
.tx__name { display: flex; flex-direction: column; min-width: 0; }
.tx__name b { font-weight: 550; color: var(--cv-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tx__name small { font-size: 11.5px; color: var(--cv-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tx__type-inline { display: none; }

.tx__type { display: inline-flex; align-items: center; gap: 7px; color: var(--cv-mut); white-space: nowrap; }
.tx__type svg { color: var(--cv-dim); }
.tx__qty { color: var(--cv-mut); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tx__sum { text-align: right; font-weight: 550; color: var(--cv-ink); white-space: nowrap; }

.tx__empty {
  display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 28px 12px; text-align: center;
  color: var(--cv-mut); border-radius: 12px; border: 1px dashed var(--cv-line-2);
}
.tx__empty b { font-size: 14px; color: var(--cv-ink); }
.tx__empty p { font-size: 13px; max-width: 320px; }

@container (max-width: 760px) {
  .tx__row { grid-template-columns: minmax(0, 1fr) 120px 130px; }
  .tx__qty { display: none; }
}
@container (max-width: 520px) {
  .tx__row { grid-template-columns: minmax(0, 1fr) auto; gap: 10px; }
  .tx__type { display: none; }
  .tx__type-inline { display: inline; }
}
</style>
