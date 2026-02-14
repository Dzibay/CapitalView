<script setup>
import { ref, computed, watch } from 'vue'
import MultiLineChart from '../../MultiLineChart.vue'
import Widget from '../base/Widget.vue'
import ValueChange from '../base/ValueChange.vue'
import PeriodFilters from '../base/PeriodFilters.vue'

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

// Функция для фильтрации данных по периоду (аналогично MultiLineChart)
function filterDataByPeriod(labels, data, period) {
  if (!labels || !labels.length || !data || !data.length) return { labels: [], data: [] }
  
  const today = new Date()
  const normalizeDate = (date) => {
    const d = new Date(date)
    d.setHours(0, 0, 0, 0)
    return d
  }
  
  const parseDate = (d) => normalizeDate(new Date(d))
  
  const points = labels.map((label, index) => ({
    date: parseDate(label),
    value: data[index]
  })).sort((a, b) => a.date - b.date)
  
  if (!points.length) return { labels: [], data: [] }
  
  const firstPoint = points[0]?.date
  let firstDate
  
  if (period === '1M') {
    firstDate = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 30)
  } else if (period === '1Y') {
    firstDate = new Date(today.getFullYear(), today.getMonth() - 11, 1)
  } else {
    firstDate = firstPoint ? new Date(firstPoint) : new Date(today)
  }
  
  firstDate = normalizeDate(firstDate)
  const lastDate = normalizeDate(today)
  
  const filteredPoints = points.filter(p => {
    const pointDate = normalizeDate(p.date)
    return pointDate >= firstDate && pointDate <= lastDate
  })
  
  if (filteredPoints.length === 0) {
    // Если нет точек в периоде, возвращаем пустые массивы
    return { labels: [], data: [] }
  }
  
  return {
    labels: filteredPoints.map(p => p.date.toISOString().split("T")[0]),
    data: filteredPoints.map(p => p.value)
  }
}

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
  
  // Абсолютное изменение за период
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

// Вычисляем отфильтрованные данные для статистики
const filteredDataForStats = computed(() => {
  if (!props.chartData?.labels?.length || !props.chartData?.data_pnl) {
    return []
  }
  
  const filtered = filterDataByPeriod(
    props.chartData.labels,
    props.chartData.data_pnl,
    selectedPeriod.value
  )
  
  return filtered.data
})

// Обновляем статистику при изменении периода или данных
watch([filteredDataForStats, selectedPeriod], () => {
  updateStats(filteredDataForStats.value)
}, { immediate: true })

// Следим за изменениями входящих данных
watch(() => props.chartData, () => {
  const filtered = filterDataByPeriod(
    props.chartData?.labels || [],
    props.chartData?.data_pnl || [],
    selectedPeriod.value
  )
  updateStats(filtered.data)
}, { deep: true })
</script>

<template>
  <Widget title="Динамика прибыли">
    <template #header>
      <PeriodFilters v-model="selectedPeriod" />
    </template>

    <div class="capital-info">
      <p class="capital-values" style="margin-top: 0;">
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
  margin-bottom: 0.75rem;
}

.capital-growth {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.chart-wrapper {
  flex: 1;
  position: relative;
  min-height: 0;
}
</style>