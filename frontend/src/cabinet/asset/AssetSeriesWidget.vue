<script setup>
/**
 * История актива на d3: цена единицы, стоимость позиции или количество.
 * Метрика выбирается переключателем, период — сегментами, наведение показывает значение на дату,
 * выделение мышью — изменение за отрезок.
 */
import { computed, ref, watch } from 'vue'
import { bisectLeft, bisectRight } from 'd3-array'
import CvWidget from '../ui/CvWidget.vue'
import CvNumber from '../ui/CvNumber.vue'
import CvDelta from '../ui/CvDelta.vue'
import CvSegmented from '../ui/CvSegmented.vue'
import CapitalChart from '../charts/CapitalChart.vue'
import { dateLong, dateShort } from '../format'
import { SERIES } from '../palette'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  /** [{ value, label, title, dates: ISO-строки, values, format, axis }] */
  metrics: { type: Array, required: true },
})
const metric = defineModel('metric', { type: String, default: '' })

const DAY = 86400000
const PERIODS = [
  { value: '1m', label: '1М' },
  { value: '3m', label: '3М' },
  { value: '1y', label: '1Г' },
  { value: 'all', label: 'Всё' },
]
const PERIOD_TEXT = { '1m': 'за месяц', '3m': 'за 3 месяца', '1y': 'за год', all: 'за всё время' }
const period = ref('1y')

const current = computed(() => props.metrics.find((m) => m.value === metric.value) || props.metrics[0])
const dates = computed(() => (current.value?.dates || []).map((l) => Date.parse(l)))
const values = computed(() => (current.value?.values || []).map((v) => Number(v) || 0))
const hasData = computed(() => dates.value.length > 1)

const zoom = ref(null)
const selection = ref(null)
const hoverIdx = ref(null)
watch([period, zoom, () => current.value?.value], () => { selection.value = null; hoverIdx.value = null })
watch(() => current.value?.value, () => { zoom.value = null })

const range = computed(() => {
  const d = dates.value
  if (!d.length) return [0, 1]
  if (zoom.value) return zoom.value
  const last = d[d.length - 1]
  const end = new Date(last)
  const back = (m) => Date.UTC(end.getUTCFullYear(), end.getUTCMonth() - m, end.getUTCDate())
  const t0 = { '1m': back(1), '3m': back(3), '1y': back(12), all: d[0] }[period.value]
  return [Math.min(Math.max(d[0], t0), last - DAY), last]
})
const segValue = computed({
  get: () => (zoom.value ? '' : period.value),
  set: (v) => { zoom.value = null; period.value = v },
})

const startIdx = computed(() => Math.min(dates.value.length - 1, bisectLeft(dates.value, range.value[0])))
const endIdx = computed(() => Math.max(startIdx.value, bisectRight(dates.value, range.value[1]) - 1))

const series = computed(() => [{ key: 'v', label: current.value?.title || '', values: values.value, color: SERIES[0], kind: 'area' }])

const relative = (a, b) => (a ? ((b - a) / Math.abs(a)) * 100 : 0)
const state = computed(() => {
  const v = values.value
  const d = dates.value
  let i0 = startIdx.value
  let i1 = endIdx.value
  let label = current.value?.title || ''
  let suffix = zoom.value ? 'за выбранный отрезок' : PERIOD_TEXT[period.value]
  if (selection.value) {
    ;({ i0, i1 } = selection.value)
    label = 'Выделенный период'
    suffix = `${dateShort(d[i0])} — ${dateShort(d[i1])}`
  } else if (hoverIdx.value != null) {
    i1 = hoverIdx.value
    label = dateLong(d[i1])
    suffix = `с ${dateShort(d[i0])}`
  }
  const a = v[i0] || 0
  const b = v[i1] || 0
  return { label, value: b, change: b - a, pct: relative(a, b), suffix }
})

const fmt = (x) => current.value?.format?.(x) ?? String(x)
const fmtChange = (x) => {
  const s = fmt(Math.abs(x))
  return x > 0 ? `+${s}` : x < 0 ? `−${s}` : s
}
</script>

<template>
  <CvWidget v-bind="$attrs" title="История">
    <template #actions>
      <CvSegmented v-if="metrics.length > 1" v-model="metric" :options="metrics" size="sm" aria-label="Что показать на графике" />
      <button v-if="zoom" type="button" class="cv-btn cv-btn--sm cv-btn--ghost" @click="zoom = null">Сбросить зум</button>
      <CvSegmented v-model="segValue" :options="PERIODS" size="sm" aria-label="Период" />
    </template>

    <div class="sw">
      <div class="sw__head">
        <span class="sw__label">{{ state.label }}</span>
        <div class="sw__value">
          <CvNumber :value="state.value" :format="fmt" :duration="hoverIdx != null ? 300 : 900" :stagger="hoverIdx != null ? 3 : 22" />
        </div>
        <div class="sw__change">
          <CvDelta :value="state.pct" />
          <span class="cv-num" :class="state.change > 0 ? 'cv-up' : state.change < 0 ? 'cv-down' : ''">{{ fmtChange(state.change) }}</span>
          <span>{{ state.suffix }}</span>
        </div>
      </div>

      <CapitalChart
        v-if="hasData"
        :key="current.value"
        v-model:selection="selection"
        :dates="dates"
        :series="series"
        :range="range"
        :height="280"
        :axis-format="current.axis"
        :aria-label="`График: ${current.title}. Стрелки влево и вправо перемещают курсор.`"
        @hover="hoverIdx = $event"
        @zoom="zoom = $event"
      >
        <template #tooltip="{ index }">
          <div class="cv-tip__date">{{ dateLong(dates[index]) }}</div>
          <div class="cv-tip__row">
            <span><i class="cv-tip__sw" :style="{ background: SERIES[0] }" />{{ current.title }}</span>
            <b>{{ fmt(values[index]) }}</b>
          </div>
        </template>
      </CapitalChart>
      <p v-else class="sw__empty">Истории пока недостаточно для графика.</p>
    </div>
  </CvWidget>
</template>

<style scoped>
.sw { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.sw__head { display: flex; flex-direction: column; gap: 4px; }
.sw__label { font-size: 12.5px; color: var(--cv-mut); }
.sw__value { font-family: var(--cv-display); font-size: 28px; font-weight: 600; letter-spacing: -0.03em; color: var(--cv-ink); line-height: 1.15; }
.sw__change { display: flex; align-items: center; flex-wrap: wrap; gap: 4px 8px; font-size: 12.5px; color: var(--cv-dim); }
.sw__change .cv-num { font-weight: 600; }
.sw__empty { display: grid; place-items: center; height: 280px; margin: 0; color: var(--cv-mut); font-size: 13px; text-align: center; }
</style>
