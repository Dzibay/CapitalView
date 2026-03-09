<template>
  <div class="form-field" :class="{ 'date-field': dateField }">
    <label v-if="label" class="form-label">
      <component v-if="icon" :is="icon" :size="16" class="label-icon" />
      <span>{{ label }}</span>
      <component v-if="loadingIcon" :is="loadingIcon" :size="14" class="loading-icon" />
    </label>
    <input
      :id="id"
      :name="name"
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :required="required"
      :disabled="disabled"
      :min="min"
      :max="max"
      :step="step"
      :class="computedInputClass"
      @input="handleInput"
      @change="handleChange"
    />
    <small v-if="hint" class="form-hint">
      <component v-if="hintIcon" :is="hintIcon" :size="12" class="hint-icon" />
      <span>{{ hint }}</span>
    </small>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  },
  label: {
    type: String,
    default: ''
  },
  icon: {
    type: Object,
    default: null
  },
  hint: {
    type: String,
    default: ''
  },
  hintIcon: {
    type: Object,
    default: null
  },
  loadingIcon: {
    type: Object,
    default: null
  },
  type: {
    type: String,
    default: 'text',
    validator: (value) => ['text', 'number', 'email', 'password', 'tel', 'url', 'search'].includes(value)
  },
  placeholder: {
    type: String,
    default: ''
  },
  required: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  },
  min: {
    type: [String, Number],
    default: undefined
  },
  max: {
    type: [String, Number],
    default: undefined
  },
  step: {
    type: [String, Number],
    default: undefined
  },
  id: {
    type: String,
    default: ''
  },
  name: {
    type: String,
    default: ''
  },
  dateField: {
    type: Boolean,
    default: false
  },
  // Для дополнительных классов
  inputClass: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

const computedInputClass = computed(() => {
  const baseClass = 'form-input'
  const classes = [baseClass]
  
  // Добавляем класс для числовых полей, чтобы убрать стрелочки
  if (props.type === 'number') {
    classes.push('number-input')
  }
  
  // Добавляем дополнительные классы, если они переданы
  if (props.inputClass) {
    classes.push(props.inputClass)
  }
  
  return classes.join(' ')
})

const handleInput = (event) => {
  let value = event.target.value
  
  // Для числовых полей конвертируем в число, если значение не пустое
  if (props.type === 'number') {
    if (value === '' || value === '-') {
      // Разрешаем пустое значение и минус для отрицательных чисел
      emit('update:modelValue', value === '' ? null : value)
    } else {
      const numValue = parseFloat(value)
      if (!isNaN(numValue)) {
        emit('update:modelValue', numValue)
      } else {
        // Если не удалось распарсить, оставляем как есть (для частичного ввода)
        emit('update:modelValue', value)
      }
    }
  } else {
    emit('update:modelValue', value)
  }
}

const handleChange = (event) => {
  handleInput(event)
}
</script>

<style scoped>
.form-field {
  display: flex;
  flex-direction: column;
}

.form-field.date-field {
  margin-top: 4px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  letter-spacing: -0.01em;
}

.label-icon {
  color: #6b7280;
  flex-shrink: 0;
}

.loading-icon {
  color: #3b82f6;
  animation: spin 1s linear infinite;
  margin-left: 8px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.form-input {
  width: 100%;
  padding: 11px 14px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  font-size: 14px;
  transition: all 0.2s ease;
  background: #fff;
  color: #111827;
  box-sizing: border-box;
  font-family: inherit;
}

.form-input::placeholder {
  color: #9ca3af;
}

.form-input:hover {
  border-color: #d1d5db;
  background: #fafafa;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
  background: #fff;
}

.form-input:disabled {
  background: #f9fafb;
  color: #9ca3af;
  cursor: not-allowed;
}

/* Убираем стрелочки у полей ввода чисел */
.number-input::-webkit-inner-spin-button,
.number-input::-webkit-outer-spin-button {
  -webkit-appearance: none;
  appearance: none;
  margin: 0;
}

.number-input {
  -moz-appearance: textfield;
  appearance: textfield;
}

.form-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  font-size: 12px;
  color: #6b7280;
}

.hint-icon {
  color: #9ca3af;
  flex-shrink: 0;
}
</style>
