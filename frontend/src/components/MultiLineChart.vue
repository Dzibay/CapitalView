<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import {
  Chart,
  LineElement,
  PointElement,
  LineController,
  CategoryScale,
  LinearScale,
  Filler,
  Tooltip,
  Legend
} from 'chart.js'

Chart.register(LineElement, PointElement, LineController, CategoryScale, LinearScale, Filler, Tooltip, Legend)

const props = defineProps({
  chartData: {
    type: Object,
    required: true
  },
  period: {
    type: String,
    default: "All"
  },
  chartType: {
    type: String,
    default: null
  },
  formatCurrency: {
    type: Function,
    default: (x) => x
  }
})

const chartCanvas = ref(null)
let chartInstance = null

const LABEL_FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif"
const LABEL_COLOR = '#94a3b8'
const LABEL_COLOR_BOLD = '#64748b'

function isBoundaryTick(labels, index) {
  if (!labels || index <= 0 || index >= labels.length) return false
  try {
    const d = new Date(labels[index])
    const p = new Date(labels[index - 1])
    const f = new Date(labels[0])
    const l = new Date(labels[labels.length - 1])
    if ([d, p, f, l].some(x => isNaN(x.getTime()))) return false
    const totalDays = (l - f) / 86400000
    // Day labels → bold month transitions
    if (totalDays <= 100) return d.getMonth() !== p.getMonth()
    // Month labels → bold year transitions only
    if (totalDays <= 1825) return d.getFullYear() !== p.getFullYear()
    // Year labels → no bolding
    return false
  } catch { return false }
}

/* --------------------------------------------------------------------------
   Helpers
-------------------------------------------------------------------------- */
const norm = (date) => {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  d.setMilliseconds(0)
  return d
}

const parseDate = (d) => {
  if (typeof d === 'string') {
    const parts = d.split('T')[0].split('-')
    if (parts.length === 3)
      return norm(new Date(+parts[0], +parts[1] - 1, +parts[2]))
  }
  return norm(new Date(d))
}

const fmtDate = (date) => {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const shortMonth = (date) => {
  const m = date.toLocaleString('ru-RU', { month: 'short' }).replace('.', '')
  return m.charAt(0).toUpperCase() + m.slice(1)
}

/* --------------------------------------------------------------------------
   Adaptive data aggregation with interval-based sampling

   Data point intervals (determines chart resolution):
     ≤ 400 days  → daily
     401–3650    → weekly  (every 7 days)
     > 3650      → monthly (1st of each month)
-------------------------------------------------------------------------- */
function aggregateData(dataObj, period, chartType) {
  if (!dataObj?.labels?.length) return { labels: [], datasets: [] }

  const today = new Date()
  const numDS = dataObj.datasets.length

  const points = dataObj.labels.map((lbl, i) => ({
    date: parseDate(lbl),
    values: dataObj.datasets.map(ds => ds.data[i])
  })).sort((a, b) => a.date - b.date)

  if (!points.length) return { labels: [], datasets: Array.from({ length: numDS }, () => []) }

  const firstPt = points[0].date
  const needsZero = chartType !== 'price'

  let start
  if (period === '1M') {
    start = norm(new Date(today.getFullYear(), today.getMonth(), today.getDate() - 30))
  } else if (period === '1Y') {
    start = norm(new Date(today.getFullYear(), today.getMonth() - 11, 1))
  } else {
    start = new Date(firstPt)
    if (needsZero) start.setDate(start.getDate() - 1)
    start = norm(start)
  }

  const end = norm(today)
  const totalDays = Math.round((end - start) / 86400000)

  const samples = []

  if (needsZero && start.getTime() < firstPt.getTime()) {
    samples.push({ date: new Date(start), zero: true })
  }

  const dataStart = norm(new Date(Math.max(start.getTime(), firstPt.getTime())))

  if (totalDays <= 400) {
    let d = new Date(dataStart)
    while (d <= end) {
      samples.push({ date: new Date(d), zero: false })
      d.setDate(d.getDate() + 1)
      d = norm(d)
    }
  } else if (totalDays <= 3650) {
    let d = new Date(dataStart)
    while (d <= end) {
      samples.push({ date: new Date(d), zero: false })
      d.setDate(d.getDate() + 7)
      d = norm(d)
    }
    const last = samples[samples.length - 1]
    if (last && last.date.getTime() !== end.getTime())
      samples.push({ date: new Date(end), zero: false })
  } else {
    samples.push({ date: new Date(dataStart), zero: false })
    let d = new Date(dataStart.getFullYear(), dataStart.getMonth() + 1, 1)
    d = norm(d)
    while (d <= end) {
      samples.push({ date: new Date(d), zero: false })
      d = new Date(d.getFullYear(), d.getMonth() + 1, 1)
      d = norm(d)
    }
    const last = samples[samples.length - 1]
    if (last && last.date.getTime() !== end.getTime())
      samples.push({ date: new Date(end), zero: false })
  }

  const labels = []
  const bufs = Array.from({ length: numDS }, () => [])
  let pi = 0
  let cur = new Array(numDS).fill(0)

  for (const s of samples) {
    const ts = s.date.getTime()
    while (pi < points.length && points[pi].date.getTime() <= ts) {
      cur = points[pi].values.map(v => v ?? 0)
      pi++
    }
    if (s.zero) {
      bufs.forEach(arr => arr.push(0))
    } else {
      bufs.forEach((arr, i) => arr.push(cur[i]))
    }
    labels.push(fmtDate(s.date))
  }

  return { labels, datasets: bufs }
}

/* --------------------------------------------------------------------------
   Y-axis helpers
-------------------------------------------------------------------------- */
function getNiceMax(value) {
  if (value <= 0) return 100
  const padded = value * 1.1
  const order = Math.floor(Math.log10(padded))
  let step
  if (order < 0) step = Math.pow(10, order) * 5
  else if (order === 0) step = 5
  else if (order === 1) step = 10
  else step = 5 * 10 ** (order - 1)
  const r = Math.ceil(padded / step) * step
  return r < padded ? r + step : r
}

function getNiceMin(value) {
  if (value >= 0) return 0
  const padded = value * 1.1
  const order = Math.floor(Math.log10(Math.abs(padded)))
  let step
  if (order < 0) step = Math.pow(10, order) * 5
  else if (order === 0) step = 5
  else if (order === 1) step = 10
  else if (order === 2) step = 50
  else if (order === 3) step = 500
  else if (order === 4) step = 5000
  else if (order === 5) step = 50000
  else step = Math.pow(10, order) * 1.2
  const r = Math.floor(padded / step) * step
  return r > padded ? r - step : r
}

/* --------------------------------------------------------------------------
   Render
-------------------------------------------------------------------------- */
const renderChart = (aggr) => {
  const ctx = chartCanvas.value?.getContext('2d')
  if (!ctx) return

  const allValues = aggr.datasets.flat()
  const minValue = allValues.length ? Math.min(...allValues) : 0
  const maxValue = allValues.length ? Math.max(...allValues) : 100
  const range = maxValue - minValue

  let yMin, yMax

  if (props.period === 'All') {
    yMin = minValue < 0 ? getNiceMin(minValue) : 0
    yMax = getNiceMax(maxValue)
  } else {
    const pad = range > 0 ? range * 0.15 : Math.max(1, Math.abs(maxValue) * 0.05)
    const rng = (maxValue + pad) - (minValue - pad)
    const rOrder = rng > 0 ? Math.floor(Math.log10(rng)) : 0
    let step
    if (rOrder < 0) step = Math.pow(10, rOrder) * 5
    else if (rOrder === 0) step = 1
    else if (rOrder === 1) step = 10
    else if (rOrder === 2) step = 100
    else if (rOrder === 3) step = 1000
    else step = Math.pow(10, rOrder - 1) * 5
    yMin = Math.floor((minValue - pad) / step) * step
    yMax = Math.ceil((maxValue + pad) / step) * step
    if (minValue >= 0 && yMin < 0) yMin = 0
  }

  const datasets = props.chartData.datasets.map((ds, i) => {
    const base = {
      label: ds.label,
      data: aggr.datasets[i],
      borderColor: ds.color,
      borderWidth: i === 0 ? 3 : 2,
      tension: i === 0 ? 0.4 : 0.35,
      pointRadius: 0,
      pointHoverRadius: i === 0 ? 6 : 4,
      pointBackgroundColor: ds.color,
      pointBorderColor: '#fff',
      pointBorderWidth: 2
    }
    if (ds.fill) {
      base.fill = true
      base.backgroundColor = (context) => {
        const { ctx: c, chartArea } = context.chart
        if (!chartArea) return null
        const g = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
        g.addColorStop(0, ds.color + '33')
        g.addColorStop(1, ds.color + '00')
        return g
      }
    } else {
      base.fill = false
    }
    return base
  })

  if (chartInstance) {
    chartInstance.data.labels = aggr.labels
    chartInstance.data.datasets = datasets
    chartInstance.options.scales.y.min = yMin
    chartInstance.options.scales.y.max = yMax
    chartInstance.update()
    return
  }

  const existing = Chart.getChart(ctx)
  if (existing) existing.destroy()

  const css = (v) =>
    typeof window !== 'undefined'
      ? getComputedStyle(document.documentElement).getPropertyValue(v).trim() || '#e5e7eb'
      : '#e5e7eb'

  const axisGrid = css('--axis-grid') || '#e5e7eb'

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: { labels: aggr.labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: aggr.labels.length > 200 ? false : { duration: 400 },
      transitions: {
        active: { animation: { duration: 120 } }
      },
      interaction: { mode: 'index', intersect: false },

      scales: {
        y: {
          min: yMin,
          max: yMax,
          grid: { color: axisGrid, drawBorder: false, lineWidth: 1, drawTicks: false, tickLength: 0 },
          border: { display: false },
          ticks: {
            callback: v => {
              const a = Math.abs(v)
              if (a >= 1e6) { const m = v / 1e6; return `${m % 1 === 0 ? m.toFixed(0) : m.toFixed(1)}M` }
              if (a >= 1e3) { const k = v / 1e3; return `${Math.abs(k) % 1 === 0 ? k.toFixed(0) : k.toFixed(1)}K` }
              return v.toString()
            },
            color: LABEL_COLOR,
            font: { size: 11, family: LABEL_FONT, weight: '300' },
            padding: 10,
            maxTicksLimit: 8
          }
        },

        x: {
          type: 'category',
          grid: { display: false, drawBorder: false },
          border: { display: false },
          ticks: {
            color: (ctx) => isBoundaryTick(ctx.chart?.data?.labels, ctx.index) ? LABEL_COLOR_BOLD : LABEL_COLOR,
            font: (ctx) => ({
              size: 11,
              family: LABEL_FONT,
              weight: isBoundaryTick(ctx.chart?.data?.labels, ctx.index) ? '500' : '300'
            }),
            autoSkip: false,
            maxRotation: 0,
            minRotation: 0,
            padding: 8,

            callback: function (_value, index) {
              const labels = this.chart.data.labels
              if (!labels || index >= labels.length) return ''

              let d
              try { d = new Date(labels[index]); if (isNaN(d.getTime())) return '' }
              catch { return '' }

              const prev = index > 0
                ? (() => { try { const p = new Date(labels[index - 1]); return isNaN(p.getTime()) ? null : p } catch { return null } })()
                : null

              const first = (() => { try { const f = new Date(labels[0]); return isNaN(f.getTime()) ? null : f } catch { return null } })()
              const last = (() => { try { const l = new Date(labels[labels.length - 1]); return isNaN(l.getTime()) ? null : l } catch { return null } })()
              if (!first || !last) return ''

              const totalDays = (last - first) / 86400000
              const sm = shortMonth(d)
              const dm = `${d.getDate()} ${sm}`
              const monthYr = `${sm}'${String(d.getFullYear()).slice(2)}`
              const isLast = index === labels.length - 1
              const monthChanged = prev && d.getMonth() !== prev.getMonth()

              // ≤ 7 days (week): every day, skip last
              if (totalDays <= 7) {
                if (isLast) return ''
                if (monthChanged) return monthYr
                return dm
              }

              // ≤ 45 days (~month): every 2 days from end, skip last
              // Month boundary always shown as "Мес'ГГ"
              if (totalDays <= 45) {
                if (isLast) return ''
                if (monthChanged) return monthYr
                const diff = labels.length - 1 - index
                return diff % 2 === 1 ? dm : ''
              }

              // ≤ 100 days (~3 months): 1st (as Мес'ГГ) and 15th (as D Мес)
              if (totalDays <= 100) {
                if (monthChanged) return monthYr
                if (d.getDate() === 15) return dm
                if (index === 0 && d.getDate() <= 7) return dm
                return ''
              }

              // ≤ 500 days (~year): monthly, year on boundary
              if (totalDays <= 500) {
                if (index === 0 && d.getDate() <= 7) return sm
                if (!prev) return ''
                if (d.getFullYear() !== prev.getFullYear()) return d.getFullYear().toString()
                if (monthChanged) return sm
                return ''
              }

              // ≤ 1825 days (~5 years): every 6 months
              if (totalDays <= 1825) {
                if (index === 0) return d.getFullYear().toString()
                if (!prev) return ''
                if (d.getFullYear() !== prev.getFullYear()) return d.getFullYear().toString()
                if (monthChanged && (d.getMonth() === 0 || d.getMonth() === 6)) return sm
                return ''
              }

              // > 5 years: yearly (dynamic step for ≤ 12 labels)
              const totalYears = totalDays / 365
              const yearStep = totalYears > 12 ? Math.ceil(totalYears / 10) : 1

              if (index === 0) return d.getFullYear().toString()
              if (!prev) return ''
              if (d.getFullYear() !== prev.getFullYear()) {
                if ((d.getFullYear() - first.getFullYear()) % yearStep === 0)
                  return d.getFullYear().toString()
              }
              return ''
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
          titleFont: { weight: '500', family: LABEL_FONT },
          bodyFont: { size: 13, family: LABEL_FONT },
          padding: 12,
          cornerRadius: 6,
          displayColors: false,
          animation: {
            duration: 150,
            easing: 'easeOutQuart'
          },
          callbacks: {
            beforeBody(items) { items.sort((a, b) => b.parsed.y - a.parsed.y) },
            title: (ctx) => ctx[0].label,
            label: (ctx) => `${ctx.dataset.label}: ${props.formatCurrency(ctx.parsed.y)}`
          }
        }
      }
    }
  })
}

/* -------------------------------------------------------------------------- */
const update = () => {
  const aggr = aggregateData(props.chartData, props.period, props.chartType)
  renderChart(aggr)
}

watch(() => props.chartData, update, { deep: true })
watch(() => props.period, update)

onMounted(update)

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
})
</script>

<template>
  <div class="chart-container">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  position: relative;
}
</style>
