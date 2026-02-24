<script setup>
import { ref, computed } from 'vue'
import { HandCoins } from 'lucide-vue-next'
import BarChart from '../../charts/BarChart.vue'
import CustomSelect from '../../base/CustomSelect.vue'
import Widget from '../base/Widget.vue'

const props = defineProps({
  title: {
    type: String,
    default: 'Выплаты по месяцам'
  },
  payouts: {
    type: Array,
    default: () => []
  },
  // 'past' для полученных выплат, 'future' для будущих
  mode: {
    type: String,
    default: 'past',
    validator: (value) => ['past', 'future'].includes(value)
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

const formatMoneyFull = (value) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: props.mode === 'past' ? 2 : 0,
    maximumFractionDigits: props.mode === 'past' ? 2 : 0
  }).format(value || 0)
}

// Фильтрация и группировка данных
const filteredPayouts = computed(() => {
  if (!props.payouts || !Array.isArray(props.payouts) || props.payouts.length === 0) {
    return []
  }
  
  const periodMonths = parseInt(selectedPeriod.value) || 12
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  
  let cutoffDate = new Date(today)
  
  if (props.mode === 'past') {
    // Для прошлых выплат: от сегодня назад
    cutoffDate.setMonth(today.getMonth() - periodMonths)
  } else {
    // Для будущих выплат: от сегодня вперед
    cutoffDate.setMonth(today.getMonth() + periodMonths)
  }
  
  // Фильтруем по периоду
  let filtered = props.payouts.filter(p => {
    if (!p || !p.month) return false
    try {
      const [year, month] = p.month.split('-')
      if (!year || !month) return false
      const payoutDate = new Date(parseInt(year), parseInt(month) - 1)
      payoutDate.setHours(0, 0, 0, 0)
      
      if (props.mode === 'past') {
        return payoutDate >= cutoffDate && payoutDate <= today
      } else {
        return payoutDate >= today && payoutDate <= cutoffDate
      }
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
  
  const datasets = []
  
  // Дивиденды
  const dividends = filteredPayouts.value.map(p => Number(p.dividends) || 0)
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
  
  // Купоны
  const coupons = filteredPayouts.value.map(p => Number(p.coupons) || 0)
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
  
  // Амортизации
  const amortizations = filteredPayouts.value.map(p => Number(p.amortizations) || 0)
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
</script>

<template>
  <Widget :title="title" :icon="HandCoins">
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
        <p>{{ mode === 'past' ? 'Нет данных о выплатах' : 'Нет данных о будущих выплатах' }}</p>
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
