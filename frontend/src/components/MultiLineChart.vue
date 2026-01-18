<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue' // Добавил onUnmounted
import {
  Chart,
  LineElement,
  PointElement,
  LineController,
  CategoryScale,
  LinearScale,
  Filler,
  Tooltip,
  Legend
} from 'chart.js'

Chart.register(LineElement, PointElement, LineController, CategoryScale, LinearScale, Filler, Tooltip, Legend)

const props = defineProps({
  chartData: {
    type: Object,
    required: true
  },
  period: {
    type: String,
    default: "All"
  },
  formatCurrency: {
    type: Function,
    default: (x) => x
  }
})

// Ссылка на DOM-элемент канваса (вместо ID)
const chartCanvas = ref(null)
let chartInstance = null

/* --------------------------------------------------------------------------
   ДАТЫ И АГРЕГАЦИЯ ПОД ПЕРИОДЫ
-------------------------------------------------------------------------- */
function aggregateData(dataObj, period) {
  if (!dataObj?.labels?.length) return { labels: [], datasets: [] }

  const today = new Date()
  
  // Вспомогательная функция для нормализации даты до начала дня
  const normalizeDate = (date) => {
    const d = new Date(date)
    d.setHours(0, 0, 0, 0)
    return d
  }
  
  const parseDate = (d) => normalizeDate(new Date(d))

  const points = dataObj.labels.map((label, index) => ({
    date: parseDate(label),
    values: dataObj.datasets.map(ds => ds.data[index])
  })).sort((a, b) => a.date - b.date)

  const firstPoint = points[0]?.date

  let firstDate
  if (period === '1M') {
    firstDate = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 30)
  } else if (period === '1Y') {
    firstDate = new Date(today.getFullYear(), today.getMonth() - 11, 1)
  } else {
    firstDate = firstPoint ? new Date(firstPoint) : new Date(today)
  }
  
  // Нормализуем даты до начала дня
  firstDate = normalizeDate(firstDate)
  const lastDate = normalizeDate(today) // Последний день - сегодня (включительно)
  
  const labels = []
  const datasetBuffers = dataObj.datasets.map(() => [])
  let idx = 0
  let lastValues = new Array(dataObj.datasets.length).fill(0)

  // Итерируемся по дням, включая последний день
  for (let d = new Date(firstDate); d <= lastDate; d.setDate(d.getDate() + 1)) {
    const currentDay = normalizeDate(d)
    
    if (currentDay < firstPoint) {
      datasetBuffers.forEach((arr) => arr.push(0))
    } else {
      // Обновляем lastValues до последней точки, которая <= текущего дня
      while (idx < points.length && points[idx].date <= currentDay) {
        lastValues = points[idx].values
        idx++
      }
      datasetBuffers.forEach((arr, i) => arr.push(lastValues[i]))
    }
    labels.push(currentDay.toISOString().split("T")[0])
  }

  return { labels, datasets: datasetBuffers }
}

/* --------------------------------------------------------------------------
    ОКРУГЛЕНИЕ ОКНА Y
-------------------------------------------------------------------------- */
function getNiceMax(value) {
  if (value <= 0) {
    // Для нулевых или отрицательных значений используем небольшой диапазон
    return 100
  }
  
  // Добавляем 10% к максимальному значению
  const padded = value * 1.1
  
  // Определяем порядок величины (логарифм по основанию 10)
  const order = padded < 1 && padded > 0 
    ? Math.floor(Math.log10(padded)) 
    : Math.floor(Math.log10(padded))
  
  // Вычисляем базовую величину (степень 10)
  const magnitude = Math.pow(10, order)
  
  // Выбираем "круглый" шаг округления в зависимости от порядка величины
  let step
  if (order < 0) {
    // Для значений меньше 1 (0.1, 0.01, 0.001 и т.д.)
    // Шаг: 0.1, 0.01, 0.001 и т.д. (кратные 5)
    step = magnitude * 5
  } else if (order === 0) {
    // Для единиц (1-9): шаг 5
    step = 5
  } else if (order === 1) {
    // Для десятков (10-99): шаг 10
    step = 10
  } else if (order === 2) {
    // Для сотен (100-999): шаг 50
    step = 50
  } else if (order === 3) {
    // Для тысяч (1000-9999): шаг 500
    step = 500
  } else if (order === 4) {
    // Для десятков тысяч (10000-99999): шаг 5000
    step = 5000
  } else if (order === 5) {
    // Для сотен тысяч (100000-999999): шаг 50000
    step = 50000
  } else {
    // Для миллионов и выше: шаг = 5 * порядок
    step = magnitude * 5
  }
  
  // Округляем вверх до ближайшего кратного шага
  const rounded = Math.ceil(padded / step) * step
  
  // Убеждаемся, что округленное значение не меньше исходного (с запасом)
  return rounded < padded ? rounded + step : rounded
}

function getNiceMin(value) {
  // Нижняя граница всегда 0
  return 0
}

/* --------------------------------------------------------------------------
   РЕНДЕР ГРАФИКА
-------------------------------------------------------------------------- */
const renderChart = (aggr) => {
  // ИСПОЛЬЗУЕМ REF ВМЕСТО getElementById
  const ctx = chartCanvas.value?.getContext("2d")
  if (!ctx) return

  const allValues = aggr.datasets.flat()
  // Нижняя граница всегда 0, верхняя округляется с запасом 10%
  const yMin = 0
  const maxValue = allValues.length > 0 ? Math.max(...allValues) : 100
  const yMax = getNiceMax(maxValue)

  const datasets = props.chartData.datasets.map((ds, i) => {
    const base = {
      label: ds.label,
      data: aggr.datasets[i],
      borderColor: ds.color,
      borderWidth: i === 0 ? 3 : 2,
      tension: i === 0 ? 0.4 : 0.35,
      pointRadius: 0,
      pointHoverRadius: i === 0 ? 6 : 4,
      pointBackgroundColor: ds.color,
      pointBorderColor: '#fff',
      pointBorderWidth: 2
    }

    if (ds.fill) {
      base.fill = true
      base.backgroundColor = (context) => {
        const chart = context.chart
        const { ctx, chartArea } = chart
        if (!chartArea) return null
        const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
        gradient.addColorStop(0, ds.color + '33')
        gradient.addColorStop(1, ds.color + '00')
        return gradient
      }
    } else base.fill = false

    return base
  })

  // ОБНОВЛЕНИЕ СУЩЕСТВУЮЩЕГО
  if (chartInstance) {
    chartInstance.data.labels = aggr.labels
    chartInstance.data.datasets = datasets
    chartInstance.options.scales.y.min = yMin
    chartInstance.options.scales.y.max = yMax
    chartInstance.update()
    return
  }

  // СОЗДАНИЕ НОВОГО (ВАЖНО: Добавлена проверка на случай HMR)
  // Если канвас уже используется (например, Chart.js не успел очиститься), уничтожаем старый экземпляр
  // Chart.getChart(ctx) ищет существующий инстанс на этом канвасе
  const existingChart = Chart.getChart(ctx)
  if (existingChart) {
    existingChart.destroy()
  }

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: aggr.labels,
      datasets
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
            callback: v => (v >= 1000 ? v / 1000 + 'k' : v),
            color: '#9ca3af',
            padding: 10
          },
          grid: { color: '#e5e7eb', borderDash: [5, 5], drawBorder: false }
        },

        x: {
          type: 'category',
          ticks: {
            color: '#9ca3af',
            autoSkip: false,
            maxRotation: 0,
            minRotation: 0,
            callback: function (value, index) {
              const labels = this.chart.data.labels
              if (!labels || index >= labels.length) return ''
              const d = new Date(labels[index])
              const prev = index > 0 ? new Date(labels[index - 1]) : null
              const first = new Date(labels[0])
              const last = new Date(labels[labels.length - 1])
              const totalDays = (last - first) / 86400000

              if (totalDays <= 45) {
                const step = Math.ceil(labels.length / 45) || 1
                if (index === 0) return d.getDate()
                if (prev && d.getMonth() !== prev.getMonth())
                  return d.toLocaleString('ru-RU', { month: 'short' })
                if (index % step === 0) return d.getDate()
                return ''
              }

              if (index === 0 && d.getDate() < 15)
                return d.getMonth() === 0
                  ? d.getFullYear()
                  : d.toLocaleString('ru-RU', { month: 'short' })

              if (prev && d.getFullYear() !== prev.getFullYear())
                return d.getFullYear()

              if (prev && d.getMonth() !== prev.getMonth()) {
                if (totalDays > 540) {
                  if (d.getMonth() % 3 === 0)
                    return d.toLocaleString('ru-RU', { month: 'short' })
                } else {
                  return d.toLocaleString('ru-RU', { month: 'short' })
                }
              }

              return ''
            }
          },
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
          callbacks: {
            beforeBody(items) {
              items.sort((a, b) => b.parsed.y - a.parsed.y)
            },
            title: (ctx) => ctx[0].label,
            label: (ctx) => `${ctx.dataset.label}: ${props.formatCurrency(ctx.parsed.y)}`
          }
        }
      }
    }
  })
}

/* -------------------------------------------------------------------------- */

const update = () => {
  const aggr = aggregateData(props.chartData, props.period)
  renderChart(aggr)
}

watch(() => props.chartData, update, { deep: true })
watch(() => props.period, update)

onMounted(update)

// ЧИСТКА ПРИ УДАЛЕНИИ КОМПОНЕНТА
onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
})
</script>

<template>
  <div class="chart-container">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  position: relative;
}
</style>