<script setup>
import { computed } from 'vue'
import Widget from '../base/Widget.vue'
import { formatCurrency, formatOperationAmount } from '../../../utils/formatCurrency'
import EmptyState from '../base/EmptyState.vue'

const props = defineProps({
  payouts: {
    type: Array,
    default: () => []
  }
})

const sortedPayouts = computed(() => {
  return [...props.payouts].sort((a, b) => {
    const dateA = new Date(a.date || a.payment_date || 0)
    const dateB = new Date(b.date || b.payment_date || 0)
    return dateB - dateA
  })
})

const getPayoutTypeLabel = (type) => {
  if (typeof type === 'string') {
    const t = type.toLowerCase()
    if (t.includes('див') || t.includes('dividend')) return 'Дивиденды'
    if (t.includes('купон') || t.includes('coupon')) return 'Купоны'
    if (t.includes('аморт') || t.includes('amortization')) return 'Амортизация'
  }
  return 'Выплата'
}

const getPayoutTypeClass = (type) => {
  if (typeof type === 'string') {
    const t = type.toLowerCase()
    if (t.includes('див') || t.includes('dividend')) return 'dividend'
    if (t.includes('купон') || t.includes('coupon')) return 'coupon'
    if (t.includes('аморт') || t.includes('amortization')) return 'amortization'
  }
  return 'other'
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('ru-RU', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}
</script>

<template>
  <Widget title="История выплат">
    <div v-if="sortedPayouts.length > 0" class="payouts-list">
      <div 
        v-for="(payout, index) in sortedPayouts" 
        :key="index"
        class="payout-item"
      >
        <div class="payout-header">
          <span class="payout-type" :class="getPayoutTypeClass(payout.type)">
            {{ getPayoutTypeLabel(payout.type) }}
          </span>
          <span class="payout-amount">{{ formatOperationAmount(payout.value || 0) }}</span>
        </div>
        <div class="payout-date">{{ formatDate(payout.payment_date) }}</div>
        <div v-if="payout.record_date" class="payout-meta">
          Дата отсечки: {{ formatDate(payout.record_date) }}
        </div>
        <div v-if="payout.dividend_yield" class="payout-meta">
          Доходность: {{ payout.dividend_yield.toFixed(2) }}%
        </div>
      </div>
    </div>

    <EmptyState v-else message="Нет данных о выплатах" />
  </Widget>
</template>

<style scoped>
.payouts-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-height: 400px;
  overflow-y: auto;
}

.payout-item {
  padding: 1rem 0;
  background: transparent;
  border-bottom: 1px solid #f3f4f6;
  transition: all 0.2s;
}

.payout-item:hover {
  background: transparent;
  border-bottom-color: #e5e7eb;
}

.payout-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  gap: 1rem;
}

.payout-type {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.payout-type.dividend {
  background: transparent;
  color: #6b7280;
  border: 1px solid #e5e7eb;
}

.payout-type.coupon {
  background: transparent;
  color: #6b7280;
  border: 1px solid #e5e7eb;
}

.payout-type.other {
  background: transparent;
  color: #6b7280;
  border: 1px solid #e5e7eb;
}

.payout-amount {
  font-size: 1.125rem;
  font-weight: 700;
  color: #111827;
}

.payout-date {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 0.25rem;
}

.payout-meta {
  font-size: 0.75rem;
  color: #9ca3af;
}
</style>
