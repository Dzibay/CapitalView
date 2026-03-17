<script setup>
import { computed, watch } from 'vue'
import { normalizeDateToString, extractDateFromString } from '../../utils/date'

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
    // Нормализуем дату, если она передана
    const normalized = normalizeDateToString(props.max)
    return normalized || props.max
  }
  // По умолчанию - сегодняшняя дата в формате YYYY-MM-DD
  return normalizeDateToString(new Date()) || ''
})

// Вычисляем минимальную дату (ВАЖНО: всегда возвращаем строку или undefined, но не null)
// Нормализуем дату, извлекая только YYYY-MM-DD из строки (например, из "2024-11-08T00:00:00")
const minDate = computed(() => {
  if (props.min !== null && props.min !== undefined && props.min !== '') {
    // Используем утилиту для нормализации даты (извлекает YYYY-MM-DD из ISO строки)
    const normalized = normalizeDateToString(props.min)
    return normalized || undefined
  }
  // Если min не задан, возвращаем undefined, чтобы атрибут min не устанавливался
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
  
  // Валидация минимальной даты (используем нормализованные даты для сравнения)
  if (minDate.value && newValue) {
    const normalizedNewValue = normalizeDateToString(newValue)
    const normalizedMinDate = normalizeDateToString(minDate.value)
    
    if (normalizedNewValue && normalizedMinDate && normalizedNewValue < normalizedMinDate) {
      // Устанавливаем минимальную дату
      event.target.value = normalizedMinDate
      emit('update:modelValue', normalizedMinDate)
      return
    }
  }
  
  // Нормализуем значение перед отправкой
  const normalizedValue = normalizeDateToString(newValue) || newValue
  emit('update:modelValue', normalizedValue)
}

// Автоматическая корректировка даты при изменении min
watch(() => props.min, (newMin, oldMin) => {
  if (newMin && props.modelValue && oldMin !== undefined) {
    const normalizedCurrent = normalizeDateToString(props.modelValue)
    const normalizedMin = normalizeDateToString(newMin)
    
    if (normalizedCurrent && normalizedMin && normalizedCurrent < normalizedMin) {
      emit('update:modelValue', normalizedMin)
    }
  }
})

// Валидация при изменении значения
watch(() => props.modelValue, (newValue) => {
  if (minDate.value && newValue) {
    const normalizedNewValue = normalizeDateToString(newValue)
    const normalizedMinDate = normalizeDateToString(minDate.value)
    
    if (normalizedNewValue && normalizedMinDate && normalizedNewValue < normalizedMinDate) {
      emit('update:modelValue', normalizedMinDate)
    }
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
    :min="minDate"
    :required="required"
    :disabled="disabled"
    :placeholder="placeholder"
    :class="inputClass"
    @input="handleInput"
    @change="handleInput"
  />
</template>