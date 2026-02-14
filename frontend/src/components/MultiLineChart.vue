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
  chartType: {
    type: String,
    default: null // 'position' | 'quantity' | 'price' или null
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
  } else {
    step = 5 * 10**(order - 1)
  }
  
  // Округляем вверх до ближайшего кратного шага
  const rounded = Math.ceil(padded / step) * step
  
  // Убеждаемся, что округленное значение не меньше исходного (с запасом)
  return rounded < padded ? rounded + step : rounded
}

function getNiceMin(value) {
  // Если значение >= 0, нижняя граница всегда 0
  if (value >= 0) {
    return 0
  }
  
  // Для отрицательных значений вычисляем "nice" минимальное значение
  // Аналогично getNiceMax, но округляем вниз
  
  // Вычитаем 10% от минимального значения для запаса
  const padded = value * 1.1
  
  // Определяем порядок величины (логарифм по основанию 10)
  // Для отрицательных чисел берем абсолютное значение
  const absValue = Math.abs(padded)
  const order = absValue < 1 && absValue > 0 
    ? Math.floor(Math.log10(absValue)) 
    : Math.floor(Math.log10(absValue))
  
  // Вычисляем базовую величину (степень 10)
  const magnitude = Math.pow(10, order)
  
  // Выбираем "круглый" шаг округления в зависимости от порядка величины
  let step
  if (order < 0) {
    step = magnitude * 5
  } else if (order === 0) {
    step = 5
  } else if (order === 1) {
    step = 10
  } else if (order === 2) {
    step = 50
  } else if (order === 3) {
    step = 500
  } else if (order === 4) {
    step = 5000
  } else if (order === 5) {
    step = 50000
  } else {
    step = magnitude * 1.2
  }
  
  // Округляем вниз до ближайшего кратного шага
  const rounded = Math.floor(padded / step) * step
  
  // Убеждаемся, что округленное значение не больше исходного (с запасом)
  return rounded > padded ? rounded - step : rounded
}

/* --------------------------------------------------------------------------
   РЕНДЕР ГРАФИКА
-------------------------------------------------------------------------- */
const renderChart = (aggr) => {
  // ИСПОЛЬЗУЕМ REF ВМЕСТО getElementById
  const ctx = chartCanvas.value?.getContext("2d")
  if (!ctx) return

  const allValues = aggr.datasets.flat()
  
  // Находим минимальное и максимальное значения
  const minValue = allValues.length > 0 ? Math.min(...allValues) : 0
  const maxValue = allValues.length > 0 ? Math.max(...allValues) : 100
  
  // Вычисляем диапазон значений
  const range = maxValue - minValue
  
  // Для коротких периодов (месяц) или графика цены единицы используем адаптивную шкалу
  // Если диапазон мал относительно значений, используем более точную шкалу
  let yMin, yMax
  
  // Применяем адаптивную шкалу для периода "месяц" с малыми изменениями
  const shouldUseAdaptiveScale = 
    props.period === '1M' && 
    range > 0 && 
    range < maxValue * 0.1
  
  if (shouldUseAdaptiveScale) {
    // Для месяца с малыми изменениями используем шкалу, основанную на диапазоне
    // Добавляем запас 15% сверху и снизу для лучшей визуализации
    const padding = range * 0.15
    const adjustedMin = minValue - padding
    const adjustedMax = maxValue + padding
    
    // Округляем до "красивых" значений, но с учетом малого диапазона
    const rangeOrder = Math.floor(Math.log10(range))
    let step
    if (rangeOrder < 0) {
      step = Math.pow(10, rangeOrder) * 5
    } else if (rangeOrder === 0) {
      step = 1
    } else if (rangeOrder === 1) {
      step = 10
    } else if (rangeOrder === 2) {
      step = 100
    } else if (rangeOrder === 3) {
      step = 1000
    } else {
      step = Math.pow(10, rangeOrder - 1) * 5
    }
    
    yMin = Math.floor(adjustedMin / step) * step
    yMax = Math.ceil(adjustedMax / step) * step
    
    // Убеждаемся, что min не меньше реального минимума, а max не больше реального максимума
    if (yMin > minValue) yMin = Math.floor(minValue / step) * step
    if (yMax < maxValue) yMax = Math.ceil(maxValue / step) * step
  } else {
    // Для длинных периодов используем стандартную логику
    // Если есть значения ниже нуля, нижняя граница динамически подстраивается
    // Если все значения выше или равны нулю, нижняя граница = 0
    yMin = minValue < 0 ? getNiceMin(minValue) : 0
    yMax = getNiceMax(maxValue)
  }

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

  // Получаем цвета из CSS переменных
  const getCSSVariable = (varName) => {
    if (typeof window !== 'undefined') {
      return getComputedStyle(document.documentElement).getPropertyValue(varName).trim() || '#6b7280'
    }
    return '#6b7280'
  }
  
  const axisText = getCSSVariable('--axis-text') || '#6b7280'
  const axisTextLight = getCSSVariable('--axis-text-light') || '#9ca3af'
  const axisGrid = getCSSVariable('--axis-grid') || '#e5e7eb'

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
          grid: {
            color: axisGrid,
            drawBorder: false,
            lineWidth: 1,
            drawTicks: false,
            tickLength: 0
          },
          border: {
            display: false
          },
          ticks: {
            callback: v => {
              const absValue = Math.abs(v)
              if (absValue >= 1000) {
                const kValue = v / 1000
                const formatted = Math.abs(kValue) % 1 === 0 
                  ? kValue.toFixed(0) 
                  : kValue.toFixed(1)
                return `${formatted}K`
              }
              return v.toString()
            },
            color: axisTextLight,
            font: {
              size: 12,
              family: 'Inter, system-ui, sans-serif',
              weight: '500'
            },
            padding: 12,
            stepSize: null,
            maxTicksLimit: 8
          }
        },

        x: {
          type: 'category',
          grid: {
            display: false,
            drawBorder: false
          },
          border: {
            display: false
          },
          ticks: {
            color: axisText,
            font: {
              size: 12,
              family: 'Inter, system-ui, sans-serif',
              weight: '500'
            },
            autoSkip: false,
            maxRotation: 0,
            minRotation: 0,
            padding: 12,
            callback: function (value, index) {
              const labels = this.chart.data.labels
              if (!labels || index >= labels.length) return ''
              
              let d
              try {
                d = new Date(labels[index])
                if (isNaN(d.getTime())) return ''
              } catch (e) {
                return ''
              }
              
              const prev = index > 0 ? (() => {
                try {
                  const prevDate = new Date(labels[index - 1])
                  return isNaN(prevDate.getTime()) ? null : prevDate
                } catch {
                  return null
                }
              })() : null
              
              const first = (() => {
                try {
                  const firstDate = new Date(labels[0])
                  return isNaN(firstDate.getTime()) ? null : firstDate
                } catch {
                  return null
                }
              })()
              
              const last = (() => {
                try {
                  const lastDate = new Date(labels[labels.length - 1])
                  return isNaN(lastDate.getTime()) ? null : lastDate
                } catch {
                  return null
                }
              })()
              
              if (!first || !last) return ''
              
              const totalDays = (last - first) / 86400000

              // Старая логика форматирования подписей
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