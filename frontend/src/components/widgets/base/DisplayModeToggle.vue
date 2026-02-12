<script setup>
const props = defineProps({
  modelValue: {
    type: String,
    required: true,
    validator: (value) => ['percent', 'currency'].includes(value)
  }
})

const emit = defineEmits(['update:modelValue'])

const updateValue = (value) => {
  emit('update:modelValue', value)
}
</script>

<template>
  <div class="display-mode-toggle">
    <button
      @click="updateValue('percent')"
      :class="['mode-toggle-btn', { active: modelValue === 'percent' }]"
    >
      %
    </button>
    <button
      @click="updateValue('currency')"
      :class="['mode-toggle-btn', { active: modelValue === 'currency' }]"
    >
      ₽
    </button>
  </div>
</template>

<style scoped>
.display-mode-toggle {
  display: flex;
  background-color: #f3f4f6;
  padding: 0.25rem;
  border-radius: 8px;
  gap: 0.25rem;
}

.mode-toggle-btn {
  border: none;
  background: transparent;
  border-radius: 6px;
  padding: 0.5rem 0.875rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  color: #6b7280;
}

.mode-toggle-btn:hover {
  background-color: #e5e7eb;
}

.mode-toggle-btn.active {
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  color: #5478EA;
  font-weight: 600;
}
</style>
