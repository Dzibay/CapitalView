<script setup>
import { ref, computed, watch } from 'vue'
import MultiLineChart from '../MultiLineChart.vue'
import Widget from './Widget.vue'
import ValueChange from './ValueChange.vue'

// --------------------------------------------------------------
// ПРОПСЫ
// --------------------------------------------------------------
const props = defineProps({
  chartData: {
    type: Object,
    required: true
  }
})

const selectedPeriod = ref("All")

// --------------------------------------------------------------
// Формат валюты
// --------------------------------------------------------------
const formatCurrency = (value) => {
  if (typeof value !== 'number') return value
  return value.toLocaleString('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  })
}

// --------------------------------------------------------------
// СТАТИСТИКА прибыльности
// --------------------------------------------------------------
const startValue = ref(0)
const endValue = ref(0)
const profitAbs = ref(0)
const profitPercent = ref(0)

const updateStats = (data) => {
  if (!data || !data.length) {
    startValue.value = 0
    endValue.value = 0
    profitAbs.value = 0
    profitPercent.value = 0
    return
  }
  
  startValue.value = data[0]
  endValue.value = data[data.length - 1]
  
  // Абсолютное изменение за весь период данных
  profitAbs.value = endValue.value - startValue.value
  
  // Процент изменения относительно начальной точки
  profitPercent.value =
    startValue.value === 0
      ? 0
      : ((profitAbs.value / Math.abs(startValue.value)) * 100).toFixed(1)
}

// --------------------------------------------------------------
// ПОДГОТОВКА ДАННЫХ ДЛЯ MultiLineChart
// --------------------------------------------------------------
const formattedChartData = computed(() => {
  // Проверка на наличие данных
  if (!props.chartData?.labels?.length || !props.chartData?.data_pnl) {
    return { labels: [], datasets: [] }
  }

  // Берем готовый PnL из данных
  const pnlData = props.chartData.data_pnl

  // Обновляем статистику в шапке (на основе полных данных)
  updateStats(pnlData)

  return {
    labels: props.chartData.labels,
    datasets: [
      {
        label: "Прибыль",
        data: pnlData,
        color: "#5478EA",
        fill: true
      }
    ]
  }
})

// Следим за изменениями входящих данных
watch(() => props.chartData, () => {
  const pnlData = props.chartData?.data_pnl || []
  updateStats(pnlData)
}, { deep: true })
</script>

<template>
  <Widget title="Динамика прибыли">
    <template #header>
      <div class="capital-filters">
        <button
          v-for="period in ['1M','1Y','All']"
          :key="period"
          @click="selectedPeriod = period"
          :class="['filter-btn', { active: selectedPeriod === period }]"
        >
          {{ period === '1M' ? 'Месяц' : period === '1Y' ? 'Год' : 'Все время' }}
        </button>
      </div>
    </template>

    <div class="capital-info">
      <p class="capital-values" style="margin-top: 15px;">
        {{ formatCurrency(startValue) }} → {{ formatCurrency(endValue) }}
      </p>

      <div class="capital-growth">
        <p>Прибыль: {{ formatCurrency(profitAbs) }}</p>
        <ValueChange 
          :value="profitPercent" 
          :is-positive="profitAbs >= 0"
          format="percent"
        />
      </div>
    </div>

    <div class="chart-wrapper">
      <MultiLineChart
        :chartData="formattedChartData"
        :period="selectedPeriod"
        :formatCurrency="formatCurrency"
      />
    </div>
  </Widget>
</template>

<style scoped>
/* Убраны стили .widget, .capital-header - теперь используется компонент Widget */
.capital-info {
  margin-bottom: 1rem;
}

.capital-growth {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.capital-filters {
  display: flex;
  background-color: #f3f4f6;
  padding: 0.25rem;
  border-radius: 8px;
  gap: 0.25rem;
}

.filter-btn {
  border: none;
  background: transparent;
  border-radius: 6px;
  padding: 0.5rem 0.9rem;
  font-size: 0.9rem;
  cursor: pointer;
}

.filter-btn.active {
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  color: #5478EA;
  font-weight: 600;
}

.chart-wrapper {
  flex: 1;
  position: relative;
}

.value-change.positive {
  color: #10b981;
}

.value-change.negative {
  color: #ef4444;
}
</style>