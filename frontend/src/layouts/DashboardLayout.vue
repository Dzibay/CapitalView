<script setup>
import { onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.store'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import { useTransactionsStore } from '../stores/transactions.store'

import AppSidebar from '../components/AppSidebar.vue'
import AppHeader from '../components/AppHeader.vue'

const router = useRouter()

// Используем stores вместо ref
const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const uiStore = useUIStore()
const transactionsStore = useTransactionsStore()

// Инициализация при загрузке
onMounted(async () => {
  try {
    // Проверяем токен через store
    await authStore.checkToken()
    
    if (!authStore.isAuthenticated) {
      router.push('/login')
      return
    }
    
    // Загружаем данные dashboard (теперь включает транзакции и аналитику)
    await dashboardStore.fetchDashboard()
    
    // Инициализируем выбранный портфель
    uiStore.initSelectedPortfolioId(dashboardStore.portfolios)
  } catch (err) {
    if (import.meta.env.DEV) {
      console.error('Ошибка при загрузке данных:', err)
    }
    // При ошибке сети не перенаправляем на логин, просто показываем ошибку
    if (err.code !== 'ERR_NETWORK') {
      authStore.logout()
      router.push('/login')
    }
  }
})

// Следим за портфелями: обновляем выбранный портфель при изменении данных
watch(() => dashboardStore.portfolios, (portfolios) => {
  if (portfolios.length > 0) {
    const exists = portfolios.find(p => p.id === uiStore.selectedPortfolioId)
    if (!uiStore.selectedPortfolioId || !exists) {
      uiStore.setSelectedPortfolioId(portfolios[0].id)
    }
  }
}, { immediate: true })

</script>

<template>
  <div class="dashboard-layout">
    <AppSidebar :user="authStore.user" :collapsed="uiStore.isSidebarCollapsed" />
    <main class="main-content" :class="{ 'full-width': uiStore.isSidebarCollapsed }">
      <AppHeader :user="authStore.user" @toggle-sidebar="uiStore.toggleSidebar" />
      <div class="page-content">
        <router-view />
      </div>
    </main>
  </div>
</template>

<style scoped>
.sidebar-hidden {
  transform: translateX(-100%);
}

.main-content {
  flex-grow: 1;
  margin-left: var(--sidebarWidth);
  transition: margin-left 0.3s ease-in-out;
  min-height: 100vh;
}

.main-content.full-width {
  margin-left: var(--sidebarWidthCollapsed);
}

.page-content {
  margin-top: var(--headerHeight);
  padding: var(--spacing);
}
</style>
