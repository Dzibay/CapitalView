<script setup>
import { computed } from 'vue'
import BarChart from '../charts/BarChart.vue'

const props = defineProps({
  futurePayouts: {
    type: Array,
    default: () => []
  }
})


const formatMoney = (value) => {
  const num = value || 0
  if (num >= 1000) {
    const kValue = num / 1000
    // Форматируем с одной цифрой после запятой, если нужно
    const formatted = kValue % 1 === 0 
      ? kValue.toFixed(0) 
      : kValue.toFixed(1).replace('.', ',')
    return `${formatted}K ₽`
  }
  return `${num} ₽`
}

// Фильтруем только на год вперед
const filteredPayouts = computed(() => {
  if (!props.futurePayouts || !Array.isArray(props.futurePayouts) || props.futurePayouts.length === 0) {
    return []
  }
  
  const currentDate = new Date()
  const oneYearLater = new Date(currentDate)
  oneYearLater.setFullYear(currentDate.getFullYear() + 1)
  
  return props.futurePayouts.filter(fp => {
    if (!fp || !fp.month) return false
    try {
      const [year, month] = fp.month.split('-')
      if (!year || !month) return false
      const payoutDate = new Date(parseInt(year), parseInt(month) - 1)
      return payoutDate <= oneYearLater
    } catch (e) {
      return false
    }
  })
})

const chartLabels = computed(() => {
  return filteredPayouts.value.map(f => f.month) || []
})

const chartDatasets = computed(() => {
  if (!filteredPayouts.value || filteredPayouts.value.length === 0) {
    return []
  }
  
  const datasets = []
  
  // Дивиденды - всегда показываем, даже если все значения 0
  const dividends = filteredPayouts.value.map(f => Number(f.dividends) || 0)
  const dividendsSum = dividends.reduce((a, b) => a + b, 0)
  datasets.push({
    label: 'Дивиденды',
    data: dividends,
    backgroundColor: 'rgba(16, 185, 129, 0.85)',
    borderColor: '#10b981',
    borderWidth: 0,
    hoverBackgroundColor: '#10b981',
    hoverBorderColor: '#059669',
    borderRadius: 8,
    borderSkipped: false,
    totalSum: dividendsSum
  })
  
  // Купоны - всегда показываем, даже если все значения 0
  const coupons = filteredPayouts.value.map(f => Number(f.coupons) || 0)
  const couponsSum = coupons.reduce((a, b) => a + b, 0)
  datasets.push({
    label: 'Купоны',
    data: coupons,
    backgroundColor: 'rgba(59, 130, 246, 0.85)',
    borderColor: '#3b82f6',
    borderWidth: 0,
    hoverBackgroundColor: '#3b82f6',
    hoverBorderColor: '#2563eb',
    borderRadius: 0,
    borderSkipped: false,
    totalSum: couponsSum
  })
  
  // Амортизации - всегда показываем, даже если все значения 0
  const amortizations = filteredPayouts.value.map(f => Number(f.amortizations) || 0)
  const amortizationsSum = amortizations.reduce((a, b) => a + b, 0)
  datasets.push({
    label: 'Амортизации',
    data: amortizations,
    backgroundColor: 'rgba(245, 158, 11, 0.85)',
    borderColor: '#f59e0b',
    borderWidth: 0,
    hoverBackgroundColor: '#f59e0b',
    hoverBorderColor: '#d97706',
    borderRadius: 0,
    borderSkipped: false,
    totalSum: amortizationsSum
  })
  
  // Сортируем по сумме значений (от меньших к большим)
  // В stacked графике порядок снизу вверх, поэтому меньшие внизу, большие наверху
  const sorted = datasets.sort((a, b) => a.totalSum - b.totalSum)
  
  // Применяем borderRadius только к верхнему слою (скругление только сверху)
  // Если есть только один dataset, он тоже должен быть скруглен сверху
  sorted.forEach((dataset, index) => {
    if (index === sorted.length - 1) {
      // Верхний слой (или единственный слой) - скругление только сверху
      dataset.borderRadius = {
        topLeft: 8,
        topRight: 8,
        bottomLeft: 0,
        bottomRight: 0
      }
    } else {
      // Нижние и средние слои - без скругления
      dataset.borderRadius = 0
    }
  })
  
  return sorted
})
</script>

<template>
  <div class="widget">
    <div class="widget-title">
      <div class="widget-title-icon-rect"></div>
      <h2>График будущих выплат</h2>
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
  </div>
</template>

<style scoped>
.widget {
  background-color: #fff;
  padding: var(--spacing);
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

.widget-title {
  display: flex;
  gap: 5px;
  align-items: center;
}

.widget-title-icon-rect {
  padding: 5px;
  width: 25px;
  height: 25px;
  border-radius: 6px;
  background-color: #F6F6F6;
}

.widget-title h2 {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  margin: 0;
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

