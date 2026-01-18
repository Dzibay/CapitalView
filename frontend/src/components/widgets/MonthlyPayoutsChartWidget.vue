<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const props = defineProps({
  monthlyPayouts: {
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

const renderChart = () => {
  if (!chartCanvas.value || !props.monthlyPayouts?.length) {
    return
  }

  if (chartInstance) {
    chartInstance.destroy()
  }

  const ctx = chartCanvas.value.getContext('2d')
  if (!ctx) return

  const labels = props.monthlyPayouts.map(m => m.month)
  const data = props.monthlyPayouts.map(m => m.total_payouts || 0)

  chartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Полученные выплаты',
        data: data,
        backgroundColor: '#10b981',
        borderRadius: 8,
        borderSkipped: false,
        maxBarThickness: 60
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

watch(() => props.monthlyPayouts, renderChart, { deep: true })
onMounted(renderChart)
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
      <h2>Полученные выплаты по месяцам</h2>
    </div>
    <div class="chart-container">
      <canvas ref="chartCanvas"></canvas>
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
</style>

