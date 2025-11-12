<script setup>
import { computed } from 'vue'
import { getCurrencySymbol } from '../../utils/currencySymbols.js'

const props = defineProps({
  assets: { type: Array, required: true },
  direction: { type: String, default: 'up' }, // 'up' или 'down'
  title: { type: String, required: true }
})

// 🔹 Считаем изменение в % и в валюте, сортируем и берём топ-4
const topAssets = computed(() => {
  if (!props.assets?.length) return []

  const processed = props.assets
    .filter(a => a.last_price && a.daily_change !== undefined && a.quantity > 0)
    .map(a => {
      const total_value = a.last_price * a.quantity
      const change_percent = (a.daily_change / a.last_price) * 100
      const change_value = a.daily_change * a.quantity
      return { ...a, total_value, change_percent, change_value }
    })

  const sorted =
    props.direction === 'up'
      ? processed.sort((a, b) => b.change_percent - a.change_percent)
      : processed.sort((a, b) => a.change_percent - b.change_percent)

  return sorted.slice(0, 4)
})
</script>

<template>
  <div class="widget">
    <div class="widget-title">
      <div class="widget-title-icon-rect"></div>
      <h2 class="widget-title">{{ title }}</h2>
    </div>

    <ul class="assets-list">
      <li v-for="asset in topAssets" :key="asset.asset_id" class="asset-item">
        <div class="asset-info">
          <span class="asset-name">{{ asset.name }}</span>
          <span class="asset-ticker">{{ asset.ticker }}</span>
        </div>

        <div class="asset-value">
          <span class="value">
            {{ asset.total_value.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
            {{ getCurrencySymbol(asset.currency_ticker) }}
          </span>
          <span
            class="value-change"
            :class="asset.change_percent >= 0 ? 'positive' : 'negative'"
          >
            {{ asset.change_percent >= 0 ? '+' : '' }}
            {{ asset.change_percent.toFixed(2) }}%
            ({{ asset.change_value >= 0 ? '+' : '' }}
            {{ asset.change_value.toFixed(2) }}
            {{ getCurrencySymbol(asset.currency_ticker) }})
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
