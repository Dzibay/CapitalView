<script setup>
defineProps({
  transactions: { type: Array, required: true },
});
</script>

<template>
  <div class="widget">

    <div class="widget-title">
      <div class="widget-title-icon-rect">

      </div>
      <h2>Последние операции</h2>
    </div>
    <ul class="transactions-list">
      <li v-for="tx in transactions.slice(0, 4)" :key="tx.id" class="transaction-item">
        <div class="tx-info">
          <span class="tx-type">{{ tx.transaction_type }}</span>
          <span class="tx-asset">{{ tx.asset_name }} · {{ tx.quantity }} шт.</span>
        </div>
        <div class="tx-info-right">
          <span>{{ tx.transaction_date }}</span>
          <span class="tx-amount" :class="tx.transaction_type == 'Покупка' ? 'buy' : 'sell'">
            {{ tx.transaction_type === 'Покупка' ? '-' : '+' }} {{ (tx.quantity * tx.price).toFixed(2) }} RUB
          </span>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.widget {
    grid-row: span 2;
    grid-column: span 1;
    background-color: #fff; 
    border-radius: 12px; 
    padding: 1.5rem; 
    box-shadow: 0 4px 10px rgba(0,0,0,0.05);
}
.transactions-list { 
    list-style: none; 
    padding: 0; 
    margin: 0; 
}
.transaction-item { 
    display: flex; 
    align-items: center; 
    padding: 0.75rem 0; 
}
.transaction-item:not(:last-child) { 
    border-bottom: 1px solid #e5e7eb;
}
.tx-icon { 
    width: 40px; 
    height: 40px; 
    border-radius: 50%; 
    display: flex; 
    align-items: center; 
    justify-content: center; 
    margin-right: 1rem; 
}
.tx-icon.buy { 
    background-color: #dcfce7; 
    color: #16a34a; 
}
.tx-icon.sell { 
    background-color: #fee2e2; 
    color: #ef4444; 
}
.tx-icon svg { width: 24px; 
    height: 24px; 
    fill: currentColor; 
}
.tx-info { 
    flex-grow: 1; 
}
.tx-info-right {
  text-align: right;
}
.tx-type { 
    display: block; 
    font-weight: 500;
    color: #1f2937; 
}
.tx-asset { 
    font-size: 0.875rem; 
    color: #6b7280; 
}
.tx-amount {
  display: block;
    font-size: 0.875rem;
    font-weight: 400; 
}
.tx-amount.buy { 
  color: #ef4444; 
}
.tx-amount.sell { 
  color: #16a34a; 
}
</style>