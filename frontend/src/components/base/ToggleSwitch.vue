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
    default: '#6474ff'
  },
  hoverColor: {
    type: String,
    default: '#5060dc'
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
  color: var(--lx-ink, #374151);
  max-width: 100%;
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
  width: 34px;
  height: 20px;
  background-color: var(--lx-fill-3, #e5e7eb);
  border-radius: 10px;
  transition: background-color 0.25s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.25s;
  flex-shrink: 0;
  box-shadow: inset 0 0 0 1px var(--lx-line-2, rgba(0, 0, 0, 0.04));
}

.toggle-switch-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  background-color: var(--lx-ink-2, white);
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  transition: transform 0.25s cubic-bezier(0.34, 1.4, 0.64, 1), background-color 0.2s;
  transform: translateX(0);
}

.toggle-switch--checked .toggle-switch-thumb {
  transform: translateX(14px);
  background-color: #fff;
}
.toggle-switch--checked .toggle-switch-track {
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
}
.toggle-switch-input:focus-visible + .toggle-switch-track {
  outline: 2px solid var(--lx-accent, #3b82f6);
  outline-offset: 2px;
}

.toggle-switch:not(.toggle-switch--disabled):not(.toggle-switch--checked):hover .toggle-switch-track {
  background-color: var(--lx-fill-2, #d1d5db);
}

.toggle-switch--checked:not(.toggle-switch--disabled):hover .toggle-switch-track {
  filter: brightness(0.95);
}

.toggle-switch-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--lx-ink-2, #374151);
  line-height: 1.2;
  min-width: 0;
  white-space: normal;
  word-break: break-word;
  overflow-wrap: anywhere;
  flex: 1 1 auto; /* позволяет лейблу сжиматься и переносить слова */
}

@media (max-width: 768px) {
  .toggle-switch-label {
    white-space: normal;
    word-break: break-word;
  }
}

.toggle-switch--disabled .toggle-switch-input {
  cursor: not-allowed;
}

.toggle-switch--disabled .toggle-switch-track {
  cursor: not-allowed;
}
</style>