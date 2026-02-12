<script setup>
import Widget from './Widget.vue'
import { formatCurrency } from '../../utils/formatCurrency'
import ValueChange from './ValueChange.vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  items: {
    type: Array,
    required: true,
    // Каждый item: { label, value, format?, isPositive?, showValueChange?, colorClass? }
    validator: (items) => {
      return Array.isArray(items) && items.every(item => 
        typeof item === 'object' && 
        item !== null && 
        'label' in item && 
        'value' in item
      )
    }
  }
})

// Форматирование значения
const formatValue = (item) => {
  const value = item.value
  
  if (item.format === 'currency') {
    return formatCurrency(value)
  } else if (item.format === 'percent') {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  } else if (item.format === 'number') {
    if (typeof value === 'number') {
      // Если число целое, не показываем десятичные знаки
      return value % 1 === 0 ? value.toString() : value.toFixed(2)
    }
    return value
  }
  
  return value
}
</script>

<template>
  <Widget :title="title">
    <div class="metrics-section">
      <div 
        v-for="(item, index) in items" 
        :key="index"
        class="stat-item"
        :class="item.colorClass || (item.isPositive !== undefined ? (item.isPositive ? 'profit' : 'loss') : '')"
      >
        <span class="stat-label">{{ item.label }}</span>
        <span class="stat-value">
          <template v-if="item.showValueChange && item.format === 'percent'">
            <ValueChange 
              :value="item.value" 
              :isPositive="item.isPositive"
              format="percent"
            />
          </template>
          <template v-else>
            {{ formatValue(item) }}
          </template>
        </span>
      </div>
    </div>
  </Widget>
</template>

<style scoped>
.metrics-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  height: 100%;
  margin-top: 1rem;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 0.5rem 0;
  gap: 0.5rem;
  flex-wrap: wrap;
  border-bottom: 1px solid #f3f4f6;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-item.profit .stat-value {
  color: var(--positiveColor, #1CBD88);
}

.stat-item.loss .stat-value {
  color: var(--negativeColor, #EF4444);
}

.stat-label {
  color: #6b7280;
  font-size: 0.875rem;
  flex: 1;
}

.stat-value {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #111827;
  text-align: right;
}
</style>
