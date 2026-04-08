<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '../layouts/PageLayout.vue'
import PageHeader from '../layouts/PageHeader.vue'
import LoadingState from '../components/base/LoadingState.vue'
import { adminService } from '../services/adminService'

const router = useRouter()
const loading = ref(true)
const error = ref('')
const overview = ref(null)

onMounted(async () => {
  error.value = ''
  loading.value = true
  try {
    overview.value = await adminService.fetchStatsOverview()
  } catch (e) {
    error.value = e.response?.data?.error || e.message || 'Не удалось загрузить статистику'
  } finally {
    loading.value = false
  }
})

function goApp() {
  router.push('/dashboard')
}
</script>

<template>
  <PageLayout>
    <PageHeader title="Администрирование" subtitle="Сводка по сервису" />
    <p class="admin-lead">
      <button type="button" class="link-to-app" @click="goApp">Перейти в приложение</button>
    </p>

    <LoadingState v-if="loading" message="Загрузка статистики…" />

    <div v-else-if="error" class="admin-error" role="alert">
      {{ error }}
    </div>

    <div v-else-if="overview" class="stats-grid">
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
  </PageLayout>
</template>

<style scoped>
.admin-lead {
  margin: 0 0 1.25rem;
  font-size: 0.9375rem;
}

.link-to-app {
  background: none;
  border: none;
  padding: 0;
  color: #527de5;
  font: inherit;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.link-to-app:hover {
  color: #3d63c9;
}

.admin-error {
  padding: 1rem 1.25rem;
  border-radius: 12px;
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.stat-card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1.25rem 1.5rem;
  border-radius: 14px;
  background: linear-gradient(145deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.stat-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 800;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}
</style>
