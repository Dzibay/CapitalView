<script setup>
/**
 * «Подключения брокеров» в настройках: статус синхронизации, автообновление,
 * замена токена и отключение. Токен сервер не возвращает — только маску.
 */
import { ref, computed, onMounted, onUnmounted, nextTick, useAttrs } from 'vue'
import { useRoute } from 'vue-router'
import { RefreshCw, KeyRound, Unplug, Plus, Check, AlertTriangle, Eye, EyeOff } from 'lucide-vue-next'
import CvWidget from '../ui/CvWidget.vue'
import brokerConnectionsService from '../../services/brokerConnectionsService'
import portfolioService from '../../services/portfolioService'
import taskService from '../../services/taskService'
import { apiErrorMessage } from '../../utils/apiError'
import { plural } from '../format'

const connections = ref([])
const brokers = ref({})
const loading = ref(true)
const loadError = ref('')

// Состояние по id подключения
const busy = ref({}) // 'sync' | 'token' | 'remove' | 'auto'
const notes = ref({}) // { tone: 'ok' | 'err', text }
const tokenForm = ref(null) // id подключения, у которого открыта форма токена
const tokenValue = ref('')
const showToken = ref(false)
const confirmRemove = ref(null)

let alive = true
onUnmounted(() => { alive = false })

const setBusy = (id, value) => { busy.value = { ...busy.value, [id]: value } }
const setNote = (id, note) => { notes.value = { ...notes.value, [id]: note } }

const load = async () => {
  loadError.value = ''
  try {
    connections.value = await brokerConnectionsService.list()
    // Синхронизация, запущенная в другом месте, — показываем её ход и здесь
    connections.value.filter((c) => c.active_task).forEach((c) => watchTask(c.id, c.active_task.task_id))
  } catch (e) {
    loadError.value = apiErrorMessage(e, 'Не удалось загрузить подключения')
  } finally {
    loading.value = false
  }
}

// Ссылка «Обновить токен в настройках» ведёт на /settings#brokers. Роутер прокручивает
// к разделу, пока список ещё грузится и страница короче, — после загрузки докручиваем
const attrs = useAttrs()
const route = useRoute()
const revealIfLinked = () => {
  if (!attrs.id || route.hash !== `#${attrs.id}`) return
  nextTick(() => document.getElementById(attrs.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

onMounted(async () => {
  load().then(revealIfLinked)
  try {
    const list = await portfolioService.getBrokers()
    brokers.value = Object.fromEntries((list || []).map((b) => [b.id, b.name]))
  } catch {
    // имена брокеров не критичны
  }
})

const watching = new Set()
const watchTask = async (id, taskId) => {
  if (!taskId || watching.has(taskId)) return
  watching.add(taskId)
  setBusy(id, 'sync')
  const final = await taskService.waitForTask(taskId)
  watching.delete(taskId)
  if (!alive) return
  setBusy(id, null)
  if (final?.status === 'completed') {
    const n = final.result?.import_result?.inserted_count
    setNote(id, { tone: 'ok', text: n != null ? `Синхронизировано: ${n} ${plural(n, 'операция', 'операции', 'операций')}.` : 'Синхронизировано.' })
  } else if (final?.status === 'failed') {
    setNote(id, { tone: 'err', text: final.error_message || 'Синхронизация не удалась' })
  }
  await load()
}

const sync = async (c) => {
  setNote(c.id, null)
  setBusy(c.id, 'sync')
  try {
    const res = await brokerConnectionsService.sync(c.id)
    if (res.already_active) setNote(c.id, { tone: 'ok', text: 'Синхронизация уже идёт — дождитесь её окончания.' })
    watchTask(c.id, res.task_id)
  } catch (e) {
    setBusy(c.id, null)
    setNote(c.id, { tone: 'err', text: apiErrorMessage(e, 'Не удалось запустить синхронизацию') })
    if (e.response?.status === 409) openTokenForm(c)
  }
}

const openTokenForm = (c) => {
  tokenForm.value = c.id
  tokenValue.value = ''
  showToken.value = false
  confirmRemove.value = null
}

const saveToken = async (c) => {
  if (!tokenValue.value.trim()) return
  setNote(c.id, null)
  setBusy(c.id, 'token')
  try {
    const res = await brokerConnectionsService.replaceToken(c.id, tokenValue.value.trim(), true)
    tokenForm.value = null
    tokenValue.value = ''
    setBusy(c.id, null)
    setNote(c.id, { tone: 'ok', text: 'Токен обновлён. Запустили синхронизацию.' })
    await load()
    if (res.task?.task_id) watchTask(c.id, res.task.task_id)
  } catch (e) {
    setBusy(c.id, null)
    setNote(c.id, { tone: 'err', text: apiErrorMessage(e, 'Не удалось сохранить токен') })
  }
}

const toggleAuto = async (c) => {
  const next = !c.auto_sync
  setBusy(c.id, 'auto')
  try {
    await brokerConnectionsService.setAutoSync(c.id, next)
    c.auto_sync = next
  } catch (e) {
    setNote(c.id, { tone: 'err', text: apiErrorMessage(e, 'Не удалось изменить настройку') })
  } finally {
    setBusy(c.id, null)
  }
}

const remove = async (c) => {
  setBusy(c.id, 'remove')
  try {
    await brokerConnectionsService.remove(c.id)
    connections.value = connections.value.filter((x) => x.id !== c.id)
    confirmRemove.value = null
  } catch (e) {
    setNote(c.id, { tone: 'err', text: apiErrorMessage(e, 'Не удалось отключить брокера') })
  } finally {
    setBusy(c.id, null)
  }
}

const dt = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
const when = (v) => {
  if (!v) return ''
  const d = new Date(v)
  return isNaN(d) ? '' : dt.format(d).replace('.', '')
}

const statusOf = (c) => {
  if (busy.value[c.id] === 'sync') return { tone: 'run', text: 'Синхронизация…' }
  if (!c.has_token) return { tone: 'off', text: 'Нет токена' }
  if (c.last_sync_status === 'token_invalid') return { tone: 'err', text: 'Нужен новый токен' }
  if (c.last_sync_status === 'error') return { tone: 'warn', text: 'Ошибка синхронизации' }
  if (c.last_sync_at) return { tone: 'ok', text: 'Работает' }
  return { tone: 'off', text: 'Ещё не синхронизировано' }
}

const metaOf = (c) => {
  const parts = [brokers.value[c.broker_id] || `Брокер #${c.broker_id}`]
  if (c.token_mask) parts.push(`токен ${c.token_mask}`)
  if (c.last_sync_at) parts.push(`обновлено ${when(c.last_sync_at)}`)
  const s = c.last_sync_summary
  if (s?.accounts?.length) parts.push(`${s.accounts.length} ${plural(s.accounts.length, 'счёт', 'счёта', 'счетов')}`)
  return parts.join(' · ')
}

const subtitle = computed(() => {
  const n = connections.value.length
  if (!n) return 'Автоматическая загрузка сделок и выплат'
  return `${n} ${plural(n, 'подключение', 'подключения', 'подключений')}`
})
</script>

<template>
  <CvWidget class="bc-widget" title="Подключения брокеров" :subtitle="subtitle">
    <template #actions>
      <router-link to="/assets?import=1" class="cv-btn cv-btn--sm">
        <Plus :size="14" /> Подключить брокера
      </router-link>
    </template>

    <p v-if="loading" class="bc__empty">Загружаем подключения…</p>
    <p v-else-if="loadError" class="cv-note cv-note--err" role="alert">{{ loadError }}</p>
    <div v-else-if="!connections.length" class="bc__empty">
      Брокеры пока не подключены. Подключите счёт — сделки, дивиденды и остатки будут загружаться автоматически.
    </div>

    <ul v-else class="bc">
      <li v-for="c in connections" :key="c.id" class="bc__item">
        <div class="bc__row">
          <div class="bc__info">
            <b class="bc__name">{{ c.portfolio_name || `Портфель #${c.portfolio_id}` }}</b>
            <span class="bc__meta">{{ metaOf(c) }}</span>
          </div>
          <span class="bc__pill" :class="`is-${statusOf(c).tone}`"><i />{{ statusOf(c).text }}</span>
        </div>

        <p v-if="c.last_sync_error && c.last_sync_status !== 'ok' && busy[c.id] !== 'sync'" class="bc__error">
          <AlertTriangle :size="13" />{{ c.last_sync_error }}
        </p>
        <p v-if="notes[c.id]" class="cv-note" :class="notes[c.id].tone === 'ok' ? 'cv-note--ok' : 'cv-note--err'">
          <Check v-if="notes[c.id].tone === 'ok'" :size="14" />{{ notes[c.id].text }}
        </p>

        <form v-if="tokenForm === c.id" class="bc__token" @submit.prevent="saveToken(c)">
          <label class="cv-field">
            <span class="cv-label">Новый токен</span>
            <input
              v-model="tokenValue"
              :type="showToken ? 'text' : 'password'"
              class="cv-input"
              placeholder="Вставьте токен"
              autocomplete="off"
              spellcheck="false"
              :disabled="busy[c.id] === 'token'"
            />
          </label>
          <div class="bc__token-actions">
            <button type="button" class="cv-btn cv-btn--ghost cv-btn--sm" @click="showToken = !showToken">
              <component :is="showToken ? EyeOff : Eye" :size="14" /> {{ showToken ? 'Скрыть' : 'Показать' }}
            </button>
            <span class="bc__spacer" />
            <button type="button" class="cv-btn cv-btn--ghost cv-btn--sm" @click="tokenForm = null">Отмена</button>
            <button type="submit" class="cv-btn cv-btn--primary cv-btn--sm" :disabled="!tokenValue.trim() || busy[c.id] === 'token'">
              {{ busy[c.id] === 'token' ? 'Проверяем…' : 'Сохранить и синхронизировать' }}
            </button>
          </div>
          <p class="bc__hint">Перед сохранением проверим токен у брокера. Старый токен будет удалён.</p>
        </form>

        <div v-else-if="confirmRemove === c.id" class="bc__confirm">
          <span>Отключить брокера? Портфель и все операции останутся, но обновляться перестанут, а токен будет удалён.</span>
          <div class="bc__token-actions">
            <button type="button" class="cv-btn cv-btn--ghost cv-btn--sm" @click="confirmRemove = null">Оставить</button>
            <button type="button" class="cv-btn cv-btn--danger cv-btn--sm" :disabled="busy[c.id] === 'remove'" @click="remove(c)">
              {{ busy[c.id] === 'remove' ? 'Отключаем…' : 'Отключить' }}
            </button>
          </div>
        </div>

        <div v-else class="bc__actions">
          <label class="bc__switch" :class="{ 'is-disabled': !c.has_token }">
            <input type="checkbox" :checked="c.auto_sync" :disabled="!c.has_token || busy[c.id] === 'auto'" @change="toggleAuto(c)" />
            <span class="bc__switch-ui" aria-hidden="true" />
            Обновлять автоматически раз в сутки
          </label>
          <span class="bc__spacer" />
          <button
            type="button"
            class="cv-btn cv-btn--sm"
            :disabled="!c.has_token || c.last_sync_status === 'token_invalid' || !!busy[c.id]"
            @click="sync(c)"
          >
            <RefreshCw :size="14" :class="{ 'bc__spin': busy[c.id] === 'sync' }" /> Синхронизировать
          </button>
          <button
            type="button"
            class="cv-btn cv-btn--sm"
            :class="{ 'cv-btn--primary': c.last_sync_status === 'token_invalid' || !c.has_token }"
            :disabled="busy[c.id] === 'sync'"
            @click="openTokenForm(c)"
          >
            <KeyRound :size="14" /> {{ c.has_token ? 'Обновить токен' : 'Указать токен' }}
          </button>
          <button type="button" class="cv-btn cv-btn--ghost cv-btn--sm cv-btn--danger" :disabled="!!busy[c.id]" @click="confirmRemove = c.id; tokenForm = null">
            <Unplug :size="14" /> Отключить
          </button>
        </div>
      </li>
    </ul>
  </CvWidget>
</template>

<style scoped>
/* при переходе по якорю не прятать заголовок под липкой шапкой кабинета */
.bc-widget { scroll-margin-top: 80px; }
.bc { display: flex; flex-direction: column; margin: 0; padding: 0; list-style: none; }
.bc__item { display: flex; flex-direction: column; gap: 10px; padding: 14px 0; border-top: 1px solid var(--cv-line); }
.bc__item:first-child { padding-top: 2px; border-top: 0; }
.bc__row { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.bc__info { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.bc__name { font-size: 14px; font-weight: 600; color: var(--cv-ink); }
.bc__meta { font-size: 12.5px; color: var(--cv-mut); }
.bc__pill {
  display: inline-flex; flex: none; align-items: center; gap: 7px; height: 24px; padding: 0 10px; border-radius: 99px;
  font-size: 12px; font-weight: 550; white-space: nowrap; color: var(--cv-ink-2); background: rgba(255, 255, 255, .04);
}
.bc__pill i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.bc__pill.is-ok { color: var(--cv-up); background: var(--cv-up-bg); }
.bc__pill.is-run { color: var(--cv-accent-ink); background: var(--cv-accent-soft); }
.bc__pill.is-warn { color: var(--cv-warn); background: var(--cv-warn-bg); }
.bc__pill.is-err { color: var(--cv-down); background: var(--cv-down-bg); }
.bc__pill.is-off { color: var(--cv-mut); }
.bc__error { display: flex; align-items: flex-start; gap: 7px; margin: 0; font-size: 12.5px; line-height: 1.5; color: var(--cv-ink-2); }
.bc__error svg { flex: none; margin-top: 3px; color: var(--cv-warn); }
.bc__actions, .bc__token-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.bc__actions .cv-btn, .bc__token-actions .cv-btn { gap: 6px; }
.bc__spacer { flex: 1; }
.bc__spin { animation: bc-spin 1s linear infinite; }
@keyframes bc-spin { to { transform: rotate(360deg); } }
.bc__token, .bc__confirm { display: flex; flex-direction: column; gap: 10px; padding: 12px; border-radius: var(--cv-r-sm); background: rgba(255, 255, 255, .02); box-shadow: inset 0 0 0 1px var(--cv-line); }
.bc__confirm > span { font-size: 13px; line-height: 1.5; color: var(--cv-ink-2); }
.bc__hint { margin: 0; font-size: 12px; color: var(--cv-dim); }
.bc__empty { margin: 0; font-size: 13px; line-height: 1.55; color: var(--cv-mut); }

.bc__switch { display: inline-flex; align-items: center; gap: 9px; font-size: 12.5px; color: var(--cv-ink-2); cursor: pointer; user-select: none; }
.bc__switch.is-disabled { opacity: .5; cursor: not-allowed; }
.bc__switch input { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }
.bc__switch-ui { position: relative; flex: none; width: 30px; height: 18px; border-radius: 99px; background: rgba(255, 255, 255, .1); transition: background .2s var(--cv-ease); }
.bc__switch-ui::after {
  content: ''; position: absolute; top: 2px; left: 2px; width: 14px; height: 14px; border-radius: 50%;
  background: #fff; transition: transform .2s var(--cv-ease);
}
.bc__switch input:checked + .bc__switch-ui { background: var(--cv-accent); }
.bc__switch input:checked + .bc__switch-ui::after { transform: translateX(12px); }
.bc__switch input:focus-visible + .bc__switch-ui { box-shadow: 0 0 0 3px var(--cv-accent-soft); }

@media (max-width: 600px) {
  .bc__row { flex-direction: column; }
  .bc__spacer { display: none; }
}
</style>
