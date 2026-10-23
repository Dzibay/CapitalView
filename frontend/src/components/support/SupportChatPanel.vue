<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { MessageCircle, Send } from 'lucide-vue-next'
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
  <div class="sc" :class="{ 'sc--embedded': embedded }">
    <div v-if="!embedded" class="sc__head">
      <h2 class="sc__title">Чат с поддержкой</h2>
      <p class="sc__lead">Напишите вопрос — ответит администратор сервиса. История сохраняется в этом окне.</p>
    </div>

    <div v-if="!authStore.isAuthenticated" class="sc__gate">
      <p>Чтобы написать в поддержку, войдите в аккаунт — так мы сможем связать переписку с вашими данными.</p>
      <button type="button" class="cv-btn cv-btn--primary" @click="goLogin">Войти</button>
    </div>

    <template v-else>
      <div ref="listRef" class="sc__messages" role="log" aria-live="polite">
        <div v-if="loading && messages.length === 0" class="sc__status">Загрузка…</div>
        <div v-else-if="!loading && messages.length === 0" class="sc__empty">
          <span class="sc__empty-ic"><MessageCircle :size="20" /></span>
          <b>Пока нет сообщений</b>
          <span>Опишите вопрос — ответ придёт сюда же.</span>
        </div>
        <div
          v-for="m in messages"
          :key="m.id"
          class="sc__row"
          :class="m.is_from_admin ? 'is-admin' : 'is-user'"
        >
          <span v-if="m.is_from_admin" class="sc__who">Поддержка CapitalView</span>
          <div class="sc__bubble">
            <p class="sc__text">{{ m.message }}</p>
          </div>
          <time class="sc__time" :datetime="m.created_at">{{ formatTime(m.created_at) }}</time>
        </div>
      </div>

      <p v-if="error" class="cv-note cv-note--err" role="alert">{{ error }}</p>

      <form class="sc__composer" @submit.prevent="send">
        <textarea
          v-model="draft"
          class="sc__input"
          rows="2"
          maxlength="5000"
          placeholder="Ваше сообщение…"
          aria-label="Сообщение в поддержку"
          :disabled="sending"
          @keydown.enter.exact.prevent="send"
        />
        <div class="sc__foot">
          <span class="sc__counter">
            <span class="sc__kbd-hint">Enter — отправить, Shift+Enter — новая строка ·</span>
            <span class="cv-num">{{ draft.length }} / 5000</span>
          </span>
          <button type="submit" class="cv-btn cv-btn--primary cv-btn--sm" :disabled="sending || !draft.trim()">
            <Send :size="14" aria-hidden="true" />
            {{ sending ? 'Отправка…' : 'Отправить' }}
          </button>
        </div>
      </form>
    </template>
  </div>
</template>

<style scoped>
.sc { display: flex; flex-direction: column; gap: 12px; width: 100%; max-width: 720px; margin: 0 auto; min-width: 0; }
.sc--embedded { max-width: none; margin: 0; height: 100%; }

.sc__head { margin-bottom: 1.5rem; text-align: center; }
.sc__title { margin: 0 0 .5rem; font-size: 1.75rem; font-weight: 500; letter-spacing: -0.02em; color: var(--cv-ink, inherit); }
.sc__lead { margin: 0; color: var(--cv-mut, inherit); }

.sc__gate {
  display: flex; flex-direction: column; align-items: center; gap: 14px; padding: 28px 20px; text-align: center;
  border-radius: var(--cv-r); box-shadow: inset 0 0 0 1px var(--cv-line);
}
.sc__gate p { margin: 0; max-width: 420px; font-size: 13px; line-height: 1.55; color: var(--cv-mut); }

.sc__messages {
  display: flex; flex-direction: column; gap: 14px; flex: 1 1 auto;
  min-height: 280px; max-height: 440px; padding: 16px; overflow-y: auto; overscroll-behavior: contain;
  border-radius: var(--cv-r); background: rgba(0, 0, 0, .18); box-shadow: inset 0 0 0 1px var(--cv-line);
}
.sc__status { margin: auto; font-size: 13px; color: var(--cv-mut); }
.sc__empty { display: flex; flex-direction: column; align-items: center; gap: 6px; margin: auto; text-align: center; font-size: 12.5px; color: var(--cv-mut); }
.sc__empty b { font-size: 13.5px; font-weight: 600; color: var(--cv-ink); }
.sc__empty-ic {
  display: grid; place-items: center; width: 40px; height: 40px; margin-bottom: 4px; border-radius: 12px;
  color: var(--cv-accent-ink); background: var(--cv-accent-soft);
}

.sc__row { display: flex; flex-direction: column; gap: 4px; max-width: min(78%, 520px); }
.sc__row.is-user { align-self: flex-end; align-items: flex-end; }
.sc__row.is-admin { align-self: flex-start; align-items: flex-start; }
.sc__who { padding: 0 4px; font-size: 11.5px; font-weight: 550; color: var(--cv-mut); }
.sc__bubble { padding: 10px 14px; border-radius: 16px; }
.sc__row.is-user .sc__bubble {
  border-bottom-right-radius: 6px; color: #fff;
  background: linear-gradient(180deg, #6f7ffd, #5866ee);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .16);
}
.sc__row.is-admin .sc__bubble {
  border-bottom-left-radius: 6px; color: var(--cv-ink);
  background: var(--cv-elev); box-shadow: inset 0 0 0 1px var(--cv-line-2);
}
.sc__text { margin: 0; color: inherit; font-size: 13.5px; line-height: 1.5; white-space: pre-wrap; overflow-wrap: anywhere; }
.sc__time { padding: 0 4px; font-size: 11px; color: var(--cv-dim); font-variant-numeric: tabular-nums; }

.sc__composer {
  display: flex; flex-direction: column; gap: 8px; padding: 10px 10px 10px 14px;
  border-radius: var(--cv-r); background: rgba(255, 255, 255, .03); box-shadow: inset 0 0 0 1px var(--cv-line-2);
  transition: box-shadow .2s var(--cv-ease);
}
.sc__composer:focus-within { box-shadow: inset 0 0 0 1px var(--cv-accent-line), 0 0 0 3px var(--cv-accent-soft); }
.sc__input {
  width: 100%; min-height: 44px; padding: 4px 0 0; border: 0; resize: vertical;
  font: inherit; font-size: 13.5px; line-height: 1.5; color: var(--cv-ink); background: transparent;
}
.sc__input:focus { outline: none; }
.sc__input::placeholder { color: var(--cv-dim); }
.sc__input:disabled { opacity: .6; }
.sc__foot { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.sc__counter { display: flex; gap: 6px; min-width: 0; font-size: 11.5px; color: var(--cv-dim); }
@media (max-width: 600px) {
  .sc__messages { max-height: 60vh; padding: 12px; }
  .sc__row { max-width: 88%; }
  .sc__kbd-hint { display: none; }
}
</style>
