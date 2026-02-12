<script setup>
import { computed } from 'vue'
import Widget from './Widget.vue'
import { formatCurrency } from '../../utils/formatCurrency'

const props = defineProps({
  payouts: {
    type: Object,
    default: null
  }
})

const hasPayouts = computed(() => {
  return props.payouts && (props.payouts.total > 0 || props.payouts.dividends > 0 || props.payouts.coupons > 0)
})
</script>

<template>
  <Widget title="Выплаты">
    <div v-if="hasPayouts" class="payouts-summary">
      <div class="summary-item primary">
        <div class="summary-label">Всего выплат</div>
        <div class="summary-value">{{ formatCurrency(payouts.total || 0) }}</div>
      </div>

      <div class="summary-row">
        <div class="summary-item">
          <div class="summary-label">Дивиденды</div>
          <div class="summary-value">{{ formatCurrency(payouts.dividends || 0) }}</div>
        </div>

        <div class="summary-item">
          <div class="summary-label">Купоны</div>
          <div class="summary-value">{{ formatCurrency(payouts.coupons || 0) }}</div>
        </div>
      </div>

      <div v-if="payouts.history && payouts.history.length > 0" class="payouts-count">
        Всего операций: {{ payouts.history.length }}
      </div>
    </div>

    <div v-else class="empty-state">
      <p>Нет данных о выплатах</p>
    </div>
  </Widget>
</template>

<style scoped>
.payouts-summary {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.summary-item {
  padding: 1rem;
  background: transparent;
  border-radius: 0;
  border-bottom: 1px solid #f3f4f6;
}

.summary-item.primary {
  background: transparent;
  border-bottom: 2px solid #e5e7eb;
}

.summary-item.primary .summary-label {
  color: #111827;
  font-weight: 600;
}

.summary-item.primary .summary-value {
  color: #111827;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.summary-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6b7280;
  margin-bottom: 0.5rem;
}

.summary-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: #111827;
}

.payouts-count {
  font-size: 0.75rem;
  color: #9ca3af;
  text-align: center;
  padding-top: 0.5rem;
  border-top: 1px solid #e5e7eb;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  color: #6b7280;
  font-size: 0.875rem;
}
</style>
