<script setup>
import { ref, computed, watch } from 'vue'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import PortfolioSelector from '../components/PortfolioSelector.vue'

// Используем stores вместо inject
const dashboardStore = useDashboardStore()
const uiStore = useUIStore()

// === STATE ===
const currentDate = ref(new Date()) // Текущий месяц
const selectedDay = ref(null)       // Выбранный день

const months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
const weekDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

// === COMPUTED: ДАННЫЕ ===

// 1. Список портфелей для селектора
const portfolios = computed(() => dashboardStore.portfolios ?? [])

// 2. Сбор дивидендов (ОБНОВЛЕННАЯ СТРУКТУРА)
const allDividends = computed(() => {
  const dataPortfolios = dashboardStore.portfolios
  if (!dataPortfolios || !uiStore.selectedPortfolioId) return []

  // 1. Находим текущий выбранный портфель
  const targetPortfolio = dataPortfolios.find(p => p.id === uiStore.selectedPortfolioId)

  // Если портфель не найден или у него нет combined_assets — возвращаем пустоту
  if (!targetPortfolio || !targetPortfolio.combined_assets) return []

  const list = []
  
  // 2. Проходимся по активам
  targetPortfolio.combined_assets.forEach(asset => {
    // Ищем массив выплат (в новой структуре это asset.payouts)
    const payouts = asset.payouts || asset.dividends || [] 
    
    payouts.forEach(div => {
      // --- ОПРЕДЕЛЕНИЕ ДАТ ---
      // Для календаря (grid) приоритет: Payment > Record > LastBuy
      // Обычно мы хотим видеть, когда придут деньги.
      const mainDateStr = div.payment_date || div.record_date || div.last_buy_date
      
      if (!mainDateStr) return // Пропускаем, если нет дат

      const calendarDate = new Date(mainDateStr)
      const lastBuyDate = div.last_buy_date ? new Date(div.last_buy_date) : null
      const paymentDate = div.payment_date ? new Date(div.payment_date) : null

      // --- ЛОГИКА СТАТУСА ---
      let status = div.status || 'unknown'
      // Если это просто прогноз без точных дат или помечен как forecast
      if (div.type === 'forecast') status = 'forecast'

      // --- ТИП ВЫПЛАТЫ ---
      // dividend, coupon, amortization
      const paymentType = div.type || 'dividend'

      list.push({
        // Уникальный ID
        id: div.id || `${asset.id}-${mainDateStr}-${div.value}`,
        
        assetTicker: asset.ticker,
        assetName: asset.name,
        
        // Дата для отображения в ячейке календаря
        date: calendarDate, 
        // Дата для отображения в карточке "Отсечка"
        lastBuyDate: lastBuyDate,
        // Реальная дата выплаты (для инфо)
        paymentDate: paymentDate,
        
        value: parseFloat(div.value),
        currency: div.currency || 'RUB',
        
        // Общая сумма: выплата * кол-во бумаг в портфеле
        totalAmount: parseFloat(div.value) * (asset.quantity || 0), 
        
        status: status, 
        // Считаем прогнозом, если статус не confirmed
        isForecast: status === 'forecast' || status === 'recommended',
        
        paymentType: paymentType
      })
    })
  })
  
  // Сортировка по дате календаря
  return list.sort((a, b) => a.date - b.date)
})

// 3. Фильтр по текущему месяцу календаря
const monthDividends = computed(() => {
  const m = currentDate.value.getMonth()
  const y = currentDate.value.getFullYear()
  return allDividends.value.filter(d => 
    d.date.getMonth() === m && d.date.getFullYear() === y
  )
})

// 4. Итоговая сумма за месяц (RUB)
const totalMonthIncome = computed(() => {
  return monthDividends.value
    .reduce((sum, item) => {
      // Упрощенная логика: суммируем только RUB, либо можно добавить конвертацию
      if (item.currency === 'RUB' || item.currency === 'SUR') return sum + item.totalAmount
      return sum
    }, 0)
    .toFixed(2)
})

// === COMPUTED: КАЛЕНДАРЬ ===

const currentMonthName = computed(() => months[currentDate.value.getMonth()])
const currentYear = computed(() => currentDate.value.getFullYear())

const calendarDays = computed(() => {
  const year = currentDate.value.getFullYear()
  const month = currentDate.value.getMonth()
  
  const firstDayOfMonth = new Date(year, month, 1)
  const lastDayOfMonth = new Date(year, month + 1, 0)
  const daysInMonth = lastDayOfMonth.getDate()
  
  // Коррекция дня недели (Пн=0, Вс=6)
  let startDayOfWeek = firstDayOfMonth.getDay() 
  startDayOfWeek = startDayOfWeek === 0 ? 6 : startDayOfWeek - 1 

  const days = []

  // Пустые ячейки
  for (let i = 0; i < startDayOfWeek; i++) {
    days.push({ day: '', type: 'empty' })
  }

  // Заполнение днями
  for (let i = 1; i <= daysInMonth; i++) {
    const dateCheck = new Date(year, month, i)
    // Поиск событий для конкретного дня
    const events = monthDividends.value.filter(d => d.date.getDate() === i)
    
    days.push({
      day: i,
      type: 'day',
      events: events,
      hasEvents: events.length > 0,
      isToday: isToday(dateCheck)
    })
  }
  return days
})

// === МЕТОДЫ ===

function prevMonth() {
  currentDate.value = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth() - 1, 1)
  selectedDay.value = null
}

function nextMonth() {
  currentDate.value = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth() + 1, 1)
  selectedDay.value = null
}

function selectDate(dayObj) {
  if (dayObj.type === 'day') {
    selectedDay.value = dayObj
  }
}

function isToday(date) {
  const today = new Date()
  return date.getDate() === today.getDate() &&
         date.getMonth() === today.getMonth() &&
         date.getFullYear() === today.getFullYear()
}

const formatMoney = (val) => new Intl.NumberFormat('ru-RU').format(val)
const formatDate = (date) => {
  if (!date) return '—'
  return new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(date)
}

// Сброс выбора дня при переключении портфеля
watch(() => uiStore.selectedPortfolioId, () => {
  selectedDay.value = null
})
</script>

<template>
  <div class="dividends-page">
    
    <div class="header-row">
      <div>
        <h1 class="page-title">Календарь выплат</h1>
        <p class="subtitle">График дивидендов, купонов и амортизаций</p>
      </div>
      
      <PortfolioSelector 
        v-if="portfolios.length > 0"
        :portfolios="portfolios"
        :modelValue="uiStore.selectedPortfolioId"
        @update:modelValue="uiStore.setSelectedPortfolioId"
      />
    </div>

    <div v-if="uiStore.loading" class="loading-state">
      <div class="loader"></div>
      <span>Загрузка данных...</span>
    </div>

    <div v-else>
      <div class="calendar-controls">
        <div class="month-nav">
          <button class="btn-icon" @click="prevMonth">‹</button>
          <h2>{{ currentMonthName }} {{ currentYear }}</h2>
          <button class="btn-icon" @click="nextMonth">›</button>
        </div>
        
        <div class="month-summary">
          <span class="label">Ожидается (RUB):</span>
          <span class="value" :class="Number(totalMonthIncome) > 0 ? 'text-green' : ''">
            + {{ formatMoney(totalMonthIncome) }} ₽
          </span>
        </div>
      </div>

      <div class="calendar-layout">
        
        <div class="calendar-grid">
          <div class="week-header">
            <div class="week-day" v-for="day in weekDays" :key="day">{{ day }}</div>
          </div>
          
          <div class="days-container">
            <div 
              v-for="(cell, index) in calendarDays" 
              :key="index"
              class="calendar-cell"
              :class="{ 
                'empty': cell.type === 'empty',
                'has-events': cell.hasEvents,
                'is-today': cell.isToday,
                'selected': selectedDay && selectedDay.day === cell.day
              }"
              @click="selectDate(cell)"
            >
              <span v-if="cell.day" class="day-number">{{ cell.day }}</span>
              
              <div v-if="cell.hasEvents" class="events-dots">
                <span 
                  v-for="evt in cell.events.slice(0, 4)" 
                  :key="evt.id" 
                  class="dot"
                  :class="[
                    `dot-${evt.paymentType}`, 
                    evt.isForecast ? 'is-forecast' : ''
                  ]"
                  :title="`${evt.assetTicker}: ${evt.value}`"
                ></span>
                <span v-if="cell.events.length > 4" class="dot dot-more">•••</span>
              </div>
            </div>
          </div>
        </div>

        <div class="details-panel">
          <div class="details-header">
            <h3 v-if="selectedDay">{{ selectedDay.day }} {{ currentMonthName }}</h3>
            <h3 v-else>Весь месяц</h3>
            
            <span class="details-subtitle" v-if="selectedDay && selectedDay.events.length">
              {{ selectedDay.events.length }} выплат(ы)
            </span>
          </div>

          <div class="events-list">
            <div 
              v-for="item in (selectedDay ? selectedDay.events : monthDividends)" 
              :key="item.id" 
              class="event-card"
              :class="{'forecast-card': item.isForecast}"
            >
              <div class="card-row">
                <div class="ticker-badge">{{ item.assetTicker }}</div>
                <div class="amount" :class="item.isForecast ? 'text-gray' : 'text-green'">
                  +{{ formatMoney(item.totalAmount.toFixed(2)) }} {{ item.currency }}
                </div>
              </div>
              
              <div class="card-row">
                <div class="company-name">{{ item.assetName }}</div>
                <div class="per-share">{{ item.value }} / шт</div>
              </div>

              <div class="card-footer">
                <div class="date-col">
                  <span class="date-label">Отсечка (T-1):</span>
                  <span class="date-val">{{ formatDate(item.lastBuyDate) }}</span>
                </div>
                <div class="date-col right">
                  <span class="date-label">Выплата:</span>
                  <span class="date-val">{{ formatDate(item.paymentDate) }}</span>
                </div>
              </div>
              
              <div v-if="item.isForecast" class="forecast-badge-row">
                 <span class="status-badge">ПРОГНОЗ</span>
              </div>
            </div>
            
            <div v-if="selectedDay && selectedDay.events.length === 0" class="no-events">
              Нет выплат в этот день
            </div>
             <div v-if="!selectedDay && monthDividends.length === 0" class="no-events">
              В этом месяце выплат не найдено
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
.dividends-page {
  max-width: 1200px;
  margin: 0 auto;
  padding-bottom: 40px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 60px;
  color: #6b7280;
}

/* Header */
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}
.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 4px 0;
}
.subtitle {
  color: #6b7280;
  margin: 0;
  font-size: 14px;
}

/* Calendar Controls */
.calendar-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  padding: 16px 24px;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  margin-bottom: 24px;
  border: 1px solid #e5e7eb;
}

.month-nav {
  display: flex;
  align-items: center;
  gap: 16px;
}
.month-nav h2 {
  margin: 0;
  min-width: 180px;
  text-align: center;
  font-size: 20px;
  font-weight: 600;
  color: #374151;
}

.btn-icon {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  width: 36px;
  height: 36px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #374151;
  transition: all 0.2s;
}
.btn-icon:hover {
  background: #f9fafb;
  border-color: #d1d5db;
}

.month-summary {
  text-align: right;
}
.month-summary .label {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 2px;
}
.month-summary .value {
  display: block;
  font-size: 22px;
  font-weight: 700;
  color: #374151;
}
.text-green { color: #10b981 !important; }
.text-gray { color: #9ca3af !important; }

/* Layout Grid */
.calendar-layout {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
}

@media (max-width: 900px) {
  .calendar-layout {
    grid-template-columns: 1fr;
  }
}

/* Calendar Grid */
.calendar-grid {
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  border: 1px solid #e5e7eb;
}

.week-header {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.week-day {
  text-align: center;
  padding: 12px 0;
  font-weight: 600;
  font-size: 13px;
  color: #6b7280;
  text-transform: uppercase;
}

.days-container {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
}

.calendar-cell {
  min-height: 110px;
  border-right: 1px solid #f3f4f6;
  border-bottom: 1px solid #f3f4f6;
  padding: 10px;
  cursor: pointer;
  position: relative;
  transition: background 0.2s;
}
.calendar-cell:nth-child(7n) {
  border-right: none;
}
.calendar-cell:hover {
  background: #f9fafb;
}
.calendar-cell.selected {
  background: #eff6ff;
  box-shadow: inset 0 0 0 2px #3b82f6;
}
.calendar-cell.is-today {
  background: #f0fdf4;
}
.calendar-cell.empty {
  background: #fcfcfc;
  cursor: default;
}

.day-number {
  font-weight: 600;
  font-size: 14px;
  color: #374151;
}

.events-dots {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: block;
  border: 1px solid transparent; 
  box-sizing: border-box;
}

/* Цвета по типам выплат */
.dot-dividend {
  background-color: #10b981; /* Зеленый */
  border-color: #10b981;
}

.dot-coupon {
  background-color: #3b82f6; /* Синий */
  border-color: #3b82f6;
}

.dot-amortization {
  background-color: #f59e0b; /* Оранжевый */
  border-color: #f59e0b;
}

.dot-unknown {
  background-color: #9ca3af;
  border-color: #9ca3af;
}

/* Прогнозы: "пустая" точка */
.dot.is-forecast {
  background-color: transparent;
  border-style: dashed;
}
.dot-more {
  width: auto;
  height: auto;
  background: none;
  border: none;
  color: #9ca3af;
  font-size: 10px;
  line-height: 8px;
}

/* Details Sidebar */
.details-panel {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  border: 1px solid #e5e7eb;
  padding: 20px;
  height: fit-content;
  max-height: 800px;
  overflow-y: auto;
}

.details-header {
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 12px;
  margin-bottom: 16px;
}
.details-header h3 {
  margin: 0;
  font-size: 18px;
  color: #111827;
}
.details-subtitle {
  font-size: 13px;
  color: #6b7280;
}

.events-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.event-card {
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  transition: transform 0.2s;
}
.event-card:hover {
  border-color: #d1d5db;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.03);
}
.event-card.forecast-card {
  background: #f8fafc;
  border-style: dashed;
}

.card-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.ticker-badge {
  font-weight: 700;
  font-size: 13px;
  background: #f3f4f6;
  padding: 2px 8px;
  border-radius: 6px;
  color: #374151;
}

.amount {
  font-weight: 700;
  font-size: 15px;
}

.company-name {
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 140px;
}
.per-share {
  font-size: 12px;
  color: #6b7280;
}

.card-footer {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f3f4f6;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}
.date-col {
  display: flex;
  flex-direction: column;
}
.date-col.right {
  align-items: flex-end;
}
.date-label {
  font-size: 10px;
  color: #9ca3af;
  margin-bottom: 2px;
}
.date-val {
  font-size: 12px;
  font-weight: 600;
  color: #4b5563;
}

.forecast-badge-row {
  margin-top: 6px;
  display: flex;
  justify-content: flex-end;
}

.status-badge {
  font-size: 10px;
  font-weight: 700;
  background: #e2e8f0;
  color: #64748b;
  padding: 2px 6px;
  border-radius: 4px;
}

.no-events {
  text-align: center;
  color: #9ca3af;
  padding: 24px 0;
  font-size: 14px;
}
</style>