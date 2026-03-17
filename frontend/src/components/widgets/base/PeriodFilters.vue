<script setup>
const props = defineProps({
  modelValue: {
    type: String,
    required: true
  },
  periods: {
    type: Array,
    default: () => [
      { value: '1M', label: 'Месяц' },
      { value: '1Y', label: 'Год' },
      { value: 'All', label: 'Все время' }
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
  padding: 0.25rem;
  border-radius: 8px;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.filter-btn {
  border: none;
  background: transparent;
  border-radius: 6px;
  padding: 0.5rem 0.9rem;
  font-size: var(--text-body-secondary-size);
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
  color: var(--text-tertiary);
}

.filter-btn:hover {
  background-color: #e5e7eb;
}

.filter-btn.active {
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  color: #5478EA;
  font-weight: 600;
}

@media (max-width: 768px) {
  .period-filters {
    padding: 0.2rem;
    gap: 0.2rem;
  }
  .filter-btn {
    padding: 0.4rem 0.65rem;
    font-size: var(--text-caption-size);
  }
}

@media (max-width: 480px) {
  .period-filters {
    padding: 0.15rem;
    gap: 0.15rem;
  }
  .filter-btn {
    padding: 0.35rem 0.5rem;
    font-size: var(--text-caption-size);
  }
}
</style>
