<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: {
    type: [Number, String],
    required: true
  },
  isPositive: {
    type: Boolean,
    default: null // null = автоматическое определение
  },
  /** Показывать префикс + / − перед значением */
  showArrow: {
    type: Boolean,
    default: true
  },
  format: {
    type: String,
    default: 'percent', // 'percent', 'currency', 'number'
    validator: (value) => ['percent', 'currency', 'number'].includes(value)
  }
})

const computedIsPositive = computed(() => {
  if (props.isPositive !== null) return props.isPositive
  const numValue = typeof props.value === 'string' ? parseFloat(props.value) : props.value
  return numValue >= 0
})

const formattedValue = computed(() => {
  const numValue = typeof props.value === 'string' ? parseFloat(props.value) : props.value
  // Math.abs(): знак показывает префикс + / −
  const absValue = Math.abs(numValue)
  
  if (props.format === 'percent') {
    return `${absValue.toFixed(2)}%`
  } else if (props.format === 'currency') {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0
    }).format(absValue)
  } else {
    return `${absValue}`
  }
})
</script>

<template>
  <div 
    class="value-change" 
    :class="{ 'positive': computedIsPositive, 'negative': !computedIsPositive }"
  >
    <span
      v-if="showArrow"
      class="sign-prefix"
      :class="{ 'sign-prefix--positive': computedIsPositive, 'sign-prefix--negative': !computedIsPositive }"
      aria-hidden="true"
    >{{ computedIsPositive ? '+' : '−' }}</span>
    <span>{{ formattedValue }}</span>
  </div>
</template>

<style scoped>
.value-change {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: var(--text-caption-size);
  font-weight: var(--text-body-secondary-weight);
}

.value-change.positive {
  color: var(--positiveColor);
}

.value-change.negative {
  color: var(--negativeColor);
}

.sign-prefix {
  flex-shrink: 0;
  font-weight: 600;
  line-height: 1;
}

.sign-prefix--positive {
  color: var(--positiveColor);
}

.sign-prefix--negative {
  color: var(--negativeColor);
}
</style>
