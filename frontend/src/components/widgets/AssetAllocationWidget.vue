<script setup>
import { ref, computed } from 'vue'
import { Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, ArcElement, DoughnutController } from 'chart.js'

ChartJS.register(Title, Tooltip, Legend, ArcElement, DoughnutController)

// Props
const props = defineProps({
  assetAllocation: {
    type: Object,
    required: true
  }
})

const centerInfo = ref({
  label: '',
  percentage: 0,
  value: 0
})

const formatCurrency = (value) => {
  return value.toLocaleString('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 })
}

const chartData = computed(() => ({
  labels: props.assetAllocation?.labels ?? [],
  datasets: props.assetAllocation?.datasets ?? []
}))

const chartOptions = {
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
          const total = data.datasets[0].data.reduce((a, b) => a + b, 0)
          const percentage = Math.round((value / total) * 100)
          centerInfo.value = { label, value, percentage }
        } else if (data.datasets?.length) {
          const total = data.datasets[0].data.reduce((a, b) => a + b, 0)
          centerInfo.value = { label: 'Всего', value: total, percentage: 100 }
        }
      }
    }
  }
}
</script>

<template>
  <div class="widget">
    <div class="widget-title">
      <div class="widget-title-icon-rect"></div>
      <h2>Распределение активов</h2>
    </div>

    <div v-if="assetAllocation && assetAllocation.labels" class="allocation-container">
      <div class="chart-wrapper">
        <Doughnut :data="chartData" :options="chartOptions" />
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
  </div>
</template>

<style scoped>
.widget {
  grid-row: span 3;
  grid-column: span 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background-color: #fff;
  padding: var(--spacing);
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  width: 100%;
  max-width: 600px;
}

.allocation-container {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.chart-wrapper {
  position: relative;
  width: 300px;
  height: 300px;
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
  font-size: 12px;
  color: #6b7280;
  display: block;
}

.center-percentage {
  font-size: 18px;
  font-weight: bold;
  color: #111827;
  display: block;
}

.center-value {
  font-size: 14px;
  color: #4b5563;
  display: block;
}

.legends {
  margin-top: 20px;
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  font-size: 12px;
  color: #6B7280;
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
</style>
