<script setup>
import { computed } from 'vue'

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
  if (props.max !== null) {
    return props.max
  }
  // По умолчанию - сегодняшняя дата в формате YYYY-MM-DD
  const today = new Date()
  return today.toISOString().split('T')[0]
})

// Вычисляем классы для input
const inputClass = computed(() => {
  const baseClass = 'form-input'
  return props.class ? `${baseClass} ${props.class}` : baseClass
})

// Обработчик изменения значения
const handleInput = (event) => {
  emit('update:modelValue', event.target.value)
}
</script>

<template>
  <input
    :id="id"
    :name="name"
    type="date"
    :value="modelValue"
    :max="maxDate"
    :min="min"
    :required="required"
    :disabled="disabled"
    :placeholder="placeholder"
    :class="inputClass"
    @input="handleInput"
  />
</template>
