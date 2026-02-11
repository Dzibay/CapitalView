<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'

const props = defineProps({
  content: {
    type: [String, Array],
    required: true
  },
  position: {
    type: String,
    default: 'top',
    validator: (value) => ['top', 'bottom', 'left', 'right'].includes(value)
  },
  delay: {
    type: Number,
    default: 50 // Почти мгновенно
  }
})

const show = ref(false)
const tooltipRef = ref(null)
const triggerRef = ref(null)
let showTimeout = null
let hideTimeout = null

const tooltipClasses = computed(() => ({
  'tooltip': true,
  [`tooltip-${props.position}`]: true,
  'tooltip-visible': show.value
}))

const formattedContent = computed(() => {
  if (Array.isArray(props.content)) {
    return props.content
  }
  // Разбиваем текст на строки для многострочного отображения
  return props.content.split('\n').filter(line => line.trim())
})

const showTooltip = () => {
  if (showTimeout) {
    clearTimeout(showTimeout)
  }
  if (hideTimeout) {
    clearTimeout(hideTimeout)
    hideTimeout = null
  }
  
  showTimeout = setTimeout(() => {
    show.value = true
    // Даем время на рендеринг перед обновлением позиции
    nextTick(() => {
      setTimeout(() => {
        updatePosition()
      }, 10)
    })
  }, props.delay)
}

const hideTooltip = () => {
  if (showTimeout) {
    clearTimeout(showTimeout)
    showTimeout = null
  }
  
  hideTimeout = setTimeout(() => {
    show.value = false
  }, 100) // Небольшая задержка для плавности
}

const updatePosition = () => {
  if (!tooltipRef.value || !triggerRef.value || !show.value) return
  
  const tooltip = tooltipRef.value
  const trigger = triggerRef.value
  const rect = trigger.getBoundingClientRect()
  const tooltipRect = tooltip.getBoundingClientRect()
  
  let top = 0
  let left = 0
  
  switch (props.position) {
    case 'top':
      top = rect.top - tooltipRect.height - 8
      left = rect.left + (rect.width / 2) - (tooltipRect.width / 2)
      break
    case 'bottom':
      top = rect.bottom + 8
      left = rect.left + (rect.width / 2) - (tooltipRect.width / 2)
      break
    case 'left':
      top = rect.top + (rect.height / 2) - (tooltipRect.height / 2)
      left = rect.left - tooltipRect.width - 8
      break
    case 'right':
      top = rect.top + (rect.height / 2) - (tooltipRect.height / 2)
      left = rect.right + 8
      break
  }
  
  // Проверка границ экрана
  const padding = 10
  if (left < padding) left = padding
  if (left + tooltipRect.width > window.innerWidth - padding) {
    left = window.innerWidth - tooltipRect.width - padding
  }
  if (top < padding) top = padding
  if (top + tooltipRect.height > window.innerHeight - padding) {
    top = window.innerHeight - tooltipRect.height - padding
  }
  
  tooltip.style.top = `${top}px`
  tooltip.style.left = `${left}px`
}

onMounted(() => {
  if (triggerRef.value) {
    triggerRef.value.addEventListener('mouseenter', showTooltip)
    triggerRef.value.addEventListener('mouseleave', hideTooltip)
    triggerRef.value.addEventListener('mousemove', () => {
      if (show.value) {
        updatePosition()
      }
    })
  }
})

onUnmounted(() => {
  if (showTimeout) clearTimeout(showTimeout)
  if (hideTimeout) clearTimeout(hideTimeout)
  if (triggerRef.value) {
    triggerRef.value.removeEventListener('mouseenter', showTooltip)
    triggerRef.value.removeEventListener('mouseleave', hideTooltip)
    triggerRef.value.removeEventListener('mousemove', updatePosition)
  }
})
</script>

<template>
  <div class="tooltip-wrapper" ref="triggerRef">
    <slot />
    <Teleport to="body">
      <div 
        v-if="show || tooltipRef" 
        ref="tooltipRef"
        :class="tooltipClasses"
      >
        <div class="tooltip-content">
          <div 
            v-for="(line, index) in formattedContent" 
            :key="index"
            class="tooltip-line"
          >
            {{ line }}
          </div>
        </div>
        <div class="tooltip-arrow"></div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.tooltip-wrapper {
  display: inline-block;
  position: relative;
}

.tooltip {
  position: fixed;
  z-index: 10000;
  pointer-events: none;
  opacity: 0;
  transform: translateY(-4px);
  transition: opacity 0.15s ease-out, transform 0.15s ease-out;
  visibility: hidden;
  display: block;
}

.tooltip-visible {
  opacity: 1;
  transform: translateY(0);
  visibility: visible;
}

.tooltip-content {
  background: rgba(31, 41, 55, 0.95);
  backdrop-filter: blur(8px);
  color: #fff;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.1);
  max-width: 300px;
  white-space: pre-line;
}

.tooltip-line {
  margin: 2px 0;
}

.tooltip-line:first-child {
  margin-top: 0;
}

.tooltip-line:last-child {
  margin-bottom: 0;
}

.tooltip-arrow {
  position: absolute;
  width: 0;
  height: 0;
}

.tooltip-top .tooltip-arrow {
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 6px solid rgba(31, 41, 55, 0.95);
}

.tooltip-bottom .tooltip-arrow {
  top: -6px;
  left: 50%;
  transform: translateX(-50%);
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-bottom: 6px solid rgba(31, 41, 55, 0.95);
}

.tooltip-left .tooltip-arrow {
  right: -6px;
  top: 50%;
  transform: translateY(-50%);
  border-top: 6px solid transparent;
  border-bottom: 6px solid transparent;
  border-left: 6px solid rgba(31, 41, 55, 0.95);
}

.tooltip-right .tooltip-arrow {
  left: -6px;
  top: 50%;
  transform: translateY(-50%);
  border-top: 6px solid transparent;
  border-bottom: 6px solid transparent;
  border-right: 6px solid rgba(31, 41, 55, 0.95);
}
</style>
