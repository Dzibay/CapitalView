<script setup>
import { ref, computed, watch } from 'vue'
import BaseChart from './BaseChart.vue'

const props = defineProps({
  labels: {
    type: Array,
    default: () => []
  },
  values: {
    type: Array,
    default: () => []
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
  },
  /** Подпись доли в процентах в центре (по умолчанию — целое, ru-RU) */
  formatPercentage: {
    type: Function,
    default: null
  },
  /** Растянуть график на высоту/ширину родителя (родитель задаёт размер, например 280×280px) */
  fillParent: {
    type: Boolean,
    default: false
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

watch(
  () => [props.labels, props.values],
  () => {
    centerInfo.value = {
      label: 'Всего',
      value: total.value,
      percentage: 100
    }
  },
  { immediate: true, deep: true }
)

function chartHeight() {
  return props.fillParent ? '100%' : props.height
}

function displayPercentage(pct) {
  if (props.formatPercentage) return props.formatPercentage(pct)
  const n = Math.round(Number(pct))
  return Number.isFinite(n) ? n.toLocaleString('ru-RU') : '0'
}
</script>

<template>
  <div
    class="doughnut-container"
    :class="[`layout-${layout}`, { 'fill-parent': fillParent }]"
  >
    <div class="chart-section">
      <div class="chart-wrapper" :style="{ height: chartHeight() }">
        <BaseChart
          type="doughnut"
          :data="chartData"
          :options="chartOptions"
          :height="chartHeight()"
        />
        <div v-if="cutout !== '0%'" class="chart-center">
          <span class="center-label">{{ centerInfo.label }}</span>
          <span class="center-percentage">{{ displayPercentage(centerInfo.percentage) }}%</span>
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

.doughnut-container.fill-parent {
  width: 100%;
  height: 100%;
  min-height: 0;
}

.doughnut-container.fill-parent .chart-section {
  flex: 1;
  min-height: 0;
  width: 100%;
}

.doughnut-container.fill-parent .chart-wrapper {
  width: 100%;
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
  font-size: var(--text-caption-size);
  color: var(--text-tertiary);
  display: block;
}

.center-percentage {
  font-size: var(--text-value-size);
  font-weight: var(--text-value-weight);
  color: var(--text-primary);
  display: block;
}

.center-value {
  font-size: var(--text-body-secondary-size);
  color: var(--text-secondary);
  display: block;
}

.legend-section {
  flex: 1;
}

.legends {
  display: flex;
  flex-direction: column;
  gap: 16px;
  font-size: var(--text-caption-size);
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
  color: var(--text-primary);
  font-weight: 500;
}

.legend-value {
  color: var(--text-tertiary);
  font-size: var(--text-caption-size);
}
</style>
