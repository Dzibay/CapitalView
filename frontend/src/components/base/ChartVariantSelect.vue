<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number],
    required: true
  },
  options: {
    type: Array,
    required: true
  },
  optionLabel: {
    type: String,
    default: 'label'
  },
  optionValue: {
    type: String,
    default: 'value'
  }
})

const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const triggerRef = ref(null)
const menuRef = ref(null)

const selectedLabel = computed(() => {
  const opt = props.options.find(o => o[props.optionValue] === props.modelValue)
  return opt ? opt[props.optionLabel] : ''
})

function toggle() {
  open.value = !open.value
}

function select(option) {
  emit('update:modelValue', option[props.optionValue])
  open.value = false
}

function onClickOutside(e) {
  if (triggerRef.value?.contains(e.target)) return
  if (menuRef.value?.contains(e.target)) return
  open.value = false
}

function adjustPosition() {
  if (!open.value || !menuRef.value || !triggerRef.value) return
  const mr = menuRef.value.getBoundingClientRect()
  const br = triggerRef.value.getBoundingClientRect()
  if (br.right - mr.width < 8) {
    menuRef.value.style.left = '0'
    menuRef.value.style.right = 'auto'
  } else {
    menuRef.value.style.right = '0'
    menuRef.value.style.left = 'auto'
  }
}

watch(open, (v) => {
  if (v) nextTick(adjustPosition)
})

onMounted(() => document.addEventListener('mousedown', onClickOutside))
onBeforeUnmount(() => document.removeEventListener('mousedown', onClickOutside))
</script>

<template>
  <div class="chart-variant-select">
    <button
      ref="triggerRef"
      class="chart-variant-trigger"
      :class="{ 'is-open': open }"
      @click.stop="toggle"
    >
      <span class="chart-variant-label">{{ selectedLabel }}</span>
      <svg
        class="chart-variant-chevron"
        width="12" height="12" viewBox="0 0 12 12" fill="none"
      >
        <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <Transition name="chart-variant-dd">
      <div v-if="open" ref="menuRef" class="chart-variant-dropdown">
        <div
          v-for="opt in options"
          :key="opt[optionValue]"
          class="chart-variant-option"
          :class="{ 'is-selected': opt[optionValue] === modelValue }"
          @click.stop="select(opt)"
        >
          {{ opt[optionLabel] }}
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.chart-variant-select {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.chart-variant-trigger {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  color: var(--text-secondary, #374151);
  white-space: nowrap;
}

.chart-variant-trigger:hover,
.chart-variant-trigger.is-open {
  background: var(--bg-tertiary, #f3f4f6);
}

.chart-variant-label {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.2;
}

.chart-variant-chevron {
  flex-shrink: 0;
  transition: transform 0.2s ease;
  color: var(--text-tertiary, #9ca3b8);
}

.chart-variant-trigger.is-open .chart-variant-chevron {
  transform: rotate(180deg);
}

.chart-variant-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 160px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  box-shadow: 0 8px 24px -4px rgba(0,0,0,0.10), 0 0 0 1px rgba(0,0,0,0.04);
  z-index: 50;
  padding: 4px;
  user-select: none;
}

.chart-variant-option {
  padding: 7px 10px;
  border-radius: 7px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  transition: background 0.12s ease;
  white-space: nowrap;
}

.chart-variant-option:hover {
  background: #f3f4f6;
}

.chart-variant-option.is-selected {
  color: #527de5;
  background: rgba(82, 125, 229, 0.08);
}

.chart-variant-dd-enter-active {
  transition: opacity 0.15s ease, transform 0.15s cubic-bezier(0.34,1.56,0.64,1);
}
.chart-variant-dd-leave-active {
  transition: opacity 0.1s ease, transform 0.1s ease;
}
.chart-variant-dd-enter-from,
.chart-variant-dd-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(-4px);
}
</style>
