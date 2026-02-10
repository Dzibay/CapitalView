<script setup>
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

const chartData = {
  labels: props.labels,
  datasets: props.datasets.map(dataset => ({
    ...dataset,
    tension: dataset.tension ?? 0.4,
    pointRadius: dataset.pointRadius ?? 4,
    pointHoverRadius: dataset.pointHoverRadius ?? 6,
    pointBorderWidth: dataset.pointBorderWidth ?? 2,
    fill: dataset.fill ?? false
  }))
}

const chartOptions = {
  scales: {
    x: {
      grid: { display: false },
      ticks: {
        color: '#6b7280',
        font: {
          size: 11
        }
      }
    },
    y: {
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
        padding: 8,
        callback: (value) => {
          // Универсальное форматирование: 1K вместо 1000 для всех графиков
          if (value >= 1000) {
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
</script>

<template>
  <BaseChart
    type="line"
    :data="chartData"
    :options="chartOptions"
    :height="height"
  />
</template>
