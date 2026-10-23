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
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 0;
  border-radius: var(--cv-r-sm, 10px);
  font-family: inherit;
  font-weight: 550;
  letter-spacing: -0.005em;
  white-space: nowrap;
  cursor: pointer;
  overflow: hidden;
  transition: background .2s var(--cv-ease), box-shadow .2s var(--cv-ease), color .2s, transform .2s var(--cv-ease);
}
.btn:active:not(.btn-disabled):not(:disabled) { transform: scale(.97); }

.btn-sm { height: 30px; padding: 0 11px; font-size: 12.5px; border-radius: 9px; }
.btn-md { height: 36px; padding: 0 14px; font-size: 13px; }
.btn-lg { height: 44px; padding: 0 20px; font-size: 14px; }
.btn-icon-only { width: 36px; padding: 0; }
.btn-icon-only.btn-sm { width: 30px; }
.btn-icon-only.btn-lg { width: 44px; }

.btn-primary {
  color: #fff;
  background: linear-gradient(180deg, #7080ff, #5866ee);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .2), inset 0 0 0 1px rgba(255, 255, 255, .06), 0 6px 18px -10px rgba(100, 116, 255, .8);
}
.btn-primary:hover:not(.btn-disabled) {
  background: linear-gradient(180deg, #7b8aff, #616ff2);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .24), inset 0 0 0 1px rgba(255, 255, 255, .08), 0 8px 22px -10px rgba(100, 116, 255, .9);
}

.btn-secondary,
.btn-outline {
  color: var(--cv-ink);
  background: rgba(255, 255, 255, .05);
  box-shadow: inset 0 0 0 1px var(--cv-line-2);
}
.btn-outline { background: transparent; color: var(--cv-ink-2); }
.btn-secondary:hover:not(.btn-disabled),
.btn-outline:hover:not(.btn-disabled) {
  color: var(--cv-ink);
  background: rgba(255, 255, 255, .08);
  box-shadow: inset 0 0 0 1px var(--cv-line-3);
}

.btn-ghost { color: var(--cv-mut); background: transparent; }
.btn-ghost:hover:not(.btn-disabled) { color: var(--cv-ink); background: var(--cv-hover); }

.btn-danger {
  color: var(--cv-down);
  background: var(--cv-down-bg);
  box-shadow: inset 0 0 0 1px rgba(242, 119, 122, .22);
}
.btn-danger:hover:not(.btn-disabled) { background: rgba(242, 119, 122, .16); }

.btn-icon { display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.btn-icon :deep(svg) { width: 15px; height: 15px; stroke-width: 2; }
.btn-sm .btn-icon :deep(svg) { width: 14px; height: 14px; }
.btn-lg .btn-icon :deep(svg) { width: 18px; height: 18px; }

.btn-text { line-height: 1; }

.btn-spinner { display: flex; align-items: center; justify-content: center; }
.spinner-icon { width: 16px; height: 16px; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.btn-disabled,
.btn:disabled { opacity: .5; cursor: not-allowed; transform: none !important; }
</style>
