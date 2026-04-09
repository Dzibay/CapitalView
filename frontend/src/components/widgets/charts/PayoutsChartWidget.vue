<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { HandCoins } from 'lucide-vue-next'
import BarChart from '../../charts/BarChart.vue'
import ChartVariantSelect from '../../base/ChartVariantSelect.vue'
import PeriodFilters from '../base/PeriodFilters.vue'
import Widget from '../base/Widget.vue'
import { PAYOUTS_FORECAST_OPACITY } from './payoutsForecastOpacity.js'
import { formatOperationAmount } from '../../../utils/formatCurrency'

const VALID_CURRENCY_CODES = [
  'RUB', 'USD', 'EUR', 'GBP', 'CNY', 'JPY', 'BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL'
]

function resolveCurrencyCode(raw) {
  if (!raw || typeof raw !== 'string') return 'RUB'
  const code = raw.trim().substring(0, 3).toUpperCase()
  return VALID_CURRENCY_CODES.includes(code) ? code : 'RUB'
}

/** monthKey: YYYY-MM; границы диапазона включительно по календарным дням */
const monthOverlapsRange = (monthKey, rangeStart, rangeEnd) => {
  const parts = monthKey.split('-')
  const y = parseInt(parts[0], 10)
  const m = parseInt(parts[1], 10)
  if (!y || !m) return false
  const mf = new Date(y, m - 1, 1)
  mf.setHours(0, 0, 0, 0)
  const ml = new Date(y, m, 0)
  ml.setHours(0, 0, 0, 0)
  return mf <= rangeEnd && ml >= rangeStart
}

/** Те же якоря, что у PortfolioChartWidget.getPeriodStartDate (чипы PeriodFilters) */
function getPeriodRangeStart(period) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  if (period === '7D') return new Date(today.getFullYear(), today.getMonth(), today.getDate() - 7)
  if (period === '1M') return new Date(today.getFullYear(), today.getMonth(), today.getDate() - 30)
  if (period === '3M') return new Date(today.getFullYear(), today.getMonth(), today.getDate() - 90)
  if (period === '6M') return new Date(today.getFullYear(), today.getMonth(), today.getDate() - 180)
  if (period === 'YTD') return new Date(today.getFullYear(), 0, 1)
  if (period === '1Y') return new Date(today.getFullYear(), today.getMonth() - 11, 1)
  if (period === '5Y') return new Date(today.getFullYear() - 5, today.getMonth(), today.getDate())
  return null
}

/** Для mode=future — правую границу от сегодня (симметрично окнам «назад») */
function getFuturePeriodEnd(period) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const end = new Date(today)
  if (period === '7D') end.setDate(end.getDate() + 7)
  else if (period === '1M') end.setDate(end.getDate() + 30)
  else if (period === '3M') end.setDate(end.getDate() + 90)
  else if (period === '6M') end.setDate(end.getDate() + 180)
  else if (period === 'YTD') {
    end.setTime(new Date(today.getFullYear(), 11, 31).getTime())
  } else if (period === '1Y') end.setFullYear(end.getFullYear() + 1)
  else if (period === '5Y') end.setFullYear(end.getFullYear() + 5)
  end.setHours(23, 59, 59, 999)
  return end
}

/** Совпадают с operation_type из get_cash_operations (CASE ot.name …) */
const OP_TYPE_DIVIDENDS = 'Дивиденды'
const OP_TYPE_COUPONS = 'Купоны'
const OP_TYPE_AMORT = 'Амортизация'

const props = defineProps({
  title: {
    type: String,
    default: 'Выплаты по месяцам'
  },
  payouts: {
    type: Array,
    default: () => []
  },
  /** ISO-код валюты сумм в данных (как у formatOperationAmount). По умолчанию RUB — дашборд/аналитика портфеля. */
  currency: {
    type: String,
    default: 'RUB'
  },
  // 'past' для полученных выплат, 'future' для будущих
  /** past / future — как раньше; all — без верхней границы по «сегодня» (удобно для актива: история + прогнозы) */
  mode: {
    type: String,
    default: 'past',
    validator: (value) => ['past', 'future', 'all'].includes(value)
  },
  /** Переход на /transactions: период + типы операций по фактическим выплатам в столбце */
  enableBarNavigation: {
    type: Boolean,
    default: false
  },
  /**
   * Частичное переопределение коэффициентов из payoutsForecastOpacity.js (PAYOUTS_FORECAST_OPACITY).
   * Пример: :forecast-opacity="{ futureMode: 0.45, allFutureBucket: 0.4 }"
   */
  forecastOpacity: {
    type: Object,
    default: null
  }
})

function formatPayoutAmount(value) {
  return formatOperationAmount(Number(value) || 0, resolveCurrencyCode(props.currency))
}

const router = useRouter()

const effectiveForecastOpacity = computed(() => {
  const o = props.forecastOpacity && typeof props.forecastOpacity === 'object' ? props.forecastOpacity : {}
  return {
    futureMode: o.futureMode ?? PAYOUTS_FORECAST_OPACITY.futureMode,
    allFutureBucket: o.allFutureBucket ?? PAYOUTS_FORECAST_OPACITY.allFutureBucket,
    allStraddleBucket: o.allStraddleBucket ?? PAYOUTS_FORECAST_OPACITY.allStraddleBucket
  }
})

const selectedPeriod = ref('1Y')
const selectedGrouping = ref('month')

const groupingOptions = [
  { value: 'month', label: 'По месяцам' },
  { value: 'quarter', label: 'По кварталам' },
  { value: 'year', label: 'По годам' }
]

// Фирменные цвета для типов выплат
const payoutColors = {
  dividends: '#2563eb',
  dividendsAlpha: 'rgba(37, 99, 235, 0.85)',
  dividendsHover: '#1d4ed8',
  dividendsDark: '#1e40af',
  coupons: '#06b6d4',
  couponsAlpha: 'rgba(6, 182, 212, 0.85)',
  couponsHover: '#0891b2',
  couponsDark: '#0e7490',
  amortizations: '#fb923c',
  amortizationsAlpha: 'rgba(251, 146, 60, 0.85)',
  amortizationsHover: '#f97316',
  amortizationsDark: '#ea580c'
}

/** Календарные границы bucket по подписи оси (YYYY-MM | YYYY-Qn | YYYY) */
function bucketCalendarRange(monthKey) {
  if (/^\d{4}-\d{2}$/.test(monthKey)) {
    const [y, m] = monthKey.split('-').map(Number)
    const start = new Date(y, m - 1, 1)
    start.setHours(0, 0, 0, 0)
    const end = new Date(y, m, 0)
    end.setHours(23, 59, 59, 999)
    return { start, end }
  }
  const qm = monthKey.match(/^(\d{4})-Q([1-4])$/)
  if (qm) {
    const y = parseInt(qm[1], 10)
    const q = parseInt(qm[2], 10)
    const startM = (q - 1) * 3 + 1
    const start = new Date(y, startM - 1, 1)
    start.setHours(0, 0, 0, 0)
    const end = new Date(y, startM + 2, 0)
    end.setHours(23, 59, 59, 999)
    return { start, end }
  }
  if (/^\d{4}$/.test(monthKey)) {
    const y = parseInt(monthKey, 10)
    const start = new Date(y, 0, 1)
    start.setHours(0, 0, 0, 0)
    const end = new Date(y, 11, 31)
    end.setHours(23, 59, 59, 999)
    return { start, end }
  }
  return null
}

/** 1 = факт; меньше 1 — прогноз (будущий период на шкале времени) */
function barForecastOpacityFactor(monthKey, mode, k) {
  if (mode === 'past') return 1
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const r = bucketCalendarRange(monthKey)
  if (!r) return 1
  if (mode === 'future') return k.futureMode
  if (r.end < today) return 1
  if (r.start > today) return k.allFutureBucket
  return k.allStraddleBucket
}

function scaleRgbaAlpha(color, factor) {
  if (typeof color !== 'string' || factor >= 0.999) return color
  const m = color.match(/^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)$/i)
  if (!m) return color
  const a = Math.min(1, parseFloat(m[4], 10) * factor)
  return `rgba(${m[1]}, ${m[2]}, ${m[3]}, ${a.toFixed(3)})`
}

function hexToRgba(hex, alpha) {
  const h = hex.replace('#', '')
  if (h.length !== 6) return hex
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha.toFixed(3)})`
}

/** Тултип, ось Y (через overrideOptions) и строка «Всего» — без округления до K/целых */
const payoutsBarChartOverrides = computed(() => ({
  scales: {
    y: {
      ticks: {
        callback: (value) => formatPayoutAmount(value)
      }
    }
  }
}))

const periodFilterBounds = computed(() => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const todayEnd = new Date(today)
  todayEnd.setHours(23, 59, 59, 999)
  const farEnd = new Date(2099, 11, 31)
  farEnd.setHours(23, 59, 59, 999)

  if (selectedPeriod.value === 'All') {
    return { periodAll: true, rangeStart: null, rangeEnd: null }
  }

  const p = selectedPeriod.value
  if (props.mode === 'past') {
    const rs = getPeriodRangeStart(p)
    if (!rs) return { periodAll: true, rangeStart: null, rangeEnd: null }
    rs.setHours(0, 0, 0, 0)
    return { periodAll: false, rangeStart: rs, rangeEnd: todayEnd }
  }
  if (props.mode === 'future') {
    const re = getFuturePeriodEnd(p)
    return { periodAll: false, rangeStart: today, rangeEnd: re }
  }
  const rs = getPeriodRangeStart(p)
  if (!rs) return { periodAll: true, rangeStart: null, rangeEnd: null }
  rs.setHours(0, 0, 0, 0)
  return { periodAll: false, rangeStart: rs, rangeEnd: farEnd }
})

// Фильтрация и группировка данных
const filteredPayouts = computed(() => {
  if (!props.payouts || !Array.isArray(props.payouts) || props.payouts.length === 0) {
    return []
  }

  const { periodAll, rangeStart, rangeEnd } = periodFilterBounds.value
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  let filtered = props.payouts.filter((p) => {
    if (!p || !p.month) return false
    try {
      const [year, month] = p.month.split('-')
      if (!year || !month) return false
      const payoutDate = new Date(parseInt(year, 10), parseInt(month, 10) - 1)
      payoutDate.setHours(0, 0, 0, 0)

      if (periodAll) {
        if (props.mode === 'past') return payoutDate <= today
        if (props.mode === 'future') return payoutDate >= today
        return true
      }

      if (!rangeStart || !rangeEnd) return false
      if (!monthOverlapsRange(p.month, rangeStart, rangeEnd)) return false

      if (props.mode === 'past') return payoutDate <= today
      if (props.mode === 'future') return payoutDate >= today
      return true
    } catch (e) {
      return false
    }
  })

  // Группировка по кварталам, если выбрано
  if (selectedGrouping.value === 'quarter') {
    const grouped = {}
    filtered.forEach(p => {
      if (!p.month) return
      try {
        const [year, month] = p.month.split('-')
        const quarter = Math.floor((parseInt(month) - 1) / 3) + 1
        const key = `${year}-Q${quarter}`
        
        if (!grouped[key]) {
          grouped[key] = {
            month: key,
            dividends: 0,
            coupons: 0,
            amortizations: 0
          }
        }
        
        grouped[key].dividends += Number(p.dividends) || 0
        grouped[key].coupons += Number(p.coupons) || 0
        grouped[key].amortizations += Number(p.amortizations) || 0
      } catch (e) {
        // Игнорируем ошибки
      }
    })
    
    return Object.values(grouped).sort((a, b) => {
      return a.month.localeCompare(b.month)
    })
  }

  if (selectedGrouping.value === 'year') {
    const grouped = {}
    filtered.forEach(p => {
      if (!p.month) return
      try {
        const ym = p.month.split('-')
        const y = ym[0]
        if (!y || !/^\d{4}$/.test(y)) return

        if (!grouped[y]) {
          grouped[y] = {
            month: y,
            dividends: 0,
            coupons: 0,
            amortizations: 0
          }
        }

        grouped[y].dividends += Number(p.dividends) || 0
        grouped[y].coupons += Number(p.coupons) || 0
        grouped[y].amortizations += Number(p.amortizations) || 0
      } catch (e) {
        // Игнорируем ошибки
      }
    })

    return Object.values(grouped).sort((a, b) => a.month.localeCompare(b.month))
  }

  return filtered
})

// Общая сумма выплат
const totalPayouts = computed(() => {
  return filteredPayouts.value.reduce((sum, p) => {
    return sum + (Number(p.dividends) || 0) + (Number(p.coupons) || 0) + (Number(p.amortizations) || 0)
  }, 0)
})

const chartLabels = computed(() => {
  return filteredPayouts.value.map(p => p.month) || []
})

const chartDatasets = computed(() => {
  if (!filteredPayouts.value || filteredPayouts.value.length === 0) {
    return []
  }

  const rows = filteredPayouts.value
  const opacityFactors = rows.map((p) =>
    barForecastOpacityFactor(p.month, props.mode, effectiveForecastOpacity.value)
  )

  const datasets = []

  // Дивиденды
  const dividends = rows.map((p) => Number(p.dividends) || 0)
  const dividendsSum = dividends.reduce((a, b) => a + b, 0)
  datasets.push({
    label: 'Дивиденды',
    data: dividends,
    backgroundColor: rows.map((p, i) =>
      scaleRgbaAlpha(payoutColors.dividendsAlpha, opacityFactors[i])
    ),
    borderColor: rows.map((p, i) =>
      hexToRgba(payoutColors.dividends, Math.min(1, 0.55 * opacityFactors[i] + 0.08))
    ),
    borderWidth: 0,
    hoverBackgroundColor: rows.map((p, i) =>
      hexToRgba(payoutColors.dividendsHover, Math.min(0.95, 0.88 * opacityFactors[i]))
    ),
    hoverBorderColor: rows.map((p, i) =>
      hexToRgba(payoutColors.dividendsDark, Math.min(1, 0.5 * opacityFactors[i] + 0.12))
    ),
    borderSkipped: false,
    totalSum: dividendsSum
  })

  // Купоны
  const coupons = rows.map((p) => Number(p.coupons) || 0)
  const couponsSum = coupons.reduce((a, b) => a + b, 0)
  datasets.push({
    label: 'Купоны',
    data: coupons,
    backgroundColor: rows.map((p, i) =>
      scaleRgbaAlpha(payoutColors.couponsAlpha, opacityFactors[i])
    ),
    borderColor: rows.map((p, i) =>
      hexToRgba(payoutColors.coupons, Math.min(1, 0.55 * opacityFactors[i] + 0.08))
    ),
    borderWidth: 0,
    hoverBackgroundColor: rows.map((p, i) =>
      hexToRgba(payoutColors.couponsHover, Math.min(0.95, 0.88 * opacityFactors[i]))
    ),
    hoverBorderColor: rows.map((p, i) =>
      hexToRgba(payoutColors.couponsDark, Math.min(1, 0.5 * opacityFactors[i] + 0.12))
    ),
    borderSkipped: false,
    totalSum: couponsSum
  })

  // Амортизации
  const amortizations = rows.map((p) => Number(p.amortizations) || 0)
  const amortizationsSum = amortizations.reduce((a, b) => a + b, 0)
  datasets.push({
    label: 'Амортизации',
    data: amortizations,
    backgroundColor: rows.map((p, i) =>
      scaleRgbaAlpha(payoutColors.amortizationsAlpha, opacityFactors[i])
    ),
    borderColor: rows.map((p, i) =>
      hexToRgba(payoutColors.amortizations, Math.min(1, 0.55 * opacityFactors[i] + 0.08))
    ),
    borderWidth: 0,
    hoverBackgroundColor: rows.map((p, i) =>
      hexToRgba(payoutColors.amortizationsHover, Math.min(0.95, 0.88 * opacityFactors[i]))
    ),
    hoverBorderColor: rows.map((p, i) =>
      hexToRgba(payoutColors.amortizationsDark, Math.min(1, 0.5 * opacityFactors[i] + 0.12))
    ),
    borderSkipped: false,
    totalSum: amortizationsSum
  })
  
  // Сортируем по сумме значений
  const sorted = datasets.sort((a, b) => a.totalSum - b.totalSum)
  
  // Применяем borderRadius только к верхнему слою (без закругления снизу)
  sorted.forEach((dataset, datasetIndex) => {
    const borderRadiusArray = dataset.data.map((value, dataIndex) => {
      if (value === 0) return 0
      
      let hasValueAbove = false
      for (let i = datasetIndex + 1; i < sorted.length; i++) {
        if (sorted[i].data[dataIndex] > 0) {
          hasValueAbove = true
          break
        }
      }
      
      return hasValueAbove ? 0 : 6
    })
    
    const firstValue = borderRadiusArray[0]
    const allSame = borderRadiusArray.every(br => br === firstValue)
    
    if (allSame) {
      if (firstValue > 0) {
        dataset.borderRadius = {
          topLeft: firstValue,
          topRight: firstValue,
          bottomLeft: 0,
          bottomRight: 0
        }
      } else {
        dataset.borderRadius = 0
      }
    } else {
      dataset.borderRadius = (ctx) => {
        const index = ctx.dataIndex
        const radius = borderRadiusArray[index] || 0
        if (radius > 0) {
          return {
            topLeft: radius,
            topRight: radius,
            bottomLeft: 0,
            bottomRight: 0
          }
        }
        return 0
      }
    }
  })
  
  return sorted
})

const payoutRowToOperationTypes = (row) => {
  const types = []
  if (Number(row.dividends) > 0) types.push(OP_TYPE_DIVIDENDS)
  if (Number(row.coupons) > 0) types.push(OP_TYPE_COUPONS)
  if (Number(row.amortizations) > 0) types.push(OP_TYPE_AMORT)
  return types
}

const onChartBarClick = ({ index }) => {
  if (!props.enableBarNavigation || props.mode !== 'past') return
  const row = filteredPayouts.value[index]
  if (!row?.month) return

  const query = { view: 'operations' }
  const opTypes = payoutRowToOperationTypes(row)
  if (opTypes.length === 1) {
    query.opType = opTypes[0]
  } else if (opTypes.length > 1) {
    query.opType = opTypes
  }

  if (/^\d{4}-\d{2}$/.test(row.month)) {
    query.month = row.month
  } else if (/^\d{4}-Q[1-4]$/.test(row.month)) {
    query.quarter = row.month
  } else if (/^\d{4}$/.test(row.month)) {
    query.year = row.month
  } else {
    return
  }

  router.push({ path: '/transactions', query })
}
</script>

<template>
  <Widget :title="title" :icon="HandCoins">
    <template #header>
      <ChartVariantSelect
        v-model="selectedGrouping"
        :options="groupingOptions"
      />
    </template>
    <template #subheader>
      <PeriodFilters v-model="selectedPeriod" />
    </template>

    <div class="total-amount">
      <span class="total-label">Всего</span>
      <span class="total-value">{{ formatPayoutAmount(totalPayouts) }}</span>
    </div>
    
    <div
      class="chart-container"
      :class="{ 'chart-container--clickable': enableBarNavigation && mode === 'past' }"
    >
      <BarChart
        v-if="filteredPayouts && filteredPayouts.length > 0"
        :labels="chartLabels"
        :datasets="chartDatasets"
        :stacked="true"
        :format-value="formatPayoutAmount"
        :override-options="payoutsBarChartOverrides"
        height="300px"
        :on-bar-click="enableBarNavigation && mode === 'past' ? onChartBarClick : null"
      />
      <div v-else class="empty-state">
        <p>{{ mode === 'future' ? 'Нет данных о будущих выплатах' : 'Нет данных о выплатах' }}</p>
      </div>
    </div>
  </Widget>
</template>

<style scoped>
.total-amount {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 1rem;
}

.total-label {
  font-size: var(--text-caption-size);
  color: var(--text-tertiary);
  font-weight: var(--text-body-secondary-weight);
}

.total-value {
  font-size: var(--text-value-size);
  font-weight: var(--text-value-weight);
  color: var(--text-primary);
}

.chart-container {
  height: 300px;
  position: relative;
}

.chart-container--clickable :deep(canvas) {
  cursor: pointer;
}

.empty-state {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--text-tertiary);
  font-size: var(--text-caption-size);
  background: white;
  z-index: 10;
}

.empty-state p {
  margin: 0;
}
</style>
