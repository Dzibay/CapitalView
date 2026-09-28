<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Check, Clock3, Sparkles } from 'lucide-vue-next'
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
  if (subscription.value?.status === 'active') return 'Активная подписка'
  return 'Подписка истекла'
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
  if (d >= 360) return 'год'
  if (d >= 170) return '6 месяцев'
  if (d >= 28 && d <= 31) return 'месяц'
  return `${d} дн.`
}

function isFeatured(t) {
  const days = Number(t.period_days) || 0
  return days >= 170 && days < 360
}

/** Позиции маркеров на шкале 0..100 */
const scaleModel = computed(() => {
  const tl = timeline.value
  if (!tl?.registered_at || !tl?.access_ends_at) {
    return { markers: [], todayPct: 0, progressPct: 0 }
  }
  const start = new Date(tl.registered_at).getTime()
  const end = new Date(tl.access_ends_at).getTime()
  const now = new Date(tl.today || Date.now()).getTime()
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
    return { markers: [], todayPct: 0, progressPct: 0 }
  }

  const span = end - start
  const pct = (ts) => Math.min(100, Math.max(0, ((ts - start) / span) * 100))

  const markers = []
  markers.push({
    key: 'reg',
    type: 'registration',
    pct: 0,
    label: 'Регистрация',
    date: tl.registered_at,
  })

  for (const ev of tl.events || []) {
    if (ev.type !== 'payment' || !ev.at) continue
    markers.push({
      key: `pay-${ev.payment_id || ev.at}`,
      type: 'payment',
      pct: pct(new Date(ev.at).getTime()),
      label: ev.label || 'Оплата',
      date: ev.at,
    })
  }

  markers.push({
    key: 'end',
    type: 'expires',
    pct: 100,
    label: hasAccess.value ? 'Окончание' : 'Истекла',
    date: tl.access_ends_at,
  })

  const todayPct = pct(now)
  const progressPct = Math.min(100, Math.max(0, todayPct))

  return { markers, todayPct, progressPct }
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
            Подписка CapitalView
          </p>
          <h1>{{ statusTitle }}</h1>
          <p class="bill-lead">
            <template v-if="isExpired">
              Доступ к портфелю приостановлен. Данные недоступны, пока не будет оформлен тариф.
              Остаются настройки, поддержка и эта страница.
            </template>
            <template v-else-if="subscription?.status === 'trial'">
              Полный доступ до {{ formatDate(subscription.trial_ends_at) }}.
              После пробного периода выберите удобный срок подписки.
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
        </div>
        <div class="bill-hero__visual" aria-hidden="true">
          <img src="/billing-hero.png" alt="" width="640" height="360" />
        </div>
      </section>

      <p v-if="error" class="msg msg-error">{{ error }}</p>
      <p v-if="info" class="msg msg-info">{{ info }}</p>

      <section v-if="scaleModel.markers.length" class="bill-scale" aria-label="Шкала подписки">
        <div class="bill-scale__track">
          <div class="bill-scale__fill" :style="{ width: scaleModel.progressPct + '%' }" />
          <div
            class="bill-scale__today"
            :style="{ left: scaleModel.todayPct + '%' }"
            title="Сегодня"
          >
            <span>Сегодня</span>
          </div>
          <div
            v-for="m in scaleModel.markers"
            :key="m.key"
            class="bill-scale__mark"
            :class="`bill-scale__mark--${m.type}`"
            :style="{ left: m.pct + '%' }"
          >
            <i />
            <em>{{ m.label }}</em>
            <small>{{ formatDate(m.date, false) }}</small>
          </div>
        </div>
      </section>

      <section class="bill-plans">
        <header class="bill-plans__head">
          <h2>Тарифы</h2>
          <p>Один полный доступ — отличается только сроком. Оплата через ЮKassa.</p>
        </header>

        <div v-if="!tariffs.length" class="empty">
          Тарифы пока не настроены. Напишите в поддержку или зайдите позже.
        </div>

        <div v-else class="tariff-grid">
          <article
            v-for="t in tariffs"
            :key="t.id"
            class="tariff-card"
            :class="{ 'tariff-card--featured': isFeatured(t) }"
          >
            <div v-if="isFeatured(t)" class="tariff-badge">Выгодно</div>
            <h3>{{ t.name }}</h3>
            <p class="price">
              {{ formatPrice(t.price_rub) }} ₽
              <span>/ {{ periodLabel(t.period_days) }}</span>
            </p>
            <p v-if="t.description" class="desc">{{ t.description }}</p>
            <ul v-if="t.features?.length">
              <li v-for="(f, i) in t.features" :key="i">
                <Check :size="15" :stroke-width="2.5" />
                {{ f }}
              </li>
            </ul>
            <button
              type="button"
              class="btn-pay"
              :disabled="payingId === t.id"
              @click="pay(t)"
            >
              {{ payingId === t.id ? 'Переход к оплате…' : (isExpired ? 'Продлить доступ' : 'Оплатить') }}
            </button>
          </article>
        </div>
      </section>

      <p class="note">
        Новым пользователям — пробный период {{ daysWord(trialDays) }}.
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
  max-width: 1040px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding-bottom: 24px;
}

.bill-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
  gap: 20px;
  align-items: stretch;
  padding: 22px;
  border-radius: 20px;
  border: 1px solid var(--border-subtle, #d8dee6);
  background:
    linear-gradient(135deg, rgba(47, 95, 143, 0.08), rgba(238, 241, 244, 0.9) 42%, #fff 100%);
  overflow: hidden;
}

.bill-hero--expired {
  background:
    linear-gradient(135deg, rgba(209, 67, 67, 0.08), rgba(238, 241, 244, 0.92) 45%, #fff 100%);
}

.bill-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 10px;
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--primary, #2f5f8f);
}

.bill-hero h1 {
  margin: 0 0 10px;
  font-size: clamp(28px, 3.4vw, 40px);
  font-weight: 650;
  letter-spacing: -0.03em;
  line-height: 1.1;
  color: #132033;
}

.bill-lead {
  margin: 0 0 16px;
  color: #5b6b7c;
  font-size: 15px;
  line-height: 1.55;
  max-width: 42ch;
}

.bill-remain {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(47, 95, 143, 0.1);
  color: var(--primary-dark, #1e3f61);
  font-weight: 650;
  font-size: 14px;
}

.bill-remain--danger {
  background: rgba(209, 67, 67, 0.12);
  color: var(--danger-dark, #a83232);
}

.bill-hero__visual {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  min-height: 180px;
  background: #dfe6ee;
}

.bill-hero__visual img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.bill-scale {
  padding: 28px 18px 42px;
  border-radius: 18px;
  border: 1px solid var(--border-subtle, #d8dee6);
  background: #fff;
}

.bill-scale__track {
  position: relative;
  height: 8px;
  margin: 28px 12px 0;
  border-radius: 999px;
  background: #e7edf3;
}

.bill-scale__fill {
  position: absolute;
  inset: 0 auto 0 0;
  border-radius: inherit;
  background: linear-gradient(90deg, #4a7aad, #2f5f8f);
}

.bill-scale__today {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 3;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #132033;
  box-shadow: 0 0 0 4px rgba(19, 32, 51, 0.12);
}

.bill-scale__today span {
  position: absolute;
  left: 50%;
  bottom: calc(100% + 10px);
  transform: translateX(-50%);
  white-space: nowrap;
  font-size: 11px;
  font-weight: 700;
  color: #132033;
}

.bill-scale__mark {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  text-align: center;
  width: max-content;
  max-width: 110px;
}

.bill-scale__mark i {
  display: block;
  width: 12px;
  height: 12px;
  margin: 0 auto;
  border-radius: 50%;
  background: #fff;
  border: 2px solid #2f5f8f;
}

.bill-scale__mark--registration i {
  border-color: #1a9a6e;
}

.bill-scale__mark--payment i {
  border-color: #c48a1a;
  background: #c48a1a;
}

.bill-scale__mark--expires i {
  border-color: #d14343;
}

.bill-scale__mark em,
.bill-scale__mark small {
  display: block;
  margin-top: 14px;
  font-style: normal;
  line-height: 1.25;
}

.bill-scale__mark em {
  font-size: 12px;
  font-weight: 650;
  color: #132033;
}

.bill-scale__mark small {
  margin-top: 2px;
  font-size: 11px;
  color: #6b7c8d;
}

.bill-plans__head {
  margin-bottom: 14px;
}

.bill-plans__head h2 {
  margin: 0 0 6px;
  font-size: 22px;
  letter-spacing: -0.02em;
}

.bill-plans__head p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
}

.tariff-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
}

.tariff-card {
  position: relative;
  border: 1px solid var(--border-subtle, #d8dee6);
  border-radius: 18px;
  padding: 20px 18px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: 0 10px 30px rgba(19, 32, 51, 0.04);
}

.tariff-card--featured {
  border-color: rgba(47, 95, 143, 0.45);
  box-shadow: 0 14px 36px rgba(47, 95, 143, 0.12);
  background: linear-gradient(180deg, #f7fafc 0%, #fff 40%);
}

.tariff-badge {
  position: absolute;
  top: 14px;
  right: 14px;
  padding: 4px 10px;
  border-radius: 999px;
  background: #2f5f8f;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
}

.tariff-card h3 {
  margin: 0;
  font-size: 18px;
  letter-spacing: -0.02em;
}

.price {
  margin: 0;
  font-size: 32px;
  font-weight: 750;
  letter-spacing: -0.03em;
  color: #132033;
}

.price span {
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
}

.desc {
  margin: 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.45;
}

ul {
  list-style: none;
  margin: 4px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 14px;
  color: #334155;
}

li svg {
  color: var(--success, #1a9a6e);
  margin-top: 2px;
  flex-shrink: 0;
}

.btn-pay {
  margin-top: auto;
  border: none;
  border-radius: 999px;
  padding: 12px 16px;
  background: #2f5f8f;
  color: #fff;
  font: inherit;
  font-weight: 650;
  cursor: pointer;
  transition: background 0.15s, transform 0.15s;
}

.tariff-card--featured .btn-pay {
  background: #1e3f61;
}

.btn-pay:hover {
  background: #264d75;
  transform: translateY(-1px);
}

.btn-pay:disabled {
  opacity: 0.7;
  cursor: wait;
  transform: none;
}

.note,
.empty {
  color: #64748b;
  font-size: 13px;
}

.msg {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
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
  align-self: flex-start;
  border: none;
  background: none;
  color: #2f5f8f;
  font: inherit;
  font-weight: 650;
  cursor: pointer;
  padding: 0;
}

@media (max-width: 860px) {
  .bill-hero {
    grid-template-columns: 1fr;
  }

  .bill-hero__visual {
    min-height: 160px;
    order: -1;
  }

  .bill-scale {
    overflow-x: auto;
  }

  .bill-scale__track {
    min-width: 520px;
  }
}
</style>
