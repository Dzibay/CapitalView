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
  // Используем Math.abs() чтобы убрать знак минуса, так как стрелка уже показывает направление
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
    <span v-if="showArrow" class="arrow-icon" :class="{ 'up': computedIsPositive, 'down': !computedIsPositive }">
      <svg v-if="computedIsPositive" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="18 15 12 9 6 15"></polyline>
      </svg>
      <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="6 9 12 15 18 9"></polyline>
      </svg>
    </span>
    <span>{{ formattedValue }}</span>
  </div>
</template>

<style scoped>
.value-change {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  font-weight: 400;
}

.value-change.positive {
  color: var(--positiveColor);
}

.value-change.negative {
  color: var(--negativeColor);
}

.arrow-icon {
  display: flex;
  align-items: center;
}

.arrow-icon.up {
  color: var(--positiveColor);
}

.arrow-icon.down {
  color: var(--negativeColor);
}
</style>
