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
  xAxisRotation: {
    type: Number,
    default: 0
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
    datasets: props.datasets.map(dataset => {
      // Если borderRadius не задан явно, используем функцию для определения закругления
      // в зависимости от знака значения (положительное - сверху, отрицательное - снизу)
      let borderRadius = dataset.borderRadius
      if (borderRadius === undefined || borderRadius === null) {
        borderRadius = (ctx) => {
          const value = ctx.parsed.y
          // Если значение отрицательное, закругляем нижние углы
          if (value < 0) {
            return {
              topLeft: 0,
              topRight: 0,
              bottomLeft: 6,
              bottomRight: 6
            }
          }
          // Если значение положительное или 0, закругляем верхние углы
          return {
            topLeft: 6,
            topRight: 6,
            bottomLeft: 0,
            bottomRight: 0
          }
        }
      }
      
      return {
        ...dataset,
        borderRadius,
        borderSkipped: dataset.borderSkipped ?? false,
        maxBarThickness: dataset.maxBarThickness ?? 50,
        barThickness: dataset.barThickness ?? undefined,
        categoryPercentage: dataset.categoryPercentage ?? (props.stacked ? 0.8 : 0.6),
        barPercentage: dataset.barPercentage ?? (props.stacked ? 0.9 : 0.7)
      }
    })
  }
})

const chartOptions = computed(() => {
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
    animation: {
      duration: 1200,
      easing: 'easeOutQuart',
      delay: (context) => {
        let delay = 0
        if (context.type === 'data' && context.mode === 'default') {
          delay = context.dataIndex * 50
        }
        return delay
      }
    },
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
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        backdropFilter: 'blur(8px)',
        titleColor: '#ffffff',
        bodyColor: '#f9fafb',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 1,
        padding: 14,
        cornerRadius: 12,
        displayColors: true,
        titleFont: {
          size: 13,
          weight: '600',
          family: 'Inter, system-ui, sans-serif'
        },
        bodyFont: {
          size: 12,
          weight: '500',
          family: 'Inter, system-ui, sans-serif'
        },
        boxPadding: 8,
        titleSpacing: 6,
        bodySpacing: 4,
        usePointStyle: true,
        boxWidth: 12,
        boxHeight: 12,
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
          padding: 12,
          maxRotation: props.xAxisRotation,
          minRotation: props.xAxisRotation,
          autoSkip: props.xAxisRotation > 0 ? false : true,
          maxTicksLimit: undefined,
          callback: function(value, index) {
            const labels = this.chart.data.labels
            if (!labels || index >= labels.length) return ''
            
            const label = labels[index]
            if (!label) return ''
            
            const totalLabels = labels.length
            
            // Адаптивное форматирование в зависимости от количества меток
            // Если меток <= 12: показываем все с полными названиями месяцев
            // Если меток 13-36: показываем каждую 2-ю или 3-ю метку
            // Если меток > 36: показываем только годы
            
            // Проверяем, это квартал или месяц
            if (typeof label === 'string' && label.includes('Q')) {
              // Кварталы: формат может быть "2025-Q1" или "Q1 25"
              let quarterStr = ''
              let year = ''
              
              if (label.includes('-Q')) {
                // Формат "2025-Q1"
                const [y, quarter] = label.split('-Q')
                year = y
                quarterStr = `Q${quarter} ${year.slice(-2)}`
              } else {
                // Формат уже "Q1 25"
                quarterStr = label
                const yearMatch = label.match(/\d{2}$/)
                if (yearMatch) {
                  year = `20${yearMatch[0]}`
                }
              }
              
              if (totalLabels <= 12) {
                // Показываем все кварталы
                return quarterStr
              } else if (totalLabels <= 36) {
                // Показываем каждый 2-й квартал
                if (index % 2 === 0 || index === labels.length - 1) {
                  return quarterStr
                }
                return ''
              } else {
                // Показываем только год
                if (!year && label.includes('-Q')) {
                  const [y] = label.split('-Q')
                  year = y
                }
                if (index === 0 || index === labels.length - 1) {
                  return year || label
                }
                // Показываем год только при смене года
                if (index > 0 && year) {
                  const prevLabel = labels[index - 1]
                  if (prevLabel && typeof prevLabel === 'string') {
                    let prevYear = ''
                    if (prevLabel.includes('-Q')) {
                      const [y] = prevLabel.split('-Q')
                      prevYear = y
                    } else {
                      const yearMatch = prevLabel.match(/\d{2}$/)
                      if (yearMatch) {
                        prevYear = `20${yearMatch[0]}`
                      }
                    }
                    if (prevYear && prevYear !== year) {
                      return year
                    }
                  }
                }
                return ''
              }
            }
            
            // Обработка месяцев
            // Парсим метку месяца (формат: "июнь 25" или "2025-06")
            let monthStr = label
            let year = ''
            let month = ''
            
            // Если метка уже отформатирована как "июнь 25"
            if (typeof label === 'string' && /[а-яё]+\s+\d{2}/i.test(label)) {
              if (totalLabels <= 12) {
                return label
              } else if (totalLabels <= 36) {
                // Показываем каждую 2-ю метку
                if (index % 2 === 0 || index === labels.length - 1) {
                  return label
                }
                return ''
              } else {
                // Извлекаем год из метки
                const yearMatch = label.match(/\d{2}$/)
                if (yearMatch) {
                  const shortYear = yearMatch[0]
                  if (index === 0 || index === labels.length - 1) {
                    return `20${shortYear}`
                  }
                  // Показываем год только при смене
                  if (index > 0) {
                    const prevLabel = labels[index - 1]
                    if (prevLabel && typeof prevLabel === 'string') {
                      const prevYearMatch = prevLabel.match(/\d{2}$/)
                      if (prevYearMatch && prevYearMatch[0] !== shortYear) {
                        return `20${shortYear}`
                      }
                    }
                  }
                }
                return ''
              }
            }
            
            // Если метка в формате "2025-06"
            if (typeof label === 'string' && /^\d{4}-\d{2}/.test(label)) {
              const [y, m] = label.split('-')
              year = y
              month = m
              
              try {
                const date = new Date(parseInt(year), parseInt(month) - 1)
                const monthName = date.toLocaleString('ru-RU', { month: 'short' })
                const yearShort = year.slice(-2)
                
                // Сокращаем длинные названия месяцев
                let shortMonth = monthName
                if (monthName.length > 4) {
                  shortMonth = monthName.slice(0, 4) + '.'
                }
                
                if (totalLabels <= 12) {
                  // Показываем все метки
                  return `${shortMonth} ${yearShort}`
                } else if (totalLabels <= 36) {
                  // Показываем каждую 2-ю метку
                  if (index % 2 === 0 || index === labels.length - 1) {
                    return `${shortMonth} ${yearShort}`
                  }
                  return ''
                } else {
                  // Показываем только год
                  if (index === 0 || index === labels.length - 1) {
                    return year
                  }
                  // Показываем год только при смене года
                  if (index > 0) {
                    const prevLabel = labels[index - 1]
                    if (prevLabel && typeof prevLabel === 'string') {
                      const [prevYear] = prevLabel.split('-')
                      if (prevYear !== year) {
                        return year
                      }
                    }
                  }
                  return ''
                }
              } catch (e) {
                return label
              }
            }
            
            // Если метка уже отформатирована, возвращаем как есть
            return label
          }
        }
      },
      y: {
        stacked: props.stacked,
        beginAtZero: true,
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
          color: axisTextLight,
          font: {
            size: 12,
            family: 'Inter, system-ui, sans-serif',
            weight: '500'
          },
          callback: formatYTick,
          padding: 12,
          stepSize: null,
          maxTicksLimit: 8
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
