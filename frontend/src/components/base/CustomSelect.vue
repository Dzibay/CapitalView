<template>
  <div ref="wrapperRef" class="custom-select-wrapper" :style="{ minWidth: minWidth, flex: flex }">
    <span v-if="label" class="select-label">{{ label }}</span>
    <div 
      class="custom-select" 
      :class="{ 'is-open': isOpen }" 
      @click="toggleDropdown"
    >
      <span class="custom-select-value" :class="{ 'placeholder': !hasSelection }">
        {{ displayValue || placeholder }}
      </span>
      <span class="custom-select-arrow">▼</span>
    </div>
    <Teleport to="body">
      <div 
        v-if="isOpen" 
        ref="dropdownRef"
        class="custom-select-dropdown" 
        :class="{ 
          'dropdown-top': dropdownPosition === 'top',
          'dropdown-positioned': isDropdownPositioned
        }"
        :style="dropdownStyle"
        @click.stop
      >
      <div 
        v-if="showEmptyOption"
        class="custom-select-option" 
        :class="{ 'is-selected': !hasSelection }"
        @click="selectOption(null, emptyOptionText)"
      >
        <span>{{ emptyOptionText }}</span>
        <span v-if="!hasSelection" class="check-icon">✓</span>
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
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { Teleport } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number, Object, Array, null],
    default: null
  },
  /** Несколько значений; modelValue — массив выбранных optionValue */
  multiple: {
    type: Boolean,
    default: false
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
const dropdownRef = ref(null)
const dropdownPosition = ref('bottom') // 'bottom' или 'top'
const dropdownStyle = ref({})
const isDropdownPositioned = ref(false) // Флаг для отслеживания готовности позиции

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

const selectedValuesArray = computed(() => {
  if (!props.multiple) return []
  const v = props.modelValue
  if (Array.isArray(v)) return v
  return []
})

const hasSelection = computed(() => {
  if (props.multiple) {
    return selectedValuesArray.value.length > 0
  }
  const v = props.modelValue
  return v != null && v !== ''
})

const isSelected = (option) => {
  const optionValue = getOptionValue(option)
  if (props.multiple) {
    return selectedValuesArray.value.some((v) => v === optionValue)
  }
  return optionValue === props.modelValue
}

const displayValue = computed(() => {
  if (props.multiple) {
    const vals = selectedValuesArray.value
    if (vals.length === 0) return null
    const labels = vals.map((v) => {
      const opt = props.options.find((o) => getOptionValue(o) === v)
      return opt ? getOptionLabel(opt) : String(v)
    })
    if (labels.length === 1) return labels[0]
    const joined = labels.join(', ')
    if (joined.length <= 48) return joined
    return `${labels.slice(0, 2).join(', ')} (+${labels.length - 2})`
  }

  if (props.modelValue == null || props.modelValue === '') return null

  if (props.showEmptyOption && !props.modelValue) {
    return props.emptyOptionText
  }

  const selected = props.options.find((opt) => getOptionValue(opt) === props.modelValue)
  if (selected) {
    return getOptionLabel(selected)
  }

  return String(props.modelValue)
})

const selectOption = (option, emptyText = null) => {
  if (props.multiple) {
    if (option === null) {
      emit('update:modelValue', [])
      emit('change', [])
      isOpen.value = false
      return
    }
    const value = getOptionValue(option)
    const current = [...selectedValuesArray.value]
    const idx = current.findIndex((v) => v === value)
    if (idx >= 0) {
      current.splice(idx, 1)
    } else {
      current.push(value)
    }
    emit('update:modelValue', current)
    emit('change', current)
    return
  }

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
  if (!wrapperRef.value) return
  if (wrapperRef.value.contains(target)) return
  // Dropdown teleported to body — клик по опции не внутри wrapperRef
  if (dropdownRef.value?.contains(target)) return
  isOpen.value = false
  dropdownPosition.value = 'bottom'
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

// Функция для определения позиции выпадающего списка
const calculateDropdownPosition = (isInitial = false) => {
  if (!wrapperRef.value || !isOpen.value) return
  
  // Сбрасываем флаг позиционирования только при первом открытии
  if (isInitial) {
    isDropdownPositioned.value = false
  }
  
  // Небольшая задержка для того, чтобы DOM обновился (Teleport требует времени)
  setTimeout(() => {
    if (!wrapperRef.value) return
    
    if (!dropdownRef.value) {
      // Повторяем попытку через небольшой интервал
      setTimeout(() => calculateDropdownPosition(isInitial), 50)
      return
    }
    
    const wrapperRect = wrapperRef.value.getBoundingClientRect()
    const viewportHeight = window.innerHeight
    const viewportWidth = window.innerWidth
    
    // Предполагаемая высота выпадающего списка (максимум 300px или меньше)
    const optionCount = props.showEmptyOption ? props.options.length + 1 : props.options.length
    const estimatedDropdownHeight = Math.min(300, optionCount * 48 + 20)
    
    // Вычисляем доступное пространство снизу и сверху
    const spaceBelow = viewportHeight - wrapperRect.bottom - 20 // 20px отступ от края
    const spaceAbove = wrapperRect.top - 20 // 20px отступ от края
    
    // Определяем позицию (сверху или снизу)
    let position = 'bottom'
    if (spaceBelow < estimatedDropdownHeight && spaceAbove > spaceBelow && spaceAbove > 100) {
      position = 'top'
    }
    dropdownPosition.value = position
    
    // Вычисляем абсолютные координаты для позиционирования
    const top = position === 'bottom' 
      ? wrapperRect.bottom + 4 
      : wrapperRect.top - estimatedDropdownHeight - 4
    
    // Ограничиваем позицию, чтобы не выходить за границы экрана
    const maxTop = Math.max(20, viewportHeight - estimatedDropdownHeight - 20)
    const finalTop = Math.min(Math.max(20, top), maxTop)
    
    // Вычисляем left и width
    const left = wrapperRect.left
    const width = wrapperRect.width
    
    // Проверяем, не выходит ли за правый край
    const maxLeft = viewportWidth - width - 20
    const finalLeft = Math.min(Math.max(20, left), maxLeft)
    
    // Вычисляем максимальную высоту с учетом доступного пространства
    const availableSpace = position === 'bottom' ? spaceBelow : spaceAbove
    const maxHeight = Math.min(estimatedDropdownHeight, availableSpace)
    
    // Устанавливаем стили для позиционирования
    dropdownStyle.value = {
      position: 'fixed',
      top: `${finalTop}px`,
      left: `${finalLeft}px`,
      width: `${width}px`,
      maxHeight: `${maxHeight}px`
    }
    
    // Помечаем, что позиция вычислена и элемент можно показывать
    isDropdownPositioned.value = true
  }, isInitial ? 50 : 0) // Задержка только при первом открытии

  // Fallback: на мобильных Teleport может быть медленнее — через 200ms показываем dropdown
  if (isInitial && isOpen.value) {
    setTimeout(() => {
      if (isOpen.value && !isDropdownPositioned.value && dropdownRef.value) {
        isDropdownPositioned.value = true
      }
    }, 200)
  }
}

const toggleDropdown = () => {
  if (!isOpen.value) {
    // Перед открытием закрываем все другие селекты
    handleSelectOpen()
    // Сбрасываем флаг позиционирования
    isDropdownPositioned.value = false
    // Открываем этот селект
    isOpen.value = true
    // Вычисляем позицию после открытия с небольшой задержкой для Teleport (первое открытие)
    nextTick(() => {
      calculateDropdownPosition(true)
    })
  } else {
    isOpen.value = false
    dropdownPosition.value = 'bottom' // Сбрасываем позицию
    isDropdownPositioned.value = false
  }
}

// Отслеживаем изменения открытия для пересчета позиции
watch(isOpen, (newVal) => {
  if (newVal) {
    // Сбрасываем флаг позиционирования
    isDropdownPositioned.value = false
    // Вычисляем позицию после открытия с задержкой для Teleport (первое открытие)
    nextTick(() => {
      calculateDropdownPosition(true)
    })
  } else {
    dropdownPosition.value = 'bottom'
    isDropdownPositioned.value = false
  }
})

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  window.addEventListener('closeAllSelects', handleCloseAllSelects)
  window.addEventListener('resize', () => calculateDropdownPosition(false))
  window.addEventListener('scroll', () => calculateDropdownPosition(false), true)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  window.removeEventListener('closeAllSelects', handleCloseAllSelects)
  window.removeEventListener('resize', calculateDropdownPosition)
  window.removeEventListener('scroll', calculateDropdownPosition, true)
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
  padding: 9px 36px 9px 12px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 42px;
  user-select: none;
  box-sizing: border-box;
  overflow: hidden;
}

.custom-select:hover {
  border-color: #d1d5db;
  background: #fafafa;
}

.custom-select.is-open {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
  background: #fff;
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
  font-size: 12px;
  transition: all 0.2s ease;
  pointer-events: none;
  display: flex;
  align-items: center;
  justify-content: center;
}

.custom-select:hover .custom-select-arrow {
  color: #374151;
}

.custom-select.is-open .custom-select-arrow {
  transform: translateY(-50%) rotate(180deg);
  color: #3b82f6;
}

.custom-select-dropdown {
  position: fixed !important;
  background: #fff !important;
  border: 1.5px solid #e5e7eb !important;
  border-radius: 8px !important;
  box-shadow: 0 10px 25px rgba(0,0,0,0.1), 0 4px 10px rgba(0,0,0,0.05) !important;
  z-index: 10000 !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
  box-sizing: border-box !important;
  min-width: 0 !important;
  /* Скрываем до вычисления позиции */
  opacity: 0 !important;
  visibility: hidden !important;
  pointer-events: none !important;
  transition: opacity 0.1s ease, visibility 0.1s ease !important;
}

.custom-select-dropdown.dropdown-positioned {
  opacity: 1 !important;
  visibility: visible !important;
  pointer-events: auto !important;
  animation: slideDown 0.2s ease !important;
}

.custom-select-dropdown.dropdown-top.dropdown-positioned {
  animation: slideUp 0.2s ease !important;
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

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(8px);
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
  /* Убирает 300ms задержку клика на мобильных */
  touch-action: manipulation;
  min-height: 44px;
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
