<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'

const props = defineProps({
  options: {
    type: Array,
    required: true
    // [{ id: string, label: string, modelValue: boolean }]
  }
})

const emit = defineEmits(['toggle'])

const open = ref(false)
const btnRef = ref(null)
const menuRef = ref(null)

function toggle() {
  open.value = !open.value
}

function onToggle(id, current) {
  emit('toggle', id, !current)
}

function onClickOutside(e) {
  if (
    menuRef.value?.contains(e.target) ||
    btnRef.value?.contains(e.target)
  ) return
  open.value = false
}

function adjustPosition() {
  if (!open.value || !menuRef.value || !btnRef.value) return
  const mr = menuRef.value.getBoundingClientRect()
  const br = btnRef.value.getBoundingClientRect()
  const vw = window.innerWidth

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

onMounted(() => {
  document.addEventListener('mousedown', onClickOutside)
  window.addEventListener('resize', adjustPosition)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onClickOutside)
  window.removeEventListener('resize', adjustPosition)
})
</script>

<template>
  <div class="chart-options">
    <button
      ref="btnRef"
      class="chart-options-btn"
      :class="{ 'chart-options-btn--active': open }"
      @click.stop="toggle"
      title="Параметры графика"
    >
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="3" cy="8" r="1.4" fill="currentColor"/>
        <circle cx="8" cy="8" r="1.4" fill="currentColor"/>
        <circle cx="13" cy="8" r="1.4" fill="currentColor"/>
      </svg>
    </button>

    <Transition name="chart-opts-dropdown">
      <div v-if="open" ref="menuRef" class="chart-options-dropdown">
        <div
          v-for="opt in options"
          :key="opt.id"
          class="chart-options-item"
          @click="onToggle(opt.id, opt.modelValue)"
        >
          <span class="chart-options-item-track" :class="{ 'is-on': opt.modelValue }">
            <span class="chart-options-item-thumb" />
          </span>
          <span class="chart-options-item-label">{{ opt.label }}</span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.chart-options {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.chart-options-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--text-tertiary, #9ca3b8);
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}
.chart-options-btn:hover,
.chart-options-btn--active {
  background: var(--bg-tertiary, #f3f4f6);
  color: var(--text-secondary, #4b5563);
}

.chart-options-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 190px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  box-shadow: 0 8px 24px -4px rgba(0,0,0,0.10), 0 0 0 1px rgba(0,0,0,0.04);
  z-index: 50;
  padding: 4px;
  user-select: none;
}

.chart-opts-dropdown-enter-active {
  transition: opacity 0.15s ease, transform 0.15s cubic-bezier(0.34,1.56,0.64,1);
}
.chart-opts-dropdown-leave-active {
  transition: opacity 0.1s ease, transform 0.1s ease;
}
.chart-opts-dropdown-enter-from,
.chart-opts-dropdown-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(-4px);
}

.chart-options-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  border-radius: 7px;
  cursor: pointer;
  transition: background 0.12s ease;
}
.chart-options-item:hover {
  background: #f3f4f6;
}

.chart-options-item-track {
  position: relative;
  width: 32px;
  height: 18px;
  border-radius: 9px;
  background: #e5e7eb;
  transition: background 0.2s ease;
  flex-shrink: 0;
}
.chart-options-item-track.is-on {
  background: #527de5;
}

.chart-options-item-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.18);
  transition: transform 0.2s cubic-bezier(0.4,0,0.2,1);
}
.chart-options-item-track.is-on .chart-options-item-thumb {
  transform: translateX(14px);
}

.chart-options-item-label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  line-height: 1.2;
  white-space: nowrap;
}
</style>
