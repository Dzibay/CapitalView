<script setup>
import { onMounted, ref, watch } from 'vue'
import { Chart, LineElement, PointElement, LineController, CategoryScale, LinearScale, Filler, Tooltip, Legend } from 'chart.js'

Chart.register(LineElement, PointElement, LineController, CategoryScale, LinearScale, Filler, Tooltip, Legend)

const props = defineProps({
  chartData: {
    type: Object,
    required: true,
    // { labels: ['2024-01-01', ...], data: [50000, ...] }
  }
})

const selectedPeriod = ref('All')
let chartInstance = null

// Статистика
const startValue = ref(0)
const endValue = ref(0)
const growthAmount = ref(0)
const growthPercent = ref(0)

// Формат валюты
const formatCurrency = (value) => {
  if (typeof value !== 'number') return value
  return value.toLocaleString('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  })
}

// --- Адаптивная агрегация данных ---
function aggregateLabelsAndData(dataObj, period) {
  const labels = [];
  const data = [];
  const today = new Date();

  if (!dataObj?.data?.length) return { labels, data };

  const parseDate = d => new Date(d);
  const points = dataObj.labels
    .map((label, idx) => ({ date: parseDate(label), value: dataObj.data[idx] }))
    .sort((a, b) => a.date - b.date);

  let firstDate;
  if (period === '1M') {
    firstDate = new Date(today);
    firstDate.setDate(today.getDate() - 30);
  } else if (period === '1Y') {
    firstDate = new Date(today.getFullYear(), today.getMonth() - 11, 1);
  } else { // 'All'
    firstDate = new Date(Math.min(...points.map(p => p.date)));
  }

  const lastDate = today;
  let pointIndex = 0;

  let lastKnownValue = 0; // до первой транзакции 0
  let firstPointDate = points[0]?.date;

  for (let d = new Date(firstDate); d <= lastDate; d.setDate(d.getDate() + 1)) {
    if (firstPointDate && d < firstPointDate) {
      // до появления первых данных — 0
      data.push(0);
    } else {
      while (pointIndex < points.length && points[pointIndex].date <= d) {
        lastKnownValue = points[pointIndex].value;
        pointIndex++;
      }
      data.push(lastKnownValue);
    }
    labels.push(d.toISOString().split('T')[0]);
  }

  return { labels, data, firstDate, lastDate };
}


// --- Вычисление статистики ---
const calculateGrowth = (data) => {
  if (!data?.length) return
  startValue.value = data[0]
  endValue.value = data[data.length - 1]
  growthAmount.value = endValue.value - startValue.value
  growthPercent.value = ((growthAmount.value / startValue.value) * 100).toFixed(1)
}

// --- Функция округления вверх к "красивой" величине ---
function getNiceMax(value) {
  if (value <= 0) return 1000

  // добавляем лёгкий запас (чтобы метка не совпадала с точкой)
  const padded = value * 1.1

  let step
  if (padded < 100_000) step = 10_000
  else if (padded < 1_000_000) step = 50_000
  else if (padded < 5_000_000) step = 100_000
  else if (padded < 10_000_000) step = 250_000
  else if (padded < 50_000_000) step = 500_000
  else step = 1_000_000

  // 🔹 округляем вниз
  const rounded = Math.floor(padded / step) * step

  // если вдруг округлилось ниже самого значения — добавим ещё один шаг
  return rounded < value ? rounded + step : rounded
}

// --- Функция округления вниз к "красивой" величине ---
function getNiceMin(value) {
  if (value === 0) return 0
  const magnitude = Math.pow(10, Math.floor(Math.log10(Math.abs(value))))
  return Math.floor(value / magnitude) * magnitude
}

// --- Рендер графика ---
const renderChart = (aggregated) => {
  const ctx = document.getElementById('capitalChart')?.getContext('2d')
  if (!ctx) return

  const yMin = getNiceMin(Math.min(...aggregated.data))
  const yMax = getNiceMax(Math.max(...aggregated.data))

  if (chartInstance) {
    chartInstance.data.labels = aggregated.labels
    chartInstance.data.datasets[0].data = aggregated.data
    chartInstance.options.scales.y.min = yMin
    chartInstance.options.scales.y.max = yMax
    chartInstance.resize()
    chartInstance.update()
    return
  }

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: aggregated.labels,
      datasets: [{
        label: 'Капитал',
        data: aggregated.data,
        fill: true,
        backgroundColor: (context) => {
          const chart = context.chart
          const {ctx, chartArea} = chart
          if (!chartArea) return null
          const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
          gradient.addColorStop(0, 'rgba(59, 130, 246, 0.2)')
          gradient.addColorStop(1, 'rgba(59, 130, 246, 0)')
          return gradient
        },
        borderColor: '#3b82f6',
        borderWidth: 3,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 6,
        pointBackgroundColor: '#3b82f6',
        pointBorderColor: '#fff',
        pointBorderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        y: {
          min: yMin,
          max: yMax,
          ticks: {
            callback: (value) => value >= 1000 ? value/1000 + 'k' : value,
            color: '#9ca3af',
            padding: 10
          },
          grid: { color: '#e5e7eb', borderDash: [5,5], drawBorder: false }
        },
        x: {
  type: 'category',
  ticks: {
    color: '#9ca3af',
    autoSkip: false,
    maxRotation: 0,
    minRotation: 0,
    callback: function(value, index) {
  const labels = this.chart.data.labels;
  if (!labels || index >= labels.length) return '';

  const d = new Date(labels[index]);
  const prevDate = index > 0 ? new Date(labels[index - 1]) : null;

  const firstLabelDate = new Date(labels[0]);
  const lastLabelDate = new Date(labels[labels.length - 1]);
  const totalDays = (lastLabelDate - firstLabelDate) / (1000 * 60 * 60 * 24);

  // --- 1. Логика для месячного графика (период до 45 дней) ---
  // Задача: показывать числа с минимальным шагом.
  if (totalDays <= 45) {
    // Рассчитываем шаг так, чтобы на графике было примерно 5-7 меток
    const step = Math.ceil(labels.length / 45) || 1;

    // Всегда показывать самую первую метку (первое число)
    if (index === 0) {
      return d.getDate();
    }
    // Если начинается новый месяц, обязательно показать его название
    if (prevDate && d.getMonth() !== prevDate.getMonth()) {
      return d.toLocaleString('ru-RU', { month: 'short' });
    }
    // Показать остальные метки с рассчитанным шагом
    if (index % step === 0) {
      return d.getDate();
    }
    return '';
  }

  // --- 2. Логика для годового и более длинных периодов ---
  // Задача: убрать наслоение первой подписи.
  
  // Для самой первой метки на графике
  if (index === 0 && d.getDate() < 15) {
      // Если график начинается с января, логичнее показать год
      return d.getMonth() === 0 
          ? d.getFullYear() 
          : d.toLocaleString('ru-RU', { month: 'short' });
  }

  // Для всех последующих меток
  // Если начался новый год, показать номер года
  if (prevDate && d.getFullYear() !== prevDate.getFullYear()) {
    return d.getFullYear();
  }

  // Если начался новый месяц (но год тот же)
  if (prevDate && d.getMonth() !== prevDate.getMonth()) {
    // Для очень длинных периодов (> 1.5 лет) показываем месяцы поквартально
    if (totalDays > 540) {
      if (d.getMonth() % 3 === 0) { // Показываем янв, апр, июл, окт
        return d.toLocaleString('ru-RU', { month: 'short' });
      }
    } else { // Для годового периода показываем каждый месяц
      return d.toLocaleString('ru-RU', { month: 'short' });
    }
  }

  return ''; // Для всех остальных точек не показывать ничего
}
  },
  grid: { display: false }
}


      },
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: true,
          mode: 'index',
          intersect: false,
          backgroundColor: '#1f2937',
          titleFont: { weight: 'bold' },
          bodyFont: { size: 14 },
          padding: 12,
          cornerRadius: 6,
          displayColors: false,
          callbacks: {
            title: ctx => {
              const d = new Date(ctx[0].label)
              return d.toISOString().split('T')[0] // tooltip показывает точную дату
            },
            label: ctx => formatCurrency(ctx.parsed.y)
          }
        }
      }
    }
  })
}

// --- Обновление графика ---
const updateChart = () => {
  if (!props.chartData?.data?.length) return
  const aggregated = aggregateLabelsAndData(props.chartData, selectedPeriod.value)
  calculateGrowth(aggregated.data)
  renderChart(aggregated)
}

// --- Watchers ---
watch([selectedPeriod], updateChart)
watch(() => props.chartData, updateChart, { deep: true })

onMounted(() => updateChart())
</script>


<template>
  <div class="widget">
    <div class="capital-header">
      <div class="capital-info">

        <div class="widget-title">
          <div class="widget-title-icon-rect">

          </div>
          <h2>Динамика капитала</h2>
        </div>

        <p class="capital-values" style="margin-top: 15px;">
          {{ formatCurrency(startValue) }} → {{ formatCurrency(endValue) }}
        </p>
        <div class="capital-growth">
          <p>Прирост: {{ formatCurrency(growthAmount) }}</p>
          <p class="value-change positive" style="margin-left: 30px;">+{{ growthPercent }}%</p>
        </div>
        
      </div>
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

    <div class="chart-wrapper">
      <canvas id="capitalChart"></canvas>
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
.chart-wrapper { flex:1; position: relative; }
</style>
