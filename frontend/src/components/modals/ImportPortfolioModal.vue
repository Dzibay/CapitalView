<template>
  <ModalBase title="Подключение брокера" :icon="Upload" @close="$emit('close')">
    <form v-if="step === 'token'" @submit.prevent="checkToken">
        <p class="import-hint">
          Подключите брокерский счёт — сделки, дивиденды и остатки загрузятся автоматически,
          а дальше портфель будет обновляться сам.
        </p>

        <div class="form-section">
          <CustomSelect
            v-model="brokerId"
            :options="brokers"
            label="Брокер"
            placeholder="Выберите брокера"
            :show-empty-option="false"
            option-label="name"
            option-value="id"
            :min-width="'100%'"
            :flex="'none'"
            :disabled="loadingBrokers || checking"
          />
        </div>

        <div v-if="brokerHelp" class="broker-help">
          <p v-for="line in brokerHelp.lines" :key="line">{{ line }}</p>
          <a v-if="brokerHelp.link" :href="brokerHelp.link.href" target="_blank" rel="noopener noreferrer" class="broker-help__link">
            {{ brokerHelp.link.text }}
            <ExternalLink :size="13" />
          </a>
        </div>

        <div class="form-section form-section--tight">
          <FormInput
            v-model="token"
            :label="brokerHelp?.tokenLabel || 'Токен API'"
            :icon="Key"
            :type="showToken ? 'text' : 'password'"
            name="broker-token"
            placeholder="Вставьте токен"
            :disabled="checking"
            required
          />
          <button type="button" class="token-toggle" @click="showToken = !showToken">
            <component :is="showToken ? EyeOff : Eye" :size="14" />
            {{ showToken ? 'Скрыть токен' : 'Показать токен' }}
          </button>
          <p class="token-safety">
            <ShieldCheck :size="13" />
            Токен хранится на сервере в зашифрованном виде и больше нигде не показывается.
          </p>
        </div>

        <div v-if="error" class="error">{{ error }}</div>

        <div class="form-actions">
          <Button variant="secondary" type="button" @click="$emit('close')" :disabled="checking">
            Отмена
          </Button>
          <Button variant="primary" type="submit" :disabled="checking || !brokerId || !token.trim()" :loading="checking">
            <template #icon>
              <ShieldCheck :size="16" />
            </template>
            Проверить токен
          </Button>
        </div>
    </form>

    <form v-else @submit.prevent="handleImport">
        <div class="check-ok">
          <CheckCircle2 :size="18" />
          <div>
            <strong>Токен принят брокером</strong>
            <span>{{ accountsSummary }}</span>
          </div>
        </div>

        <ul v-if="accounts.length" class="accounts">
          <li v-for="acc in accounts" :key="acc.id" :class="{ 'is-closed': isClosed(acc) }">
            <span class="accounts__name">{{ acc.name }}</span>
            <span v-if="accountMeta(acc)" class="accounts__meta">{{ accountMeta(acc) }}</span>
          </li>
        </ul>

        <p v-if="alreadyConnected" class="import-hint">
          Этот токен уже подключён к портфелю «{{ alreadyConnected.portfolio_name || 'без названия' }}».
          Импорт обновит его данные — ничего не задвоится.
        </p>

        <div v-else class="form-section">
          <FormInput
            v-model="portfolioName"
            label="Название портфеля"
            :icon="FileText"
            type="text"
            placeholder="Например: Т-Инвестиции"
            hint="Каждый счёт брокера станет отдельным вложенным портфелем."
            required
          />
        </div>

        <div v-if="error" class="error">{{ error }}</div>

        <div class="form-actions">
          <Button variant="secondary" type="button" @click="backToToken" :disabled="loading">
            Назад
          </Button>
          <Button variant="primary" type="submit" :disabled="loading || (!alreadyConnected && !portfolioName.trim())" :loading="loading">
            <template #icon>
              <Upload :size="16" />
            </template>
            {{ alreadyConnected ? 'Обновить портфель' : 'Импортировать' }}
          </Button>
        </div>
    </form>
  </ModalBase>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Upload, Key, FileText, Eye, EyeOff, ShieldCheck, CheckCircle2, ExternalLink } from 'lucide-vue-next'
import { Button } from '../base'
import CustomSelect from '../base/CustomSelect.vue'
import FormInput from '../base/FormInput.vue'
import portfolioService from '../../services/portfolioService'
import brokerConnectionsService from '../../services/brokerConnectionsService'
import { apiErrorMessage } from '../../utils/apiError'
import ModalBase from './ModalBase.vue'

const props = defineProps({
  onImport: Function,
  onTaskCreated: Function
})
const emit = defineEmits(['close'])

// Подсказки «где взять токен» по id брокера (1 — Т-Инвестиции, 2 — БКС)
const BROKER_HELP = {
  1: {
    tokenLabel: 'Токен T-Invest API',
    lines: [
      'Создайте токен в приложении или на сайте Т-Инвестиций: Настройки → Токены T-Invest API.',
      'Достаточно токена «Только для чтения» с доступом ко всем счетам — торговать по нему нельзя.',
    ],
    link: { href: 'https://www.tbank.ru/invest/settings/api/', text: 'Открыть настройки токенов' },
  },
  2: {
    tokenLabel: 'Refresh-токен БКС',
    lines: [
      'Скопируйте refresh-токен из раздела API в личном кабинете БКС.',
      'Если токен перевыпустить, старый перестанет работать — тогда обновите его в настройках.',
    ],
  },
}

const ACCOUNT_TYPES = {
  ACCOUNT_TYPE_TINKOFF: 'Брокерский счёт',
  ACCOUNT_TYPE_TINKOFF_IIS: 'ИИС',
  ACCOUNT_TYPE_INVEST_BOX: 'Инвесткопилка',
  ACCOUNT_TYPE_INVEST_FUND: 'Фонд',
}

const getDefaultBrokerId = () => {
  const parsed = parseInt(import.meta.env.VITE_DEFAULT_BROKER_ID, 10)
  return isNaN(parsed) ? null : parsed
}

const step = ref('token')
const token = ref('')
const showToken = ref(false)
const brokerId = ref(null)
const brokers = ref([])
const loadingBrokers = ref(false)
const portfolioName = ref(import.meta.env.VITE_DEFAULT_PORTFOLIO_NAME || '')
const checking = ref(false)
const loading = ref(false)
const error = ref('')
const accounts = ref([])
const alreadyConnected = ref(null)

const brokerHelp = computed(() => BROKER_HELP[brokerId.value] || null)
const brokerName = computed(() => brokers.value.find((b) => b.id === brokerId.value)?.name || '')

const isClosed = (acc) => acc.status === 'ACCOUNT_STATUS_CLOSED'
const accountMeta = (acc) => {
  // тип не повторяем, если счёт так и называется («Брокерский счёт», «ИИС»)
  const parts = [ACCOUNT_TYPES[acc.type] !== acc.name ? ACCOUNT_TYPES[acc.type] : null]
  if (isClosed(acc)) parts.push('закрыт — загрузится история')
  if (acc.access_level === 'ACCOUNT_ACCESS_LEVEL_NO_ACCESS') parts.push('нет доступа по токену')
  return parts.filter(Boolean).join(' · ')
}

const plural = (n, one, few, many) => {
  const m10 = n % 10
  const m100 = n % 100
  if (m10 === 1 && m100 !== 11) return one
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few
  return many
}
const accountsSummary = computed(() => {
  const n = accounts.value.length
  if (!n) return 'Счета загрузятся при импорте.'
  return `Найдено ${n} ${plural(n, 'счёт', 'счёта', 'счетов')} — загрузим все.`
})

const loadBrokers = async () => {
  loadingBrokers.value = true
  try {
    const brokersList = await portfolioService.getBrokers()
    brokers.value = Array.isArray(brokersList) ? brokersList : []
    const defaultBrokerId = getDefaultBrokerId()
    if (defaultBrokerId && brokers.value.find((b) => b.id === defaultBrokerId)) {
      brokerId.value = defaultBrokerId
    } else if (brokers.value.length > 0) {
      brokerId.value = brokers.value[0].id
    }
  } catch (e) {
    error.value = apiErrorMessage(e, 'Не удалось загрузить список брокеров. Обновите страницу.')
  } finally {
    loadingBrokers.value = false
  }
}

onMounted(loadBrokers)

// Сменили брокера или токен — прежняя проверка больше не действует
watch([brokerId, token], () => {
  if (step.value !== 'token') step.value = 'token'
  error.value = ''
})

const checkToken = async () => {
  if (!brokerId.value) {
    error.value = 'Выберите брокера'
    return
  }
  if (!token.value.trim()) {
    error.value = 'Вставьте токен'
    return
  }
  checking.value = true
  error.value = ''
  try {
    const res = await brokerConnectionsService.checkToken(brokerId.value, token.value.trim())
    accounts.value = res.accounts || []
    alreadyConnected.value = res.already_connected || null
    if (!portfolioName.value.trim()) portfolioName.value = brokerName.value
    step.value = 'confirm'
  } catch (e) {
    error.value = apiErrorMessage(e, 'Не удалось проверить токен. Попробуйте ещё раз.')
  } finally {
    checking.value = false
  }
}

const backToToken = () => {
  step.value = 'token'
  error.value = ''
}

const handleImport = async () => {
  if (!alreadyConnected.value && !portfolioName.value.trim()) {
    error.value = 'Введите название портфеля'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const result = await props.onImport({
      broker_id: brokerId.value,
      token: token.value.trim(),
      portfolioId: alreadyConnected.value?.portfolio_id || null,
      portfolio_name: alreadyConnected.value?.portfolio_name || portfolioName.value.trim()
    })
    if (result?.success && result.task_id && props.onTaskCreated) {
      props.onTaskCreated(result.task_id)
    }
    emit('close')
  } catch (e) {
    error.value = apiErrorMessage(e, 'Не удалось запустить импорт. Попробуйте ещё раз.')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.import-hint {
  margin: 0 0 16px;
  padding: 10px 12px;
  background: var(--lx-fill, #eff6ff);
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.45;
  color: var(--lx-accent-ink, #1e40af);
}

.form-section {
  margin-bottom: 20px;
}

.form-section--tight {
  margin-bottom: 14px;
}

.broker-help {
  margin: -6px 0 16px;
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--lx-ink-2, #6b7280);
}

.broker-help p {
  margin: 0 0 4px;
}

.broker-help__link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--lx-accent-ink, #2563eb);
  text-decoration: none;
  font-weight: 500;
}

.broker-help__link:hover {
  text-decoration: underline;
}

.token-toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 6px;
  padding: 0;
  border: 0;
  background: none;
  font: inherit;
  font-size: 12.5px;
  color: var(--lx-accent-ink, #2563eb);
  cursor: pointer;
}

.token-safety {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--lx-mut, #9ca3af);
}

.check-ok {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 12px;
  color: var(--lx-up, #16a34a);
}

.check-ok div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.check-ok strong {
  font-size: 14px;
}

.check-ok span {
  font-size: 13px;
  color: var(--lx-ink-2, #6b7280);
}

.accounts {
  list-style: none;
  margin: 0 0 16px;
  padding: 0;
  border: 1px solid var(--lx-line, #e5e7eb);
  border-radius: 10px;
  max-height: 220px;
  overflow-y: auto;
}

.accounts li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 12px;
  font-size: 13px;
}

.accounts li + li {
  border-top: 1px solid var(--lx-line, #f3f4f6);
}

.accounts li.is-closed {
  opacity: .65;
}

.accounts__name {
  color: var(--lx-ink, #111827);
  font-weight: 500;
}

.accounts__meta {
  color: var(--lx-mut, #9ca3af);
  text-align: right;
}

.error {
  padding: 10px 14px;
  background: var(--lx-down-soft, #fef2f2);
  border: 1px solid var(--lx-down-line, #fecaca);
  border-radius: 10px;
  color: var(--lx-down, #dc2626);
  font-size: 13px;
  line-height: 1.45;
  margin-bottom: 12px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 16px;
  margin-top: 8px;
  border-top: 1px solid var(--lx-line, #f3f4f6);
}
</style>
