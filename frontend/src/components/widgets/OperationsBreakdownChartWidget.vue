<script setup>
import { computed } from 'vue'
import DoughnutChart from '../charts/DoughnutChart.vue'

const props = defineProps({
  operationsBreakdown: {
    type: Array,
    default: () => []
  }
})

const formatMoney = (value) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  }).format(value || 0)
}

const chartLabels = computed(() => {
  return props.operationsBreakdown?.map(op => op.type || 'Unknown') || []
})

const chartValues = computed(() => {
  return props.operationsBreakdown?.map(op => Math.abs(op.sum || 0)) || []
})
</script>

<template>
  <div class="widget">
    <div class="widget-title">
      <div class="widget-title-icon-rect"></div>
      <h2>Распределение операций</h2>
    </div>
    <div class="chart-container">
      <DoughnutChart
        v-if="operationsBreakdown && operationsBreakdown.length > 0"
        :labels="chartLabels"
        :values="chartValues"
        layout="vertical"
        :format-value="formatMoney"
        height="300px"
        :show-legend="true"
      />
      <div v-else class="empty-state">
        <p>Нет данных об операциях</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.widget {
  background-color: #fff;
  padding: var(--spacing);
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

.widget-title {
  display: flex;
  gap: 5px;
  align-items: center;
}

.widget-title-icon-rect {
  padding: 5px;
  width: 25px;
  height: 25px;
  border-radius: 6px;
  background-color: #F6F6F6;
}

.widget-title h2 {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.chart-container {
  height: 300px;
  position: relative;
}

.empty-state {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #6b7280;
  font-size: 14px;
  background: white;
  z-index: 10;
}

.empty-state p {
  margin: 0;
}
</style>
