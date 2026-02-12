<script setup>
import { computed } from 'vue'
import DoughnutChart from '../charts/DoughnutChart.vue'
import Widget from './Widget.vue'

const props = defineProps({
  portfolios: {
    type: Array,
    default: () => []
  },
  allPortfolios: {
    type: Array,
    default: () => []
  },
  selectedPortfolioId: {
    type: Number,
    default: null
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

// Получаем портфели только на один уровень вниз
const portfolioValues = computed(() => {
  if (!props.selectedPortfolioId || !props.allPortfolios?.length) return []
  
  // Находим выбранный портфель
  const selectedPortfolio = props.allPortfolios.find(p => p.portfolio_id === props.selectedPortfolioId)
  if (!selectedPortfolio) return []
  
  // Получаем портфели только на один уровень вниз
  const directChildren = props.portfolios
    .filter(p => p.parent_portfolio_id === props.selectedPortfolioId)
    .map((childPortfolio, index) => {
      const childAnalytics = props.allPortfolios.find(a => a.portfolio_id === childPortfolio.id)
      return {
        name: childPortfolio.name,
        value: childAnalytics?.totals?.total_value || 0,
        index: index
      }
    })
    .filter(p => p.value > 0)
  
  // Добавляем текущий портфель, если у него есть собственные активы (не в дочерних)
  const parentValue = selectedPortfolio.totals?.total_value || 0
  const childrenSum = directChildren.reduce((sum, child) => sum + child.value, 0)
  const ownValue = Math.max(0, parentValue - childrenSum)
  
  const values = []
  if (ownValue > 0) {
    values.push({
      name: selectedPortfolio.portfolio_name,
      value: ownValue,
      index: -1
    })
  }
  values.push(...directChildren)
  
  return values
})

const chartData = computed(() => {
  if (!portfolioValues.value?.length) {
    return { labels: [], values: [] }
  }
  
  const labels = portfolioValues.value.map(p => p.name)
  const values = portfolioValues.value.map(p => p.value)
  
  return { labels, values }
})

const total = computed(() => {
  return chartData.value.values.reduce((a, b) => a + b, 0)
})

</script>

<template>
  <Widget title="Распределение портфелей">
    <div v-if="portfolioValues && portfolioValues.length" class="allocation-container">
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
        <div class="legends">
          <div 
            v-for="(portfolio, i) in portfolioValues" 
            :key="portfolio.name || i" 
            class="legend-item"
          >
            <span 
              class="legend-color" 
              :style="{ 
                backgroundColor: colors[i % colors.length]
              }"
            ></span>
            <span class="legend-label">{{ portfolio.name }}</span>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="empty-state">
      <p>Нет данных о распределении портфелей</p>
    </div>
  </Widget>
</template>

<style scoped>
/* Убраны стили .widget, .widget-title - теперь используется компонент Widget */

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
}

.legend-section {
  flex: 1;
  min-width: 0;
}

.legends {
  display: flex;
  flex-direction: column;
  gap: 12px;
  font-size: 13px;
}

.legends {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
  font-size: 12px;
  color: #6B7280;
}

.legend-item {
  display: flex;
  align-items: center;
  min-width: 0;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 8px;
  flex-shrink: 0;
}

.legend-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  max-width: 100%;
}

.legend-value {
  color: #6b7280;
  font-size: 12px;
  font-weight: 400;
  flex-shrink: 0;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #6b7280;
  font-size: 14px;
  padding: 40px 20px;
}

.empty-state p {
  margin: 0;
}
</style>
