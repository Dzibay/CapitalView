<script setup>
/**
 * Календарь месяца: в ячейке — сумма дня в ₽ и до двух выплат, остальные «+N».
 * Клик по дню фильтрует список выплат рядом, повторный клик — снимает фильтр.
 */
import { computed } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import CvWidget from '../ui/CvWidget.vue'
import { axisMoney, money } from '../format'
import { PAYOUT_KINDS, MONTHS } from './payoutTypes'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  /** события выбранного месяца */
  events: { type: Array, default: () => [] },
  year: { type: Number, required: true },
  month: { type: Number, required: true },
  day: { type: Number, default: null },
})
const emit = defineEmits(['prev', 'next', 'today', 'update:day'])

const WEEK = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
const now = new Date()
const isCurrent = computed(() => now.getFullYear() === props.year && now.getMonth() === props.month)

const cells = computed(() => {
  const first = new Date(props.year, props.month, 1)
  const days = new Date(props.year, props.month + 1, 0).getDate()
  const lead = (first.getDay() + 6) % 7
  const list = Array.from({ length: lead }, (_, i) => ({ key: `e${i}`, empty: true }))
  for (let d = 1; d <= days; d++) {
    const items = props.events.filter((e) => e.date.getDate() === d).sort((a, b) => (b.rub || 0) - (a.rub || 0))
    const total = items.reduce((s, e) => s + (e.rub || 0), 0)
    const date = new Date(props.year, props.month, d)
    list.push({
      key: d,
      day: d,
      items,
      total,
      incomplete: items.some((e) => e.rub == null),
      weekend: date.getDay() === 0 || date.getDay() === 6,
      isToday: isCurrent.value && now.getDate() === d,
      isPast: date < new Date(now.getFullYear(), now.getMonth(), now.getDate()),
      allReceived: items.length > 0 && items.every((e) => e.received),
    })
  }
  while (list.length % 7) list.push({ key: `t${list.length}`, empty: true })
  return list
})

const pick = (c) => {
  if (c.empty || !c.items.length) return
  emit('update:day', props.day === c.day ? null : c.day)
}
</script>

<template>
  <CvWidget v-bind="$attrs" :title="`${MONTHS[month]} ${year}`">
    <template #actions>
      <button v-if="!isCurrent" type="button" class="cv-btn cv-btn--ghost cv-btn--sm" @click="emit('today')">Сегодня</button>
      <div class="pcal__nav">
        <button type="button" class="cv-btn cv-btn--ghost cv-btn--sm cv-btn--icon" aria-label="Предыдущий месяц" @click="emit('prev')">
          <ChevronLeft :size="16" />
        </button>
        <button type="button" class="cv-btn cv-btn--ghost cv-btn--sm cv-btn--icon" aria-label="Следующий месяц" @click="emit('next')">
          <ChevronRight :size="16" />
        </button>
      </div>
    </template>

    <div class="pcal">
      <div class="pcal__week" aria-hidden="true">
        <span v-for="(w, i) in WEEK" :key="w" :class="{ 'is-we': i > 4 }">{{ w }}</span>
      </div>
      <div class="pcal__grid" role="grid" :aria-label="`Выплаты: ${MONTHS[month]} ${year}`">
        <div
          v-for="(c, i) in cells"
          :key="`${year}-${month}-${c.key}`"
          class="pcal__cell"
          :class="{
            'is-empty': c.empty,
            'has-ev': c.items?.length,
            'is-today': c.isToday,
            'is-past': c.isPast,
            'is-we': c.weekend,
            'is-sel': day != null && c.day === day,
            'is-off': day != null && c.day !== day && !c.empty,
          }"
          :style="{ '--i': i }"
          role="gridcell"
          :tabindex="c.items?.length ? 0 : -1"
          @click="pick(c)"
          @keydown.enter.prevent="pick(c)"
        >
          <template v-if="!c.empty">
            <div class="pcal__top">
              <span class="pcal__num">{{ c.day }}</span>
              <span v-if="c.total > 0" class="pcal__sum cv-num" :class="{ 'is-rec': c.allReceived }" :title="money(c.total)">
                {{ axisMoney(c.total) }}{{ c.total < 1000 ? ' ₽' : '' }}{{ c.incomplete ? '*' : '' }}
              </span>
            </div>
            <ul v-if="c.items.length" class="pcal__ev">
              <li v-for="e in c.items.slice(0, 2)" :key="e.id" :class="{ 'is-fc': e.forecast, 'is-rec': e.received }">
                <i :style="{ background: PAYOUT_KINDS[e.kind].color }" />
                <span>{{ e.ticker || e.name }}</span>
              </li>
              <li v-if="c.items.length > 2" class="pcal__more">+{{ c.items.length - 2 }}</li>
            </ul>
            <span v-if="c.items.length" class="pcal__dots" aria-hidden="true">
              <i v-for="e in c.items.slice(0, 3)" :key="e.id" :style="{ background: PAYOUT_KINDS[e.kind].color }" />
            </span>
          </template>
        </div>
      </div>
    </div>
  </CvWidget>
</template>

<style scoped>
.pcal { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.pcal__nav { display: flex; gap: 2px; }
.pcal__week { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; }
.pcal__week span { padding: 0 8px; font-size: 11px; font-weight: 550; letter-spacing: .04em; text-transform: uppercase; color: var(--cv-dim); }
.pcal__week span.is-we { color: rgba(255, 255, 255, .22); }

.pcal__grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; }
.pcal__cell {
  position: relative; display: flex; flex-direction: column; gap: 6px; min-width: 0; min-height: 92px;
  padding: 8px; border-radius: 10px; background: rgba(255, 255, 255, .018);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .035);
  transition: background .2s, box-shadow .2s, opacity .2s;
  animation: pcal-in .5s var(--cv-ease) backwards; animation-delay: calc(var(--i) * 8ms + 60ms);
}
.pcal__cell.is-empty { background: transparent; box-shadow: none; }
.pcal__cell.is-we:not(.is-empty) { background: rgba(255, 255, 255, .008); }
.pcal__cell.has-ev { cursor: pointer; background: rgba(115, 129, 255, .045); box-shadow: inset 0 0 0 1px rgba(115, 129, 255, .1); }
.pcal__cell.has-ev:hover { background: rgba(115, 129, 255, .09); box-shadow: inset 0 0 0 1px rgba(115, 129, 255, .22); }
.pcal__cell.has-ev:focus-visible { outline: none; box-shadow: inset 0 0 0 1px var(--cv-accent); }
.pcal__cell.is-sel { background: rgba(115, 129, 255, .14); box-shadow: inset 0 0 0 1px var(--cv-accent-line); }
.pcal__cell.is-off { opacity: .45; }
.pcal__cell.is-today .pcal__num { background: var(--cv-accent); color: #fff; }

.pcal__top { display: flex; align-items: center; justify-content: space-between; gap: 4px; min-width: 0; }
.pcal__num {
  display: inline-grid; place-items: center; min-width: 22px; height: 22px; padding: 0 5px; border-radius: 7px;
  font-size: 12px; font-weight: 550; color: var(--cv-ink-2); font-variant-numeric: tabular-nums;
}
.pcal__cell.is-past:not(.has-ev) .pcal__num { color: var(--cv-dim); }
.pcal__sum { font-size: 11.5px; font-weight: 600; color: var(--cv-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pcal__sum.is-rec { color: var(--cv-up); }

.pcal__ev { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.pcal__ev li { display: flex; align-items: center; gap: 6px; min-width: 0; font-size: 11.5px; color: var(--cv-ink-2); }
.pcal__ev li.is-fc { color: var(--cv-mut); }
.pcal__ev li.is-fc i { opacity: .45; }
.pcal__ev i { width: 6px; height: 6px; flex: none; border-radius: 2px; }
.pcal__ev span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pcal__more { padding-left: 12px; color: var(--cv-dim) !important; }
.pcal__dots { display: none; }

@keyframes pcal-in { from { opacity: 0; transform: translateY(3px); } }

@media (max-width: 1000px) {
  .pcal__cell { min-height: 74px; }
  .pcal__ev { display: none; }
  .pcal__dots { display: flex; gap: 3px; margin-top: auto; }
  .pcal__dots i { width: 5px; height: 5px; border-radius: 50%; }
}
@media (max-width: 768px) {
  .pcal__week span { padding: 0; text-align: center; font-size: 10px; }
  .pcal__grid { gap: 3px; }
  .pcal__cell { min-height: 52px; padding: 5px 3px; gap: 3px; align-items: center; }
  .pcal__top { flex-direction: column; gap: 2px; }
  .pcal__num { min-width: 20px; height: 20px; font-size: 11.5px; }
  .pcal__sum { font-size: 9.5px; max-width: 100%; }
  .pcal__dots { margin-top: 0; }
}
@media (prefers-reduced-motion: reduce) { .pcal__cell { animation: none; } }
</style>
