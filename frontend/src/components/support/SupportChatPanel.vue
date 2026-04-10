<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Send } from 'lucide-vue-next'
import { useAuthStore } from '../../stores/auth.store'
import { supportService } from '../../services/supportService'

defineProps({
  /** Виджет внутри личного кабинета: без дублирующего заголовка, цвета из темы приложения */
  embedded: { type: Boolean, default: false },
})

const authStore = useAuthStore()
const router = useRouter()

const messages = ref([])
const draft = ref('')
const loading = ref(false)
const sending = ref(false)
const error = ref('')
const listRef = ref(null)

let pollId = null

function scrollToBottom() {
  const el = listRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

async function loadThread() {
  if (!localStorage.getItem('access_token')) {
    messages.value = []
    return
  }
  loading.value = true
  error.value = ''
  try {
    messages.value = await supportService.fetchMessages()
    await nextTick()
    scrollToBottom()
  } catch (e) {
    error.value =
      e.response?.data?.detail || e.response?.data?.error || e.message || 'Не удалось загрузить чат'
  } finally {
    loading.value = false
  }
}

async function ensureAuth() {
  try {
    const u = await authStore.checkToken()
    return !!u
  } catch {
    return false
  }
}

async function send() {
  const text = draft.value?.trim()
  if (!text || sending.value) return
  sending.value = true
  error.value = ''
  try {
    await supportService.sendMessage(text)
    draft.value = ''
    await loadThread()
  } catch (e) {
    error.value =
      e.response?.data?.detail || e.response?.data?.error || e.message || 'Не удалось отправить'
  } finally {
    sending.value = false
  }
}

function goLogin() {
  router.push({ path: '/login', query: { redirect: '/support#chat' } })
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

watch(messages, () => nextTick().then(scrollToBottom))

onMounted(async () => {
  const ok = await ensureAuth()
  if (ok) {
    await loadThread()
    pollId = window.setInterval(loadThread, 12000)
  }
})

onUnmounted(() => {
  if (pollId != null) {
    clearInterval(pollId)
    pollId = null
  }
})
</script>

<template>
  <div class="support-chat" :class="{ 'support-chat--embedded': embedded }">
    <div v-if="!embedded" class="support-chat__head">
      <h2 class="support-chat__title">Чат с поддержкой</h2>
      <p class="support-chat__lead">
        Напишите вопрос — ответит администратор сервиса. История сохраняется в этом окне.
      </p>
    </div>
    <p v-else class="support-chat__hint">
      Напишите вопрос — ответит администратор. История сохраняется здесь.
    </p>

    <div v-if="!authStore.isAuthenticated" class="support-chat__gate">
      <p class="support-chat__gate-text">
        Чтобы написать в поддержку, войдите в аккаунт — так мы сможем связать переписку с вашими данными.
      </p>
      <button type="button" class="support-chat__btn" @click="goLogin">Войти</button>
    </div>

    <template v-else>
      <div ref="listRef" class="support-chat__messages" role="log" aria-live="polite">
        <div v-if="loading && messages.length === 0" class="support-chat__status">Загрузка…</div>
        <div v-else-if="!loading && messages.length === 0" class="support-chat__empty">
          Пока нет сообщений. Напишите нам — мы ответим в этом чате.
        </div>
        <div
          v-for="m in messages"
          :key="m.id"
          class="support-chat__row"
          :class="{ 'support-chat__row--user': !m.is_from_admin, 'support-chat__row--admin': m.is_from_admin }"
        >
          <div class="support-chat__bubble">
            <p class="support-chat__text">{{ m.message }}</p>
            <time class="support-chat__time" :datetime="m.created_at">{{ formatTime(m.created_at) }}</time>
          </div>
        </div>
      </div>

      <div v-if="error" class="support-chat__error" role="alert">{{ error }}</div>

      <div class="support-chat__composer">
        <textarea
          v-model="draft"
          class="support-chat__input"
          rows="3"
          maxlength="5000"
          placeholder="Ваше сообщение…"
          :disabled="sending"
          @keydown.enter.exact.prevent="send"
        />
        <div class="support-chat__composer-foot">
          <span class="support-chat__counter">{{ draft.length }} / 5000</span>
          <button
            type="button"
            class="support-chat__send"
            :disabled="sending || !draft.trim()"
            @click="send"
          >
            <Send :size="18" stroke-width="2" aria-hidden="true" />
            {{ sending ? 'Отправка…' : 'Отправить' }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.support-chat {
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
}

.support-chat--embedded {
  max-width: none;
  margin: 0;
  --font-display: inherit;
  --font-body: inherit;
  --color-text: var(--text-primary, #0f172a);
  --color-text-secondary: var(--text-tertiary, #64748b);
  --color-primary: var(--primary, #3b82f6);
  --color-primary-hover: var(--primary-hover, #2563eb);
}

.support-chat__hint {
  margin: 0 0 1rem;
  font-size: var(--text-caption-size, 0.875rem);
  line-height: 1.5;
  color: var(--text-secondary, #64748b);
}

.support-chat__head {
  text-align: center;
  margin-bottom: 2rem;
}

.support-chat__title {
  margin: 0 0 0.75rem;
  font-family: var(--font-display);
  font-size: clamp(1.5rem, 3vw, 2rem);
  font-weight: 300;
  letter-spacing: -0.02em;
  color: var(--color-text);
}

.support-chat__lead {
  margin: 0;
  font-size: 0.9375rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.support-chat__gate {
  padding: 1.75rem 1.5rem;
  border-radius: 16px;
  border: 1px dashed rgba(15, 23, 42, 0.12);
  background: rgba(248, 250, 252, 0.9);
  text-align: center;
}

.support-chat__gate-text {
  margin: 0 0 1.25rem;
  font-size: 0.9375rem;
  line-height: 1.55;
  color: var(--color-text-secondary);
}

.support-chat__btn {
  padding: 0.65rem 1.5rem;
  border-radius: 999px;
  border: none;
  background: var(--color-primary);
  color: #fff;
  font-family: var(--font-body);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.15s ease;
}

.support-chat__btn:hover {
  background: var(--color-primary-hover);
}

.support-chat__btn:active {
  transform: scale(0.98);
}

.support-chat__messages {
  max-height: min(52vh, 420px);
  overflow-y: auto;
  padding: 0.5rem 0.25rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.65);
  margin-bottom: 1rem;
}

.support-chat__status,
.support-chat__empty {
  padding: 1.25rem;
  text-align: center;
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

.support-chat__row {
  display: flex;
  width: 100%;
}

.support-chat__row--user {
  justify-content: flex-end;
}

.support-chat__row--admin {
  justify-content: flex-start;
}

.support-chat__bubble {
  max-width: min(88%, 420px);
  padding: 0.65rem 0.85rem 0.5rem;
  border-radius: 14px;
  box-sizing: border-box;
}

.support-chat__row--user .support-chat__bubble {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.14), rgba(59, 130, 246, 0.06));
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.support-chat__row--admin .support-chat__bubble {
  background: rgba(241, 245, 249, 0.95);
  border: 1px solid rgba(15, 23, 42, 0.08);
}

.support-chat__text {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--color-text);
  white-space: pre-wrap;
  word-break: break-word;
}

.support-chat__time {
  display: block;
  margin-top: 0.35rem;
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  opacity: 0.85;
}

.support-chat__error {
  padding: 0.65rem 0.85rem;
  margin-bottom: 0.75rem;
  border-radius: 10px;
  background: rgba(239, 68, 68, 0.08);
  color: #b91c1c;
  font-size: 0.85rem;
}

.support-chat__composer {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 16px;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.85);
}

.support-chat__input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 12px;
  padding: 0.65rem 0.75rem;
  font-family: var(--font-body);
  font-size: 0.9rem;
  resize: vertical;
  min-height: 72px;
  background: #fff;
  color: var(--color-text);
}

.support-chat__input:focus {
  outline: 2px solid rgba(59, 130, 246, 0.35);
  outline-offset: 1px;
}

.support-chat__input:disabled {
  opacity: 0.65;
}

.support-chat__composer-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: 0.65rem;
}

.support-chat__counter {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.support-chat__send {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.55rem 1.1rem;
  border-radius: 999px;
  border: none;
  background: var(--color-primary);
  color: #fff;
  font-family: var(--font-body);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, opacity 0.2s ease;
}

.support-chat__send:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.support-chat__send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 480px) {
  .support-chat__messages {
    max-height: 48vh;
  }
}
</style>
