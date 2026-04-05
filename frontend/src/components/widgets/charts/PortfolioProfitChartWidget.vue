<script setup>
import { ref, computed, watch } from 'vue'
import MultiLineChart from '../../charts/MultiLineChart.vue'
import Widget from '../base/Widget.vue'
import PeriodFilters from '../base/PeriodFilters.vue'
import ChartPeriodSummary from '../base/ChartPeriodSummary.vue'
import ChartOptionsMenu from '../../base/ChartOptionsMenu.vue'
import { TrendingUp } from 'lucide-vue-next'

const props = defineProps({
  chartData: {
    type: Object,
    required: true
  }
})

const selectedPeriod = ref("All")
const showMinMax = ref(false)

const chartMenuOptions = computed(() => [
  { id: 'minmax', label: 'Min / Max', modelValue: showMinMax.value }
])

function onChartOptionToggle(id, val) {
  if (id === 'minmax') showMinMax.value = val
}

const formatCurrency = (value) => {
  if (typeof value !== 'number') return value
  return value.toLocaleString('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  })
}

const formatChangeValue = (v) => {
  if (typeof v !== 'number') return v
  return v.toLocaleString('ru-RU', { maximumFractionDigits: 0 })
}

const profitAbs = ref(0)
const profitPercent = ref(0)
const periodStartDate = ref(null)
const periodEndDate = ref(null)

function getPeriodStartDate(period) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  if (period === '7D') return new Date(today.getFullYear(), today.getMonth(), today.getDate() - 7)
  if (period === '1M') return new Date(today.getFullYear(), today.getMonth(), today.getDate() - 30)
  if (period === '3M') return new Date(today.getFullYear(), today.getMonth(), today.getDate() - 90)
  if (period === '6M') return new Date(today.getFullYear(), today.getMonth(), today.getDate() - 180)
  if (period === 'YTD') return new Date(today.getFullYear(), 0, 1)
  if (period === '1Y') return new Date(today.getFullYear(), today.getMonth() - 11, 1)
  if (period === '5Y') return new Date(today.getFullYear() - 5, today.getMonth(), today.getDate())
  return null
}

function filterPointsByPeriod(labels, data, period) {
  if (!labels?.length || !data?.length) return []
  const today = new Date()
  today.setHours(23, 59, 59, 999)
  const points = labels.map((label, i) => ({
    date: new Date(label),
    value: Number(data[i]) || 0
  })).sort((a, b) => a.date - b.date)
  if (!points.length) return []

  const start = getPeriodStartDate(period)
  if (!start) return points

  start.setHours(0, 0, 0, 0)
  const filtered = points.filter(p => {
    const pd = new Date(p.date)
    pd.setHours(0, 0, 0, 0)
    return pd >= start && pd <= today
  })
  if (filtered.length) return filtered
  const before = points.filter(p => p.date <= today)
  if (before.length) return [before[before.length - 1]]
  return points.length ? [points[0], points[points.length - 1]] : []
}

function updateStats() {
  const labels = props.chartData?.labels || []
  const data = props.chartData?.data_pnl || []
  const pts = filterPointsByPeriod(labels, data, selectedPeriod.value)
  if (!pts.length) {
    profitAbs.value = 0
    profitPercent.value = 0
    periodStartDate.value = null
    periodEndDate.value = null
    return
  }
  const first = pts[0].value
  const last = pts[pts.length - 1].value
  profitAbs.value = last - first
  profitPercent.value = first === 0 ? 0 : ((profitAbs.value / Math.abs(first)) * 100)
  periodStartDate.value = pts[0].date
  periodEndDate.value = pts[pts.length - 1].date
}

const formattedChartData = computed(() => {
  if (!props.chartData?.labels?.length || !props.chartData?.data_pnl) {
    return { labels: [], datasets: [] }
  }
  return {
    labels: props.chartData.labels,
    datasets: [{
      label: "Прибыль",
      data: props.chartData.data_pnl,
      color: "#5478EA",
      fill: true
    }]
  }
})

watch(() => props.chartData, updateStats, { deep: true })
watch(() => selectedPeriod.value, updateStats)
updateStats()
</script>

<template>
  <Widget title="Динамика прибыли" :icon="TrendingUp">
    <template #header>
      <ChartOptionsMenu
        :options="chartMenuOptions"
        @toggle="onChartOptionToggle"
      />
    </template>

    <template #subheader>
      <PeriodFilters v-model="selectedPeriod" />
      <ChartPeriodSummary
        :startDate="periodStartDate"
        :endDate="periodEndDate"
        :changeValue="profitAbs"
        :changePercent="profitPercent"
        :formatValue="formatChangeValue"
      />
    </template>

    <div class="chart-wrapper">
      <MultiLineChart
        :chartData="formattedChartData"
        :period="selectedPeriod"
        :zeroAtStart="false"
        :formatCurrency="formatCurrency"
        :showMinMaxGuides="showMinMax"
      />
    </div>
  </Widget>
</template>

<style scoped>
.chart-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  min-height: 0;
  max-height: 300px;
}
</style>