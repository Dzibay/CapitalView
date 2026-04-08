<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-vue-next'
import PageLayout from '../layouts/PageLayout.vue'
import PageHeader from '../layouts/PageHeader.vue'
import LoadingState from '../components/base/LoadingState.vue'
import MultiLineChart from '../components/charts/MultiLineChart.vue'
import { adminService } from '../services/adminService'

const router = useRouter()
const loading = ref(true)
const error = ref('')
const overview = ref(null)
const usersSeries = ref([])
const adminUsers = ref([])

/** По умолчанию: дата регистрации, новые сверху (по убыванию даты). */
const usersSortKey = ref('created_at')
const usersSortDir = ref('desc')

function userSortTimestamp(value, descending) {
  if (value == null || value === '') {
    return descending ? Number.NEGATIVE_INFINITY : Number.POSITIVE_INFINITY
  }
  const t = new Date(value).getTime()
  if (Number.isNaN(t)) {
    return descending ? Number.NEGATIVE_INFINITY : Number.POSITIVE_INFINITY
  }
  return t
}

const sortedAdminUsers = computed(() => {
  const list = [...adminUsers.value]
  const key = usersSortKey.value
  const desc = usersSortDir.value === 'desc'
  list.sort((a, b) => {
    const av = userSortTimestamp(a[key], desc)
    const bv = userSortTimestamp(b[key], desc)
    return desc ? bv - av : av - bv
  })
  return list
})

function toggleUsersSort(column) {
  if (usersSortKey.value === column) {
    usersSortDir.value = usersSortDir.value === 'desc' ? 'asc' : 'desc'
  } else {
    usersSortKey.value = column
    usersSortDir.value = 'desc'
  }
}

function usersSortAriaSort(column) {
  if (usersSortKey.value !== column) return 'none'
  return usersSortDir.value === 'asc' ? 'ascending' : 'descending'
}

const usersChartData = computed(() => {
  const pts = usersSeries.value || []
  if (!pts.length) {
    return { labels: [], datasets: [] }
  }
  return {
    labels: pts.map((p) => p.date),
    datasets: [
      {
        label: 'Всего пользователей',
        data: pts.map((p) => Number(p.cumulative_users)),
        color: '#527de5',
        fill: true,
      },
      {
        label: 'С подтверждённым email',
        data: pts.map((p) => Number(p.cumulative_verified)),
        color: '#0d9488',
        fill: false,
      },
    ],
  }
})

function formatCount(v) {
  if (typeof v !== 'number' || !Number.isFinite(v)) return String(v)
  return v.toLocaleString('ru-RU', { maximumFractionDigits: 0 })
}

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

const usersChartTooltipCallbacks = {
  label(ctx) {
    const label = ctx.dataset?.label || ''
    const raw = ctx.raw
    return `${label}: ${formatCount(raw)}`
  },
}

onMounted(async () => {
  error.value = ''
  loading.value = true
  try {
    const { overview: ov, users_registration_series: series, users } =
      await adminService.fetchAdminData()
    overview.value = ov
    usersSeries.value = series
    adminUsers.value = users
  } catch (e) {
    error.value = e.response?.data?.error || e.message || 'Не удалось загрузить статистику'
  } finally {
    loading.value = false
  }
})

function goSettings() {
  router.push('/settings')
}

function openUserPortfolios(u) {
  router.push({
    path: `/admin/users/${u.id}`,
    query: {
      name: u.name != null ? String(u.name) : '',
      email: u.email != null ? String(u.email) : '',
    },
  })
}
</script>

<template>
  <PageLayout>
    <div class="admin-page">
      <header class="admin-page__header">
        <div class="admin-page__header-text">
          <PageHeader title="Администрирование" subtitle="Сводка по сервису" />
        </div>
        <button type="button" class="admin-page__to-app" @click="goSettings">
          Настройки
        </button>
      </header>

      <LoadingState v-if="loading" message="Загрузка статистики…" />

      <div v-else-if="error" class="admin-error" role="alert">
        {{ error }}
      </div>

      <div v-else-if="overview" class="admin-body">
        <div class="stats-grid">
          <div class="stat-card">
            <span class="stat-label">Пользователей</span>
            <span class="stat-value">{{ overview.users_total }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">С подтверждённым email</span>
            <span class="stat-value">{{ overview.users_verified }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">Портфелей</span>
            <span class="stat-value">{{ overview.portfolios_total }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">Связей портфель–актив</span>
            <span class="stat-value">{{ overview.portfolio_assets_total }}</span>
          </div>
        </div>

        <section class="admin-panel chart-section" aria-labelledby="admin-users-chart-title">
          <h2 id="admin-users-chart-title" class="admin-section-title">
            Рост пользовательской базы
          </h2>
          <p class="admin-section-caption">
            Накопленное число учётных записей по дате регистрации (UTC). Вторая линия — среди них с подтверждённым email (по текущему состоянию профиля).
          </p>

          <div v-if="usersSeries.length === 0" class="chart-empty">
            Нет зарегистрированных пользователей — график появится после первых регистраций.
          </div>

          <template v-else>
            <div class="chart-legend" aria-hidden="true">
              <span class="chart-legend-item">
                <span class="chart-legend-swatch chart-legend-swatch--primary" />
                Всего пользователей
              </span>
              <span class="chart-legend-item">
                <span class="chart-legend-swatch chart-legend-swatch--verified" />
                С подтверждённым email
              </span>
            </div>
            <div class="admin-chart-wrap">
              <MultiLineChart
                :chart-data="usersChartData"
                period="All"
                skip-aggregation
                :zero-at-start="false"
                :format-currency="formatCount"
                :tooltip-callbacks="usersChartTooltipCallbacks"
                aggregation-end="lastPoint"
              />
            </div>
          </template>
        </section>

        <section class="admin-panel users-section" aria-labelledby="admin-users-list-title">
          <h2 id="admin-users-list-title" class="admin-section-title">
            Пользователи
          </h2>
          <p class="admin-section-caption">
            Сортировка по столбцам «Регистрация» и «Последний вход». У без входа дата последнего входа не заполняется. Строка — переход к просмотру портфелей пользователя.
          </p>

          <div v-if="adminUsers.length === 0" class="users-empty">
            Нет пользователей.
          </div>

          <div v-else class="users-table-wrap">
            <table class="users-table">
              <thead>
                <tr>
                  <th scope="col" class="users-table__th users-table__th--text">
                    <span class="users-table__th-label">Имя</span>
                  </th>
                  <th scope="col" class="users-table__th users-table__th--text">
                    <span class="users-table__th-label">Email</span>
                  </th>
                  <th
                    scope="col"
                    class="users-table__th users-table__th--sort"
                    :aria-sort="usersSortAriaSort('created_at')"
                  >
                    <button
                      type="button"
                      class="users-table__th-btn"
                      @click="toggleUsersSort('created_at')"
                    >
                      <span>Регистрация</span>
                      <span class="users-table__sort-icon" aria-hidden="true">
                        <ArrowUp
                          v-if="usersSortKey === 'created_at' && usersSortDir === 'asc'"
                          :size="14"
                          stroke-width="2.5"
                        />
                        <ArrowDown
                          v-else-if="usersSortKey === 'created_at' && usersSortDir === 'desc'"
                          :size="14"
                          stroke-width="2.5"
                        />
                        <ArrowUpDown
                          v-else
                          :size="14"
                          stroke-width="2"
                          class="users-table__sort-icon--muted"
                        />
                      </span>
                    </button>
                  </th>
                  <th
                    scope="col"
                    class="users-table__th users-table__th--sort"
                    :aria-sort="usersSortAriaSort('last_login_at')"
                  >
                    <button
                      type="button"
                      class="users-table__th-btn"
                      @click="toggleUsersSort('last_login_at')"
                    >
                      <span>Последний вход</span>
                      <span class="users-table__sort-icon" aria-hidden="true">
                        <ArrowUp
                          v-if="usersSortKey === 'last_login_at' && usersSortDir === 'asc'"
                          :size="14"
                          stroke-width="2.5"
                        />
                        <ArrowDown
                          v-else-if="usersSortKey === 'last_login_at' && usersSortDir === 'desc'"
                          :size="14"
                          stroke-width="2.5"
                        />
                        <ArrowUpDown
                          v-else
                          :size="14"
                          stroke-width="2"
                          class="users-table__sort-icon--muted"
                        />
                      </span>
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="u in sortedAdminUsers"
                  :key="u.id"
                  class="users-table__row users-table__row--clickable"
                  tabindex="0"
                  role="button"
                  :aria-label="`Портфели пользователя ${u.email || u.name || u.id}`"
                  @click="openUserPortfolios(u)"
                  @keydown.enter.prevent="openUserPortfolios(u)"
                >
                  <td class="users-table__name">{{ u.name || '—' }}</td>
                  <td class="users-table__email">{{ u.email }}</td>
                  <td class="users-table__date">{{ formatDateTime(u.created_at) }}</td>
                  <td class="users-table__date">{{ formatDateTime(u.last_login_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
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

.admin-page__to-app:hover {
  border-color: var(--primary, #527de5);
  background: rgba(82, 125, 229, 0.06);
  color: var(--primary-hover, #4568d4);
}

.admin-page__to-app:focus-visible {
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

.admin-body {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

@media (min-width: 769px) {
  .admin-body {
    gap: 1.75rem;
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

@media (min-width: 640px) {
  .stats-grid {
    grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr));
    gap: 1rem;
  }
}

.stat-card {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding: 1rem 1.125rem;
  border-radius: 14px;
  background: var(--bg-primary, #fff);
  border: 1px solid var(--axis-grid, #e5e7eb);
  border-left: 3px solid var(--primary, #527de5);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}

.stat-label {
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--text-tertiary, #6b7280);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  line-height: 1.3;
}

.stat-value {
  font-size: clamp(1.375rem, 4vw, 1.75rem);
  font-weight: 800;
  color: var(--text-primary, #111827);
  font-variant-numeric: tabular-nums;
  line-height: 1.15;
}

.admin-panel {
  padding: 1.125rem 1.125rem 1.25rem;
  border-radius: 16px;
  background: var(--bg-primary, #fff);
  border: 1px solid var(--axis-grid, #e5e7eb);
  box-shadow: 0 4px 24px -8px rgba(15, 23, 42, 0.08);
}

@media (min-width: 769px) {
  .admin-panel {
    padding: 1.35rem 1.5rem 1.5rem;
  }
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
  max-width: 48rem;
}

.chart-empty {
  padding: 2rem 1rem;
  text-align: center;
  color: var(--text-tertiary, #64748b);
  font-size: 0.9375rem;
  background: var(--bg-secondary, #f8fafc);
  border-radius: 12px;
  border: 1px dashed var(--axis-border, #e2e8f0);
}

.chart-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem 1.5rem;
  margin-bottom: 0.75rem;
  font-size: 0.8125rem;
  color: var(--text-secondary, #475569);
}

.chart-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.chart-legend-swatch {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  flex-shrink: 0;
}

.chart-legend-swatch--primary {
  background: var(--primary, #527de5);
}

.chart-legend-swatch--verified {
  background: var(--success, #0d9488);
}

.admin-chart-wrap {
  width: 100%;
  min-height: 280px;
  height: 320px;
  position: relative;
}

@media (max-width: 768px) {
  .admin-chart-wrap {
    min-height: 240px;
    height: 260px;
  }
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

.users-table-wrap {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  border-radius: 12px;
  border: 1px solid var(--axis-grid, #e5e7eb);
  background: var(--bg-secondary, #f9fafb);
}

.users-table {
  width: 100%;
  min-width: 32rem;
  border-collapse: collapse;
  font-size: var(--text-caption-size, 0.875rem);
  background: var(--bg-primary, #fff);
}

@media (min-width: 768px) {
  .users-table {
    min-width: 38rem;
  }
}

/* Единая «коробка» ячейки заголовка: текстовые и сортируемые выровнены */
.users-table thead th.users-table__th {
  text-align: left;
  padding: 0.625rem 0.75rem;
  background: var(--bg-tertiary, #f3f4f6);
  color: var(--text-tertiary, #6b7280);
  font-weight: 700;
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  border-bottom: 1px solid var(--axis-grid, #e5e7eb);
  vertical-align: middle;
  line-height: 1.25;
}

@media (min-width: 640px) {
  .users-table thead th.users-table__th {
    padding: 0.625rem 1rem;
  }
}

.users-table__th--text {
  white-space: nowrap;
}

/* Та же высота и выравнивание, что у .users-table__th-btn (блочный flex на всю ширину ячейки) */
.users-table__th-label {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 2.75rem;
  box-sizing: border-box;
}

.users-table__th-btn {
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0.35rem;
  width: 100%;
  margin: 0;
  padding: 0;
  min-height: 2.75rem;
  border: none;
  border-radius: 8px;
  background: transparent;
  font: inherit;
  font-weight: 700;
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.users-table__th-btn:hover {
  color: var(--text-secondary, #374151);
  background: rgba(82, 125, 229, 0.08);
}

.users-table__th-btn:focus-visible {
  outline: 2px solid var(--primary, #527de5);
  outline-offset: -2px;
}

.users-table__sort-icon {
  display: inline-flex;
  color: var(--primary, #527de5);
  flex-shrink: 0;
}

.users-table__sort-icon--muted {
  color: var(--axis-text-light, #9ca3af);
}

.users-table td {
  padding: 0.65rem 0.75rem;
  border-bottom: 1px solid var(--axis-grid-light, #f3f4f6);
  color: var(--text-secondary, #374151);
  vertical-align: top;
}

@media (min-width: 640px) {
  .users-table td {
    padding: 0.75rem 1rem;
  }
}

.users-table tbody tr:last-child td {
  border-bottom: none;
}

.users-table tbody tr:hover td {
  background: rgba(82, 125, 229, 0.03);
}

.users-table__row--clickable {
  cursor: pointer;
}

.users-table__row--clickable:focus-visible {
  outline: 2px solid var(--primary, #527de5);
  outline-offset: -2px;
}

.users-table__name {
  font-weight: 600;
  color: var(--text-primary, #111827);
}

.users-table__email {
  word-break: break-word;
  overflow-wrap: anywhere;
}

.users-table__date {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  color: var(--text-tertiary, #6b7280);
  font-size: 0.8125rem;
}

@media (max-width: 768px) {
  .admin-page {
    padding-bottom: calc(var(--bottomNavHeight, 76px) + 0.5rem);
  }

  .admin-page__header {
    flex-direction: column;
    align-items: stretch;
  }

  .admin-page__to-app {
    width: 100%;
    justify-content: center;
    text-align: center;
    padding: 0.65rem 1rem;
    min-height: 44px;
  }
}
</style>
