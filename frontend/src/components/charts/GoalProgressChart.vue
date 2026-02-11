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
  formatValue: {
    type: Function,
    default: null
  },
  useInflation: {
    type: Boolean,
    default: false
  }
})

const chartData = computed(() => ({
  labels: props.labels,
  datasets: props.datasets.map(dataset => ({
    ...dataset,
    tension: dataset.tension ?? 0.4,
    pointRadius: dataset.pointRadius ?? 0,
    pointHoverRadius: dataset.pointHoverRadius ?? 6,
    pointBorderWidth: dataset.pointBorderWidth ?? 2,
    fill: dataset.fill ?? false
  }))
}))

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
  
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false
    },
    scales: {
      x: {
        display: true,
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
          maxRotation: 45,
          minRotation: 0
        }
      },
      y: {
        beginAtZero: true,
        display: true,
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
          padding: 12,
          stepSize: null,
          maxTicksLimit: 8,
          callback: (value) => {
            if (value >= 1000000) {
              const mValue = value / 1000000
              const formatted = mValue % 1 === 0 
                ? mValue.toFixed(0) 
                : mValue.toFixed(1)
              return `${formatted} млн`
            } else if (value >= 1000) {
              const kValue = value / 1000
              const formatted = kValue % 1 === 0 
                ? kValue.toFixed(0) 
                : kValue.toFixed(1)
              return `${formatted}K`
            }
            return value.toString()
          }
        }
      }
    },
  plugins: {
    legend: {
      display: false
    },
    tooltip: {
      enabled: true,
      backgroundColor: 'rgba(31, 41, 55, 0.95)',
      titleColor: '#fff',
      bodyColor: '#fff',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 8,
      displayColors: false,
      callbacks: props.formatValue ? {
        title: (context) => {
          if (!context || !context[0]) return ''
          return context[0].label || ''
        },
        label: (context) => {
          if (!context || context.parsed.y === null) return null
          
          if (context.dataset.label === 'Достижение цели') return null
          
          const value = props.formatValue(context.parsed.y)
          
          if (props.useInflation && context.dataset.label === 'Прогноз капитала') {
            const goalDataset = context.chart.data.datasets.find(ds => ds.label === 'Целевой капитал')
            if (goalDataset && goalDataset.data && context.dataIndex >= 0) {
              const goalDataValue = goalDataset.data[context.dataIndex]
              if (goalDataValue !== undefined && goalDataValue !== null && !isNaN(Number(goalDataValue)) && Number(goalDataValue) > 0) {
                const goalValue = props.formatValue(Number(goalDataValue))
                return [`Капитал: ${value}`, `Цель: ${goalValue}`]
              }
            }
            return `Капитал: ${value}`
          }
          
          if (context.dataset.label === 'Целевой капитал') return null
          return `Капитал: ${value}`
        },
        filter: (tooltipItem) => {
          if (!tooltipItem) return false
          
          if (tooltipItem.dataset.label === 'Достижение цели') return false
          
          if (props.useInflation) {
            return tooltipItem.parsed.y !== null && tooltipItem.dataset.label === 'Прогноз капитала'
          }
          
          return tooltipItem.parsed.y !== null && tooltipItem.dataset.label === 'Прогноз капитала'
        }
      } : {}
    }
  }
  }
})
</script>

<template>
  <div class="goal-chart-container">
    <BaseChart
      type="line"
      :data="chartData"
      :options="chartOptions"
      :height="height"
    />
  </div>
</template>

<style scoped>
.goal-chart-container {
  width: 100%;
  height: 100%;
  position: relative;
}
</style>
