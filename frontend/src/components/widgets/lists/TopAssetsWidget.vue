<script setup>
import { computed } from 'vue'
import Widget from '../base/Widget.vue'
import ValueChangePill from '../base/ValueChangePill.vue'
import { effectiveUnitPriceInCurrency } from '../../../utils/effectiveAssetPrice'

const props = defineProps({
  assets: { type: Array, required: true },
});

// Берём 4 лучших по прибыли
const topAssets = computed(() =>
  [...props.assets]
    .sort((a, b) => b.profit_rub - a.profit_rub)
    .slice(0, 4)
);

function positionValueRub(asset) {
  const q = Number(asset.quantity) || 0
  const rate = Number(asset.currency_rate_to_rub) || 1
  return effectiveUnitPriceInCurrency(asset) * q * rate
}
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
            {{ positionValueRub(asset).toFixed(2) }} ₽
          </span>
          <ValueChangePill 
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
  font-weight: var(--text-label-weight);
  color: var(--text-primary);
}
.asset-ticker {
  font-size: var(--text-caption-size);
  color: var(--text-tertiary);
}
.asset-value {
  text-align: right;
}
.value {
  display: block;
  font-weight: var(--text-body-secondary-weight);
}
</style>