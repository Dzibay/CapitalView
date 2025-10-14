<script setup>
import { ref, onMounted, provide } from 'vue'
import { useRouter } from 'vue-router'
import { authService } from '../services/authService.js'
import assetsService from "../services/assetsService";
import { fetchDashboardData } from '../services/dashboardService.js'

import AppSidebar from '../components/AppSidebar.vue'
import AppHeader from '../components/AppHeader.vue'

const user = ref(null)
const dashboardData = ref(null)
const loading = ref(true)
const isSidebarVisible = ref(true)
const router = useRouter()

// 🔹 Универсальная перезагрузка Dashboard
const reloadDashboard = async () => {
  try {
    dashboardData.value = await fetchDashboardData()
  } catch (err) {
    console.error('Ошибка получения данных Dashboard:', err)
  }
}

// 🔹 Добавление актива
const addAsset = async (assetData) => {
  try {
    await assetsService.addAsset(assetData)
    await reloadDashboard()
  } catch (err) {
    console.error('Ошибка добавления актива:', err)
  }
}

// 🔹 Продажа актива
const sellAsset = async ({ portfolio_asset_id, quantity, price, date }) => {
  try {
    await assetsService.sellAsset(portfolio_asset_id, quantity, price, date)
    await reloadDashboard()
  } catch (err) {
    console.error('Ошибка продажи актива:', err)
  }
}

// 🔹 Удаление актива
const removeAsset = async (assetId) => {
  if (!confirm("Удалить актив?")) return
  try {
    await assetsService.deleteAsset(assetId)
    await reloadDashboard()
  } catch (err) {
    console.error('Ошибка удаления актива:', err)
  }
}

// // 🔹 Импорт портфеля из Tinkoff
// const importPortfolio = async ({ token, portfolioId, portfolio_name }) => {
//   try {
//     const res = await assetsService.importPortfolio(token, portfolioId, portfolio_name)
//     if (!res.success) throw new Error(res.error || 'Ошибка импорта портфеля')
//     await reloadDashboard()
//   } catch (err) {
//     console.error('Ошибка импорта портфеля:', err)
//   }
// }

// 🔹 Инициализация при загрузке
onMounted(async () => {
  try {
    const u = await authService.checkToken()
    if (!u) {
      router.push('/login')
      return
    }
    user.value = u.user
    await reloadDashboard()
    console.log('✅ Dashboard данные загружены', dashboardData.value)
  } catch (err) {
    console.error('Ошибка при авторизации:', err)
    authService.logout()
    router.push('/login')
  } finally {
    loading.value = false
  }
})

// 👇 передаём всё дочерним страницам
provide('user', user)
provide('dashboardData', dashboardData)
provide('loading', loading)
provide('reloadDashboard', reloadDashboard)
provide('addAsset', addAsset)
// provide('sellAsset', sellAsset)
provide('removeAsset', removeAsset)
// provide('importPortfolio', importPortfolio)

function toggleSidebar() {
  isSidebarVisible.value = !isSidebarVisible.value
}
</script>

<template>
  <div class="dashboard-layout">
    <AppSidebar :class="{ 'sidebar-hidden': !isSidebarVisible }" />
    <main class="main-content" :class="{ 'full-width': !isSidebarVisible }">
      <AppHeader :user="user" @toggle-sidebar="toggleSidebar" />
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
  margin-left: 0;
}

.page-content {
  margin-top: var(--headerHeight);
  padding: var(--spacing);
}
</style>
