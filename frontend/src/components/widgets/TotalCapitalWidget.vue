<script setup>
import { computed } from 'vue'
import StatCardWidget from './StatCardWidget.vue'

const props = defineProps({
  totalAmount: { type: Number, required: true },
  investedAmount: { type: Number, required: true },
})

const profitPercent = computed(() => {
  if (!props.investedAmount || props.investedAmount === 0) return 0
  return ((props.totalAmount - props.investedAmount) / props.investedAmount * 100)
})

const profitAmount = computed(() => {
  return props.totalAmount - props.investedAmount
})

const formattedProfitAmount = computed(() => {
  return new Intl.NumberFormat('ru-RU', { 
    style: 'currency', 
    currency: 'RUB',
    maximumFractionDigits: 0
  }).format(profitAmount.value)
})

const tooltipText = computed(() => {
  return `Разница между текущей стоимостью активов и суммой инвестиций составляет ${Math.abs(profitPercent.value).toFixed(2)}% (${formattedProfitAmount.value})`
})
</script>

<template>
  <StatCardWidget
    title="Общий капитал"
    :main-value="totalAmount"
    main-value-format="currency"
    :change-value="profitPercent"
    :change-is-positive="profitPercent >= 0"
    :change-tooltip="tooltipText"
    secondary-text="Инвестировано: "
    :secondary-value="investedAmount"
    secondary-format="currency"
  />
</template>