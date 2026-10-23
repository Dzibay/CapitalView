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
  dividends: '#7381ff',
  dividendsAlpha: 'rgba(115, 129, 255, 0.85)',
  dividendsHover: '#8f9bff',
  dividendsDark: '#5060dc',
  
  // Купоны - голубой/cyan
  coupons: '#b0b8ff',
  couponsAlpha: 'rgba(176, 184, 255, 0.85)',
  couponsHover: '#c6cbff',
  couponsDark: '#8f9bff',
  
  // Амортизации - оранжевый
  amortizations: '#8e93a5',
  amortizationsAlpha: 'rgba(142, 147, 165, 0.85)',
  amortizationsHover: '#a4a8b8',
  amortizationsDark: '#6f7486'
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
  <Widget title="Выплаты по активам" :icon="HandCoins">
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

