<script setup>
import { computed } from 'vue'
import Widget from './Widget.vue'
import ValueChange from './ValueChange.vue'

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
  <Widget title="Лучшие активы">

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
          <ValueChange 
            :value="asset.profit_rub" 
            :is-positive="asset.profit_rub >= 0"
            format="currency"
            :show-arrow="false"
          />
        </div>
      </li>
    </ul>
  </Widget>
</template>

<style scoped>
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