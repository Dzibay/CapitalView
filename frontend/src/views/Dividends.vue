<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useDashboardStore } from '../stores/dashboard.store'
import { useDividendsStore } from '../stores/dividends.store'
import { getCurrencySymbol } from '../utils/currencySymbols'
import { payoutAmountToRub } from '../utils/currencyRatesToRub'
import { useUIStore } from '../stores/ui.store'
import { getDescendantPortfolioIds } from '../utils/portfolioSubtree'
import LoadingState from '../components/base/LoadingState.vue'
import PageLayout from '../layouts/PageLayout.vue'
import PageHeader from '../layouts/PageHeader.vue'
import { CheckCircle2, Clock } from 'lucide-vue-next'

// Используем stores вместо inject
const route = useRoute()
const dashboardStore = useDashboardStore()
const dividendsStore = useDividendsStore()
const uiStore = useUIStore()

// === STATE ===
const currentDate = ref(new Date()) // Текущий месяц

const months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
const weekDays = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']

/** Кэш выплат: запрос(ы) только по корневым портфелям (RPC уже отдаёт всё поддерево). Смена портфеля — фильтр из Pinia без нового запроса. */
watch(
  () => ({
    path: route.path,
    portfolioIds: (dashboardStore.portfolios || [])
      .map((p) => p.id)
      .filter((id) => id != null)
      .sort()
      .join(','),
    dashboardStamp: dashboardStore.lastFetch,
  }),
  async ({ path, portfolioIds }) => {
    if (path !== '/dividends' || !portfolioIds) return
    try {
      await dividendsStore.fetchPayoutPositionsForAllPortfolios()
    } catch (e) {
      if (import.meta.env.VITE_APP_DEV) console.error(e)
    }
  },
  { immediate: true }
)

/** Позиции выплат для выбранного портфеля и его подпортфелей (из общего кэша по portfolio_id). */
const payoutPositions = computed(() => {
  const all = dividendsStore.payoutPositionsFlat
  if (!all?.length) return []
  const sid = uiStore.selectedPortfolioId
  if (sid == null) return []
  const subtree = getDescendantPortfolioIds(dashboardStore.portfolios ?? [], sid)
  return all.filter((row) => subtree.has(row.portfolio_id))
})

/** Первый заход: ждём общий лоадер дашборда или загрузку выплат; повторный заход при непустом кэше — не блокируем весь экран. */
const dividendsPageBlocking = computed(
  () =>
    uiStore.loading ||
    (dividendsStore.payoutPositionsLoading && dividendsStore.payoutPositionsCacheIsEmpty)
)

// === COMPUTED: ДАННЫЕ ===

// 1. Список портфелей для селектора
const portfolios = computed(() => dashboardStore.portfolios ?? [])

// 2. Сбор дивидендов из отдельного API выплат
const allDividends = computed(() => {
  if (!payoutPositions.value?.length) return []

  const list = []

  payoutPositions.value.forEach(asset => {
    const payouts = asset.payouts || []

    payouts.forEach(div => {
      // --- ОПРЕДЕЛЕНИЕ ДАТ ---
      // Календарь: дата отсечки (record_date); без неё — выплата / last_buy (бэкенд сравнивает с cash_operations по payment_date).
      const mainDateStr = div.record_date || div.payment_date || div.last_buy_date
      
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

      const dy =
        div.dividend_yield != null && div.dividend_yield !== ''
          ? parseFloat(div.dividend_yield)
          : null

      list.push({
        id: div.id || `${asset.asset_id ?? asset.portfolio_asset_id}-${mainDateStr}-${div.value}`,

        assetTicker: asset.ticker,
        assetName: asset.name,

        date: calendarDate,
        lastBuyDate,
        paymentDate,

        value: parseFloat(div.value),
        /** Валюта номинала выплаты = валюта котировки актива (как в asset_payouts и на бэкенде) */
        currency: asset.currency_ticker || div.currency || 'RUB',

        /** Сумма позиции по выплате в той же валюте (для ₽-итогов — через payoutAmountToRub) */
        totalAmount:
          div.expected_total != null && div.expected_total !== ''
            ? parseFloat(div.expected_total)
            : parseFloat(div.value) * (asset.quantity || 0),

        dividendYield: Number.isFinite(dy) ? dy : null,

        status,
        isForecast: status === 'forecast' || status === 'recommended',

        paymentType,
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

// 4. Итоги за месяц в ₽: получено (сверено с операциями) и ожидается (прочее)
function _sumMonthDividendsRub(items) {
  const ref = dashboardStore.referenceData
  let sum = 0
  for (const item of items) {
    const rub = payoutAmountToRub(item.totalAmount, item.currency, ref)
    if (rub != null) sum += rub
  }
  return sum.toFixed(2)
}

function _monthItemsIncomplete(items) {
  const ref = dashboardStore.referenceData
  return items.some((item) => payoutAmountToRub(item.totalAmount, item.currency, ref) == null)
}

const monthDividendsReceived = computed(() =>
  monthDividends.value.filter((d) => d.status === 'received')
)

const monthDividendsExpected = computed(() =>
  monthDividends.value.filter((d) => d.status !== 'received')
)

const totalMonthReceived = computed(() => _sumMonthDividendsRub(monthDividendsReceived.value))

const totalMonthExpected = computed(() => _sumMonthDividendsRub(monthDividendsExpected.value))

const totalMonthIncomeIncomplete = computed(
  () =>
    _monthItemsIncomplete(monthDividendsReceived.value) ||
    _monthItemsIncomplete(monthDividendsExpected.value)
)

// Справочник (в т.ч. currency_rates_to_rub) уже грузит DashboardLayout → fetchDashboard → fetchReferenceData.
// Отдельный вызов здесь давал второй параллельный запрос: дочерний вид монтировался до заполнения store.

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

  const ref = dashboardStore.referenceData

  for (let i = 1; i <= daysInMonth; i++) {
    const dateCheck = new Date(year, month, i)
    const events = monthDividends.value.filter((d) => d.date.getDate() === i)
    let dayTotalRub = 0
    let dayIncomplete = false
    for (const item of events) {
      const rub = payoutAmountToRub(item.totalAmount, item.currency, ref)
      if (rub != null) dayTotalRub += rub
      else dayIncomplete = true
    }

    days.push({
      day: i,
      type: 'day',
      events,
      hasEvents: events.length > 0,
      isToday: isToday(dateCheck),
      dayTotalRub,
      dayTotalIncomplete: dayIncomplete,
    })
  }
  return days
})

// === МЕТОДЫ ===

function prevMonth() {
  currentDate.value = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth() - 1, 1)
}

function nextMonth() {
  currentDate.value = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth() + 1, 1)
}

function isToday(date) {
  const today = new Date()
  return date.getDate() === today.getDate() &&
         date.getMonth() === today.getMonth() &&
         date.getFullYear() === today.getFullYear()
}

const formatMoney = (val) => new Intl.NumberFormat('ru-RU').format(val)

/** Итог по дню в ячейке: +929,43 ₽ или +3,64 тыс. ₽ */
function formatDayCellTotalRub(rub, incomplete) {
  if (rub == null || rub <= 0) return ''
  const nf = new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
  let body
  if (rub >= 1000) {
    body = `${nf.format(rub / 1000)} тыс. ₽`
  } else {
    body = `${nf.format(rub)} ₽`
  }
  return incomplete ? `${body}*` : body
}

/** Сумма на карточке — в валюте выплаты; итоги по дню/месяцу считаются в ₽ отдельно */
function formatPayoutCardAmount(item) {
  const n = Number(item.totalAmount)
  if (!Number.isFinite(n)) return '—'
  return `${formatMoney(Number(n.toFixed(2)))} ${getCurrencySymbol(item.currency)}`
}

function formatDividendYieldPct(y) {
  if (y == null || !Number.isFinite(y)) return null
  return `${new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(y)}%`
}

/** Класс для левой полосы (--payout-* из main.css) */
function payoutAccentClass(paymentType) {
  if (paymentType === 'coupon') return 'payout-mini--coupon'
  if (paymentType === 'amortization') return 'payout-mini--amortization'
  if (paymentType === 'dividend') return 'payout-mini--dividend'
  return 'payout-mini--other'
}

/** Список выплат месяца по дате (для мобильной ленты) */
const monthDividendsChronological = computed(() =>
  [...monthDividends.value].sort((a, b) => a.date.getTime() - b.date.getTime())
)

const payoutRowDateFmt = new Intl.DateTimeFormat('ru-RU', {
  day: 'numeric',
  month: 'short',
})

function formatPayoutRowDate(evt) {
  if (!evt?.date) return ''
  return payoutRowDateFmt.format(evt.date).replace(/\.$/, '')
}
</script>

<template>
  <PageLayout>
    <PageHeader 
      title="Календарь выплат"
      subtitle="График дивидендов, купонов и амортизаций"
    />

    <LoadingState v-if="dividendsPageBlocking" />

    <div v-else class="dividends-content">
      <div class="calendar-controls">
        <div class="month-nav">
          <button class="btn-icon" @click="prevMonth">‹</button>
          <h2 class="month-title">
            {{ currentMonthName }} {{ currentYear }}
          </h2>
          <button class="btn-icon" @click="nextMonth">›</button>
        </div>
        
        <div class="month-summary">
          <div class="month-summary-list">
            <div class="month-summary-item">
              <span class="month-summary-ico month-summary-ico--ok" aria-hidden="true">
                <CheckCircle2 :size="20" :stroke-width="2.25" />
              </span>
              <div class="month-summary-text">
                <div class="month-summary-lbl">Получено</div>
                <div class="month-summary-val">
                  + {{ formatMoney(totalMonthReceived) }} ₽
                </div>
              </div>
            </div>
            <div class="month-summary-item">
              <span class="month-summary-ico month-summary-ico--wait" aria-hidden="true">
                <Clock :size="20" :stroke-width="2.25" />
              </span>
              <div class="month-summary-text">
                <div class="month-summary-lbl">Ожидается</div>
                <div class="month-summary-val month-summary-val--expected">
                  + {{ formatMoney(totalMonthExpected) }} ₽
                </div>
              </div>
            </div>
          </div>
          <span v-if="totalMonthIncomeIncomplete" class="month-summary-note">
            Часть выплат в валюте без курса в справочнике в сумму не входит
          </span>
        </div>
      </div>

      <div class="calendar-layout">
        <div class="calendar-grid calendar-grid--desktop">
          <div class="week-header">
            <div class="week-day" v-for="day in weekDays" :key="day">{{ day }}</div>
          </div>

          <div class="days-container">
            <div
              v-for="(cell, index) in calendarDays"
              :key="index"
              class="calendar-cell"
              :class="{
                empty: cell.type === 'empty',
                'has-events': cell.hasEvents,
                'is-today': cell.isToday,
              }"
            >
              <template v-if="cell.type === 'day'">
                <div class="cell-head">
                  <span class="day-number">{{ cell.day }}</span>
                  <span
                    v-if="cell.hasEvents && cell.dayTotalRub > 0"
                    class="day-total text-green"
                    :title="cell.dayTotalIncomplete ? 'Часть сумм без курса в ₽' : ''"
                  >
                    +{{ formatDayCellTotalRub(cell.dayTotalRub, cell.dayTotalIncomplete) }}
                  </span>
                </div>

                <div v-if="cell.hasEvents" class="payout-cards">
                  <div
                    v-for="evt in cell.events"
                    :key="evt.id"
                    class="payout-mini-card"
                    :class="[
                      payoutAccentClass(evt.paymentType),
                      {
                        'payout-mini--forecast': evt.isForecast,
                        'payout-mini--received': evt.status === 'received',
                      },
                    ]"
                  >
                    <span
                      v-if="evt.status === 'received'"
                      class="payout-mini-received-icon"
                      role="img"
                      aria-label="Выплата получена"
                      title="Выплата получена"
                    >
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <path
                          d="M20 6L9 17l-5-5"
                          stroke="currentColor"
                          stroke-width="2.5"
                          stroke-linecap="round"
                          stroke-linejoin="round"
                        />
                      </svg>
                    </span>
                    <div class="payout-mini-body">
                      <div class="payout-mini-name" :title="evt.assetName || ''">
                        {{ evt.assetName || '—' }}
                      </div>
                      <div
                        v-if="evt.assetTicker"
                        class="payout-mini-ticker"
                        :title="evt.assetTicker"
                      >
                        {{ evt.assetTicker }}
                      </div>
                      <div class="payout-mini-meta">
                        <span
                          class="payout-mini-amount"
                          :class="evt.isForecast ? 'text-muted' : ''"
                        >
                          {{ formatPayoutCardAmount(evt) }}
                        </span>
                        <template v-if="formatDividendYieldPct(evt.dividendYield)">
                          <span class="payout-mini-sep">•</span>
                          <span class="payout-mini-yield">{{
                            formatDividendYieldPct(evt.dividendYield)
                          }}</span>
                        </template>
                      </div>
                      <div v-if="evt.isForecast" class="payout-mini-badge">прогноз</div>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </div>

        <div class="mobile-payout-stack">
          <template v-if="monthDividendsChronological.length">
            <article
              v-for="evt in monthDividendsChronological"
              :key="evt.id"
              class="payout-mini-card mobile-payout-card"
              :class="[
                payoutAccentClass(evt.paymentType),
                {
                  'payout-mini--forecast': evt.isForecast,
                  'payout-mini--received': evt.status === 'received',
                },
              ]"
            >
              <div class="mobile-payout-date">{{ formatPayoutRowDate(evt) }}</div>
              <span
                v-if="evt.status === 'received'"
                class="payout-mini-received-icon"
                role="img"
                aria-label="Выплата получена"
                title="Выплата получена"
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M20 6L9 17l-5-5"
                    stroke="currentColor"
                    stroke-width="2.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </span>
              <div class="payout-mini-body">
                <div class="payout-mini-name" :title="evt.assetName || ''">
                  {{ evt.assetName || '—' }}
                </div>
                <div
                  v-if="evt.assetTicker"
                  class="payout-mini-ticker"
                  :title="evt.assetTicker"
                >
                  {{ evt.assetTicker }}
                </div>
                <div class="payout-mini-meta">
                  <span
                    class="payout-mini-amount"
                    :class="evt.isForecast ? 'text-muted' : ''"
                  >
                    {{ formatPayoutCardAmount(evt) }}
                  </span>
                  <template v-if="formatDividendYieldPct(evt.dividendYield)">
                    <span class="payout-mini-sep">•</span>
                    <span class="payout-mini-yield">{{
                      formatDividendYieldPct(evt.dividendYield)
                    }}</span>
                  </template>
                </div>
                <div v-if="evt.isForecast" class="payout-mini-badge">прогноз</div>
              </div>
            </article>
          </template>
          <p
            v-else-if="!monthDividends.length && payoutPositions.length"
            class="empty-month-hint empty-month-hint--mobile"
          >
            В этом месяце выплат не найдено
          </p>
        </div>

        <p
          v-if="!monthDividends.length && payoutPositions.length"
          class="empty-month-hint empty-month-hint--desktop"
        >
          В этом месяце выплат не найдено
        </p>
      </div>
    </div>
  </PageLayout>
</template>

<style scoped>
.dividends-content {
  width: 100%;
  min-width: 0;
  overflow-x: hidden;
  box-sizing: border-box;
}

/* Управление календарём */
.calendar-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
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
  min-width: 0;
  max-width: min(100%, 20rem);
}

.month-summary-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-items: flex-end;
  width: 100%;
}

.month-summary-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.month-summary-ico {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  line-height: 0;
  color: inherit;
}

.month-summary-ico :deep(svg) {
  display: block;
}

.month-summary-ico--ok {
  background: #dbeafe;
  color: #1d4ed8;
}

.month-summary-ico--wait {
  background: #d1fae5;
  color: #047857;
}

.month-summary-text {
  text-align: right;
  min-width: 0;
}

.month-summary-lbl {
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.25;
}

.month-summary-val {
  font-size: 16px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: #111827;
  line-height: 1.3;
}

.month-summary-val--expected {
  color: #059669;
}

.month-summary-note {
  display: block;
  font-size: 11px;
  color: #9ca3af;
  margin-top: 8px;
  max-width: 22rem;
  margin-left: auto;
  line-height: 1.35;
}
.text-green { color: #10b981 !important; }
.text-gray { color: #9ca3af !important; }

/* Календарь на всю ширину */
.calendar-layout {
  min-width: 0;
}

.empty-month-hint {
  margin: 16px 0 0;
  text-align: center;
  color: #9ca3af;
  font-size: 14px;
}

.empty-month-hint--mobile {
  display: none;
  margin-top: 8px;
}

.mobile-payout-stack {
  display: none;
}

/* Мобильная вёрстка: месяц → суммы → лента карточек на всю ширину */
@media (max-width: 768px) {
  .calendar-controls {
    flex-direction: column;
    align-items: stretch;
    gap: 16px;
    padding: 14px 16px;
    margin-bottom: 16px;
  }

  .month-nav {
    justify-content: space-between;
    width: 100%;
    order: 1;
  }

  .month-nav h2 {
    min-width: 0;
    flex: 1;
    text-align: center;
    font-size: 18px;
  }

  .month-summary {
    order: 2;
    text-align: center;
    max-width: none;
    width: 100%;
  }

  .month-summary-list {
    align-items: center;
  }

  .month-summary-text {
    text-align: center;
  }

  .month-summary-note {
    margin-left: auto;
    margin-right: auto;
    text-align: center;
  }

  .calendar-grid--desktop {
    display: none !important;
  }

  .empty-month-hint--desktop {
    display: none !important;
  }

  .empty-month-hint--mobile {
    display: block;
  }

  .mobile-payout-stack {
    display: flex;
    flex-direction: column;
    gap: 12px;
    width: 100%;
    min-width: 0;
    padding-bottom: 24px;
  }

  .mobile-payout-card {
    width: 100%;
    box-sizing: border-box;
    padding: 12px 14px 12px 12px;
    border-radius: 12px;
  }

  .mobile-payout-card .payout-mini-name {
    font-size: 13px;
  }

  .mobile-payout-card .payout-mini-ticker {
    font-size: 11px;
  }

  .mobile-payout-card .payout-mini-meta {
    font-size: 12px;
  }

  .mobile-payout-date {
    font-size: 11px;
    font-weight: 600;
    color: #9ca3af;
    text-transform: lowercase;
    margin-bottom: 8px;
    letter-spacing: 0.02em;
  }

  .mobile-payout-card.payout-mini--received .mobile-payout-date {
    padding-right: 22px;
  }

  .mobile-payout-card .payout-mini-received-icon {
    top: 10px;
    right: 10px;
  }
}

/* Сетка календаря */
.calendar-grid {
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  border: 1px solid #e5e7eb;
  min-height: 520px;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.week-header {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
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
  grid-template-columns: repeat(7, minmax(0, 1fr));
  grid-auto-rows: minmax(132px, auto);
  flex: 1;
  min-height: 0;
  min-width: 0;
}

.calendar-cell {
  min-height: 132px;
  border-right: 1px solid #f3f4f6;
  border-bottom: 1px solid #f3f4f6;
  padding: 8px 6px 6px;
  position: relative;
  transition: background 0.2s;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  box-sizing: border-box;
}
.calendar-cell:nth-child(7n) {
  border-right: none;
}
.calendar-cell:hover:not(.empty) {
  background: #fafafa;
}
.calendar-cell.is-today {
  background: #f7fdf9;
}
.calendar-cell.empty {
  background: #fcfcfc;
}

.cell-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 4px;
  flex-shrink: 0;
}

.day-number {
  font-weight: 600;
  font-size: 13px;
  color: #374151;
  line-height: 1.2;
}

.day-total {
  font-size: 10px;
  font-weight: 600;
  line-height: 1.25;
  text-align: right;
  max-width: 58%;
  word-break: break-word;
}

.payout-cards {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 6px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 1px;
}

.payout-cards::-webkit-scrollbar {
  width: 4px;
}
.payout-cards::-webkit-scrollbar-thumb {
  background: #e5e7eb;
  border-radius: 2px;
}

/* Карточка выплаты в ячейке; слева акцент по типу (--payout-* в main.css) */
.payout-mini-card {
  position: relative;
  padding: 6px 7px 6px 8px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #eef0f3;
  border-left-width: 3px;
  border-left-style: solid;
  min-width: 0;
}

.payout-mini--received {
  padding-right: 22px;
}

.payout-mini-received-icon {
  position: absolute;
  top: 5px;
  right: 5px;
  width: 15px;
  height: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--payout-dividends, #2563eb);
  pointer-events: none;
}

.payout-mini-received-icon svg {
  width: 100%;
  height: 100%;
  display: block;
}

.payout-mini--coupon .payout-mini-received-icon {
  color: var(--payout-coupons, #06b6d4);
}

.payout-mini--amortization .payout-mini-received-icon {
  color: var(--payout-amortizations, #fb923c);
}

.payout-mini--other .payout-mini-received-icon {
  color: #94a3b8;
}

.payout-mini--dividend {
  border-left-color: var(--payout-dividends, #2563eb);
}

.payout-mini--coupon {
  border-left-color: var(--payout-coupons, #06b6d4);
}

.payout-mini--amortization {
  border-left-color: var(--payout-amortizations, #fb923c);
}

.payout-mini--other {
  border-left-color: #94a3b8;
}

.payout-mini--forecast {
  border-style: dashed;
  border-left-style: solid;
  background: #fafbfc;
}

.payout-mini-body {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.payout-mini-name {
  font-size: 11px;
  font-weight: 600;
  color: #111827;
  line-height: 1.25;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.payout-mini-ticker {
  font-size: 10px;
  font-weight: 400;
  color: #9ca3af;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.payout-mini-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 3px 4px;
  font-size: 11px;
  line-height: 1.3;
}

.payout-mini-amount {
  font-weight: 700;
  color: #1f2937;
}

.payout-mini-sep {
  color: #d1d5db;
  font-weight: 400;
}

.payout-mini-yield {
  color: #9ca3af;
  font-weight: 500;
}

.payout-mini-badge {
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: #64748b;
  margin-top: 1px;
}

.text-muted {
  color: #9ca3af !important;
}
</style>