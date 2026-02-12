<script setup>
import MetricsWidget from './MetricsWidget.vue'
import { computed } from 'vue'

const props = defineProps({
  portfolioValue: {
    type: Number,
    default: 0
  },
  assetValue: {
    type: Number,
    default: 0
  },
  percentageInPortfolio: {
    type: Number,
    default: 0
  },
  percentageInRoot: {
    type: Number,
    default: null
  }
})

const items = computed(() => {
  const result = [
    { label: 'Общая стоимость портфеля', value: props.portfolioValue || 0, format: 'currency' },
    { label: 'Стоимость актива', value: props.assetValue || 0, format: 'currency' },
    { label: 'Доля в портфеле', value: props.percentageInPortfolio || 0, format: 'number' }
  ]
  
  if (props.percentageInRoot !== null && props.percentageInRoot !== undefined) {
    result.push({
      label: 'Доля в портфеле "Все активы"',
      value: props.percentageInRoot,
      format: 'number'
    })
  }
  
  return result
})
</script>

<template>
  <MetricsWidget title="Вклад в портфель" :items="items" />
</template>
