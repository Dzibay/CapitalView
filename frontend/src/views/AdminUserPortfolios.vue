<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronLeft } from 'lucide-vue-next'
import PageLayout from '../layouts/PageLayout.vue'
import PageHeader from '../layouts/PageHeader.vue'
import LoadingState from '../components/base/LoadingState.vue'
import PortfolioTree from '../components/PortfolioTree.vue'
import { usePortfolio } from '../composables/usePortfolio'
import { adminService } from '../services/adminService'
import { fetchReferenceData } from '../services/referenceService'

const props = defineProps({
  userId: { type: String, required: true },
})

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const portfolios = ref([])
const referenceData = ref({})

const userLabel = computed(() => {
  const q = route.query
  const name = typeof q.name === 'string' ? q.name.trim() : ''
  const email = typeof q.email === 'string' ? q.email.trim() : ''
  if (name && email) return `${name} · ${email}`
  if (email) return email
  if (name) return name
  return `ID: ${props.userId}`
})

const dashboardDataComputed = computed(() => ({
  portfolios: portfolios.value,
  recent_transactions: [],
  referenceData: referenceData.value,
}))

const { buildPortfolioTree } = usePortfolio(dashboardDataComputed, null)

const portfolioTree = computed(() => buildPortfolioTree(portfolios.value))

const expandedPortfolios = ref([])
const updatingPortfolios = ref(new Set())
/** Админ видит полную картину, включая проданные позиции. */
const showSoldAssets = ref(true)

function collectPortfolioIdsFromTree(nodes, acc = []) {
  if (!nodes?.length) return acc
  for (const n of nodes) {
    acc.push(n.id)
    if (n.children?.length) collectPortfolioIdsFromTree(n.children, acc)
  }
  return acc
}

function togglePortfolio(id) {
  const i = expandedPortfolios.value.indexOf(id)
  if (i === -1) {
    expandedPortfolios.value = [...expandedPortfolios.value, id]
  } else {
    expandedPortfolios.value = expandedPortfolios.value.filter((x) => x !== id)
  }
}

async function load() {
  error.value = ''
  loading.value = true
  portfolios.value = []
  try {
    const [refBundle, dashboard] = await Promise.all([
      fetchReferenceData({ bypassCache: false }).catch(() => null),
      adminService.fetchUserDashboard(props.userId),
    ])
    if (refBundle?.reference && typeof refBundle.reference === 'object') {
      referenceData.value = refBundle.reference
    }
    if (!dashboard) {
      error.value = 'Не удалось загрузить данные'
      return
    }
    portfolios.value = dashboard.portfolios || []
    expandedPortfolios.value = collectPortfolioIdsFromTree(
      buildPortfolioTree(portfolios.value),
    )
  } catch (e) {
    const d = e.response?.data
    const msg =
      (typeof d?.error === 'string' && d.error) ||
      (typeof d?.detail?.error === 'string' && d.detail.error) ||
      e.message ||
      'Ошибка загрузки'
    error.value = msg
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(
  () => props.userId,
  () => load(),
)

function backToAdmin() {
  router.push('/admin')
}
</script>

<template>
  <PageLayout>
    <div class="admin-page">
      <header class="admin-page__header">
        <div class="admin-page__header-text">
          <button type="button" class="admin-back" @click="backToAdmin">
            <ChevronLeft :size="18" stroke-width="2.5" aria-hidden="true" />
            К списку пользователей
          </button>
          <PageHeader title="Портфели пользователя" :subtitle="userLabel" />
        </div>
      </header>

      <LoadingState v-if="loading" message="Загрузка портфелей…" />

      <div v-else-if="error" class="admin-error" role="alert">
        {{ error }}
      </div>

      <div v-else-if="!portfolioTree.length" class="admin-empty">
        У пользователя пока нет портфелей.
      </div>

      <div v-else class="admin-panel">
        <p class="admin-ro-hint">
          Просмотр только для чтения: меню действий и переходы в карточки активов отключены.
        </p>
        <PortfolioTree
          :portfolios="portfolioTree"
          :expanded-portfolios="expandedPortfolios"
          :updating-portfolios="updatingPortfolios"
          :show-sold-assets="showSoldAssets"
          :read-only="true"
          @toggle-portfolio="togglePortfolio"
        />
      </div>
    </div>
  </PageLayout>
</template>

<style scoped>
.admin-page {
  padding-bottom: 0.5rem;
}

.admin-page__header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.admin-page__header-text {
  flex: 1 1 12rem;
  min-width: 0;
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

.admin-error {
  padding: 1rem 1.25rem;
  border-radius: 12px;
  background: #fef2f2;
  color: var(--danger-dark, #b91c1c);
  border: 1px solid #fecaca;
}

.admin-empty {
  padding: 2rem 1rem;
  text-align: center;
  color: var(--text-tertiary, #6b7280);
  font-size: var(--text-caption-size, 0.875rem);
  background: var(--bg-secondary, #f8fafc);
  border-radius: 12px;
  border: 1px dashed var(--axis-border, #e2e8f0);
}

.admin-panel {
  padding: 1.125rem;
  border-radius: 16px;
  background: var(--bg-primary, #fff);
  border: 1px solid var(--axis-grid, #e5e7eb);
  box-shadow: 0 4px 24px -8px rgba(15, 23, 42, 0.08);
}

@media (min-width: 769px) {
  .admin-panel {
    padding: 1.35rem 1.5rem;
  }
}

.admin-ro-hint {
  margin: 0 0 1rem;
  font-size: var(--text-caption-size, 0.875rem);
  color: var(--text-tertiary, #6b7280);
  line-height: 1.5;
  max-width: 48rem;
}
</style>
