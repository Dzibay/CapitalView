<script setup>
import { ref, onMounted, watch, onUnmounted, computed, nextTick } from 'vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const props = defineProps({
  portfolios: {
    type: Array,
    default: () => []
  },
  allPortfolios: {
    type: Array,
    default: () => []
  },
  selectedPortfolioId: {
    type: Number,
    default: null
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

// Получаем портфели только на один уровень вниз
const portfolioValues = computed(() => {
  if (!props.selectedPortfolioId || !props.allPortfolios?.length) return []
  
  // Находим выбранный портфель
  const selectedPortfolio = props.allPortfolios.find(p => p.portfolio_id === props.selectedPortfolioId)
  if (!selectedPortfolio) return []
  
  // Получаем портфели только на один уровень вниз
  const directChildren = props.portfolios
    .filter(p => p.parent_portfolio_id === props.selectedPortfolioId)
    .map(childPortfolio => {
      const childAnalytics = props.allPortfolios.find(a => a.portfolio_id === childPortfolio.id)
      return {
        name: childPortfolio.name,
        value: childAnalytics?.totals?.total_value || 0
      }
    })
    .filter(p => p.value > 0)
  
  // Добавляем текущий портфель, если у него есть собственные активы (не в дочерних)
  const parentValue = selectedPortfolio.totals?.total_value || 0
  const childrenSum = directChildren.reduce((sum, child) => sum + child.value, 0)
  const ownValue = Math.max(0, parentValue - childrenSum)
  
  const values = []
  if (ownValue > 0) {
    values.push({
      name: selectedPortfolio.portfolio_name,
      value: ownValue
    })
  }
  values.push(...directChildren)
  
  return values
})

const renderChart = () => {
  if (!chartCanvas.value || !portfolioValues.value?.length) {
    return
  }

  if (chartInstance) {
    chartInstance.destroy()
  }

  const ctx = chartCanvas.value.getContext('2d')
  if (!ctx) return

  const labels = portfolioValues.value.map(p => p.name)
  const data = portfolioValues.value.map(p => p.value)

  chartInstance = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: [
          '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
          '#8b5cf6', '#f472b6', '#60a5fa', '#fbbf24'
        ]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { 
          position: 'bottom',
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
              const label = context.label || ''
              const value = formatMoney(context.parsed)
              const total = context.dataset.data.reduce((a, b) => a + b, 0)
              const percent = total > 0 ? ((context.parsed / total) * 100).toFixed(1) : 0
              return `${label}: ${value} (${percent}%)`
            }
          }
        }
      }
    }
  })
}

watch(() => portfolioValues.value, renderChart, { deep: true, immediate: true })
watch(() => props.selectedPortfolioId, renderChart)
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
      <h2>Распределение портфелей</h2>
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

