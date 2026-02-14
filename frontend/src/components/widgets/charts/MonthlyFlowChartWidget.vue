<script setup>
import { computed, ref } from 'vue'
import BarChart from '../../charts/BarChart.vue'
import Widget from '../base/Widget.vue'
import ToggleSwitch from '../../base/ToggleSwitch.vue'

const props = defineProps({
  monthlyFlow: {
    type: Array,
    default: () => []
  }
})

const showInflow = ref(true)
const showOutflow = ref(true)
const showDifference = ref(false)

const formatMoney = (value) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  }).format(value || 0)
}

const chartLabels = computed(() => {
  return props.monthlyFlow?.map(m => m.month) || []
})

const chartDatasets = computed(() => {
  const datasets = []
  
  if (showInflow.value) {
    datasets.push({
      label: 'Приток',
      data: props.monthlyFlow?.map(m => m.inflow || 0) || [],
      backgroundColor: 'rgba(16, 185, 129, 0.9)',
      borderColor: 'transparent',
      borderWidth: 0,
      hoverBackgroundColor: 'rgba(16, 185, 129, 1)',
      hoverBorderColor: 'transparent',
      categoryPercentage: 0.8,
      barPercentage: 0.95
    })
  }
  
  if (showOutflow.value) {
    datasets.push({
      label: 'Отток',
      data: props.monthlyFlow?.map(m => m.outflow || 0) || [],
      backgroundColor: 'rgba(239, 68, 68, 0.9)',
      borderColor: 'transparent',
      borderWidth: 0,
      hoverBackgroundColor: 'rgba(239, 68, 68, 1)',
      hoverBorderColor: 'transparent',
      categoryPercentage: 0.8,
      barPercentage: 0.95
    })
  }
  
  if (showDifference.value) {
    datasets.push({
      label: 'Чистый приток',
      data: props.monthlyFlow?.map(m => (m.inflow || 0) + (m.outflow || 0)) || [],
      backgroundColor: 'rgba(59, 130, 246, 0.9)',
      borderColor: 'transparent',
      borderWidth: 0,
      hoverBackgroundColor: 'rgba(59, 130, 246, 1)',
      hoverBorderColor: 'transparent',
      categoryPercentage: 0.8,
      barPercentage: 0.95
    })
  }
  
  return datasets
})
</script>

<template>
  <Widget title="Месячные потоки">
    <template #header>
      <div class="chart-controls">
        <ToggleSwitch 
          v-model="showInflow"
          label="Приток"
          active-color="#10b981"
          hover-color="#059669"
        />
        <ToggleSwitch 
          v-model="showOutflow"
          label="Отток"
          active-color="#ef4444"
          hover-color="#dc2626"
        />
        <ToggleSwitch 
          v-model="showDifference"
          label="Чистый приток"
          active-color="#3b82f6"
          hover-color="#2563eb"
        />
      </div>
    </template>
    <div class="chart-container">
      <BarChart
        v-if="monthlyFlow && monthlyFlow.length > 0 && chartDatasets.length > 0"
        :key="`${showInflow}-${showOutflow}-${showDifference}`"
        :labels="chartLabels"
        :datasets="chartDatasets"
        :format-value="formatMoney"
        height="300px"
      />
      <div v-else-if="chartDatasets.length === 0" class="empty-state">
        <p>Выберите хотя бы один тип данных для отображения</p>
      </div>
      <div v-else class="empty-state">
        <p>Нет данных о месячных потоках</p>
      </div>
    </div>
  </Widget>
</template>

<style scoped>
/* Убраны стили .widget, .widget-header, .widget-title - теперь используется компонент Widget */

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

.chart-controls {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
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
