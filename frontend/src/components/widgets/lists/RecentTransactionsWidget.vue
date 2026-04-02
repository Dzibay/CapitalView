<script setup>
import { History } from 'lucide-vue-next'
import Widget from '../base/Widget.vue'
import { formatDateTimeForDisplay } from '../../../utils/date'
import { getCurrencySymbol } from '../../../utils/currencySymbols'

const props = defineProps({
  transactions: { type: Array, required: true }
})

const txLineTotal = (tx) => {
  const q = Number(tx.quantity) || 0
  const p = Number(tx.price) || 0
  return q * p
}
</script>

<template>
  <Widget title="Последние операции" :icon="History">
    <ul class="transactions-list">
      <li v-for="tx in transactions.slice(0, 4)" :key="tx.transaction_id || tx.id" class="transaction-item">
        <div class="tx-info">
          <span class="tx-type">{{ tx.transaction_type }}</span>
          <span class="tx-asset">{{ tx.asset_name }} · {{ tx.quantity }} шт.</span>
        </div>
        <div class="tx-info-right">
          <span class="tx-date">{{ formatDateTimeForDisplay(tx.transaction_date) }}</span>
          <span class="tx-amount" :class="tx.transaction_type == 'Покупка' ? 'buy' : (tx.transaction_type === 'Погашение' ? 'redemption' : 'sell')">
            {{ tx.transaction_type === 'Покупка' ? '-' : '+' }}
            {{ txLineTotal(tx).toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) }}
            {{ getCurrencySymbol(tx.currency_ticker || 'RUB') }}
          </span>
        </div>
      </li>
    </ul>
  </Widget>
</template>

<style scoped>
.transactions-list {
  list-style: none;
  padding: 0;
  margin: 0;
  min-width: 0;
}

.transaction-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.75rem 0;
  min-width: 0;
}

.transaction-item:not(:last-child) {
  border-bottom: 1px solid #e5e7eb;
}

.tx-info {
  flex: 1;
  min-width: 0;
}

.tx-info-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.25rem;
  flex-shrink: 0;
}

.tx-date {
  font-size: var(--text-caption-size);
  color: var(--text-tertiary);
  white-space: nowrap;
}

.tx-type {
  display: block;
  font-weight: var(--text-label-weight);
  color: var(--text-primary);
}

.tx-asset {
  display: block;
  font-size: var(--text-caption-size);
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tx-amount {
  display: block;
  font-size: var(--text-caption-size);
  font-weight: var(--text-body-secondary-weight);
  white-space: nowrap;
}

.tx-amount.buy {
  color: #ef4444;
}

.tx-amount.sell {
  color: #16a34a;
}
</style>