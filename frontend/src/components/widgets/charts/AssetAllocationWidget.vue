<script setup>
import { ref, computed, watch, inject, onMounted, unref } from 'vue'
import { PieChart } from 'lucide-vue-next'
import { Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, ArcElement, DoughnutController } from 'chart.js'
import Widget from '../base/Widget.vue'
import { LANDING_DASH_REVEAL_KEY } from '../../../constants/landingDashboardReveal'

ChartJS.register(Title, Tooltip, Legend, ArcElement, DoughnutController)

// Props
const props = defineProps({
  assetAllocation: {
    type: Object,
    required: true
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

const formatCurrency = (value) => {
  return value.toLocaleString('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 })
}

const chartData = computed(() => ({
  labels: props.assetAllocation?.labels ?? [],
  datasets: props.assetAllocation?.datasets ?? []
}))

const total = computed(() => {
  if (!props.assetAllocation?.datasets?.length) return 0
  return props.assetAllocation.datasets[0].data.reduce((a, b) => a + b, 0)
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

        if (tooltipModel.dataPoints?.length && data.datasets?.length) {
          const idx = tooltipModel.dataPoints[0].dataIndex
          const label = data.labels[idx]
          const value = data.datasets[0].data[idx]
          const totalValue = total.value
          const percentage = totalValue > 0 ? Math.round((value / totalValue) * 100) : 0
          centerInfo.value = { label, value, percentage }
        } else if (data.datasets?.length) {
          centerInfo.value = { label: 'Всего', value: total.value, percentage: 100 }
        }
      }
    }
  },
  onHover: (event, activeElements, chart) => {
    const data = props.assetAllocation
    if (activeElements && activeElements.length > 0 && data.datasets?.length) {
      const index = activeElements[0].index
      const label = data.labels[index]
      const value = data.datasets[0].data[index]
      const totalValue = total.value
      const percentage = totalValue > 0 ? Math.round((value / totalValue) * 100) : 0
      centerInfo.value = { label, value, percentage }
    } else if (data.datasets?.length) {
      centerInfo.value = { label: 'Всего', value: total.value, percentage: 100 }
    }
  }
}))

// Инициализация и обновление centerInfo при изменении данных
watch(() => props.assetAllocation, () => {
  if (props.assetAllocation?.datasets?.length) {
    centerInfo.value = { label: 'Всего', value: total.value, percentage: 100 }
  }
}, { immediate: true, deep: true })
</script>

<template>
  <Widget title="Распределение активов" :icon="PieChart">
    <div v-if="assetAllocation && assetAllocation.labels" class="allocation-container">
      <div class="chart-wrapper">
        <Doughnut :key="doughnutRemountKey" :data="chartData" :options="chartOptions" />
        <div v-if="centerInfo.label" class="chart-center">
          <span class="center-label">{{ centerInfo.label }}</span>
          <span class="center-percentage">{{ centerInfo.percentage }}%</span>
          <span class="center-value">{{ formatCurrency(centerInfo.value) }}</span>
        </div>
      </div>

      <div class="legends">
        <div v-for="(label, i) in assetAllocation.labels" :key="label" class="legend-item">
          <span class="legend-color" :style="{ backgroundColor: assetAllocation.datasets[0].backgroundColor[i] }"></span>
          <span class="legend-label">{{ label }}</span>
        </div>
      </div>
    </div>
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
