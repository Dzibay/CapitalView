<script setup>
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'

const props = defineProps({
  labels: {
    type: Array,
    required: true
  },
  datasets: {
    type: Array,
    required: true
  },
  height: {
    type: String,
    default: '300px'
  },
  stacked: {
    type: Boolean,
    default: false
  },
  formatValue: {
    type: Function,
    default: null
  },
  showTotals: {
    type: Boolean,
    default: false
  },
  totals: {
    type: Array,
    default: () => []
  }
})

// Кастомный плагин для отображения сумм на вершине столбцов
const totalsPlugin = computed(() => {
  if (!props.showTotals || !props.totals.length || !props.formatValue) {
    return null
  }
  
  return {
    id: 'totalsPlugin',
    afterDraw: (chart) => {
      const ctx = chart.ctx
      const chartArea = chart.chartArea
      
      if (!chartArea) return
      
      ctx.save()
      ctx.textAlign = 'center'
      ctx.textBaseline = 'bottom'
      
      // Для stacked графиков находим верхний столбец
      const datasetCount = chart.data.datasets.length
      const firstMeta = chart.getDatasetMeta(0)
      
      if (!firstMeta || !firstMeta.data) return
      
      firstMeta.data.forEach((bar, index) => {
        const total = props.totals[index] || 0
        if (total > 0 && bar) {
          const x = bar.x
          let topY = chartArea.top
          
          // Если stacked, находим самую верхнюю точку всех слоев
          if (props.stacked && datasetCount > 1) {
            let minTopY = Infinity
            for (let i = 0; i < datasetCount; i++) {
              const meta = chart.getDatasetMeta(i)
              if (meta && meta.data && meta.data[index]) {
                const barElement = meta.data[index]
                // Для stacked баров y верхнего края = y - height
                const barTopY = barElement.y - barElement.height
                minTopY = Math.min(minTopY, barTopY)
              }
            }
            if (minTopY !== Infinity) {
              topY = minTopY
            }
          } else {
            // Для не-stacked берем верх столбца
            if (bar.height) {
              topY = bar.y - bar.height
            }
          }
          
          // Размещаем текст прямо над столбцом (без отступа)
          const textY = topY
          const text = props.formatValue(total)
          
          // Вычисляем высоту текста для проверки видимости
          ctx.font = '600 12px Inter, system-ui, sans-serif'
          const textMetrics = ctx.measureText(text)
          const textHeight = 12 // примерная высота текста
          
          // Проверяем, что текст помещается в видимую область (с небольшим запасом сверху)
          const minY = chartArea.top + textHeight + 2
          const maxY = chartArea.bottom
          
          if (textY >= minY && textY <= maxY) {
            // Стиль текста как на примере
            ctx.fillStyle = '#374151'
            
            // Очень легкая белая тень для читаемости
            ctx.shadowColor = 'rgba(255, 255, 255, 0.9)'
            ctx.shadowBlur = 2
            ctx.shadowOffsetX = 0
            ctx.shadowOffsetY = 0
            
            ctx.fillText(text, x, textY)
            
            // Убираем тень
            ctx.shadowColor = 'transparent'
            ctx.shadowBlur = 0
          } else if (textY < minY) {
            // Если столбец слишком высокий, размещаем текст внизу видимой области
            const adjustedY = minY
            ctx.fillStyle = '#374151'
            ctx.shadowColor = 'rgba(255, 255, 255, 0.9)'
            ctx.shadowBlur = 2
            ctx.shadowOffsetX = 0
            ctx.shadowOffsetY = 0
            ctx.fillText(text, x, adjustedY)
            ctx.shadowColor = 'transparent'
            ctx.shadowBlur = 0
          }
        }
      })
      
      ctx.restore()
    }
  }
})

const chartData = computed(() => {
  return {
    labels: props.labels,
    datasets: props.datasets.map(dataset => ({
      ...dataset,
      borderRadius: dataset.borderRadius ?? (props.stacked ? 0 : 10),
      borderSkipped: dataset.borderSkipped ?? false,
      maxBarThickness: dataset.maxBarThickness ?? 50,
      barThickness: dataset.barThickness ?? undefined,
      categoryPercentage: props.stacked ? 0.8 : 0.6,
      barPercentage: props.stacked ? 0.9 : 0.7
    }))
  }
})

const chartOptions = computed(() => {
  // Универсальное форматирование для оси Y (1K вместо 1000)
  const formatYTick = (value) => {
    // Всегда используем формат с K для оси Y (работает и для отрицательных значений)
    const absValue = Math.abs(value)
    if (absValue >= 1000) {
      const kValue = value / 1000
      const formatted = Math.abs(kValue) % 1 === 0 
        ? kValue.toFixed(0) 
        : kValue.toFixed(1)
      return `${formatted}K`
    }
    return value.toString()
  }
  
  return {
    interaction: {
      mode: 'index',
      intersect: false
    },
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        backgroundColor: 'rgba(31, 41, 55, 0.95)',
        titleColor: '#fff',
        bodyColor: '#fff',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
        displayColors: true,
        callbacks: props.formatValue ? {
          title: (context) => {
            return context[0].label || ''
          },
          label: (context) => {
            const label = context.dataset.label || ''
            // Для stacked графика используем raw значение, для обычного - parsed.y
            const rawValue = context.raw !== undefined ? context.raw : context.parsed.y
            // Пропускаем элементы с нулевым значением
            if (!rawValue || rawValue === 0) {
              return null
            }
            const value = props.formatValue(rawValue)
            return `${label}: ${value}`
          },
          filter: (tooltipItem) => {
            // Фильтруем элементы с нулевым значением
            const rawValue = tooltipItem.raw !== undefined ? tooltipItem.raw : tooltipItem.parsed.y
            return rawValue && rawValue !== 0
          },
          footer: (tooltipItems) => {
            if (props.stacked && tooltipItems.length > 0) {
              // Для stacked графика суммируем raw значения только ненулевых элементов
              const total = tooltipItems.reduce((sum, item) => {
                const rawValue = item.raw !== undefined ? item.raw : item.parsed.y
                return sum + (rawValue || 0)
              }, 0)
              if (total > 0) {
                return `Итого: ${props.formatValue(total)}`
              }
            }
            return ''
          }
        } : {}
      }
    },
    scales: {
      x: {
        stacked: props.stacked,
        grid: { display: false },
        ticks: {
          color: '#6b7280',
          font: {
            size: 11
          }
        }
      },
      y: {
        stacked: props.stacked,
        beginAtZero: true,
        grid: {
          color: '#e5e7eb',
          drawBorder: false,
          lineWidth: 1
        },
        ticks: {
          color: '#9ca3af',
          font: {
            size: 11
          },
          callback: formatYTick,
          padding: 8
        }
      }
    }
  }
})

const customPlugins = computed(() => {
  if (props.showTotals && props.totals.length > 0 && totalsPlugin.value && totalsPlugin.value.id) {
    return [totalsPlugin.value]
  }
  return []
})
</script>

<template>
  <BaseChart
    type="bar"
    :data="chartData"
    :options="chartOptions"
    :plugins="customPlugins"
    :height="height"
  />
</template>
