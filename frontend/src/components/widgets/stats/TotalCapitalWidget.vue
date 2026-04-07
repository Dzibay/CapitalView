<script setup>
import { computed } from 'vue'
import { Wallet } from 'lucide-vue-next'
import StatCardWidget from '../base/StatCardWidget.vue'
import { formatCurrency } from '../../../utils/formatCurrency'

const props = defineProps({
  totalAmount: { type: Number, required: true },
  /** Сумма в позициях + остаток на счёте портфеля (total_invested + balance) */
  investedAmount: { type: Number, required: true },
  /** Нереализованная прибыль в валюте; если null — totalAmount − investedAmount */
  unrealizedPl: { type: Number, default: null },
  /** Доля нереализованной прибыли от вложений в активы, %; если null — считается из сумм */
  unrealizedPercent: { type: Number, default: null },
  scrollReveal: { type: Boolean, default: false },
  landingRevealRef: { type: [Object, Boolean], default: null },
})

const effectiveUnrealizedPl = computed(() => {
  if (props.unrealizedPl != null && Number.isFinite(Number(props.unrealizedPl))) {
    return Number(props.unrealizedPl)
  }
  return props.totalAmount - props.investedAmount
})

const effectiveUnrealizedPercent = computed(() => {
  if (props.unrealizedPercent != null && Number.isFinite(Number(props.unrealizedPercent))) {
    return Number(props.unrealizedPercent)
  }
  if (!props.investedAmount) return 0
  return (effectiveUnrealizedPl.value / props.investedAmount) * 100
})

const formattedUnrealized = computed(() =>
  formatCurrency(effectiveUnrealizedPl.value, { maximumFractionDigits: 0 })
)

const tooltipText = computed(() => {
  const pct = Math.abs(effectiveUnrealizedPercent.value).toFixed(2)
  return `Нереализованная прибыль от оценки портфеля: ${pct}% (${formattedUnrealized.value}) относительно стоимости позиции и остатка на счёте`
})

const investedTooltipText =
  'Стоимость текущих открытых позиций + остаток на счёте портфеля'
</script>

<template>
  <StatCardWidget
    title="Общий капитал"
    :icon="Wallet"
    :main-value="totalAmount"
    main-value-format="currency"
    :change-value="effectiveUnrealizedPercent"
    :change-is-positive="effectiveUnrealizedPl >= 0"
    :change-tooltip="tooltipText"
    secondary-text="Инвестировано: "
    :secondary-value="investedAmount"
    secondary-format="currency"
    :secondary-value-tooltip="investedTooltipText"
    :scroll-reveal="scrollReveal"
    :landing-reveal-ref="landingRevealRef"
  />
</template>
