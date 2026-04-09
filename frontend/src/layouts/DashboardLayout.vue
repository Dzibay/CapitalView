<script setup>
import { onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.store'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import { useTransactionsStore } from '../stores/transactions.store'

import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
import AppFooter from './AppFooter.vue'
import AppBottomNav from './AppBottomNav.vue'

const router = useRouter()

// Используем stores вместо ref
const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const uiStore = useUIStore()
const transactionsStore = useTransactionsStore()

// Инициализация при загрузке
onMounted(async () => {
  try {
    // ОПТИМИЗИРОВАНО: проверяем токен только если он еще не проверен
    // (router guard уже проверил токен, но может быть не обновил store)
    if (!authStore.isAuthenticated) {
      await authStore.checkToken()
    }
    
    if (!authStore.isAuthenticated) {
      router.push('/login')
      return
    }
    
    // ОПТИМИЗИРОВАНО: загружаем dashboard в фоновом режиме после загрузки основного контента
    // Это особенно важно для страницы актива, чтобы не блокировать загрузку
    const currentRoute = router.currentRoute.value
    const isAdminPage = currentRoute.path.startsWith('/admin')
    const isAssetDetailPage = currentRoute.path.startsWith('/assets/')

    if (isAdminPage) {
      return
    }

    if (isAssetDetailPage) {
      // Для страницы актива откладываем загрузку dashboard
      setTimeout(async () => {
        await dashboardStore.fetchDashboard()
        uiStore.initSelectedPortfolioId(dashboardStore.portfolios)
      }, 0)
    } else {
      // Для других страниц загружаем сразу
      await dashboardStore.fetchDashboard()
      uiStore.initSelectedPortfolioId(dashboardStore.portfolios)
    }
  } catch (err) {
    if (import.meta.env.VITE_APP_DEV) {
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

function handleToggleSidebar() {
  if (typeof window !== 'undefined' && window.innerWidth <= 768) {
    return
  }
  uiStore.toggleSidebar()
}

</script>

<template>
  <div class="dashboard-layout">
    <AppSidebar
      :user="authStore.user"
      :collapsed="uiStore.isSidebarCollapsed"
      :mobile-open="false"
    />
    <main class="main-content" :class="{ 'full-width': uiStore.isSidebarCollapsed }">
      <AppHeader
        :user="authStore.user"
        :sidebar-collapsed="uiStore.isSidebarCollapsed"
        @toggle-sidebar="handleToggleSidebar"
      />
      <div class="page-content">
        <router-view />
      </div>
      <AppFooter />
    </main>
    <AppBottomNav />
  </div>
</template>

<style scoped>
.sidebar-hidden {
  transform: translateX(-100%);
}

.main-content {
  flex-grow: 1;
  flex-shrink: 1;
  margin-left: var(--sidebarWidth);
  transition: margin-left 0.3s ease-in-out;
  min-height: 100vh;
  min-width: 0;
  max-width: 100%;
  display: flex;
  flex-direction: column;
}

.main-content.full-width {
  margin-left: var(--sidebarWidthCollapsed);
}

.page-content {
  margin-top: var(--headerHeight);
  padding: var(--spacing);
  flex: 1;
  min-width: 0;
  /* Не даём широким детям раздувать всю колонку; горизонтальный скролл — внутри своих обёрток (таблицы и т.д.) */
  overflow-x: hidden;
  width: 100%;
}

/* Планшет: меньше боковых отступов */
@media (max-width: 1200px) {
  .page-content {
    padding: 16px 12px;
  }
}

/* Адаптив: мобильные */
@media (max-width: 768px) {
  .main-content,
  .main-content.full-width {
    margin-left: 0;
    padding-bottom: calc(var(--bottomNavHeight) + env(safe-area-inset-bottom, 0px));
  }

  .page-content {
    padding: 10px 12px;
  }
}
</style>
