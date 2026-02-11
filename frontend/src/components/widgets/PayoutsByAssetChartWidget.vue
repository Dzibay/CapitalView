<script setup>
import { computed } from 'vue'
import BarChart from '../charts/BarChart.vue'

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

const formatMoney = (value) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  }).format(value || 0)
}

const chartLabels = computed(() => {
  const topAssets = props.payoutsByAsset?.slice(0, 10) || []
  return topAssets.map(a => a.asset_ticker || a.asset_name || 'Unknown')
})

const chartDatasets = computed(() => {
  const topAssets = props.payoutsByAsset?.slice(0, 10) || []
  return [
    {
      label: 'Дивиденды',
      data: topAssets.map(a => a.total_dividends || 0),
      backgroundColor: payoutColors.dividendsAlpha,
      borderColor: payoutColors.dividends,
      borderWidth: 2,
      hoverBackgroundColor: payoutColors.dividendsHover,
      hoverBorderColor: payoutColors.dividendsDark,
      borderRadius: 8
    },
    {
      label: 'Купоны',
      data: topAssets.map(a => a.total_coupons || 0),
      backgroundColor: payoutColors.couponsAlpha,
      borderColor: payoutColors.coupons,
      borderWidth: 2,
      hoverBackgroundColor: payoutColors.couponsHover,
      hoverBorderColor: payoutColors.couponsDark,
      borderRadius: 8
    }
  ]
})
</script>

<template>
  <div class="widget">
    <div class="widget-title">
      <div class="widget-title-icon-rect"></div>
      <h2>Выплаты по активам</h2>
    </div>
    <div class="chart-container">
      <BarChart
        v-if="payoutsByAsset && payoutsByAsset.length > 0"
        :labels="chartLabels"
        :datasets="chartDatasets"
        :stacked="true"
        :format-value="formatMoney"
        height="300px"
      />
      <div v-else class="empty-state">
        <p>Нет данных о выплатах по активам</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.widget {
  background-color: #fff;
  padding: var(--spacing);
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

.widget-title {
  display: flex;
  gap: 5px;
  align-items: center;
}

.widget-title-icon-rect {
  padding: 5px;
  width: 25px;
  height: 25px;
  border-radius: 6px;
  background-color: #F6F6F6;
}

.widget-title h2 {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.chart-container {
  height: 300px;
  position: relative;
}

.empty-state {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #6b7280;
  font-size: 14px;
  background: white;
  z-index: 10;
}

.empty-state p {
  margin: 0;
}
</style>

