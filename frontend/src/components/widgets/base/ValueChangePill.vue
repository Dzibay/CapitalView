<script setup>
import { computed } from 'vue'
import ValueChange from './ValueChange.vue'

const props = defineProps({
  value: {
    type: [Number, String],
    required: true
  },
  isPositive: {
    type: Boolean,
    default: null
  },
  format: {
    type: String,
    default: 'percent',
    validator: (v) => ['percent', 'currency', 'number'].includes(v)
  },
  showArrow: {
    type: Boolean,
    default: true
  }
})

const isNegative = computed(() => {
  if (props.isPositive === true) return false
  if (props.isPositive === false) return true
  const n = typeof props.value === 'string' ? parseFloat(props.value) : props.value
  return typeof n === 'number' && n < 0
})
</script>

<template>
  <span
    class="value-change-pill"
    :class="{ 'value-change-pill--negative': isNegative }"
  >
    <ValueChange
      :value="value"
      :is-positive="isPositive"
      :format="format"
      :show-arrow="showArrow"
    />
  </span>
</template>

<style scoped>
.value-change-pill {
  display: inline-flex;
  align-items: center;
  padding: 1px 6px;
  border-radius: 999px;
  font-size: var(--widget-font-small, 0.8125rem);
  font-weight: 500;
  line-height: 1.15;
  background: rgba(28, 189, 136, 0.12);
}
.value-change-pill :deep(.value-change) {
  font-size: inherit;
  font-weight: inherit;
  line-height: inherit;
  gap: 0.12rem;
}
.value-change-pill :deep(.arrow-icon svg) {
  width: 12px;
  height: 12px;
}
.value-change-pill :deep(.value-change.positive) {
  color: var(--positiveColor);
}
.value-change-pill--negative {
  background: rgba(239, 68, 68, 0.12);
}
.value-change-pill--negative :deep(.value-change.negative) {
  color: var(--negativeColor);
}
</style>
