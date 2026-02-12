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
  variant: {
    type: String,
    default: 'default', // 'default' или 'filter'
    validator: (value) => ['default', 'filter'].includes(value)
  },
  size: {
    type: String,
    default: 'medium', // 'small', 'medium', 'large'
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  },
  disabled: {
    type: Boolean,
    default: false
  }
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
      'checkbox', 
      `checkbox--${variant}`, 
      `checkbox--${size}`,
      { 'checkbox--disabled': disabled }
    ]"
  >
    <input 
      type="checkbox" 
      :checked="modelValue"
      :disabled="disabled"
      @change="handleChange"
      class="checkbox-input"
    />
    <span class="checkbox-custom"></span>
    <span v-if="label" class="checkbox-label">{{ label }}</span>
    <slot />
  </label>
</template>

<style scoped>
.checkbox {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  user-select: none;
  font-size: 0.875rem;
  color: #374151;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.checkbox--default {
  gap: 0.5rem;
}

.checkbox--filter {
  gap: 8px;
  padding: 8px 12px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.checkbox--filter:hover:not(.checkbox--disabled) {
  background: #f9fafb;
  border-color: #d1d5db;
}

.checkbox-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  margin: 0;
  cursor: pointer;
}

.checkbox-custom {
  position: relative;
  flex-shrink: 0;
  background: #fff;
  border: 2px solid #d1d5db;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.checkbox-custom::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(59, 130, 246, 0.2);
  transform: translate(-50%, -50%);
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), 
              height 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              opacity 0.2s ease;
  opacity: 0;
}

/* Размеры */
.checkbox--small .checkbox-custom {
  width: 16px;
  height: 16px;
  border-radius: 4px;
}

.checkbox--medium .checkbox-custom {
  width: 18px;
  height: 18px;
  border-radius: 5px;
}

.checkbox--large .checkbox-custom {
  width: 20px;
  height: 20px;
  border-radius: 6px;
}

.checkbox--filter .checkbox-custom {
  width: 18px;
  height: 18px;
  border-radius: 5px;
}

/* Hover состояние - только если не checked */
.checkbox:hover:not(.checkbox--disabled) .checkbox-input:not(:checked) + .checkbox-custom {
  border-color: #9ca3af;
  background: #f9fafb;
}

/* Checked состояние */
.checkbox-input:checked + .checkbox-custom {
  background: #3b82f6;
  border-color: #3b82f6;
  animation: checkmark-bounce 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

.checkbox-input:checked + .checkbox-custom::before {
  width: 100%;
  height: 100%;
  opacity: 1;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), 
              height 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              opacity 0.1s ease 0.15s;
}

.checkbox-input:checked + .checkbox-custom::after {
  content: '';
  position: absolute;
  left: 5px;
  top: 2px;
  width: 5px;
  height: 9px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg) scale(0);
  animation: checkmark-draw 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55) 0.15s forwards;
  transform-origin: center;
}

@keyframes checkmark-bounce {
  0% {
    transform: scale(0.95);
  }
  50% {
    transform: scale(1.03);
  }
  100% {
    transform: scale(1);
  }
}

@keyframes checkmark-draw {
  0% {
    transform: rotate(45deg) scale(0);
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
  100% {
    transform: rotate(45deg) scale(1);
    opacity: 1;
  }
}

.checkbox--small .checkbox-input:checked + .checkbox-custom::after {
  left: 4px;
  top: 1px;
  width: 4px;
  height: 7px;
  animation: checkmark-draw-small 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55) 0.15s forwards;
}

.checkbox--large .checkbox-input:checked + .checkbox-custom::after {
  left: 6px;
  top: 2px;
  width: 5px;
  height: 10px;
  animation: checkmark-draw-large 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55) 0.15s forwards;
}

@keyframes checkmark-draw-small {
  0% {
    transform: rotate(45deg) scale(0);
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
  100% {
    transform: rotate(45deg) scale(1);
    opacity: 1;
  }
}

@keyframes checkmark-draw-large {
  0% {
    transform: rotate(45deg) scale(0);
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
  100% {
    transform: rotate(45deg) scale(1);
    opacity: 1;
  }
}

.checkbox--filter .checkbox-input:checked + .checkbox-custom {
  background: #2563eb;
  border-color: #2563eb;
  animation: checkmark-bounce 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

/* Label */
.checkbox-label {
  color: #374151;
  font-size: 0.875rem;
  font-weight: 500;
  white-space: nowrap;
  line-height: 1.2;
  transition: color 0.2s ease;
}

.checkbox:hover:not(.checkbox--disabled) .checkbox-label {
  color: #111827;
}

.checkbox-input:checked ~ .checkbox-label {
  color: #111827;
}

.checkbox--filter .checkbox-label {
  font-weight: 500;
}

/* Disabled состояние */
.checkbox--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.checkbox--disabled .checkbox-input {
  cursor: not-allowed;
}

.checkbox--disabled .checkbox-custom {
  background: #f3f4f6;
  border-color: #e5e7eb;
  cursor: not-allowed;
}

.checkbox--disabled:hover .checkbox-custom {
  border-color: #e5e7eb;
  background: #f3f4f6;
}
</style>
