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
    default: 60
  },
  /** 0…1 — доля точек слева (отрисовка «слева направо», лендинг) */
  drawProgress: {
    type: Number,
    default: 1
  },
  /** Горизонтали min/max и подписи справа (как на референсе) */
  showMinMaxGuides: {
    type: Boolean,
    default: false
  }
})

const chartCanvas = ref(null)
let chartInstance = null
let chartResizeObserver = null
/** Подхватывается плагином min/max до первого draw (в т.ч. при new Chart) */
let mlMinMaxPayload = null

function attachChartResizeObserver() {
  if (chartResizeObserver) {
    chartResizeObserver.disconnect()
    chartResizeObserver = null
  }
  const containerEl = chartCanvas.value?.closest('.chart-container')
  if (containerEl && typeof ResizeObserver !== 'undefined') {
    chartResizeObserver = new ResizeObserver(() => {
      chartInstance?.resize()
    })
    chartResizeObserver.observe(containerEl)
  }
  requestAnimationFrame(() => {
    chartInstance?.resize()
  })
}

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

const MIN_MAX_GUIDE_LINE = '#d1d5db'
const MIN_MAX_GUIDE_TEXT = '#94a3b8'

/** Линии на уровнях глобального min/max ряда и подписи «max: …» / «min: …» у правого края области графика */
const minMaxGuidePlugin = {
  id: 'minMaxGuides',
  beforeDraw(chart) {
    chart.$mlMinMax = mlMinMaxPayload
  },
  afterDraw(chart) {
    const mm = chart.$mlMinMax
    if (!mm?.format) return
    const { min: vMin, max: vMax, format } = mm
    if (typeof vMax !== 'number' || !Number.isFinite(vMax)) return

    const hasMinGuide = typeof vMin === 'number' && Number.isFinite(vMin)
    const { ctx, chartArea, scales } = chart
    const yScale = scales.y
    if (!chartArea || !yScale) return

    const max = vMax
    const maxP = yScale.getPixelForValue(max)
    const { top, bottom, left, right } = chartArea

    ctx.save()
    ctx.strokeStyle = MIN_MAX_GUIDE_LINE
    ctx.lineWidth = 1
    ctx.setLineDash([4, 4])
    ctx.font = `300 10px ${LABEL_FONT}`
    ctx.fillStyle = MIN_MAX_GUIDE_TEXT
    ctx.textAlign = 'right'

    const drawOne = (y, label, baseline, dy) => {
      const yy = Math.min(bottom, Math.max(top, y))
      ctx.beginPath()
      ctx.moveTo(left, yy)
      ctx.lineTo(right, yy)
      ctx.stroke()
      ctx.textBaseline = baseline
      ctx.fillText(label, right - 6, yy + dy)
    }

    if (!hasMinGuide) {
      const off = 5
      drawOne(maxP, `max: ${format(max)}`, 'bottom', -off)
      ctx.restore()
      return
    }

    const min = vMin
    const minP = yScale.getPixelForValue(min)
    const gap = Math.abs(maxP - minP)
    const tight = min !== max && gap < 22
    const off = tight ? 3 : 5

    if (min === max) {
      drawOne(maxP, `max: ${format(max)}`, 'bottom', -off)
    } else {
      drawOne(maxP, `max: ${format(max)}`, 'bottom', -off)
      drawOne(minP, `min: ${format(min)}`, 'top', off)
    }

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

/** Запасной вариант: равномерно по индексам (если даты не разобрать) */
function pickTickIndicesByIndex(length, cap) {
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

function labelTimeValid(labels, i) {
  try {
    const t = parseDate(labels[i]).getTime()
    return Number.isFinite(t) && !isNaN(t)
  } catch {
    return false
  }
}

function parseLabelTimes(labels) {
  const n = labels?.length ?? 0
  let lo = 0
  let hi = n - 1
  while (lo <= hi && !labelTimeValid(labels, lo)) lo++
  while (hi >= lo && !labelTimeValid(labels, hi)) hi--
  return { lo, hi, n }
}

/**
 * span = (m−1)·q + r, q = ⌊span/(m−1)⌋, 0 ≤ r < m−1.
 * Подбираем m ∈ [2, min(span+1, cap)], максимизируя m − k·r (k=2): сильнее штрафуем остаток,
 * но не отказываемся от почти полного бюджета меток ради r=0 (в отличие от сырого min r).
 * При равном score — больше m.
 */
function pickOptimalTickCount(span, cap) {
  const mMax = Math.min(span + 1, Math.max(2, cap))
  if (span <= 0 || mMax <= 2) return Math.max(1, Math.min(span + 1, mMax))
  const k = 2
  let bestM = 2
  let bestScore = -Infinity
  for (let m = 2; m <= mMax; m++) {
    const gaps = m - 1
    const q = Math.floor(span / gaps)
    const r = span - gaps * q
    const score = m - k * r
    if (score > bestScore || (score === bestScore && m > bestM)) {
      bestScore = score
      bestM = m
    }
  }
  return bestM
}

/**
 * Ровно m подписей: span = (m−1)·q + r, q = ⌊span/(m−1)⌋.
 * Остаток r делим пополам: отступ слева ⌊r/2⌋, справа ⌈r/2⌉ — первая подпись lo+⌊r/2⌋,
 * между подписями везде q, последняя hi−⌈r/2⌉ (= lo+⌊r/2⌋+(m−1)·q). При r=0 снова lo…hi с шагом q.
 */
function pickTickFixedIndexStep(lo, hi, maxLabels) {
  const set = new Set()
  const span = hi - lo
  if (span < 0) return set
  const mBudget = Math.min(maxLabels, span + 1)

  if (mBudget >= span + 1) {
    for (let i = lo; i <= hi; i++) set.add(i)
    return set
  }
  if (mBudget <= 1) {
    set.add(lo)
    return set
  }

  const m = pickOptimalTickCount(span, maxLabels)

  const gaps = m - 1
  const q = Math.floor(span / gaps)
  const r = span - q * gaps
  const leftInset = Math.floor(r / 2)
  const start = lo + leftInset
  for (let k = 0; k < m; k++) {
    set.add(start + k * q)
  }
  return set
}

function pickTickIndicesByTime(labels, cap) {
  const { lo, hi, n } = parseLabelTimes(labels)
  if (lo > hi) return new Set()

  const maxLabels = Math.max(2, Math.min(n, Math.max(2, cap)))

  if (maxLabels >= n) {
    const all = new Set()
    for (let i = 0; i < n; i++) all.add(i)
    return all
  }

  return pickTickFixedIndexStep(lo, hi, maxLabels)
}

/** Первый индекс каждого календарного месяца на [lo, hi] */
function collectMonthBoundaryIndices(labels, lo, hi) {
  const out = []
  let lastKey = null
  for (let i = lo; i <= hi; i++) {
    if (!labelTimeValid(labels, i)) continue
    const d = parseDate(labels[i])
    const key = d.getFullYear() * 12 + d.getMonth()
    if (key !== lastKey) {
      lastKey = key
      out.push(i)
    }
  }
  return out
}

/** Первый индекс каждого календарного года на [lo, hi] */
function collectYearBoundaryIndices(labels, lo, hi) {
  const out = []
  let lastY = null
  for (let i = lo; i <= hi; i++) {
    if (!labelTimeValid(labels, i)) continue
    const y = parseDate(labels[i]).getFullYear()
    if (y !== lastY) {
      lastY = y
      out.push(i)
    }
  }
  return out
}

/**
 * Подписи только по «якорям» (месяц или год), прореживание тем же pickTickFixedIndexStep по списку якорей.
 * Интервал по умолчанию 1 месяц/год; при нехватке cap с ширины — шаг растёт (меньше меток).
 */
function pickTicksFromCandidates(candidates, cap) {
  const set = new Set()
  if (candidates.length === 0) return set
  const L = candidates.length
  const maxLabels = Math.max(2, Math.min(L, Math.max(2, cap)))
  if (maxLabels >= L) {
    for (const idx of candidates) set.add(idx)
    return set
  }
  const posHi = L - 1
  const inner = pickTickFixedIndexStep(0, posHi, maxLabels)
  for (const p of inner) set.add(candidates[p])
  return set
}

function pickTickIndicesByMonth(labels, lo, hi, cap) {
  const c = collectMonthBoundaryIndices(labels, lo, hi)
  return pickTicksFromCandidates(c, cap)
}

function pickTickIndicesByYear(labels, lo, hi, cap) {
  const c = collectYearBoundaryIndices(labels, lo, hi)
  return pickTicksFromCandidates(c, cap)
}

/** <180 дн. — по индексу; [180,700) — по месяцам; ≥700 — по годам */
const SPAN_AXIS_DAY = 180
const SPAN_AXIS_MONTH_MAX = 700

function xAxisSpanBucket(spanDays) {
  if (spanDays < SPAN_AXIS_DAY) return 0
  if (spanDays < SPAN_AXIS_MONTH_MAX) return 1
  return 2
}

function getXTickIndexSetForSpan(labels, spanDays, chart, minPx) {
  const w = xAxisChartWidth(chart)
  const cap = Math.max(2, Math.floor(w / Math.max(24, minPx)))
  const { lo, hi } = parseLabelTimes(labels)
  if (lo > hi) return new Set()

  const bucket = xAxisSpanBucket(spanDays)
  if (bucket === 0) {
    return pickTickIndicesByTime(labels, cap)
  }
  if (bucket === 1) {
    return pickTickIndicesByMonth(labels, lo, hi, cap)
  }
  return pickTickIndicesByYear(labels, lo, hi, cap)
}

function xAxisChartWidth(chart) {
  const a = chart?.chartArea
  if (a && a.right > a.left) return a.right - a.left
  const w = chart?.width
  return typeof w === 'number' && w > 0 ? w * 0.72 : 280
}

/** После первого layout chartArea даёт реальную ширину; иначе кэш тиков считается по fallback и подсветка/метки неверны до ресайза */
const xTickRelayoutPlugin = {
  id: 'mlXTickRelayout',
  afterLayout(chart) {
    if (chart.$mlXTickRelayouting) return
    const labels = chart.data?.labels
    if (!labels?.length) return
    const w = xAxisChartWidth(chart)
    if (!(w > 0)) return
    const sig = chart.$mlXTickSig
    if (sig && Math.abs(sig.w - w) > 1) {
      chart.$mlXTickSig = null
      chart.$mlXTickSpan = undefined
      chart.$mlXTickRelayouting = true
      try {
        chart.update('none')
      } finally {
        chart.$mlXTickRelayouting = false
      }
    }
  }
}

function getXTickIndexSet(chart, labels, minPx, spanDays) {
  const byTime = getXTickIndexSetForSpan(labels, spanDays, chart, minPx)
  if (byTime.size > 0) return byTime
  const w = xAxisChartWidth(chart)
  const cap = Math.max(2, Math.floor(w / Math.max(24, minPx)))
  return pickTickIndicesByIndex(labels?.length ?? 0, cap)
}

/**
 * <180 дн. — при смене месяца/года относительно предыдущей видимой метки только месяц, иначе день+месяц;
 * [180,700) — см. sortedTickIndices; ≥700 — только год.
 */
function formatXAxisDateLabel(labels, index, d, spanDays, sortedTickIndices) {
  const sm = shortMonth(d)
  const y = d.getFullYear()
  const day = d.getDate()
  if (spanDays < SPAN_AXIS_DAY) {
    if (!sortedTickIndices?.length) return `${day} ${sm}`
    const pos = sortedTickIndices.indexOf(index)
    if (pos <= 0) return day === 1 ? sm : `${day} ${sm}`
    let p
    try {
      p = parseDate(labels[sortedTickIndices[pos - 1]])
      if (isNaN(p.getTime())) return `${day} ${sm}`
    } catch {
      return `${day} ${sm}`
    }
    if (p.getMonth() !== d.getMonth() || p.getFullYear() !== d.getFullYear()) return sm
    return `${day} ${sm}`
  }
  if (spanDays < SPAN_AXIS_MONTH_MAX) {
    if (!sortedTickIndices?.length) return sm
    const pos = sortedTickIndices.indexOf(index)
    if (pos <= 0) return sm
    let p
    try {
      p = parseDate(labels[sortedTickIndices[pos - 1]])
      if (isNaN(p.getTime())) return sm
    } catch {
      return sm
    }
    if (p.getFullYear() !== d.getFullYear()) return String(y)
    return sm
  }
  return String(y)
}

/** Подсветка соседних показанных тиков в зависимости от режима оси */
function computeXTickEmphasis(labels, tickIndices, spanDays) {
  const emphasis = new Set()
  const sorted = Array.from(tickIndices).sort((a, b) => a - b)
  for (let i = 1; i < sorted.length; i++) {
    const idx = sorted[i]
    const prevIdx = sorted[i - 1]
    let d
    let p
    try {
      d = new Date(labels[idx])
      p = new Date(labels[prevIdx])
      if (isNaN(d.getTime()) || isNaN(p.getTime())) continue
    } catch {
      continue
    }
    if (spanDays < SPAN_AXIS_DAY) {
      if (spanDays <= 120) {
        if (d.getMonth() !== p.getMonth() || d.getFullYear() !== p.getFullYear()) emphasis.add(idx)
      } else if (d.getFullYear() !== p.getFullYear()) {
        emphasis.add(idx)
      }
    } else if (spanDays < SPAN_AXIS_MONTH_MAX) {
      if (d.getFullYear() !== p.getFullYear()) emphasis.add(idx)
    } else if (Math.floor(d.getFullYear() / 10) !== Math.floor(p.getFullYear() / 10)) {
      emphasis.add(idx)
    }
  }
  return emphasis
}

function spanDaysForLabels(labels) {
  if (!labels?.length) return 0
  const { lo, hi } = parseLabelTimes(labels)
  if (lo > hi) return 0
  try {
    const first = parseDate(labels[lo])
    const last = parseDate(labels[hi])
    if (isNaN(first.getTime()) || isNaN(last.getTime())) return 0
    return (last - first) / 86400000
  } catch {
    return 0
  }
}

function ensureXTickCache(chart, labels, minPx) {
  if (!labels?.length) return
  const w = xAxisChartWidth(chart)
  const span = spanDaysForLabels(labels)
  const spanBucket = xAxisSpanBucket(span)
  const sig = chart.$mlXTickSig
  if (
    !sig ||
    sig.n !== labels.length ||
    sig.w !== w ||
    sig.minPx !== minPx ||
    sig.spanBucket !== spanBucket
  ) {
    chart.$mlXTickSet = getXTickIndexSet(chart, labels, minPx, span)
    chart.$mlXTickSorted = Array.from(chart.$mlXTickSet).sort((a, b) => a - b)
    chart.$mlXTickEmphasis = computeXTickEmphasis(labels, chart.$mlXTickSet, span)
    chart.$mlXTickSpan = span
    chart.$mlXTickSig = { n: labels.length, w, minPx, spanBucket }
  }
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

/**
 * Полная ось X с первого кадра: все метки остаются, «непрорисованный» хвост — null.
 * Линия и заливка растут слева направо без появления новых подписей по мере прогресса.
 */
function maskAggregatedSeriesByProgress(aggr, progress) {
  const p = Math.max(0, Math.min(1, progress))
  if (p >= 1 || !aggr?.labels?.length) return aggr
  const n = aggr.labels.length
  if (p <= 0) {
    return {
      labels: aggr.labels.slice(),
      datasets: aggr.datasets.map((arr) => arr.map(() => null))
    }
  }
  const cut = Math.min(n, Math.max(2, Math.ceil(n * p)))
  return {
    labels: aggr.labels.slice(),
    datasets: aggr.datasets.map((arr) => arr.map((v, i) => (i < cut ? v : null)))
  }
}

/* --------------------------------------------------------------------------
   Render
-------------------------------------------------------------------------- */
/** boundsAggr — полный ряд для min/max по Y при анимации drawProgress (ось не «прыгает») */
const renderChart = (aggr, boundsAggr = null) => {
  const ctx = chartCanvas.value?.getContext('2d')
  if (!ctx) return

  const boundSrc = boundsAggr && props.drawProgress < 1 ? boundsAggr : aggr
  const allValues = boundSrc.datasets
    .flat()
    .filter((v) => typeof v === 'number' && Number.isFinite(v))
  const minValue = allValues.length ? Math.min(...allValues) : 0
  const maxValue = allValues.length ? Math.max(...allValues) : 100
  const range = maxValue - minValue

  const positiveValues = allValues.filter((v) => v > 0)
  const guideMinPositive = positiveValues.length ? Math.min(...positiveValues) : null

  mlMinMaxPayload =
    props.showMinMaxGuides && allValues.length
      ? {
          min: guideMinPositive,
          max: maxValue,
          format: (v) => {
            try {
              return props.formatCurrency(v)
            } catch {
              return String(v)
            }
          }
        }
      : null

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
      spanGaps: props.drawProgress < 1 ? false : (ds.spanGaps ?? false)
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
    chartInstance.$mlXTickSpan = undefined
    chartInstance.data.labels = aggr.labels
    chartInstance.data.datasets = datasets
    chartInstance.options.scales.y.min = yMin
    chartInstance.options.scales.y.max = yMax
    chartInstance.options.plugins.tooltip.callbacks = { ...props.tooltipCallbacks }
    if (props.drawProgress < 1) chartInstance.update('none')
    else chartInstance.update()
    requestAnimationFrame(() => chartInstance?.resize())
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
    plugins: [crosshairPlugin, xTickRelayoutPlugin, minMaxGuidePlugin],
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation:
        props.drawProgress < 1 ? false : aggr.labels.length > 200 ? false : { duration: 400 },
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
            color: (ctx) => {
              const chart = ctx.chart
              const labels = chart?.data?.labels
              if (!labels?.length) return LABEL_COLOR
              ensureXTickCache(chart, labels, props.minPxPerXTick)
              return chart.$mlXTickEmphasis?.has(ctx.index) ? LABEL_COLOR_BOLD : LABEL_COLOR
            },
            font: (ctx) => {
              const chart = ctx.chart
              const labels = chart?.data?.labels
              let bold = false
              if (labels?.length) {
                ensureXTickCache(chart, labels, props.minPxPerXTick)
                bold = !!chart.$mlXTickEmphasis?.has(ctx.index)
              }
              return {
                size: 11,
                family: LABEL_FONT,
                weight: bold ? '500' : '300'
              }
            },
            autoSkip: false,
            maxRotation: 0,
            minRotation: 0,
            padding: 8,

            callback: function (_value, index) {
              const chart = this.chart
              const labels = chart.data.labels
              if (!labels || index >= labels.length) return ''

              ensureXTickCache(chart, labels, props.minPxPerXTick)
              if (!chart.$mlXTickSet.has(index)) return ''

              let d
              try {
                d = parseDate(labels[index])
                if (isNaN(d.getTime())) return ''
              } catch {
                return ''
              }

              return formatXAxisDateLabel(
                labels,
                index,
                d,
                chart.$mlXTickSpan ?? 0,
                chart.$mlXTickSorted
              )
            }
          }
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
  const aggrRaw = props.skipAggregation
    ? prepareRawSeries(props.chartData)
    : aggregateData(
        props.chartData,
        props.period,
        props.chartType,
        props.zeroAtStart,
        props.aggregationEnd
      )
  const aggr = maskAggregatedSeriesByProgress(aggrRaw, props.drawProgress)
  renderChart(aggr, aggrRaw)
}

watch(() => props.chartData, update, { deep: true })
watch(() => props.period, update)
watch(() => props.aggregationEnd, update)
watch(() => props.skipAggregation, update)
watch(() => props.minPxPerXTick, update)
watch(() => props.drawProgress, update)
watch(() => props.showMinMaxGuides, update)
watch(() => props.tooltipCallbacks, update, { deep: true })

onMounted(update)

onUnmounted(() => {
  chartResizeObserver?.disconnect()
  chartResizeObserver = null
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
})
</script>

<template>
  <div class="chart-container">
    <div class="chart-wrapper">
      <canvas ref="chartCanvas"></canvas>
    </div>
  </div>
</template>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 0;
  flex: 1 1 auto;
  position: relative;
  display: flex;
  flex-direction: column;
}
.chart-wrapper {
  width: 100%;
  flex: 1 1 auto;
  min-height: 0;
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
