<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import MultiLineChart from '../MultiLineChart.vue'   // подключаем новый компонент

const props = defineProps({
  chartData: {
    type: Object,
    required: true
  }
})

const selectedPeriod = ref("All")

// --------------------------
// Формат валюты
// --------------------------
const formatCurrency = (value) => {
  if (typeof value !== 'number') return value
  return value.toLocaleString('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  })
}

// --------------------------
// Статистика по капиталу
// --------------------------
const startValue = ref(0)
const endValue = ref(0)
const growthAmount = ref(0)
const growthPercent = ref(0)

const updateStats = (values) => {
  if (!values.length) return
  startValue.value = values[0]
  endValue.value = values[values.length - 1]
  growthAmount.value = endValue.value - startValue.value
  growthPercent.value = ((growthAmount.value / startValue.value) * 100).toFixed(1)
}

// --------------------------
// Формируем данные для универсального графика
// --------------------------
const formattedChartData = computed(() => {
  if (!props.chartData?.labels?.length) return { labels: [], datasets: [] }

  const labels = props.chartData.labels

  const datasets = [
    {
      label: "Капитал",
      data: props.chartData.data_value,
      color: '#3b82f6',
      fill: true
    },
    {
      label: "Инвестиции",
      data: props.chartData.data_invested,
      color: '#10b981',
      fill: false
    }
  ]

  updateStats(props.chartData.data_value)

  return { labels, datasets }
})

// следим за данными
watch(() => props.chartData, () => {
  updateStats(props.chartData?.data_value || [])
}, { deep: true })

</script>

<template>
  <div class="widget">
    <div class="capital-header">
      <div class="capital-info">

        <div class="widget-title">
          <div class="widget-title-icon-rect"></div>
          <h2>Динамика капитала</h2>
        </div>

        <p class="capital-values" style="margin-top: 15px;">
          {{ formatCurrency(startValue) }} → {{ formatCurrency(endValue) }}
        </p>

        <div class="capital-growth">
          <p>Прирост: {{ formatCurrency(growthAmount) }}</p>
          <p class="value-change positive" style="margin-left: 30px;">
            +{{ growthPercent }}%
          </p>
        </div>
      </div>

      <!-- Фильтры периодов -->
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
    </div>

    <!-- График -->
    <div class="chart-wrapper">
      <MultiLineChart
        :chartData="formattedChartData"
        :period="selectedPeriod"
      />
    </div>
  </div>
</template>

<style scoped>
.widget {
  grid-row: span 3;
  grid-column: span 3;
  background-color: #fff;
  padding: var(--spacing);
  border-radius: 14px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  height: 100%;
}
.capital-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}
.capital-info { max-width: 60%; }
.capital-growth {
  display: flex;
  justify-content: space-between;
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
  transition: background-color 0.2s,color 0.2s;
}
.filter-btn:hover { background-color: #e5e7eb; }
.filter-btn.active {
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  color: #5478EA;
  font-weight: 600;
}
.chart-wrapper { flex: 1; position: relative; }
</style>
