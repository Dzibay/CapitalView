<script setup>
import { computed } from 'vue';
import Tooltip from '../Tooltip.vue';
import Widget from './Widget.vue';
import ValueChange from './ValueChange.vue';

const props = defineProps({
  totalAmount: { type: Number, required: true },
  totalProfit: { type: Number, required: true },
  monthlyChange: { type: Number, required: true },
  investedAmount: { type: Number, required: true },
  analytics: { type: Object, default: () => ({}) },
});

const isPositiveChange = computed(() => {
  return props.totalProfit >= 0
});

// Рост прибыли за месяц в процентах
// monthlyChange = current_pnl - month_ago_pnl
// month_ago_pnl = current_pnl - monthlyChange
// Процент роста = (monthlyChange / month_ago_pnl) * 100
const monthlyGrowthPercent = computed(() => {
  if (!props.monthlyChange || props.monthlyChange === 0) return 0
  const monthAgoPnl = props.totalProfit - props.monthlyChange
  if (!monthAgoPnl || monthAgoPnl === 0) return 0
  return (props.monthlyChange / Math.abs(monthAgoPnl)) * 100
});

const formattedMonthlyGrowthPercent = computed(() => {
  const percent = monthlyGrowthPercent.value
  const formatted = new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(percent);
  return `${formatted}%`;
});

// Отношение прибыли к инвестициям
const profitToInvestedPercent = computed(() => {
  if (!props.investedAmount || props.investedAmount === 0) return 0
  return (props.totalProfit / props.investedAmount) * 100
});

const formattedProfitToInvestedPercent = computed(() => {
  const percent = profitToInvestedPercent.value
  const formatted = new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(percent);
  return `${formatted}%`;
});

// Форматирование для tooltip разбивки прибыли
const formatCurrency = (value) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  }).format(value || 0);
};

const profitBreakdown = computed(() => {
  const analytics = props.analytics || {}
  const realized = analytics.realized_pl || 0
  const unrealized = analytics.unrealized_pl || 0
  const dividends = analytics.dividends || 0
  const coupons = analytics.coupons || 0
  const commissions = analytics.commissions || 0
  const taxes = analytics.taxes || 0
  
  return {
    realized,
    unrealized,
    dividends,
    coupons,
    commissions,
    taxes,
    total: props.totalProfit
  }
});

const profitBreakdownTooltip = computed(() => {
  const b = profitBreakdown.value
  const parts = []
  
  if (b.realized !== 0) parts.push(`Реализованная прибыль: ${formatCurrency(b.realized)}`)
  if (b.unrealized !== 0) parts.push(`Нереализованная прибыль: ${formatCurrency(b.unrealized)}`)
  if (b.dividends !== 0) parts.push(`Дивиденды: ${formatCurrency(b.dividends)}`)
  if (b.coupons !== 0) parts.push(`Купоны: ${formatCurrency(b.coupons)}`)
  if (b.commissions !== 0) parts.push(`Комиссии: ${formatCurrency(Math.abs(b.commissions))} (уменьшают прибыль)`)
  if (b.taxes !== 0) parts.push(`Налоги: ${formatCurrency(Math.abs(b.taxes))} (уменьшают прибыль)`)
  
  if (parts.length === 0) return 'Прибыль: 0 ₽'
  
  return `Состав прибыли:\n${parts.join('\n')}\n\nИтого: ${formatCurrency(b.total)}`
});

</script>

<template>
  <Widget title="Прибыль">

    <div class="capital-value-with-change">
      <Tooltip :content="profitBreakdownTooltip" position="top">
        <div class="capital-values">
          {{ props.totalProfit.toFixed(2) }} ₽
        </div>
      </Tooltip>
      <Tooltip :content="`Изменение прибыли за последний месяц составляет ${formattedMonthlyGrowthPercent}`" position="top">
        <ValueChange 
          :value="monthlyGrowthPercent" 
          format="percent"
        />
      </Tooltip>
    </div>
    <p>
      <span 
        class="profit-percent" 
        :class="{ 'positive': profitToInvestedPercent >= 0, 'negative': profitToInvestedPercent < 0 }"
      >
        {{ formattedProfitToInvestedPercent }}
      </span>
      <span> от инвестиций</span>
    </p>
  </Widget>
</template>

<style scoped>
.capital-value-with-change {
  margin: 15px 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.profit-percent.positive {
  color: var(--positiveColor);
}
.profit-percent.negative {
  color: var(--negativeColor);
}
</style>