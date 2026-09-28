<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'primary',
    validator: (value) => ['primary', 'secondary', 'outline', 'ghost', 'danger'].includes(value)
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value)
  },
  disabled: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  iconOnly: {
    type: Boolean,
    default: false
  },
  type: {
    type: String,
    default: 'button'
  }
})

const emit = defineEmits(['click'])

const buttonClasses = computed(() => [
  'btn',
  `btn-${props.variant}`,
  `btn-${props.size}`,
  {
    'btn-icon-only': props.iconOnly,
    'btn-loading': props.loading,
    'btn-disabled': props.disabled
  }
])

const handleClick = (event) => {
  if (!props.disabled && !props.loading) {
    emit('click', event)
  }
}
</script>

<template>
  <button
    :type="type"
    :class="buttonClasses"
    :disabled="disabled || loading"
    @click="handleClick"
  >
    <span v-if="loading" class="btn-spinner">
      <svg class="spinner-icon" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-dasharray="32" stroke-dashoffset="32">
          <animate attributeName="stroke-dasharray" dur="2s" values="0 32;16 16;0 32;0 32" repeatCount="indefinite"/>
          <animate attributeName="stroke-dashoffset" dur="2s" values="0;-16;-32;-32" repeatCount="indefinite"/>
        </circle>
      </svg>
    </span>
    <span v-else-if="$slots.icon" class="btn-icon">
      <slot name="icon" />
    </span>
    <span v-if="!iconOnly && ($slots.default || $slots.icon)" class="btn-text">
      <slot />
    </span>
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  border-radius: var(--radius-sm, 6px);
  border: none;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
  letter-spacing: -0.01em;
  white-space: nowrap;
  position: relative;
  overflow: hidden;
  font-family: inherit;
}

/* Размеры */
.btn-sm {
  height: 32px;
  padding: 0 12px;
  font-size: 12px;
}

.btn-md {
  height: 38px;
  padding: 0 16px;
  font-size: 13px;
}

.btn-lg {
  height: 44px;
  padding: 0 20px;
  font-size: 14px;
}

.btn-icon-only {
  padding: 0;
  width: 38px;
}

.btn-icon-only.btn-sm {
  width: 32px;
}

.btn-icon-only.btn-lg {
  width: 44px;
}

/* Основной вариант */
.btn-primary {
  background: var(--primary, #2f5f8f);
  color: white;
  box-shadow: none;
}

.btn-primary:hover:not(.btn-disabled) {
  background: var(--primary-hover, #264d75);
  transform: none;
  box-shadow: none;
}

.btn-primary:active:not(.btn-disabled) {
  transform: none;
  box-shadow: none;
  background: var(--primary-dark, #1e3f61);
}

/* Вторичный вариант */
.btn-secondary {
  background: white;
  color: var(--text-secondary, #3d4654);
  border: 1px solid var(--border-subtle, #d8dee6);
  box-shadow: none;
}

.btn-secondary:hover:not(.btn-disabled) {
  background: var(--bg-secondary, #eef1f4);
  border-color: var(--border-strong, #c5ced8);
  transform: none;
  box-shadow: none;
}

.btn-secondary:active:not(.btn-disabled) {
  transform: none;
  box-shadow: none;
}

/* Контурный вариант */
.btn-outline {
  background: transparent;
  border: 1px solid var(--border-subtle, #d8dee6);
  color: var(--text-tertiary, #6b7380);
}

.btn-outline:hover:not(.btn-disabled) {
  border-color: var(--primary, #2f5f8f);
  color: var(--primary, #2f5f8f);
  background: rgba(47, 95, 143, 0.06);
  transform: none;
}

.btn-outline:active:not(.btn-disabled) {
  transform: none;
  background: rgba(47, 95, 143, 0.1);
}

/* Прозрачный вариант */
.btn-ghost {
  background: transparent;
  color: var(--text-tertiary, #6b7380);
  border: none;
}

.btn-ghost:hover:not(.btn-disabled) {
  background: var(--bg-tertiary, #e4e8ed);
  color: var(--primary, #2f5f8f);
}

/* Вариант «опасность» */
.btn-danger {
  background: var(--danger, #d14343);
  color: white;
  box-shadow: none;
}

.btn-danger:hover:not(.btn-disabled) {
  background: var(--danger-dark, #a83232);
  transform: none;
  box-shadow: none;
}

.btn-danger:active:not(.btn-disabled) {
  transform: none;
  box-shadow: none;
}

/* Иконка */
.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.btn-icon :deep(svg) {
  width: 16px;
  height: 16px;
  stroke-width: 2;
}

.btn-sm .btn-icon :deep(svg) {
  width: 14px;
  height: 14px;
}

.btn-lg .btn-icon :deep(svg) {
  width: 18px;
  height: 18px;
}

/* Текст */
.btn-text {
  line-height: 1;
}

/* Спиннер */
.btn-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
}

.spinner-icon {
  width: 16px;
  height: 16px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Состояние «отключено» */
.btn-disabled,
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

.btn-disabled:hover,
.btn:disabled:hover {
  transform: none !important;
  box-shadow: none !important;
}
</style>