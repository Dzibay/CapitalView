<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useDashboardStore } from '../stores/dashboard.store'
import { useDividendsStore } from '../stores/dividends.store'
import { payoutAmountToRub } from '../utils/currencyRatesToRub'
import { useUIStore } from '../stores/ui.store'
import { getDescendantPortfolioIds } from '../utils/portfolioSubtree'
import { money, moneyCompact, plural, dateShort } from '../cabinet/format'
import { kindOf, MONTHS_IN } from '../cabinet/dividends/payoutTypes'

import CvPageHead from '../cabinet/ui/CvPageHead.vue'
import CvKpiStrip from '../cabinet/ui/CvKpiStrip.vue'
import DashboardSkeleton from '../cabinet/dashboard/DashboardSkeleton.vue'
import PayoutYearWidget from '../cabinet/dividends/PayoutYearWidget.vue'
import PayoutCalendarWidget from '../cabinet/dividends/PayoutCalendarWidget.vue'
import PayoutListWidget from '../cabinet/dividends/PayoutListWidget.vue'

const route = useRoute()
const dashboardStore = useDashboardStore()
const dividendsStore = useDividendsStore()
const uiStore = useUIStore()

/** выплаты хотя бы раз загружены — до этого пустой список ещё не значит «выплат нет» */
const fetched = ref(!dividendsStore.payoutPositionsCacheIsEmpty)

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
    } finally {
      fetched.value = true
    }
  },
  { immediate: true }
)
// портфелей нет вовсе — грузить нечего
watch(
  () => !!dashboardStore.lastFetch && !uiStore.loading && !(dashboardStore.portfolios || []).length,
  (none) => { if (none) fetched.value = true },
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
const blocking = computed(
  () =>
    uiStore.loading ||
    !fetched.value ||
    (dividendsStore.payoutPositionsLoading && dividendsStore.payoutPositionsCacheIsEmpty)
)

const selectedPortfolio = computed(() => (dashboardStore.portfolios || []).find((p) => p.id === uiStore.selectedPortfolioId))

// ── события выплат ─────────────────────────────────────────────────────────
const events = computed(() => {
  const refData = dashboardStore.referenceData
  const list = []
  for (const asset of payoutPositions.value) {
    for (const div of asset.payouts || []) {
      // Календарь: дата отсечки (record_date); без неё — выплата / last_buy (бэкенд сравнивает с cash_operations по payment_date).
      const mainDateStr = div.record_date || div.payment_date || div.last_buy_date
      if (!mainDateStr) continue
      const status = div.type === 'forecast' ? 'forecast' : div.status || 'unknown'

      const basisRaw = div.basis_quantity != null && div.basis_quantity !== '' ? parseFloat(div.basis_quantity) : null
      const basisQty = Number.isFinite(basisRaw) ? basisRaw : asset.quantity || 0
      const amount = div.expected_total != null && div.expected_total !== '' ? parseFloat(div.expected_total) : parseFloat(div.value) * basisQty
      if (!Number.isFinite(amount) || amount <= 0) continue

      const dy = div.dividend_yield != null && div.dividend_yield !== '' ? parseFloat(div.dividend_yield) : null
      /** Валюта номинала выплаты = валюта котировки актива (как в asset_payouts и на бэкенде) */
      const currency = asset.currency_ticker || div.currency || 'RUB'
      const date = new Date(mainDateStr)
      date.setHours(0, 0, 0, 0)

      list.push({
        id: div.id || `${asset.asset_id ?? asset.portfolio_asset_id}-${mainDateStr}-${div.value}`,
        assetId: asset.asset_id,
        ticker: asset.ticker,
        name: asset.name || asset.ticker,
        date,
        kind: kindOf(div.type),
        amount,
        currency,
        rub: payoutAmountToRub(amount, currency, refData),
        yield: Number.isFinite(dy) ? dy : null,
        received: status === 'received',
        forecast: status === 'forecast' || status === 'recommended',
      })
    }
  }
  return list.sort((a, b) => a.date - b.date)
})

// ── выбранный месяц и день ─────────────────────────────────────────────────
const now = new Date()
const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
const year = ref(now.getFullYear())
const month = ref(now.getMonth())
const day = ref(null)
watch([year, month], () => { day.value = null })

function shift(n) {
  const d = new Date(year.value, month.value + n, 1)
  year.value = d.getFullYear()
  month.value = d.getMonth()
}
function goToday() {
  year.value = now.getFullYear()
  month.value = now.getMonth()
}

const monthEvents = computed(() => events.value.filter((e) => e.date.getFullYear() === year.value && e.date.getMonth() === month.value))
const sumRub = (list) => list.reduce((s, e) => s + (e.rub || 0), 0)
const incomplete = computed(() => monthEvents.value.some((e) => e.rub == null))

// ── шапка и ключевые показатели ───────────────────────────────────────────
const upcoming = computed(() => events.value.filter((e) => !e.received && e.date >= today))
const next = computed(() => upcoming.value[0] || null)
const last12 = computed(() => {
  const from = new Date(today.getFullYear() - 1, today.getMonth(), today.getDate())
  return sumRub(events.value.filter((e) => e.received && e.date > from && e.date <= today))
})
const next12 = computed(() => {
  const to = new Date(today.getFullYear() + 1, today.getMonth(), today.getDate())
  return sumRub(upcoming.value.filter((e) => e.date < to))
})

const count = (n) => `${n} ${plural(n, 'выплата', 'выплаты', 'выплат')}`

const meta = computed(() => {
  const n = new Set(events.value.map((e) => e.assetId ?? e.ticker)).size
  const list = [`${n} ${plural(n, 'платящий актив', 'платящих актива', 'платящих активов')}`]
  if (upcoming.value.length) list.push(`${count(upcoming.value.length)} впереди`)
  return list
})

const kpis = computed(() => {
  const rec = monthEvents.value.filter((e) => e.received)
  const exp = monthEvents.value.filter((e) => !e.received)
  const m = MONTHS_IN[month.value]
  const n = next.value
  const daysTo = n ? Math.round((n.date - today) / 86400000) : 0
  return [
    { key: 'rec', label: `Получено в ${m}`, value: sumRub(rec), format: (v) => money(v), note: count(rec.length) },
    { key: 'exp', label: `Ожидается в ${m}`, value: sumRub(exp), format: (v) => money(v), note: incomplete.value ? `${count(exp.length)} · без части валют*` : count(exp.length) },
    {
      key: 'next', label: 'Следующая выплата', value: n ? n.rub ?? n.amount : 0, format: (v) => money(v),
      note: n ? `${n.ticker || n.name} · ${daysTo === 0 ? 'сегодня' : daysTo === 1 ? 'завтра' : dateShort(n.date)}` : 'не запланирована',
    },
    { key: 'year', label: 'Ожидается за 12 месяцев', value: next12.value, format: (v) => money(v), note: `за прошлые 12 — ${moneyCompact(last12.value)}` },
  ]
})

// каскадное появление — только при первом показе
const intro = ref(true)
watch(blocking, (b) => { if (!b) setTimeout(() => { intro.value = false }, 1600) }, { immediate: true })
</script>

<template>
  <div class="dv">
    <Transition name="dv-swap" mode="out-in">
      <DashboardSkeleton v-if="blocking" key="skel" />

      <div v-else key="ready">
        <CvPageHead :eyebrow="selectedPortfolio?.name || 'Портфель'" title="Календарь выплат" :meta="meta" />

        <div v-if="!events.length" class="dv__empty cv-card">
          <b>Выплат пока нет</b>
          <p>Когда в портфеле появятся акции с дивидендами или облигации с купонами, их график будет здесь.</p>
        </div>

        <div v-else class="cv-grid" :class="{ 'is-intro': intro }">
          <CvKpiStrip class="is-xl" :items="kpis" :style="{ '--i': 0 }" />

          <PayoutYearWidget
            class="is-xl"
            :style="{ '--i': 1 }"
            :events="events"
            :year="year"
            :month="month"
            @select="month = $event"
            @year="year = $event"
          />

          <PayoutCalendarWidget
            v-model:day="day"
            class="is-l"
            :style="{ '--i': 2 }"
            :events="monthEvents"
            :year="year"
            :month="month"
            @prev="shift(-1)"
            @next="shift(1)"
            @today="goToday"
          />
          <PayoutListWidget
            v-model:day="day"
            class="is-s is-full-md"
            :style="{ '--i': 3 }"
            :events="monthEvents"
            :month="month"
          />
        </div>

        <p v-if="incomplete" class="dv__note">* Часть выплат в валюте без курса в справочнике — в суммы в рублях они не входят.</p>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.dv { padding-bottom: 8px; }
.dv__empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 48px 16px; text-align: center; color: var(--cv-mut); }
.dv__empty b { color: var(--cv-ink); font-size: 15px; }
.dv__empty p { margin: 0; max-width: 440px; font-size: 13.5px; }
.dv__note { margin: 14px 0 0; font-size: 12px; color: var(--cv-dim); }

.dv-swap-enter-active { transition: opacity .35s var(--cv-ease); }
.dv-swap-leave-active { transition: opacity .15s ease; }
.dv-swap-enter-from, .dv-swap-leave-to { opacity: 0; }
</style>
