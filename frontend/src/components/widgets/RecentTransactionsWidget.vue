<script setup>
defineProps({
  transactions: { type: Array, required: true },
});
</script>

<template>
  <div class="widget">
    <h3 class="widget-title">Последние операции</h3>
    <ul class="transactions-list">
      <li v-for="tx in transactions" :key="tx.id" class="transaction-item">
        <div class="tx-icon" :class="tx.type">
          <svg v-if="tx.type === 'buy'" viewBox="0 0 24 24"><path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"></path></svg>
          <svg v-else viewBox="0 0 24 24"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"></path></svg>
        </div>
        <div class="tx-info">
          <span class="tx-asset">{{ tx.asset }}</span>
          <span class="tx-date">{{ tx.date }}</span>
        </div>
        <div class="tx-amount" :class="tx.type">
          {{ tx.type === 'buy' ? '+' : '-' }} {{ tx.amount.toLocaleString('ru-RU') }} RUB
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.widget { background-color: #fff; border-radius: 12px; padding: 1.5rem; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
.widget-title { font-size: 1rem; color: #6b7280; margin: 0 0 1rem; }
.transactions-list { list-style: none; padding: 0; margin: 0; }
.transaction-item { display: flex; align-items: center; padding: 0.75rem 0; }
.transaction-item:not(:last-child) { border-bottom: 1px solid #e5e7eb; }
.tx-icon { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 1rem; }
.tx-icon.buy { background-color: #dcfce7; color: #16a34a; }
.tx-icon.sell { background-color: #fee2e2; color: #ef4444; }
.tx-icon svg { width: 24px; height: 24px; fill: currentColor; }
.tx-info { flex-grow: 1; }
.tx-asset { display: block; font-weight: 500; color: #1f2937; }
.tx-date { font-size: 0.875rem; color: #6b7280; }
.tx-amount { font-weight: 600; }
.tx-amount.buy { color: #16a34a; }
.tx-amount.sell { color: #ef4444; }
</style>