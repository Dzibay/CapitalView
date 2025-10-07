<script setup>
import { onMounted, ref, watch } from 'vue'
import { Chart, LineElement, PointElement, LineController, CategoryScale, LinearScale, Filler, Tooltip, Legend } from 'chart.js'

Chart.register(LineElement, PointElement, LineController, CategoryScale, LinearScale, Filler, Tooltip, Legend)

// Получаем props
const props = defineProps({
  chartData: {
    type: Object,
    required: true,
    // { labels: ['2024-01-01', ...], data: [50000, ...] }
  }
})

const selectedPeriod = ref('All')
let chartInstance = null

// Статистика
const startValue = ref(0)
const endValue = ref(0)
const growthAmount = ref(0)
const growthPercent = ref(0)

// Формат валюты
const formatCurrency = (value) => {
  if (typeof value !== 'number') return value
  return value.toLocaleString('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  })
}

// Агрегирование данных
function aggregateLabelsAndData(dataObj, period) {
  const labels = []
  const data = []

  if (period === '1M') {
    const sliceData = dataObj.data.slice(-30)
    const sliceLabels = dataObj.labels.slice(-30)
    return { labels: sliceLabels, data: sliceData }
  } else {
    const monthMap = {}
    dataObj.labels.forEach((dateStr, idx) => {
      const date = new Date(dateStr)
      const monthKey = date.toLocaleString('ru-RU', { month: 'short', year: 'numeric' })
      if (!monthMap[monthKey]) monthMap[monthKey] = []
      monthMap[monthKey].push(dataObj.data[idx])
    })

    Object.keys(monthMap).forEach(month => {
      const values = monthMap[month]
      const avg = Math.round(values.reduce((a,b)=>a+b,0)/values.length)
      labels.push(month)
      data.push(avg)
    })

    if (period === '1Y') {
      return { labels: labels.slice(-12), data: data.slice(-12) }
    }

    return { labels, data }
  }
}

// Вычисление статистики
const calculateGrowth = (data) => {
  if (!data?.length) return
  startValue.value = data[0]
  endValue.value = data[data.length - 1]
  growthAmount.value = endValue.value - startValue.value
  growthPercent.value = ((growthAmount.value / startValue.value) * 100).toFixed(1)
}

// Создание графика
// const createCapitalChart = (dataObj) => {
//   const ctx = document.getElementById('capitalChart')?.getContext('2d')
//   if (!ctx) return

//   if (chartInstance) chartInstance.destroy()

//   ctx.canvas.height = ctx.canvas.parentNode.clientHeight
//   ctx.canvas.width = ctx.canvas.parentNode.clientWidth

//   const gradient = ctx.createLinearGradient(0, 0, 0, ctx.canvas.height)
//   gradient.addColorStop(0, 'rgba(84, 120, 234, 0.2)')
//   gradient.addColorStop(1, 'rgba(84, 120, 234, 0)')

//   const yMin = Math.min(...dataObj.data)
//   const yMax = Math.max(...dataObj.data)

//   chartInstance = new Chart(ctx, {
//     type: 'line',
//     data: {
//       labels: dataObj.labels,
//       datasets: [{
//         label: 'Капитал',
//         data: dataObj.data,
//         fill: true,
//         backgroundColor: gradient,
//         borderColor: '#5478EA',
//         borderWidth: 3,
//         tension: 0.4,
//         pointRadius: 0,
//         pointHoverRadius: 6,
//         pointBackgroundColor: '#5478EA',
//         pointBorderColor: '#fff',
//         pointBorderWidth: 2,
//       }]
//     },
//     options: {
//       responsive: true,
//       maintainAspectRatio: false,
//       scales: {
//         y: {
//           min: yMin,
//           max: yMax,
//           ticks: {
//             callback(value) {
//               if (value >= 1000) return (value / 1000) + 'k'
//               return value
//             },
//             color: '#9ca3af',
//             padding: 10
//           },
//           grid: {
//             color: '#e5e7eb',
//             borderDash: [5, 5],
//             drawBorder: false
//           }
//         },
//         x: {
//           ticks: { color: '#9ca3af' },
//           grid: { display: false }
//         }
//       },
//       plugins: {
//         legend: { display: false },
//         tooltip: {
//           enabled: true,
//           mode: 'index',
//           intersect: false,
//           backgroundColor: '#1f2937',
//           titleFont: { weight: 'bold' },
//           bodyFont: { size: 14 },
//           padding: 12,
//           cornerRadius: 6,
//           displayColors: false,
//           callbacks: {
//             label: (context) => `${formatCurrency(context.parsed.y)}`
//           }
//         }
//       },
//       interaction: { mode: 'index', intersect: false }
//     }
//   })
// }
const renderChart = (aggregated) => {
  const ctx = document.getElementById('capitalChart')?.getContext('2d')
  if (!ctx) return

  const yMin = Math.min(...aggregated.data)
  const yMax = Math.max(...aggregated.data)

  if (chartInstance) {
    chartInstance.data.labels = aggregated.labels
    chartInstance.data.datasets[0].data = aggregated.data
    chartInstance.options.scales.y.min = yMin
    chartInstance.options.scales.y.max = yMax
    chartInstance.resize()
    chartInstance.update()
    return
  }

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: aggregated.labels,
      datasets: [{
        label: 'Капитал',
        data: aggregated.data,
        fill: true,
        backgroundColor: (context) => {
          const chart = context.chart
          const {ctx, chartArea} = chart
          if (!chartArea) return null
          const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
          gradient.addColorStop(0, 'rgba(59, 130, 246, 0.2)')
          gradient.addColorStop(1, 'rgba(59, 130, 246, 0)')
          return gradient
        },
        borderColor: '#3b82f6',
        borderWidth: 3,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 6,
        pointBackgroundColor: '#3b82f6',
        pointBorderColor: '#fff',
        pointBorderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        y: {
          min: yMin,
          max: yMax,
          ticks: {
            callback: (value) => value >= 1000 ? value/1000 + 'k' : value,
            color: '#9ca3af',
            padding: 10
          },
          grid: { color: '#e5e7eb', borderDash: [5,5], drawBorder: false }
        },
        x: {
          ticks: { color: '#9ca3af' },
          grid: { display: false }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: true,
          mode: 'index',
          intersect: false,
          backgroundColor: '#1f2937',
          titleFont: { weight: 'bold' },
          bodyFont: { size: 14 },
          padding: 12,
          cornerRadius: 6,
          displayColors: false,
          callbacks: { label: ctx => formatCurrency(ctx.parsed.y) }
        }
      }
    }
  })
}

// Функция обновления графика
const updateChart = () => {
  if (!props.chartData?.data?.length) return
  const aggregated = aggregateLabelsAndData(props.chartData, selectedPeriod.value)
  calculateGrowth(aggregated.data)
  renderChart(aggregated)
}

// Watchers
watch([selectedPeriod], updateChart)
watch(() => props.chartData, updateChart, { deep: true })

onMounted(() => updateChart())
</script>

<template>
  <div class="widget">
    <div class="capital-header">
      <div class="capital-info">

        <div class="widget-title">
          <div class="widget-title-icon-rect">

          </div>
          <h2>Динамика капитала</h2>
        </div>

        <p class="capital-values" style="margin-top: 15px;">
          {{ formatCurrency(startValue) }} → {{ formatCurrency(endValue) }}
        </p>
        <div class="capital-growth">
          <p>Прирост: {{ formatCurrency(growthAmount) }}</p>
          <p class="value-change positive" style="margin-left: 30px;">+{{ growthPercent }}%</p>
        </div>
        
      </div>
      <div class="capital-filters">
        <button
          v-for="period in ['1M','1Y','All']"
          :key="period"
          @click="selectedPeriod = period"
          :class="['filter-btn', { active: selectedPeriod === period }]"
        >
          {{ period === '1M' ? 'Месяц' : period === '1Y' ? 'Год' : 'Все время' }}
        </button>
      </div>
    </div>

    <div class="chart-wrapper">
      <canvas id="capitalChart"></canvas>
    </div>
  </div>
</template>

<style scoped>
.widget {
  grid-row: span 3;
  grid-column: span 3;
  background-color: #fff;
  padding: var(--spacing);
  border-radius: 14px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  height: 100%;
}
.capital-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}
.capital-info { max-width: 60%; }
.capital-growth {
  display: flex;
  justify-content: space-between;
}
.capital-filters {
  display: flex;
  background-color: #f3f4f6;
  padding: 0.25rem;
  border-radius: 8px;
  gap: 0.25rem;
}
.filter-btn {
  border: none;
  background: transparent;
  border-radius: 6px;
  padding: 0.5rem 0.9rem;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background-color 0.2s,color 0.2s;
}
.filter-btn:hover { background-color: #e5e7eb; }
.filter-btn.active {
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  color: #5478EA;
  font-weight: 600;
}
.chart-wrapper { flex:1; position: relative; }
</style>
