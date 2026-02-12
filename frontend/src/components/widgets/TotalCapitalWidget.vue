<script setup>
import { computed } from 'vue';
import Tooltip from '../Tooltip.vue';
import Widget from './Widget.vue';

const props = defineProps({
  totalAmount: { type: Number, required: true },
  investedAmount: { type: Number, required: true },
});

const formattedTotalAmount = computed(() => {
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB' }).format(props.totalAmount);
});
const formattedInvestedAmount = computed(() => {
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB' }).format(props.investedAmount);
});
const profitPercent = computed(() => {
  if (!props.investedAmount || props.investedAmount === 0) return 0
  return ((props.totalAmount - props.investedAmount) / props.investedAmount * 100)
});

const formattedProfit = computed(() => {
  return Math.abs(profitPercent.value).toFixed(2)
});

const isPositiveChange = computed(() => {
  return profitPercent.value >= 0
});

// Разница в рублях
const profitAmount = computed(() => {
  return props.totalAmount - props.investedAmount
});

const formattedProfitAmount = computed(() => {
  return new Intl.NumberFormat('ru-RU', { 
    style: 'currency', 
    currency: 'RUB',
    maximumFractionDigits: 0
  }).format(profitAmount.value);
});

// Текст подсказки с разницей в рублях
const tooltipText = computed(() => {
  return `Разница между текущей стоимостью активов и суммой инвестиций составляет ${formattedProfit.value}% (${formattedProfitAmount.value})`
});

</script>

<template>
  <Widget title="Общий капитал">

    <div class="capital-value-with-change">
      <div class="capital-values">{{ formattedTotalAmount }}</div>
      
      <Tooltip :content="tooltipText" position="top">
        <div 
          class="value-change" 
          :class="{ 'positive': isPositiveChange, 'negative': !isPositiveChange }"
        >
          <span class="arrow-icon" :class="{ 'up': isPositiveChange, 'down': !isPositiveChange }">
            <svg v-if="isPositiveChange" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="18 15 12 9 6 15"></polyline>
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </span>
          <span>{{ formattedProfit }}%</span>
        </div>
      </Tooltip>
    </div>

    <p>Инвестировано: {{ formattedInvestedAmount }}</p>
  </Widget>
</template>

<style scoped>

.capital-value-with-change {
  margin: 15px 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.value-change {
  display: flex;
  align-items: center;
  gap: 0.25rem;
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