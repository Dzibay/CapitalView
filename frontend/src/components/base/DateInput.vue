<script setup>
import { computed, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  // Максимальная дата (по умолчанию - сегодня)
  max: {
    type: String,
    default: null
  },
  // Минимальная дата (опционально)
  min: {
    type: String,
    default: null
  },
  // Все остальные стандартные атрибуты input
  required: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  },
  placeholder: {
    type: String,
    default: ''
  },
  id: {
    type: String,
    default: ''
  },
  name: {
    type: String,
    default: ''
  },
  // Дополнительные классы CSS
  class: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

// Вычисляем максимальную дату (сегодня по умолчанию)
const maxDate = computed(() => {
  if (props.max !== null && props.max !== undefined) {
    return props.max
  }
  // По умолчанию - сегодняшняя дата в формате YYYY-MM-DD
  const today = new Date()
  return today.toISOString().split('T')[0]
})

// Вычисляем минимальную дату (только если она установлена)
const minDate = computed(() => {
  if (props.min !== null && props.min !== undefined && props.min !== '') {
    return props.min
  }
  return undefined
})

// Вычисляем классы для input
const inputClass = computed(() => {
  const baseClass = 'form-input'
  return props.class ? `${baseClass} ${props.class}` : baseClass
})

// Обработчик изменения значения
const handleInput = (event) => {
  const newValue = event.target.value
  // Валидация: если выбрана дата раньше minDate, корректируем её
  if (minDate.value && newValue && new Date(newValue) < new Date(minDate.value)) {
    event.target.value = minDate.value
    emit('update:modelValue', minDate.value)
    return
  }
  emit('update:modelValue', newValue)
}

// Автоматическая корректировка даты при изменении min
// НЕ используем immediate: true, чтобы не сбрасывать дату при инициализации
watch(() => props.min, (newMin, oldMin) => {
  // Корректируем дату только если min действительно изменился (не при первой установке)
  if (newMin && props.modelValue && oldMin !== undefined) {
    const currentDate = new Date(props.modelValue)
    const minDate = new Date(newMin)
    // Если текущая дата раньше минимальной, обновляем её
    if (currentDate < minDate) {
      emit('update:modelValue', newMin)
    }
  }
})

// Валидация при изменении значения
watch(() => props.modelValue, (newValue) => {
  if (minDate.value && newValue && new Date(newValue) < new Date(minDate.value)) {
    // Если дата раньше минимальной, корректируем её
    emit('update:modelValue', minDate.value)
  }
})
</script>

<template>
  <input
    :id="id"
    :name="name"
    type="date"
    :value="modelValue"
    :max="maxDate"
    :min="minDate || undefined"
    :required="required"
    :disabled="disabled"
    :placeholder="placeholder"
    :class="inputClass"
    @input="handleInput"
    @change="handleInput"
  />
</template>
