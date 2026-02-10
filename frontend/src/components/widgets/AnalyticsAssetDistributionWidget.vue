<script setup>
import { computed } from 'vue'
import DoughnutChart from '../charts/DoughnutChart.vue'

const props = defineProps({
  assetDistribution: {
    type: Array,
    default: () => []
  },
  layout: {
    type: String,
    default: 'horizontal', // 'vertical' or 'horizontal'
    validator: (value) => ['vertical', 'horizontal'].includes(value)
  }
})

const formatMoney = (value) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  }).format(value || 0)
}

// Общий массив цветов для графика и легенды
const colors = [
  '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6',
  '#10b981', '#f472b6', '#60a5fa', '#fbbf24', '#a78bfa',
  '#ec4899', '#14b8a6', '#f97316', '#6366f1'
]

const chartData = computed(() => {
  if (!props.assetDistribution?.length) {
    return { labels: [], values: [] }
  }
  
  const labels = props.assetDistribution.map(a => a.asset_name || a.asset_ticker || 'Unknown')
  const values = props.assetDistribution.map(a => a.total_value || 0)
  
  return { labels, values }
})

const total = computed(() => {
  return chartData.value.values.reduce((a, b) => a + b, 0)
})

// Разделяем активы на два столбца: сначала левый, потом правый
const leftColumnAssets = computed(() => {
  if (!props.assetDistribution?.length) return []
  const mid = Math.ceil(props.assetDistribution.length / 2)
  return props.assetDistribution.slice(0, mid)
})

const rightColumnAssets = computed(() => {
  if (!props.assetDistribution?.length) return []
  const mid = Math.ceil(props.assetDistribution.length / 2)
  return props.assetDistribution.slice(mid)
})
</script>

<template>
  <div class="widget">
    <div class="widget-header">
      <div class="widget-title">
        <h2>Все активы</h2>
        <button class="help-icon" title="Справка">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/>
            <path d="M8 11V8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <circle cx="8" cy="5" r="0.5" fill="currentColor"/>
          </svg>
        </button>
      </div>
      <button class="filter-button" title="Фильтр по вложениям">
        <span>По вложениям</span>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/>
          <path d="M8 11V8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <circle cx="8" cy="5" r="0.5" fill="currentColor"/>
        </svg>
      </button>
    </div>

    <div v-if="assetDistribution && assetDistribution.length" class="allocation-container">
      <div class="chart-section">
        <DoughnutChart
          :labels="chartData.labels"
          :values="chartData.values"
          :colors="colors"
          layout="horizontal"
          :format-value="formatMoney"
          height="300px"
          :show-legend="false"
        />
      </div>
      
      <div class="legend-section">
        <div class="legends two-columns">
          <div class="legend-column">
            <div 
              v-for="(asset, i) in leftColumnAssets" 
              :key="asset.asset_id || asset.asset_ticker || i" 
              class="legend-item"
            >
              <span 
                class="legend-color" 
                :style="{ 
                  backgroundColor: colors[i % colors.length]
                }"
              ></span>
              <span class="legend-label">{{ asset.asset_name || asset.asset_ticker || 'Unknown' }}</span>
              <span class="legend-value">
                {{ total > 0 ? Math.round(((asset.total_value || 0) / total) * 100 * 100) / 100 : 0 }}%
              </span>
            </div>
          </div>
          <div class="legend-column">
            <div 
              v-for="(asset, i) in rightColumnAssets" 
              :key="asset.asset_id || asset.asset_ticker || (leftColumnAssets.length + i)" 
              class="legend-item"
            >
              <span 
                class="legend-color" 
                :style="{ 
                  backgroundColor: colors[(leftColumnAssets.length + i) % colors.length]
                }"
              ></span>
              <span class="legend-label">{{ asset.asset_name || asset.asset_ticker || 'Unknown' }}</span>
              <span class="legend-value">
                {{ total > 0 ? Math.round(((asset.total_value || 0) / total) * 100 * 100) / 100 : 0 }}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="empty-state">
      <p>Нет данных о распределении активов</p>
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
  gap: 20px;
  width: 100%;
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.widget-title {
  display: flex;
  gap: 8px;
  align-items: center;
}

.widget-title h2 {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.help-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  padding: 0;
  transition: color 0.2s;
}

.help-icon:hover {
  color: #111827;
}

.filter-button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  color: #111827;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-button:hover {
  border-color: #d1d5db;
  background: #f9fafb;
}

.filter-button svg {
  color: #6b7280;
}

.allocation-container {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 60px;
  width: 100%;
}

.chart-section {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  box-sizing: border-box;
}

.legend-section {
  flex: 1;
  min-width: 0;
}

.legends {
  display: flex;
  flex-direction: column;
  gap: 12px;
  font-size: 12px;
  color: #6B7280;
}

.legends.two-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 20px;
  max-height: 400px;
  overflow-y: auto;
}

.legend-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  min-width: 0;
}

.legend-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 8px;
  flex-shrink: 0;
}

.legend-value {
  color: #6B7280;
  font-size: 12px;
  flex-shrink: 0;
}

.empty-state {
  text-align: center;
  color: #6b7280;
  font-size: 14px;
  padding: 40px 20px;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-state p {
  margin: 0;
}

@media (max-width: 768px) {
  .allocation-container {
    flex-direction: column;
    gap: 20px;
  }
  
  .legends.two-columns {
    grid-template-columns: 1fr;
  }
  
  .widget-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}
</style>

