<script setup>
const props = defineProps({
  modelValue: {
    type: String,
    required: true
  },
  periods: {
    type: Array,
    default: () => [
      { value: '7D', label: '7д' },
      { value: '1M', label: '1м' },
      { value: '3M', label: '3м' },
      { value: '6M', label: '6м' },
      { value: 'YTD', label: 'YTD' },
      { value: '1Y', label: '1г' },
      { value: '5Y', label: '5л' },
      { value: 'All', label: 'все' }
    ]
  }
})

const emit = defineEmits(['update:modelValue'])

const updateValue = (value) => {
  emit('update:modelValue', value)
}
</script>

<template>
  <div class="period-filters">
    <button
      v-for="period in periods"
      :key="period.value"
      @click="updateValue(period.value)"
      :class="['filter-btn', { active: modelValue === period.value }]"
    >
      {{ period.label }}
    </button>
  </div>
</template>

<style scoped>
.period-filters {
  display: flex;
  background-color: #f3f4f6;
  padding: 3px;
  border-radius: 8px;
  gap: 2px;
  flex-wrap: nowrap;
}

.filter-btn {
  border: none;
  background: transparent;
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
  color: var(--text-tertiary, #6b7280);
  white-space: nowrap;
  line-height: 1.2;
}

.filter-btn:hover {
  background-color: #e5e7eb;
  color: var(--text-secondary, #4b5563);
}

.filter-btn.active {
  background-color: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  color: #5478EA;
  font-weight: 600;
}

@media (max-width: 768px) {
  .period-filters {
    padding: 2px;
    gap: 1px;
  }
  .filter-btn {
    padding: 4px 7px;
    font-size: 11.5px;
  }
}

@media (max-width: 480px) {
  .period-filters {
    flex-wrap: wrap;
  }
  .filter-btn {
    padding: 4px 6px;
    font-size: 11px;
  }
}
</style>
