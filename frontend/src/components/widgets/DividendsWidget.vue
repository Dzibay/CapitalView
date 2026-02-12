<script setup>
import { computed } from 'vue'
import Tooltip from '../Tooltip.vue'
import Widget from './Widget.vue'

const props = defineProps({
  annualDividends: {
    type: Number,
    default: 0
  }
})

const formattedAnnualDividends = computed(() => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  }).format(props.annualDividends || 0)
})

// Средняя выплата в месяц = годовые дивиденды / 12
const monthlyAverage = computed(() => {
  return (props.annualDividends || 0) / 12
})

const formattedMonthlyAverage = computed(() => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  }).format(monthlyAverage.value)
})
</script>

<template>
  <Widget title="Дивиденды">

    <div class="capital-value-with-change">
      <Tooltip content="Среднегодовые дивиденды всех активов в портфеле" position="top">
        <div class="capital-values">
          {{ formattedAnnualDividends }}
        </div>
      </Tooltip>
      <p> в год</p>
    </div>

    <p>{{ formattedMonthlyAverage }} в месяц</p>
  </Widget>
</template>

<style scoped>

.capital-value-with-change {
  margin: 15px 0;
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
}

.capital-value-with-change p {
  margin: 0;
  font-size: 1rem;
  color: #6b7280;
  line-height: 1;
  padding-bottom: 0.2rem;
}
</style>
