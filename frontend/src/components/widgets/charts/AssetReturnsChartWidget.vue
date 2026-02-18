<script setup>
import { computed, ref } from 'vue'
import BaseChart from '../../charts/BaseChart.vue'
import Widget from '../base/Widget.vue'
import DisplayModeToggle from '../base/DisplayModeToggle.vue'
import PeriodFilters from '../base/PeriodFilters.vue'
import EmptyState from '../base/EmptyState.vue'
import ToggleSwitch from '../../base/ToggleSwitch.vue'

const props = defineProps({
  assetReturns: {
    type: Array,
    default: () => []
  }
})

const selectedPeriod = ref('All') // 'All', '1Y', '1M'
const displayMode = ref('percent') // 'percent' или 'currency'
const showSoldAssets = ref(false) // Отображать проданные активы

const periodOptions = [
  { value: 'All', label: 'Все время' },
  { value: '1Y', label: 'Год' },
  { value: '1M', label: 'Месяц' }
]

const formatPercent = (value, withSign = true) => {
  const num = Number(value) || 0
  // Форматируем проценты
  const sign = num >= 0 ? (withSign ? '+' : '') : '-'
  if (Math.abs(num) < 0.1) {
    return `${sign}${Math.abs(num).toFixed(2)}%`
  } else if (Math.abs(num) < 1) {
    return `${sign}${Math.abs(num).toFixed(1)}%`
  } else {
    return `${sign}${Math.abs(Math.round(num))}%`
  }
}

// Форматирование для оси X (без знака "+", но с "-" для отрицательных)
const formatPercentAxis = (value) => {
  const num = Number(value) || 0
  const sign = num < 0 ? '-' : ''
  if (Math.abs(num) < 0.1) {
    return `${sign}${Math.abs(num).toFixed(2)}%`
  } else if (Math.abs(num) < 1) {
    return `${sign}${Math.abs(num).toFixed(1)}%`
  } else {
    return `${sign}${Math.abs(Math.round(num))}%`
  }
}

const formatMoney = (value) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  }).format(value || 0)
}

// Получаем данные за выбранный период
const getPeriodData = (asset) => {
  if (selectedPeriod.value === '1Y') {
    return {
      return_percent: Number(asset?.return_percent_year) || 0,
      total_return: Number(asset?.total_return_year) || 0,
      price_change: Number(asset?.price_change_year) || 0,
      realized_profit: Number(asset?.realized_profit_year) || 0,
      total_payouts: Number(asset?.total_payouts_year) || 0,
      invested_amount: Number(asset?.value_year_ago) || 0,
      current_value: Number(asset?.current_value) || 0
    }
  } else if (selectedPeriod.value === '1M') {
    return {
      return_percent: Number(asset?.return_percent_month) || 0,
      total_return: Number(asset?.total_return_month) || 0,
      price_change: Number(asset?.price_change_month) || 0,
      realized_profit: Number(asset?.realized_profit_month) || 0,
      total_payouts: Number(asset?.total_payouts_month) || 0,
      invested_amount: Number(asset?.value_month_ago) || 0,
      current_value: Number(asset?.current_value) || 0
    }
  } else {
    // Все время
    return {
      return_percent: Number(asset?.return_percent) || 0,
      total_return: Number(asset?.total_return) || 0,
      price_change: Number(asset?.price_change) || 0,
      realized_profit: Number(asset?.realized_profit) || 0,
      total_payouts: Number(asset?.total_payouts) || 0,
      invested_amount: Number(asset?.invested_amount) || 0,
      current_value: Number(asset?.current_value) || 0
    }
  }
}

// Функция для определения, является ли актив проданным
const isSoldAsset = (asset) => {
  const periodData = getPeriodData(asset)
  // Актив считается проданным, если current_value = 0 (current_quantity = 0)
  return (periodData.current_value || 0) === 0
}

// Сохраняем отсортированные активы для использования в tooltip
const sortedAssetsData = computed(() => {
  // Явно используем selectedPeriod, displayMode и showSoldAssets для отслеживания зависимостей
  const period = selectedPeriod.value
  const mode = displayMode.value
  const showSold = showSoldAssets.value
  const assetReturns = props.assetReturns || []
  
  if (!Array.isArray(assetReturns) || assetReturns.length === 0) {
    return []
  }
  
  // Получаем данные за выбранный период, фильтруем активы с нулевым итоговым показателем и сортируем по доходности
  const assetsWithPeriodData = [...assetReturns]
    .map(asset => ({
      ...asset,
      periodData: getPeriodData(asset),
      isSold: isSoldAsset(asset)
    }))
    .filter(asset => {
      // Если не показываем проданные активы, исключаем их
      if (!showSold && asset.isSold) {
        return false
      }
      
      // Исключаем активы с нулевым итоговым показателем в зависимости от режима отображения
      if (mode === 'currency') {
        // В режиме валюты фильтруем по total_return
        const totalReturn = asset.periodData.total_return || 0
        return Math.abs(totalReturn) > 0.01 // Учитываем погрешность округления
      } else {
        // В режиме процентов фильтруем по return_percent
        const returnPercent = asset.periodData.return_percent || 0
        return Math.abs(returnPercent) > 0.01 // Учитываем погрешность округления
      }
    })
  
  // Сортируем в зависимости от режима отображения
  return assetsWithPeriodData.sort((a, b) => {
    if (mode === 'currency') {
      // В режиме валюты сортируем по total_return
      const returnA = a.periodData.total_return || 0
      const returnB = b.periodData.total_return || 0
      return returnB - returnA
    } else {
      // В режиме процентов сортируем по return_percent
      const returnA = a.periodData.return_percent || 0
      const returnB = b.periodData.return_percent || 0
      return returnB - returnA
    }
  })
})

// Вычисляем динамическую высоту графика на основе количества активов
const chartHeight = computed(() => {
  const assetCount = sortedAssetsData.value.length
  if (assetCount === 0) {
    return '500px' // Минимальная высота
  }
  
  // Минимальная высота на один актив (включая отступы)
  const minHeightPerAsset = 17
  // Минимальная общая высота
  const minTotalHeight = 400
  // Вычисляем высоту: количество активов * высота на актив, но не меньше минимума
  const calculatedHeight = Math.max(minTotalHeight, assetCount * minHeightPerAsset)
  
  return `${calculatedHeight}px`
})

const chartData = computed(() => {
  if (sortedAssetsData.value.length === 0) {
    return { labels: [], datasets: [] }
  }
  
  const labels = sortedAssetsData.value.map(a => a?.asset_ticker || a?.asset_name || 'Unknown')
  
  // Определяем значения в зависимости от режима отображения и периода
  let values, signs
  if (displayMode.value === 'currency') {
    // В режиме валюты используем total_return за выбранный период
    values = sortedAssetsData.value.map(a => Math.abs(a.periodData.total_return || 0))
    signs = sortedAssetsData.value.map(a => {
      const returnValue = a.periodData.total_return || 0
      return returnValue >= 0
    })
  } else {
    // В режиме процентов используем return_percent за выбранный период
    values = sortedAssetsData.value.map(a => Math.abs(a.periodData.return_percent || 0))
    signs = sortedAssetsData.value.map(a => {
      const percent = a.periodData.return_percent || 0
      return percent >= 0
    })
  }
  
  return {
    labels,
    datasets: [
      {
        label: displayMode.value === 'currency' ? 'Прибыль' : 'Доходность',
        data: values,
        backgroundColor: signs.map(isPositive => isPositive ? 'rgba(16, 185, 129, 0.85)' : 'rgba(239, 68, 68, 0.85)'),
        borderColor: signs.map(isPositive => isPositive ? '#10b981' : '#ef4444'),
        borderWidth: 0,
        borderRadius: 4,
        maxBarThickness: 30,
        // Сохраняем исходные данные для использования в плагинах
        _originalData: sortedAssetsData.value
      }
    ]
  }
})

const chartOptions = computed(() => {
  // Получаем цвета из CSS переменных
  const getCSSVariable = (varName) => {
    if (typeof window !== 'undefined') {
      return getComputedStyle(document.documentElement).getPropertyValue(varName).trim() || '#6b7280'
    }
    return '#6b7280'
  }
  
  const axisText = getCSSVariable('--axis-text') || '#6b7280'
  const axisTextLight = getCSSVariable('--axis-text-light') || '#9ca3af'
  const axisGrid = getCSSVariable('--axis-grid') || '#e5e7eb'
  
  return {
    indexAxis: 'y', // Горизонтальная ориентация
    interaction: {
      mode: 'y', // Для горизонтальных баров используем только Y-ось
      intersect: false
    },
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        mode: 'y', // Для горизонтальных баров используем только Y-ось
        intersect: false,
        backgroundColor: 'rgba(31, 41, 55, 0.95)',
        titleColor: '#fff',
        bodyColor: '#fff',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
        displayColors: true,
        z: 1000, // Увеличиваем z-index для tooltip, чтобы он был поверх текста на графике
        callbacks: {
          title: (context) => {
            return context[0].label || ''
          },
          label: (context) => {
            const chart = context.chart
            const index = context.dataIndex
            
            // Получаем исходные данные из dataset
            const originalData = chart.data.datasets[0]._originalData || []
            const asset = originalData[index]
            
            if (!asset || !asset.periodData) return []
            
            const periodData = asset.periodData
            const returnPercent = periodData.return_percent || 0
            const totalReturn = periodData.total_return || 0
            const priceChange = periodData.price_change || 0
            const realizedProfit = periodData.realized_profit || 0
            const totalPayouts = periodData.total_payouts || 0
            const investedAmount = periodData.invested_amount || 0
            const currentValue = periodData.current_value || 0
            
            const periodLabel = selectedPeriod.value === '1Y' ? ' (за год)' : 
                               selectedPeriod.value === '1M' ? ' (за месяц)' : ' (все время)'
            
            // Получаем комиссии из данных актива (если есть)
            const totalCommissions = Number(asset?.total_commissions || asset?.total_commissions_all || asset?.total_commissions_year || asset?.total_commissions_month || 0)
            
            const labels = [
              `Доходность${periodLabel}: ${formatPercent(returnPercent)}`,
              '',
              'Состав прибыли:',
              `  Общая прибыль: ${formatMoney(totalReturn)}`,
              `  Нереализованная прибыль: ${formatMoney(priceChange)}`,
              `  Реализованная прибыль: ${formatMoney(realizedProfit)}`,
              `  Выплаты: ${formatMoney(totalPayouts)}`,
              totalCommissions !== 0 ? `  Комиссии: ${formatMoney(-Math.abs(totalCommissions))} (уменьшают прибыль)` : null
            ].filter(Boolean) // Убираем null значения
            
            return labels
          }
        }
      }
    },
    scales: {
      x: {
        beginAtZero: true,
        min: 0, // Все бары начинаются с нуля (только правая сторона)
        grid: {
          color: axisGrid,
          drawBorder: false,
          lineWidth: 1,
          drawTicks: false,
          tickLength: 0
        },
        border: {
          display: false
        },
        ticks: {
          color: axisTextLight,
          font: {
            size: 12,
            family: 'Inter, system-ui, sans-serif',
            weight: '500'
          },
          callback: (value) => {
            if (displayMode.value === 'currency') {
              // Для валюты используем форматирование денег
              const absValue = Math.abs(value)
              if (absValue >= 1000) {
                const kValue = value / 1000
                const formatted = Math.abs(kValue) % 1 === 0 
                  ? kValue.toFixed(0) 
                  : kValue.toFixed(1)
                return `${formatted}K ₽`
              }
              return formatMoney(value)
            } else {
              // Для процентов используем форматирование без знака "+"
              return formatPercentAxis(value)
            }
          },
          padding: 12,
          stepSize: null,
          maxTicksLimit: 8
        }
      },
      y: {
        grid: {
          display: false,
          drawBorder: false
        },
        border: {
          display: false
        },
        ticks: {
          color: axisText,
          font: {
            size: 12,
            family: 'Inter, system-ui, sans-serif',
            weight: '500'
          },
          padding: 12,
          // Показываем все активы на оси Y
          autoSkip: false,
          // Для названий активов разрешаем наклон
          maxRotation: 45,
          minRotation: 0,
          // Убеждаемся, что все метки отображаются
          callback: function(value, index) {
            const labels = this.chart.data.labels
            if (labels && index < labels.length) {
              return labels[index] || ''
            }
            return ''
          }
        }
      }
    }
  }
})

// Плагин для отображения процентов/валюты справа от баров
// Скрываем текст при наведении, чтобы не перекрывать tooltip
const percentPlugin = {
  id: 'percentPlugin',
  afterDraw: (chart) => {
    const ctx = chart.ctx
    const chartArea = chart.chartArea
    
    if (!chartArea) return
    
    // Проверяем, активен ли tooltip
    const tooltip = chart.tooltip
    const isTooltipActive = tooltip && tooltip.opacity > 0
    
    ctx.save()
    ctx.textAlign = 'left'
    ctx.textBaseline = 'middle'
    ctx.font = '600 12px Inter, system-ui, sans-serif'
    
    const meta = chart.getDatasetMeta(0)
    if (!meta || !meta.data) {
      ctx.restore()
      return
    }
    
    // Получаем исходные данные из dataset
    const originalData = chart.data.datasets[0]._originalData || []
    const currentDisplayMode = displayMode.value
    
    meta.data.forEach((bar, index) => {
      const asset = originalData[index]
      if (!asset || !asset.periodData) return
      
      const value = chart.data.datasets[0].data[index]
      const periodData = asset.periodData
      const returnPercent = periodData.return_percent || 0
      const totalReturn = periodData.total_return || 0
      
      if (value !== undefined && value !== null) {
        const x = bar.x
        const y = bar.y
        
        // Если tooltip активен и это тот же элемент, не рисуем текст
        if (isTooltipActive && tooltip.dataPoints && tooltip.dataPoints.length > 0) {
          const tooltipIndex = tooltip.dataPoints[0].dataIndex
          if (tooltipIndex === index) {
            return // Пропускаем отрисовку текста для элемента с активным tooltip
          }
        }
        
        // Определяем текст в зависимости от режима отображения
        let text
        if (currentDisplayMode === 'currency') {
          // В режиме валюты показываем total_return с учетом знака
          const sign = totalReturn >= 0 ? '+' : ''
          text = `${sign}${formatMoney(Math.abs(totalReturn))}`
        } else {
          // В режиме процентов показываем return_percent с учетом знака
          text = formatPercent(returnPercent, true)
        }
        
        // Размещаем текст справа от бара
        const textX = x + 8
        const textY = y
        
        // Проверяем, что текст помещается в видимую область
        if (textX >= chartArea.left && textX <= chartArea.right && 
            textY >= chartArea.top && textY <= chartArea.bottom) {
          ctx.fillStyle = '#374151'
          ctx.fillText(text, textX, textY)
        }
      }
    })
    
    ctx.restore()
  }
}
</script>

<template>
  <Widget title="Прибыльность активов">
    <template #header>
      <div class="widget-controls">
        <ToggleSwitch v-model="showSoldAssets" label="Отображать проданные" />
        <DisplayModeToggle v-model="displayMode" />
        <PeriodFilters v-model="selectedPeriod" :periods="periodOptions" />
      </div>
    </template>

    <div class="chart-container" :style="{ minHeight: chartHeight }">
      <BaseChart
        v-if="chartData.labels && chartData.labels.length > 0"
        type="bar"
        :data="chartData"
        :options="chartOptions"
        :plugins="[percentPlugin]"
        :height="chartHeight"
      />
      <EmptyState v-else message="Нет данных о доходности активов" />
    </div>
  </Widget>
</template>

<style scoped>
.widget-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.chart-container {
  position: relative;
  width: 100%;
}
</style>
