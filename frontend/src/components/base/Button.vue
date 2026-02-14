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
  font-weight: 600;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  letter-spacing: -0.01em;
  white-space: nowrap;
  position: relative;
  overflow: hidden;
  font-family: inherit;
}

/* Sizes */
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

/* Primary variant */
.btn-primary {
  background: linear-gradient(135deg, #527de5, #6b91ea);
  color: white;
  box-shadow: 0 1px 2px rgba(82, 125, 229, 0.2);
}

.btn-primary:hover:not(.btn-disabled) {
  background: linear-gradient(135deg, #4568d4, #5a7fd9);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(82, 125, 229, 0.3);
}

.btn-primary:active:not(.btn-disabled) {
  transform: translateY(0);
  box-shadow: 0 1px 2px rgba(82, 125, 229, 0.2);
}

/* Secondary variant */
.btn-secondary {
  background: white;
  color: #374151;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.btn-secondary:hover:not(.btn-disabled) {
  background: #f9fafb;
  border-color: #d1d5db;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
}

.btn-secondary:active:not(.btn-disabled) {
  transform: translateY(0);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

/* Outline variant */
.btn-outline {
  background: transparent;
  border: 1px solid #e5e7eb;
  color: #6b7280;
}

.btn-outline:hover:not(.btn-disabled) {
  border-color: #527de5;
  color: #527de5;
  background: #f0f9ff;
  transform: translateY(-1px);
}

.btn-outline:active:not(.btn-disabled) {
  transform: translateY(0);
  background: #e0f2fe;
}

/* Ghost variant */
.btn-ghost {
  background: transparent;
  color: #6b7280;
  border: none;
}

.btn-ghost:hover:not(.btn-disabled) {
  background: #f9fafb;
  color: #527de5;
}

/* Danger variant */
.btn-danger {
  background: #ef4444;
  color: white;
  box-shadow: 0 1px 2px rgba(239, 68, 68, 0.2);
}

.btn-danger:hover:not(.btn-disabled) {
  background: #dc2626;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.btn-danger:active:not(.btn-disabled) {
  transform: translateY(0);
  box-shadow: 0 1px 2px rgba(239, 68, 68, 0.2);
}

/* Icon */
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

/* Text */
.btn-text {
  line-height: 1;
}

/* Spinner */
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

/* Disabled state */
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