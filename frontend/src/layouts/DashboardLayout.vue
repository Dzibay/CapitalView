<script setup>
import { onBeforeUnmount, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.store'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import { useLandingFonts } from '../site/components/home/useLandingMotion'

import '../cabinet/styles/cabinet.css'
import CvSidebar from '../cabinet/shell/CvSidebar.vue'
import CvHeader from '../cabinet/shell/CvHeader.vue'
import CvFooter from '../cabinet/shell/CvFooter.vue'
import CvBottomNav from '../cabinet/shell/CvBottomNav.vue'
import CommandPalette from '../cabinet/shell/CommandPalette.vue'

const router = useRouter()
const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const uiStore = useUIStore()

useLandingFonts('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Inter+Tight:wght@500;600;700&display=swap')

// Страницы на новых компонентах кабинета. Остальные — легаси-разметка в тёмной теме (.cv-legacy).
const DARK_ROUTES = new Set(['/dashboard'])
const viewKey = (route) => route.matched[route.matched.length - 1]?.path ?? route.path
const isDark = (route) => DARK_ROUTES.has(viewKey(route))

onMounted(async () => {
  document.body.classList.add('cv-body')
  try {
    // router guard уже проверил токен, но store мог не обновиться
    if (!authStore.isAuthenticated) {
      await authStore.checkToken()
    }
    if (!authStore.isAuthenticated) {
      router.push('/login')
      return
    }

    const currentRoute = router.currentRoute.value
    if (currentRoute.path.startsWith('/admin')) return

    if (currentRoute.path.startsWith('/assets/')) {
      // страница актива грузится первой, дашборд — следом
      setTimeout(async () => {
        await dashboardStore.fetchDashboard()
        uiStore.initSelectedPortfolioId(dashboardStore.portfolios)
      }, 0)
    } else {
      await dashboardStore.fetchDashboard()
      uiStore.initSelectedPortfolioId(dashboardStore.portfolios)
    }
  } catch (err) {
    if (import.meta.env.VITE_APP_DEV) {
      console.error('Ошибка при загрузке данных:', err)
    }
    // при ошибке сети не выкидываем на логин
    if (err.code !== 'ERR_NETWORK') {
      authStore.logout()
      router.push('/login')
    }
  }
})

onBeforeUnmount(() => {
  document.body.classList.remove('cv-body')
})

// выбранный портфель должен существовать в актуальных данных
watch(() => dashboardStore.portfolios, (portfolios) => {
  if (portfolios.length > 0) {
    const exists = portfolios.find((p) => p.id === uiStore.selectedPortfolioId)
    if (!uiStore.selectedPortfolioId || !exists) {
      uiStore.setSelectedPortfolioId(portfolios[0].id)
    }
  }
}, { immediate: true })

function toggleSidebar() {
  if (typeof window !== 'undefined' && window.innerWidth <= 768) return
  uiStore.toggleSidebar()
}
</script>

<template>
  <div class="cv cv-shell" :class="{ 'is-collapsed': uiStore.isSidebarCollapsed }">
    <div class="cv-shell__aurora" aria-hidden="true" />
    <CvSidebar
      :user="authStore.user"
      :collapsed="uiStore.isSidebarCollapsed"
      @toggle="toggleSidebar"
    />
    <div class="cv-shell__main">
      <CvHeader :user="authStore.user" />
      <main class="cv-shell__content">
        <router-view v-slot="{ Component, route }">
          <Transition name="cv-page" mode="out-in">
            <div :key="viewKey(route)" class="cv-view" :class="{ 'cv-legacy': !isDark(route) }">
              <component :is="Component" />
            </div>
          </Transition>
        </router-view>
      </main>
      <CvFooter />
    </div>
    <CvBottomNav :user="authStore.user" />
    <CommandPalette :user="authStore.user" />
  </div>
</template>

<style scoped>
.cv-shell {
  position: relative;
  min-height: 100vh;
  min-height: 100dvh;
}
/* едва заметный свет сверху — без цветных пятен */
.cv-shell__aurora {
  position: fixed; inset: 0 0 auto 0; height: 520px; z-index: 0; pointer-events: none;
  background: radial-gradient(55% 60% at 30% -18%, rgba(100, 116, 255, .07), transparent 72%);
}
.cv-shell__main {
  position: relative; z-index: 1;
  display: flex; flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
  min-width: 0;
  margin-left: var(--cv-side-w);
  transition: margin-left .32s var(--cv-ease);
}
.cv-shell.is-collapsed .cv-shell__main { margin-left: var(--cv-side-w-c); }

.cv-shell__content {
  flex: 1;
  min-width: 0;
  padding: 8px var(--cv-pad) 0;
  /* широкие дети не раздувают колонку; горизонтальный скролл — внутри своих обёрток */
  overflow-x: clip;
}
.cv-view { min-width: 0; max-width: 1600px; margin: 0 auto; }

@media (max-width: 1200px) {
  .cv-shell { --cv-pad: 20px; }
}
@media (max-width: 768px) {
  .cv-shell { --cv-pad: 12px; }
  .cv-shell__main,
  .cv-shell.is-collapsed .cv-shell__main {
    margin-left: 0;
    padding-bottom: calc(var(--cv-bottom-h) + 14px + env(safe-area-inset-bottom, 0px));
  }
  .cv-shell__content { padding-top: 4px; }
}
</style>
