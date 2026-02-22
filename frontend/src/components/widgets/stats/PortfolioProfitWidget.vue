<script setup>
import { computed } from 'vue'
import StatCardWidget from '../base/StatCardWidget.vue'

const props = defineProps({
  totalAmount: { type: Number, required: true },
  totalProfit: { type: Number, required: true },
  monthlyChange: { type: Number, required: true },
  investedAmount: { type: Number, required: true },
  analytics: { type: Object, default: () => ({}) },
})

// Рост прибыли за месяц в процентах
const monthlyGrowthPercent = computed(() => {
  if (!props.monthlyChange || props.monthlyChange === 0) return 0
  const monthAgoPnl = props.totalProfit - props.monthlyChange
  if (!monthAgoPnl || monthAgoPnl === 0) return 0
  return (props.monthlyChange / Math.abs(monthAgoPnl)) * 100
})

const formattedMonthlyGrowthPercent = computed(() => {
  const percent = monthlyGrowthPercent.value
  return new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(percent) + '%'
})

// Отношение прибыли к инвестициям
const profitToInvestedPercent = computed(() => {
  if (!props.investedAmount || props.investedAmount === 0) return 0
  return (props.totalProfit / props.investedAmount) * 100
})

// Форматирование для tooltip разбивки прибыли
const formatCurrency = (value) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  }).format(value || 0)
}

const profitBreakdown = computed(() => {
  const analytics = props.analytics || {}
  const totals = analytics.totals || {}
  // Поддерживаем оба формата: новый (totals) и старый (прямые поля)
  const realized = totals.realized_pl ?? analytics.realized_pl ?? 0
  const unrealized = totals.unrealized_pl ?? analytics.unrealized_pl ?? 0
  const dividends = totals.dividends ?? analytics.dividends ?? 0
  const coupons = totals.coupons ?? analytics.coupons ?? 0
  // Комиссии - это расходы, берем абсолютное значение (на случай если они отрицательные)
  const commissions = Math.abs(totals.commissions ?? analytics.commissions ?? 0)
  // Налоги - это расходы, берем абсолютное значение (на случай если они отрицательные)
  const taxes = Math.abs(totals.taxes ?? analytics.taxes ?? 0)
  
  return {
    realized,
    unrealized,
    dividends,
    coupons,
    commissions,
    taxes,
    total: props.totalProfit
  }
})

const profitBreakdownTooltip = computed(() => {
  const b = profitBreakdown.value
  const parts = []
  
  if (b.realized !== 0) parts.push(`Реализованная прибыль: ${formatCurrency(b.realized)}`)
  if (b.unrealized !== 0) parts.push(`Нереализованная прибыль: ${formatCurrency(b.unrealized)}`)
  if (b.dividends !== 0) parts.push(`Дивиденды: ${formatCurrency(b.dividends)}`)
  if (b.coupons !== 0) parts.push(`Купоны: ${formatCurrency(b.coupons)}`)
  // Комиссии показываем как отрицательные (расходы уменьшают прибыль)
  if (b.commissions !== 0) {
    const commissionsAbs = Math.abs(b.commissions)
    parts.push(`Комиссии: ${formatCurrency(-commissionsAbs)} (уменьшают прибыль)`)
  }
  // Налоги показываем как отрицательные (расходы уменьшают прибыль)
  if (b.taxes !== 0) {
    const taxesAbs = Math.abs(b.taxes)
    parts.push(`Налоги: ${formatCurrency(-taxesAbs)} (уменьшают прибыль)`)
  }
  
  if (parts.length === 0) return 'Прибыль: 0 ₽'
  
  return `Состав прибыли:\n${parts.join('\n')}\n\nИтого: ${formatCurrency(b.total)}`
})
</script>

<template>
  <StatCardWidget
    title="Прибыль"
    :main-value="`${totalProfit.toFixed(2)} ₽`"
    main-value-format="custom"
    :main-value-tooltip="profitBreakdownTooltip"
    :change-value="monthlyGrowthPercent"
    :change-tooltip="`Изменение прибыли за последний месяц составляет ${formattedMonthlyGrowthPercent}`"
    :secondary-value="profitToInvestedPercent"
    secondary-format="percent"
    :secondary-class="profitToInvestedPercent >= 0 ? 'positive' : 'negative'"
    secondary-text=" от инвестиций"
  />
</template>