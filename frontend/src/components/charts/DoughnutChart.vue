<script setup>
import { ref, computed, watch } from 'vue'
import BaseChart from './BaseChart.vue'

const props = defineProps({
  labels: {
    type: Array,
    required: true
  },
  values: {
    type: Array,
    required: true
  },
  colors: {
    type: Array,
    default: () => [
      '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
      '#f472b6', '#60a5fa', '#fbbf24', '#a78bfa', '#ec4899',
      '#14b8a6', '#f97316', '#6366f1'
    ]
  },
  height: {
    type: String,
    default: '300px'
  },
  cutout: {
    type: String,
    default: '75%'
  },
  showLegend: {
    type: Boolean,
    default: true
  },
  formatValue: {
    type: Function,
    default: null
  },
  layout: {
    type: String,
    default: 'vertical', // 'vertical' or 'horizontal'
    validator: (value) => ['vertical', 'horizontal'].includes(value)
  }
})

const centerInfo = ref({
  label: 'Всего',
  percentage: 100,
  value: 0
})

const total = computed(() => {
  return props.values.reduce((a, b) => a + b, 0)
})

const chartData = computed(() => ({
  labels: props.labels,
  datasets: [{
    data: props.values,
    backgroundColor: props.colors.slice(0, props.values.length)
  }]
}))

const chartOptions = computed(() => ({
  cutout: props.cutout,
  plugins: {
    legend: {
      display: props.showLegend && props.layout === 'vertical',
      position: 'bottom'
    },
    tooltip: {
      enabled: false,
      external: (context) => {
        const tooltipModel = context.tooltip
        if (tooltipModel.dataPoints?.length) {
          const index = tooltipModel.dataPoints[0].dataIndex
          const label = props.labels[index]
          const value = props.values[index]
          const percent = total.value > 0 ? Math.round((value / total.value) * 100) : 0
          centerInfo.value = { 
            label, 
            value, 
            percentage: percent 
          }
        } else {
          centerInfo.value = {
            label: 'Всего',
            value: total.value,
            percentage: 100
          }
        }
      }
    }
  },
  onHover: (event, activeElements, chart) => {
    if (activeElements && activeElements.length > 0) {
      const index = activeElements[0].index
      const label = props.labels[index]
      const value = props.values[index]
      const percent = total.value > 0 ? Math.round((value / total.value) * 100) : 0
      centerInfo.value = { label, value, percentage: percent }
    } else {
      centerInfo.value = {
        label: 'Всего',
        value: total.value,
        percentage: 100
      }
    }
  }
}))

watch(() => props.values, () => {
  centerInfo.value = {
    label: 'Всего',
    value: total.value,
    percentage: 100
  }
}, { immediate: true })
</script>

<template>
  <div class="doughnut-container" :class="`layout-${layout}`">
    <div class="chart-section">
      <div class="chart-wrapper" :style="{ height: height }">
        <BaseChart
          type="doughnut"
          :data="chartData"
          :options="chartOptions"
          :height="height"
        />
        <div v-if="cutout !== '0%'" class="chart-center">
          <span class="center-label">{{ centerInfo.label }}</span>
          <span class="center-percentage">{{ centerInfo.percentage }}%</span>
          <span v-if="formatValue" class="center-value">{{ formatValue(centerInfo.value) }}</span>
        </div>
      </div>
    </div>
    
    <div v-if="showLegend && layout === 'horizontal'" class="legend-section">
      <div class="legends">
        <div 
          v-for="(label, i) in labels" 
          :key="i" 
          class="legend-item"
        >
          <span 
            class="legend-color" 
            :style="{ backgroundColor: colors[i % colors.length] }"
          ></span>
          <span class="legend-label">{{ label }}</span>
          <span v-if="formatValue" class="legend-value">
            {{ formatValue(values[i]) }} ({{ total > 0 ? Math.round((values[i] / total) * 100) : 0 }}%)
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.doughnut-container {
  display: flex;
  width: 100%;
}

.doughnut-container.layout-vertical {
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.doughnut-container.layout-horizontal {
  flex-direction: row;
  align-items: center;
  gap: 30px;
}

.chart-section {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.chart-wrapper {
  position: relative;
}

.chart-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  pointer-events: none;
}

.center-label {
  font-size: 12px;
  color: #6b7280;
  display: block;
  margin-bottom: 4px;
}

.center-percentage {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
  display: block;
  margin-bottom: 4px;
}

.center-value {
  font-size: 14px;
  color: #4b5563;
  display: block;
}

.legend-section {
  flex: 1;
}

.legends {
  display: flex;
  flex-direction: column;
  gap: 16px;
  font-size: 13px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.legend-color {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-label {
  flex: 1;
  color: #111827;
  font-weight: 500;
}

.legend-value {
  color: #6b7280;
  font-size: 12px;
}
</style>
