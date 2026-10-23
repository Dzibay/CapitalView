<script setup>
/**
 * Динамика прибыли: накопленный P&L по дням, период и изменение за период.
 * Наведение показывает прибыль на дату, выделение — изменение за отрезок.
 */
import { computed, ref, watch } from 'vue'
import { bisectLeft, bisectRight } from 'd3-array'
import CvWidget from '../ui/CvWidget.vue'
import CvNumber from '../ui/CvNumber.vue'
import CvDelta from '../ui/CvDelta.vue'
import CvSegmented from '../ui/CvSegmented.vue'
import CapitalChart from '../charts/CapitalChart.vue'
import { money, dateLong, dateShort } from '../format'
import { SERIES } from '../palette'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  /** expandPortfolioHistoryForCharts(...) */
  history: { type: Object, required: true },
})

const DAY = 86400000
const PERIODS = [
  { value: '3m', label: '3М' },
  { value: '6m', label: '6М' },
  { value: '1y', label: '1Г' },
  { value: 'all', label: 'Всё' },
]
const PERIOD_TEXT = { '3m': 'за 3 месяца', '6m': 'за полгода', '1y': 'за год', all: 'за всё время' }
const period = ref('1y')

const dates = computed(() => (props.history.labels || []).map((l) => Date.parse(l)))
const pnl = computed(() => {
  const p = props.history.data_pnl
  const v = props.history.data_value || []
  const inv = props.history.data_invested || []
  if (p?.length === v.length) return p
  return v.map((x, i) => x - (inv[i] || 0))
})
const hasData = computed(() => dates.value.length > 1)

const zoom = ref(null)
const selection = ref(null)
const hoverIdx = ref(null)
watch([period, zoom], () => { selection.value = null })

const range = computed(() => {
  const d = dates.value
  if (!d.length) return [0, 1]
  if (zoom.value) return zoom.value
  const last = d[d.length - 1]
  const end = new Date(last)
  const back = (m) => Date.UTC(end.getUTCFullYear(), end.getUTCMonth() - m, end.getUTCDate())
  const t0 = { '3m': back(3), '6m': back(6), '1y': back(12), all: d[0] }[period.value]
  return [Math.min(Math.max(d[0], t0), last - DAY), last]
})
const segValue = computed({
  get: () => (zoom.value ? '' : period.value),
  set: (v) => { zoom.value = null; period.value = v },
})

const startIdx = computed(() => Math.min(dates.value.length - 1, bisectLeft(dates.value, range.value[0])))
const endIdx = computed(() => Math.max(startIdx.value, bisectRight(dates.value, range.value[1]) - 1))

const series = computed(() => [{ key: 'pnl', label: 'Рост стоимости', values: pnl.value, color: SERIES[0], kind: 'area' }])

const state = computed(() => {
  const p = pnl.value
  const d = dates.value
  if (selection.value) {
    const { i0, i1 } = selection.value
    return { label: 'Выделенный период', value: p[i1], change: p[i1] - p[i0], suffix: `${dateShort(d[i0])} — ${dateShort(d[i1])}` }
  }
  if (hoverIdx.value != null) {
    const i = hoverIdx.value
    return { label: dateLong(d[i]), value: p[i], change: p[i] - p[startIdx.value], suffix: `с ${dateShort(d[startIdx.value])}` }
  }
  const a = startIdx.value
  const b = endIdx.value
  return { label: 'Рост стоимости над вложенным', value: p[b] || 0, change: (p[b] || 0) - (p[a] || 0), suffix: zoom.value ? 'за выбранный отрезок' : PERIOD_TEXT[period.value] }
})

const fmt = (v) => money(v, { sign: true })
</script>

<template>
  <CvWidget v-bind="$attrs" title="Динамика прибыли">
    <template #actions>
      <button v-if="zoom" type="button" class="cv-btn cv-btn--sm cv-btn--ghost" @click="zoom = null">Сбросить зум</button>
      <CvSegmented v-model="segValue" :options="PERIODS" size="sm" aria-label="Период прибыли" />
    </template>

    <div class="pc">
      <div class="pc__head">
        <span class="pc__label">{{ state.label }}</span>
        <div class="pc__value">
          <CvNumber :value="state.value" :format="fmt" :duration="hoverIdx != null ? 300 : 900" :stagger="hoverIdx != null ? 3 : 22" />
        </div>
        <div class="pc__change">
          <CvDelta :value="state.change" kind="money" />
          <span>{{ state.suffix }}</span>
        </div>
      </div>

      <CapitalChart
        v-if="hasData"
        v-model:selection="selection"
        :dates="dates"
        :series="series"
        :range="range"
        :height="250"
        aria-label="График накопленной прибыли. Стрелки влево и вправо перемещают курсор."
        @hover="hoverIdx = $event"
        @zoom="zoom = $event"
      >
        <template #tooltip="{ index }">
          <div class="cv-tip__date">{{ dateLong(dates[index]) }}</div>
          <div class="cv-tip__row">
            <span><i class="cv-tip__sw" :style="{ background: SERIES[0] }" />Рост стоимости</span>
            <b :class="pnl[index] > 0 ? 'cv-up' : pnl[index] < 0 ? 'cv-down' : ''">{{ money(pnl[index], { sign: true }) }}</b>
          </div>
        </template>
      </CapitalChart>
      <p v-else class="pc__empty">График появится, когда накопится история портфеля.</p>
    </div>
  </CvWidget>
</template>

<style scoped>
.pc { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.pc__head { display: flex; flex-direction: column; gap: 4px; }
.pc__label { font-size: 12.5px; color: var(--cv-mut); }
.pc__value { font-family: var(--cv-display); font-size: 28px; font-weight: 600; letter-spacing: -0.03em; color: var(--cv-ink); line-height: 1.15; }
.pc__change { display: flex; align-items: center; gap: 8px; font-size: 12.5px; color: var(--cv-dim); }
.pc__empty { display: grid; place-items: center; height: 250px; color: var(--cv-mut); font-size: 13px; text-align: center; }
</style>
