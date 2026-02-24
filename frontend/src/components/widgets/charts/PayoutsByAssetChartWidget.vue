<script setup>
import { computed } from 'vue'
import BarChart from '../../charts/BarChart.vue'
import Widget from '../base/Widget.vue'
import EmptyState from '../base/EmptyState.vue'
import { formatMoney } from '../../../utils/formatCurrency.js'
import { HandCoins } from 'lucide-vue-next'

// Фирменные цвета для типов выплат
const payoutColors = {
  // Дивиденды - синий
  dividends: '#2563eb',
  dividendsAlpha: 'rgba(37, 99, 235, 0.85)',
  dividendsHover: '#1d4ed8',
  dividendsDark: '#1e40af',
  
  // Купоны - голубой/cyan
  coupons: '#06b6d4',
  couponsAlpha: 'rgba(6, 182, 212, 0.85)',
  couponsHover: '#0891b2',
  couponsDark: '#0e7490',
  
  // Амортизации - оранжевый
  amortizations: '#fb923c',
  amortizationsAlpha: 'rgba(251, 146, 60, 0.85)',
  amortizationsHover: '#f97316',
  amortizationsDark: '#ea580c'
}

const props = defineProps({
  payoutsByAsset: {
    type: Array,
    default: () => []
  }
})

const chartLabels = computed(() => {
  const topAssets = (props.payoutsByAsset || []).slice(0, 10)
  return topAssets.map(a => a.asset_ticker || a.asset_name || 'Unknown')
})

const chartDatasets = computed(() => {
  const topAssets = (props.payoutsByAsset || []).slice(0, 10)
  return [
    {
      label: 'Дивиденды',
      data: topAssets.map(a => a.total_dividends || 0),
      backgroundColor: payoutColors.dividendsAlpha,
      borderColor: 'transparent',
      borderWidth: 0,
      hoverBackgroundColor: payoutColors.dividendsHover,
      hoverBorderColor: 'transparent',
      categoryPercentage: 0.8,
      barPercentage: 0.95
    },
    {
      label: 'Купоны',
      data: topAssets.map(a => a.total_coupons || 0),
      backgroundColor: payoutColors.couponsAlpha,
      borderColor: 'transparent',
      borderWidth: 0,
      hoverBackgroundColor: payoutColors.couponsHover,
      hoverBorderColor: 'transparent',
      categoryPercentage: 0.8,
      barPercentage: 0.95
    }
  ]
})
</script>

<template>
  <Widget title="Выплаты по активам", :icon="HandCoins">
    <div class="chart-container">
      <BarChart
        v-if="payoutsByAsset && payoutsByAsset.length > 0"
        :labels="chartLabels"
        :datasets="chartDatasets"
        :stacked="true"
        :format-value="formatMoney"
        :x-axis-rotation="45"
        height="300px"
      />
      <EmptyState v-else message="Нет данных о выплатах по активам" />
    </div>
  </Widget>
</template>

<style scoped>
.chart-container {
  height: 300px;
  position: relative;
}
</style>

