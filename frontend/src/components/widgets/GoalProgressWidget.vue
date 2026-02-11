<script setup>
import { computed, ref } from 'vue'
import EditGoalModal from '../modals/EditGoalModal.vue'
import GoalProgressChart from '../charts/GoalProgressChart.vue'

const props = defineProps({
  goalData: { type: Object, required: true },
  onSaveGoal: { type: Function, required: true },
  defaultReturnPercent: { type: Number, default: 0 }
})

const showModal = ref(false)

function openModal() {
  showModal.value = true
}

function saveGoal(newGoal) {
  if (!props.goalData?.portfolioId) return

  // Если annualReturn не задан, используем значение по умолчанию
  const annualReturnValue = newGoal.annualReturn !== null && newGoal.annualReturn !== undefined 
    ? newGoal.annualReturn 
    : props.defaultReturnPercent || 0

  const saveData = {
    portfolioId: props.goalData.portfolioId,
    targetAmount: newGoal.targetAmount,
    monthlyContribution: newGoal.monthlyContribution || 0,
    annualReturn: annualReturnValue,
    useInflation: newGoal.useInflation || false,
    inflationRate: newGoal.inflationRate || 7.5
  }

  props.onSaveGoal(saveData)
    .then(() => {
      props.goalData.targetAmount = newGoal.targetAmount
      props.goalData.monthlyContribution = newGoal.monthlyContribution || 0
      props.goalData.annualReturn = annualReturnValue
      props.goalData.useInflation = newGoal.useInflation || false
      props.goalData.use_inflation = newGoal.useInflation || false
      props.goalData.inflationRate = newGoal.inflationRate || 7.5
      props.goalData.inflation_rate = newGoal.inflationRate || 7.5
      showModal.value = false
    })
    .catch(err => {
      console.error('[GoalProgressWidget] Ошибка при обновлении цели:', err)
    })
}

const hasGoal = computed(() => !!props.goalData?.targetAmount && props.goalData.targetAmount > 0)

const currentTargetAmount = computed(() => {
  let targetAmount = 0
  
  if (props.goalData?.targetAmount !== undefined && props.goalData?.targetAmount !== null) {
    targetAmount = Number(props.goalData.targetAmount)
  } else if (props.goalData?.capital_target_value !== undefined && props.goalData?.capital_target_value !== null) {
    targetAmount = Number(props.goalData.capital_target_value)
  }
  
  const useInflationValue = useInflation.value
  const inflationRateValue = inflationRate.value
  
  if (!useInflationValue) {
    return targetAmount
  }
  
  const projection = goalProjection.value
  let goalYear = null
  
  if (projection.goalReachedMonth !== null && projection.goalReachedMonth !== undefined) {
    const startDate = new Date()
    const goalDate = new Date(startDate)
    if (projection.goalReachedMonth > 0) {
      goalDate.setMonth(goalDate.getMonth() + projection.goalReachedMonth)
    }
    goalYear = goalDate.getFullYear()
  } else if (projection.labels && projection.labels.length > 0) {
    const lastYear = parseInt(projection.labels[projection.labels.length - 1])
    goalYear = lastYear
  }
  
  if (goalYear !== null) {
    const currentYear = new Date().getFullYear()
    const yearsFromNow = goalYear - currentYear
    return targetAmount * Math.pow(1 + inflationRateValue / 100, yearsFromNow)
  }
  
  return targetAmount
})

const progressPercentage = computed(() => {
  if (!hasGoal.value || !currentTargetAmount.value) return 0
  return Math.min((props.goalData.currentAmount / currentTargetAmount.value) * 100, 100)
})

// Получаем значения из goalData или используем значения по умолчанию
const monthlyContribution = computed(() => props.goalData?.monthlyContribution || 0)
const annualReturn = computed(() => {
  // Используем сохраненное значение, если есть, иначе значение из ReturnWidget
  return props.goalData?.annualReturn || props.defaultReturnPercent || 0
})
const useInflation = computed(() => {
  return props.goalData?.useInflation || props.goalData?.use_inflation || false
})

const inflationRate = computed(() => {
  return props.goalData?.inflationRate || props.goalData?.inflation_rate || 7.5
})

// Расчет прогноза достижения цели
const goalProjection = computed(() => {
  // Получаем targetAmount из разных возможных источников
  const targetAmount = Number(props.goalData?.targetAmount) || 
                       Number(props.goalData?.capital_target_value) || 0
  
  if (!hasGoal.value || !targetAmount) {
    return { labels: [], datasets: [], goalReachedMonth: null }
  }

  const currentAmount = props.goalData.currentAmount || 0
  const monthly = monthlyContribution.value || 0
  const annualReturnPercent = annualReturn.value || 0
  
  // Получаем значения инфляции
  const useInflationValue = props.goalData?.useInflation || props.goalData?.use_inflation || false
  const inflationRateValue = props.goalData?.inflationRate || props.goalData?.inflation_rate || 7.5
  
  // Месячная доходность (приблизительно)
  const monthlyReturnRate = annualReturnPercent / 12 / 100
  
  const startDate = new Date()
  
  // Функция для расчета цели с учетом инфляции для конкретного месяца
  const getTargetForMonth = (monthNumber) => {
    if (!useInflationValue) {
      return targetAmount
    }
    const currentYear = new Date().getFullYear()
    const targetDate = new Date(startDate)
    targetDate.setMonth(targetDate.getMonth() + monthNumber)
    const targetYear = targetDate.getFullYear()
    const yearsFromNow = targetYear - currentYear
    // Увеличиваем цель на инфляцию каждый год
    return targetAmount * Math.pow(1 + inflationRateValue / 100, yearsFromNow)
  }
  
  // Данные по месяцам для точного расчета
  const monthlyData = []
  let current = currentAmount
  let month = 0
  const maxMonths = 240 // Максимум 20 лет
  let goalReachedMonth = null
  monthlyData.push({
    month: 0,
    value: current,
    date: new Date(startDate)
  })
  
  // Проверяем, достигнута ли цель уже сейчас
  const currentTarget = getTargetForMonth(0)
  if (current >= currentTarget) {
    goalReachedMonth = 0
  }
  
  // Рассчитываем по месяцам до достижения цели и после
  while (month < maxMonths) {
    month++
    current = current * (1 + monthlyReturnRate) + monthly
    
    const date = new Date(startDate)
    date.setMonth(date.getMonth() + month)
    
    monthlyData.push({
      month,
      value: current,
      date: new Date(date)
    })
    
    // Получаем цель для этого месяца с учетом инфляции
    const monthTarget = getTargetForMonth(month)
    
    if (current >= monthTarget && goalReachedMonth === null) {
      goalReachedMonth = month
    }
    
    // Продолжаем расчет после достижения цели еще на 12 месяцев
    if (goalReachedMonth !== null && month >= goalReachedMonth + 12) {
      break
    }
  }
  
  // Группируем по годам (берем значение на конец каждого года)
  const yearData = new Map()
  monthlyData.forEach(point => {
    const year = point.date.getFullYear()
    if (!yearData.has(year) || point.month > yearData.get(year).month) {
      yearData.set(year, point)
    }
  })
  
  // Сортируем по годам
  const sortedYears = Array.from(yearData.keys()).sort()
  
  const labels = sortedYears.map(year => year.toString())
  const projectionData = sortedYears.map(year => yearData.get(year).value)
  
  // Рассчитываем линию цели с учетом инфляции
  const targetLine = sortedYears.map((year, index) => {
    if (!useInflationValue) {
      return targetAmount
    }
    // Вычисляем количество лет от текущего года
    const currentYear = new Date().getFullYear()
    const yearsFromNow = year - currentYear
    // Увеличиваем цель на инфляцию каждый год
    const inflatedTarget = targetAmount * Math.pow(1 + inflationRateValue / 100, yearsFromNow)
    return inflatedTarget
  })
  
  const goalMarkerData = sortedYears.map(() => null)
  
  // Добавляем маркер достижения цели на линии портфеля
  if (goalReachedMonth !== null) {
    const goalDate = new Date(startDate)
    if (goalReachedMonth > 0) {
      goalDate.setMonth(goalDate.getMonth() + goalReachedMonth)
    }
    const goalYear = goalDate.getFullYear()
    
    const goalYearIndex = sortedYears.indexOf(goalYear)
    if (goalYearIndex !== -1) {
      // Находим значение портфеля в год достижения цели
      // Используем yearData, чтобы получить значение портфеля для этого года
      const goalYearData = yearData.get(goalYear)
      if (goalYearData) {
        // Используем значение портфеля, а не цели
        const markerPortfolioValue = goalYearData.value
        goalMarkerData[goalYearIndex] = markerPortfolioValue
        
      } else {
        const goalPoint = monthlyData.find(p => p.month === goalReachedMonth)
      if (goalPoint) {
        goalMarkerData[goalYearIndex] = goalPoint.value
      }
    }
  } else if (goalReachedMonth === 0 && sortedYears.length > 0) {
    goalMarkerData[0] = currentAmount
  }
  }
  
  return {
    labels,
    datasets: [
      {
        label: 'Прогноз капитала',
        data: projectionData,
        borderColor: '#5478EA',
        backgroundColor: 'rgba(84, 120, 234, 0.06)',
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 5,
        borderWidth: 2
      },
      {
        label: 'Целевой капитал',
        data: targetLine,
        borderColor: '#9ca3af',
        backgroundColor: 'transparent',
        borderDash: [5, 5],
        borderWidth: 1.5,
        fill: false,
        pointRadius: 0
      },
      {
        label: 'Достижение цели',
        data: goalMarkerData,
        borderColor: '#fff',
        backgroundColor: '#10b981',
        pointRadius: 8,
        pointHoverRadius: 10,
        pointBorderWidth: 2.5,
        pointBorderColor: '#fff',
        pointBackgroundColor: '#10b981',
        showLine: false,
        order: 1,
        pointStyle: 'circle'
      }
    ],
    goalReachedMonth
  }
})

// Форматирование валюты для графика
const formatCurrency = (value) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0
  }).format(value)
}

// Расчет времени до достижения цели
const timeToGoal = computed(() => {
  if (!hasGoal.value || !props.goalData.targetAmount) return null
  
  const projection = goalProjection.value
  
  // Если цель уже достигнута
  if (projection.goalReachedMonth === 0) {
    return { text: 'Уже достигнуто', year: null }
  }
  
  // Если цель не достигнута за максимальный период
  if (projection.goalReachedMonth === null) {
    return { text: 'Более 20 лет', year: null }
  }
  
  const months = projection.goalReachedMonth
  if (months === 0) return { text: 'Уже достигнуто', year: null }
  
  const years = Math.floor(months / 12)
  const remainingMonths = months % 12
  
  // Вычисляем год достижения цели
  const goalDate = new Date()
  goalDate.setMonth(goalDate.getMonth() + months)
  const goalYear = goalDate.getFullYear()
  
  let text = ''
  if (years > 0 && remainingMonths > 0) {
    text = `${years} ${years === 1 ? 'год' : years < 5 ? 'года' : 'лет'} ${remainingMonths} ${remainingMonths === 1 ? 'месяц' : remainingMonths < 5 ? 'месяца' : 'месяцев'}`
  } else if (years > 0) {
    text = `${years} ${years === 1 ? 'год' : years < 5 ? 'года' : 'лет'}`
  } else {
    text = `${remainingMonths} ${remainingMonths === 1 ? 'месяц' : remainingMonths < 5 ? 'месяца' : 'месяцев'}`
  }
  
  return { text, year: goalYear }
})

const formatAmountShort = (value) => {
  const numValue = Number(value) || 0
  
  if (numValue >= 1000000) {
    const mValue = numValue / 1000000
    const formatted = mValue % 1 === 0 
      ? mValue.toFixed(0) 
      : mValue.toFixed(2)
    return `${formatted} млн ₽`
  } else if (numValue >= 1000) {
    const kValue = numValue / 1000
    const formatted = kValue % 1 === 0 
      ? kValue.toFixed(0) 
      : kValue.toFixed(2)
    return `${formatted} тыс. ₽`
  }
  return formatCurrency(numValue)
}
</script>

<template>
  <div class="widget">
    <div class="widget-title">
      <div class="widget-title-icon-rect">
        <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
        </svg>
      </div>
      <h2 class="widget-title">Прогноз достижения цели</h2>
      <button @click="openModal" class="edit-button">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
        </svg>
        Изменить цель
      </button>
    </div>

    <template v-if="hasGoal">
      <!-- Информация о цели с круговым прогрессом -->
      <div class="goal-summary">
        <div class="progress-circle-wrapper">
          <svg class="progress-circle" viewBox="0 0 100 100">
            <circle
              class="progress-circle-bg"
              cx="50"
              cy="50"
              r="45"
              fill="none"
              stroke="#e5e7eb"
              stroke-width="8"
            />
            <circle
              class="progress-circle-fill"
              cx="50"
              cy="50"
              r="45"
              fill="none"
              stroke="#5478EA"
              stroke-width="8"
              :stroke-dasharray="`${2 * Math.PI * 45}`"
              :stroke-dashoffset="`${2 * Math.PI * 45 * (1 - progressPercentage / 100)}`"
              transform="rotate(-90 50 50)"
            />
          </svg>
          <div class="progress-percentage">{{ progressPercentage.toFixed(0) }}%</div>
        </div>
        
        <div class="goal-amounts-info">
          <div class="capital-info">
            <div class="capital-amounts">
              <span class="current-amount">{{ formatAmountShort(props.goalData.currentAmount || 0) }}</span>
              <span class="separator">/</span>
              <span class="target-amount">{{ formatAmountShort(currentTargetAmount) }}</span>
            </div>
            <div class="capital-label">Капитал</div>
          </div>
        </div>
        
        <div v-if="timeToGoal" class="achievement-info">
          <div class="achievement-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#5478EA" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M7 10v12l5-3 5 3V10M7 10l5-7 5 7M7 10h10"/>
            </svg>
          </div>
          <div class="achievement-text">
            <div class="achievement-time">Достижима через {{ timeToGoal.text }}</div>
            <div v-if="timeToGoal.year" class="achievement-year">В {{ timeToGoal.year }} году</div>
          </div>
        </div>
      </div>
      
      <!-- График прогноза -->
      <div v-if="goalProjection.labels.length > 0" class="projection-chart">
        <GoalProgressChart 
          :labels="goalProjection.labels"
          :datasets="goalProjection.datasets"
          :formatValue="formatCurrency"
          :useInflation="useInflation.value"
        />
      </div>
    </template>

    <EditGoalModal
      :show="showModal"
      :targetAmount="props.goalData?.targetAmount || 0"
      :monthlyContribution="monthlyContribution"
      :annualReturn="annualReturn"
      :useInflation="useInflation"
      :inflationRate="inflationRate"
      @close="showModal = false"
      @save="saveGoal"
    />
  </div>
</template>

<style scoped>
.widget {
  grid-row: span 1;
  grid-column: span 1;
  display: flex;
  flex-direction: column;
  background-color: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
  min-height: 0;
}

.widget-title {
  display: flex;
  gap: 5px;
  align-items: center;
  margin-bottom: 1rem;
}

.widget-title-icon-rect {
  padding: 5px;
  width: 25px;
  height: 25px;
  border-radius: 6px;
  background-color: #F6F6F6;
  display: flex;
  align-items: center;
  justify-content: center;
}

.widget-title h2 {
  font-size: 1rem;
  font-weight: 400;
  color: #6B7280;
  margin: 0;
  flex: 1;
}

.edit-button {
  background: #f3f4f6;
  color: #374151;
  border: none;
  border-radius: 8px;
  padding: 0.5rem 0.875rem;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 500;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: auto;
}

.edit-button:hover {
  background: #e5e7eb;
  color: #111827;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.edit-button svg {
  width: 16px;
  height: 16px;
}

.goal-summary {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-bottom: 0.75rem;
}

.progress-circle-wrapper {
  position: relative;
  width: 64px;
  height: 64px;
  flex-shrink: 0;
}

.progress-circle {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.progress-circle-bg {
  stroke: #f3f4f6;
}

.progress-circle-fill {
  stroke: #5478EA;
  transition: stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1);
  stroke-linecap: round;
  animation: progressAnimation 1s ease-out;
}

@keyframes progressAnimation {
  from {
    stroke-dashoffset: 282.743;
  }
}

.progress-percentage {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 0.875rem;
  font-weight: 700;
  color: #111827;
}

.goal-amounts-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.capital-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.capital-amounts {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-weight: 600;
  color: #111827;
}

.current-amount {
  color: #111827;
  font-size: 1.125rem;
}

.separator {
  color: #9ca3af;
  font-weight: 400;
  font-size: 0.875rem;
}

.target-amount {
  color: #6b7280;
  font-size: 0.875rem;
}

.capital-label {
  font-size: 0.75rem;
  color: #6b7280;
  font-weight: 500;
}

.achievement-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.625rem;
  background: #f9fafb;
  border-radius: 6px;
  flex-shrink: 0;
}

.achievement-icon svg {
  width: 18px;
  height: 18px;
}

.achievement-text {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.achievement-time {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #111827;
  line-height: 1.2;
}

.achievement-year {
  font-size: 0.6875rem;
  color: #6b7280;
  line-height: 1.2;
}

.projection-chart {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  margin-top: 0.75rem;
  position: relative;
}

.projection-chart :deep(div) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.projection-chart :deep(canvas) {
  flex: 1;
  min-height: 0;
}
</style>
