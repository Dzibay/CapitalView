<script setup>
import { ref, onMounted, watch, onUnmounted, computed, nextTick } from 'vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const props = defineProps({
  futurePayouts: {
    type: Array,
    default: () => []
  }
})

const chartCanvas = ref(null)
let chartInstance = null

const formatMoney = (value) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  }).format(value || 0)
}

// Фильтруем только на год вперед
const filteredPayouts = computed(() => {
  if (!props.futurePayouts?.length) return []
  
  const currentDate = new Date()
  const oneYearLater = new Date(currentDate)
  oneYearLater.setFullYear(currentDate.getFullYear() + 1)
  
  return props.futurePayouts.filter(fp => {
    const [year, month] = fp.month.split('-')
    const payoutDate = new Date(parseInt(year), parseInt(month) - 1)
    return payoutDate <= oneYearLater
  })
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
  if (!filteredPayouts.value?.length) {
    return
  }

  const ctx = chartCanvas.value.getContext('2d')
  if (!ctx) return

  const labels = filteredPayouts.value.map(f => f.month)
  const data = filteredPayouts.value.map(f => f.total_amount || 0)

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Будущие выплаты',
        data: data,
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245, 158, 11, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: '#f59e0b',
        pointBorderColor: '#fff',
        pointBorderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: true,
          backgroundColor: '#1f2937',
          titleFont: { weight: 'bold', size: 14 },
          bodyFont: { size: 14 },
          padding: 12,
          cornerRadius: 6,
          displayColors: false,
          callbacks: {
            label: (context) => formatMoney(context.parsed.y)
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            font: { size: 12 },
            color: '#6b7280'
          }
        },
        y: {
          beginAtZero: true,
          grid: {
            color: '#f3f4f6',
            drawBorder: false
          },
          ticks: {
            font: { size: 12 },
            color: '#6b7280',
            callback: (value) => formatMoney(value)
          }
        }
      }
    }
  })
}

watch(() => props.futurePayouts, renderChart, { deep: true })
watch(() => filteredPayouts.value, renderChart, { deep: true })
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
      <h2>График будущих выплат</h2>
    </div>
    <div class="chart-container">
      <canvas ref="chartCanvas"></canvas>
      <div v-if="!filteredPayouts || filteredPayouts.length === 0" class="empty-state">
        <p>Нет данных о будущих выплатах</p>
      </div>
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

.chart-container {
  height: 300px;
  position: relative;
}

.empty-state {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #6b7280;
  font-size: 14px;
  background: white;
  z-index: 10;
}

.empty-state p {
  margin: 0;
}
</style>

