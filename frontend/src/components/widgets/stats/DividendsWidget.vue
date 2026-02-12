<script setup>
import { computed } from 'vue'
import StatCardWidget from '../base/StatCardWidget.vue'

const props = defineProps({
  annualDividends: {
    type: Number,
    default: 0
  }
})

// Средняя выплата в месяц = годовые дивиденды / 12
const monthlyAverage = computed(() => {
  return (props.annualDividends || 0) / 12
})
</script>

<template>
  <StatCardWidget
    title="Дивиденды"
    :main-value="annualDividends"
    main-value-format="currency"
    main-value-tooltip="Среднегодовые дивиденды всех активов в портфеле"
    main-value-suffix=" в год"
    :secondary-value="monthlyAverage"
    secondary-format="currency"
    secondary-text-suffix=" в месяц"
  />
</template>
