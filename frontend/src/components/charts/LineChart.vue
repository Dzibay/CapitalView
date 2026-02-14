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
  }
})

const chartData = computed(() => ({
  labels: props.labels,
  datasets: props.datasets.map(dataset => ({
    ...dataset,
    tension: dataset.tension ?? 0.4,
    pointRadius: dataset.pointRadius ?? 4,
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
  
  // Форматирование для оси Y
  const formatYTick = (value) => {
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
    scales: {
      x: {
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
    },
  plugins: {
    tooltip: {
      callbacks: props.formatValue ? {
        label: (context) => {
          const label = context.dataset.label || ''
          const value = props.formatValue(context.parsed.y)
          return `${label}: ${value}`
        }
      } : {}
    }
  }
  }
})
</script>

<template>
  <BaseChart
    type="line"
    :data="chartData"
    :options="chartOptions"
    :height="height"
  />
</template>
