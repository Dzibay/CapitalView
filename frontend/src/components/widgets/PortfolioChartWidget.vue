<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import MultiLineChart from '../MultiLineChart.vue'   // подключаем новый компонент
import Widget from './Widget.vue'
import ValueChange from './ValueChange.vue'

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

// Функция для получения первого и последнего значения за период
function getPeriodValues(labels, data, period) {
  if (!labels || !labels.length || !data || !data.length) return [null, null]
  
  const today = new Date()
  today.setHours(23, 59, 59, 999) // Устанавливаем конец дня
  const parseDate = d => new Date(d)
  
  // Создаем массив точек с датами и значениями, сортируем по дате
  const points = labels.map((label, index) => ({
    date: parseDate(label),
    value: Number(data[index]) || 0
  })).sort((a, b) => a.date - b.date)
  
  if (!points.length) return [null, null]
  
  // Определяем начальную дату периода
  let periodStartDate
  if (period === '1M') {
    periodStartDate = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 30)
    periodStartDate.setHours(0, 0, 0, 0)
  } else if (period === '1Y') {
    periodStartDate = new Date(today.getFullYear(), today.getMonth() - 11, 1)
    periodStartDate.setHours(0, 0, 0, 0)
  } else {
    // Для периода "All" используем первую доступную дату
    periodStartDate = points[0].date
  }
  
  // Фильтруем точки, которые попадают в период
  const pointsInPeriod = points.filter(p => {
    const pointDate = new Date(p.date)
    pointDate.setHours(0, 0, 0, 0)
    const startDate = new Date(periodStartDate)
    startDate.setHours(0, 0, 0, 0)
    const endDate = new Date(today)
    endDate.setHours(0, 0, 0, 0)
    return pointDate >= startDate && pointDate <= endDate
  })
  
  // Если нет точек в периоде, но есть точки до периода, используем последнюю доступную
  if (pointsInPeriod.length === 0) {
    const pointsBeforePeriod = points.filter(p => {
      const pointDate = new Date(p.date)
      pointDate.setHours(0, 0, 0, 0)
      const endDate = new Date(today)
      endDate.setHours(0, 0, 0, 0)
      return pointDate <= endDate
    })
    
    if (pointsBeforePeriod.length > 0) {
      const lastPoint = pointsBeforePeriod[pointsBeforePeriod.length - 1]
      return [lastPoint.value, lastPoint.value]
    }
    
    // Если вообще нет точек, используем первую и последнюю из всех
    return [points[0].value, points[points.length - 1].value]
  }
  
  // Возвращаем первое и последнее значение из отфильтрованных точек
  return [pointsInPeriod[0].value, pointsInPeriod[pointsInPeriod.length - 1].value]
}

const updateStats = (labels, values, period) => {
  const [firstVal, lastVal] = getPeriodValues(labels, values, period)
  
  if (firstVal === null || lastVal === null) {
    startValue.value = 0
    endValue.value = 0
    growthAmount.value = 0
    growthPercent.value = 0
    return
  }
  
  const start = Number(firstVal) || 0
  const end = Number(lastVal) || 0
  
  startValue.value = start
  endValue.value = end
  growthAmount.value = end - start
  
  if (start === 0) {
    growthPercent.value = 0
  } else {
    growthPercent.value = ((growthAmount.value / start) * 100).toFixed(1)
  }
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
      data: (props.chartData.data_value || []).map(v => Number(v) || 0),
      color: '#3b82f6',
      fill: true
    },
    {
      label: "Инвестиции",
      data: (props.chartData.data_invested || []).map(v => Number(v) || 0),
      color: '#10b981',
      fill: false
    }
  ]

  return { labels, datasets }
})

// Обновляем статистику при изменении данных или периода
const updateStatsForPeriod = () => {
  if (!props.chartData?.labels?.length || !props.chartData?.data_value) {
    updateStats([], [], selectedPeriod.value)
    return
  }
  updateStats(props.chartData.labels, props.chartData.data_value, selectedPeriod.value)
}

// Следим за изменениями данных и периода
watch(() => props.chartData, updateStatsForPeriod, { deep: true })
watch(() => selectedPeriod.value, updateStatsForPeriod)

// Инициализация при монтировании
onMounted(() => {
  updateStatsForPeriod()
})

</script>

<template>
  <Widget title="Динамика капитала">
    <template #header>
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
    </template>

    <div class="capital-info">
      <p class="capital-values" style="margin-top: 15px;">
        {{ formatCurrency(startValue) }} → {{ formatCurrency(endValue) }}
      </p>

      <div class="capital-growth">
        <p>Прирост: {{ formatCurrency(growthAmount) }}</p>
        <ValueChange 
          :value="growthPercent" 
          :is-positive="growthAmount >= 0"
          format="percent"
        />
      </div>
    </div>

    <!-- График -->
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
  transition: background-color 0.2s,color 0.2s;
}
.filter-btn:hover { background-color: #e5e7eb; }
.filter-btn.active {
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  color: #5478EA;
  font-weight: 600;
}
.chart-wrapper { 
  flex: 1; 
  position: relative; 
  min-height: 0; /* Позволяет графику правильно сжиматься */
}
</style>
