<script setup>
import { computed } from 'vue'
import Widget from './Widget.vue'
import ValueChange from './ValueChange.vue'
import Tooltip from '../../Tooltip.vue'
import { formatCurrency } from '../../../utils/formatCurrency'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  // Основное значение
  mainValue: {
    type: [Number, String],
    required: true
  },
  // Формат основного значения: 'currency', 'percent', 'number', 'custom'
  mainValueFormat: {
    type: String,
    default: 'currency',
    validator: (value) => ['currency', 'percent', 'number', 'custom'].includes(value)
  },
  // Подсказка для основного значения
  mainValueTooltip: {
    type: String,
    default: null
  },
  // Изменение значения (для ValueChange)
  changeValue: {
    type: Number,
    default: null
  },
  // Является ли изменение положительным
  changeIsPositive: {
    type: Boolean,
    default: null
  },
  // Подсказка для изменения
  changeTooltip: {
    type: String,
    default: null
  },
  // Вторичный текст (под основным значением)
  secondaryText: {
    type: String,
    default: null
  },
  // Вторичное значение (если нужно отформатировать)
  secondaryValue: {
    type: [Number, String],
    default: null
  },
  // Формат вторичного значения
  secondaryFormat: {
    type: String,
    default: 'currency',
    validator: (value) => ['currency', 'percent', 'number', 'custom'].includes(value)
  },
  // Класс для вторичного значения (например, 'positive', 'negative')
  secondaryClass: {
    type: String,
    default: null
  },
  // Позиция ValueChange: 'right' (по умолчанию) или 'below'
  changePosition: {
    type: String,
    default: 'right',
    validator: (value) => ['right', 'below'].includes(value)
  },
  // Суффикс для вторичного текста (например, " в месяц")
  secondaryTextSuffix: {
    type: String,
    default: null
  },
  // Подсказка для вторичного значения
  secondaryTooltip: {
    type: String,
    default: null
  },
  // Суффикс для основного значения (например, " в год")
  mainValueSuffix: {
    type: String,
    default: null
  }
})

// Форматирование основного значения
const formattedMainValue = computed(() => {
  if (props.mainValueFormat === 'custom') {
    return props.mainValue
  }
  
  if (props.mainValueFormat === 'currency') {
    return formatCurrency(Number(props.mainValue) || 0)
  }
  
  if (props.mainValueFormat === 'percent') {
    return new Intl.NumberFormat('ru-RU', {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format((Number(props.mainValue) || 0) / 100)
  }
  
  if (props.mainValueFormat === 'number') {
    const num = Number(props.mainValue) || 0
    return num.toFixed(2)
  }
  
  return props.mainValue
})

// Форматирование вторичного значения
const formattedSecondaryValue = computed(() => {
  if (!props.secondaryValue && props.secondaryValue !== 0) {
    return null
  }
  
  if (props.secondaryFormat === 'custom') {
    return props.secondaryValue
  }
  
  if (props.secondaryFormat === 'currency') {
    return formatCurrency(Number(props.secondaryValue) || 0)
  }
  
  if (props.secondaryFormat === 'percent') {
    return new Intl.NumberFormat('ru-RU', {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format((Number(props.secondaryValue) || 0) / 100)
  }
  
  if (props.secondaryFormat === 'number') {
    const num = Number(props.secondaryValue) || 0
    return num.toFixed(2)
  }
  
  return props.secondaryValue
})

// Определение isPositive для changeValue, если не указано явно
const computedChangeIsPositive = computed(() => {
  if (props.changeIsPositive !== null && props.changeIsPositive !== undefined) {
    return props.changeIsPositive
  }
  if (props.changeValue !== null && props.changeValue !== undefined) {
    return props.changeValue >= 0
  }
  return null
})
</script>

<template>
  <Widget :title="title">
    <div 
      class="stat-card-content"
      :class="{ 'change-below': changePosition === 'below' }"
    >
      <!-- Основное значение с изменением -->
      <div class="main-value-row">
        <div class="main-value-wrapper">
          <Tooltip 
            v-if="mainValueTooltip" 
            :content="mainValueTooltip" 
            position="top"
          >
            <div class="main-value">
              {{ formattedMainValue }}
            </div>
          </Tooltip>
          <div v-else class="main-value">
            {{ formattedMainValue }}
          </div>
          <span v-if="(mainValueSuffix || (secondaryText && changePosition !== 'below' && !formattedSecondaryValue))" class="main-value-suffix">
            {{ mainValueSuffix || secondaryText }}
          </span>
        </div>
        
        <Tooltip 
          v-if="changeValue !== null && changeValue !== undefined && changeTooltip" 
          :content="changeTooltip" 
          position="top"
        >
          <ValueChange 
            v-if="changeValue !== null && changeValue !== undefined"
            :value="changeValue" 
            :is-positive="computedChangeIsPositive"
            format="percent"
          />
        </Tooltip>
        <ValueChange 
          v-else-if="changeValue !== null && changeValue !== undefined"
          :value="changeValue" 
          :is-positive="computedChangeIsPositive"
          format="percent"
        />
      </div>
      
      <!-- Вторичный текст -->
      <p v-if="secondaryText || formattedSecondaryValue" class="secondary-text">
        <Tooltip 
          v-if="secondaryValue !== null && secondaryValue !== undefined && secondaryTooltip"
          :content="secondaryTooltip" 
          position="top"
        >
          <span v-if="secondaryText && formattedSecondaryValue && secondaryText.includes(':')">{{ secondaryText }}</span>
          <span 
            v-if="formattedSecondaryValue !== null"
            :class="secondaryClass"
          >
            {{ formattedSecondaryValue }}
          </span>
          <span v-if="secondaryText && formattedSecondaryValue && !secondaryText.includes(':')">{{ secondaryText }}</span>
        </Tooltip>
        <template v-else>
          <span v-if="secondaryText && formattedSecondaryValue && secondaryText.includes(':')">{{ secondaryText }}</span>
          <span 
            v-if="formattedSecondaryValue !== null"
            :class="secondaryClass"
          >
            {{ formattedSecondaryValue }}
          </span>
          <span v-if="secondaryText && formattedSecondaryValue && !secondaryText.includes(':')">{{ secondaryText }}</span>
          <span v-else-if="secondaryText && !formattedSecondaryValue">{{ secondaryText }}</span>
        </template>
        <span v-if="secondaryTextSuffix && formattedSecondaryValue">{{ secondaryTextSuffix }}</span>
      </p>
    </div>
  </Widget>
</template>

<style scoped>
.stat-card-content {
  display: flex;
  flex-direction: column;
}

.main-value-row {
  margin: 15px 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-card-content.change-below .main-value-row {
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
}

.main-value-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
}

.main-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: #111827;
  line-height: 1.2;
}

.main-value-suffix {
  font-size: 1rem;
  color: #6b7280;
  line-height: 1;
  padding-bottom: 0.2rem;
  margin: 0;
}

.secondary-text {
  margin: 0;
  margin-top: 0;
  font-size: 1rem;
  color: #6b7280;
  line-height: 1.2;
}

.secondary-text .positive {
  color: var(--positiveColor, #1CBD88);
}

.secondary-text .negative {
  color: var(--negativeColor, #EF4444);
}
</style>
