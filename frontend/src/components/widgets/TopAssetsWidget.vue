<script setup>
defineProps({
  assets: { type: Array, required: true },
});
</script>

<template>
  <div class="widget">
    <h3 class="widget-title">Лучшие активы</h3>
    <ul class="assets-list">
      <li v-for="asset in assets" :key="asset.id" class="asset-item">
        <div class="asset-info">
          <span class="asset-name">{{ asset.name }}</span>
          <span class="asset-ticker">{{ asset.ticker }}</span>
        </div>
        <div class="asset-value">
          <span class="value">{{ asset.value.toLocaleString('ru-RU') }} RUB</span>
          <span class="change" :class="asset.changePercentage >= 0 ? 'positive' : 'negative'">
            {{ asset.changePercentage >= 0 ? '+' : '' }}{{ asset.changePercentage }}%
          </span>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.widget { background-color: #fff; border-radius: 12px; padding: 1.5rem; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
.widget-title { font-size: 1rem; color: #6b7280; margin: 0 0 1rem; }
.assets-list { list-style: none; padding: 0; margin: 0; }
.asset-item { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 0; }
.asset-item:not(:last-child) { border-bottom: 1px solid #e5e7eb; }
.asset-name { display: block; font-weight: 500; color: #1f2937; }
.asset-ticker { font-size: 0.875rem; color: #6b7280; }
.asset-value { text-align: right; }
.value { display: block; font-weight: 600; }
.change { font-size: 0.875rem; }
.change.positive { color: #10b981; }
.change.negative { color: #ef4444; }
</style>