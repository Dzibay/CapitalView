<script setup>
import { computed } from 'vue'
import LineChart from '../charts/LineChart.vue'

const props = defineProps({
  history: {
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
  <div class="widget">
    <div class="widget-title">
      <div class="widget-title-icon-rect"></div>
      <h2>Динамика стоимости портфеля</h2>
    </div>
    <div class="chart-container">
      <LineChart
        v-if="history && history.length > 0"
        :labels="chartLabels"
        :datasets="chartDatasets"
        :format-value="formatMoney"
        height="300px"
      />
      <div v-else class="empty-state">
        <p>Нет данных о динамике портфеля</p>
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
