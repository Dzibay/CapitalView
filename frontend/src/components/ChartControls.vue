<script setup>
import { computed } from 'vue'
import CustomSelect from './CustomSelect.vue'

const props = defineProps({
  chartType: {
    type: String,
    required: true
  },
  period: {
    type: String,
    required: true
  },
  chartTypeOptions: {
    type: Array,
    default: () => [
      { key: 'position', label: 'Стоимость позиции' },
      { key: 'quantity', label: 'Количество' },
      { key: 'price', label: 'Цена единицы' }
    ]
  },
  periodOptions: {
    type: Array,
    default: () => [
      { key: '1M', label: 'Месяц' },
      { key: '1Y', label: 'Год' },
      { key: 'All', label: 'Все время' }
    ]
  }
})

const emit = defineEmits(['update:chartType', 'update:period'])

const updateChartType = (value) => {
  emit('update:chartType', value)
}

const updatePeriod = (value) => {
  emit('update:period', value)
}

// Преобразуем chartTypeOptions в формат для CustomSelect
const chartTypeSelectOptions = computed(() => {
  return props.chartTypeOptions.map(opt => ({
    value: opt.key,
    label: opt.label
  }))
})
</script>

<template>
  <div class="chart-controls">
    <!-- Выбор типа графика -->
    <CustomSelect
      :modelValue="chartType"
      :options="chartTypeSelectOptions"
      label="Тип графика"
      placeholder="Выберите тип графика"
      :show-empty-option="false"
      option-label="label"
      option-value="value"
      :min-width="'200px'"
      :flex="'none'"
      @update:modelValue="updateChartType"
    />

    <!-- Выбор периода -->
    <div class="capital-filters">
      <button
        v-for="option in periodOptions"
        :key="option.key"
        @click="updatePeriod(option.key)"
        :class="['filter-btn', { active: period === option.key }]"
      >
        {{ option.label }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.chart-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}


.capital-filters {
  display: flex;
  background-color: #f3f4f6;
  padding: 0.25rem;
  border-radius: 8px;
  gap: 0.25rem;
}

.filter-btn {
  border: none;
  background: transparent;
  border-radius: 6px;
  padding: 0.5rem 0.9rem;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
  color: #6b7280;
}

.filter-btn:hover {
  background-color: #e5e7eb;
}

.filter-btn.active {
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  color: #5478EA;
  font-weight: 600;
}
</style>

