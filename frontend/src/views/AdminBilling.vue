<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { CreditCard, Plus, RefreshCw, Trash2 } from 'lucide-vue-next'
import PageLayout from '../layouts/PageLayout.vue'
import PageHeader from '../layouts/PageHeader.vue'
import LoadingState from '../components/base/LoadingState.vue'
import { adminService } from '../services/adminService'

const router = useRouter()

const loading = ref(true)
const savingSettings = ref(false)
const savingTariff = ref(false)
const error = ref('')
const success = ref('')

const settings = ref({
  trial_days: 14,
  yookassa_shop_id: '',
  yookassa_secret_key: '',
  yookassa_configured: false,
})

const tariffs = ref([])

const tariffForm = ref({
  id: null,
  name: '',
  description: '',
  price_rub: 299,
  period_days: 30,
  is_active: true,
  sort_order: 0,
  featuresText: '',
})

const isEditingTariff = computed(() => tariffForm.value.id != null)

function featuresToText(features) {
  if (!Array.isArray(features)) return ''
  return features.join('\n')
}

function textToFeatures(text) {
  return String(text || '')
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
}

function resetTariffForm() {
  tariffForm.value = {
    id: null,
    name: '',
    description: '',
    price_rub: 299,
    period_days: 30,
    is_active: true,
    sort_order: tariffs.value.length,
    featuresText: '',
  }
}

function editTariff(t) {
  tariffForm.value = {
    id: t.id,
    name: t.name || '',
    description: t.description || '',
    price_rub: Number(t.price_rub || 0),
    period_days: Number(t.period_days || 30),
    is_active: Boolean(t.is_active),
    sort_order: Number(t.sort_order || 0),
    featuresText: featuresToText(t.features),
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await adminService.fetchBilling()
    settings.value = {
      trial_days: Number(data.settings?.trial_days ?? 14),
      yookassa_shop_id: data.settings?.yookassa_shop_id || '',
      yookassa_secret_key: data.settings?.yookassa_secret_key || '',
      yookassa_configured: Boolean(data.settings?.yookassa_configured),
    }
    tariffs.value = data.tariffs || []
    if (!isEditingTariff.value) {
      tariffForm.value.sort_order = tariffs.value.length
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Не удалось загрузить биллинг'
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  savingSettings.value = true
  error.value = ''
  success.value = ''
  try {
    const updated = await adminService.updateBillingSettings({
      trial_days: Number(settings.value.trial_days),
      yookassa_shop_id: settings.value.yookassa_shop_id,
      yookassa_secret_key: settings.value.yookassa_secret_key,
    })
    settings.value = {
      trial_days: Number(updated?.trial_days ?? settings.value.trial_days),
      yookassa_shop_id: updated?.yookassa_shop_id || '',
      yookassa_secret_key: updated?.yookassa_secret_key || '',
      yookassa_configured: Boolean(updated?.yookassa_configured),
    }
    success.value = 'Настройки сохранены'
    setTimeout(() => { success.value = '' }, 2500)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Ошибка сохранения'
  } finally {
    savingSettings.value = false
  }
}

async function saveTariff() {
  savingTariff.value = true
  error.value = ''
  success.value = ''
  const payload = {
    name: tariffForm.value.name.trim(),
    description: tariffForm.value.description.trim(),
    price_rub: Number(tariffForm.value.price_rub),
    period_days: Number(tariffForm.value.period_days),
    is_active: Boolean(tariffForm.value.is_active),
    sort_order: Number(tariffForm.value.sort_order || 0),
    features: textToFeatures(tariffForm.value.featuresText),
  }
  try {
    if (isEditingTariff.value) {
      await adminService.updateTariff(tariffForm.value.id, payload)
      success.value = 'Тариф обновлён'
    } else {
      await adminService.createTariff(payload)
      success.value = 'Тариф создан'
    }
    resetTariffForm()
    await load()
    setTimeout(() => { success.value = '' }, 2500)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Ошибка сохранения тарифа'
  } finally {
    savingTariff.value = false
  }
}

async function removeTariff(id) {
  if (!window.confirm('Удалить тариф?')) return
  error.value = ''
  try {
    await adminService.deleteTariff(id)
    if (tariffForm.value.id === id) resetTariffForm()
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Не удалось удалить тариф'
  }
}

function formatPrice(v) {
  return Number(v || 0).toLocaleString('ru-RU', { maximumFractionDigits: 2 })
}

onMounted(load)
</script>

<template>
  <PageLayout>
    <PageHeader title="Биллинг и ЮKassa">
      <template #actions>
        <button type="button" class="btn-secondary" @click="router.push('/admin')">Статистика</button>
        <button type="button" class="btn-icon" title="Обновить" :disabled="loading" @click="load">
          <RefreshCw :size="18" />
        </button>
      </template>
    </PageHeader>

    <LoadingState v-if="loading" />

    <div v-else class="billing-admin">
      <p v-if="error" class="msg msg-error">{{ error }}</p>
      <p v-if="success" class="msg msg-ok">{{ success }}</p>

      <section class="card">
        <h2>
          <CreditCard :size="18" />
          Настройки
        </h2>
        <div class="grid">
          <label>
            <span>Пробный период (дней) для новых пользователей</span>
            <input v-model.number="settings.trial_days" type="number" min="0" max="3650" />
          </label>
          <label>
            <span>ЮKassa shopId</span>
            <input v-model="settings.yookassa_shop_id" type="text" autocomplete="off" placeholder="shopId" />
          </label>
          <label class="full">
            <span>ЮKassa секретный ключ</span>
            <input
              v-model="settings.yookassa_secret_key"
              type="password"
              autocomplete="new-password"
              placeholder="live_… или test_…"
            />
          </label>
        </div>
        <p class="hint">
          Webhook URL для ЮKassa:
          <code>https://capital-view.ru/api/v1/billing/webhook/yookassa</code>
          · статус ключей:
          {{ settings.yookassa_configured ? 'заполнены' : 'не заполнены' }}
        </p>
        <button type="button" class="btn-primary" :disabled="savingSettings" @click="saveSettings">
          {{ savingSettings ? 'Сохранение…' : 'Сохранить настройки' }}
        </button>
      </section>

      <section class="card">
        <div class="card-head">
          <h2>Тарифы</h2>
          <button type="button" class="btn-secondary" @click="resetTariffForm">
            <Plus :size="16" />
            Новый
          </button>
        </div>

        <div v-if="!tariffs.length" class="empty">Тарифов пока нет — создайте первый ниже.</div>
        <div v-else class="tariff-list">
          <article v-for="t in tariffs" :key="t.id" class="tariff-row">
            <div>
              <strong>{{ t.name }}</strong>
              <span class="meta">
                {{ formatPrice(t.price_rub) }} ₽ / {{ t.period_days }} дн.
                · {{ t.is_active ? 'активен' : 'выключен' }}
              </span>
              <p v-if="t.description" class="desc">{{ t.description }}</p>
            </div>
            <div class="row-actions">
              <button type="button" class="btn-secondary" @click="editTariff(t)">Изменить</button>
              <button type="button" class="btn-danger" @click="removeTariff(t.id)">
                <Trash2 :size="16" />
              </button>
            </div>
          </article>
        </div>

        <h3>{{ isEditingTariff ? 'Редактирование тарифа' : 'Новый тариф' }}</h3>
        <div class="grid">
          <label>
            <span>Название</span>
            <input v-model="tariffForm.name" type="text" maxlength="200" />
          </label>
          <label>
            <span>Цена, ₽</span>
            <input v-model.number="tariffForm.price_rub" type="number" min="0" step="0.01" />
          </label>
          <label>
            <span>Период, дней</span>
            <input v-model.number="tariffForm.period_days" type="number" min="1" />
          </label>
          <label>
            <span>Порядок</span>
            <input v-model.number="tariffForm.sort_order" type="number" />
          </label>
          <label class="full">
            <span>Описание</span>
            <input v-model="tariffForm.description" type="text" />
          </label>
          <label class="full">
            <span>Возможности (по одной на строку)</span>
            <textarea v-model="tariffForm.featuresText" rows="4" />
          </label>
          <label class="check">
            <input v-model="tariffForm.is_active" type="checkbox" />
            <span>Активен (виден пользователям)</span>
          </label>
        </div>
        <div class="form-actions">
          <button type="button" class="btn-primary" :disabled="savingTariff || !tariffForm.name.trim()" @click="saveTariff">
            {{ savingTariff ? 'Сохранение…' : (isEditingTariff ? 'Обновить тариф' : 'Создать тариф') }}
          </button>
          <button v-if="isEditingTariff" type="button" class="btn-secondary" @click="resetTariffForm">Отмена</button>
        </div>
      </section>
    </div>
  </PageLayout>
</template>

<style scoped>
.billing-admin {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 860px;
}

.card {
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 16px;
  padding: 20px 22px;
}

.card h2 {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px;
  font-size: 18px;
  font-weight: 600;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.card-head h2 {
  margin: 0;
}

.card h3 {
  margin: 20px 0 12px;
  font-size: 15px;
  font-weight: 600;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 14px;
}

.grid label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--color-text-secondary, #64748b);
}

.grid label.full {
  grid-column: 1 / -1;
}

.grid label.check {
  flex-direction: row;
  align-items: center;
  gap: 8px;
  grid-column: 1 / -1;
}

input,
textarea {
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 10px;
  padding: 10px 12px;
  font: inherit;
  color: var(--color-text, #0f172a);
  background: #fff;
}

.hint {
  font-size: 12px;
  color: var(--color-text-secondary, #64748b);
  margin: 0 0 14px;
}

.hint code {
  font-size: 11px;
  word-break: break-all;
}

.btn-primary,
.btn-secondary,
.btn-danger,
.btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: 10px;
  border: 1px solid transparent;
  padding: 10px 14px;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary {
  background: var(--color-primary, #3b82f6);
  color: #fff;
}

.btn-secondary {
  background: #fff;
  border-color: var(--color-border, #e2e8f0);
  color: var(--color-text, #0f172a);
}

.btn-danger {
  background: #fff;
  border-color: #fecaca;
  color: #dc2626;
  padding: 10px;
}

.btn-icon {
  background: #fff;
  border-color: var(--color-border, #e2e8f0);
  padding: 8px;
}

.tariff-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 8px;
}

.tariff-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 12px;
}

.tariff-row .meta {
  display: block;
  margin-top: 4px;
  font-size: 13px;
  color: var(--color-text-secondary, #64748b);
}

.tariff-row .desc {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--color-text-secondary, #64748b);
}

.row-actions,
.form-actions {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.empty {
  color: var(--color-text-secondary, #64748b);
  font-size: 14px;
  margin-bottom: 12px;
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

.msg-ok {
  background: #ecfdf5;
  color: #047857;
}

@media (max-width: 700px) {
  .grid {
    grid-template-columns: 1fr;
  }

  .tariff-row {
    flex-direction: column;
  }
}
</style>
