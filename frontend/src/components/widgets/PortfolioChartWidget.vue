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
  const dataValue = [];
  const dataInvested = [];

  const today = new Date();
  if (!dataObj?.data_value?.length) return { labels, dataValue, dataInvested };

  const parseDate = d => new Date(d);

  const points = dataObj.labels.map((label, i) => ({
    date: parseDate(label),
    value: dataObj.data_value[i],
    invested: dataObj.data_invested[i]
  })).sort((a, b) => a.date - b.date);

  let firstDate = period === '1M'
    ? new Date(today.setDate(today.getDate() - 30))
    : period === '1Y'
      ? new Date(today.getFullYear(), today.getMonth() - 11, 1)
      : new Date(Math.min(...points.map(p => p.date)));

  const lastDate = new Date();
  let pointIndex = 0;

  let lastValue = 0;
  let lastInvested = 0;

  let firstPointDate = points[0]?.date;

  for (let d = new Date(firstDate); d <= lastDate; d.setDate(d.getDate() + 1)) {

    if (firstPointDate && d < firstPointDate) {
      dataValue.push(0);
      dataInvested.push(0);
    } else {
      while (pointIndex < points.length && points[pointIndex].date <= d) {
        lastValue = points[pointIndex].value;
        lastInvested = points[pointIndex].invested;
        pointIndex++;
      }
      dataValue.push(lastValue);
      dataInvested.push(lastInvested);
    }

    labels.push(d.toISOString().split('T')[0]);
  }

  return { labels, dataValue, dataInvested, firstDate, lastDate };
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

  const allValues = [
    ...aggregated.dataValue,
    ...aggregated.dataInvested
  ]

  const yMin = getNiceMin(Math.min(...allValues))
  const yMax = getNiceMax(Math.max(...allValues))

  // ---- обновление ---
  if (chartInstance) {
    chartInstance.data.labels = aggregated.labels
    chartInstance.data.datasets[0].data = aggregated.dataValue
    chartInstance.data.datasets[1].data = aggregated.dataInvested

    chartInstance.options.scales.y.min = yMin
    chartInstance.options.scales.y.max = yMax

    chartInstance.resize()
    chartInstance.update()
    return
  }

  // ---- создание ---
  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: aggregated.labels,
      datasets: [
        {
          label: 'Капитал',
          data: aggregated.dataValue,
          fill: true,
          backgroundColor: (context) => {
            const chart = context.chart
            const { ctx, chartArea } = chart
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
        },
        {
          label: 'Инвестиции',
          data: aggregated.dataInvested,
          borderColor: '#10b981',
          borderWidth: 2,
          tension: 0.35,
          pointRadius: 0,
          fill: false
        }
      ]
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

        // 🔥 полностью возвращаю твою ось X, без малейших изменений
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

              if (totalDays <= 45) {
                const step = Math.ceil(labels.length / 45) || 1;
                if (index === 0) return d.getDate();
                if (prevDate && d.getMonth() !== prevDate.getMonth())
                  return d.toLocaleString('ru-RU', { month: 'short' });
                if (index % step === 0) return d.getDate();
                return '';
              }

              if (index === 0 && d.getDate() < 15) {
                return d.getMonth() === 0 
                  ? d.getFullYear() 
                  : d.toLocaleString('ru-RU', { month: 'short' });
              }

              if (prevDate && d.getFullYear() !== prevDate.getFullYear())
                return d.getFullYear();

              if (prevDate && d.getMonth() !== prevDate.getMonth()) {
                if (totalDays > 540) {
                  if (d.getMonth() % 3 === 0)
                    return d.toLocaleString('ru-RU', { month: 'short' });
                } else {
                  return d.toLocaleString('ru-RU', { month: 'short' });
                }
              }

              return '';
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
            beforeBody(items) {
              // сортируем по значению: сначала большее
              items.sort((a, b) => b.parsed.y - a.parsed.y);
            },
            title: ctx => {
              const d = new Date(ctx[0].label)
              return d.toISOString().split('T')[0]
            },
            label: ctx => `${ctx.dataset.label}: ${formatCurrency(ctx.parsed.y)}`
          }
        }
      }
    }
  })
}


// --- Обновление графика ---
const updateChart = () => {
  if (!props.chartData?.data_value?.length) return
  const aggr = aggregateLabelsAndData(props.chartData, selectedPeriod.value)

  calculateGrowth(aggr.dataValue)  // прирост по капиталу

  renderChart(aggr)
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
