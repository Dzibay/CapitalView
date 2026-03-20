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
  // Явное управление добавлением "нулевой" точки в начало истории.
  // Если не задано — поведение как раньше: не добавляем для `chartType === 'price'`.
  zeroAtStart: {
    type: Boolean
  },
  formatCurrency: {
    type: Function,
    default: (x) => x
  },
  /** 'today' — как раньше; 'lastPoint' — ось до последней точки (прогнозы в будущее) */
  aggregationEnd: {
    type: String,
    default: 'today',
    validator: (v) => ['today', 'lastPoint'].includes(v)
  },
  /** Сливаются в plugins.tooltip.callbacks (Chart.js), внешний тултип берёт body отсюда */
  tooltipCallbacks: {
    type: Object,
    default: () => ({})
  },
  /** true — без дневной/недельной агрегации (нет «ступенек» между редкими точками) */
  skipAggregation: {
    type: Boolean,
    default: false
  },
  /** Мин. расстояние между подписями дат по X (px); от него и ширины графика считается число меток */
  minPxPerXTick: {
    type: Number,
    default: 52
  }
})

const chartCanvas = ref(null)
const chartWrapper = ref(null)
let chartInstance = null

const LABEL_FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif"
const LABEL_COLOR = '#94a3b8'
const LABEL_COLOR_BOLD = '#64748b'

/* --------------------------------------------------------------------------
   Crosshair plugin — vertical line at hovered point
-------------------------------------------------------------------------- */
const crosshairPlugin = {
  id: 'crosshair',
  afterDraw(chart) {
    const active = chart.tooltip?.getActiveElements()
    if (!active?.length) return
    const { ctx, chartArea } = chart
    const x = active[0].element.x
    ctx.save()
    ctx.beginPath()
    ctx.setLineDash([4, 4])
    ctx.lineWidth = 1
    ctx.strokeStyle = '#cbd5e1'
    ctx.moveTo(x, chartArea.top)
    ctx.lineTo(x, chartArea.bottom)
    ctx.stroke()
    ctx.restore()
  }
}

/* --------------------------------------------------------------------------
   Custom external tooltip with CSS transitions
-------------------------------------------------------------------------- */
function getOrCreateTooltip(wrapperEl) {
  let el = wrapperEl.querySelector('.chart-tooltip')
  if (!el) {
    el = document.createElement('div')
    el.className = 'chart-tooltip'
    wrapperEl.appendChild(el)
  }
  return el
}

function externalTooltipHandler(context) {
  const { chart, tooltip } = context
  const wrapper = chart.canvas.closest('.chart-wrapper')
  if (!wrapper) return

  const el = getOrCreateTooltip(wrapper)

  if (tooltip.opacity === 0) {
    el.style.opacity = '0'
    el.style.pointerEvents = 'none'
    return
  }

  // Build content
  const title = tooltip.title?.[0] || ''
  const lines = (tooltip.body || []).map(b => b.lines?.[0] || '')

  el.innerHTML = `
    <div class="chart-tooltip__title">${title}</div>
    ${lines.map(l => `<div class="chart-tooltip__line">${l}</div>`).join('')}
  `

  // Position
  const { offsetLeft, offsetTop } = chart.canvas
  const tipW = el.offsetWidth
  const tipH = el.offsetHeight
  let left = offsetLeft + tooltip.caretX
  let top = offsetTop + tooltip.caretY - tipH - 12

  // Keep within chart bounds
  if (left + tipW / 2 > chart.width) left = chart.width - tipW / 2
  if (left - tipW / 2 < 0) left = tipW / 2
  if (top < 0) top = offsetTop + tooltip.caretY + 12

  el.style.opacity = '1'
  el.style.left = `${left}px`
  el.style.top = `${top}px`
  el.style.pointerEvents = 'none'
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
    const trimmed = d.trim()
    const yearOnly = /^(\d{4})$/.exec(trimmed)
    if (yearOnly) return norm(new Date(+yearOnly[1], 11, 31))
    const parts = trimmed.split('T')[0].split('-')
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

/** Равномерно по оси индексов, всегда края; не больше cap меток */
function pickTickIndices(length, cap) {
  const set = new Set()
  if (length <= 0) return set
  const maxLabels = Math.max(2, Math.min(length, Math.max(2, cap)))
  if (maxLabels >= length) {
    for (let i = 0; i < length; i++) set.add(i)
    return set
  }
  for (let k = 0; k < maxLabels; k++) {
    set.add(Math.round((k * (length - 1)) / (maxLabels - 1)))
  }
  return set
}

function xAxisChartWidth(chart) {
  const a = chart?.chartArea
  if (a && a.right > a.left) return a.right - a.left
  const w = chart?.width
  return typeof w === 'number' && w > 0 ? w * 0.72 : 280
}

function getXTickIndexSet(chart, labelsLength, minPx) {
  const w = xAxisChartWidth(chart)
  const cap = Math.max(2, Math.floor(w / Math.max(24, minPx)))
  return pickTickIndices(labelsLength, cap)
}

/** Формат подписи только от длины интервала (дней между первой и последней точкой) */
function formatXAxisDateLabel(d, spanDays) {
  const sm = shortMonth(d)
  const y = d.getFullYear()
  const day = d.getDate()
  if (spanDays <= 21) return `${day} ${sm}`
  if (spanDays <= 120) return `${day} ${sm}`
  if (spanDays <= 540) return `${day} ${sm}`
  if (spanDays <= 1000) return `${sm} '${String(y).slice(2)}`
  if (spanDays <= 3600) return `${sm} ${y}`
  return String(y)
}

/* --------------------------------------------------------------------------
   Adaptive data aggregation with interval-based sampling
-------------------------------------------------------------------------- */
function aggregateData(dataObj, period, chartType, zeroAtStart, aggregationEnd = 'today') {
  if (!dataObj?.labels?.length) return { labels: [], datasets: [] }

  const today = new Date()
  const numDS = dataObj.datasets.length

  const points = dataObj.labels.map((lbl, i) => ({
    date: parseDate(lbl),
    values: dataObj.datasets.map(ds => ds.data[i])
  })).sort((a, b) => a.date - b.date)

  if (!points.length) return { labels: [], datasets: Array.from({ length: numDS }, () => []) }

  const firstPt = points[0].date
  const lastDataDate = points[points.length - 1].date
  const needsZero = (zeroAtStart !== undefined) ? zeroAtStart : (chartType !== 'price')

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

  const end =
    aggregationEnd === 'lastPoint' ? norm(lastDataDate) : norm(today)
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
      cur = points[pi].values.map((v) => {
        if (v === null || v === undefined) return null
        const n = Number(v)
        return Number.isFinite(n) ? n : 0
      })
      pi++
    }
    if (s.zero) {
      bufs.forEach(arr => arr.push(0))
    } else {
      bufs.forEach((arr, i) => {
        const val = cur[i]
        arr.push(val === null ? null : val)
      })
    }
    labels.push(fmtDate(s.date))
  }

  return { labels, datasets: bufs }
}

function prepareRawSeries(dataObj) {
  if (!dataObj?.labels?.length) return { labels: [], datasets: [] }
  const numDS = dataObj.datasets?.length ?? 0
  if (!numDS) return { labels: [], datasets: [] }
  const labels = dataObj.labels.map((lbl) => fmtDate(parseDate(lbl)))
  const datasets = dataObj.datasets.map((ds) =>
    (ds.data || []).map((v) => {
      if (v === null || v === undefined) return null
      const n = Number(v)
      return Number.isFinite(n) ? n : 0
    })
  )
  return { labels, datasets }
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

  const allValues = aggr.datasets
    .flat()
    .filter((v) => typeof v === 'number' && Number.isFinite(v))
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
    const lineColor = ds.color || ds.borderColor || '#5478EA'
    const base = {
      label: ds.label,
      data: aggr.datasets[i],
      borderColor: lineColor,
      borderWidth: ds.borderWidth ?? (i === 0 ? 3 : 2),
      tension: ds.tension ?? (i === 0 ? 0.4 : 0.35),
      pointRadius: ds.pointRadius ?? 0,
      pointHoverRadius: ds.pointHoverRadius ?? (i === 0 ? 5 : 3),
      pointHitRadius: ds.pointHitRadius ?? 8,
      pointBackgroundColor: ds.pointBackgroundColor ?? ds.backgroundColor ?? lineColor,
      pointBorderColor: ds.pointBorderColor ?? '#fff',
      pointHoverBorderWidth: ds.pointHoverBorderWidth ?? 2,
      pointBorderWidth: ds.pointBorderWidth ?? 0,
      spanGaps: ds.spanGaps ?? false
    }
    if (ds.order != null) base.order = ds.order
    if (ds.borderDash) base.borderDash = ds.borderDash
    if (ds.showLine === false) base.showLine = false
    if (ds.fill) {
      base.fill = true
      base.backgroundColor = (context) => {
        const { ctx: c, chartArea } = context.chart
        if (!chartArea) return null
        const g = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
        g.addColorStop(0, lineColor + '33')
        g.addColorStop(1, lineColor + '00')
        return g
      }
    } else {
      base.fill = false
    }
    return base
  })

  if (chartInstance) {
    chartInstance.$mlXTickSig = null
    chartInstance.data.labels = aggr.labels
    chartInstance.data.datasets = datasets
    chartInstance.options.scales.y.min = yMin
    chartInstance.options.scales.y.max = yMax
    chartInstance.options.plugins.tooltip.callbacks = { ...props.tooltipCallbacks }
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
    plugins: [crosshairPlugin],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: aggr.labels.length > 200 ? false : { duration: 400 },
      transitions: {
        active: {
          animation: { duration: 150, easing: 'easeOutCubic' }
        }
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

              if (totalDays <= 7) {
                if (isLast) return ''
                if (monthChanged) return monthYr
                return dm
              }

              if (totalDays <= 45) {
                if (isLast) return ''
                const diff = labels.length - 1 - index
                if (diff % 2 !== 1) return ''
                if (index >= 2) {
                  try {
                    const prevVisDate = new Date(labels[index - 2])
                    if (!isNaN(prevVisDate.getTime()) && d.getMonth() !== prevVisDate.getMonth())
                      return monthYr
                  } catch { /* пропускаем */ }
                }
                return dm
              }

              if (totalDays <= 100) {
                if (monthChanged) return monthYr
                if (d.getDate() === 15) return dm
                if (index === 0 && d.getDate() <= 7) return dm
                return ''
              }

              if (totalDays <= 500) {
                if (index === 0 && d.getDate() <= 7) return sm
                if (!prev) return ''
                if (d.getFullYear() !== prev.getFullYear()) return d.getFullYear().toString()
                if (monthChanged) return sm
                return ''
              }

              if (totalDays <= 1825) {
                if (index === 0) return d.getFullYear().toString()
                if (!prev) return ''
                if (d.getFullYear() !== prev.getFullYear()) return d.getFullYear().toString()
                if (monthChanged && (d.getMonth() === 0 || d.getMonth() === 6)) return sm
                return ''
              }

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
          enabled: false,
          mode: 'index',
          intersect: false,
          callbacks: { ...props.tooltipCallbacks },
          external: externalTooltipHandler
        }
      }
    }
  })
}

/* -------------------------------------------------------------------------- */
const update = () => {
  const aggr = props.skipAggregation
    ? prepareRawSeries(props.chartData)
    : aggregateData(
        props.chartData,
        props.period,
        props.chartType,
        props.zeroAtStart,
        props.aggregationEnd
      )
  renderChart(aggr)
}

watch(() => props.chartData, update, { deep: true })
watch(() => props.period, update)
watch(() => props.aggregationEnd, update)
watch(() => props.skipAggregation, update)
watch(() => props.tooltipCallbacks, update, { deep: true })

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
    <div ref="chartWrapper" class="chart-wrapper">
      <canvas ref="chartCanvas"></canvas>
    </div>
  </div>
</template>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  position: relative;
}
.chart-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
}
</style>

<style>
.chart-tooltip {
  position: absolute;
  transform: translateX(-50%);
  background: #1f2937;
  color: #fff;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  pointer-events: none;
  white-space: nowrap;
  opacity: 0;
  transition: left 150ms ease-out, top 150ms ease-out, opacity 120ms ease-out;
  z-index: 10;
}
.chart-tooltip__title {
  font-weight: 500;
  font-size: 12px;
  margin-bottom: 4px;
  color: #94a3b8;
}
.chart-tooltip__line {
  font-size: 13px;
  line-height: 1.4;
}
</style>
