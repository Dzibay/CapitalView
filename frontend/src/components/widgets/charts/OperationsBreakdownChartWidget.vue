<script setup>
import { computed } from 'vue'
import DoughnutChart from '../../charts/DoughnutChart.vue'
import Widget from '../base/Widget.vue'
import EmptyState from '../base/EmptyState.vue'
import { formatMoney } from '../../../utils/formatCurrency.js'

const props = defineProps({
  operationsBreakdown: {
    type: Array,
    default: () => []
  }
})

const chartLabels = computed(() => {
  return props.operationsBreakdown?.map(op => op.type || 'Unknown') || []
})

const chartValues = computed(() => {
  return props.operationsBreakdown?.map(op => Math.abs(op.sum || 0)) || []
})
</script>

<template>
  <Widget title="Распределение операций">
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
      <EmptyState v-else message="Нет данных об операциях" />
    </div>
  </Widget>
</template>

<style scoped>
.chart-container {
  height: 300px;
  position: relative;
}
</style>
