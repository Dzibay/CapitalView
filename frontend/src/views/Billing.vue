<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { AlertCircle, Check, Clock3, ShieldCheck, Sparkles, Zap } from 'lucide-vue-next'
import CvPageHead from '../cabinet/ui/CvPageHead.vue'
import CvWidget from '../cabinet/ui/CvWidget.vue'
import { plural } from '../cabinet/format'
import { billingService } from '../services/billingService'
import { useAuthStore } from '../stores/auth.store'

const route = useRoute()
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
  }).replace(' г.', '')
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

const statusTone = computed(() => {
  if (isExpired.value) return 'off'
  return subscription.value?.status === 'trial' ? 'trial' : 'on'
})
const accessEndsAt = computed(() => (
  subscription.value?.current_period_ends_at
  || subscription.value?.trial_ends_at
  || subscription.value?.access_ends_at
  || timeline.value?.access_ends_at
  || null
))
const daysTone = computed(() => (isExpired.value || (daysLeft.value != null && daysLeft.value <= 7) ? 'warn' : ''))
const pageMeta = computed(() => [statusTitle.value, daysLeftLabel.value])
</script>

<template>
  <div class="bl">
    <CvPageHead eyebrow="Аккаунт" title="Подписка" :meta="loading ? [] : pageMeta">
      <template v-if="hasAccess && !loading" #actions>
        <router-link to="/dashboard" class="cv-btn cv-btn--ghost">Вернуться в кабинет</router-link>
      </template>
    </CvPageHead>

    <div v-if="loading" class="cv-grid">
      <div class="cv-skel is-l bl__skel" />
      <div class="cv-skel is-s bl__skel" />
      <div class="cv-skel is-xl bl__skel bl__skel--lg" />
    </div>

    <template v-else>
      <p v-if="error" class="cv-note cv-note--err bl__note" role="alert"><AlertCircle :size="14" />{{ error }}</p>
      <p v-if="info" class="cv-note cv-note--info bl__note" role="status"><Clock3 :size="14" />{{ info }}</p>

      <div class="cv-grid is-intro">
        <!-- Статус -->
        <CvWidget class="is-l" style="--i: 0" glow title="Доступ">
          <div class="bs">
            <div class="bs__top">
              <div class="bs__copy">
                <span class="bs__pill" :class="`is-${statusTone}`"><i />{{ statusTitle }}</span>
                <p class="bs__lead">
                  <template v-if="isExpired">
                    Портфель и аналитика откроются сразу после оплаты. Настройки и поддержка доступны без ограничений.
                  </template>
                  <template v-else-if="subscription?.status === 'trial'">
                    Полный доступ до {{ formatDate(subscription.trial_ends_at) }}. Оформите тариф заранее — доступ продолжится без паузы.
                  </template>
                  <template v-else>
                    Доступ до {{ formatDate(accessEndsAt) }}<template v-if="subscription?.tariff"> · тариф «{{ subscription.tariff.name }}»</template>.
                  </template>
                </p>
              </div>
              <div class="bs__days" :class="daysTone && `is-${daysTone}`">
                <template v-if="daysLeft != null && daysLeft >= 0">
                  <b class="cv-num">{{ daysLeft }}</b>
                  <span>{{ daysLeft === 0 ? 'последний день' : `${plural(daysLeft, 'день', 'дня', 'дней')} осталось` }}</span>
                </template>
                <template v-else>
                  <b><Clock3 :size="22" /></b>
                  <span>{{ daysLeftLabel }}</span>
                </template>
              </div>
            </div>

            <div v-if="scaleModel.milestones.length" class="bs__journey" aria-label="История подписки">
              <div
                class="bs__track"
                role="progressbar"
                :aria-valuenow="Math.round(scaleModel.progressPct)"
                aria-valuemin="0"
                aria-valuemax="100"
                :aria-label="`Прошло ${Math.round(scaleModel.progressPct)}% периода`"
              >
                <div class="bs__fill" :style="{ width: `${scaleModel.progressPct}%` }" />
                <div
                  class="bs__now"
                  :class="{ 'is-start': scaleModel.progressPct < 18, 'is-end': scaleModel.progressPct > 82 }"
                  :style="{ left: `${scaleModel.progressPct}%` }"
                >
                  <span>Сегодня · {{ scaleModel.todayLabel }}</span>
                </div>
              </div>
              <ol class="bs__steps">
                <li
                  v-for="m in scaleModel.milestones"
                  :key="m.key"
                  class="bs__step"
                  :class="[`is-${m.tone}`, { 'is-done': m.done }]"
                >
                  <i aria-hidden="true" />
                  <div>
                    <b>{{ m.title }}</b>
                    <span>{{ m.detail }} · {{ formatDate(m.date) }}</span>
                  </div>
                </li>
              </ol>
            </div>
          </div>
        </CvWidget>

        <!-- Что входит -->
        <CvWidget class="is-s is-full-md" style="--i: 1" title="Что входит">
          <div class="bi">
            <ul class="bi__list">
              <li v-for="(f, i) in sharedFeatures" :key="i"><Check :size="14" :stroke-width="2.4" />{{ f }}</li>
            </ul>
            <ul class="bi__perks">
              <li><ShieldCheck :size="15" />Доступ к брокеру только на чтение</li>
              <li><Zap :size="15" />Все функции в любом тарифе</li>
            </ul>
          </div>
        </CvWidget>

        <!-- Тарифы -->
        <CvWidget
          class="is-xl"
          style="--i: 2"
          title="Тарифы"
          subtitle="Один полный доступ — отличаются только срок и цена. Оплата через ЮKassa."
        >
          <p v-if="!orderedTariffs.length" class="bt__empty">
            Тарифы пока не настроены. Напишите в поддержку или зайдите позже.
          </p>
          <div v-else class="bt">
            <article
              v-for="t in orderedTariffs"
              :key="t.id"
              class="bt__card"
              :class="{ 'is-featured': isFeatured(t) }"
            >
              <div class="bt__head">
                <span class="bt__period">{{ periodTitle(t.period_days) }}</span>
                <span v-if="isFeatured(t)" class="bt__badge"><Sparkles :size="12" />Выгоднее всего</span>
              </div>
              <span class="bt__name">{{ t.name }}</span>
              <div class="bt__price">
                <b class="cv-num">{{ formatPrice(t.price_rub) }}</b><span>₽</span>
              </div>
              <div class="bt__meta">
                {{ periodLabel(t.period_days) }}
                <template v-if="monthlyEquivalent(t) && Number(t.period_days) > 31">
                  · <span class="cv-num">{{ formatPrice(monthlyEquivalent(t)) }} ₽</span>/мес
                </template>
              </div>
              <div class="bt__save">
                <span v-if="savingsVsMonthly(t)" class="cv-up">−{{ savingsVsMonthly(t) }}% к помесячной оплате</span>
              </div>
              <button
                type="button"
                class="cv-btn bt__cta"
                :class="{ 'cv-btn--primary': isFeatured(t) }"
                :disabled="payingId === t.id"
                @click="pay(t)"
              >
                {{ payingId === t.id ? 'Переход к оплате…' : (isExpired ? 'Возобновить' : 'Выбрать') }}
              </button>
            </article>
          </div>
          <p class="bt__foot">
            Новым пользователям — пробный период {{ daysWord(trialDays) }}, карта не нужна до оплаты.
          </p>
        </CvWidget>
      </div>
    </template>
  </div>
</template>

<style scoped>
.bl__note { margin-bottom: var(--cv-gap); }
.bl__skel { height: 260px; border-radius: var(--cv-r-lg); }
.bl__skel--lg { height: 340px; }

/* статус */
.bs { display: flex; flex-direction: column; gap: 26px; }
.bs__top { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; }
.bs__copy { display: flex; flex-direction: column; align-items: flex-start; gap: 12px; min-width: 0; max-width: 460px; }
.bs__lead { margin: 0; font-size: 13.5px; line-height: 1.6; color: var(--cv-ink-2); }
.bs__pill {
  display: inline-flex; align-items: center; gap: 7px; height: 26px; padding: 0 10px; border-radius: 99px;
  font-size: 12px; font-weight: 550;
}
.bs__pill i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.bs__pill.is-on { color: var(--cv-up); background: var(--cv-up-bg); }
.bs__pill.is-trial { color: var(--cv-accent-ink); background: var(--cv-accent-soft); }
.bs__pill.is-off { color: var(--cv-down); background: var(--cv-down-bg); }
.bs__days { display: flex; flex-direction: column; align-items: flex-end; flex: none; text-align: right; }
.bs__days b {
  display: flex; align-items: center; min-height: 52px;
  font-family: var(--cv-display); font-size: 48px; font-weight: 600; line-height: 1; letter-spacing: -0.04em; color: var(--cv-ink);
}
.bs__days span { font-size: 12.5px; color: var(--cv-mut); }
.bs__days.is-warn b { color: var(--cv-warn); }

.bs__journey { display: flex; flex-direction: column; gap: 18px; }
.bs__track { position: relative; height: 6px; margin-top: 22px; border-radius: 99px; background: rgba(255, 255, 255, .06); }
.bs__fill { position: absolute; inset: 0 auto 0 0; border-radius: inherit; background: var(--cv-grad); animation: bs-fill 1s var(--cv-ease) .3s backwards; }
.bs__now { position: absolute; top: 50%; width: 12px; height: 12px; margin: -6px 0 0 -6px; border-radius: 50%; background: var(--cv-ink); box-shadow: 0 0 0 4px rgba(100, 116, 255, .25); }
.bs__now span {
  position: absolute; bottom: calc(100% + 8px); left: 50%; transform: translateX(-50%);
  font-size: 11.5px; font-weight: 550; color: var(--cv-ink-2); white-space: nowrap;
}
.bs__now.is-start span { left: -6px; transform: none; }
.bs__now.is-end span { left: auto; right: -6px; transform: none; }
@keyframes bs-fill { from { width: 0; } }
.bs__steps { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px 24px; margin: 0; padding: 0; list-style: none; }
.bs__step { display: flex; align-items: flex-start; gap: 9px; min-width: 0; }
.bs__step > i { flex: none; width: 8px; height: 8px; margin-top: 5px; border-radius: 50%; box-shadow: inset 0 0 0 1.5px var(--cv-line-3); }
.bs__step.is-done > i { background: var(--cv-accent); box-shadow: none; }
.bs__step.is-end > i { box-shadow: inset 0 0 0 1.5px var(--cv-accent); }
.bs__step.is-expired > i { background: var(--cv-down); box-shadow: none; }
.bs__step b { display: block; font-size: 12.5px; font-weight: 600; color: var(--cv-ink); }
.bs__step span { font-size: 12px; color: var(--cv-mut); }
.bs__step:last-child { text-align: right; flex-direction: row-reverse; }

/* что входит */
.bi { display: flex; flex-direction: column; gap: 18px; height: 100%; }
.bi__list, .bi__perks { display: flex; flex-direction: column; gap: 11px; margin: 0; padding: 0; list-style: none; }
.bi__list li { display: flex; align-items: flex-start; gap: 10px; font-size: 13px; line-height: 1.45; color: var(--cv-ink-2); }
.bi__list svg { flex: none; margin-top: 2px; color: var(--cv-accent-ink); }
.bi__perks { margin-top: auto; padding-top: 16px; border-top: 1px solid var(--cv-line); }
.bi__perks li { display: flex; align-items: center; gap: 10px; font-size: 12.5px; color: var(--cv-mut); }
.bi__perks svg { flex: none; color: var(--cv-dim); }

/* тарифы */
.bt { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
.bt__card {
  position: relative; display: flex; flex-direction: column; gap: 4px; padding: 20px;
  border-radius: var(--cv-r); background: rgba(255, 255, 255, .02); box-shadow: inset 0 0 0 1px var(--cv-line);
  transition: box-shadow .25s var(--cv-ease), background .25s var(--cv-ease), transform .25s var(--cv-ease);
}
.bt__card:hover { background: rgba(255, 255, 255, .035); box-shadow: inset 0 0 0 1px var(--cv-line-3); transform: translateY(-2px); }
.bt__card.is-featured {
  background: linear-gradient(180deg, rgba(100, 116, 255, .1), rgba(100, 116, 255, .03));
  box-shadow: inset 0 0 0 1px var(--cv-accent-line), 0 18px 40px -28px rgba(100, 116, 255, .7);
}
.bt__head { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 24px; }
.bt__period { font-size: 11px; font-weight: 550; letter-spacing: .08em; text-transform: uppercase; color: var(--cv-mut); }
.bt__badge {
  display: inline-flex; align-items: center; gap: 5px; height: 22px; padding: 0 8px; border-radius: 99px;
  font-size: 11px; font-weight: 600; color: var(--cv-accent-ink); background: var(--cv-accent-soft);
}
.bt__name { font-size: 14px; font-weight: 600; color: var(--cv-ink); }
.bt__price { display: flex; align-items: baseline; gap: 5px; margin-top: 12px; }
.bt__price b { font-family: var(--cv-display); font-size: 34px; font-weight: 600; line-height: 1.1; letter-spacing: -0.035em; color: var(--cv-ink); }
.bt__price span { font-size: 16px; font-weight: 550; color: var(--cv-mut); }
.bt__meta { font-size: 12.5px; color: var(--cv-mut); }
.bt__save { min-height: 20px; margin-top: 6px; font-size: 12px; font-weight: 550; }
.bt__cta { width: 100%; margin-top: 14px; }
.bt__empty { margin: 0; padding: 28px 0; font-size: 13px; text-align: center; color: var(--cv-mut); }
.bt__foot { margin: 16px 0 0; font-size: 12.5px; color: var(--cv-dim); }

@media (min-width: 601px) and (max-width: 1200px) {
  .bi { flex-direction: row; gap: 32px; }
  .bi__list { flex: 1; }
  .bi__perks { flex: 1; justify-content: center; margin-top: 0; padding: 0 0 0 32px; border-top: 0; border-left: 1px solid var(--cv-line); }
}
@media (max-width: 600px) {
  .bs__top { flex-direction: column-reverse; gap: 14px; }
  .bs__days { align-items: flex-start; text-align: left; }
  .bs__days b { min-height: 0; font-size: 40px; }
  .bs__steps { flex-direction: column; }
  .bs__step:last-child { text-align: left; flex-direction: row; }
}
@media (prefers-reduced-motion: reduce) {
  .bs__fill { animation: none; }
}
</style>
