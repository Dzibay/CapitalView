<script setup>
import { ref, computed, onMounted, watch, onUnmounted, nextTick } from 'vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const props = defineProps({
  assetDistribution: {
    type: Array,
    default: () => []
  }
})

const chartCanvas = ref(null)
let chartInstance = null
const centerInfo = ref({
  label: 'Всего',
  percentage: 100,
  value: 0
})

const formatMoney = (value) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  }).format(value || 0)
}

const chartData = computed(() => {
  if (!props.assetDistribution?.length) {
    return { labels: [], values: [], total: 0 }
  }
  
  const labels = props.assetDistribution.map(a => a.asset_name || a.asset_ticker || 'Unknown')
  const values = props.assetDistribution.map(a => a.total_value || 0)
  const total = values.reduce((a, b) => a + b, 0)
  
  return { labels, values, total }
})

const renderChart = () => {
  // Уничтожаем старый график при любых изменениях
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }

  if (!chartCanvas.value) {
    return
  }

  // Если данных нет, не создаем график
  if (!chartData.value.labels.length) {
    return
  }

  const ctx = chartCanvas.value.getContext('2d')
  if (!ctx) return

  const { labels, values, total } = chartData.value
  
  // Обновляем центральную информацию
  centerInfo.value = {
    label: 'Всего',
    value: total,
    percentage: 100
  }

  chartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: [
          '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6',
          '#10b981', '#f472b6', '#60a5fa', '#fbbf24', '#a78bfa',
          '#ec4899', '#14b8a6', '#f97316', '#6366f1'
        ]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '75%',
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: false,
          external: (context) => {
            const tooltipModel = context.tooltip
            if (tooltipModel.dataPoints?.length) {
              const index = tooltipModel.dataPoints[0].dataIndex
              const label = labels[index]
              const value = values[index]
              const percent = total > 0 ? Math.round((value / total) * 100) : 0
              centerInfo.value = { label, value, percentage: percent }
            } else {
              centerInfo.value = {
                label: 'Всего',
                value: total,
                percentage: 100
              }
            }
          }
        }
      },
      onHover: (event, activeElements, chart) => {
        if (activeElements && activeElements.length > 0) {
          const index = activeElements[0].index
          const label = labels[index]
          const value = values[index]
          const total = values.reduce((a, b) => a + b, 0)
          const percent = total > 0 ? Math.round((value / total) * 100) : 0
          centerInfo.value = { label, value, percentage: percent }
        } else {
          centerInfo.value = {
            label: 'Всего',
            value: total,
            percentage: 100
          }
        }
      }
    }
  })
}

watch(() => props.assetDistribution, renderChart, { deep: true })
onMounted(() => {
  nextTick(() => renderChart())
})
onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
})
</script>

<template>
  <div class="widget">
    <div class="widget-title">
      <div class="widget-title-icon-rect"></div>
      <h2>Распределение по активам</h2>
    </div>

    <div v-if="assetDistribution && assetDistribution.length" class="allocation-container">
      <div class="chart-wrapper">
        <div class="chart-container-asset">
          <canvas ref="chartCanvas"></canvas>
        </div>
        <div v-if="centerInfo.label" class="chart-center">
          <span class="center-label">{{ centerInfo.label }}</span>
          <span class="center-percentage">{{ centerInfo.percentage }}%</span>
          <span class="center-value">{{ formatMoney(centerInfo.value) }}</span>
        </div>
      </div>

      <div class="legends">
        <div 
          v-for="(asset, i) in assetDistribution" 
          :key="asset.asset_id || asset.asset_ticker || i" 
          class="legend-item"
        >
          <span 
            class="legend-color" 
            :style="{ 
              backgroundColor: [
                '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6',
                '#10b981', '#f472b6', '#60a5fa', '#fbbf24', '#a78bfa',
                '#ec4899', '#14b8a6', '#f97316', '#6366f1'
              ][i % 13]
            }"
          ></span>
          <span class="legend-label">{{ asset.asset_name || asset.asset_ticker || 'Unknown' }}</span>
        </div>
      </div>
    </div>
    <div v-else class="empty-state">
      <p>Нет данных о распределении активов</p>
    </div>
  </div>
</template>

<style scoped>
.widget {
  background-color: #fff;
  padding: var(--spacing);
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

.widget-title {
  display: flex;
  gap: 5px;
  align-items: center;
}

.widget-title-icon-rect {
  padding: 5px;
  width: 25px;
  height: 25px;
  border-radius: 6px;
  background-color: #F6F6F6;
}

.widget-title h2 {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.allocation-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.chart-wrapper {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.chart-container-asset {
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
  font-weight: 600;
  color: #111827;
  display: block;
}

.center-value {
  font-size: 14px;
  color: #4b5563;
  display: block;
}

.legends {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  font-size: 12px;
  color: #6b7280;
  justify-content: center;
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

.empty-state {
  text-align: center;
  color: #6b7280;
  font-size: 14px;
  padding: 40px 20px;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-state p {
  margin: 0;
}
</style>

