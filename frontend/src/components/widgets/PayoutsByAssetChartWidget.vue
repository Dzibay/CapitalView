<script setup>
import { ref, onMounted, watch, onUnmounted, nextTick } from 'vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const props = defineProps({
  payoutsByAsset: {
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
  // Уничтожаем старый график при любых изменениях
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }

  if (!chartCanvas.value) {
    return
  }

  // Если данных нет, не создаем график
  if (!props.payoutsByAsset?.length) {
    return
  }

  const ctx = chartCanvas.value.getContext('2d')
  if (!ctx) return

  // Ограничиваем до топ-10 активов для читаемости
  const topAssets = props.payoutsByAsset.slice(0, 10)
  const labels = topAssets.map(a => a.asset_ticker || a.asset_name || 'Unknown')
  const dividends = topAssets.map(a => a.total_dividends || 0)
  const coupons = topAssets.map(a => a.total_coupons || 0)

  chartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Дивиденды',
          data: dividends,
          backgroundColor: '#10b981',
          borderRadius: 8,
          borderSkipped: false,
          maxBarThickness: 60
        },
        {
          label: 'Купоны',
          data: coupons,
          backgroundColor: '#3b82f6',
          borderRadius: 8,
          borderSkipped: false,
          maxBarThickness: 60
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { 
          position: 'top',
          labels: {
            font: { size: 12 },
            color: '#6b7280',
            usePointStyle: true,
            padding: 15
          }
        },
        tooltip: {
          enabled: true,
          backgroundColor: '#1f2937',
          titleFont: { weight: 'bold', size: 14 },
          bodyFont: { size: 14 },
          padding: 12,
          cornerRadius: 6,
          displayColors: true,
          callbacks: {
            label: (context) => {
              const label = context.dataset.label || ''
              return `${label}: ${formatMoney(context.parsed.y)}`
            }
          }
        }
      },
      scales: {
        x: {
          stacked: true,
          grid: { display: false },
          ticks: {
            font: { size: 12 },
            color: '#6b7280',
            maxRotation: 45,
            minRotation: 45
          }
        },
        y: {
          stacked: true,
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

watch(() => props.payoutsByAsset, renderChart, { deep: true })
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
      <h2>Выплаты по активам</h2>
    </div>
    <div class="chart-container">
      <canvas ref="chartCanvas"></canvas>
      <div v-if="!payoutsByAsset || payoutsByAsset.length === 0" class="empty-state">
        <p>Нет данных о выплатах по активам</p>
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

