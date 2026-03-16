<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import DoughnutChart from '../../charts/DoughnutChart.vue'
import Widget from '../base/Widget.vue'
import { PieChart } from 'lucide-vue-next'

const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1200)
const chartHeight = computed(() => {
  if (windowWidth.value <= 480) return '200px'
  if (windowWidth.value <= 768) return '240px'
  if (windowWidth.value <= 1200) return '260px'
  return '300px'
})

function updateWidth() {
  windowWidth.value = window.innerWidth
}

onMounted(() => {
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', updateWidth)
  }
})
onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', updateWidth)
  }
})

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
  <Widget title="Все активы" :icon="PieChart">
    <template #header>
      <button class="help-icon" title="Справка">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/>
          <path d="M8 11V8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <circle cx="8" cy="5" r="0.5" fill="currentColor"/>
        </svg>
      </button>
      <button class="filter-button" title="Фильтр по вложениям">
        <span>По вложениям</span>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/>
          <path d="M8 11V8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <circle cx="8" cy="5" r="0.5" fill="currentColor"/>
        </svg>
      </button>
    </template>

    <div v-if="assetDistribution && assetDistribution.length" class="allocation-container">
      <div class="chart-section">
        <DoughnutChart
          :labels="chartData.labels"
          :values="chartData.values"
          :colors="colors"
          layout="horizontal"
          :format-value="formatMoney"
          :height="chartHeight"
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
  </Widget>
</template>

<style scoped>
/* Убраны стили .widget, .widget-header, .widget-title - теперь используется компонент Widget */

.help-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 0;
  transition: color 0.2s;
}

.help-icon:hover {
  color: var(--text-primary);
}

.filter-button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  color: var(--text-primary);
  font-size: var(--text-body-secondary-size);
  font-weight: var(--text-label-weight);
  cursor: pointer;
  transition: all 0.2s;
}

.filter-button:hover {
  border-color: #d1d5db;
  background: #f9fafb;
}

.filter-button svg {
  color: var(--text-tertiary);
}

.allocation-container {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 60px;
  width: 100%;
  min-width: 0;
}

.chart-section {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  box-sizing: border-box;
  max-width: 100%;
}

.legend-section {
  flex: 1;
  min-width: 0;
}

.legends {
  display: flex;
  flex-direction: column;
  gap: 12px;
  font-size: var(--text-caption-size);
  color: var(--text-tertiary);
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
  color: var(--text-tertiary);
  font-size: var(--text-caption-size);
  flex-shrink: 0;
}

.empty-state {
  text-align: center;
  color: var(--text-tertiary);
  font-size: var(--text-caption-size);
  padding: 40px 20px;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-state p {
  margin: 0;
}

@media (max-width: 1200px) {
  .allocation-container {
    gap: 32px;
  }
  .chart-section {
    padding: 16px;
  }
  .legends.two-columns {
    gap: 10px 16px;
    max-height: 320px;
  }
}

@media (max-width: 768px) {
  .allocation-container {
    flex-direction: column;
    gap: 20px;
  }
  .chart-section {
    padding: 12px;
    width: 100%;
  }
  /* На мобильной список активов в два столбца, уменьшенный шрифт */
  .legends.two-columns {
    grid-template-columns: 1fr 1fr;
    gap: 8px 12px;
    max-height: 280px;
    font-size: 0.75rem;
  }
  .legend-item {
    gap: 0.25rem;
  }
  .legend-color {
    width: 10px;
    height: 10px;
    margin-right: 6px;
  }
  .legend-value {
    font-size: 0.6875rem;
  }
}

@media (max-width: 480px) {
  .allocation-container {
    gap: 16px;
  }
  .chart-section {
    padding: 8px;
  }
  .legends.two-columns {
    gap: 6px 10px;
    max-height: 240px;
    font-size: 0.6875rem;
  }
  .legend-color {
    width: 8px;
    height: 8px;
    margin-right: 4px;
  }
  .legend-value {
    font-size: 0.625rem;
  }
}
</style>

