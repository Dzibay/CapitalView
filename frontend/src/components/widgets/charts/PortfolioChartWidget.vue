<script setup>
import { ref, computed, onMounted, onUnmounted, watch, inject, nextTick, unref } from 'vue'
import { LineChart } from 'lucide-vue-next'
import MultiLineChart from '../../charts/MultiLineChart.vue'
import Widget from '../base/Widget.vue'
import PeriodFilters from '../base/PeriodFilters.vue'
import ChartPeriodSummary from '../base/ChartPeriodSummary.vue'
import ChartOptionsMenu from '../../base/ChartOptionsMenu.vue'
import { LANDING_DASH_REVEAL_KEY } from '../../../constants/landingDashboardReveal'

const props = defineProps({
  chartData: {
    type: Object,
    required: true
  },
  /** Лендинг: линия и блок сумм «прорисовываются» при появлении превью */
  scrollRevealChart: {
    type: Boolean,
    default: false
  },
  landingRevealRef: {
    type: Object,
    default: null
  }
})

const injectedLandingReveal = inject(LANDING_DASH_REVEAL_KEY, null)

function revealSource() {
  return props.landingRevealRef ?? injectedLandingReveal
}

function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3)
}

const drawProgress = ref(props.scrollRevealChart ? 0 : 1)
const summaryT = ref(props.scrollRevealChart ? 0 : 1)
let chartRevealRaf = null

function setChartRevealStatic() {
  drawProgress.value = 1
  summaryT.value = 1
}

function runChartRevealAnimation() {
  const duration = 1450
  if (prefersReducedMotion()) {
    setChartRevealStatic()
    return
  }
  const start = performance.now()
  if (chartRevealRaf) cancelAnimationFrame(chartRevealRaf)
  function frame(now) {
    const u = Math.min(1, (now - start) / duration)
    const t = easeOutCubic(u)
    drawProgress.value = t
    summaryT.value = t
    if (u < 1) chartRevealRaf = requestAnimationFrame(frame)
    else {
      chartRevealRaf = null
      setChartRevealStatic()
    }
  }
  drawProgress.value = 0
  summaryT.value = 0
  chartRevealRaf = requestAnimationFrame(frame)
}

function syncChartReveal() {
  if (!props.scrollRevealChart) {
    setChartRevealStatic()
    return
  }
  const src = revealSource()
  if (src == null) {
    setChartRevealStatic()
    return
  }
  if (!unref(src)) {
    drawProgress.value = 0
    summaryT.value = 0
    return
  }
  runChartRevealAnimation()
}

watch(
  () => {
    if (!props.scrollRevealChart) return null
    const src = revealSource()
    if (src == null) return true
    return unref(src)
  },
  (revealed) => {
    if (!props.scrollRevealChart) return
    nextTick(() => {
      if (revealed) syncChartReveal()
      else {
        drawProgress.value = 0
        summaryT.value = 0
      }
    })
  }
)

onUnmounted(() => {
  if (chartRevealRaf) cancelAnimationFrame(chartRevealRaf)
})

const selectedPeriod = ref("All")
const includeBalance = ref(true)
const showMinMax = ref(false)

const chartMenuOptions = computed(() => [
  { id: 'balance', label: 'С балансом', modelValue: includeBalance.value },
  { id: 'minmax', label: 'Min / Max', modelValue: showMinMax.value }
])

function onChartOptionToggle(id, val) {
  if (id === 'balance') includeBalance.value = val
  else if (id === 'minmax') showMinMax.value = val
}

// --------------------------
// Формат валюты
// --------------------------
const formatCurrency = (value) => {
  if (typeof value !== 'number') return value
  return value.toLocaleString('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  })
}

// --------------------------
// Статистика по капиталу
// --------------------------
const growthAmount = ref(0)
const growthPercent = ref(0)
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

const updateStats = (labels, values, period) => {
  const pts = filterPointsByPeriod(labels, values, period)
  if (!pts.length) {
    growthAmount.value = 0
    growthPercent.value = 0
    periodStartDate.value = null
    periodEndDate.value = null
    return
  }
  const first = pts[0].value
  const last = pts[pts.length - 1].value
  growthAmount.value = last - first
  growthPercent.value = first === 0 ? 0 : ((growthAmount.value / Math.abs(first)) * 100)
  periodStartDate.value = pts[0].date
  periodEndDate.value = pts[pts.length - 1].date
}

// --------------------------
// Формируем данные для универсального графика
// --------------------------
const formattedChartData = computed(() => {
  if (!props.chartData?.labels?.length) return { labels: [], datasets: [] }

  const labels = props.chartData.labels
  
  // Базовые данные
  const valueData = (props.chartData.data_value || []).map(v => Number(v) || 0)
  const investedData = (props.chartData.data_invested || []).map(v => Number(v) || 0)
  const balanceData = (props.chartData.data_balance || []).map(v => Number(v) || 0)
  
  // Агрегируем данные с балансом на фронтенде (оптимально)
  // Аналогично как для инвестиций: если включен баланс, добавляем его к стоимости и инвестициям
  const valueWithBalance = includeBalance.value
    ? valueData.map((val, index) => val + (balanceData[index] || 0))
    : valueData
  
  const investedWithBalance = includeBalance.value
    ? investedData.map((inv, index) => inv + (balanceData[index] || 0))
    : investedData

  const datasets = [
    {
      label: includeBalance.value ? "Капитал (с балансом)" : "Капитал",
      data: valueWithBalance,
      color: '#3b82f6',
      fill: true
    },
    {
      label: includeBalance.value ? "Инвестиции (с балансом)" : "Инвестиции",
      data: investedWithBalance,
      color: '#10b981',
      fill: false
    }
  ]

  return { labels, datasets }
})

// Обновляем статистику при изменении данных или периода
const updateStatsForPeriod = () => {
  if (!props.chartData?.labels?.length) {
    updateStats([], [], selectedPeriod.value)
    return
  }
  
  // Агрегируем данные с балансом на фронтенде (аналогично графику)
  const valueData = (props.chartData.data_value || []).map(v => Number(v) || 0)
  const balanceData = (props.chartData.data_balance || []).map(v => Number(v) || 0)
  
  // Если включен баланс, добавляем его к стоимости портфеля
  const valueWithBalance = includeBalance.value
    ? valueData.map((val, index) => val + (balanceData[index] || 0))
    : valueData
  
  if (!valueWithBalance || valueWithBalance.length === 0) {
    updateStats([], [], selectedPeriod.value)
    return
  }
  
  updateStats(props.chartData.labels, valueWithBalance, selectedPeriod.value)
}

// Следим за изменениями данных, периода и переключателя баланса
watch(() => props.chartData, updateStatsForPeriod, { deep: true })
watch(() => selectedPeriod.value, updateStatsForPeriod)
watch(() => includeBalance.value, updateStatsForPeriod)

// Инициализация при монтировании (сначала цифры периода, затем анимация графика)
onMounted(() => {
  updateStatsForPeriod()
  nextTick(() => syncChartReveal())
})

const formatChangeValue = (v) => {
  if (typeof v !== 'number') return v
  return v.toLocaleString('ru-RU', { maximumFractionDigits: 0 })
}

</script>

<template>
  <Widget title="Динамика капитала" :icon="LineChart">
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
        :changeValue="growthAmount"
        :changePercent="growthPercent"
        :formatValue="formatChangeValue"
      />
    </template>

    <div class="chart-wrapper">
      <MultiLineChart
        :chartData="formattedChartData"
        :period="selectedPeriod"
        :formatCurrency="formatCurrency"
        :zeroAtStart="false"
        :draw-progress="drawProgress"
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
  min-height: 200px;
  min-width: 0;
  width: 100%;
  overflow: hidden;
}

@media (max-width: 1200px) {
  .chart-wrapper {
    min-height: 220px;
  }
}

@media (max-width: 768px) {
  .chart-wrapper {
    min-height: 200px;
  }
}

@media (max-width: 480px) {
  .chart-wrapper {
    min-height: 180px;
  }
}
</style>
