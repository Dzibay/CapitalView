<script setup>
import { ref, onMounted, watch, onUnmounted, nextTick } from 'vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const props = defineProps({
  type: {
    type: String,
    required: true,
    validator: (value) => ['bar', 'line', 'doughnut', 'pie'].includes(value)
  },
  data: {
    type: Object,
    required: true
  },
  options: {
    type: Object,
    default: () => ({})
  },
  height: {
    type: String,
    default: '300px'
  },
  plugins: {
    type: Array,
    default: () => []
  }
})

const chartCanvas = ref(null)
let chartInstance = null

const defaultOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: 'top',
      labels: {
        font: { size: 12, family: 'Inter, system-ui, sans-serif' },
        color: '#6b7280',
        usePointStyle: true,
        padding: 15,
        boxWidth: 12,
        boxHeight: 12
      }
    },
    tooltip: {
      enabled: true,
      backgroundColor: 'rgba(31, 41, 55, 0.95)',
      titleFont: { weight: 'bold', size: 14, family: 'Inter, system-ui, sans-serif' },
      bodyFont: { size: 13, family: 'Inter, system-ui, sans-serif' },
      padding: 12,
      cornerRadius: 8,
      displayColors: true,
      borderColor: 'rgba(255, 255, 255, 0.1)',
      borderWidth: 1,
      boxPadding: 6,
      titleSpacing: 4,
      bodySpacing: 4
    }
  },
  scales: {
    x: {
      display: false,
      grid: {
        display: false
      },
      ticks: {
        display: false
      },
      border: {
        display: false
      }
    },
    y: {
      display: false,
      beginAtZero: true,
      grid: {
        display: false
      },
      ticks: {
        display: false
      },
      border: {
        display: false
      }
    }
  },
  animation: {
    duration: 1000,
    easing: 'easeInOutQuart'
  },
  elements: {
    point: {
      hoverRadius: 6,
      hoverBorderWidth: 2
    }
  }
}

const renderChart = () => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }

  if (!chartCanvas.value) {
    return
  }

  if (!props.data || !props.data.labels || props.data.labels.length === 0) {
    return
  }
  
  if (!props.data.datasets || props.data.datasets.length === 0) {
    return
  }

  const ctx = chartCanvas.value.getContext('2d')
  if (!ctx) return

  const mergedOptions = {
    ...defaultOptions,
    ...props.options
  }

  chartInstance = new Chart(ctx, {
    type: props.type,
    data: props.data,
    options: mergedOptions,
    plugins: props.plugins || []
  })
}

watch(() => props.data, renderChart, { deep: true })
watch(() => props.options, renderChart, { deep: true })
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
  <div class="chart-wrapper" :style="{ height: height }">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<style scoped>
.chart-wrapper {
  position: relative;
  width: 100%;
}
</style>
