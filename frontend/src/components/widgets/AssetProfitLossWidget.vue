<script setup>
import MetricsWidget from './MetricsWidget.vue'
import { computed } from 'vue'

const props = defineProps({
  invested: {
    type: Number,
    default: 0
  },
  currentValue: {
    type: Number,
    default: 0
  },
  profit: {
    type: Number,
    default: 0
  },
  isProfit: {
    type: Boolean,
    default: false
  },
  realizedProfit: {
    type: Number,
    default: 0
  },
  receivedPayouts: {
    type: Number,
    default: 0
  },
  totalProfit: {
    type: Number,
    default: 0
  },
  isTotalProfit: {
    type: Boolean,
    default: false
  }
})

const items = computed(() => [
  { label: 'Инвестировано', value: props.invested || 0, format: 'currency' },
  { label: 'Текущая стоимость', value: props.currentValue || 0, format: 'currency' },
  { 
    label: 'Нереализованная прибыль', 
    value: props.profit || 0, 
    format: 'currency',
    isPositive: props.isProfit
  },
  { 
    label: 'Прибыль от продаж', 
    value: props.realizedProfit || 0, 
    format: 'currency',
    isPositive: props.realizedProfit >= 0
  },
  { 
    label: 'Получено выплат', 
    value: props.receivedPayouts || 0, 
    format: 'currency',
    colorClass: 'profit'
  },
  { 
    label: 'Общая прибыль', 
    value: props.totalProfit || 0, 
    format: 'currency',
    isPositive: props.isTotalProfit
  }
])
</script>

<template>
  <MetricsWidget title="Прибыль и убытки" :items="items" />
</template>
