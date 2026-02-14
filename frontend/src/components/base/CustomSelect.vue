<template>
  <div ref="wrapperRef" class="custom-select-wrapper" :style="{ minWidth: minWidth, flex: flex }">
    <span v-if="label" class="select-label">{{ label }}</span>
    <div 
      class="custom-select" 
      :class="{ 'is-open': isOpen }" 
      @click="toggleDropdown"
    >
      <span class="custom-select-value" :class="{ 'placeholder': !selectedValue }">
        {{ displayValue || placeholder }}
      </span>
      <span class="custom-select-arrow">▼</span>
    </div>
    <div v-if="isOpen" class="custom-select-dropdown" @click.stop>
      <div 
        v-if="showEmptyOption"
        class="custom-select-option" 
        :class="{ 'is-selected': !selectedValue }"
        @click="selectOption(null, emptyOptionText)"
      >
        <span>{{ emptyOptionText }}</span>
        <span v-if="!selectedValue" class="check-icon">✓</span>
      </div>
      <div 
        v-for="option in options" 
        :key="getOptionValue(option)" 
        class="custom-select-option"
        :class="{ 'is-selected': isSelected(option) }"
        @click="selectOption(option)"
      >
        <span>{{ getOptionLabel(option) }}</span>
        <span v-if="isSelected(option)" class="check-icon">✓</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number, Object, null],
    default: null
  },
  options: {
    type: Array,
    required: true
  },
  label: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: 'Выберите...'
  },
  emptyOptionText: {
    type: String,
    default: 'Все'
  },
  showEmptyOption: {
    type: Boolean,
    default: true
  },
  optionLabel: {
    type: [String, Function],
    default: 'label'
  },
  optionValue: {
    type: [String, Function],
    default: 'value'
  },
  minWidth: {
    type: String,
    default: '180px'
  },
  flex: {
    type: String,
    default: '1'
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const isOpen = ref(false)
const wrapperRef = ref(null)

const getOptionLabel = (option) => {
  if (typeof props.optionLabel === 'function') {
    return props.optionLabel(option)
  }
  if (typeof option === 'string' || typeof option === 'number') {
    return option
  }
  return option[props.optionLabel] || option.name || option.label || String(option)
}

const getOptionValue = (option) => {
  if (typeof props.optionValue === 'function') {
    return props.optionValue(option)
  }
  if (typeof option === 'string' || typeof option === 'number') {
    return option
  }
  return option[props.optionValue] || option.id || option.value || option
}

const isSelected = (option) => {
  const optionValue = getOptionValue(option)
  return optionValue === props.modelValue
}

const selectedValue = computed(() => props.modelValue)

const displayValue = computed(() => {
  if (!props.modelValue) return null
  
  // Если есть пустая опция и выбрана она
  if (props.showEmptyOption && !props.modelValue) {
    return props.emptyOptionText
  }
  
  // Ищем выбранную опцию
  const selected = props.options.find(opt => isSelected(opt))
  if (selected) {
    return getOptionLabel(selected)
  }
  
  // Если значение не найдено, возвращаем само значение
  return String(props.modelValue)
})

const selectOption = (option, emptyText = null) => {
  if (option === null) {
    emit('update:modelValue', null)
    emit('change', null)
  } else {
    const value = getOptionValue(option)
    emit('update:modelValue', value)
    emit('change', value)
  }
  isOpen.value = false
}


const handleClickOutside = (event) => {
  const target = event.target
  if (wrapperRef.value && !wrapperRef.value.contains(target)) {
    isOpen.value = false
  }
}

// Закрываем все другие селекты при открытии этого
const handleSelectOpen = () => {
  // Отправляем событие для закрытия всех других селектов
  window.dispatchEvent(new CustomEvent('closeAllSelects'))
}

const handleCloseAllSelects = () => {
  // Закрываем этот селект при открытии другого
  // Используем небольшую задержку, чтобы текущий селект успел открыться
  if (isOpen.value && wrapperRef.value) {
    setTimeout(() => {
      // Проверяем, открыт ли этот селект (если нет - значит был открыт другой)
      if (isOpen.value) {
        const select = wrapperRef.value.querySelector('.custom-select')
        // Если у селекта нет класса is-open, значит он был закрыт
        // Или если есть другой открытый селект
        const allOpenSelects = document.querySelectorAll('.custom-select.is-open')
        if (allOpenSelects.length > 1 || (select && !select.classList.contains('is-open'))) {
          isOpen.value = false
        }
      }
    }, 10)
  }
}

const toggleDropdown = () => {
  if (!isOpen.value) {
    // Перед открытием закрываем все другие селекты
    handleSelectOpen()
    // Открываем этот селект
    isOpen.value = true
  } else {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  window.addEventListener('closeAllSelects', handleCloseAllSelects)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  window.removeEventListener('closeAllSelects', handleCloseAllSelects)
})
</script>

<style scoped>
.custom-select-wrapper {
  position: relative;
  flex: 1;
  min-width: 180px;
  max-width: 100%;
  box-sizing: border-box;
}

.select-label {
  position: absolute;
  top: -8px;
  left: 12px;
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  background: #fff;
  padding: 0 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  z-index: 2;
  pointer-events: none;
}

.custom-select {
  position: relative;
  width: 100%;
  max-width: 100%;
  padding: 10px 36px 10px 12px;
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 42px;
  user-select: none;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  box-sizing: border-box;
  overflow: hidden;
}

.custom-select:hover {
  border-color: #d1d5db;
  background: linear-gradient(180deg, #fafafa 0%, #f5f5f5 100%);
  box-shadow: 0 2px 4px rgba(0,0,0,0.08);
  transform: translateY(-1px);
}

.custom-select.is-open {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.1), 0 4px 12px rgba(59,130,246,0.15);
  background: #fff;
  transform: translateY(0);
}

.custom-select-value {
  font-size: 14px;
  color: #111827;
  font-weight: 400;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.custom-select-value.placeholder {
  color: #9ca3af;
}

.custom-select-arrow {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #6b7280;
  font-size: 10px;
  transition: transform 0.2s ease;
  pointer-events: none;
}

.custom-select.is-open .custom-select-arrow {
  transform: translateY(-50%) rotate(180deg);
  color: #3b82f6;
}

.custom-select-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: #fff;
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.1), 0 4px 10px rgba(0,0,0,0.05);
  z-index: 100;
  max-height: 300px;
  overflow-y: auto;
  overflow-x: hidden;
  animation: slideDown 0.2s ease;
  box-sizing: border-box;
  min-width: 0;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.custom-select-dropdown::-webkit-scrollbar {
  width: 6px;
}

.custom-select-dropdown::-webkit-scrollbar-track {
  background: #f9fafb;
  border-radius: 3px;
}

.custom-select-dropdown::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.custom-select-dropdown::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

.custom-select-option {
  padding: 12px 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: all 0.15s ease;
  border-left: 3px solid transparent;
  font-size: 14px;
  color: #111827;
  position: relative;
  min-width: 0;
  overflow: hidden;
}

.custom-select-option > span:first-child {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.custom-select-option:first-child {
  border-radius: 8px 8px 0 0;
}

.custom-select-option:last-child {
  border-radius: 0 0 8px 8px;
}

.custom-select-option:hover {
  background: linear-gradient(90deg, #f3f4f6 0%, #f9fafb 100%);
  border-left-color: #3b82f6;
  padding-left: 13px;
}

.custom-select-option.is-selected {
  background: linear-gradient(90deg, #eff6ff 0%, #dbeafe 100%);
  color: #2563eb;
  font-weight: 600;
  border-left-color: #3b82f6;
  box-shadow: inset 0 0 0 1px rgba(59,130,246,0.1);
}

.custom-select-option.is-selected:hover {
  background: linear-gradient(90deg, #dbeafe 0%, #bfdbfe 100%);
}

.check-icon {
  color: #2563eb;
  font-weight: 700;
  font-size: 18px;
  margin-left: 8px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: rgba(37,99,235,0.1);
  border-radius: 50%;
  line-height: 1;
}
</style>
