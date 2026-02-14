<script setup>
import { computed } from 'vue'
import LineChart from '../../charts/LineChart.vue'
import Widget from '../base/Widget.vue'
import EmptyState from '../base/EmptyState.vue'
import { formatMoney } from '../../../utils/formatCurrency.js'

const props = defineProps({
  history: {
    type: Array,
    default: () => []
  }
})

const chartLabels = computed(() => {
  if (!props.history?.length) return []
  // Берем последние 30 точек для читаемости
  const recentHistory = props.history.slice(-30)
  return recentHistory.map(h => {
    if (typeof h === 'string') return h
    return h.date || h.month || ''
  })
})

const chartDatasets = computed(() => {
  if (!props.history?.length) return []
  
  const recentHistory = props.history.slice(-30)
  const values = recentHistory.map(h => {
    if (typeof h === 'object') {
      return h.value || h.total_value || 0
    }
    return 0
  })
  
  return [{
    label: 'Стоимость портфеля',
    data: values,
    borderColor: '#3b82f6',
    backgroundColor: 'rgba(59, 130, 246, 0.15)',
    fill: true,
    pointBackgroundColor: '#3b82f6',
    pointBorderColor: '#fff',
    pointBorderWidth: 2,
    pointHoverBackgroundColor: '#2563eb',
    pointHoverBorderColor: '#fff',
    pointHoverBorderWidth: 3,
    borderWidth: 3
  }]
})
</script>

<template>
  <Widget title="Динамика стоимости портфеля">
    <div class="chart-container">
      <LineChart
        v-if="history && history.length > 0"
        :labels="chartLabels"
        :datasets="chartDatasets"
        :format-value="formatMoney"
        height="300px"
      />
      <EmptyState v-else message="Нет данных о динамике портфеля" />
    </div>
  </Widget>
</template>

<style scoped>
.chart-container {
  height: 300px;
  position: relative;
}
</style>
