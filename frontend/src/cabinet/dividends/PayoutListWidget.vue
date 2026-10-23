<script setup>
/**
 * Выплаты месяца списком по датам: статус (получено / ожидается / прогноз), сумма в валюте выплаты,
 * доходность. Если в календаре выбран день — только его выплаты.
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Check, X } from 'lucide-vue-next'
import CvWidget from '../ui/CvWidget.vue'
import { money, moneyIn, pct, plural } from '../format'
import { PAYOUT_KINDS, MONTHS_IN, MONTHS_GEN, MONTHS_SHORT } from './payoutTypes'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  events: { type: Array, default: () => [] },
  month: { type: Number, required: true },
  day: { type: Number, default: null },
})
const emit = defineEmits(['update:day'])
const router = useRouter()

const shown = computed(() =>
  [...props.events]
    .filter((e) => props.day == null || e.date.getDate() === props.day)
    .sort((a, b) => a.date - b.date || (b.rub || 0) - (a.rub || 0)),
)
const total = computed(() => shown.value.reduce((s, e) => s + (e.rub || 0), 0))
const title = computed(() => (props.day != null ? `Выплаты ${props.day} ${MONTHS_GEN[props.month]}` : `Выплаты в ${MONTHS_IN[props.month]}`))

const status = (e) => (e.received ? 'получено' : e.forecast ? 'прогноз' : 'ожидается')
const isRub = (c) => !c || /^RUB|^RUR/i.test(c)
const open = (e) => e.assetId != null && router.push(`/assets/${e.assetId}`)
</script>

<template>
  <CvWidget v-bind="$attrs" :title="title">
    <template #actions>
      <button v-if="day != null" type="button" class="cv-btn cv-btn--ghost cv-btn--sm pl__reset" @click="emit('update:day', null)">
        Весь месяц <X :size="13" />
      </button>
    </template>

    <div class="pl">
      <p class="pl__sum">
        <b class="cv-num">{{ money(total) }}</b>
        <span>{{ shown.length }} {{ plural(shown.length, 'выплата', 'выплаты', 'выплат') }}</span>
      </p>

      <ul v-if="shown.length" class="pl__list">
        <li v-for="(e, i) in shown" :key="e.id" :style="{ '--i': i }">
          <button type="button" class="pl__row" :class="{ 'is-fc': e.forecast }" @click="open(e)">
            <span class="pl__date">
              <b class="cv-num">{{ e.date.getDate() }}</b>
              <small>{{ MONTHS_SHORT[e.date.getMonth()] }}</small>
            </span>
            <span class="pl__what">
              <b>{{ e.name }}</b>
              <small>
                <i class="pl__sw" :style="{ background: PAYOUT_KINDS[e.kind].color }" />
                {{ PAYOUT_KINDS[e.kind].one }}
                <template v-if="e.yield != null"> · {{ pct(e.yield, { sign: false, digits: 2 }) }}</template>
              </small>
            </span>
            <span class="pl__amt">
              <b class="cv-num">{{ moneyIn(e.amount, e.currency, { digits: 2 }) }}</b>
              <small :class="{ 'is-rec': e.received }">
                <Check v-if="e.received" :size="12" :stroke-width="2.5" />
                {{ status(e) }}<template v-if="!isRub(e.currency) && e.rub != null"> · {{ money(e.rub) }}</template>
              </small>
            </span>
          </button>
        </li>
      </ul>
      <p v-else class="pl__empty">В этом месяце выплат нет</p>
    </div>
  </CvWidget>
</template>

<style scoped>
.pl { display: flex; flex-direction: column; gap: 12px; min-width: 0; height: 100%; }
.pl__reset { gap: 5px; }
.pl__sum { display: flex; align-items: baseline; gap: 10px; margin: 0; }
.pl__sum b { font-family: var(--cv-display); font-size: 22px; font-weight: 600; letter-spacing: -0.02em; color: var(--cv-ink); }
.pl__sum span { font-size: 12.5px; color: var(--cv-mut); }

.pl__list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; max-height: 620px; overflow-y: auto; scrollbar-width: thin; }
.pl__list li { animation: pl-in .5s var(--cv-ease) backwards; animation-delay: calc(var(--i) * 25ms + 40ms); }
.pl__list li + li .pl__row { box-shadow: inset 0 1px 0 var(--cv-line); }
.pl__row {
  display: grid; grid-template-columns: 34px minmax(0, 1fr) auto; align-items: center; gap: 12px;
  width: 100%; padding: 9px 8px; border: 0; border-radius: 10px; background: transparent;
  text-align: left; cursor: pointer; transition: background .2s;
}
.pl__row:hover { background: var(--cv-hover); box-shadow: none !important; }
.pl__date { display: flex; flex-direction: column; align-items: center; line-height: 1.1; }
.pl__date b { font-family: var(--cv-display); font-size: 17px; font-weight: 500; color: var(--cv-ink); }
.pl__date small { font-size: 10.5px; color: var(--cv-dim); }
.pl__what { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.pl__what b { font-size: 13px; font-weight: 550; color: var(--cv-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pl__what small { display: flex; align-items: center; gap: 6px; font-size: 11.5px; color: var(--cv-dim); white-space: nowrap; overflow: hidden; }
.pl__sw { width: 7px; height: 7px; flex: none; border-radius: 2px; }
.pl__row.is-fc .pl__sw { opacity: .45; }
.pl__amt { display: flex; flex-direction: column; align-items: flex-end; gap: 3px; }
.pl__amt b { font-size: 13px; font-weight: 550; color: var(--cv-ink); white-space: nowrap; }
.pl__row.is-fc .pl__amt b { color: var(--cv-ink-2); }
.pl__amt small { display: inline-flex; align-items: center; gap: 3px; font-size: 11px; color: var(--cv-dim); white-space: nowrap; }
.pl__amt small.is-rec { color: var(--cv-up); }
.pl__empty { flex: 1; display: grid; place-items: center; min-height: 140px; margin: 0; font-size: 13px; color: var(--cv-mut); border-radius: 12px; border: 1px dashed var(--cv-line-2); }

@keyframes pl-in { from { opacity: 0; transform: translateY(3px); } }
@media (prefers-reduced-motion: reduce) { .pl__list li { animation: none; } }
</style>
