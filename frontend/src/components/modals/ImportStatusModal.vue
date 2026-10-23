<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { X, Upload, Loader2, CheckCircle2, XCircle, Ban, Clock, AlertTriangle, RotateCw, Info } from 'lucide-vue-next'
import { Button } from '../base'
import taskService from '../../services/taskService'
import portfolioService from '../../services/portfolioService'
import { useImportTasksStore } from '../../stores/importTasks.store'
import { apiErrorMessage } from '../../utils/apiError'
import ModalBase from './ModalBase.vue'

const props = defineProps({
  taskId: {
    type: Number,
    required: true
  },
  onComplete: Function,
  onError: Function
})

// retry — запущена новая задача ({ task_id, portfolio_id }), родитель переключает окно на неё
const emit = defineEmits(['close', 'retry'])

const importTasksStore = useImportTasksStore()

const status = ref('pending')
const progress = ref(0)
const progressMessage = ref('')
const errorMessage = ref(null)
const result = ref(null)
const completedAt = ref(null)
const portfolioId = ref(null)
const retrying = ref(false)
const retryError = ref('')
const openedDetails = ref(new Set())

let pollInterval = null
const POLL_INTERVAL = 2000 // 2 секунды

const isActive = computed(() => status.value === 'pending' || status.value === 'processing')
const errorCode = computed(() => result.value?.error_code || null)
const tokenInvalid = computed(() => errorCode.value === 'token_invalid')

// Итог по счетам из result.import_result (см. portfolio_import_service._import_broker_portfolio_locked)
const importResult = computed(() => result.value?.import_result || null)
const accounts = computed(() => importResult.value?.accounts || [])
const totalInserted = computed(() => importResult.value?.inserted_count ?? null)
const hasProblems = computed(() =>
  accounts.value.some((a) => a.failed_count || a.skipped_count || mismatchCount(a) || unknownTransfers(a))
)

const SKIP_REASONS = {
  asset_not_found: 'бумага не найдена в справочнике',
  portfolio_asset_not_created: 'не удалось создать позицию',
  redemption_quantity_unknown: 'неизвестно количество бумаг при погашении',
  bad_date: 'некорректная дата у брокера',
  unknown_operation_type: 'неизвестный тип операции',
}

const OP_TYPES = {
  Buy: 'Покупка',
  Sell: 'Продажа',
  Dividend: 'Дивиденд',
  Coupon: 'Купон',
  Amortization: 'Погашение',
  Other: 'Прочее',
  Deposit: 'Пополнение',
  Withdraw: 'Вывод',
  Commission: 'Комиссия',
  Tax: 'Налог',
}

const formatDate = (value) => {
  if (!value) return ''
  const d = new Date(value)
  return isNaN(d) ? String(value).slice(0, 10) : d.toLocaleDateString('ru-RU')
}

const formatQty = (value) => Number(value || 0).toLocaleString('ru-RU', { maximumFractionDigits: 6 })

const plural = (n, one, few, many) => {
  const m10 = n % 10
  const m100 = n % 100
  if (m10 === 1 && m100 !== 11) return one
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few
  return many
}

const mismatchCount = (acc) => acc.reconciliation?.mismatch_count ?? acc.reconciliation?.mismatches?.length ?? 0

// Перевод бумаг от другого брокера: откуда взята себестоимость (portfolio_import_service)
const PRICE_SOURCES = {
  broker_average: 'по средней цене у брокера',
  market: 'по рыночной цене на дату перевода',
  fifo: 'по цене покупки',
  unknown: 'себестоимость неизвестна — укажите вручную',
}

const unknownTransfers = (acc) => (acc.transfers || []).filter((t) => t.price_source === 'unknown').length

const transferLine = (t) => {
  const what = [t.direction === 'out' ? 'Вывод' : 'Ввод', t.ticker || t.name].filter(Boolean).join(' ')
  const price = t.price_source !== 'unknown' && t.price ? `: ${formatQty(t.price)}` : ''
  return `${formatDate(t.date)} · ${what}, ${formatQty(t.quantity)} шт. — ${PRICE_SOURCES[t.price_source] || ''}${price}`
}

// Ошибки apply_operations_batch, которые стоит перевести для пользователя
const FAIL_REASONS = {
  'Transaction already exists (duplicate)': 'такая операция уже есть в портфеле',
}

// Что синхронизация сознательно не загрузила: удалённое/изменённое пользователем и уже внесённое вручную
const keptLines = (acc) => {
  const lines = []
  if (acc.suppressed_count) {
    lines.push(
      `${acc.suppressed_count} ${plural(acc.suppressed_count, 'операцию', 'операции', 'операций')} брокера вы удалили или изменили — не возвращаем`
    )
  }
  if (acc.matched_manual_count) {
    lines.push(
      `${acc.matched_manual_count} ${plural(acc.matched_manual_count, 'операция уже была добавлена', 'операции уже были добавлены', 'операций уже были добавлены')} вручную — не дублируем`
    )
  }
  return lines
}

const problemLines = (acc) => {
  const lines = []
  for (const op of acc.skipped_operations || []) {
    const what = [OP_TYPES[op.type] || op.type, op.ticker || op.isin].filter(Boolean).join(' ')
    lines.push(`${formatDate(op.date)} · ${what} — ${SKIP_REASONS[op.reason] || op.reason || 'пропущено'}`)
  }
  for (const item of acc.failed_operations || []) {
    const op = item.operation || item
    const date = op.operation_date || op.transaction_date || op.date
    lines.push(`${formatDate(date)} · ${FAIL_REASONS[item.error] || item.error || 'не удалось записать операцию'}`)
  }
  return lines
}

const toggleDetails = (key) => {
  const next = new Set(openedDetails.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  openedDetails.value = next
}

const resetState = () => {
  status.value = 'pending'
  progress.value = 0
  progressMessage.value = ''
  errorMessage.value = null
  result.value = null
  completedAt.value = null
  retryError.value = ''
  openedDetails.value = new Set()
}

// Функция для проверки статуса задачи
const checkStatus = async () => {
  try {
    const response = await taskService.getTaskStatus(props.taskId)
    if (response.success) {
      status.value = response.status
      progress.value = response.progress || 0
      progressMessage.value = response.progress_message || ''
      errorMessage.value = response.error_message
      result.value = response.result
      completedAt.value = response.completed_at
      portfolioId.value = response.portfolio_id || response.result?.portfolio_id || portfolioId.value

      if (response.status === 'completed') {
        stopPolling()
        setTimeout(() => {
          importTasksStore.removeTask(props.taskId)
        }, 3000)
        if (props.onComplete) {
          props.onComplete(response.result)
        }
      } else if (response.status === 'failed') {
        stopPolling()
        setTimeout(() => {
          importTasksStore.removeTask(props.taskId)
        }, 5000)
        if (props.onError) {
          props.onError(response.error_message)
        }
      } else if (response.status === 'cancelled') {
        stopPolling()
        importTasksStore.removeTask(props.taskId)
      }
    }
  } catch (error) {
    // Сетевой сбой — продолжаем опрос; задача не найдена (404) — останавливаемся
    if (error.response?.status === 404) {
      stopPolling()
      errorMessage.value = 'Задача не найдена'
      status.value = 'failed'
    }
  }
}

const startPolling = () => {
  checkStatus()
  pollInterval = setInterval(checkStatus, POLL_INTERVAL)
}

const stopPolling = () => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

// Отменить можно только задачу в очереди: запущенный импорт идёт в одной транзакции
// и всё равно либо запишется целиком, либо откатится
const cancelTask = async () => {
  try {
    await taskService.cancelTask(props.taskId)
    stopPolling()
    status.value = 'cancelled'
    importTasksStore.removeTask(props.taskId)
  } catch (error) {
    retryError.value = apiErrorMessage(error, 'Не удалось отменить импорт')
  }
}

// Повтор по сохранённому токену подключения
const retry = async () => {
  if (!portfolioId.value) return
  retrying.value = true
  retryError.value = ''
  try {
    const res = await portfolioService.syncPortfolio(portfolioId.value)
    if (res?.task_id) emit('retry', { task_id: res.task_id, portfolio_id: portfolioId.value })
  } catch (error) {
    retryError.value = error.response?.status === 404
      ? 'Подключение не сохранилось — запустите импорт заново через «Импорт портфеля».'
      : apiErrorMessage(error, 'Не удалось запустить импорт заново')
  } finally {
    retrying.value = false
  }
}

// Закрытие окна не отменяет импорт — он продолжится в фоне
const handleClose = () => {
  importTasksStore.closeModal(props.taskId)
  emit('close')
}

onMounted(() => {
  importTasksStore.openModal(props.taskId)
  if (props.taskId) {
    startPolling()
  }
})

onUnmounted(() => {
  importTasksStore.closeModal(props.taskId)
  stopPolling()
})

watch(() => props.taskId, (newId, oldId) => {
  if (newId) {
    stopPolling()
    if (oldId) importTasksStore.closeModal(oldId)
    resetState()
    importTasksStore.openModal(newId)
    startPolling()
  }
})

const statusIcon = {
  pending: Clock,
  processing: Loader2,
  completed: CheckCircle2,
  failed: XCircle,
  cancelled: Ban
}

const statusText = {
  pending: 'В очереди',
  processing: 'Загружаем данные',
  completed: 'Готово',
  failed: 'Ошибка',
  cancelled: 'Отменено'
}

const statusColor = {
  pending: '#6b7280',
  processing: '#7381ff',
  completed: '#5bd18b',
  failed: '#f2777a',
  cancelled: '#9ca3af'
}
</script>

<template>
  <ModalBase title="Импорт портфеля" :icon="Upload" @close="handleClose">
    <template #close-button>
      <button
        class="close-btn"
        @click="handleClose"
        :aria-label="isActive ? 'Свернуть' : 'Закрыть'"
        :title="isActive ? 'Свернуть — импорт продолжится в фоне' : 'Закрыть'"
      >
        <X :size="16" />
      </button>
    </template>
    <div class="status-content">
      <div class="status-info">
        <div class="status-badge" :style="{ color: statusColor[status] }">
          <component :is="statusIcon[status]" :size="18" class="status-icon" :class="{ 'spinning': status === 'processing' }" />
          <span class="status-text">{{ statusText[status] }}</span>
        </div>
      </div>

      <div v-if="isActive" class="progress-section">
        <div class="progress-bar-container">
          <div
            class="progress-bar"
            :style="{ width: `${progress}%`, backgroundColor: statusColor[status] }"
          ></div>
        </div>
        <div class="progress-text">
          <span class="progress-percent">{{ progress }}%</span>
          <span v-if="progressMessage" class="progress-message">{{ progressMessage }}</span>
        </div>
        <p class="background-hint">
          Окно можно закрыть — импорт продолжится в фоне, а данные на странице обновятся сами.
        </p>
      </div>

      <div v-if="errorMessage && status === 'failed'" class="error-box">
        <XCircle :size="16" class="error-icon" />
        <div>
          <span>{{ errorMessage }}</span>
          <router-link v-if="tokenInvalid" to="/settings#brokers" class="error-link" @click="handleClose">
            Обновить токен в настройках
          </router-link>
        </div>
      </div>

      <div v-if="status === 'cancelled'" class="cancel-box">
        Импорт отменён, данные портфеля не изменились.
      </div>

      <div v-if="status === 'completed'" class="result-box">
        <div class="result-header">
          <CheckCircle2 :size="18" class="result-icon" />
          <span class="result-title">
            Импорт завершён{{ totalInserted !== null ? ` — загружено операций: ${totalInserted}` : '' }}
          </span>
        </div>

        <ul v-if="accounts.length" class="accounts">
          <li v-for="(acc, i) in accounts" :key="acc.portfolio_id || i">
            <div class="accounts__row">
              <span class="accounts__name">{{ acc.account || `Счёт ${i + 1}` }}</span>
              <span class="accounts__count">{{ acc.inserted_count || 0 }} опер.</span>
            </div>

            <div v-if="acc.reconciliation" class="accounts__recon" :class="{ 'is-warn': mismatchCount(acc) }">
              <template v-if="mismatchCount(acc)">
                <AlertTriangle :size="13" />
                <span>
                  Расходится с брокером: {{ mismatchCount(acc) }}
                  {{ plural(mismatchCount(acc), 'позиция', 'позиции', 'позиций') }}
                </span>
              </template>
              <template v-else>
                <CheckCircle2 :size="13" />
                <span>Позиции совпадают с брокером</span>
              </template>
            </div>
            <ul v-if="acc.reconciliation?.mismatches?.length" class="accounts__mismatch">
              <li v-for="m in acc.reconciliation.mismatches" :key="m.asset_id || m.isin || m.ticker">
                <b>{{ m.ticker || m.name || m.isin }}</b>
                <template v-if="m.reason === 'asset_not_found'">
                  у брокера {{ formatQty(m.broker_quantity) }} шт. — бумаги нет в справочнике
                </template>
                <template v-else>
                  у брокера {{ formatQty(m.broker_quantity) }}, в портфеле {{ formatQty(m.portfolio_quantity) }}
                </template>
              </li>
            </ul>

            <div v-for="(line, j) in keptLines(acc)" :key="`kept-${j}`" class="accounts__kept">
              <Info :size="13" />
              <span>{{ line }}</span>
            </div>

            <button
              v-if="acc.transfer_count"
              type="button"
              class="accounts__info"
              :class="{ 'is-warn': unknownTransfers(acc) }"
              @click="toggleDetails(`t${i}`)"
            >
              <component :is="unknownTransfers(acc) ? AlertTriangle : Info" :size="13" />
              <template v-if="unknownTransfers(acc) && unknownTransfers(acc) < acc.transfer_count">
                Переводы бумаг: {{ acc.transfer_count }}, без себестоимости — {{ unknownTransfers(acc) }}
              </template>
              <template v-else-if="unknownTransfers(acc)">
                Без себестоимости: {{ unknownTransfers(acc) }}
                {{ plural(unknownTransfers(acc), 'перевод', 'перевода', 'переводов') }} бумаг
              </template>
              <template v-else>
                Переводы бумаг: {{ acc.transfer_count }} — себестоимость рассчитана, проверьте
              </template>
              <span class="accounts__toggle">{{ openedDetails.has(`t${i}`) ? 'скрыть' : 'подробнее' }}</span>
            </button>
            <ul v-if="openedDetails.has(`t${i}`)" class="accounts__details">
              <li v-for="(t, j) in acc.transfers" :key="j">{{ transferLine(t) }}</li>
              <li class="accounts__more">
                Цену можно исправить в операциях портфеля — правка сохранится при следующей синхронизации.
              </li>
            </ul>

            <button
              v-if="acc.skipped_count || acc.failed_count"
              type="button"
              class="accounts__warn"
              @click="toggleDetails(i)"
            >
              <AlertTriangle :size="13" />
              Не загружено операций: {{ (acc.skipped_count || 0) + (acc.failed_count || 0) }}
              <span class="accounts__toggle">{{ openedDetails.has(i) ? 'скрыть' : 'подробнее' }}</span>
            </button>
            <ul v-if="openedDetails.has(i)" class="accounts__details">
              <li v-for="(line, j) in problemLines(acc)" :key="j">{{ line }}</li>
              <li v-if="problemLines(acc).length < (acc.skipped_count || 0) + (acc.failed_count || 0)" class="accounts__more">
                Показаны первые {{ problemLines(acc).length }}
              </li>
            </ul>
          </li>
        </ul>

        <p v-if="hasProblems" class="result-note">
          Пропущенные операции можно добавить вручную — при следующей синхронизации они сохранятся.
        </p>
      </div>

      <div v-if="retryError" class="error-box">
        <XCircle :size="16" class="error-icon" />
        <span>{{ retryError }}</span>
      </div>

      <div v-if="completedAt && !isActive" class="completed-time">
        Завершено: {{ new Date(completedAt).toLocaleString('ru-RU') }}
      </div>
    </div>

    <div class="form-actions">
      <Button
        v-if="status === 'pending'"
        variant="secondary"
        @click="cancelTask"
      >
        Отменить импорт
      </Button>
      <Button
        v-if="status === 'failed' && !tokenInvalid && portfolioId"
        variant="secondary"
        :loading="retrying"
        :disabled="retrying"
        @click="retry"
      >
        <template #icon>
          <RotateCw :size="15" />
        </template>
        Повторить
      </Button>
      <Button
        :variant="isActive ? 'secondary' : 'primary'"
        @click="handleClose"
      >
        {{ isActive ? 'Свернуть' : 'Закрыть' }}
      </Button>
    </div>
  </ModalBase>
</template>

<style scoped>
.status-content {
  min-height: 160px;
}

.status-info {
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: var(--lx-surface, #f9fafb);
  border-radius: 12px;
  font-weight: 600;
  font-size: 15px;
}

.status-icon {
  flex-shrink: 0;
}

.status-icon.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.progress-section {
  margin-bottom: 20px;
}

.progress-bar-container {
  width: 100%;
  height: 8px;
  background: var(--lx-fill, #e5e7eb);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-bar {
  height: 100%;
  background: var(--lx-accent, #3b82f6);
  border-radius: 4px;
  transition: width 0.3s ease;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.8;
  }
}

.progress-text {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: var(--lx-ink-2, #6b7280);
}

.progress-percent {
  font-weight: 600;
  color: var(--lx-ink, #374151);
}

.progress-message {
  flex: 1;
  text-align: right;
  margin-left: 12px;
}

.background-hint {
  margin: 14px 0 0;
  font-size: 12.5px;
  color: var(--lx-mut, #9ca3af);
  text-align: center;
}

.error-box {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 16px;
  background: var(--lx-down-soft, #fef2f2);
  border: 1px solid var(--lx-down-line, #fecaca);
  border-radius: 10px;
  color: var(--lx-down, #dc2626);
  font-size: 13px;
  line-height: 1.45;
  margin-bottom: 16px;
}

.error-box > div {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.error-link {
  color: var(--lx-accent-ink, #2563eb);
  font-weight: 500;
}

.error-icon {
  flex-shrink: 0;
  margin-top: 1px;
}

.cancel-box {
  padding: 12px 16px;
  border-radius: 10px;
  background: var(--lx-fill, #f3f4f6);
  color: var(--lx-ink-2, #6b7280);
  font-size: 13px;
  text-align: center;
  margin-bottom: 16px;
}

.result-box {
  padding: 16px;
  background: var(--lx-up-soft, #f0fdf4);
  border: 1px solid var(--lx-up-line, #bbf7d0);
  border-radius: 10px;
  margin-bottom: 16px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--lx-up, #059669);
  font-size: 14px;
}

.result-icon {
  flex-shrink: 0;
}

.accounts {
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
  max-height: 280px;
  overflow-y: auto;
}

.accounts > li {
  padding: 9px 0;
  border-top: 1px solid var(--lx-line, #e5e7eb);
  font-size: 13px;
}

.accounts__row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.accounts__name {
  color: var(--lx-ink, #111827);
  font-weight: 500;
}

.accounts__count {
  color: var(--lx-ink-2, #6b7280);
  white-space: nowrap;
}

.accounts__recon,
.accounts__warn {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 5px;
  font-size: 12.5px;
  color: var(--lx-ink-2, #6b7280);
}

.accounts__kept {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 5px;
  font-size: 12.5px;
  color: var(--lx-mut, #9ca3af);
}

.accounts__kept svg {
  flex-shrink: 0;
  margin-top: 2px;
}

.accounts__recon.is-warn {
  color: var(--lx-warn, #d97706);
}

.accounts__info {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 5px;
  padding: 0;
  border: 0;
  background: none;
  font: inherit;
  font-size: 12.5px;
  text-align: left;
  color: var(--lx-ink-2, #6b7280);
  cursor: pointer;
}

.accounts__info.is-warn {
  color: var(--lx-warn, #d97706);
}

.accounts__warn {
  padding: 0;
  border: 0;
  background: none;
  font: inherit;
  font-size: 12.5px;
  color: var(--lx-warn, #d97706);
  cursor: pointer;
}

.accounts__toggle {
  color: var(--lx-accent-ink, #2563eb);
}

.accounts__mismatch,
.accounts__details {
  margin: 6px 0 0 19px;
  padding: 0;
  list-style: none;
  font-size: 12px;
  color: var(--lx-ink-2, #6b7280);
  line-height: 1.6;
}

.accounts__mismatch b {
  color: var(--lx-warn, #d97706);
  font-weight: 600;
  margin-right: 4px;
}

.accounts__more {
  color: var(--lx-mut, #9ca3af);
}

.result-note {
  margin: 10px 0 0;
  font-size: 12.5px;
  color: var(--lx-ink-2, #6b7280);
}

.completed-time {
  text-align: center;
  font-size: 12px;
  color: var(--lx-mut, #9ca3af);
  margin-top: 16px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 16px;
  margin-top: 8px;
  border-top: 1px solid var(--lx-line, #f3f4f6);
}

.close-btn {
  background: var(--lx-fill, #f3f4f6);
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--lx-ink-2, #6b7280);
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.close-btn:hover {
  background: var(--lx-hover, #e5e7eb);
  color: var(--lx-ink, #111827);
  transform: scale(1.05);
}

.close-btn:active {
  transform: scale(0.95);
}
</style>
