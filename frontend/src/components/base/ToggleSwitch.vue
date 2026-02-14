<script setup>
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  label: {
    type: String,
    default: null
  },
  disabled: {
    type: Boolean,
    default: false
  },
  activeColor: {
    type: String,
    default: '#527de5'
  },
  hoverColor: {
    type: String,
    default: '#4568d4'
  },
})

const emit = defineEmits(['update:modelValue'])

const handleChange = (event) => {
  if (!props.disabled) {
    emit('update:modelValue', event.target.checked)
  }
}

</script>

<template>
  <label 
    :class="[
      'toggle-switch',
      { 'toggle-switch--disabled': disabled, 'toggle-switch--checked': modelValue }
    ]"
  >
    <input 
      type="checkbox" 
      :checked="modelValue"
      :disabled="disabled"
      @change="handleChange"
      class="toggle-switch-input"
    />
    <span 
      class="toggle-switch-track"
      :style="modelValue ? {
        backgroundColor: activeColor
      } : {}"
    >
      <span class="toggle-switch-thumb"></span>
    </span>
    <span 
      v-if="label" 
      class="toggle-switch-label"
    >{{ label }}</span>
    <slot />
  </label>
</template>

<style scoped>
.toggle-switch {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
  font-size: 14px;
  color: #374151;
}

.toggle-switch--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.toggle-switch-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  margin: 0;
  cursor: pointer;
}

.toggle-switch-track {
  position: relative;
  width: 44px;
  height: 24px;
  background-color: #e5e7eb;
  border-radius: 12px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.06);
}

.toggle-switch-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  background-color: white;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  transform: translateX(0);
}

.toggle-switch--checked .toggle-switch-thumb {
  transform: translateX(20px);
}

.toggle-switch:not(.toggle-switch--disabled):not(.toggle-switch--checked):hover .toggle-switch-track {
  background-color: #d1d5db;
}

.toggle-switch--checked:not(.toggle-switch--disabled):hover .toggle-switch-track {
  filter: brightness(0.95);
}

.toggle-switch-label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  white-space: nowrap;
  line-height: 1.2;
}

.toggle-switch--disabled .toggle-switch-input {
  cursor: not-allowed;
}

.toggle-switch--disabled .toggle-switch-track {
  cursor: not-allowed;
}
</style>