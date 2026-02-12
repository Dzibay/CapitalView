<script setup>
import { computed, ref } from 'vue'
import BarChart from '../charts/BarChart.vue'
import Widget from './Widget.vue'

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
      backgroundColor: 'rgba(16, 185, 129, 0.85)',
      borderColor: '#10b981',
      borderWidth: 2,
      hoverBackgroundColor: '#10b981',
      hoverBorderColor: '#059669',
      borderRadius: 8
    })
  }
  
  if (showOutflow.value) {
    datasets.push({
      label: 'Отток',
      data: props.monthlyFlow?.map(m => m.outflow || 0) || [],
      backgroundColor: 'rgba(239, 68, 68, 0.85)',
      borderColor: '#ef4444',
      borderWidth: 2,
      hoverBackgroundColor: '#ef4444',
      hoverBorderColor: '#dc2626',
      borderRadius: 8
    })
  }
  
  if (showDifference.value) {
    datasets.push({
      label: 'Разница',
      data: props.monthlyFlow?.map(m => (m.inflow || 0) + (m.outflow || 0)) || [],
      backgroundColor: 'rgba(59, 130, 246, 0.85)',
      borderColor: '#3b82f6',
      borderWidth: 2,
      hoverBackgroundColor: '#3b82f6',
      hoverBorderColor: '#2563eb',
      borderRadius: 8
    })
  }
  
  return datasets
})
</script>

<template>
  <Widget title="Месячные потоки">
    <template #header>
      <div class="chart-controls">
        <label class="control-checkbox inflow">
          <input 
            type="checkbox" 
            v-model="showInflow"
            class="checkbox-input"
          />
          <span class="checkbox-custom"></span>
          <span class="checkbox-label">Приток</span>
        </label>
        <label class="control-checkbox outflow">
          <input 
            type="checkbox" 
            v-model="showOutflow"
            class="checkbox-input"
          />
          <span class="checkbox-custom"></span>
          <span class="checkbox-label">Отток</span>
        </label>
        <label class="control-checkbox difference">
          <input 
            type="checkbox" 
            v-model="showDifference"
            class="checkbox-input"
          />
          <span class="checkbox-custom"></span>
          <span class="checkbox-label">Разница</span>
        </label>
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
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.control-checkbox {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.checkbox-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.checkbox-custom {
  position: relative;
  width: 20px;
  height: 20px;
  border: 2px solid #d1d5db;
  border-radius: 4px;
  background: #fff;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.control-checkbox:hover .checkbox-custom {
  border-color: #9ca3af;
  background: #f9fafb;
}

.checkbox-input:checked + .checkbox-custom {
  background: #3b82f6;
  border-color: #3b82f6;
}

.checkbox-input:checked + .checkbox-custom::after {
  content: '';
  position: absolute;
  left: 6px;
  top: 2px;
  width: 5px;
  height: 10px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.checkbox-label {
  font-size: 14px;
  color: #4b5563;
  font-weight: 500;
  transition: color 0.2s;
  padding-left: 0;
}

.control-checkbox:hover .checkbox-label {
  color: #111827;
}

.checkbox-input:checked ~ .checkbox-label {
  color: #111827;
  font-weight: 600;
}

/* Цветовые индикаторы для каждого типа */
.control-checkbox.inflow .checkbox-input:checked + .checkbox-custom {
  background: #10b981;
  border-color: #10b981;
}

.control-checkbox.outflow .checkbox-input:checked + .checkbox-custom {
  background: #ef4444;
  border-color: #ef4444;
}

.control-checkbox.difference .checkbox-input:checked + .checkbox-custom {
  background: #3b82f6;
  border-color: #3b82f6;
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
