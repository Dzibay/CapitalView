<script setup>
import { computed } from 'vue'

const props = defineProps({
  assets: { type: Array, required: true },
});

// Берём 4 лучших по прибыли
const topAssets = computed(() =>
  [...props.assets]
    .sort((a, b) => b.profit_rub - a.profit_rub)
    .slice(0, 4)
);
</script>

<template>
  <div class="widget">
    <div class="widget-title">
      <div class="widget-title-icon-rect"></div>
      <h2 class="widget-title">Лучшие активы</h2>
    </div>

    <ul class="assets-list">
      <li v-for="asset in topAssets" :key="asset.asset_id" class="asset-item">
        <div class="asset-info">
          <span class="asset-name">{{ asset.name }}</span>
          <span class="asset-ticker">{{ asset.ticker }}</span>
        </div>

        <div class="asset-value">
          <span class="value">
            {{ (asset.last_price * asset.quantity).toFixed(2) }} ₽
          </span>
          <span
            class="value-change"
            :class="asset.profit_rub >= 0 ? 'positive' : 'negative'"
          >
            {{ asset.profit_rub >= 0 ? '+' : '' }}{{ asset.profit_rub.toFixed(2) }} ₽
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
.assets-list { 
  list-style: none;
}
.asset-item { 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  padding: 0.75rem 0; 
}
.asset-item:not(:last-child) { 
  border-bottom: 1px solid #e5e7eb; 
}
.asset-name { 
  display: block; 
  font-weight: 500; 
  color: #1f2937; 
}
.asset-ticker { 
  font-size: 0.875rem; 
  color: #6b7280; 
}
.asset-value { 
  text-align: right; 
}
.value { 
  display: block; 
  font-weight: 400; 
}
</style>