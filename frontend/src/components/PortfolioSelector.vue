<script setup>
defineProps({
  portfolios: {
    type: Array,
    required: true,
    default: () => []
  },
  modelValue: {
    type: [String, Number],
    default: null
  }
})

const emit = defineEmits(['update:modelValue'])

const handleChange = (event) => {
  emit('update:modelValue', Number(event.target.value))
}
</script>

<template>
  <div class="portfolio-selector">
    <select 
      :value="modelValue" 
      class="portfolio-select"
      @change="handleChange"
    >
      <option v-for="p in portfolios" :key="p.id" :value="p.id">
        {{ p.name }}
      </option>
    </select>
    <div class="select-arrow">▼</div>
  </div>
</template>

<style scoped>
.portfolio-selector {
  position: relative;
  display: inline-block;
  min-width: 200px;
}

.portfolio-select {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  width: 100%;
  padding: 10px 16px;
  padding-right: 40px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #1a1a1a);
  background: var(--bg-secondary, #f8f9fa);
  border: 2px solid var(--border-color, #e1e5e9);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  outline: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.portfolio-select:hover {
  border-color: var(--primary-color, #007bff);
  background: var(--bg-primary, #ffffff);
  box-shadow: 0 4px 8px rgba(0, 123, 255, 0.15);
}

.portfolio-select:focus {
  border-color: var(--primary-color, #007bff);
  background: var(--bg-primary, #ffffff);
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.select-arrow {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: var(--text-secondary, #6c757d);
  font-size: 12px;
  transition: transform 0.2s ease;
}

.portfolio-select:focus + .select-arrow {
  transform: translateY(-50%) rotate(180deg);
  color: var(--primary-color, #007bff);
}

.portfolio-select option {
  padding: 12px;
  background: var(--bg-primary, #ffffff);
  color: var(--text-primary, #1a1a1a);
  font-size: 14px;
}
</style>