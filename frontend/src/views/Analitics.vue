<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { Chart, registerables } from 'chart.js'
import { useAuthStore } from '../stores/auth.store'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import { useTransactionsStore } from '../stores/transactions.store'
Chart.register(...registerables)

// Используем stores вместо inject
const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const uiStore = useUIStore()
const transactionsStore = useTransactionsStore()

// --- Локальное состояние ---
const selectedPortfolioId = ref(null)
const selectedPortfolioAnalytics = ref(null)
const isLoadingAnalytics = ref(false)

// --- Элементы графиков ---
const pieCanvas = ref(null)
const barCanvas = ref(null)
let pieChart = null
let barChart = null

const portfolios = computed(() => dashboardStore.portfolios ?? [])

// --- ⚡ Автовыбор первого портфеля ---
watch(
  () => dashboardStore.portfolios,
  (newPortfolios) => {
    if (newPortfolios?.length && !selectedPortfolioId.value) {
      selectedPortfolioId.value = newPortfolios[0].id
    }
  },
  { immediate: true }
)

// --- 🧩 Автозагрузка аналитики, когда dashboard готов ---
watch(
  () => dashboardStore.portfolios,
  async (portfolios) => {
    if (portfolios?.length) {
      await safeLoadAnalytics()
    }
  },
  { immediate: true }
)

// --- Безопасная загрузка аналитики ---
async function safeLoadAnalytics() {
  if (isLoadingAnalytics.value) return
  try {
    isLoadingAnalytics.value = true
    await transactionsStore.loadAnalytics()

    // дожидаемся, пока аналитика появится в dashboardStore
    await nextTick()
    watch(
    () => dashboardStore.analytics,
    async (newAnalytics) => {
        if (Array.isArray(newAnalytics) && newAnalytics.length > 0) {
        await updateSelectedAnalytics()
        }
    },
    { immediate: true, once: true, deep: true }
    )

  } catch (err) {
    console.error('❌ Ошибка при загрузке аналитики:', err)
  } finally {
    isLoadingAnalytics.value = false
  }
}

// --- Перерисовка при смене портфеля ---
watch(selectedPortfolioId, async () => {
  await updateSelectedAnalytics()
})

// --- Форматирование чисел ---
function formatMoney(value) {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  }).format(value || 0)
}

// --- Отрисовка графиков ---
async function drawCharts() {
  const analytics = selectedPortfolioAnalytics.value
  if (!analytics) {
    console.warn('⚠️ drawCharts: нет аналитики для выбранного портфеля')
    return
  }

  await nextTick()

  const breakdown = analytics.operations_breakdown || []
  const monthly = analytics.monthly_flow || []

  const pieCtx = pieCanvas.value?.getContext?.('2d')
  const barCtx = barCanvas.value?.getContext?.('2d')

  if (!pieCtx || !barCtx) {
    console.warn('⚠️ drawCharts: canvas не готов')
    return
  }

  // Очистка старых графиков
  if (pieChart) pieChart.destroy()
  if (barChart) barChart.destroy()

  try {
    // 🥧 Диаграмма распределения
    pieChart = new Chart(pieCtx, {
      type: 'doughnut',
      data: {
        labels: breakdown.map(b => b.type),
        datasets: [{
          data: breakdown.map(b => b.sum),
          backgroundColor: [
            '#3b82f6', '#10b981', '#f59e0b',
            '#ef4444', '#8b5cf6', '#f43f5e'
          ]
        }]
      },
      options: {
        plugins: { legend: { position: 'bottom' } },
        responsive: true,
        maintainAspectRatio: false
      }
    })

    // 📊 Диаграмма динамики
    barChart = new Chart(barCtx, {
      type: 'bar',
      data: {
        labels: monthly.map(m => m.month),
        datasets: [
          { label: 'Приток', data: monthly.map(m => m.inflow), backgroundColor: '#10b981' },
          { label: 'Отток', data: monthly.map(m => m.outflow), backgroundColor: '#ef4444' }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { x: { stacked: true }, y: { stacked: true } }
      }
    })
  } catch (err) {
    console.error('❌ Ошибка при создании графика:', err)
  }
}

// --- Обновление выбранной аналитики ---
async function updateSelectedAnalytics() {
  const allAnalytics = dashboardStore.analytics ?? []
  selectedPortfolioAnalytics.value =
    allAnalytics.find(a => a.portfolio_id === selectedPortfolioId.value) || null


  if (!selectedPortfolioAnalytics.value) {
    console.warn('⚠️ Аналитика не найдена для портфеля', selectedPortfolioId.value)
    return
  }

  await nextTick()
  drawCharts()
}
</script>

<template>
  <div v-if="!uiStore.loading">
    <div class="title" style="display: flex; align-items: center; justify-content: space-between;">
      <div>
        <h1>Финансовая аналитика</h1>
        <h2>Сводные показатели</h2>
      </div>

      <!-- 🔘 Селектор портфеля -->
      <div class="portfolio-selector">
        <select v-model="selectedPortfolioId" class="portfolio-select">
          <option v-for="p in portfolios" :key="p.id" :value="p.id">
            {{ p.name }}
          </option>
        </select>
        <div class="select-arrow">▼</div>
      </div>
    </div>

    <LoadingState v-if="isLoadingAnalytics" message="Загрузка аналитики..." />

    <div v-else-if="selectedPortfolioAnalytics" class="widgets-grid">
      <!-- Метрики -->
      <div class="metric-grid">
        <div class="metric" style="--color: #10b981">
          <p>Приток</p>
          <h3>{{ formatMoney(selectedPortfolioAnalytics.totals.inflow) }}</h3>
        </div>
        <div class="metric" style="--color: #ef4444">
          <p>Отток</p>
          <h3>{{ formatMoney(selectedPortfolioAnalytics.totals.outflow) }}</h3>
        </div>
        <div class="metric" style="--color: #10b981">
          <p>Дивиденды</p>
          <h3>{{ formatMoney(selectedPortfolioAnalytics.totals.dividends) }}</h3>
        </div>
        <div class="metric" style="--color: #10b981">
          <p>Купоны</p>
          <h3>{{ formatMoney(selectedPortfolioAnalytics.totals.coupons) }}</h3>
        </div>
        <div class="metric" style="--color: #ef4444">
          <p>Комиссии</p>
          <h3>{{ formatMoney(selectedPortfolioAnalytics.totals.commissions) }}</h3>
        </div>
        <div class="metric" style="--color: #ef4444">
          <p>Налоги</p>
          <h3>{{ formatMoney(selectedPortfolioAnalytics.totals.taxes) }}</h3>
        </div>
      </div>

      <!-- 💰 Чистый поток -->
      <div class="summary-box">
        <h2>Чистый денежный поток</h2>
        <p :class="selectedPortfolioAnalytics.totals.net_cashflow >= 0 ? 'positive' : 'negative'">
          {{ formatMoney(selectedPortfolioAnalytics.totals.net_cashflow) }}
        </p>
      </div>

      <!-- Графики -->
      <div class="chart-box">
        <h2>Распределение по типам операций</h2>
        <div class="chart-container"><canvas ref="pieCanvas"></canvas></div>
      </div>

      <div class="chart-box">
        <h2>Динамика притоков и оттоков</h2>
        <div class="chart-container"><canvas ref="barCanvas"></canvas></div>
      </div>
    </div>
  </div>

  <LoadingState v-else />
</template>

<style scoped>
.title {
  margin-bottom: var(--spacing);
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: var(--spacing);
}
.metric {
  background: var(--bg-secondary, #f8f9fa);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  transition: transform 0.2s ease;
}
.metric:hover { transform: translateY(-2px); }
.metric p { color: var(--text-secondary, #6b7280); font-size: 0.9rem; }
.metric h3 { color: var(--color); font-size: 1.4rem; font-weight: 600; }
.summary-box {
  background: white;
  padding: 24px;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.summary-box h2 { font-size: 1rem; color: #374151; margin-bottom: 8px; }
.summary-box p { font-size: 2rem; font-weight: 600; }
.summary-box .positive { color: #10b981; }
.summary-box .negative { color: #ef4444; }
.chart-box {
  background: white;
  padding: 24px;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.chart-box h2 { margin-bottom: 12px; font-size: 1rem; color: #374151; }
.chart-container { height: 300px; }
.widgets-grid {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}
.portfolio-selector {
  position: relative;
  display: inline-block;
  min-width: 200px;
}
.portfolio-select {
  appearance: none;
  width: 100%;
  padding: 10px 16px;
  padding-right: 40px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #1a1a1a);
  background: var(--bg-secondary, #f8f9fa);
  border: 2px solid var(--border-color, #e1e5e9);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  outline: none;
}
.portfolio-select:hover {
  border-color: var(--primary-color, #007bff);
  background: var(--bg-primary, #ffffff);
}
.select-arrow {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: var(--text-secondary, #6c757d);
  font-size: 12px;
}
</style>
