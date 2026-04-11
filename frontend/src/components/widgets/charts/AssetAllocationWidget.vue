<script setup>
import { ref, computed, watch, inject, onMounted, unref, useSlots } from 'vue'
import { PieChart } from 'lucide-vue-next'
import { Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, ArcElement, DoughnutController } from 'chart.js'
import Widget from '../base/Widget.vue'
import EmptyState from '../base/EmptyState.vue'
import { LANDING_DASH_REVEAL_KEY } from '../../../constants/landingDashboardReveal'

ChartJS.register(Title, Tooltip, Legend, ArcElement, DoughnutController)

// Props
const props = defineProps({
  title: {
    type: String,
    default: 'Распределение активов'
  },
  icon: {
    type: [Object, Function],
    default: () => PieChart
  },
  assetAllocation: {
    type: Object,
    default: null
  },
  /** Подпись суммы в центре кольца (по умолчанию — formatCurrency в RUB) */
  formatCenterValue: {
    type: Function,
    default: null
  },
  /** Показать EmptyState, если данных для графика нет */
  emptyMessage: {
    type: String,
    default: null
  },
  scrollReveal: {
    type: Boolean,
    default: false
  },
  landingRevealRef: {
    type: [Object, Boolean],
    default: null
  }
})

const slots = useSlots()

const injectedLandingReveal = inject(LANDING_DASH_REVEAL_KEY, null)

function revealSource() {
  return props.landingRevealRef ?? injectedLandingReveal
}
const doughnutRemountKey = ref(0)

function bumpDoughnut() {
  doughnutRemountKey.value += 1
}

watch(
  () => {
    if (!props.scrollReveal) return null
    const src = revealSource()
    if (src == null) return false
    return unref(src)
  },
  (ok) => {
    if (props.scrollReveal && ok) bumpDoughnut()
  }
)

onMounted(() => {
  const src = revealSource()
  if (props.scrollReveal && src != null && unref(src)) bumpDoughnut()
})

const centerInfo = ref({
  label: 'Всего',
  percentage: 100,
  value: 0
})

const formatTwoDecimals = (value) => {
  const n = Number(value)
  if (!Number.isFinite(n)) return '0,00'
  return n.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatCurrency = (value) => {
  const n = Number(value)
  if (!Number.isFinite(n)) {
    return (0).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  return n.toLocaleString('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/** Доля в процентах, округление до 2 знаков (сумма по сегментам может отличаться от 100.00 из-за округления). */
function percentOfPart(value, totalValue) {
  if (!(totalValue > 0)) return 0
  return Math.round((Number(value) / totalValue) * 10000) / 100
}

function formatCenterDisplay(value) {
  if (props.formatCenterValue) return props.formatCenterValue(value)
  return formatCurrency(value)
}

const chartData = computed(() => ({
  labels: props.assetAllocation?.labels ?? [],
  datasets: props.assetAllocation?.datasets ?? []
}))

const total = computed(() => {
  if (!props.assetAllocation?.datasets?.length) return 0
  return props.assetAllocation.datasets[0].data.reduce((a, b) => a + (Number(b) || 0), 0)
})

const hasRenderableData = computed(() => {
  const a = props.assetAllocation
  if (!a?.labels?.length || !a.datasets?.[0]?.data?.length) return false
  return total.value > 0
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  cutout: '75%',
  plugins: {
    legend: { display: false },
    tooltip: {
      enabled: false,
      external(context) {
        const tooltipModel = context.tooltip
        const data = props.assetAllocation

        if (tooltipModel.dataPoints?.length && data?.datasets?.length) {
          const idx = tooltipModel.dataPoints[0].dataIndex
          const label = data.labels[idx]
          const value = data.datasets[0].data[idx]
          const totalValue = total.value
          const percentage = percentOfPart(value, totalValue)
          centerInfo.value = { label, value, percentage }
        } else if (data?.datasets?.length) {
          centerInfo.value = { label: 'Всего', value: total.value, percentage: 100 }
        }
      }
    }
  },
  onHover: (event, activeElements, chart) => {
    const data = props.assetAllocation
    if (activeElements && activeElements.length > 0 && data?.datasets?.length) {
      const index = activeElements[0].index
      const label = data.labels[index]
      const value = data.datasets[0].data[index]
      const totalValue = total.value
      const percentage = percentOfPart(value, totalValue)
      centerInfo.value = { label, value, percentage }
    } else if (data?.datasets?.length) {
      centerInfo.value = { label: 'Всего', value: total.value, percentage: 100 }
    }
  }
}))

// Инициализация и обновление centerInfo при изменении данных
watch(
  () => props.assetAllocation,
  () => {
    if (hasRenderableData.value) {
      centerInfo.value = { label: 'Всего', value: total.value, percentage: 100 }
    }
  },
  { immediate: true, deep: true }
)
</script>

<template>
  <Widget :title="title" :icon="icon">
    <template v-if="slots.header" #header>
      <slot name="header" />
    </template>
    <div v-if="hasRenderableData" class="allocation-container">
      <div class="chart-wrapper">
        <Doughnut :key="doughnutRemountKey" :data="chartData" :options="chartOptions" />
        <div v-if="centerInfo.label" class="chart-center">
          <span class="center-label">{{ centerInfo.label }}</span>
          <span class="center-percentage">{{ formatTwoDecimals(centerInfo.percentage) }}%</span>
          <span class="center-value">{{ formatCenterDisplay(centerInfo.value) }}</span>
        </div>
      </div>

      <div class="legends">
        <div v-for="(label, i) in assetAllocation.labels" :key="label" class="legend-item">
          <span class="legend-color" :style="{ backgroundColor: assetAllocation.datasets[0].backgroundColor[i] }"></span>
          <span class="legend-label">{{ label }}</span>
        </div>
      </div>
    </div>
    <EmptyState v-else-if="emptyMessage" :message="emptyMessage" />
  </Widget>
</template>

<style scoped>

.allocation-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-width: 0;
  flex: 1;
  min-height: 0;
}

.chart-wrapper {
  position: relative;
  width: 280px;
  height: 280px;
  max-width: 100%;
  flex-shrink: 0;
}

.chart-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  pointer-events: none;
}

.center-label {
  font-size: var(--text-caption-size);
  color: var(--text-tertiary);
  display: block;
}

.center-percentage {
  font-size: var(--text-value-size);
  font-weight: var(--text-value-weight);
  color: var(--text-primary);
  display: block;
}

.center-value {
  font-size: var(--text-body-secondary-size);
  color: var(--text-secondary);
  display: block;
}

.legends {
  margin-top: 20px;
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  font-size: var(--text-caption-size);
  color: var(--text-tertiary);
}

.legend-item {
  display: flex;
  align-items: center;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 8px;
}

@media (max-width: 1200px) {
  .chart-wrapper {
    width: 240px;
    height: 240px;
  }
  .legends {
    margin-top: 14px;
    gap: 12px;
  }
}

@media (max-width: 768px) {
  .chart-wrapper {
    width: 200px;
    height: 200px;
  }
  .legends {
    margin-top: 12px;
    gap: 10px;
  }
}

@media (max-width: 480px) {
  .chart-wrapper {
    width: 180px;
    height: 180px;
  }
  .legends {
    margin-top: 10px;
    gap: 8px;
  }
}
</style>
