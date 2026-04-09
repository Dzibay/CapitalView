<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { RefreshCw } from 'lucide-vue-next'
import PageLayout from '../layouts/PageLayout.vue'
import PageHeader from '../layouts/PageHeader.vue'
import LoadingState from '../components/base/LoadingState.vue'
import { useAdminStore } from '../stores/admin.store'

const router = useRouter()
const adminStore = useAdminStore()
const { supportMessages, supportMessagesError } = storeToRefs(adminStore)

const loading = ref(!adminStore.hasFreshSupportMessages)
const refreshing = ref(false)

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
  } catch {
    /* текст в store */
  } finally {
    loading.value = false
    refreshing.value = false
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
          <PageHeader title="Сообщения в поддержку" />
          <p class="admin-page__subtitle-line">
            Обращения пользователей (данные кэшируются при навигации по админке)
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

      <LoadingState v-if="loading" message="Загрузка сообщений…" />

      <div v-else-if="supportMessagesError" class="admin-error" role="alert">
        {{ supportMessagesError }}
      </div>

      <div v-else class="admin-body">
        <section class="admin-panel messages-section" aria-labelledby="admin-messages-title">
          <h2 id="admin-messages-title" class="admin-section-title">
            Сообщения
          </h2>
          <p class="admin-section-caption">
            Новые сверху. Список подгружается при первом заходе на страницу и при нажатии «Обновить».
          </p>

          <div v-if="supportMessages.length === 0" class="users-empty">
            Нет сообщений в поддержку.
          </div>

          <ul v-else class="messages-list">
            <li
              v-for="m in supportMessages"
              :key="m.id"
              class="messages-list__item"
            >
              <div class="messages-list__meta">
                <span class="messages-list__id">#{{ m.id }}</span>
                <time class="messages-list__time" :datetime="m.created_at">
                  {{ formatDateTime(m.created_at) }}
                </time>
              </div>
              <div class="messages-list__user">
                <span class="messages-list__email">{{ m.user_email || '—' }}</span>
                <span v-if="m.user_name" class="messages-list__name">{{ m.user_name }}</span>
              </div>
              <p class="messages-list__text">
                {{ m.message }}
              </p>
            </li>
          </ul>
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

.admin-page__refresh:disabled {
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

.admin-body {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  min-width: 0;
  max-width: 100%;
}

.admin-panel {
  padding: 1.125rem 1.125rem 1.25rem;
  border-radius: 16px;
  background: var(--bg-primary, #fff);
  border: 1px solid var(--axis-grid, #e5e7eb);
  box-shadow: 0 4px 24px -8px rgba(15, 23, 42, 0.08);
  min-width: 0;
  max-width: 100%;
}

.admin-section-title {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--text-primary, #111827);
  letter-spacing: -0.02em;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--axis-grid, #e5e7eb);
  position: relative;
}

.admin-section-title::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: -1px;
  width: 2.75rem;
  height: 2px;
  border-radius: 2px;
  background: var(--primary-gradient, linear-gradient(135deg, #527de5, #6b91ea));
}

.admin-section-caption {
  margin: 0.75rem 0 1rem;
  font-size: var(--text-caption-size, 0.875rem);
  line-height: 1.5;
  color: var(--text-tertiary, #6b7280);
  max-width: 100%;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.users-empty {
  padding: 1.5rem 1rem;
  text-align: center;
  color: var(--text-tertiary, #64748b);
  font-size: 0.9375rem;
  background: var(--bg-secondary, #f8fafc);
  border-radius: 12px;
  border: 1px dashed var(--axis-border, #e2e8f0);
}

.messages-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.messages-list__item {
  padding: 1rem 1.125rem;
  border-radius: 12px;
  border: 1px solid var(--axis-grid, #e5e7eb);
  background: var(--bg-secondary, #f9fafb);
}

.messages-list__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.5rem 1rem;
  margin-bottom: 0.5rem;
}

.messages-list__id {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--text-tertiary, #6b7280);
  font-variant-numeric: tabular-nums;
}

.messages-list__time {
  font-size: 0.8125rem;
  color: var(--text-tertiary, #6b7280);
  font-variant-numeric: tabular-nums;
}

.messages-list__user {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.75rem;
  margin-bottom: 0.65rem;
  font-size: var(--text-caption-size, 0.875rem);
}

.messages-list__email {
  font-weight: 600;
  color: var(--text-primary, #111827);
  word-break: break-word;
}

.messages-list__name {
  color: var(--text-secondary, #475569);
}

.messages-list__text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: var(--text-caption-size, 0.875rem);
  line-height: 1.5;
  color: var(--text-secondary, #374151);
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

  .admin-back {
    align-self: flex-start;
    min-height: 44px;
    margin-bottom: 0.25rem;
  }

  .admin-panel {
    padding: 0.875rem 0.75rem 1rem;
    border-radius: 14px;
  }

  .admin-error,
  .users-empty {
    padding: 1rem 0.875rem;
    font-size: 0.875rem;
  }
}
</style>
