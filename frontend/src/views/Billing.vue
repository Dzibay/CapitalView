<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Check, Clock3, ShieldCheck, Sparkles, Zap } from 'lucide-vue-next'
import PageLayout from '../layouts/PageLayout.vue'
import LoadingState from '../components/base/LoadingState.vue'
import { billingService } from '../services/billingService'
import { useAuthStore } from '../stores/auth.store'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const payingId = ref(null)
const error = ref('')
const info = ref('')
const trialDays = ref(14)
const tariffs = ref([])
const subscription = ref(null)
const timeline = ref(null)

const hasAccess = computed(() => Boolean(subscription.value?.has_access || authStore.user?.is_admin))
const isExpired = computed(() => !hasAccess.value)

const statusTitle = computed(() => {
  if (subscription.value?.status === 'trial') return 'Пробный период'
  if (subscription.value?.status === 'active') return 'Подписка активна'
  return 'Доступ приостановлен'
})

const daysLeft = computed(() => {
  const d = timeline.value?.days_left
  return typeof d === 'number' ? d : null
})

const daysLeftLabel = computed(() => {
  const d = daysLeft.value
  if (d == null) return 'Срок не задан'
  if (d > 0) return `Осталось ${daysWord(d)}`
  if (d === 0) return 'Истекает сегодня'
  return `Истекла ${daysWord(Math.abs(d))} назад`
})

function daysWord(n) {
  const abs = Math.abs(n)
  const mod10 = abs % 10
  const mod100 = abs % 100
  let unit = 'дней'
  if (mod10 === 1 && mod100 !== 11) unit = 'день'
  else if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) unit = 'дня'
  return `${abs} ${unit}`
}

function formatDate(value, withYear = true) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short',
    ...(withYear ? { year: 'numeric' } : {}),
  })
}

function formatPrice(v) {
  return Number(v || 0).toLocaleString('ru-RU', { maximumFractionDigits: 0 })
}

function periodLabel(days) {
  const d = Number(days) || 0
  if (d >= 360) return 'в год'
  if (d >= 170) return 'за 6 месяцев'
  if (d >= 28 && d <= 31) return 'в месяц'
  return `за ${d} дн.`
}

function periodTitle(days) {
  const d = Number(days) || 0
  if (d >= 360) return 'Год'
  if (d >= 170) return 'Полгода'
  if (d >= 28 && d <= 31) return 'Месяц'
  return `${d} дн.`
}

function monthlyEquivalent(t) {
  const days = Number(t.period_days) || 0
  const price = Number(t.price_rub) || 0
  if (days <= 0 || price <= 0) return null
  return Math.round(price / (days / 30.4))
}

function isFeatured(t) {
  const days = Number(t.period_days) || 0
  return days >= 170 && days < 360
}

function sortedTariffs() {
  return [...(tariffs.value || [])].sort(
    (a, b) => (Number(a.period_days) || 0) - (Number(b.period_days) || 0)
  )
}

const orderedTariffs = computed(() => sortedTariffs())

const monthlyBasePrice = computed(() => {
  const monthly = orderedTariffs.value.find((t) => {
    const d = Number(t.period_days) || 0
    return d >= 28 && d <= 31
  })
  return monthly ? monthlyEquivalent(monthly) : null
})

function savingsVsMonthly(t) {
  const base = monthlyBasePrice.value
  const eq = monthlyEquivalent(t)
  const days = Number(t.period_days) || 0
  if (!base || !eq || days <= 31) return null
  const pct = Math.round((1 - eq / base) * 100)
  return pct > 0 ? pct : null
}

const sharedFeatures = computed(() => {
  const withFeatures = orderedTariffs.value.find((t) => Array.isArray(t.features) && t.features.length)
  if (withFeatures) return withFeatures.features
  return ['Портфели и импорт брокеров', 'Аналитика и цели', 'Поддержка']
})

/** Прогресс и события шкалы без наложений подписей на трек */
const scaleModel = computed(() => {
  const tl = timeline.value
  if (!tl?.registered_at || !tl?.access_ends_at) {
    return { milestones: [], progressPct: 0, todayLabel: '' }
  }
  const start = new Date(tl.registered_at).getTime()
  const end = new Date(tl.access_ends_at).getTime()
  const now = new Date(tl.today || Date.now()).getTime()
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
    return { milestones: [], progressPct: 0, todayLabel: '' }
  }

  const span = end - start
  const pct = (ts) => Math.min(100, Math.max(0, ((ts - start) / span) * 100))
  const progressPct = pct(now)

  const milestones = [
    {
      key: 'reg',
      tone: 'start',
      title: 'Старт',
      detail: 'Регистрация',
      date: tl.registered_at,
      done: true,
    },
  ]

  for (const ev of tl.events || []) {
    if (ev.type !== 'payment' || !ev.at) continue
    const at = new Date(ev.at).getTime()
    milestones.push({
      key: `pay-${ev.payment_id || ev.at}`,
      tone: 'pay',
      title: 'Оплата',
      detail: ev.label || 'Продление',
      date: ev.at,
      done: at <= now,
    })
  }

  milestones.push({
    key: 'end',
    tone: hasAccess.value ? 'end' : 'expired',
    title: hasAccess.value ? 'Окончание' : 'Истекла',
    detail: hasAccess.value ? 'Конец текущего периода' : 'Доступ закрыт',
    date: tl.access_ends_at,
    done: !hasAccess.value,
  })

  return {
    milestones,
    progressPct,
    todayLabel: formatDate(tl.today || new Date().toISOString(), false),
  }
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await billingService.fetchMe()
    subscription.value = data.subscription
    tariffs.value = data.tariffs || []
    trialDays.value = data.trial_days
    timeline.value = data.timeline
    if (authStore.user) {
      authStore.setUser({ ...authStore.user, subscription: data.subscription })
    }
  } catch (e) {
    error.value = e.response?.data?.detail?.error
      || e.response?.data?.detail
      || e.message
      || 'Не удалось загрузить тарифы'
  } finally {
    loading.value = false
  }
}

async function pay(tariff) {
  payingId.value = tariff.id
  error.value = ''
  info.value = ''
  try {
    const returnUrl = `${window.location.origin}/billing?payment=return`
    const payment = await billingService.createPayment(tariff.id, returnUrl)
    if (payment?.confirmation_url) {
      window.location.href = payment.confirmation_url
      return
    }
    info.value = 'Платёж создан. Обновите страницу через минуту.'
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Не удалось создать платёж'
  } finally {
    payingId.value = null
  }
}

onMounted(async () => {
  if (route.query.payment === 'return') {
    info.value = 'Если оплата прошла успешно, подписка активируется в течение минуты.'
  }
  await load()
})
</script>

<template>
  <PageLayout>
    <LoadingState v-if="loading" />

    <div v-else class="bill">
      <section class="bill-hero" :class="{ 'bill-hero--expired': isExpired }">
        <div class="bill-hero__copy">
          <p class="bill-eyebrow">
            <Sparkles :size="14" :stroke-width="2.25" />
            CapitalView · Подписка
          </p>
          <h1>{{ statusTitle }}</h1>
          <p class="bill-lead">
            <template v-if="isExpired">
              Портфель и аналитика снова откроются сразу после оплаты.
              Настройки и поддержка доступны без ограничений.
            </template>
            <template v-else-if="subscription?.status === 'trial'">
              Полный доступ до {{ formatDate(subscription.trial_ends_at) }}.
              Оформите тариф заранее — доступ продолжится без паузы.
            </template>
            <template v-else>
              Доступ до {{ formatDate(subscription?.current_period_ends_at || subscription?.access_ends_at) }}
              <template v-if="subscription?.tariff"> · {{ subscription.tariff.name }}</template>.
            </template>
          </p>
          <div class="bill-remain" :class="{ 'bill-remain--danger': isExpired || (daysLeft != null && daysLeft <= 7) }">
            <Clock3 :size="18" />
            <span>{{ daysLeftLabel }}</span>
          </div>
          <ul class="bill-perks">
            <li><ShieldCheck :size="16" /> Все портфели и импорт брокеров</li>
            <li><Zap :size="16" /> Аналитика, цели и прогнозы</li>
          </ul>
        </div>
        <div class="bill-hero__visual" aria-hidden="true">
          <img src="/billing-hero.png" alt="" width="640" height="360" />
        </div>
      </section>

      <p v-if="error" class="msg msg-error">{{ error }}</p>
      <p v-if="info" class="msg msg-info">{{ info }}</p>

      <section v-if="scaleModel.milestones.length" class="bill-journey" aria-label="История подписки">
        <div class="bill-journey__head">
          <div>
            <h2>Ваш путь</h2>
            <p>От регистрации до окончания текущего периода</p>
          </div>
          <div class="bill-journey__today">
            <span>Сегодня</span>
            <strong>{{ scaleModel.todayLabel }}</strong>
          </div>
        </div>

        <div class="bill-progress" role="progressbar" :aria-valuenow="Math.round(scaleModel.progressPct)" aria-valuemin="0" aria-valuemax="100">
          <div class="bill-progress__track">
            <div class="bill-progress__fill" :style="{ width: scaleModel.progressPct + '%' }" />
            <div class="bill-progress__now" :style="{ left: scaleModel.progressPct + '%' }" />
          </div>
          <div class="bill-progress__meta">
            <span>Начало</span>
            <span>{{ Math.round(scaleModel.progressPct) }}%</span>
            <span>Конец периода</span>
          </div>
        </div>

        <ol class="bill-steps">
          <li
            v-for="m in scaleModel.milestones"
            :key="m.key"
            class="bill-step"
            :class="[`bill-step--${m.tone}`, { 'bill-step--done': m.done }]"
          >
            <span class="bill-step__dot" aria-hidden="true" />
            <div class="bill-step__body">
              <strong>{{ m.title }}</strong>
              <span>{{ m.detail }}</span>
              <time>{{ formatDate(m.date) }}</time>
            </div>
          </li>
        </ol>
      </section>

      <section class="bill-plans">
        <header class="bill-plans__head">
          <h2>Выберите тариф</h2>
          <p>Один полный доступ — отличаются только длительность и цена. Оплата через ЮKassa.</p>
        </header>

        <ul v-if="orderedTariffs.length" class="bill-includes">
          <li v-for="(f, i) in sharedFeatures" :key="i">
            <Check :size="14" :stroke-width="2.5" />
            {{ f }}
          </li>
        </ul>

        <div v-if="!orderedTariffs.length" class="empty">
          Тарифы пока не настроены. Напишите в поддержку или зайдите позже.
        </div>

        <div v-else class="tariff-grid">
          <article
            v-for="t in orderedTariffs"
            :key="t.id"
            class="tariff"
            :class="{ 'tariff--featured': isFeatured(t) }"
          >
            <div class="tariff__ribbon" v-if="isFeatured(t)">Выгоднее всего</div>

            <div class="tariff__period">{{ periodTitle(t.period_days) }}</div>
            <div class="tariff__name">{{ t.name }}</div>

            <div class="tariff__price">
              <span class="tariff__amount">{{ formatPrice(t.price_rub) }}</span>
              <span class="tariff__currency">₽</span>
            </div>
            <div class="tariff__meta">
              <span>{{ periodLabel(t.period_days) }}</span>
              <span v-if="monthlyEquivalent(t) && Number(t.period_days) > 31" class="tariff__eq">
                · {{ formatPrice(monthlyEquivalent(t)) }} ₽/мес
              </span>
            </div>

            <div v-if="savingsVsMonthly(t)" class="tariff__save">
              Экономия {{ savingsVsMonthly(t) }}% к месячному
            </div>
            <div v-else class="tariff__save tariff__save--spacer" aria-hidden="true" />

            <button
              type="button"
              class="tariff__cta"
              :disabled="payingId === t.id"
              @click="pay(t)"
            >
              {{ payingId === t.id ? 'Переход…' : (isExpired ? 'Возобновить' : 'Выбрать') }}
            </button>
          </article>
        </div>
      </section>

      <p class="note">
        Новым пользователям — пробный период {{ daysWord(trialDays) }} без привязки карты до оплаты.
      </p>

      <button
        v-if="hasAccess"
        type="button"
        class="linkish"
        @click="router.push('/dashboard')"
      >
        Вернуться в кабинет
      </button>
    </div>
  </PageLayout>
</template>

<style scoped>
.bill {
  max-width: 1080px;
  display: flex;
  flex-direction: column;
  gap: 28px;
  padding-bottom: 32px;
}

.bill-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(220px, 0.8fr);
  gap: 24px;
  align-items: stretch;
  padding: 28px;
  border-radius: 24px;
  border: 1px solid rgba(47, 95, 143, 0.12);
  background:
    radial-gradient(120% 80% at 0% 0%, rgba(74, 122, 173, 0.14), transparent 55%),
    linear-gradient(165deg, #f4f7fb 0%, #ffffff 55%, #eef3f8 100%);
  overflow: hidden;
}

.bill-hero--expired {
  background:
    radial-gradient(100% 80% at 0% 0%, rgba(209, 67, 67, 0.1), transparent 50%),
    linear-gradient(165deg, #fbf4f4 0%, #ffffff 55%, #f7eef0 100%);
  border-color: rgba(209, 67, 67, 0.14);
}

.bill-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 12px;
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #2f5f8f;
}

.bill-hero h1 {
  margin: 0 0 12px;
  font-size: clamp(30px, 3.6vw, 42px);
  font-weight: 700;
  letter-spacing: -0.035em;
  line-height: 1.08;
  color: #0f1c2e;
}

.bill-lead {
  margin: 0 0 18px;
  color: #5a6b7d;
  font-size: 15.5px;
  line-height: 1.55;
  max-width: 44ch;
}

.bill-remain {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 999px;
  background: rgba(47, 95, 143, 0.1);
  color: #1e3f61;
  font-weight: 650;
  font-size: 14px;
}

.bill-remain--danger {
  background: rgba(209, 67, 67, 0.1);
  color: #a83232;
}

.bill-perks {
  list-style: none;
  margin: 18px 0 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
}

.bill-perks li {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  font-weight: 550;
  color: #3d4f63;
}

.bill-perks svg {
  color: #2f5f8f;
  flex-shrink: 0;
}

.bill-hero__visual {
  position: relative;
  border-radius: 18px;
  overflow: hidden;
  min-height: 220px;
  background: #d5dde8;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.35);
}

.bill-hero__visual img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

/* Journey / progress */
.bill-journey {
  padding: 24px;
  border-radius: 22px;
  border: 1px solid rgba(47, 95, 143, 0.1);
  background: #fff;
  box-shadow: 0 12px 40px rgba(15, 28, 46, 0.04);
}

.bill-journey__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}

.bill-journey__head h2 {
  margin: 0 0 4px;
  font-size: 20px;
  letter-spacing: -0.02em;
  color: #0f1c2e;
}

.bill-journey__head p {
  margin: 0;
  color: #6b7c8d;
  font-size: 14px;
}

.bill-journey__today {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  padding: 8px 12px;
  border-radius: 12px;
  background: #f4f7fb;
}

.bill-journey__today span {
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #6b7c8d;
}

.bill-journey__today strong {
  font-size: 14px;
  color: #0f1c2e;
}

.bill-progress {
  margin-bottom: 22px;
}

.bill-progress__track {
  position: relative;
  height: 10px;
  border-radius: 999px;
  background: #e8eef4;
  overflow: visible;
}

.bill-progress__fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #6a9bc4, #2f5f8f);
  transition: width 0.4s ease;
}

.bill-progress__now {
  position: absolute;
  top: 50%;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #0f1c2e;
  border: 3px solid #fff;
  box-shadow: 0 2px 8px rgba(15, 28, 46, 0.25);
  transform: translate(-50%, -50%);
  z-index: 2;
}

.bill-progress__meta {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  font-size: 12px;
  color: #6b7c8d;
}

.bill-progress__meta span:nth-child(2) {
  font-weight: 700;
  color: #2f5f8f;
}

.bill-steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.bill-step {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 14px 14px 14px 12px;
  border-radius: 14px;
  background: #f7f9fc;
  border: 1px solid transparent;
}

.bill-step--done {
  background: #f0f7f4;
  border-color: rgba(26, 154, 110, 0.12);
}

.bill-step__dot {
  width: 10px;
  height: 10px;
  margin-top: 5px;
  border-radius: 50%;
  flex-shrink: 0;
  background: #94a3b8;
  box-shadow: 0 0 0 4px rgba(148, 163, 184, 0.18);
}

.bill-step--start .bill-step__dot,
.bill-step--done .bill-step__dot {
  background: #1a9a6e;
  box-shadow: 0 0 0 4px rgba(26, 154, 110, 0.16);
}

.bill-step--pay .bill-step__dot {
  background: #c48a1a;
  box-shadow: 0 0 0 4px rgba(196, 138, 26, 0.16);
}

.bill-step--end .bill-step__dot {
  background: #2f5f8f;
  box-shadow: 0 0 0 4px rgba(47, 95, 143, 0.16);
}

.bill-step--expired .bill-step__dot {
  background: #d14343;
  box-shadow: 0 0 0 4px rgba(209, 67, 67, 0.14);
}

.bill-step__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.bill-step__body strong {
  font-size: 14px;
  color: #0f1c2e;
  letter-spacing: -0.01em;
}

.bill-step__body span {
  font-size: 13px;
  color: #5a6b7d;
  line-height: 1.35;
}

.bill-step__body time {
  margin-top: 4px;
  font-size: 12px;
  color: #8494a5;
}

/* Plans */
.bill-plans__head {
  margin-bottom: 16px;
  text-align: center;
}

.bill-plans__head h2 {
  margin: 0 0 6px;
  font-size: 24px;
  letter-spacing: -0.03em;
  color: #0f1c2e;
}

.bill-plans__head p {
  margin: 0 auto;
  max-width: 40ch;
  color: #64748b;
  font-size: 14px;
  line-height: 1.5;
}

.bill-includes {
  list-style: none;
  margin: 0 auto 22px;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px 18px;
  max-width: 720px;
}

.bill-includes li {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #3d4f63;
}

.bill-includes svg {
  color: #1a9a6e;
  flex-shrink: 0;
}

.tariff-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  align-items: stretch;
  margin-top: 10px;
  padding-top: 8px;
}

.tariff {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 28px 20px 22px;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  background: #fff;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.tariff:hover {
  border-color: #c5d0dc;
  box-shadow: 0 10px 28px rgba(15, 28, 46, 0.06);
}

.tariff--featured {
  border-color: #2f5f8f;
  background: #f7fafc;
  box-shadow: 0 12px 32px rgba(47, 95, 143, 0.1);
}

.tariff__ribbon {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translate(-50%, -50%);
  padding: 5px 12px;
  border-radius: 999px;
  background: #1e3f61;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.tariff__period {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #2f5f8f;
  margin-bottom: 4px;
}

.tariff__name {
  font-size: 13px;
  color: #8494a5;
  margin-bottom: 18px;
  line-height: 1.3;
  max-width: 18ch;
}

.tariff__price {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 3px;
  color: #0f1c2e;
  line-height: 1;
}

.tariff__amount {
  font-size: 42px;
  font-weight: 700;
  letter-spacing: -0.045em;
  font-variant-numeric: tabular-nums;
}

.tariff__currency {
  margin-top: 6px;
  font-size: 16px;
  font-weight: 650;
  color: #5a6b7d;
}

.tariff__meta {
  margin-top: 8px;
  font-size: 13px;
  color: #6b7c8d;
}

.tariff__eq {
  color: #3d4f63;
  font-weight: 550;
}

.tariff__save {
  margin-top: 12px;
  min-height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 10px;
  border-radius: 8px;
  background: rgba(26, 154, 110, 0.1);
  color: #0f7a54;
  font-size: 12px;
  font-weight: 650;
}

.tariff__save--spacer {
  background: transparent;
  visibility: hidden;
}

.tariff__cta {
  margin-top: 16px;
  width: 100%;
  border: 1px solid #2f5f8f;
  border-radius: 10px;
  padding: 12px 14px;
  background: #fff;
  color: #1e3f61;
  font: inherit;
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.tariff__cta:hover {
  background: #2f5f8f;
  color: #fff;
}

.tariff--featured .tariff__cta {
  background: #1e3f61;
  border-color: #1e3f61;
  color: #fff;
}

.tariff--featured .tariff__cta:hover {
  background: #16324d;
  border-color: #16324d;
}

.tariff__cta:disabled {
  opacity: 0.65;
  cursor: wait;
}

.note,
.empty {
  color: #64748b;
  font-size: 13px;
  text-align: center;
}

.msg {
  margin: 0;
  padding: 12px 14px;
  border-radius: 12px;
  font-size: 14px;
}

.msg-error {
  background: #fef2f2;
  color: #b91c1c;
}

.msg-info {
  background: #eff6ff;
  color: #1d4ed8;
}

.linkish {
  align-self: center;
  border: none;
  background: none;
  color: #2f5f8f;
  font: inherit;
  font-weight: 650;
  cursor: pointer;
  padding: 0;
}

@media (max-width: 960px) {
  .tariff-grid {
    grid-template-columns: 1fr;
    max-width: 340px;
    margin: 0 auto;
    width: 100%;
  }

  .tariff {
    padding-top: 32px;
  }
}

@media (max-width: 860px) {
  .bill-hero {
    grid-template-columns: 1fr;
    padding: 22px;
  }

  .bill-hero__visual {
    min-height: 160px;
    order: -1;
  }

  .bill-journey__head {
    flex-direction: column;
  }

  .bill-journey__today {
    align-items: flex-start;
  }
}
</style>
