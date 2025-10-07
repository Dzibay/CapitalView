<script setup>
import { computed } from 'vue';

const props = defineProps({
  totalAmount: { type: Number, required: true },
  monthlyChange: { type: Object, required: true },
});

const formattedAmount = computed(() => {
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB' }).format(props.totalAmount);
});

const isPositiveChange = computed(() => props.monthlyChange.absolute >= 0);
</script>

<template>
  <div class="widget">
    <h3 class="widget-title">Общий капитал</h3>
    <div class="total-amount">{{ formattedAmount }}</div>
    <div class="monthly-change" :class="{ 'positive': isPositiveChange, 'negative': !isPositiveChange }">
      <svg v-if="isPositiveChange" viewBox="0 0 24 24"><path d="M7 14l5-5 5 5z"></path></svg>
      <svg v-else viewBox="0 0 24 24"><path d="M7 10l5 5 5-5z"></path></svg>
      <span>{{ monthlyChange.percentage }}%</span>
      <span>({{ monthlyChange.absolute.toFixed(2) }} RUB) за месяц</span>
    </div>
  </div>
</template>

<style scoped>
.widget {
  background-color: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
}
.widget-title {
  font-size: 1rem;
  color: #6b7280;
  margin: 0 0 0.5rem;
}
.total-amount {
  font-size: 2.25rem;
  font-weight: 700;
  color: #111827;
}
.monthly-change {
  display: flex;
  align-items: center;
  font-size: 0.875rem;
  margin-top: 0.5rem;
}
.monthly-change.positive { color: #10b981; }
.monthly-change.negative { color: #ef4444; }
.monthly-change svg {
  width: 20px;
  height: 20px;
  fill: currentColor;
}
.monthly-change span {
  margin-left: 0.25rem;
}
</style>