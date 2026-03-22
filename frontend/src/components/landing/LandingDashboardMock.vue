<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const root = ref(null)
const capital = ref(0)
const profit = ref(0)
const inView = ref(false)
let rafIds = []

const targetCapital = 1_842_500
const targetProfit = 18.4

const months = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']

const chartData = computed(() => ({
  labels: months,
  datasets: [
    {
      label: 'Капитал',
      data: [120, 128, 135, 142, 148, 155, 162, 168, 172, 178, 182, 184],
      borderColor: 'rgba(59, 130, 246, 0.9)',
      backgroundColor: 'rgba(59, 130, 246, 0.12)',
      fill: true,
      tension: 0.4,
      pointRadius: 0,
      borderWidth: 2
    },
    {
      label: 'Бенчмарк',
      data: [118, 122, 126, 129, 131, 134, 136, 138, 139, 141, 142, 143],
      borderColor: 'rgba(139, 92, 246, 0.55)',
      backgroundColor: 'transparent',
      fill: false,
      tension: 0.35,
      pointRadius: 0,
      borderWidth: 2,
      borderDash: [6, 4]
    }
  ]
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: inView.value ? { duration: 1400 } : false,
  interaction: { intersect: false, mode: 'index' },
  plugins: {
    legend: {
      display: true,
      position: 'top',
      align: 'end',
      labels: { boxWidth: 10, usePointStyle: true, font: { size: 11, family: 'Plus Jakarta Sans, sans-serif' } }
    },
    tooltip: { enabled: true }
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { font: { size: 10 }, maxRotation: 0, color: '#94a3b8' }
    },
    y: {
      grid: { color: 'rgba(148, 163, 184, 0.15)' },
      ticks: {
        font: { size: 10 },
        color: '#94a3b8',
        callback: (v) => `${v}%`
      }
    }
  }
}))

function cancelRafs() {
  rafIds.forEach((id) => cancelAnimationFrame(id))
  rafIds = []
}

function animateCount(getter, setter, target, durationMs) {
  const start = performance.now()
  const from = getter()
  const delta = target - from
  const tick = (now) => {
    const t = Math.min(1, (now - start) / durationMs)
    const eased = 1 - (1 - t) ** 3
    setter(from + delta * eased)
    if (t < 1) rafIds.push(requestAnimationFrame(tick))
  }
  rafIds.push(requestAnimationFrame(tick))
}

function formatMoney(n) {
  return Math.round(n).toLocaleString('ru-RU', { maximumFractionDigits: 0 }) + ' ₽'
}

function runAnimations() {
  cancelRafs()
  capital.value = 0
  profit.value = 0
  animateCount(() => capital.value, (v) => { capital.value = v }, targetCapital, 1800)
  animateCount(() => profit.value, (v) => { profit.value = v }, targetProfit, 1600)
  inView.value = true
}

let observer

onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting && e.intersectionRatio > 0.12) {
          runAnimations()
          observer?.unobserve(e.target)
        }
      })
    },
    { threshold: [0.12, 0.25] }
  )
  if (root.value) observer.observe(root.value)
})

onUnmounted(() => {
  observer?.disconnect()
  cancelRafs()
})

</script>

<template>
  <div ref="root" class="mock" aria-hidden="true">
    <div class="mock-inner">
      <aside class="mock-side">
        <div class="mock-logo">Capital<span>View</span></div>
        <p class="mock-side-h">Меню</p>
        <div class="mock-nav">
          <span class="nav-i on">Дашборд</span>
          <span class="nav-i">Активы</span>
          <span class="nav-i">Сделки</span>
          <span class="nav-i">Аналитика</span>
        </div>
      </aside>
      <div class="mock-main">
        <header class="mock-top">
          <span class="mock-greet">Добрый день 👋</span>
          <div class="mock-top-actions">
            <span class="pill">Поиск…</span>
            <span class="dot" />
          </div>
        </header>

        <div class="mock-grid">
          <div class="mock-card stat blue">
            <span class="stat-label">Капитал</span>
            <strong class="stat-val">{{ formatMoney(capital) }}</strong>
          </div>
          <div class="mock-card stat purple">
            <span class="stat-label">Доходность (год)</span>
            <strong class="stat-val">{{ profit.toFixed(1) }}%</strong>
          </div>
          <div class="mock-card chart-card">
            <div class="chart-head">
              <span>Динамика портфеля</span>
              <span class="chip">12 мес.</span>
            </div>
            <div class="chart-box">
              <Line :data="chartData" :options="chartOptions" />
            </div>
          </div>
        </div>

        <div class="mock-slots">
          <div v-for="n in 6" :key="n" class="slot" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mock {
  width: 100%;
  border-radius: 22px;
  background: #fff;
  box-shadow:
    0 0 0 1px rgba(15, 23, 42, 0.06),
    0 24px 64px rgba(15, 23, 42, 0.12),
    0 8px 24px rgba(15, 23, 42, 0.06);
  overflow: hidden;
}

.mock-inner {
  display: grid;
  grid-template-columns: 180px 1fr;
  min-height: 320px;
}

@media (max-width: 767px) {
  .mock-inner {
    grid-template-columns: 1fr;
  }
  .mock-side {
    display: none;
  }
}

.mock-side {
  padding: 20px 16px;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  border-right: 1px solid #e2e8f0;
}

.mock-logo {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #0f172a;
  margin-bottom: 20px;
}

.mock-logo span {
  color: #3b82f6;
}

.mock-side-h {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #94a3b8;
  margin: 0 0 10px;
}

.mock-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-i {
  font-size: 13px;
  padding: 8px 10px;
  border-radius: 10px;
  color: #64748b;
}

.nav-i.on {
  background: rgba(59, 130, 246, 0.12);
  color: #2563eb;
  font-weight: 600;
}

.mock-main {
  padding: 16px 18px 14px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: #fff;
}

.mock-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.mock-greet {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.02em;
}

.mock-top-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pill {
  font-size: 12px;
  color: #94a3b8;
  padding: 6px 12px;
  background: #f8fafc;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
}

.dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e2e8f0, #cbd5e1);
}

.mock-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto 1fr;
  gap: 10px;
  flex: 1;
  min-height: 0;
}

.stat {
  padding: 14px 16px;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stat.blue {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #fff;
}

.stat.purple {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  color: #fff;
}

.stat-label {
  font-size: 12px;
  opacity: 0.9;
  font-weight: 500;
}

.stat-val {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.chart-card {
  grid-column: 1 / -1;
  padding: 12px 14px;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  min-height: 200px;
  display: flex;
  flex-direction: column;
}

.chart-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.chip {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 999px;
  background: #fff;
  border: 1px solid #e2e8f0;
  color: #64748b;
}

.chart-box {
  flex: 1;
  min-height: 160px;
  position: relative;
}

.mock-slots {
  display: flex;
  gap: 8px;
  justify-content: center;
  padding-top: 4px;
}

.slot {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: #f1f5f9;
  border: 1px dashed #cbd5e1;
}

@media (max-width: 767px) {
  .mock-grid {
    grid-template-columns: 1fr;
  }
  .stat.purple {
    grid-row: auto;
  }
  .chart-card {
    min-height: 180px;
  }
  .chart-box {
    min-height: 140px;
  }
}
</style>
