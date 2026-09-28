<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Check, CreditCard } from 'lucide-vue-next'
import PageLayout from '../layouts/PageLayout.vue'
import PageHeader from '../layouts/PageHeader.vue'
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

const hasAccess = computed(() => Boolean(subscription.value?.has_access || authStore.user?.is_admin))

const statusLabel = computed(() => {
  const s = subscription.value?.status
  if (s === 'trial') return 'Пробный период'
  if (s === 'active') return 'Активная подписка'
  return 'Подписка истекла'
})

function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: 'long', year: 'numeric' })
}

function formatPrice(v) {
  return Number(v || 0).toLocaleString('ru-RU', { maximumFractionDigits: 0 })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await billingService.fetchMe()
    subscription.value = data.subscription
    tariffs.value = data.tariffs || []
    trialDays.value = data.trial_days
    if (authStore.user) {
      authStore.setUser({ ...authStore.user, subscription: data.subscription })
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Не удалось загрузить тарифы'
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
    <PageHeader title="Подписка и тарифы" />

    <LoadingState v-if="loading" />

    <div v-else class="billing-page">
      <p v-if="error" class="msg msg-error">{{ error }}</p>
      <p v-if="info" class="msg msg-info">{{ info }}</p>

      <section class="status-card">
        <div class="status-icon"><CreditCard :size="22" /></div>
        <div>
          <h2>{{ statusLabel }}</h2>
          <p v-if="subscription?.status === 'trial'">
            Пробный период до {{ formatDate(subscription.trial_ends_at) }}
            <template v-if="!hasAccess"> — доступ приостановлен, выберите тариф.</template>
          </p>
          <p v-else-if="subscription?.status === 'active'">
            Действует до {{ formatDate(subscription.current_period_ends_at) }}
            <template v-if="subscription.tariff"> · {{ subscription.tariff.name }}</template>
          </p>
          <p v-else>
            Пробный период закончился. Оформите подписку, чтобы продолжить пользоваться сервисом.
          </p>
        </div>
      </section>

      <div v-if="!tariffs.length" class="empty">
        Тарифы пока не настроены. Напишите в поддержку или зайдите позже.
      </div>

      <div v-else class="tariff-grid">
        <article v-for="t in tariffs" :key="t.id" class="tariff-card">
          <h3>{{ t.name }}</h3>
          <p class="price">
            {{ formatPrice(t.price_rub) }} ₽
            <span>/ {{ t.period_days }} дн.</span>
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
            {{ payingId === t.id ? 'Переход к оплате…' : 'Оплатить' }}
          </button>
        </article>
      </div>

      <p class="note">
        Новым пользователям доступен пробный период {{ trialDays }}
        {{ trialDays === 1 ? 'день' : trialDays > 1 && trialDays < 5 ? 'дня' : 'дней' }}.
        Оплата через ЮKassa.
      </p>

      <button v-if="hasAccess" type="button" class="linkish" @click="router.push('/dashboard')">
        Вернуться в кабинет
      </button>
    </div>
  </PageLayout>
</template>

<style scoped>
.billing-page {
  max-width: 920px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.status-card {
  display: flex;
  gap: 14px;
  padding: 18px 20px;
  border-radius: 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  background: #fff;
}

.status-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: rgba(59, 130, 246, 0.1);
  color: #2563eb;
  flex-shrink: 0;
}

.status-card h2 {
  margin: 0 0 4px;
  font-size: 18px;
}

.status-card p {
  margin: 0;
  color: var(--color-text-secondary, #64748b);
  font-size: 14px;
  line-height: 1.5;
}

.tariff-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
}

.tariff-card {
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 16px;
  padding: 18px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tariff-card h3 {
  margin: 0;
  font-size: 17px;
}

.price {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.price span {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary, #64748b);
}

.desc {
  margin: 0;
  color: var(--color-text-secondary, #64748b);
  font-size: 14px;
}

ul {
  list-style: none;
  margin: 0;
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
}

li svg {
  color: var(--color-success, #16a34a);
  margin-top: 2px;
  flex-shrink: 0;
}

.btn-pay {
  margin-top: auto;
  border: none;
  border-radius: 999px;
  padding: 12px 16px;
  background: var(--color-primary, #3b82f6);
  color: #fff;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

.btn-pay:disabled {
  opacity: 0.7;
  cursor: wait;
}

.note,
.empty {
  color: var(--color-text-secondary, #64748b);
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
  color: var(--color-primary, #3b82f6);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}
</style>
