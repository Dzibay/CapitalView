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

const chartOptions = computed(() => ({
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
      ticks: {
        color: '#9ca3af',
        font: {
          size: 10,
          weight: '400'
        },
        padding: 8,
        maxRotation: 0,
        minRotation: 0
      }
    },
    y: {
      beginAtZero: true,
      display: true,
      grid: {
        color: '#f3f4f6',
        drawBorder: false,
        lineWidth: 1,
        borderDash: [4, 4]
      },
      ticks: {
        color: '#9ca3af',
        font: {
          size: 10
        },
        padding: 8,
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
            return `${formatted}К`
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
}))
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
