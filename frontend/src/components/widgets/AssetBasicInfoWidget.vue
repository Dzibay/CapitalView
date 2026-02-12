<script setup>
import { computed } from 'vue'
import MetricsWidget from './MetricsWidget.vue'

const props = defineProps({
  quantity: {
    type: Number,
    default: 0
  },
  averagePrice: {
    type: Number,
    default: 0
  },
  lastPrice: {
    type: Number,
    default: 0
  },
  priceGrowth: {
    type: Object,
    default: null
  }
})

const items = computed(() => {
  const result = [
    { label: 'Количество', value: props.quantity || 0, format: 'number' },
    { label: 'Средняя цена', value: props.averagePrice || 0, format: 'number' },
    { label: 'Текущая цена', value: props.lastPrice || 0, format: 'number' }
  ]
  
  if (props.priceGrowth) {
    result.push({
      label: 'Рост цены',
      value: props.priceGrowth.percent,
      format: 'percent',
      isPositive: props.priceGrowth.isPositive,
      showValueChange: true
    })
  }
  
  return result
})
</script>

<template>
  <MetricsWidget title="Основная информация" :items="items" />
</template>
