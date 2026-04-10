<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { RefreshCw, Send } from 'lucide-vue-next'
import PageLayout from '../layouts/PageLayout.vue'
import PageHeader from '../layouts/PageHeader.vue'
import LoadingState from '../components/base/LoadingState.vue'
import { useAdminStore } from '../stores/admin.store'

const router = useRouter()
const adminStore = useAdminStore()
const { supportMessages, supportMessagesError } = storeToRefs(adminStore)

const loading = ref(!adminStore.hasFreshSupportMessages)
const refreshing = ref(false)
const selectedUserId = ref(null)
const replyText = ref('')
const replySending = ref(false)
const replyError = ref('')

const threads = computed(() => {
  const list = supportMessages.value || []
  const map = new Map()
  for (const m of list) {
    const uid = m.user_id
    if (!uid) continue
    if (!map.has(uid)) {
      map.set(uid, {
        userId: uid,
        user_email: m.user_email || '—',
        user_name: m.user_name || '',
        messages: [],
      })
    }
    map.get(uid).messages.push(m)
  }
  for (const t of map.values()) {
    t.messages.sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
  }
  return Array.from(map.values()).sort((a, b) => {
    const la = a.messages[a.messages.length - 1]
    const lb = b.messages[b.messages.length - 1]
    return new Date(lb?.created_at || 0) - new Date(la?.created_at || 0)
  })
})

const activeThread = computed(() => {
  if (!selectedUserId.value) return null
  return threads.value.find((t) => t.userId === selectedUserId.value) || null
})

function formatDateTime(value) {
  if (value == null || value === '') return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function goAdmin() {
  router.push('/admin')
}

async function load(force) {
  if (!force && adminStore.hasFreshSupportMessages) {
    return
  }
  if (force) {
    refreshing.value = true
  } else {
    loading.value = true
  }
  try {
    await adminStore.fetchSupportMessages(force)
    if (!selectedUserId.value && threads.value.length) {
      selectedUserId.value = threads.value[0].userId
    }
    if (
      selectedUserId.value &&
      !threads.value.some((t) => t.userId === selectedUserId.value)
    ) {
      selectedUserId.value = threads.value[0]?.userId ?? null
    }
  } catch {
    /* текст в store */
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

async function sendReply() {
  const uid = selectedUserId.value
  const text = replyText.value?.trim()
  replyError.value = ''
  if (!uid || !text) {
    replyError.value = 'Выберите пользователя и введите ответ'
    return
  }
  replySending.value = true
  try {
    await adminStore.sendSupportReply(uid, text)
    replyText.value = ''
  } catch (e) {
    const d = e.response?.data?.detail
    replyError.value =
      (typeof d === 'string' ? d : d?.error) ||
      e.response?.data?.error ||
      e.message ||
      'Не удалось отправить ответ'
  } finally {
    replySending.value = false
  }
}

onMounted(() => {
  adminStore.supportMessagesError = ''
  load(false)
})
</script>

<template>
  <PageLayout>
    <div class="admin-page">
      <header class="admin-page__header">
        <div class="admin-page__header-text">
          <button type="button" class="admin-back" @click="goAdmin">
            ← Статистика
          </button>
          <PageHeader title="Поддержка" />
          <p class="admin-page__subtitle-line">
            Переписки с пользователями. Ответы отображаются у них на странице «Поддержка».
          </p>
        </div>
        <button
          type="button"
          class="admin-page__to-app admin-page__refresh"
          :disabled="loading || refreshing"
          @click="load(true)"
        >
          <RefreshCw
            class="admin-page__refresh-icon"
            :class="{ 'admin-page__refresh-icon--spin': refreshing }"
            :size="16"
            stroke-width="2.25"
            aria-hidden="true"
          />
          Обновить
        </button>
      </header>

      <LoadingState v-if="loading" message="Загрузка…" />

      <div v-else-if="supportMessagesError" class="admin-error" role="alert">
        {{ supportMessagesError }}
      </div>

      <div v-else class="messenger">
        <aside class="messenger__sidebar" aria-label="Пользователи">
          <div v-if="threads.length === 0" class="messenger__empty-side">
            Нет обращений в поддержку.
          </div>
          <ul v-else class="messenger__users">
            <li v-for="t in threads" :key="t.userId">
              <button
                type="button"
                class="messenger__user-btn"
                :class="{ 'messenger__user-btn--active': selectedUserId === t.userId }"
                @click="selectedUserId = t.userId"
              >
                <span class="messenger__user-email">{{ t.user_email }}</span>
                <span v-if="t.user_name" class="messenger__user-name">{{ t.user_name }}</span>
                <span class="messenger__user-preview">
                  {{ t.messages[t.messages.length - 1]?.message || '' }}
                </span>
              </button>
            </li>
          </ul>
        </aside>

        <section class="messenger__main" aria-label="Чат">
          <div v-if="!activeThread" class="messenger__placeholder">
            Выберите пользователя слева или дождитесь нового обращения.
          </div>
          <template v-else>
            <div class="messenger__thread-head">
              <div>
                <div class="messenger__thread-email">{{ activeThread.user_email }}</div>
                <div v-if="activeThread.user_name" class="messenger__thread-name">
                  {{ activeThread.user_name }}
                </div>
              </div>
            </div>

            <div class="messenger__scroll">
              <div
                v-for="m in activeThread.messages"
                :key="m.id"
                class="messenger__row"
                :class="{
                  'messenger__row--user': !m.is_from_admin,
                  'messenger__row--admin': m.is_from_admin,
                }"
              >
                <div class="messenger__bubble">
                  <span class="messenger__role">
                    {{ m.is_from_admin ? 'Администратор' : 'Пользователь' }}
                  </span>
                  <p class="messenger__text">{{ m.message }}</p>
                  <time class="messenger__time" :datetime="m.created_at">
                    {{ formatDateTime(m.created_at) }}
                  </time>
                </div>
              </div>
            </div>

            <div class="messenger__reply">
              <div v-if="replyError" class="messenger__reply-error" role="alert">
                {{ replyError }}
              </div>
              <textarea
                v-model="replyText"
                class="messenger__textarea"
                rows="3"
                maxlength="5000"
                placeholder="Ответ пользователю…"
                :disabled="replySending"
              />
              <div class="messenger__reply-foot">
                <span class="messenger__counter">{{ replyText.length }} / 5000</span>
                <button
                  type="button"
                  class="messenger__send"
                  :disabled="replySending || !replyText.trim()"
                  @click="sendReply"
                >
                  <Send :size="16" stroke-width="2.25" aria-hidden="true" />
                  {{ replySending ? 'Отправка…' : 'Отправить ответ' }}
                </button>
              </div>
            </div>
          </template>
        </section>
      </div>
    </div>
  </PageLayout>
</template>

<style scoped>
.admin-page {
  padding-bottom: 0.5rem;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.admin-page__header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.admin-page__header-text :deep(.page-header) {
  margin-bottom: 0.35rem;
}

.admin-page__subtitle-line {
  margin: 0;
  font-size: var(--text-heading-2-size, 1rem);
  font-weight: var(--text-heading-2-weight, 400);
  color: var(--text-heading-2-color, var(--text-tertiary));
  line-height: var(--text-heading-2-line, 1.35);
  max-width: 100%;
}

.admin-back {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-bottom: 0.75rem;
  padding: 0.35rem 0.6rem 0.35rem 0.25rem;
  border: none;
  background: transparent;
  color: var(--primary, #527de5);
  font-size: var(--text-caption-size, 0.875rem);
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  border-radius: 8px;
}

.admin-back:hover {
  background: rgba(82, 125, 229, 0.08);
}

.admin-back:focus-visible {
  outline: 2px solid var(--primary, #527de5);
  outline-offset: 2px;
}

.admin-page__to-app {
  flex-shrink: 0;
  align-self: flex-start;
  margin-top: 0.125rem;
  padding: 0.5rem 1rem;
  border-radius: 10px;
  border: 1px solid var(--axis-border, #d1d5db);
  background: var(--bg-primary, #fff);
  color: var(--primary, #527de5);
  font-size: var(--text-caption-size, 0.875rem);
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease,
    color 0.15s ease;
}

.admin-page__to-app:hover:not(:disabled) {
  border-color: var(--primary, #527de5);
  background: rgba(82, 125, 229, 0.06);
  color: var(--primary-hover, #4568d4);
}

.admin-page__to-app:focus-visible {
  outline: 2px solid var(--primary, #527de5);
  outline-offset: 2px;
}

.admin-page__refresh {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.admin-page__to-app:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.admin-page__refresh-icon--spin {
  animation: admin-msg-spin 0.85s linear infinite;
}

@keyframes admin-msg-spin {
  to {
    transform: rotate(360deg);
  }
}

.admin-error {
  padding: 1rem 1.25rem;
  border-radius: 12px;
  background: #fef2f2;
  color: var(--danger-dark, #b91c1c);
  border: 1px solid #fecaca;
}

.messenger {
  display: grid;
  grid-template-columns: minmax(220px, 280px) 1fr;
  gap: 0;
  min-height: 420px;
  max-height: min(72vh, 640px);
  border-radius: 16px;
  border: 1px solid var(--axis-grid, #e5e7eb);
  background: var(--bg-primary, #fff);
  overflow: hidden;
  box-shadow: 0 4px 24px -8px rgba(15, 23, 42, 0.08);
}

.messenger__sidebar {
  border-right: 1px solid var(--axis-grid, #e5e7eb);
  background: var(--bg-secondary, #f9fafb);
  overflow-y: auto;
  min-width: 0;
}

.messenger__empty-side {
  padding: 1.25rem;
  font-size: 0.875rem;
  color: var(--text-tertiary, #6b7280);
}

.messenger__users {
  list-style: none;
  margin: 0;
  padding: 0.5rem 0;
}

.messenger__user-btn {
  width: 100%;
  text-align: left;
  padding: 0.65rem 0.85rem;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  border-left: 3px solid transparent;
  transition: background 0.15s ease;
}

.messenger__user-btn:hover {
  background: rgba(82, 125, 229, 0.06);
}

.messenger__user-btn--active {
  background: rgba(82, 125, 229, 0.1);
  border-left-color: var(--primary, #527de5);
}

.messenger__user-email {
  display: block;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-primary, #111827);
  word-break: break-word;
}

.messenger__user-name {
  display: block;
  font-size: 0.75rem;
  color: var(--text-tertiary, #6b7280);
  margin-top: 0.15rem;
}

.messenger__user-preview {
  display: block;
  font-size: 0.72rem;
  color: var(--text-tertiary, #9ca3af);
  margin-top: 0.35rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.messenger__main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

.messenger__placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  text-align: center;
  color: var(--text-tertiary, #6b7280);
  font-size: 0.9rem;
}

.messenger__thread-head {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--axis-grid, #e5e7eb);
  flex-shrink: 0;
}

.messenger__thread-email {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--text-primary, #111827);
  word-break: break-word;
}

.messenger__thread-name {
  font-size: 0.8125rem;
  color: var(--text-tertiary, #6b7280);
  margin-top: 0.2rem;
}

.messenger__scroll {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  background: var(--bg-primary, #fff);
}

.messenger__row {
  display: flex;
  width: 100%;
}

.messenger__row--user {
  justify-content: flex-start;
}

.messenger__row--admin {
  justify-content: flex-end;
}

.messenger__bubble {
  max-width: min(92%, 400px);
  padding: 0.55rem 0.75rem 0.45rem;
  border-radius: 12px;
  border: 1px solid var(--axis-grid, #e5e7eb);
  background: var(--bg-secondary, #f9fafb);
}

.messenger__row--admin .messenger__bubble {
  background: rgba(82, 125, 229, 0.1);
  border-color: rgba(82, 125, 229, 0.25);
}

.messenger__role {
  display: block;
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-tertiary, #6b7280);
  margin-bottom: 0.25rem;
}

.messenger__text {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.45;
  color: var(--text-secondary, #374151);
  white-space: pre-wrap;
  word-break: break-word;
}

.messenger__time {
  display: block;
  margin-top: 0.35rem;
  font-size: 0.7rem;
  color: var(--text-tertiary, #9ca3af);
}

.messenger__reply {
  flex-shrink: 0;
  padding: 0.75rem 1rem 1rem;
  border-top: 1px solid var(--axis-grid, #e5e7eb);
  background: var(--bg-secondary, #f9fafb);
}

.messenger__reply-error {
  font-size: 0.8125rem;
  color: var(--danger-dark, #b91c1c);
  margin-bottom: 0.5rem;
}

.messenger__textarea {
  width: 100%;
  box-sizing: border-box;
  border-radius: 10px;
  border: 1px solid var(--axis-border, #d1d5db);
  padding: 0.5rem 0.65rem;
  font-family: inherit;
  font-size: 0.875rem;
  resize: vertical;
  min-height: 72px;
  background: var(--bg-primary, #fff);
}

.messenger__textarea:focus {
  outline: 2px solid rgba(82, 125, 229, 0.35);
  outline-offset: 1px;
}

.messenger__textarea:disabled {
  opacity: 0.65;
}

.messenger__reply-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.messenger__counter {
  font-size: 0.75rem;
  color: var(--text-tertiary, #9ca3af);
}

.messenger__send {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.45rem 0.9rem;
  border-radius: 999px;
  border: none;
  background: var(--primary, #527de5);
  color: #fff;
  font-size: 0.8125rem;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
}

.messenger__send:hover:not(:disabled) {
  filter: brightness(0.95);
}

.messenger__send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .admin-page {
    padding-bottom: calc(var(--bottomNavHeight, 76px) + env(safe-area-inset-bottom, 0px) + 0.75rem);
  }

  .admin-page__header {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .admin-page__to-app {
    align-self: stretch;
    width: 100%;
    justify-content: center;
    min-height: 44px;
    box-sizing: border-box;
  }

  .messenger {
    grid-template-columns: 1fr;
    max-height: none;
    min-height: 360px;
  }

  .messenger__sidebar {
    border-right: none;
    border-bottom: 1px solid var(--axis-grid, #e5e7eb);
    max-height: 200px;
  }
}
</style>
