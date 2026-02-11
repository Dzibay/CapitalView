<script setup>
import { ref, computed } from 'vue'
import BarChart from '../charts/BarChart.vue'
import CustomSelect from '../CustomSelect.vue'
import Widget from './Widget.vue'

const props = defineProps({
  futurePayouts: {
    type: Array,
    default: () => []
  }
})

// Фильтры
const selectedPeriod = ref('12')
const selectedGrouping = ref('month')

// Опции для фильтров
const periodOptions = [
  { value: '6', label: '6 мес.' },
  { value: '12', label: '12 мес.' },
  { value: '24', label: '24 мес.' },
  { value: '36', label: '36 мес.' }
]

const groupingOptions = [
  { value: 'month', label: 'По месяцам' },
  { value: 'quarter', label: 'По кварталам' }
]

// Фирменные цвета для типов выплат
const payoutColors = {
  // Дивиденды - синий
  dividends: '#2563eb',
  dividendsAlpha: 'rgba(37, 99, 235, 0.85)',
  dividendsHover: '#1d4ed8',
  dividendsDark: '#1e40af',
  
  // Купоны - голубой/cyan
  coupons: '#06b6d4',
  couponsAlpha: 'rgba(6, 182, 212, 0.85)',
  couponsHover: '#0891b2',
  couponsDark: '#0e7490',
  
  // Амортизации - оранжевый
  amortizations: '#fb923c',
  amortizationsAlpha: 'rgba(251, 146, 60, 0.85)',
  amortizationsHover: '#f97316',
  amortizationsDark: '#ea580c'
}

const formatMoney = (value) => {
  const num = value || 0
  if (num >= 1000) {
    const kValue = num / 1000
    const formatted = kValue % 1 === 0 
      ? kValue.toFixed(0) 
      : kValue.toFixed(1).replace('.', ',')
    return `${formatted}K ₽`
  }
  return `${num} ₽`
}

// Форматирование для отображения суммы
const formatMoneyFull = (value) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  }).format(value || 0)
}

// Форматирование меток месяцев
const formatMonthLabel = (monthStr) => {
  if (!monthStr) return ''
  try {
    const [year, month] = monthStr.split('-')
    if (!year || !month) return monthStr
    
    const date = new Date(parseInt(year), parseInt(month) - 1)
    const monthName = date.toLocaleString('ru-RU', { month: 'long' })
    const shortYear = year.slice(-2)
    return `${monthName} ${shortYear}`
  } catch (e) {
    return monthStr
  }
}

// Фильтрация и группировка данных
const filteredPayouts = computed(() => {
  if (!props.futurePayouts || !Array.isArray(props.futurePayouts) || props.futurePayouts.length === 0) {
    return []
  }
  
  const periodMonths = parseInt(selectedPeriod.value) || 12
  const today = new Date()
  const cutoffDate = new Date(today)
  cutoffDate.setMonth(today.getMonth() + periodMonths)
  
  // Фильтруем по периоду (будущие выплаты)
  let filtered = props.futurePayouts.filter(fp => {
    if (!fp || !fp.month) return false
    try {
      const [year, month] = fp.month.split('-')
      if (!year || !month) return false
      const payoutDate = new Date(parseInt(year), parseInt(month) - 1)
      return payoutDate >= today && payoutDate <= cutoffDate
    } catch (e) {
      return false
    }
  })
  
  // Группировка по кварталам, если выбрано
  if (selectedGrouping.value === 'quarter') {
    const grouped = {}
    filtered.forEach(fp => {
      if (!fp.month) return
      try {
        const [year, month] = fp.month.split('-')
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
        
        grouped[key].dividends += fp.dividends || 0
        grouped[key].coupons += fp.coupons || 0
        grouped[key].amortizations += fp.amortizations || 0
      } catch (e) {
        // Игнорируем ошибки
      }
    })
    
    return Object.values(grouped).sort((a, b) => {
      return a.month.localeCompare(b.month)
    })
  }
  
  return filtered
})

// Общая сумма будущих выплат
const totalPayouts = computed(() => {
  return filteredPayouts.value.reduce((sum, fp) => {
    return sum + (Number(fp.dividends) || 0) + (Number(fp.coupons) || 0) + (Number(fp.amortizations) || 0)
  }, 0)
})

const chartLabels = computed(() => {
  // Передаем исходные даты, BarChart будет форматировать их адаптивно
  return filteredPayouts.value.map(fp => fp.month) || []
})

const chartDatasets = computed(() => {
  if (!filteredPayouts.value || filteredPayouts.value.length === 0) {
    return []
  }
  
  const datasets = []
  
  // Дивиденды - синий
  const dividends = filteredPayouts.value.map(fp => Number(fp.dividends) || 0)
  const dividendsSum = dividends.reduce((a, b) => a + b, 0)
  datasets.push({
    label: 'Дивиденды',
    data: dividends,
    backgroundColor: payoutColors.dividendsAlpha,
    borderColor: payoutColors.dividends,
    borderWidth: 0,
    hoverBackgroundColor: payoutColors.dividendsHover,
    hoverBorderColor: payoutColors.dividendsDark,
    borderSkipped: false,
    totalSum: dividendsSum
  })
  
  // Купоны - голубой/cyan
  const coupons = filteredPayouts.value.map(fp => Number(fp.coupons) || 0)
  const couponsSum = coupons.reduce((a, b) => a + b, 0)
  datasets.push({
    label: 'Купоны',
    data: coupons,
    backgroundColor: payoutColors.couponsAlpha,
    borderColor: payoutColors.coupons,
    borderWidth: 0,
    hoverBackgroundColor: payoutColors.couponsHover,
    hoverBorderColor: payoutColors.couponsDark,
    borderSkipped: false,
    totalSum: couponsSum
  })
  
  // Амортизации - оранжевый
  const amortizations = filteredPayouts.value.map(fp => Number(fp.amortizations) || 0)
  const amortizationsSum = amortizations.reduce((a, b) => a + b, 0)
  datasets.push({
    label: 'Амортизации',
    data: amortizations,
    backgroundColor: payoutColors.amortizationsAlpha,
    borderColor: payoutColors.amortizations,
    borderWidth: 0,
    hoverBackgroundColor: payoutColors.amortizationsHover,
    hoverBorderColor: payoutColors.amortizationsDark,
    borderSkipped: false,
    totalSum: amortizationsSum
  })
  
  // Сортируем по сумме значений (от меньших к большим)
  const sorted = datasets.sort((a, b) => a.totalSum - b.totalSum)
  
  // Применяем borderRadius только к верхнему слою для каждого столбца отдельно
  sorted.forEach((dataset, datasetIndex) => {
    const borderRadiusArray = dataset.data.map((value, dataIndex) => {
      if (value === 0) {
        return 0
      }
      
      // Проверяем, есть ли ненулевые значения выше этого слоя для данного столбца
      let hasValueAbove = false
      for (let i = datasetIndex + 1; i < sorted.length; i++) {
        if (sorted[i].data[dataIndex] > 0) {
          hasValueAbove = true
          break
        }
      }
      
      // Если нет значений выше, это верхний слой - скругляем сверху
      if (!hasValueAbove) {
        return 8
      }
      
      return 0
    })
    
    // Проверяем, все ли значения одинаковые
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
      // Если разные, используем функцию для динамического скругления
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
</script>

<template>
  <Widget title="График будущих выплат">
    <template #header>
      <CustomSelect
        v-model="selectedPeriod"
        :options="periodOptions"
        :option-label="'label'"
        :option-value="'value'"
        placeholder="Период"
        :show-empty-option="false"
        min-width="120px"
        flex="0"
      />
      <CustomSelect
        v-model="selectedGrouping"
        :options="groupingOptions"
        :option-label="'label'"
        :option-value="'value'"
        placeholder="Группировка"
        :show-empty-option="false"
        min-width="140px"
        flex="0"
      />
    </template>
    
    <div class="total-amount">
      <span class="total-label">Всего</span>
      <span class="total-value">{{ formatMoneyFull(totalPayouts) }}</span>
    </div>
    
    <div class="chart-container">
      <BarChart
        v-if="filteredPayouts && filteredPayouts.length > 0"
        :labels="chartLabels"
        :datasets="chartDatasets"
        :stacked="true"
        :format-value="formatMoney"
        height="300px"
      />
      <div v-else class="empty-state">
        <p>Нет данных о будущих выплатах</p>
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
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 400;
}

.total-value {
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827;
}

.chart-container {
  height: 300px;
  position: relative;
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
  color: #6b7280;
  font-size: 14px;
  background: white;
  z-index: 10;
}

.empty-state p {
  margin: 0;
}
</style>

